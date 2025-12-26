from minio import Minio
from app.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

BUCKET_NAME = "forensic-images"
if not client.bucket_exists(BUCKET_NAME):
    client.make_bucket(BUCKET_NAME)

def upload_image(file_path: str, object_name: str) -> str:
    client.fput_object(BUCKET_NAME, object_name, file_path)
    return f"http://{MINIO_ENDPOINT}/{BUCKET_NAME}/{object_name}"
