"""S3-compatible upload/download helpers for control-plane artifact assembly."""

from __future__ import annotations

from pathlib import Path
import hashlib

import boto3

from .config import settings


def s3_client():
    kwargs = {
        "aws_access_key_id": settings.r2_access_key_id,
        "aws_secret_access_key": settings.r2_secret_access_key,
    }
    if settings.r2_endpoint:
        kwargs["endpoint_url"] = settings.r2_endpoint
    return boto3.client("s3", **kwargs)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_storage_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Unsupported storage uri: {uri}")
    bucket_and_key = uri[len("s3://") :]
    bucket, key = bucket_and_key.split("/", 1)
    return bucket, key


def upload_file(path: Path, key: str) -> str:
    client = s3_client()
    client.upload_file(str(path), settings.r2_bucket, key)
    return f"s3://{settings.r2_bucket}/{key}"


def download_file(uri: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    bucket, key = split_storage_uri(uri)
    s3_client().download_file(bucket, key, str(destination))
    return destination
