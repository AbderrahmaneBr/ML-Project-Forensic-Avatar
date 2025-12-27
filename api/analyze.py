"""Analysis API endpoint for running detection and OCR on conversation images."""
import json
from collections.abc import Generator
from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from backend.db.database import get_db, SessionLocal
from backend.db.models import Conversation, Image, DetectedObject, ExtractedText, Message, MessageRole, ImageStatus
from backend.services.object_detection import detect_objects
from backend.services.ocr_service import extract_text
from backend.services.nlp_service import generate_hypothesis, generate_hypotheses_stream
from backend.services.storage_service import get_presigned_url
from backend.schemas.schemas import (
    AnalyzeRequest,
    AnalysisResult,
    ImageAnalysisResult,
    DetectedObjectResponse,
    ExtractedTextResponse,
    BoundingBox,
)

router = APIRouter()


@router.post("/", response_model=AnalysisResult)
def analyze_conversation(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Run full analysis pipeline on all images in a conversation.

    Pipeline steps:
    1. Object Detection (YOLOv8) - for each image
    2. OCR Text Extraction (Tesseract) - for each image
    3. NLP Hypothesis Generation (Ollama) - combined analysis of all evidence

    The hypothesis is saved as an assistant message in the conversation.
    """
    # Validate conversation exists
    conversation = db.query(Conversation).filter(Conversation.id == request.conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get all images in the conversation
    images = db.query(Image).filter(Image.conversation_id == request.conversation_id).all()
    if not images:
        raise HTTPException(status_code=400, detail="No images in conversation")

    # Collect all evidence across images
    all_objects_data: list[dict] = []
    all_texts_data: list[dict] = []
    image_results: list[ImageAnalysisResult] = []

    for image in images:
        image_id = cast(UUID, image.id)
        object_name = cast(str, image.storage_url)
        presigned_url = get_presigned_url(object_name)

        # Update status to processing
        image.status = ImageStatus.PROCESSING  # type: ignore[assignment]
        db.commit()

        # Step 1: Object Detection
        detected = detect_objects(presigned_url)
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
            all_objects_data.append({
                "label": obj["label"],
                "confidence": obj["confidence"]
            })

        # Step 2: OCR Text Extraction
        extracted = extract_text(presigned_url)
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
            all_texts_data.append({
                "text": item["text"],
                "confidence": item["confidence"]
            })

        # Update status to completed for this image
        image.status = ImageStatus.COMPLETED  # type: ignore[assignment]
        db.commit()

        # Refresh objects to get IDs
        for db_obj in db_objects:
            db.refresh(db_obj)
        for db_text in db_texts:
            db.refresh(db_text)

        # Build response for this image
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

        image_results.append(ImageAnalysisResult(
            image_id=image_id,
            detected_objects=response_objects,
            extracted_texts=response_texts,
        ))

    # Step 3: NLP Hypothesis Generation (combined analysis)
    generated = generate_hypothesis(all_objects_data, all_texts_data, request.context)

    # Save hypothesis as assistant message in the conversation
    assistant_msg = Message(
        conversation_id=request.conversation_id,
        role=MessageRole.ASSISTANT,
        content=generated["content"]
    )
    db.add(assistant_msg)
    db.commit()

    return AnalysisResult(
        status="completed",
        images=image_results,
        hypothesis=generated["content"]
    )


def analyze_stream_generator(conversation_id: UUID, context: str | None) -> Generator[dict, None, None]:
    """Generator that yields SSE events for the analysis pipeline."""
    db = SessionLocal()

    try:
        # Validate conversation exists
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            yield {"event": "error", "data": json.dumps({"error": "Conversation not found"})}
            return

        # Get all images in the conversation
        images = db.query(Image).filter(Image.conversation_id == conversation_id).all()
        if not images:
            yield {"event": "error", "data": json.dumps({"error": "No images in conversation"})}
            return

        yield {"event": "start", "data": json.dumps({"status": "starting", "total_images": len(images)})}

        all_objects_data: list[dict] = []
        all_texts_data: list[dict] = []
        total_images = len(images)

        for idx, image in enumerate(images, 1):
            image_id = cast(UUID, image.id)
            object_name = cast(str, image.storage_url)
            presigned_url = get_presigned_url(object_name)

            # Update status to processing
            image.status = ImageStatus.PROCESSING  # type: ignore[assignment]
            db.commit()

            # Step 1: Object Detection
            yield {
                "event": "progress",
                "data": json.dumps({
                    "step": "detection",
                    "image": idx,
                    "total_images": total_images
                })
            }

            detected = detect_objects(presigned_url)
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
                all_objects_data.append({
                    "label": obj["label"],
                    "confidence": obj["confidence"]
                })

            # Step 2: OCR Text Extraction
            yield {
                "event": "progress",
                "data": json.dumps({
                    "step": "ocr",
                    "image": idx,
                    "total_images": total_images
                })
            }

            extracted = extract_text(presigned_url)
            for item in extracted:
                db_text = ExtractedText(
                    image_id=image_id,
                    text=item["text"],
                    confidence=item["confidence"],
                    position_x=item["position_x"],
                    position_y=item["position_y"],
                )
                db.add(db_text)
                all_texts_data.append({
                    "text": item["text"],
                    "confidence": item["confidence"]
                })

            # Update status to completed for this image
            image.status = ImageStatus.COMPLETED  # type: ignore[assignment]
            db.commit()

        # Step 3: NLP Hypothesis Generation with streaming
        yield {
            "event": "progress",
            "data": json.dumps({"step": "nlp"})
        }

        full_hypothesis = ""
        for token in generate_hypotheses_stream(all_objects_data, all_texts_data, context):
            full_hypothesis += token
            yield {
                "event": "text",
                "data": json.dumps({"text": token})
            }

        # Save hypothesis as assistant message
        assistant_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=full_hypothesis.strip()
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        yield {
            "event": "complete",
            "data": json.dumps({
                "message_id": str(assistant_msg.id),
                "hypothesis": full_hypothesis.strip()
            })
        }

    except Exception as e:
        yield {"event": "error", "data": json.dumps({"error": str(e)})}
    finally:
        db.close()


@router.post("/stream")
def analyze_stream(request: AnalyzeRequest):
    """
    Stream the analysis pipeline progress using Server-Sent Events.

    Events:
    - start: Analysis started, includes total_images
    - progress: Current step (detection, ocr, nlp) and image number
    - text: LLM token for hypothesis generation
    - complete: Analysis finished, includes message_id and full hypothesis
    - error: An error occurred
    """
    return EventSourceResponse(
        analyze_stream_generator(request.conversation_id, request.context),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
