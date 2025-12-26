import ollama

SYSTEM_PROMPT = """You are a forensic analyst AI assistant. Based on the objects detected in an image and any text extracted from it, generate plausible forensic hypotheses about the scene.

Your hypotheses should:
1. Be based only on the evidence provided
2. Consider relationships between detected objects
3. Note any significant text that might be relevant
4. Suggest possible scenarios or events
5. Be professional and objective

Provide 1-3 concise hypotheses, each on a new line starting with "- "."""


def generate_hypotheses(
    detected_objects: list[dict],
    extracted_texts: list[dict],
    model: str = "llama3.2"
) -> list[dict]:
    """
    Generate forensic hypotheses based on detected objects and extracted text.
    Uses Ollama for local LLM inference.
    """
    # Format the evidence
    objects_str = ", ".join([
        f"{obj['label']} (confidence: {obj['confidence']:.0%})"
        for obj in detected_objects
    ]) if detected_objects else "No objects detected"

    texts_str = ", ".join([
        f'"{text["text"]}"'
        for text in extracted_texts
    ]) if extracted_texts else "No text extracted"

    user_prompt = f"""Analyze this forensic evidence:

Detected Objects: {objects_str}

Extracted Text: {texts_str}

Generate forensic hypotheses based on this evidence."""

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        # Parse response into hypotheses
        content = response["message"]["content"]
        hypotheses = []

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                hypotheses.append({
                    "content": line[2:].strip(),
                    "confidence": 0.7  # Default confidence for LLM hypotheses
                })
            elif line and not hypotheses:
                # If no bullet format, treat whole response as one hypothesis
                hypotheses.append({
                    "content": line,
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
