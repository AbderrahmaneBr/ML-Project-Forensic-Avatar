"""Conversation API endpoints."""
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Conversation, Image, Message, MessageRole
from backend.schemas.schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationWithImagesResponse,
    ConversationDetailResponse,
    ImageResponse,
    MessageResponse,
)

router = APIRouter()


@router.post("/", response_model=ConversationResponse, status_code=201)
def create_conversation(request: ConversationCreate, db: Session = Depends(get_db)):
    """Create a new conversation."""
    conversation = Conversation(
        name=request.name,
        description=request.description,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/", response_model=list[ConversationWithImagesResponse])
def list_conversations(db: Session = Depends(get_db)):
    """List all conversations with their images."""
    conversations = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    return conversations


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    """Get a conversation with all images and messages."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    """Delete a conversation and all related data."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conversation)
    db.commit()
    return {"message": "Conversation deleted"}


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: UUID,
    request: ConversationCreate,
    db: Session = Depends(get_db)
):
    """Update a conversation's name or description."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.name = request.name  # type: ignore[assignment]
    if request.description is not None:
        conversation.description = request.description  # type: ignore[assignment]

    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(conversation_id: UUID, db: Session = Depends(get_db)):
    """Get all messages in a conversation."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    return messages
