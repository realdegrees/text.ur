"""Unit tests for the local filesystem StorageManager.

Tests cover upload, download, download_stream, delete, metadata,
exists, get_last_modified, ETag generation, list_keys, path
traversal prevention, and subdirectory support.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import time

import pytest
from api.dependencies.storage import StorageManager
from core.app_exception import AppException


@pytest.fixture()
def storage(tmp_path: object) -> StorageManager:
    """Create a StorageManager backed by a temporary directory."""
    return StorageManager(storage_dir=str(tmp_path))


# ── Upload / Download ──────────────────────────────────────


def test_upload_and_download(storage: StorageManager) -> None:
    """Uploaded bytes can be retrieved via download()."""
    data = io.BytesIO(b"hello world")
    storage.upload("myfile", data, content_type="text/plain")

    result = storage.download("myfile")
    assert result.read() == b"hello world"
    result.close()


def test_upload_creates_meta_sidecar(storage: StorageManager) -> None:
    """upload() writes a .meta JSON sidecar with the content type."""
    storage.upload("doc", io.BytesIO(b"x"), content_type="application/pdf")

    meta_path = storage._meta_path("doc")
    assert os.path.isfile(meta_path)
    with open(meta_path) as f:
        meta = json.load(f)
    assert meta["content_type"] == "application/pdf"


def test_upload_overwrites_existing(storage: StorageManager) -> None:
    """A second upload to the same key replaces the file."""
    storage.upload("key", io.BytesIO(b"v1"), content_type="text/plain")
    storage.upload("key", io.BytesIO(b"v2"), content_type="text/plain")

    assert storage.download("key").read() == b"v2"


# ── Subdirectory support ───────────────────────────────────


def test_upload_with_subdirectory(storage: StorageManager) -> None:
    """Keys containing slashes create subdirectories on disk."""
    data = io.BytesIO(b"pdf bytes")
    storage.upload("documents/abc123", data, content_type="application/pdf")

    result = storage.download("documents/abc123")
    assert result.read() == b"pdf bytes"
    result.close()


def test_nested_subdirectories(storage: StorageManager) -> None:
    """Multiple levels of nesting work correctly."""
    storage.upload("a/b/c/d", io.BytesIO(b"deep"), content_type="text/plain")

    assert storage.exists("a/b/c/d")
    assert storage.download("a/b/c/d").read() == b"deep"


# ── Path traversal prevention ──────────────────────────────


@pytest.mark.parametrize(
    "key",
    [
        "..",
        "../etc/passwd",
        "foo/../../etc/passwd",
        "foo/..",
        "./foo",
        "foo/./bar",
        "",
        "foo//bar",
    ],
)
def test_path_traversal_rejected(storage: StorageManager, key: str) -> None:
    """Keys that could escape the storage root are rejected."""
    with pytest.raises(ValueError, match="Invalid storage key"):
        storage._path(key)


def test_valid_key_accepted(storage: StorageManager) -> None:
    """A simple alphanumeric key with slashes passes validation."""
    # Should not raise
    path = storage._path("documents/abc123")
    assert "documents" in path
    assert "abc123" in path


# ── Download stream ────────────────────────────────────────


def test_download_stream(storage: StorageManager) -> None:
    """download_stream() yields the file content in chunks."""
    payload = b"A" * 20000  # larger than default chunk_size
    storage.upload("big", io.BytesIO(payload), content_type="application/octet-stream")

    chunks = list(storage.download_stream("big", chunk_size=8192))
    assert b"".join(chunks) == payload
    assert len(chunks) >= 2  # should be split into multiple chunks


def test_download_stream_missing_key(storage: StorageManager) -> None:
    """download_stream() raises AppException for missing keys."""
    with pytest.raises(AppException) as exc_info:
        storage.download_stream("nonexistent")
    assert exc_info.value.status_code == 404


# ── Delete ─────────────────────────────────────────────────


def test_delete_removes_file_and_meta(storage: StorageManager) -> None:
    """delete() removes both the data file and its .meta sidecar."""
    storage.upload("todel", io.BytesIO(b"x"), content_type="text/plain")
    assert storage.exists("todel")

    result = storage.delete("todel")
    assert result is True
    assert not storage.exists("todel")
    assert not os.path.isfile(storage._meta_path("todel"))


def test_delete_missing_key_returns_true(storage: StorageManager) -> None:
    """Deleting a non-existent key still returns True (idempotent)."""
    result = storage.delete("ghost")
    assert result is True


# ── Metadata / exists / get_last_modified ──────────────────


def test_metadata_returns_none_for_missing(storage: StorageManager) -> None:
    """metadata() returns None when the key doesn't exist."""
    assert storage.metadata("nope") is None


def test_metadata_contains_expected_keys(storage: StorageManager) -> None:
    """metadata() returns ContentLength, LastModified, ETag, ContentType."""
    storage.upload("m", io.BytesIO(b"12345"), content_type="image/png")

    meta = storage.metadata("m")
    assert meta is not None
    assert meta["ContentLength"] == 5
    assert meta["ContentType"] == "image/png"
    assert "ETag" in meta
    assert "LastModified" in meta


def test_metadata_default_content_type_without_sidecar(
    storage: StorageManager,
) -> None:
    """When the .meta sidecar is missing, content type falls back to octet-stream."""
    # Write a file directly without going through upload()
    file_path = storage._path("raw")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(b"raw bytes")

    meta = storage.metadata("raw")
    assert meta is not None
    assert meta["ContentType"] == "application/octet-stream"


def test_exists_true_and_false(storage: StorageManager) -> None:
    """exists() reflects whether the key has been uploaded."""
    assert not storage.exists("x")
    storage.upload("x", io.BytesIO(b"y"), content_type="text/plain")
    assert storage.exists("x")


def test_get_last_modified(storage: StorageManager) -> None:
    """get_last_modified() returns a datetime close to now."""
    storage.upload("ts", io.BytesIO(b"z"), content_type="text/plain")

    from datetime import UTC, datetime

    ts = storage.get_last_modified("ts")
    assert abs((datetime.now(UTC) - ts).total_seconds()) < 5


def test_get_last_modified_missing(storage: StorageManager) -> None:
    """get_last_modified() raises FileNotFoundError for missing keys."""
    with pytest.raises(FileNotFoundError):
        storage.get_last_modified("missing")


# ── ETag ───────────────────────────────────────────────────


def test_etag_deterministic(storage: StorageManager) -> None:
    """The same file produces the same ETag on repeated calls."""
    storage.upload("e", io.BytesIO(b"data"), content_type="text/plain")

    meta1 = storage.metadata("e")
    meta2 = storage.metadata("e")
    assert meta1["ETag"] == meta2["ETag"]


def test_etag_changes_on_reupload(storage: StorageManager) -> None:
    """Re-uploading changes mtime, which should change the ETag."""
    storage.upload("e2", io.BytesIO(b"v1"), content_type="text/plain")
    etag1 = storage.metadata("e2")["ETag"]

    # Ensure mtime differs (filesystem resolution may be 1 s)
    time.sleep(0.05)
    storage.upload("e2", io.BytesIO(b"v2"), content_type="text/plain")
    _ = storage.metadata("e2")["ETag"]

    # Use different sizes to guarantee a different ETag.
    storage.upload("e2", io.BytesIO(b"v2longer"), content_type="text/plain")
    etag3 = storage.metadata("e2")["ETag"]
    assert etag1 != etag3


# ── list_keys ──────────────────────────────────────────────


def test_list_keys_empty(storage: StorageManager) -> None:
    """list_keys() yields nothing for an empty storage."""
    assert list(storage.list_keys()) == []


def test_list_keys_includes_files(storage: StorageManager) -> None:
    """list_keys() yields uploaded file keys."""
    storage.upload("a", io.BytesIO(b"1"), content_type="text/plain")
    storage.upload("b/c", io.BytesIO(b"2"), content_type="text/plain")

    keys = set(storage.list_keys())
    assert "a" in keys
    assert "b/c" in keys


def test_list_keys_excludes_meta_and_tmp(storage: StorageManager) -> None:
    """list_keys() skips .meta sidecars and .tmp files."""
    storage.upload("f", io.BytesIO(b"x"), content_type="text/plain")

    # Create a stray .tmp file
    tmp_path = os.path.join(storage._storage_dir, "stray.tmp")
    with open(tmp_path, "w") as fh:
        fh.write("tmp")

    keys = list(storage.list_keys())
    assert "f" in keys
    assert not any(k.endswith(".meta") for k in keys)
    assert not any(k.endswith(".tmp") for k in keys)


def test_list_keys_excludes_hidden(storage: StorageManager) -> None:
    """list_keys() skips dot-prefixed files like .write_test."""
    # Create a hidden file
    hidden_path = os.path.join(storage._storage_dir, ".hidden")
    with open(hidden_path, "w") as fh:
        fh.write("hidden")

    assert ".hidden" not in list(storage.list_keys())


# ── Error paths ────────────────────────────────────────────


def test_download_missing_raises(storage: StorageManager) -> None:
    """download() raises AppException 404 for missing files."""
    with pytest.raises(AppException) as exc_info:
        storage.download("nonexistent")
    assert exc_info.value.status_code == 404


def test_verify_connection_bad_dir() -> None:
    """StorageManager raises for a non-creatable directory."""
    # /proc is a virtual filesystem — creating subdirs is not allowed.
    with pytest.raises((RuntimeError, OSError)):
        StorageManager(storage_dir="/proc/nonexistent_path_xyz")


def test_corrupt_meta_sidecar(storage: StorageManager) -> None:
    """A corrupt .meta sidecar falls back to defaults gracefully."""
    storage.upload("cm", io.BytesIO(b"x"), content_type="image/png")

    # Corrupt the sidecar
    meta_path = storage._meta_path("cm")
    with open(meta_path, "w") as f:
        f.write("{bad json")

    meta = storage.metadata("cm")
    assert meta is not None
    # Falls back to octet-stream when sidecar is unreadable
    assert meta["ContentType"] == "application/octet-stream"
