import base64
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_OCR_KEY")

VISION_URL = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"

def google_ocr_image(image_bytes: bytes) -> str:
    """Use Google Vision API (REST) to OCR an image without google-cloud-vision package."""
    if not API_KEY:
        return ""

    img_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "requests": [
            {
                "image": {"content": img_b64},
                "features": [{"type": "TEXT_DETECTION"}]
            }
        ]
    }

    resp = requests.post(VISION_URL, json=payload)
    data = resp.json()

    try:
        return data["responses"][0]["fullTextAnnotation"]["text"]
    except KeyError:
        return ""
