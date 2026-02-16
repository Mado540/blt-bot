import os
import time
import subprocess
import json
from datetime import datetime

# Paths
BASE = os.path.dirname(os.path.abspath(__file__))
INCOMING = os.path.join(BASE, "ocr_inbox", "incoming")
TEXT_OUT = os.path.join(BASE, "ocr_inbox", "text")
PARSED = os.path.join(BASE, "ocr_inbox", "parsed")
RESULTS = os.path.join(BASE, "ocr_inbox", "results")
LOG = os.path.join(BASE, "logs", "ocr.log")

def log(msg):
    with open(LOG, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
    except Exception as e:
        return f"ERR: {e}"

def extract_text(image_path, out_txt):
    cmd = f"tesseract '{image_path}' '{out_txt.replace('.txt', '')}' --psm 6"
    log(f"Running OCR: {cmd}")
    run_cmd(cmd)

def run_qwen_ocr(prompt):
    payload = {
        "prompt": prompt,
        "n_predict": 256,
        "temperature": 0.1,
        "top_k": 20,
        "stop": ["</s>"]
    }
    try:
        import requests
        r = requests.post("http://127.0.0.1:8082/completion", json=payload)
        data = r.json()
        return (data.get("content") or "").strip()
    except:
        return "Error: Could not reach Qwen-OCR."

def interpret_bt(text):
    # On-demand Qwen: launch, process, shutdown
    log("Launching Qwen-OCR (llama-server)...")
    qwen_cmd = (
        "/data/data/com.termux/files/home/llama.cpp/build/bin/llama-server "
        "-m '/data/data/com.termux/files/home/models/Qwen2.5-3B-Instruct-Q4_K_M.gguf' "
        "-c 1024 -t 6 --port 8082 > /dev/null 2>&1 &"
    )
    run_cmd(qwen_cmd)
    time.sleep(4)

    prompt = (
        "You are a Kingshot BT-parser.\n"
        "Extract and interpret the following Bear Trap result text:\n\n"
        f"{text}\n\n"
        "Output JSON:\n"
        "{ 'players': [...], 'total_points': xxx, 'top5': [...], 'comment': 'short summary' }"
    )

    out = run_qwen_ocr(prompt)

    log("Shutting down Qwen-OCR...")
    run_cmd("pkill -f 'llama-server -m'")

    return out

def main_loop():
    log("OCR Worker Started (On-Demand Mode).")
    while True:
        files = os.listdir(INCOMING)
        for f in files:
            if not f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                continue

            path = os.path.join(INCOMING, f)
            txt_path = os.path.join(TEXT_OUT, f + ".txt")

            log(f"Processing image: {path}")

            extract_text(path, txt_path)

            text = ""
            if os.path.exists(txt_path):
                text = open(txt_path, "r", encoding="utf-8").read()

            parsed = interpret_bt(text)

            result_file = os.path.join(RESULTS, "latest_bt.json")
            with open(result_file, "w", encoding="utf-8") as rf:
                rf.write(parsed)

            log(f"Saved parsed BT result → {result_file}")

            os.rename(path, os.path.join(PARSED, f))

        time.sleep(2)

if __name__ == "__main__":
    main_loop()
