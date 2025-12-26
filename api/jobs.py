"""Background job API for async analysis."""
from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db, SessionLocal
from app.db.models import Image, DetectedObject, ExtractedText, Hypothesis, ImageStatus
from app.services.object_detection import detect_objects
from app.services.ocr_service import extract_text
from app.services.nlp_service import generate_hypothesis
from app.services.storage_service import get_presigned_url
from app.services.job_service import job_store, JobStatus, Job

router = APIRouter()


# Request/Response schemas
class JobRequest(BaseModel):
    image_ids: list[UUID] = Field(..., min_length=1)
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


def run_analysis_job(job_id: UUID, image_ids: list[UUID], context: str | None):
    """Background task that runs the full analysis pipeline."""
    db = SessionLocal()

    try:
        job_store.update_job(job_id, status=JobStatus.RUNNING, current_step="validating")

        # Validate images
        images: list[Image] = []
        for img_id in image_ids:
            image = db.query(Image).filter(Image.id == img_id).first()
            if not image:
                job_store.update_job(
                    job_id,
                    status=JobStatus.FAILED,
                    error=f"Image {img_id} not found"
                )
                return
            images.append(image)

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

        # Save hypothesis
        first_image_id = cast(UUID, images[0].id)
        db_hypothesis = Hypothesis(
            image_id=first_image_id,
            content=hypothesis_data["content"],
            confidence=hypothesis_data["confidence"]
        )
        db.add(db_hypothesis)
        db.commit()
        db.refresh(db_hypothesis)

        # Mark complete
        job_store.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            current_step="complete",
            result={
                "hypothesis_id": str(db_hypothesis.id),
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
    Create a background analysis job.

    Returns immediately with a job_id that can be polled for status.
    """
    # Validate images exist before starting job
    for image_id in request.image_ids:
        image = db.query(Image).filter(Image.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail=f"Image {image_id} not found")

    # Create job
    job = job_store.create_job()

    # Start background task
    background_tasks.add_task(
        run_analysis_job,
        job.id,
        request.image_ids,
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
