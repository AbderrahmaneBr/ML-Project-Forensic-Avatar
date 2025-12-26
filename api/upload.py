from fastapi import APIRouter, UploadFile, File

router = APIRouter()

@router.post("/")
async def upload_image(file: UploadFile = File(...), case_id: int = 0):
    # Minimal placeholder
    return {
        "message": "Upload endpoint placeholder",
        "filename": file.filename,
        "case_id": case_id
    }
