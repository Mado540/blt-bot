# ============================================================
# AI INTERPRETER — v10.2-A
# Reads raw OCR text → Cleans → Extracts numbers → Saves results
# ============================================================

import os
import time
import re
from datetime import datetime
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))

RAW_DIR      = os.path.join(BASE, "raw")
PARSED_DIR   = os.path.join(BASE, "processed")
RESULT_DIR   = os.path.join(BASE, "results")
LOG_DIR      = os.path.join(BASE, "logs")
os.makedirs(PARSED_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE     = os.path.join(LOG_DIR, "worker_ai.log")
BT_HISTORY   = os.path.join(RESULT_DIR, "BT_history.txt")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

# ------------------------------------------------------------
# Extract name + damage lines from OCR text
# ------------------------------------------------------------
def parse_text(raw_text):
    entries = []

    # Generic formats:
    #   Name — 485,000,000
    #   Damage Points: 485,000,000
    #   FictionAddict
    #       Damage Points: 467,388,307
    #
    #   Name    467,388,307
    #
    pattern = re.compile(
        r"([A-Za-z0-9·\u4e00-\u9fff\-_ ]{2,})[^\d]{0,20}([\d,]{3,})"
    )

    for match in pattern.finditer(raw_text):
        name = match.group(1).strip()
        dmg = match.group(2).replace(",", "")
        try:
            dmg_val = int(dmg)
            entries.append((name, dmg_val))
        except:
            continue

    # Sort highest first
    entries.sort(key=lambda x: x[1], reverse=True)
    return entries

def format_entries(entries):
    out = ["Top Damage:"]
    rank = 1

    for name, dmg in entries:
        out.append(f"{rank}) {name} — {dmg:,}")
        rank += 1
        if rank > 20:   # safety limit
            break

    return "\n".join(out)

def main():
    log("=== AI INTERPRETER STARTED ===")

    while True:
        files = [f for f in os.listdir(RAW_DIR) if f.endswith(".txt")]

        for f in files:
            path = os.path.join(RAW_DIR, f)

            try:
                raw = open(path, "r", encoding="utf-8").read()

                entries = parse_text(raw)
                formatted = format_entries(entries)

                # Save parsed file
                parsed_path = os.path.join(PARSED_DIR, f)
                with open(parsed_path, "w", encoding="utf-8") as p:
                    p.write(formatted)

                # Append to BT history
                with open(BT_HISTORY, "a", encoding="utf-8") as h:
                    h.write("\n=== OCR BT Result ===\n")
                    h.write(formatted + "\n")
                    h.write(f"(Saved {datetime.now()})\n\n")

                log(f"[AI] Parsed → {parsed_path}")

                os.remove(path)
                log(f"[AI] Deleted raw → {path}")

            except Exception as e:
                log("[AI ERROR] " + str(e))
                log(traceback.format_exc())

        time.sleep(1)

if __name__ == "__main__":
    main()
