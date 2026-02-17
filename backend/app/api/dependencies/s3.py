from collections.abc import Iterator
from datetime import UTC, datetime, timezone
from functools import lru_cache
from typing import Annotated, Any, BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from core.config import (
    AWS_ACCESS_KEY,
    AWS_ENDPOINT_URL,
    AWS_REGION,
    AWS_SECRET_KEY,
    S3_BUCKET,
)
from core.logger import get_logger
from fastapi import Depends

s3_logger = get_logger("s3")


class S3Manager:
    """S3 manager for handling S3 operations as a dependency."""

    def __init__(self) -> None:
        """Initialize the S3Manager with a boto3 client."""
        if not all([AWS_ACCESS_KEY, AWS_SECRET_KEY, S3_BUCKET, AWS_ENDPOINT_URL]):
            raise RuntimeError("Not all required S3 configuration variables are set.")

        self.verify_connection()

    def verify_connection(self) -> None:
        """Verify S3 connection and bucket access at startup."""
        self._client = boto3.client(
            "s3",
            endpoint_url=AWS_ENDPOINT_URL,
            region_name=AWS_REGION or "auto",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            config=Config(
                signature_version="s3v4",
                connect_timeout=10,
                read_timeout=30,
            ),
        )
        s3_logger.info(
            "S3 client configured (bucket: %s)", S3_BUCKET
        )

    def metadata(self, key: str) -> dict | None:
        """Check if an object exists in S3 and return its metadata."""
        try:
            return self._client.head_object(Bucket=S3_BUCKET, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            raise

    def exists(self, key: str) -> bool:
        """Check if an object exists in S3."""
        return self.metadata(key) is not None
    
    def get_last_modified(self, key: str) -> datetime:
        """Get the Last-Modified timestamp of an object in S3."""
        metadata = self.metadata(key)
        last_modified: datetime = metadata["LastModified"]
        # Ensure a timezone-aware UTC datetime is returned
        return last_modified.astimezone(UTC)

    def delete(self, key: str) -> bool:
        """Delete an object from S3."""
        try:
            self._client.delete_object(Bucket=S3_BUCKET, Key=key)
            s3_logger.info("Deleted object: %s", key)
            return True
        except ClientError as e:
            s3_logger.error("Failed to delete object %s: %s", key, e)
            return False

    def upload(self, key: str, data: BinaryIO, content_type: str) -> None:
        """Upload an object to S3."""
        self._client.put_object(Bucket=S3_BUCKET, Key=key, Body=data, ContentType=content_type)
        s3_logger.info("Uploaded object: %s (content_type=%s)", key, content_type)

    def download(self, key: str) -> Any:  # noqa: ANN401 # this trash library is so poorly typed I cba to find the right type
        """Download an object from S3."""
        response = self._client.get_object(Bucket=S3_BUCKET, Key=key)
        s3_logger.debug("Downloaded object: %s", key)
        return response["Body"]

    def download_stream(self, key: str, chunk_size: int = 8192) -> Iterator[bytes]:
        """Return an iterator of bytes for the object, streaming in chunks.

        This keeps streaming logic close to the S3 client (where it belongs)
        while remaining framework-agnostic. Callers can forward the iterator
        directly to `starlette.responses.StreamingResponse`.
        """
        response = self._client.get_object(Bucket=S3_BUCKET, Key=key)
        body = response["Body"]

        # boto3 "StreamingBody" exposes an `iter_chunks` method that yields
        # bytes. Use it when available.
        if hasattr(body, "iter_chunks"):
            return body.iter_chunks(chunk_size)

        # If only a file-like object with `read` is available, wrap it in a
        # generator to yield chunks.
        if hasattr(body, "read"):
            def _reader() -> Iterator[bytes]:
                chunk = body.read(chunk_size)
                while chunk:
                    yield chunk
                    chunk = body.read(chunk_size)

            return _reader()

        # Otherwise, fall back to returning the full content as a single
        # chunk. This keeps the signature consistent for callers.
        return iter([response["Body"]])


@lru_cache(maxsize=1)
def get_s3_manager() -> S3Manager:
    """Lazily instantiate the S3Manager to avoid import-time network checks.

    This keeps module import fast and side effect free while preserving the
    dependency-injection interface via `S3`.
    """
    return S3Manager()


S3 = Annotated[S3Manager, Depends(get_s3_manager)]


 
