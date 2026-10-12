"""S3-compatible storage client (MinIO / AWS S3 / Cloudflare R2).

Provides internal object upload and presigned URL generation for clients.
"""

from collections.abc import Mapping
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from revenue_swarm.config import (
    STORAGE_ACCESS_KEY,
    STORAGE_BUCKET,
    STORAGE_ENDPOINT,
    STORAGE_PUBLIC_ENDPOINT,
    STORAGE_REGION,
    STORAGE_SECRET_KEY,
)


def _client(*, public: bool = False):
    """Return a boto3 S3 client. """
    endpoint = STORAGE_PUBLIC_ENDPOINT if public else STORAGE_ENDPOINT
    return boto3.client(
        "s3",
        endpoint_url=endpoint or None,
        aws_access_key_id=STORAGE_ACCESS_KEY,
        aws_secret_access_key=STORAGE_SECRET_KEY,
        region_name=STORAGE_REGION,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket_exists() -> None:
    """Ensure the target bucket exists, creating it if necessary."""
    client = _client(public=False)
    try:
        client.head_bucket(Bucket=STORAGE_BUCKET)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=STORAGE_BUCKET)
        else:
            raise


def put(
    key: str,
    body: bytes,
    content_type: str,
    metadata: Mapping[str, str] | None = None,
) -> None:
    """Upload an object to the bucket."""
    params: dict[str, Any] = {
        "Bucket": STORAGE_BUCKET,
        "Key": key,
        "Body": body,
        "ContentType": content_type,
    }
    if metadata:
        params["Metadata"] = dict(metadata)
    _client(public=False).put_object(**params)


def get(key: str) -> bytes:
    """Download an object from the bucket."""
    response = _client(public=False).get_object(Bucket=STORAGE_BUCKET, Key=key)
    return response["Body"].read()


def presigned_url(key: str, expires_in: int = 300) -> str:
    """Generate a presigned GET URL for public client download."""
    client = _client(public=True)
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": STORAGE_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
