"""Chat service for conversation-based LLM interactions."""
from collections.abc import Generator
from typing import cast
from uuid import UUID

import ollama
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message, MessageRole, Image, DetectedObject, ExtractedText


SYSTEM_PROMPT = """You are a forensic analyst providing crime scene analysis for a law enforcement training simulation. Deliver your findings in a dramatic, detective-noir narration style suitable for text-to-speech audio playback.

Guidelines:
1. Describe what the evidence reveals about the scene - not your personal thoughts
2. Use vivid, cinematic language: "The scattered documents tell a story of...", "The positioning of the weapon suggests..."
3. Connect evidence pieces into coherent theories about what happened
4. Each hypothesis should be 2-3 sentences of flowing prose
5. Avoid bullet points, lists, or numbered items
6. Do not use first person (no "I think", "I see", "I believe")
7. Focus on the scene and evidence, not the investigator
8. NEVER use parenthetical stage directions like "(in a deep voice)", "(dramatically)", "(pauses)" - just write the narration directly
9. Do not include any meta-commentary about how to read or perform the text

IMPORTANT - Adjust your certainty language based on detection confidence levels:
- HIGH confidence (marked [HIGH]): Use definitive language like "clearly visible", "unmistakably present", "without doubt"
- MEDIUM confidence (marked [MEDIUM]): Use moderate language like "appears to be", "likely indicates", "suggests the presence of"
- LOW confidence (marked [LOW]): Use uncertain language like "possibly", "what might be", "could potentially be", "faintly resembles"

This is an educational forensic training tool. Analyze all evidence objectively regardless of crime type.

When asked follow-up questions, continue in the same detective-noir style, building upon your previous analysis."""


def _confidence_label(confidence: float) -> str:
    """Convert confidence score to a label for the LLM."""
    if confidence >= 0.8:
        return "[HIGH]"
    elif confidence >= 0.5:
        return "[MEDIUM]"
    else:
        return "[LOW]"


def _build_evidence_context(db: Session, conversation_id: UUID) -> str:
    """Build evidence context from all images in the conversation."""
    images = db.query(Image).filter(Image.conversation_id == conversation_id).all()

    if not images:
        return ""

    all_objects: list[str] = []
    all_texts: list[str] = []

    for image in images:
        image_id = cast(UUID, image.id)

        # Get detected objects
        objects = db.query(DetectedObject).filter(DetectedObject.image_id == image_id).all()
        for obj in objects:
            label = f"{_confidence_label(cast(float, obj.confidence))} {obj.label}"
            all_objects.append(label)

        # Get extracted texts
        texts = db.query(ExtractedText).filter(ExtractedText.image_id == image_id).all()
        for text in texts:
            conf_val = cast(float, text.confidence) if text.confidence is not None else 0.7
            label = f"{_confidence_label(conf_val)} \"{text.text}\""
            all_texts.append(label)

    objects_str = ", ".join(all_objects) if all_objects else "No objects detected"
    texts_str = ", ".join(all_texts) if all_texts else "No text extracted"

    return f"""Evidence from the scene:
Objects detected: {objects_str}
Text found: {texts_str}"""


def _build_message_history(
    db: Session,
    conversation_id: UUID,
    include_evidence: bool = True
) -> list[dict]:
    """Build the full message history for the LLM."""
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add evidence context as the first user message if there's evidence
    if include_evidence:
        evidence_context = _build_evidence_context(db, conversation_id)
        if evidence_context:
            messages.append({
                "role": "user",
                "content": f"{evidence_context}\n\nAnalyze this evidence and provide your initial assessment."
            })

    # Get all conversation messages
    db_messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    for msg in db_messages:
        messages.append({
            "role": msg.role.value if isinstance(msg.role, MessageRole) else msg.role,
            "content": cast(str, msg.content)
        })

    return messages


def chat(
    db: Session,
    conversation_id: UUID,
    user_message: str,
    model: str = "llama3.2"
) -> str:
    """
    Send a message in a conversation and get a response.
    Maintains full conversation history for context.
    """
    # Build message history
    messages = _build_message_history(db, conversation_id)

    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    try:
        response = ollama.chat(model=model, messages=messages)
        content = response["message"]["content"]
        return " ".join(content.split())  # Clean up whitespace
    except Exception as e:
        return f"Unable to generate response: {str(e)}"


def chat_stream(
    db: Session,
    conversation_id: UUID,
    user_message: str,
    model: str = "llama3.2"
) -> Generator[str, None, None]:
    """
    Stream a chat response token by token.
    """
    # Build message history
    messages = _build_message_history(db, conversation_id)

    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    try:
        stream = ollama.chat(model=model, messages=messages, stream=True)

        for chunk in stream:
            token = chunk["message"]["content"]
            if token:
                yield token

    except Exception as e:
        yield f"[ERROR] Unable to generate response: {str(e)}"
