from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Case
from app.schemas.schemas import CaseCreate, CaseResponse, CaseWithImagesResponse

router = APIRouter()


@router.post("/", response_model=CaseResponse)
def create_case(case: CaseCreate, db: Session = Depends(get_db)):
    """Create a new forensic case."""
    db_case = Case(name=case.name, description=case.description)
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: UUID, db: Session = Depends(get_db)):
    """Get a case by ID."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.get("/", response_model=list[CaseWithImagesResponse])
def get_cases(db: Session = Depends(get_db)):
    """Get all cases with their linked images."""
    return db.query(Case).all()

