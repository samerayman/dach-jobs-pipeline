"""S3 (MinIO) resource. Thin boto3 wrapper for bronze writes."""

from __future__ import annotations

import os
from functools import cached_property

import boto3
from botocore.client import Config
from dagster import ConfigurableResource


class S3Resource(ConfigurableResource):
    endpoint_url: str = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    access_key: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
    secret_key: str = os.getenv("S3_SECRET_KEY", "minioadmin")
    region: str = os.getenv("S3_REGION", "us-east-1")

    @cached_property
    def client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(signature_version="s3v4"),
        )

    def put_bytes(self, bucket: str, key: str, body: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)
