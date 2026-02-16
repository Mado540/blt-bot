#!/data/data/com.termux/files/usr/bin/bash
set -e

# ================================================
# BLT-bot Service Launcher — v3.4 CLEAN & CORRECT
# (bot.py already contains scheduler)
# ================================================

# Force the script to operate from blt_bot every time
BASE="/data/data/com.termux/files/home/blt_bot"
cd "$BASE" || { echo "ERROR: Cannot cd to $BASE"; exit 1; }

LOGDIR="$BASE/logs"
OCR="$BASE/ocr"
PY="/data/data/com.termux/files/usr/bin/python3"

mkdir -p "$LOGDIR"
mkdir -p "$OCR/incoming" "$OCR/raw" "$OCR/results"

QWEN_BIN="/data/data/com.termux/files/home/llama.cpp/build/bin/llama-server"
MODEL="/data/data/com.termux/files/home/models/Qwen2.5-3B-Instruct-Q4_K_M.gguf"

echo "=== Inside tmux: BLT-bot startup ==="
echo "Date: $(date)"
echo "----------------------------------------"

###################################################
# 0) CLEAN OLD PROCESSES
###################################################
echo "[0/5] Killing old processes..."
pkill -f llama-server 2>/dev/null || true
pkill -f api.py       2>/dev/null || true
pkill -f worker.py    2>/dev/null || true
pkill -f interpreter.py 2>/dev/null || true
pkill -f bot.py       2>/dev/null || true
echo "Old processes cleared."
sleep 1

###################################################
# 1) Qwen Server
###################################################
echo "[1/5] Starting Qwen..."
"$QWEN_BIN" \
  -m "$MODEL" \
  -c 8192 -t 6 \
  -ngl 12 \
  --parallel 2 --cont-batching --mlock --no-mmap \
  --port 8080 \
  >> "$LOGDIR/qwen.log" 2>&1 &
sleep 3
echo "Qwen started."

###################################################
# 2) Local API
###################################################
echo "[2/5] Starting Local API..."
$PY "$BASE/local_api/api.py" \
    >> "$LOGDIR/api.log" 2>&1 &
sleep 1
echo "API started."

###################################################
# 3) Raw OCR Worker
###################################################
echo "[3/5] Starting RAW OCR Worker..."
$PY "$OCR/worker.py" \
    >> "$LOGDIR/worker_raw.log" 2>&1 &
sleep 1
echo "RAW worker started."

###################################################
# 4) AI Interpreter
###################################################
echo "[4/5] Starting AI Interpreter..."
$PY "$OCR/interpreter.py" \
    >> "$LOGDIR/worker_ai.log" 2>&1 &
sleep 1
echo "Interpreter started."

###################################################
# 5) bot.py (SCHEDULER INCLUDED)
###################################################
echo "[5/5] Starting bot.py..."

(
    cd "$BASE" || exit 1
    env PYTHONUNBUFFERED=1 $PY bot.py >> "$LOGDIR/bot.log" 2>&1
) &

echo "bot.py started."

echo "----------------------------------------"
echo "All services running in background."
echo "Logs → $LOGDIR/"
echo "BLT-bot running inside tmux. Detach with Ctrl+B then D."

# Keep tmux pane alive
tail -f /dev/null
