#!/data/data/com.termux/files/usr/bin/bash
set -e

BASE="$HOME/blt_bot"
LOGDIR="$BASE/logs"
mkdir -p "$LOGDIR"

echo "=== Inside tmux: BLT-bot v10.2 ==="
echo "Date: $(date)"
echo "----------------------------------------"

echo "[1/5] Qwen..."
pkill -9 llama-server || true
$HOME/llama.cpp/build/bin/llama-server \
   -m $HOME/models/Qwen2.5-3B-Instruct-Q4_K_M.gguf \
   -c 2048 -t 6 --parallel 2 --cont-batching --mlock --no-mmap \
   --port 8080 >> "$LOGDIR/qwen.log" 2>&1 &
sleep 3
echo "Qwen started."

echo "[2/5] Local API..."
pkill -9 api.py || true
cd "$BASE/local_api"
python3 api.py >> "$LOGDIR/api.log" 2>&1 &
sleep 2
echo "API started."

echo "[3/5] RAW OCR..."
pkill -9 worker_raw.py || true
cd "$BASE/ocr_pipeline"
python3 worker_raw.py >> "$LOGDIR/worker_raw.log" 2>&1 &
sleep 1
echo "RAW OCR worker started."

echo "[4/5] AI INTERPRETER..."
pkill -9 worker_ai.py || true
python3 worker_ai.py >> "$LOGDIR/worker_ai.log" 2>&1 &
sleep 1
echo "AI interpreter started."

echo "[5/5] bot.py..."
pkill -9 bot.py || true
cd "$BASE"
python3 bot.py >> "$LOGDIR/bot.log" 2>&1 &
sleep 1
echo "bot.py started."

echo "----------------------------------------"
echo "All services running."

echo "----------------------------------------"
echo "All services running."
echo "BLT-bot services started. Keeping session alive..."

# Prevent tmux from exiting
while true
do
    sleep 600
done
