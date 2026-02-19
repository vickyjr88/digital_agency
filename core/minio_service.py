# MinIO Storage Service for Digital Products
# Endpoint: minio.vitaldigitalmedia.net

import boto3
import os
import uuid
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import Optional
from datetime import datetime

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "https://minio.vitaldigitalmedia.net")
# Public endpoint is what the browser will reach.
# In Docker dev the backend uses http://minio:9000 internally but the browser
# must use http://localhost:19000, so set MINIO_PUBLIC_ENDPOINT accordingly.
# In production both are the same (https://minio.vitaldigitalmedia.net).
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", MINIO_ENDPOINT)
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "dexter-digital-products")
MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")
# Presigned URL expiry (seconds) - 24 hours default
DOWNLOAD_URL_EXPIRY = int(os.getenv("MINIO_DOWNLOAD_URL_EXPIRY", "86400"))


def _get_client():
    """Internal client — uses MINIO_ENDPOINT (Docker-internal address ok)."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name=MINIO_REGION,
    )


def _get_public_client():
    """
    Client used only for generating presigned URLs.
    Uses MINIO_PUBLIC_ENDPOINT so the signed URLs contain the hostname the
    browser can actually reach (e.g. localhost:19000 in dev, the public
    domain in production).
    """
    return boto3.client(
        "s3",
        endpoint_url=MINIO_PUBLIC_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name=MINIO_REGION,
    )


def ensure_bucket_exists():
    """Create the bucket if it doesn't already exist."""
    client = _get_client()
    try:
        client.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=MINIO_BUCKET)
            print(f"✅ MinIO bucket '{MINIO_BUCKET}' created.")
        else:
            raise


def upload_digital_product(
    file_bytes: bytes,
    original_filename: str,
    content_type: str,
    product_id: str,
) -> dict:
    """
    Upload a digital product file (e.g. PDF) to MinIO.

    Returns a dict with:
      - object_key: the key stored in MinIO
      - file_size: bytes
      - file_name: original filename
      - content_type: MIME type
    """
    ensure_bucket_exists()
    client = _get_client()

    # Sanitise filename and build a unique key
    safe_name = original_filename.replace(" ", "_")
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    object_key = f"digital-products/{product_id}/{timestamp}-{unique_id}-{safe_name}"

    client.put_object(
        Bucket=MINIO_BUCKET,
        Key=object_key,
        Body=file_bytes,
        ContentType=content_type,
        ContentDisposition=f'attachment; filename="{original_filename}"',
    )

    return {
        "object_key": object_key,
        "file_size": len(file_bytes),
        "file_name": original_filename,
        "content_type": content_type,
    }


def generate_download_url(object_key: str, expiry_seconds: int = DOWNLOAD_URL_EXPIRY) -> str:
    """
    Generate a presigned download URL for a digital product file.

    The URL is time-limited (default 24 h) so buyers cannot share permanent links.
    Uses MINIO_PUBLIC_ENDPOINT so the URL is reachable from the browser.
    """
    client = _get_public_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": MINIO_BUCKET, "Key": object_key},
        ExpiresIn=expiry_seconds,
    )
    return url


def delete_digital_product(object_key: str) -> bool:
    """Delete a file from MinIO (called when a product is archived/deleted)."""
    client = _get_client()
    try:
        client.delete_object(Bucket=MINIO_BUCKET, Key=object_key)
        return True
    except ClientError:
        return False


def upload_product_image(
    file_bytes: bytes,
    original_filename: str,
    content_type: str,
    product_id: str,
) -> dict:
    """
    Upload a product image (JPEG, PNG, WebP, GIF) to MinIO.
    Returns a dict with object_key and a 7-day presigned URL for display.
    """
    ensure_bucket_exists()
    client = _get_client()

    safe_name = original_filename.replace(" ", "_")
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    object_key = f"product-images/{product_id}/{timestamp}-{unique_id}-{safe_name}"

    client.put_object(
        Bucket=MINIO_BUCKET,
        Key=object_key,
        Body=file_bytes,
        ContentType=content_type,
    )

    # 7-day presigned URL — long enough for display, refresh on product edit.
    # Must use the public client so the URL hostname is browser-reachable.
    url = _get_public_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": MINIO_BUCKET, "Key": object_key},
        ExpiresIn=60 * 60 * 24 * 7,
    )
    return {
        "object_key": object_key,
        "url": url,
        "file_name": original_filename,
        "file_size": len(file_bytes),
        "content_type": content_type,
    }


def delete_product_image(object_key: str) -> bool:
    """Delete a product image from MinIO."""
    client = _get_client()
    try:
        client.delete_object(Bucket=MINIO_BUCKET, Key=object_key)
        return True
    except ClientError:
        return False


def get_object_metadata(object_key: str) -> Optional[dict]:
    """Return metadata for an existing object, or None if not found."""
    client = _get_client()
    try:
        resp = client.head_object(Bucket=MINIO_BUCKET, Key=object_key)
        return {
            "content_type": resp.get("ContentType"),
            "content_length": resp.get("ContentLength"),
            "last_modified": resp.get("LastModified"),
        }
    except ClientError:
        return None
