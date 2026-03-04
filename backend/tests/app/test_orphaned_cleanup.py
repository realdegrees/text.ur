"""Tests for orphaned storage file cleanup.

Exercises ``_cleanup_orphaned_files`` from ``util.cleanup``,
verifying that:
- Files without a matching ``Document`` row and older than 24 h
  are deleted.
- Recent files (< 24 h) are kept even if orphaned.
- Files with a matching ``Document`` row are never deleted.

The cleanup function imports ``get_storage_manager`` and
``SessionFactory`` *inside* its body (lazy imports to avoid
circular dependencies), so we patch them at their origin
modules and let the function resolve them dynamically.
"""

from __future__ import annotations

import io
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.dependencies.storage import StorageManager


@pytest.fixture()
def storage(tmp_path: object) -> StorageManager:
    """Create a StorageManager backed by a temporary directory."""
    return StorageManager(storage_dir=str(tmp_path))


def _age_file(path: str, age_seconds: float) -> None:
    """Backdate mtime of *path* by *age_seconds*."""
    old_time = time.time() - age_seconds
    os.utime(path, (old_time, old_time))


def _mock_db_context(known_keys: list[str]) -> MagicMock:
    """Build a mock that mimics ``SessionFactory()`` as an async context manager."""
    mock_result = MagicMock()
    mock_result.all.return_value = known_keys

    mock_session = AsyncMock()
    mock_session.exec = AsyncMock(return_value=mock_result)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx


def _mock_advisory_lock(acquired: bool = True) -> MagicMock:
    """Build a mock for the ``advisory_lock`` async context manager."""
    lock_ctx = AsyncMock()
    lock_ctx.__aenter__ = AsyncMock(return_value=acquired)
    lock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_lock = MagicMock(return_value=lock_ctx)
    return mock_lock


async def test_orphaned_old_files_deleted(
    storage: StorageManager,
) -> None:
    """Files older than 24 h with no Document row are deleted."""
    storage.upload(
        "documents/old1",
        io.BytesIO(b"data1"),
        content_type="application/pdf",
    )
    storage.upload(
        "documents/old2",
        io.BytesIO(b"data2"),
        content_type="application/pdf",
    )
    _age_file(storage._path("documents/old1"), 90000)
    _age_file(storage._path("documents/old2"), 90000)

    with (
        patch("util.cleanup.advisory_lock", _mock_advisory_lock()),
        patch(
            "api.dependencies.storage.get_storage_manager",
            return_value=storage,
        ),
        patch(
            "api.dependencies.database.SessionFactory",
            return_value=_mock_db_context([]),
        ),
    ):
        from util.cleanup import _cleanup_orphaned_files

        removed = await _cleanup_orphaned_files()

    assert removed == 2
    assert not storage.exists("documents/old1")
    assert not storage.exists("documents/old2")


async def test_recent_orphaned_files_kept(
    storage: StorageManager,
) -> None:
    """Files less than 24 h old are kept even if orphaned."""
    storage.upload(
        "documents/recent",
        io.BytesIO(b"new"),
        content_type="application/pdf",
    )

    with (
        patch("util.cleanup.advisory_lock", _mock_advisory_lock()),
        patch(
            "api.dependencies.storage.get_storage_manager",
            return_value=storage,
        ),
        patch(
            "api.dependencies.database.SessionFactory",
            return_value=_mock_db_context([]),
        ),
    ):
        from util.cleanup import _cleanup_orphaned_files

        removed = await _cleanup_orphaned_files()

    assert removed == 0
    assert storage.exists("documents/recent")


async def test_known_files_kept(
    storage: StorageManager,
) -> None:
    """Files whose storage_key matches a Document row are kept."""
    storage.upload(
        "documents/known",
        io.BytesIO(b"tracked"),
        content_type="application/pdf",
    )
    _age_file(storage._path("documents/known"), 90000)

    with (
        patch("util.cleanup.advisory_lock", _mock_advisory_lock()),
        patch(
            "api.dependencies.storage.get_storage_manager",
            return_value=storage,
        ),
        patch(
            "api.dependencies.database.SessionFactory",
            return_value=_mock_db_context(["documents/known"]),
        ),
    ):
        from util.cleanup import _cleanup_orphaned_files

        removed = await _cleanup_orphaned_files()

    assert removed == 0
    assert storage.exists("documents/known")


async def test_mixed_scenario(
    storage: StorageManager,
) -> None:
    """Only old orphaned files are deleted; recent + tracked survive."""
    # Old orphan — should be deleted
    storage.upload(
        "documents/orphan-old",
        io.BytesIO(b"old"),
        content_type="application/pdf",
    )
    _age_file(storage._path("documents/orphan-old"), 90000)

    # Recent orphan — should survive (< 24 h)
    storage.upload(
        "documents/orphan-new",
        io.BytesIO(b"new"),
        content_type="application/pdf",
    )

    # Old tracked — should survive (in DB)
    storage.upload(
        "documents/tracked-old",
        io.BytesIO(b"tracked"),
        content_type="application/pdf",
    )
    _age_file(storage._path("documents/tracked-old"), 90000)

    with (
        patch("util.cleanup.advisory_lock", _mock_advisory_lock()),
        patch(
            "api.dependencies.storage.get_storage_manager",
            return_value=storage,
        ),
        patch(
            "api.dependencies.database.SessionFactory",
            return_value=_mock_db_context(["documents/tracked-old"]),
        ),
    ):
        from util.cleanup import _cleanup_orphaned_files

        removed = await _cleanup_orphaned_files()

    assert removed == 1
    assert not storage.exists("documents/orphan-old")
    assert storage.exists("documents/orphan-new")
    assert storage.exists("documents/tracked-old")


async def test_lock_not_acquired_returns_zero() -> None:
    """When the advisory lock is held by another worker, return 0."""
    with patch(
        "util.cleanup.advisory_lock",
        _mock_advisory_lock(acquired=False),
    ):
        from util.cleanup import _cleanup_orphaned_files

        removed = await _cleanup_orphaned_files()

    assert removed == 0
