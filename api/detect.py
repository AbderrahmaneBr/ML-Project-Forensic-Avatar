from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class DetectRequest(BaseModel):
    image_url: str

@router.post("/")
def detect_endpoint(req: DetectRequest):
    # Minimal placeholder
    return {
        "message": "Detect endpoint placeholder",
        "image_url": req.image_url,
        "objects": []
    }
