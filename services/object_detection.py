from io import BytesIO

import requests
from PIL import Image
from ultralytics import YOLO

model = YOLO("yolov8n.pt")


def detect_objects(image_url: str) -> list[dict]:
    """
    Run YOLOv8 object detection on an image.
    Returns list of detected objects with labels, confidence, and bounding boxes.
    """
    response = requests.get(image_url)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))

    results = model(image)

    detected_objects = []
    for result in results:
        for box in result.boxes:
            detected_objects.append({
                "label": model.names[int(box.cls[0])],
                "confidence": float(box.conf[0]),
                "bbox": {
                    "x": float(box.xyxy[0][0]),
                    "y": float(box.xyxy[0][1]),
                    "width": float(box.xyxy[0][2] - box.xyxy[0][0]),
                    "height": float(box.xyxy[0][3] - box.xyxy[0][1]),
                }
            })

    return detected_objects
