from io import BytesIO

import cv2
import numpy as np
import pytesseract
import requests
from PIL import Image


def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocess image for better OCR accuracy."""
    # Convert to OpenCV format
    img_array = np.array(image)

    # Convert to grayscale if needed
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    # Apply thresholding to get binary image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)

    return Image.fromarray(denoised)


def extract_text(image_url: str) -> list[dict]:
    """
    Run OCR on an image and extract text with position data.
    Returns list of extracted text blocks with confidence and position.
    """
    # Fetch image
    response = requests.get(image_url)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))

    # Preprocess for better OCR
    processed = preprocess_image(image)

    # Run OCR with detailed output
    data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)

    extracted_texts = []
    n_boxes = len(data['text'])

    for i in range(n_boxes):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])

        # Skip empty text or low confidence results
        if not text or conf < 30:
            continue

        extracted_texts.append({
            "text": text,
            "confidence": conf / 100.0,
            "position_x": float(data['left'][i]),
            "position_y": float(data['top'][i]),
        })

    return extracted_texts
