from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import case, upload, detect, ocr, nlp, analyze, analyze_stream, jobs
from app.db.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="AI Forensic Avatar", lifespan=lifespan)

app.include_router(case.router, prefix="/api/v1/cases", tags=["Cases"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(detect.router, prefix="/api/v1/detect", tags=["Detection"])
app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["OCR"])
app.include_router(nlp.router, prefix="/api/v1/nlp", tags=["Hypotheses"])
app.include_router(analyze.router, prefix="/api/v1/analyze", tags=["Analysis"])
app.include_router(analyze_stream.router, prefix="/api/v1/analyze", tags=["Analysis Stream"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])