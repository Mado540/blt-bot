#!/data/data/com.termux/files/usr/bin/bash

pkill -f bot.py
pkill -f schedule.py
pkill -f llama-server

sleep 2

~/blt_bot/scripts/start.sh
