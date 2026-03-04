"""drop document secret column, migrate storage keys

Revision ID: bad1ae560489
Revises: 5492a960cd49
Create Date: 2026-03-04 00:54:13.601396

Schema changes:
  - Drop the unused ``Document.secret`` column.

Data migration:
  - Rename existing storage keys from the old flat format
    (``document-{uuid}.pdf``) to the new subdirectory format
    (``documents/{group_id}/{uuid}``).
  - Move the corresponding files on disk into group-specific
    subdirectories and strip the ``.pdf`` extension.
  - Create ``.meta`` JSON sidecar files so the download endpoint
    can read the content type from storage metadata.
"""

import json
import os
import re
import shutil
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bad1ae560489"
down_revision: Union[str, None] = "5492a960cd49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Matches the old key format: document-<uuid>.pdf
_OLD_KEY_RE = re.compile(
    r"^document-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}"
    r"-[0-9a-f]{4}-[0-9a-f]{12})\.pdf$"
)

# Matches the new key format: documents/<group_id>/<uuid>
_NEW_KEY_RE = re.compile(r"^documents/(\d+)/(.+)$")


def _get_storage_dir() -> str:
    """Resolve STORAGE_DIR the same way the app does."""
    backend_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    is_test = os.getenv("TESTING", "").lower() == "true"
    if is_test:
        return os.path.join(backend_path, "storage-test")
    return os.getenv(
        "STORAGE_DIR", os.path.join(backend_path, "storage")
    )


def _migrate_files_forward(storage_dir: str, rows: list) -> None:
    """Move files from flat layout to documents/{group_id}/ subdirs.

    Each ``(old_key, new_key)`` pair is processed independently.
    Files that are already at the new location (e.g. re-running
    after a partial failure) are silently skipped.
    """
    for old_key, new_key in rows:
        old_path = os.path.join(storage_dir, old_key)
        new_path = os.path.join(storage_dir, *new_key.split("/"))

        # Ensure the group subdirectory exists
        os.makedirs(os.path.dirname(new_path), exist_ok=True)

        # Move the file
        if os.path.isfile(old_path):
            shutil.move(old_path, new_path)

            # Move existing .meta sidecar if present
            old_meta = old_path + ".meta"
            new_meta = new_path + ".meta"
            if os.path.isfile(old_meta):
                shutil.move(old_meta, new_meta)

        # Create .meta sidecar if missing (old files never had one)
        meta_path = new_path + ".meta"
        if os.path.isfile(new_path) and not os.path.isfile(
            meta_path
        ):
            with open(meta_path, "w") as f:
                json.dump({"content_type": "application/pdf"}, f)


def _migrate_files_backward(
    storage_dir: str, rows: list
) -> None:
    """Move files from documents/{group_id}/ subdirs back to flat."""
    seen_group_dirs: set[str] = set()

    for new_key, old_key in rows:
        new_path = os.path.join(storage_dir, *new_key.split("/"))
        old_path = os.path.join(storage_dir, old_key)
        group_dir = os.path.dirname(new_path)
        seen_group_dirs.add(group_dir)

        if os.path.isfile(new_path):
            shutil.move(new_path, old_path)

            # Move .meta sidecar back
            new_meta = new_path + ".meta"
            old_meta = old_path + ".meta"
            if os.path.isfile(new_meta):
                shutil.move(new_meta, old_meta)

    # Clean up empty group and documents/ subdirectories
    for group_dir in seen_group_dirs:
        if os.path.isdir(group_dir) and not os.listdir(
            group_dir
        ):
            os.rmdir(group_dir)
    docs_subdir = os.path.join(storage_dir, "documents")
    if os.path.isdir(docs_subdir) and not os.listdir(
        docs_subdir
    ):
        os.rmdir(docs_subdir)


def upgrade() -> None:
    """Drop secret column and migrate storage keys."""
    # -- Schema change --
    with op.batch_alter_table("document", schema=None) as batch_op:
        batch_op.drop_column("secret")

    # -- Data migration: rename storage keys --
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT id, group_id, storage_key FROM document"
        )
    )
    updates: list[tuple[str, str]] = []  # (old_key, new_key)
    for row in result:
        doc_id, group_id, old_key = row[0], row[1], row[2]
        m = _OLD_KEY_RE.match(old_key)
        if not m:
            # Already in new format or unrecognised — skip
            continue
        uuid_part = m.group(1)
        new_key = f"documents/{group_id}/{uuid_part}"
        conn.execute(
            sa.text(
                "UPDATE document SET storage_key = :new_key "
                "WHERE id = :id"
            ),
            {"new_key": new_key, "id": doc_id},
        )
        updates.append((old_key, new_key))

    # -- File migration --
    storage_dir = _get_storage_dir()
    if os.path.isdir(storage_dir) and updates:
        _migrate_files_forward(storage_dir, updates)


def downgrade() -> None:
    """Restore secret column and revert storage keys."""
    # -- Schema change --
    with op.batch_alter_table("document", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "secret",
                sa.UUID(),
                autoincrement=False,
                nullable=True,
            )
        )

    # -- Data migration: revert storage keys --
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id, storage_key FROM document")
    )
    reverts: list[tuple[str, str]] = []  # (new_key, old_key)
    for row in result:
        doc_id, new_key = row[0], row[1]
        m = _NEW_KEY_RE.match(new_key)
        if not m:
            continue
        uuid_part = m.group(2)
        old_key = f"document-{uuid_part}.pdf"
        conn.execute(
            sa.text(
                "UPDATE document SET storage_key = :old_key "
                "WHERE id = :id"
            ),
            {"old_key": old_key, "id": doc_id},
        )
        reverts.append((new_key, old_key))

    # -- File migration --
    storage_dir = _get_storage_dir()
    if os.path.isdir(storage_dir) and reverts:
        _migrate_files_backward(storage_dir, reverts)
