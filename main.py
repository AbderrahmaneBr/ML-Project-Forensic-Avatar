from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api import conversation, upload, detect, ocr, analyze, chat, jobs
from backend.db.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="AI Forensic Avatar", lifespan=lifespan)

app.include_router(conversation.router, prefix="/api/v1/conversations", tags=["Conversations"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(detect.router, prefix="/api/v1/detect", tags=["Detection"])
app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["OCR"])
app.include_router(analyze.router, prefix="/api/v1/analyze", tags=["Analysis"])
app.include_router(chat.router, prefix="/api/v1/conversations", tags=["Chat"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
