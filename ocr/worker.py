# ========================================================
# RAW OCR WORKER — v10.2-A
# Reads images from ocr/inbox → Outputs raw text to ocr/raw
# ========================================================

import os
import time
import pytesseract
from PIL import Image
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))

INBOX      = os.path.join(BASE, "inbox")
RAW_OUT    = os.path.join(BASE, "raw")
LOG_DIR    = os.path.join(BASE, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE   = os.path.join(LOG_DIR, "worker_raw.log")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

def process_image(path):
    """Convert image → raw text file."""
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="eng+chi_sim")

        out_name = os.path.basename(path) + ".txt"
        out_path = os.path.join(RAW_OUT, out_name)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)

        log(f"[RAW] Extracted → {out_path}")

    except Exception as e:
        log("[RAW ERROR] " + str(e))
        log(traceback.format_exc())

def main():
    log("=== RAW OCR WORKER STARTED ===")

    while True:
        files = os.listdir(INBOX)

        for f in files:
            fp = os.path.join(INBOX, f)

            if os.path.isfile(fp):
                log(f"[RAW] Processing {fp}")
                process_image(fp)

                os.remove(fp)
                log(f"[RAW] Deleted input → {fp}")

        time.sleep(1)

if __name__ == "__main__":
    main()
