import pytesseract
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import re
import os

# Ensure Tesseract knows where tessdata is located
TESSDATA_PATH = os.path.expanduser("~/usr/share/tessdata")

pytesseract.pytesseract.tesseract_cmd = "/data/data/com.termux/files/usr/bin/tesseract"
os.environ["TESSDATA_PREFIX"] = TESSDATA_PATH


def preprocess(img: Image.Image) -> Image.Image:
    """
    Enhance image for Kingshot BT screenshots.
    """
    # Convert to grayscale
    img = img.convert("L")

    # Auto-contrast
    img = ImageOps.autocontrast(img)

    # Slight sharpen
    img = img.filter(ImageFilter.SHARPEN)

    # Increase brightness and contrast slightly
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = ImageEnhance.Brightness(img).enhance(1.2)

    return img


def auto_fix_rotation(img: Image.Image) -> Image.Image:
    """
    If text is sideways / upside down, auto-correct it.
    """
    try:
        osd = pytesseract.image_to_osd(img)
        angle = int(re.search(r"Rotate: (\d+)", osd).group(1))
        if angle != 0:
            return img.rotate(-angle, expand=True)
    except Exception:
        pass
    return img


def extract_numbers(text: str):
    """
    Extract key numeric values for BT like damage, points, ranking.
    """
    numbers = re.findall(r"\d[\d,\.]*", text)
    return [n.replace(",", "") for n in numbers]


def clean_text(text: str) -> str:
    """
    Remove garbage, duplicates, excessive whitespace.
    """
    lines = text.splitlines()
    cleaned = []

    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if all(c in "-_=*" for c in ln):
            continue
        cleaned.append(ln)

    return "\n".join(cleaned)


def ocr_image(path: str) -> dict:
    """
    Main OCR flow:
    - Apply pre-processing
    - Chinese+English OCR
    - Extract numbers
    - Return structured payload for Qwen
    """
    img = Image.open(path)

    img = auto_fix_rotation(img)
    img = preprocess(img)

    raw = pytesseract.image_to_string(
        img,
        lang="chi_sim+eng",
        config="--psm 6"
    )

    cleaned = clean_text(raw)
    nums = extract_numbers(cleaned)

    return {
        "raw_text": raw,
        "clean_text": cleaned,
        "numbers": nums
    }
