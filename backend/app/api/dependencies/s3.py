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

app_logger = get_logger("app")


class S3Manager:
    """S3 manager for handling S3 operations as a dependency."""

    def __init__(self) -> None:
        """Initialize the S3Manager with a boto3 client."""
        self.enabled = all([AWS_ACCESS_KEY, AWS_SECRET_KEY, S3_BUCKET])
        if not self.enabled:
            app_logger.warning("⚠️ S3 is not fully configured. S3 operations are disabled.")
            return
            
        self._client = boto3.client(
            "s3",
            endpoint_url=AWS_ENDPOINT_URL,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            config=Config(signature_version="s3v4"),
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

    def delete(self, key: str) -> bool:
        """Delete an object from S3."""
        try:
            self._client.delete_object(Bucket=S3_BUCKET, Key=key)
            return True
        except ClientError:
            return False

    def upload(self, key: str, data: BinaryIO, content_type: str) -> None:
        """Upload an object to S3."""
        self._client.put_object(Bucket=S3_BUCKET, Key=key, Body=data, ContentType=content_type)

    def download(self, key: str) -> Any:  # noqa: ANN401 # this trash library is so poorly typed I cba to find the right type
        """Download an object from S3."""
        response = self._client.get_object(Bucket=S3_BUCKET, Key=key)
        return response["Body"]


manager = S3Manager()
S3 = Annotated[S3Manager, Depends(lambda: manager)]
