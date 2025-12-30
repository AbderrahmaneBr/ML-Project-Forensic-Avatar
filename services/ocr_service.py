"""OCR service using Tesseract for text extraction."""
import os
import httpx
import tempfile

import pytesseract
from PIL import Image


def extract_text(image_url: str) -> list[dict]:
    """
    Extract text from an image using Tesseract OCR.
    
    Args:
        image_url: URL or path to the image
    
    Returns:
        List of extracted text items with text, confidence, and position
    """
    # Download image if URL
    if image_url.startswith(('http://', 'https://')):
        with httpx.Client(timeout=30.0) as client:
            response = client.get(image_url)
            response.raise_for_status()
            image_data = response.content
            
            # Save temporarily
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(image_data)
                temp_path = f.name
            
            try:
                img = Image.open(temp_path)
                results = _extract_from_image(img)
            finally:
                os.unlink(temp_path)
    else:
        img = Image.open(image_url)
        results = _extract_from_image(img)
    
    return results


def _extract_from_image(img: Image.Image) -> list[dict]:
    """
    Extract text with detailed information from a PIL Image.
    
    Args:
        img: PIL Image object
    
    Returns:
        List of extracted text items
    """
    # Get detailed OCR data
    try:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    except Exception as e:
        print(f"Tesseract error: {e}")
        return []
    
    results = []
    n_boxes = len(data['text'])
    
    for i in range(n_boxes):
        text = data['text'][i].strip()
        conf = int(data['conf'][i]) if data['conf'][i] != -1 else 0
        
        # Skip empty text or very low confidence
        if not text or conf < 10:
            continue
        
        results.append({
            "text": text,
            "confidence": conf / 100.0,  # Normalize to 0-1
            "position_x": float(data['left'][i]),
            "position_y": float(data['top'][i]),
        })
    
    # Also get full text blocks (for better context)
    # Group adjacent words into lines/blocks
    if not results:
        # Fallback: try simple text extraction
        try:
            full_text = pytesseract.image_to_string(img).strip()
            if full_text:
                results.append({
                    "text": full_text,
                    "confidence": 0.7,
                    "position_x": 0.0,
                    "position_y": 0.0,
                })
        except Exception:
            pass
    
    return results
