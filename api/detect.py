from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Image, DetectedObject, ImageStatus
from backend.services.object_detection import detect_objects
from backend.services.storage_service import get_presigned_url
from backend.schemas.schemas import DetectRequest, DetectResponse, DetectedObjectResponse, BoundingBox

router = APIRouter()


@router.post("/", response_model=DetectResponse)
def detect_endpoint(req: DetectRequest, db: Session = Depends(get_db)):
    """Run object detection on an image."""
    # Get image from database
    image = db.query(Image).filter(Image.id == req.image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Run detection
    object_name = cast(str, image.storage_url)
    image_id = cast(UUID, image.id)
    presigned_url = get_presigned_url(object_name)
    detected = detect_objects(presigned_url)

    # Save results to database
    db_objects: list[DetectedObject] = []
    for obj in detected:
        db_obj = DetectedObject(
            image_id=image_id,
            label=obj["label"],
            confidence=obj["confidence"],
            bbox_x=obj["bbox"]["x"],
            bbox_y=obj["bbox"]["y"],
            bbox_width=obj["bbox"]["width"],
            bbox_height=obj["bbox"]["height"],
        )
        db.add(db_obj)
        db_objects.append(db_obj)

    # Update image status
    image.status = ImageStatus.PROCESSING  # type: ignore[assignment]
    db.commit()

    # Refresh to get IDs
    for db_obj in db_objects:
        db.refresh(db_obj)

    # Build response
    response_objects = [
        DetectedObjectResponse(
            id=cast(UUID, obj.id),
            label=cast(str, obj.label),
            confidence=cast(float, obj.confidence),
            bbox=BoundingBox(
                x=cast(float, obj.bbox_x),
                y=cast(float, obj.bbox_y),
                width=cast(float, obj.bbox_width),
                height=cast(float, obj.bbox_height)
            ),
            created_at=cast(datetime, obj.created_at)
        )
        for obj in db_objects
    ]

    return DetectResponse(image_id=image_id, objects=response_objects)
