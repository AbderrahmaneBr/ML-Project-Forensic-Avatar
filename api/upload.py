import uuid

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Image, Case, ImageStatus
from app.services.storage_service import upload_file
from app.schemas.schemas import UploadResponse, ImageResponse

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    case_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """Upload a forensic image to a case."""
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

    # Validate case exists
    case_uuid = uuid.UUID(case_id)
    case = db.query(Case).filter(Case.id == case_uuid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Generate unique object name
    filename = file.filename or "image.jpg"
    file_ext = filename.split(".")[-1] if "." in filename else "jpg"
    object_name = f"{case_id}/{uuid.uuid4()}.{file_ext}"

    # Upload to MinIO
    content_type = file.content_type or "image/jpeg"
    storage_url = upload_file(content, object_name, content_type)

    # Save to database
    image = Image(
        case_id=case_uuid,
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
