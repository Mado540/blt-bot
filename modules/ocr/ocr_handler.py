import io
import discord
from PIL import Image

from modules.ocr.google_ocr_rest import google_ocr_image
from modules.ocr.postprocess import postprocess_ocr
from modules.ocr.format_blt_summary import format_blt_summary


# ----------------------------------------------------
# Process 1–6 uploaded images using Google OCR (REST)
# ----------------------------------------------------
async def process_uploaded_images(attachments):
    all_raw = []

    for att in attachments:
        # Read file bytes
        img_bytes = await att.read()

        # Send raw bytes to Google OCR REST API
        text = google_ocr_image(img_bytes)

        # -----------------------------
        # Optional debug print
        # -----------------------------
        print("\n===== RAW OCR BLOCK =====")
        print(text)
        print("===== END OCR BLOCK =====\n")

        # Append OCR result in required structure
        all_raw.append({"text": text})

    # Postprocess
    players, total = postprocess_ocr(all_raw)

    # Format the BLT-style summary
    summary = format_blt_summary(players, total)

    return summary


def format_summary(text):
    return text
