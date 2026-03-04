"""Local filesystem storage manager.

Stores files in a directory structure under ``STORAGE_DIR``.
Each file may have an accompanying ``.meta`` JSON sidecar that
records ``content_type``.

A :class:`StorageProtocol` defines the public interface so that
alternative backends (e.g. S3 / MinIO) can be swapped in via
configuration without changing application code.
"""

import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any, BinaryIO, Protocol, runtime_checkable

from core.app_exception import AppException
from core.config import STORAGE_DIR
from core.logger import get_logger
from fastapi import Depends
from models.enums import AppErrorCode

storage_logger = get_logger("storage")


# ── Public protocol ─────────────────────────────────────────
@runtime_checkable
class StorageProtocol(Protocol):
    """Interface that any storage backend must implement."""

    def verify_connection(self) -> None:
        """Verify that the backend is reachable and writable."""
        ...

    def metadata(self, key: str) -> dict[str, Any] | None:
        """Return metadata dict or *None* if the key does not exist.

        Expected keys: ``ContentLength``, ``LastModified``,
        ``ETag``, ``ContentType``.
        """
        ...

    def exists(self, key: str) -> bool:
        """Return whether *key* exists in storage."""
        ...

    def get_last_modified(self, key: str) -> datetime:
        """Return the last-modified timestamp of *key*."""
        ...

    def delete(self, key: str) -> bool:
        """Delete *key* (and any sidecar metadata).

        Returns ``True`` on success, ``False`` on failure.
        """
        ...

    def upload(self, key: str, data: BinaryIO, content_type: str) -> None:
        """Store *data* under *key* with the given content type."""
        ...

    def download(self, key: str) -> BinaryIO:
        """Return an open file-like object for *key*."""
        ...

    def download_stream(self, key: str, chunk_size: int = 8192) -> Iterator[bytes]:
        """Yield the contents of *key* in chunks."""
        ...

    def list_keys(self) -> Iterator[str]:
        """Yield every storage key currently stored."""
        ...


# ── Local filesystem implementation ─────────────────────────
class StorageManager:
    """Local filesystem storage manager.

    Stores files in a directory tree under ``STORAGE_DIR``.
    Each file may have an accompanying ``.meta`` JSON sidecar
    that records ``content_type``.
    """

    def __init__(self, storage_dir: str | None = None) -> None:
        """Initialize the StorageManager and verify the directory."""
        self._storage_dir = storage_dir or STORAGE_DIR
        if not self._storage_dir:
            raise RuntimeError("STORAGE_DIR is not configured.")
        self.verify_connection()

    def verify_connection(self) -> None:
        """Verify that the storage directory exists and is writable."""
        os.makedirs(self._storage_dir, exist_ok=True)
        test_path = os.path.join(self._storage_dir, ".write_test")
        try:
            with open(test_path, "w") as f:
                f.write("ok")
            os.remove(test_path)
        except OSError as e:
            raise RuntimeError(f"Storage directory {self._storage_dir} is not writable: {e}") from e
        storage_logger.info("Storage configured (dir: %s)", self._storage_dir)

    # ── path helpers ────────────────────────────────────────
    def _path(self, key: str) -> str:
        """Return the full filesystem path for a storage key.

        Keys may contain forward slashes to denote subdirectories
        (e.g. ``documents/abc123``).  Each path component is
        validated to prevent directory traversal.
        """
        parts = key.split("/")
        for part in parts:
            if not part or part in (".", "..") or os.sep in part:
                raise ValueError(f"Invalid storage key: {key!r}")

        candidate = os.path.join(self._storage_dir, *parts)
        # Belt-and-suspenders: ensure resolved path stays inside
        # the storage root even if os.sep tricks slip through.
        if not os.path.abspath(candidate).startswith(os.path.abspath(self._storage_dir) + os.sep) and os.path.abspath(
            candidate
        ) != os.path.abspath(self._storage_dir):
            raise ValueError(f"Path traversal detected for key: {key!r}")

        return candidate

    def _meta_path(self, key: str) -> str:
        """Return the path for the sidecar metadata file."""
        return self._path(key) + ".meta"

    def _read_meta(self, key: str) -> dict[str, Any]:
        """Read the sidecar metadata file, if it exists."""
        meta_path = self._meta_path(key)
        if os.path.exists(meta_path):
            try:
                with open(meta_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                storage_logger.warning(
                    "Corrupt .meta sidecar for %s, falling back to defaults",
                    key,
                )
        return {}

    def _write_meta(self, key: str, content_type: str) -> None:
        """Write the sidecar metadata file atomically."""
        meta_path = self._meta_path(key)
        parent = os.path.dirname(meta_path)
        os.makedirs(parent, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=parent, suffix=".meta.tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"content_type": content_type}, f)
            os.rename(tmp_path, meta_path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    @staticmethod
    def _generate_etag(file_path: str) -> str:
        """Generate an ETag from file mtime and size."""
        stat = os.stat(file_path)
        raw = f"{stat.st_mtime_ns}-{stat.st_size}"
        return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324

    # ── public interface ────────────────────────────────────
    def metadata(self, key: str) -> dict[str, Any] | None:
        """Return metadata for a stored file, or None if missing."""
        file_path = self._path(key)
        if not os.path.isfile(file_path):
            return None

        stat = os.stat(file_path)
        meta = self._read_meta(key)
        etag = self._generate_etag(file_path)

        return {
            "ContentLength": stat.st_size,
            "LastModified": datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            "ETag": f'"{etag}"',
            "ContentType": meta.get("content_type", "application/octet-stream"),
        }

    def exists(self, key: str) -> bool:
        """Check if a file exists in storage."""
        return self.metadata(key) is not None

    def get_last_modified(self, key: str) -> datetime:
        """Get the Last-Modified timestamp of a stored file."""
        metadata = self.metadata(key)
        if metadata is None:
            raise FileNotFoundError(f"File not found: {key}")
        return metadata["LastModified"]

    def delete(self, key: str) -> bool:
        """Delete a file and its metadata sidecar from storage."""
        file_path = self._path(key)
        meta_path = self._meta_path(key)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            if os.path.isfile(meta_path):
                os.remove(meta_path)
            storage_logger.info("Deleted object: %s", key)
            return True
        except OSError as e:
            storage_logger.error("Failed to delete object %s: %s", key, e)
            return False

    def upload(self, key: str, data: BinaryIO, content_type: str) -> None:
        """Upload a file to storage atomically.

        Writes to a temporary file first, then renames to the
        final path to prevent partial reads.  Subdirectories
        are created on demand.
        """
        file_path = self._path(key)
        parent = os.path.dirname(file_path)
        os.makedirs(parent, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "wb") as f:
                    while chunk := data.read(8192):
                        f.write(chunk)
                os.rename(tmp_path, file_path)
            except BaseException:
                # Clean up temp file on any failure
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise
        except OSError as e:
            storage_logger.error("Upload failed for %s: %s", key, e)
            raise AppException(
                status_code=502,
                error_code=AppErrorCode.STORAGE_UNAVAILABLE,
                detail="File storage is temporarily unavailable.",
            ) from e

        self._write_meta(key, content_type)
        storage_logger.info(
            "Uploaded object: %s (content_type=%s)",
            key,
            content_type,
        )

    def download(self, key: str) -> BinaryIO:
        """Download a file from storage, returning a file object."""
        file_path = self._path(key)
        if not os.path.isfile(file_path):
            storage_logger.warning("Object not found: %s", key)
            raise AppException(
                status_code=404,
                error_code=AppErrorCode.FILE_NOT_FOUND,
                detail="The requested file was not found.",
            )
        try:
            storage_logger.debug("Downloaded object: %s", key)
            return open(file_path, "rb")
        except OSError as e:
            storage_logger.error("Download failed for %s: %s", key, e)
            raise AppException(
                status_code=502,
                error_code=AppErrorCode.STORAGE_UNAVAILABLE,
                detail="File storage is temporarily unavailable.",
            ) from e

    def download_stream(self, key: str, chunk_size: int = 8192) -> Iterator[bytes]:
        """Return an iterator of bytes, streaming in chunks.

        Callers can forward the iterator directly to
        ``starlette.responses.StreamingResponse``.
        """
        file_path = self._path(key)
        if not os.path.isfile(file_path):
            storage_logger.warning("Object not found: %s", key)
            raise AppException(
                status_code=404,
                error_code=AppErrorCode.FILE_NOT_FOUND,
                detail="The requested file was not found.",
            )

        def _reader() -> Iterator[bytes]:
            try:
                with open(file_path, "rb") as f:
                    while chunk := f.read(chunk_size):
                        yield chunk
            except OSError as e:
                storage_logger.error(
                    "Download stream failed for %s: %s",
                    key,
                    e,
                )
                raise AppException(
                    status_code=502,
                    error_code=AppErrorCode.STORAGE_UNAVAILABLE,
                    detail="File storage is temporarily unavailable.",
                ) from e

        return _reader()

    def list_keys(self) -> Iterator[str]:
        """Yield every storage key currently stored.

        Walks the directory tree and yields keys relative to
        the storage root, skipping ``.meta`` sidecars and
        temporary files.
        """
        root = self._storage_dir
        for dirpath, _dirs, filenames in os.walk(root):
            for fname in filenames:
                if fname.endswith((".meta", ".tmp", ".meta.tmp")):
                    continue
                # Hidden helper files (e.g. .write_test)
                if fname.startswith("."):
                    continue
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, root)
                # Normalise to forward slashes (cross-platform)
                yield rel.replace(os.sep, "/")


@lru_cache(maxsize=1)
def get_storage_manager() -> StorageManager:
    """Lazily instantiate the StorageManager.

    This keeps module import fast and side-effect-free while
    preserving the dependency-injection interface via ``Storage``.
    """
    return StorageManager()


Storage = Annotated[StorageManager, Depends(get_storage_manager)]
