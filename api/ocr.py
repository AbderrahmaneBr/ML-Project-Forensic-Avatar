from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Image, ExtractedText
from backend.services.ocr_service import extract_text
from backend.services.storage_service import get_presigned_url
from backend.schemas.schemas import OCRRequest, OCRResponse, ExtractedTextResponse

router = APIRouter()


@router.post("/", response_model=OCRResponse)
def ocr_endpoint(req: OCRRequest, db: Session = Depends(get_db)):
    """Run OCR on an image to extract text."""
    # Get image from database
    image = db.query(Image).filter(Image.id == req.image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Run OCR
    object_name = cast(str, image.storage_url)
    image_id = cast(UUID, image.id)
    presigned_url = get_presigned_url(object_name)
    extracted = extract_text(presigned_url)

    # Save results to database
    db_texts: list[ExtractedText] = []
    for item in extracted:
        db_text = ExtractedText(
            image_id=image_id,
            text=item["text"],
            confidence=item["confidence"],
            position_x=item["position_x"],
            position_y=item["position_y"],
        )
        db.add(db_text)
        db_texts.append(db_text)

    db.commit()

    # Refresh to get IDs
    for db_text in db_texts:
        db.refresh(db_text)

    # Build response
    response_texts = [
        ExtractedTextResponse(
            id=cast(UUID, t.id),
            text=cast(str, t.text),
            confidence=cast(float | None, t.confidence),
            position_x=cast(float | None, t.position_x),
            position_y=cast(float | None, t.position_y),
            created_at=cast(datetime, t.created_at)
        )
        for t in db_texts
    ]

    return OCRResponse(image_id=image_id, texts=response_texts)
