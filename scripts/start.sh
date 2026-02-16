#!/data/data/com.termux/files/usr/bin/bash

# Start Qwen model
echo "Starting Qwen server..."
nohup llama-server -m ~/models/Qwen2.5-3B-Instruct-Q4_K_M.gguf -c 4096 --port 8080 > qwen.log 2>&1 &

sleep 3

# Start main BLT bot
echo "Starting BLT-bot..."
nohup python ~/blt_bot/bot.py > bot.log 2>&1 &

sleep 2

# Start scheduler for announcements
echo "Starting scheduler..."
nohup python ~/blt_bot/scripts/schedule.py > schedule.log 2>&1 &

echo "BLT-bot system started."
