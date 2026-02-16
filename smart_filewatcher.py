#!/usr/bin/env python3
import os
import time
import json
from datetime import datetime

# ===== ROOT DIRECTORY =====
ROOT = "/data/data/com.termux/files/home"

# ===== FILES TO MONITOR =====
FILES = {
    "bot.py": f"{ROOT}/blt_bot/bot.py",
    "run_services.sh": f"{ROOT}/blt_bot/run_services.sh",
    "run_all.sh": f"{ROOT}/run_all.sh"
}

# ===== OUTPUT FILES =====
LOG_FILE = f"{ROOT}/blt_bot/filechange_log.txt"
SNAPSHOT_FILE = f"{ROOT}/blt_bot/filesnapshot.json"
SCAN_INTERVAL = 4  # seconds

# Ensure the logging directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def load_snapshot():
    if not os.path.exists(SNAPSHOT_FILE):
        return {}
    try:
        return json.load(open(SNAPSHOT_FILE))
    except:
        return {}

def save_snapshot(data):
    json.dump(data, open(SNAPSHOT_FILE, "w"))

def human_log(msg):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{stamp}] {msg}\n")

def scan_targets():
    snap = {}
    for name, path in FILES.items():
        if os.path.exists(path):
            try:
                st = os.stat(path)
                snap[name] = {
                    "mtime": st.st_mtime,
                    "size": st.st_size
                }
            except:
                snap[name] = None
        else:
            snap[name] = None
    return snap

def describe_changes(old, new):
    out = []

    for name in FILES:
        old_meta = old.get(name)
        new_meta = new.get(name)

        # ===== NEW FILE =====
        if old_meta is None and new_meta is not None:
            out.append(
                f"🆕 {name} registered in the directory. "
                f"The system notes its arrival as a new active component."
            )
            continue

        # ===== REMOVED FILE =====
        if old_meta is not None and new_meta is None:
            out.append(
                f"❌ {name} is no longer present. "
                f"Entry removed from the active file set."
            )
            continue

        # If the file is still missing, skip further checks
        if new_meta is None:
            continue

        # ===== SIZE CHANGE =====
        if old_meta["size"] != new_meta["size"]:
            old_s = old_meta["size"]
            new_s = new_meta["size"]

            if new_s > old_s:
                out.append(
                    f"⬆️ {name} increased in size ({old_s} → {new_s} bytes). "
                    f"System records growth, likely due to recent additions."
                )
            else:
                out.append(
                    f"⬇️ {name} decreased in size ({old_s} → {new_s} bytes). "
                    f"System notes reduction, possibly from cleanup or refactoring."
                )

        # ===== MODIFIED TIMESTAMP ONLY =====
        elif old_meta["mtime"] != new_meta["mtime"]:
            out.append(
                f"🔧 {name} shows a modification timestamp change. "
                f"Content updated without altering file size."
            )

    return out

# ================= MAIN LOOP ================= #
def main():
    old = load_snapshot()
    human_log("👀 Smart file watcher activated (Termux). Monitoring bot.py + service scripts...")

    while True:
        new = scan_targets()
        changes = describe_changes(old, new)

        for text in changes:
            human_log(text)

        old = new
        save_snapshot(new)
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()
