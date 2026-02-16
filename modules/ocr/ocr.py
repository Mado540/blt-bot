# modules/ocr/ocr.py
import pytesseract
from PIL import Image, ImageOps, ImageFilter
import io
import re

# ----------------------------------------
# IMAGE PREPROCESSING
# ----------------------------------------
def preprocess_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))

    # Convert to grayscale
    img = ImageOps.grayscale(img)

    # Auto contrast (boost text visibility)
    img = ImageOps.autocontrast(img)

    # Reduce noise
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # Sharpen text
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    # Convert to black/white threshold
    img = img.point(lambda p: 255 if p > 160 else 0)

    return img


# ----------------------------------------
# OCR RUNNER
# ----------------------------------------
def run_ocr(image_bytes):
    """Perform OCR on image."""
    img = preprocess_image(image_bytes)

    text = pytesseract.image_to_string(
        img, lang='chi_sim+eng'
        config="--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz:/.-"
    )

    return text


# ----------------------------------------
# MULTI-IMAGE AGGREGATOR
# ----------------------------------------
def aggregate_results(results):
    """
    results = [(filename, text), ...]
    """
    summary = {
        "players": [],
        "total_damage": 0,
        "notes": []
    }

    # Pattern for damage numbers like: 1,234,567
    damage_pattern = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)")

    for filename, text in results:

        # Detect TOTAL line
        total_match = re.search(r"Total Damage[:\s]+(\d[\d,\.]*)", text, re.IGNORECASE)
        if total_match:
            try:
                summary["total_damage"] += int(total_match.group(1).replace(",", ""))
            except:
                pass

        # Parse player rows
        for line in text.split("\n"):
            nums = damage_pattern.findall(line)
            if not nums:
                continue

            dmg_str = nums[-1]
            dmg_val = int(dmg_str.replace(",", ""))

            # Extract name
            name = None
            parts = line.split()
            for p in parts:
                if not re.match(r"^[\d,\.]+$", p):
                    name = p
                    break

            if name:
                summary["players"].append({
                    "name": name,
                    "damage": dmg_val,
                    "rank": len(summary["players"]) + 1
                })

        if "Total" not in text:
            summary["notes"].append(f"{filename}: no TOTAL detected")

    # sort by damage
    summary["players"] = sorted(summary["players"], key=lambda x: x["damage"], reverse=True)

    return summary
