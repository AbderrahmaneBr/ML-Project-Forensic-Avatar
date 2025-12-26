from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import upload, detect, ocr, nlp
from db.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="AI Forensic Avatar", lifespan=lifespan)

app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(detect.router, prefix="/api/v1/detect", tags=["Detection"])
app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["OCR"])
app.include_router(nlp.router, prefix="/api/v1/nlp", tags=["Hypotheses"])