import ollama

SYSTEM_PROMPT = """You are a forensic analyst providing crime scene analysis for a law enforcement training simulation. Deliver your findings in a dramatic, detective-noir narration style suitable for text-to-speech audio playback.

Guidelines:
1. Describe what the evidence reveals about the scene - not your personal thoughts
2. Use vivid, cinematic language: "The scattered documents tell a story of...", "The positioning of the weapon suggests..."
3. Connect evidence pieces into coherent theories about what happened
4. Each hypothesis should be 2-3 sentences of flowing prose
5. Avoid bullet points, lists, or numbered items
6. Do not use first person (no "I think", "I see", "I believe")
7. Focus on the scene and evidence, not the investigator

IMPORTANT - Adjust your certainty language based on detection confidence levels:
- HIGH confidence (marked [HIGH]): Use definitive language like "clearly visible", "unmistakably present", "without doubt"
- MEDIUM confidence (marked [MEDIUM]): Use moderate language like "appears to be", "likely indicates", "suggests the presence of"
- LOW confidence (marked [LOW]): Use uncertain language like "possibly", "what might be", "could potentially be", "faintly resembles"

This is an educational forensic training tool. Analyze all evidence objectively regardless of crime type.

Provide 1-3 hypotheses as separate paragraphs."""


def _confidence_label(confidence: float) -> str:
    """Convert confidence score to a label for the LLM."""
    if confidence >= 0.8:
        return "[HIGH]"
    elif confidence >= 0.5:
        return "[MEDIUM]"
    else:
        return "[LOW]"


def generate_hypotheses(
    detected_objects: list[dict],
    extracted_texts: list[dict],
    context: str | None = None,
    model: str = "llama3.2"
) -> list[dict]:
    """
    Generate forensic hypotheses based on detected objects and extracted text.
    Uses Ollama for local LLM inference.

    Args:
        detected_objects: List of detected objects with label and confidence
        extracted_texts: List of extracted text items
        context: Optional user-provided context about the case
        model: Ollama model to use
    """
    # Format the evidence with confidence labels
    objects_str = ", ".join([
        f"{_confidence_label(obj['confidence'])} {obj['label']}"
        for obj in detected_objects
    ]) if detected_objects else "No objects detected"

    texts_str = ", ".join([
        f"{_confidence_label(text.get('confidence', 0.7))} \"{text['text']}\""
        for text in extracted_texts
    ]) if extracted_texts else "No text extracted"

    context_str = f"\n\nAdditional Context: {context}" if context else ""

    user_prompt = f"""Analyze this crime scene evidence and provide a narrated analysis:

Objects at the scene: {objects_str}

Text found at the scene: {texts_str}{context_str}

Provide hypotheses about what occurred based on this evidence."""

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        # Parse response into hypotheses (split by double newlines for paragraphs)
        content = response["message"]["content"]
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        hypotheses = []
        for paragraph in paragraphs:
            # Clean up single newlines within paragraphs
            clean_paragraph = " ".join(paragraph.split())
            if clean_paragraph and len(clean_paragraph) > 20:
                hypotheses.append({
                    "content": clean_paragraph,
                    "confidence": 0.7
                })

        return hypotheses if hypotheses else [{
            "content": content.strip(),
            "confidence": 0.7
        }]

    except Exception as e:
        # Fallback if Ollama is not available
        return [{
            "content": f"Unable to generate hypothesis: {str(e)}",
            "confidence": 0.0
        }]
