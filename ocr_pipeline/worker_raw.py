import os
import time
import pytesseract
from PIL import Image
import io
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))
INCOMING = os.path.join(BASE, "incoming")
RAW = os.path.join(BASE, "raw")
LOG = os.path.join(BASE, "logs", "worker_raw.log")

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

def process_image(path):
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="eng+chi_sim")

        out_path = os.path.join(RAW, os.path.basename(path) + ".txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)

        log(f"[RAW] Extracted → {out_path}")

    except Exception as e:
        log("[RAW] ERROR: " + str(e))
        log(traceback.format_exc())

def main():
    log("=== RAW WORKER STARTED ===")

    while True:
        files = os.listdir(INCOMING)
        for f in files:
            fp = os.path.join(INCOMING, f)

            if os.path.isfile(fp):
                log(f"[RAW] Processing {fp}")
                process_image(fp)
                os.remove(fp)

        time.sleep(1)


if __name__ == "__main__":
    main()
