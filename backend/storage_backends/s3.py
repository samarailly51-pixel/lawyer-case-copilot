from __future__ import annotations

import hashlib
import re
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from core.config import settings
from .base import StorageBackend, StoredObject


class S3StorageBackend(StorageBackend):
    def __init__(self):
        if not settings.s3_bucket:
            raise RuntimeError("STORAGE_BACKEND=s3 时必须配置 S3_BUCKET")
        self.client = boto3.client(
            "s3", endpoint_url=settings.s3_endpoint_url or None, region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id or None,
            aws_secret_access_key=settings.s3_secret_access_key or None,
        )
        try:
            self.client.head_bucket(Bucket=settings.s3_bucket)
        except ClientError:
            params = {"Bucket": settings.s3_bucket}
            if not settings.s3_endpoint_url and settings.s3_region not in {"", "auto", "us-east-1"}:
                params["CreateBucketConfiguration"] = {"LocationConstraint": settings.s3_region}
            self.client.create_bucket(**params)

    def put(self, case_id: str, filename: str, content: bytes) -> StoredObject:
        digest = hashlib.sha256(content).hexdigest()
        safe_name = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", Path(filename).name)
        key = f"cases/{case_id}/{digest[:12]}_{safe_name}"
        extra = {"ServerSideEncryption": "AES256"} if settings.encrypt_uploads else {}
        self.client.put_object(Bucket=settings.s3_bucket, Key=key, Body=content,
                               Metadata={"sha256": digest}, **extra)
        return StoredObject(key=key, uri=f"s3://{settings.s3_bucket}/{key}", sha256=digest,
                            encrypted=settings.encrypt_uploads)

    def get(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=settings.s3_bucket, Key=key)
        return response["Body"].read()
