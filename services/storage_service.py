from io import BytesIO

from minio import Minio

from app.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

BUCKET_NAME = "forensic-images"


def ensure_bucket_exists():
    if not client.bucket_exists(BUCKET_NAME):
        client.make_bucket(BUCKET_NAME)


def upload_file(data: bytes, object_name: str, content_type: str) -> str:
    """Upload file bytes to MinIO and return the URL."""
    ensure_bucket_exists()
    client.put_object(
        BUCKET_NAME,
        object_name,
        BytesIO(data),
        length=len(data),
        content_type=content_type
    )
    return f"http://{MINIO_ENDPOINT}/{BUCKET_NAME}/{object_name}"
