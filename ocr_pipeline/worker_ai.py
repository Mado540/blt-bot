import os
import json
import time
import aiohttp
import asyncio
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
OUT = os.path.join(BASE, "processed")
LOG = os.path.join(BASE, "logs", "worker_ai.log")

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

async def ask_qwen(text):
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "prompt": (
                    "Extract Bear Trap results from raw OCR text.\n"
                    "Return ONLY JSON with keys:\n"
                    "{ 'rallies': int, 'total_damage': int, 'players': [ {'name': str, 'damage': int} ] }\n\n"
                    f"RAW TEXT:\n{text}"
                ),
                "n_predict": 300,
                "temperature": 0.2
            }

            async with session.post("http://127.0.0.1:8080/completion", json=payload) as r:
                data = await r.json()
                return data.get("content", "")

    except Exception as e:
        return "ERROR: " + str(e)

async def process_file(path):
    try:
        raw = open(path, "r", encoding="utf-8").read()

        log(f"[AI] Sending OCR text to Qwen → {path}")
        out = await ask_qwen(raw)

        out_path = os.path.join(OUT, os.path.basename(path))
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out)

        log(f"[AI] Saved parsed output → {out_path}")

    except Exception as e:
        log("[AI] ERROR: " + str(e))
        log(traceback.format_exc())

async def loop_main():
    log("=== AI INTERPRETER STARTED ===")

    while True:
        files = [f for f in os.listdir(RAW) if f.endswith(".txt")]
        for f in files:
            fp = os.path.join(RAW, f)
            await process_file(fp)
            os.remove(fp)

        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(loop_main())
