# ============================
# Discord Bot Configuration (INTEGRATED MODE)
# ============================

# Your bot token (Keep this safe!)
import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ABSOLUTE PATH to your .gguf model file.
# I derived this from your screenshots.
MODEL_PATH = "/data/data/com.termux/files/home/models/Qwen2.5-3B-Instruct-Q4_K_M.gguf"

# Admin users who can run /announce /aar /reload_data
ADMIN_USERS = [
    "Mados"
]

# Path to bot_data folder
DATA_PATH = "/data/data/com.termux/files/home/blt_bot/bot_data"

# Path to system prompt file
PROMPT_FILE = "/data/data/com.termux/files/home/blt_bot/system_prompt.txt"
