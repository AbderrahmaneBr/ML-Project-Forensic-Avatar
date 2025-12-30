"""Background job API for async analysis."""
from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.database import get_db, SessionLocal
from backend.db.models import Conversation, Image, DetectedObject, ExtractedText, Message, MessageRole, ImageStatus
from backend.services.object_detection import detect_objects
from backend.services.ocr_service import extract_text
from backend.services.nlp_service import generate_hypothesis
from backend.services.storage_service import get_presigned_url
from backend.services.job_service import job_store, JobStatus

router = APIRouter()


# Request/Response schemas
class JobRequest(BaseModel):
    conversation_id: UUID
    context: str | None = Field(None, description="Additional context about the case")


class JobResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    current_step: str | None
    progress: dict
    created_at: datetime
    updated_at: datetime
    result: dict | None = None
    error: str | None = None


def run_analysis_job(job_id: UUID, conversation_id: UUID, context: str | None):
    """Background task that runs the full analysis pipeline."""
    db = SessionLocal()

    try:
        job_store.update_job(job_id, status=JobStatus.RUNNING, current_step="validating")

        # Validate conversation and get images
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            job_store.update_job(
                job_id,
                status=JobStatus.FAILED,
                error=f"Conversation {conversation_id} not found"
            )
            return

        images = db.query(Image).filter(Image.conversation_id == conversation_id).all()
        if not images:
            job_store.update_job(
                job_id,
                status=JobStatus.FAILED,
                error="No images in conversation"
            )
            return

        all_objects_data: list[dict] = []
        all_texts_data: list[dict] = []
        total_images = len(images)

        for idx, image in enumerate(images, 1):
            image_id = cast(UUID, image.id)
            presigned_url = get_presigned_url(cast(str, image.storage_url))

            image.status = ImageStatus.PROCESSING  # type: ignore[assignment]
            db.commit()

            # Detection
            job_store.update_job(
                job_id,
                current_step="detection",
                progress={"image": idx, "total_images": total_images, "step": "detection"}
            )

            detected = detect_objects(presigned_url)
            for obj in detected:
                db.add(DetectedObject(
                    image_id=image_id, label=obj["label"], confidence=obj["confidence"],
                    bbox_x=obj["bbox"]["x"], bbox_y=obj["bbox"]["y"],
                    bbox_width=obj["bbox"]["width"], bbox_height=obj["bbox"]["height"]
                ))
                all_objects_data.append({"label": obj["label"], "confidence": obj["confidence"]})

            # OCR
            job_store.update_job(
                job_id,
                current_step="ocr",
                progress={"image": idx, "total_images": total_images, "step": "ocr"}
            )

            extracted = extract_text(presigned_url)
            for item in extracted:
                db.add(ExtractedText(
                    image_id=image_id, text=item["text"], confidence=item["confidence"],
                    position_x=item["position_x"], position_y=item["position_y"]
                ))
                all_texts_data.append({"text": item["text"], "confidence": item["confidence"]})

            image.status = ImageStatus.COMPLETED  # type: ignore[assignment]
            db.commit()

        # NLP
        job_store.update_job(
            job_id,
            current_step="nlp",
            progress={"step": "nlp", "status": "generating hypothesis"}
        )

        hypothesis_data = generate_hypothesis(all_objects_data, all_texts_data, context)

        # Save hypothesis as assistant message
        assistant_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=hypothesis_data["content"]
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        # Mark complete
        job_store.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            current_step="complete",
            result={
                "message_id": str(assistant_msg.id),
                "hypothesis": hypothesis_data["content"],
                "objects_detected": len(all_objects_data),
                "texts_extracted": len(all_texts_data)
            }
        )

    except Exception as e:
        job_store.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=str(e)
        )
    finally:
        db.close()


@router.post("/", response_model=JobResponse)
def create_analysis_job(
    request: JobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a background analysis job for a conversation.

    Returns immediately with a job_id that can be polled for status.
    """
    # Validate conversation exists
    conversation = db.query(Conversation).filter(Conversation.id == request.conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check for images
    images = db.query(Image).filter(Image.conversation_id == request.conversation_id).all()
    if not images:
        raise HTTPException(status_code=400, detail="No images in conversation")

    # Create job
    job = job_store.create_job()

    # Start background task
    background_tasks.add_task(
        run_analysis_job,
        job.id,
        request.conversation_id,
        request.context
    )

    return JobResponse(
        job_id=job.id,
        status=job.status.value,
        message="Analysis job created. Poll /jobs/{job_id} for status."
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: UUID):
    """Get the status of an analysis job."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        current_step=job.current_step,
        progress=job.progress,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result=job.result,
        error=job.error
    )


@router.get("/", response_model=list[JobStatusResponse])
def list_jobs(limit: int = 20):
    """List recent analysis jobs."""
    jobs = job_store.list_jobs(limit=limit)
    return [
        JobStatusResponse(
            job_id=job.id,
            status=job.status.value,
            current_step=job.current_step,
            progress=job.progress,
            created_at=job.created_at,
            updated_at=job.updated_at,
            result=job.result,
            error=job.error
        )
        for job in jobs
    ]


@router.delete("/{job_id}")
def delete_job(job_id: UUID):
    """Delete a job from the store."""
    if job_store.delete_job(job_id):
        return {"message": "Job deleted"}
    raise HTTPException(status_code=404, detail="Job not found")
