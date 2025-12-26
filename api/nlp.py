from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Image, DetectedObject, ExtractedText, Hypothesis, ImageStatus
from app.services.nlp_service import generate_hypotheses
from app.schemas.schemas import NLPRequest, NLPResponse, HypothesisResponse

router = APIRouter()


@router.post("/", response_model=NLPResponse)
def nlp_endpoint(req: NLPRequest, db: Session = Depends(get_db)):
    """Generate forensic hypotheses based on detected objects and extracted text."""
    # Get image from database
    image = db.query(Image).filter(Image.id == req.image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    image_id = cast(UUID, image.id)

    # Get detected objects for this image
    detected_objects = db.query(DetectedObject).filter(
        DetectedObject.image_id == image_id
    ).all()

    # Get extracted texts for this image
    extracted_texts = db.query(ExtractedText).filter(
        ExtractedText.image_id == image_id
    ).all()

    # Format data for NLP service
    objects_data = [
        {"label": cast(str, obj.label), "confidence": cast(float, obj.confidence)}
        for obj in detected_objects
    ]
    texts_data = [
        {"text": cast(str, text.text)}
        for text in extracted_texts
    ]

    # Generate hypotheses
    generated = generate_hypotheses(objects_data, texts_data)

    # Save results to database
    db_hypotheses: list[Hypothesis] = []
    for hyp in generated:
        db_hyp = Hypothesis(
            image_id=image_id,
            content=hyp["content"],
            confidence=hyp["confidence"],
        )
        db.add(db_hyp)
        db_hypotheses.append(db_hyp)

    # Update image status to completed
    image.status = ImageStatus.COMPLETED  # type: ignore[assignment]
    db.commit()

    # Refresh to get IDs
    for db_hyp in db_hypotheses:
        db.refresh(db_hyp)

    # Build response
    response_hypotheses = [
        HypothesisResponse(
            id=cast(UUID, h.id),
            content=cast(str, h.content),
            confidence=cast(float | None, h.confidence),
            created_at=cast(datetime, h.created_at)
        )
        for h in db_hypotheses
    ]

    return NLPResponse(image_id=image_id, hypotheses=response_hypotheses)
