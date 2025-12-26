import asyncio
import json
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.db.database import get_db
from app.db.models import Image, DetectedObject, ExtractedText, Hypothesis, ImageStatus
from app.services.object_detection import detect_objects
from app.services.ocr_service import extract_text
from app.services.nlp_service import generate_hypotheses_stream
from app.services.storage_service import get_presigned_url
from app.schemas.schemas import AnalyzeRequest

router = APIRouter()
executor = ThreadPoolExecutor(max_workers=4)


async def run_in_thread(func, *args):
    """Run a sync function in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)


async def analysis_event_generator(
    request: AnalyzeRequest,
    db: Session
) -> AsyncGenerator[dict, None]:
    """Generate SSE events for the analysis pipeline."""
    images: list[Image] = []
    for image_id in request.image_ids:
        image = db.query(Image).filter(Image.id == image_id).first()
        if not image:
            yield {"event": "error", "data": json.dumps({"error": f"Image {image_id} not found"})}
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
        yield {"event": "progress", "data": json.dumps({"step": "detection", "status": "running", "image": idx, "total_images": total_images})}
        await asyncio.sleep(0)  # Allow event to flush

        detected = await run_in_thread(detect_objects, presigned_url)
        for obj in detected:
            db.add(DetectedObject(image_id=image_id, label=obj["label"], confidence=obj["confidence"],
                bbox_x=obj["bbox"]["x"], bbox_y=obj["bbox"]["y"], bbox_width=obj["bbox"]["width"], bbox_height=obj["bbox"]["height"]))
            all_objects_data.append({"label": obj["label"], "confidence": obj["confidence"]})

        yield {"event": "progress", "data": json.dumps({"step": "detection", "status": "complete", "image": idx, "objects_found": len(detected)})}
        await asyncio.sleep(0)

        # OCR
        yield {"event": "progress", "data": json.dumps({"step": "ocr", "status": "running", "image": idx})}
        await asyncio.sleep(0)

        extracted = await run_in_thread(extract_text, presigned_url)
        for item in extracted:
            db.add(ExtractedText(image_id=image_id, text=item["text"], confidence=item["confidence"],
                position_x=item["position_x"], position_y=item["position_y"]))
            all_texts_data.append({"text": item["text"], "confidence": item["confidence"]})

        yield {"event": "progress", "data": json.dumps({"step": "ocr", "status": "complete", "image": idx, "texts_found": len(extracted)})}
        await asyncio.sleep(0)

        image.status = ImageStatus.COMPLETED  # type: ignore[assignment]
        db.commit()

    # NLP Streaming
    yield {"event": "progress", "data": json.dumps({"step": "nlp", "status": "streaming"})}
    await asyncio.sleep(0)

    full_content = ""

    # Stream tokens from LLM using a queue
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def stream_to_queue():
        for token in generate_hypotheses_stream(all_objects_data, all_texts_data, request.context):
            queue.put_nowait(token)
        queue.put_nowait(None)  # Signal end

    # Start streaming in background thread
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, stream_to_queue)

    # Yield tokens as they arrive
    while True:
        try:
            token = await asyncio.wait_for(queue.get(), timeout=0.1)
            if token is None:
                break
            full_content += token
            yield {"event": "token", "data": json.dumps({"text": token})}
        except asyncio.TimeoutError:
            await asyncio.sleep(0.01)
            continue

    db_hypothesis = Hypothesis(image_id=cast(UUID, images[0].id), content=full_content.strip(), confidence=0.7)
    db.add(db_hypothesis)
    db.commit()
    db.refresh(db_hypothesis)

    yield {"event": "complete", "data": json.dumps({"status": "completed", "hypothesis_id": str(db_hypothesis.id)})}


@router.post("/stream")
async def analyze_stream(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """Stream analysis results using Server-Sent Events."""
    return EventSourceResponse(
        analysis_event_generator(request, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
