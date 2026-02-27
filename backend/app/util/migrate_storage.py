"""One-time migration utility: copy files from S3 to local storage.

This module is only used when ``MIGRATE_FROM_S3=true``.  After a
successful migration the env var should be removed and this file
can be deleted in a follow-up commit.
"""

import json
import os

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from core.config import (
    AWS_ACCESS_KEY,
    AWS_ENDPOINT_URL,
    AWS_REGION,
    AWS_SECRET_KEY,
    S3_BUCKET,
    STORAGE_DIR,
)
from core.logger import get_logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

migrate_logger = get_logger("storage")


def _download_one(s3: boto3.client, key: str, local_path: str) -> None:  # type: ignore[type-arg]
    """Download a single object from S3 and write it with a .meta sidecar."""
    response = s3.get_object(Bucket=S3_BUCKET, Key=key)
    body = response["Body"]
    content_type = response.get(
        "ContentType", "application/octet-stream"
    )

    # Atomic write via temp file + rename
    tmp_path = local_path + ".tmp"
    with open(tmp_path, "wb") as f:
        while True:
            chunk = body.read(8192)
            if not chunk:
                break
            f.write(chunk)
    os.rename(tmp_path, local_path)

    # Write .meta sidecar atomically
    meta_path = local_path + ".meta"
    meta_tmp = meta_path + ".tmp"
    with open(meta_tmp, "w") as mf:
        json.dump({"content_type": content_type}, mf)
    os.rename(meta_tmp, meta_path)


async def migrate_from_s3(engine: AsyncEngine) -> None:
    """Download every document from S3 into ``STORAGE_DIR``.

    Skips files that already exist locally (idempotent).
    Logs progress so operators can monitor long migrations.
    """
    migrate_logger.info(
        "Starting S3 -> local storage migration "
        "(bucket=%s, dir=%s)",
        S3_BUCKET,
        STORAGE_DIR,
    )

    # Build a temporary S3 client from legacy env vars
    if not all(
        [AWS_ACCESS_KEY, AWS_SECRET_KEY, S3_BUCKET, AWS_ENDPOINT_URL]
    ):
        raise RuntimeError(
            "MIGRATE_FROM_S3 is enabled but the legacy AWS_*"
            " / S3_BUCKET env vars are not all set."
        )

    s3 = boto3.client(
        "s3",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION or "auto",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        config=Config(
            signature_version="s3v4",
            connect_timeout=10,
            read_timeout=60,
        ),
    )

    os.makedirs(STORAGE_DIR, exist_ok=True)

    # Fetch all storage keys from the database
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT storage_key FROM document")
        )
        keys: list[str] = [row[0] for row in result.fetchall()]

    total = len(keys)
    skipped = 0
    migrated = 0
    failed = 0

    for i, key in enumerate(keys, 1):
        safe_key = os.path.basename(key)
        local_path = os.path.join(STORAGE_DIR, safe_key)

        # Idempotent: skip only if both file and .meta exist
        if os.path.isfile(local_path) and os.path.isfile(
            local_path + ".meta"
        ):
            skipped += 1
            continue

        try:
            _download_one(s3, key, local_path)
            migrated += 1
            if migrated % 10 == 0 or i == total:
                migrate_logger.info(
                    "Migration progress: %d/%d "
                    "(migrated=%d, skipped=%d, failed=%d)",
                    i,
                    total,
                    migrated,
                    skipped,
                    failed,
                )
        except ClientError as e:
            failed += 1
            migrate_logger.error(
                "Failed to migrate %s from S3: %s", key, e
            )
        except OSError as e:
            failed += 1
            migrate_logger.error(
                "Failed to write %s to disk: %s", key, e
            )
            # Clean up partial temp file
            tmp = local_path + ".tmp"
            if os.path.exists(tmp):
                os.remove(tmp)

    migrate_logger.info(
        "S3 migration complete: %d migrated, %d skipped, "
        "%d failed out of %d total",
        migrated,
        skipped,
        failed,
        total,
    )
    if failed > 0:
        migrate_logger.warning(
            "%d files failed to migrate. Re-run with "
            "MIGRATE_FROM_S3=true to retry.",
            failed,
        )
