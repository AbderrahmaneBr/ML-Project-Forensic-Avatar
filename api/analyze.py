from fastapi import APIRouter

from app.schemas.schemas import AnalyzeRequest, AnalysisResult

router = APIRouter()


@router.post("/", response_model=AnalysisResult | None)
async def analyze_image(request: AnalyzeRequest):
    """Run full analysis pipeline on an image."""
    return None
