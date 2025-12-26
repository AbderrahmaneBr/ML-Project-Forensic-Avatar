from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field


# ============== Case Schemas ==============

class CaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class CaseResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============== Image Schemas ==============

class ImageResponse(BaseModel):
    id: UUID
    case_id: UUID
    filename: str
    storage_url: str
    content_type: Optional[str]
    file_size: Optional[int]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True, "use_enum_values": True}


class UploadResponse(BaseModel):
    message: str
    image: ImageResponse


class CaseWithImagesResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    images: list[ImageResponse]

    model_config = {"from_attributes": True}


# ============== Detection Schemas ==============

class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class DetectedObjectResponse(BaseModel):
    id: UUID
    label: str
    confidence: float
    bbox: Optional[BoundingBox] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DetectRequest(BaseModel):
    image_id: UUID


class DetectResponse(BaseModel):
    image_id: UUID
    objects: list[DetectedObjectResponse]


# ============== OCR Schemas ==============

class ExtractedTextResponse(BaseModel):
    id: UUID
    text: str
    confidence: Optional[float]
    position_x: Optional[float]
    position_y: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class OCRRequest(BaseModel):
    image_id: UUID


class OCRResponse(BaseModel):
    image_id: UUID
    texts: list[ExtractedTextResponse]


# ============== NLP/Hypothesis Schemas ==============

class HypothesisResponse(BaseModel):
    id: UUID
    content: str
    confidence: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class NLPRequest(BaseModel):
    image_id: UUID


class NLPResponse(BaseModel):
    image_id: UUID
    hypotheses: list[HypothesisResponse]


# ============== Full Analysis Schemas ==============

class AnalyzeRequest(BaseModel):
    image_id: UUID


class AnalysisResult(BaseModel):
    image_id: UUID
    status: str
    detected_objects: list[DetectedObjectResponse]
    extracted_texts: list[ExtractedTextResponse]
    hypotheses: list[HypothesisResponse]


# ============== Error Schemas ==============

class ErrorResponse(BaseModel):
    detail: str
