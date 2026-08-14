"""Cloudflare R2 (S3-compatible) access for the feedback admin app.

Reads/deletes objects by their FULL key as already stored in the `feedback`
table's `original_path` / `overlay_path` / `evidence_paths` columns (those
already include the "research-app/" prefix — written by
streamlit_app/storage.py::upload_image() / upload_file()). No PREFIX is
added here; this app never uploads, only reads and deletes.
"""

from functools import lru_cache

import streamlit as st


@lru_cache(maxsize=1)
def _client():
    r2 = st.secrets["r2"]
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=f"https://{r2['account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=r2["access_key_id"],
        aws_secret_access_key=r2["secret_access_key"],
        region_name="auto",
    )


def _bucket() -> str:
    return st.secrets["r2"]["bucket"]


def get_image_url(key: str, expires_in: int = 3600) -> str:
    """Pre-signed URL so st.image() can load the (private) object directly."""
    return _client().generate_presigned_url(
        "get_object", Params={"Bucket": _bucket(), "Key": key}, ExpiresIn=expires_in,
    )


def download_bytes(key: str) -> bytes:
    return _client().get_object(Bucket=_bucket(), Key=key)["Body"].read()


def delete_image(key: str) -> None:
    _client().delete_object(Bucket=_bucket(), Key=key)
