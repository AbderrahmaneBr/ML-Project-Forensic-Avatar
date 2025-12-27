# from backend.services.object_detection import detect_objects
# from backend.services.ocr_service import extract_text
# from backend.services.nlp_service import generate_hypotheses
# from backend.db.crud import save_detection, save_ocr, save_hypotheses

# def analyze_image(image_path: str, case_id: int):
#     objects = detect_objects(image_path)
#     save_detection(case_id, objects)

#     texts = extract_text(image_path)
#     save_ocr(case_id, texts)

#     hypotheses = generate_hypotheses(objects, texts)
#     save_hypotheses(case_id, hypotheses)

#     return {
#         "objects": objects,
#         "texts": texts,
#         "hypotheses": hypotheses
#     }
