from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class OCRRequest(BaseModel):
    image_url: str

@router.post("/")
def ocr_endpoint(req: OCRRequest):
    # Minimal placeholder
    return {
        "message": "OCR endpoint placeholder",
        "image_url": req.image_url,
        "texts": []
    }
