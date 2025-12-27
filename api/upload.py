import uuid
from typing import cast
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Image, Conversation, ImageStatus
from backend.services.storage_service import upload_file, delete_file
from backend.schemas.schemas import UploadResponse, ImageResponse

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    conversation_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """Upload a forensic image to a conversation."""
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_TYPES)}"
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )

    # Validate conversation exists
    conversation_uuid = uuid.UUID(conversation_id)
    conversation = db.query(Conversation).filter(Conversation.id == conversation_uuid).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Generate unique object name
    filename = file.filename or "image.jpg"
    file_ext = filename.split(".")[-1] if "." in filename else "jpg"
    object_name = f"{conversation_id}/{uuid.uuid4()}.{file_ext}"

    # Upload to MinIO
    content_type = file.content_type or "image/jpeg"
    storage_url = upload_file(content, object_name, content_type)

    # Save to database
    image = Image(
        conversation_id=conversation_uuid,
        filename=filename,
        storage_url=storage_url,
        content_type=content_type,
        file_size=len(content),
        status=ImageStatus.PENDING
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return UploadResponse(
        message="Image uploaded successfully",
        image=ImageResponse.model_validate(image)
    )


@router.delete("/{image_id}")
def delete_image(image_id: UUID, db: Session = Depends(get_db)):
    """Delete an image from the database and storage."""
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Delete from MinIO
    object_name = cast(str, image.storage_url)
    delete_file(object_name)

    # Delete from database (cascades to related objects)
    db.delete(image)
    db.commit()

    return {"message": "Image deleted successfully"}
