import discord
from discord import app_commands
import aiohttp
import asyncio
import os
import re
from datetime import datetime, timezone

from collections import defaultdict
from time import time

from config import DISCORD_TOKEN, DATA_PATH, PROMPT_FILE

# ────────────────────────────────────────────────
# COOLDOWN
# ────────────────────────────────────────────────
LAST_USE = defaultdict(float)
COOLDOWN_SEC = 25

# ────────────────────────────────────────────────
# MEMORY
# ────────────────────────────────────────────────
MEMORY_DIR = "chat_memory"
os.makedirs(MEMORY_DIR, exist_ok=True)

MAX_MEMORY_CHARS = 1600
RECENT_LINES = 20
MENTION_RE = re.compile(r"<@!?(\d+)>")

def memory_path(uid):
    return os.path.join(MEMORY_DIR, f"{uid}.txt")

def load_memory(uid):
    path = memory_path(uid)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def save_memory(uid, user_msg, bot_msg):
    path = memory_path(uid)
    entry = f"User: {user_msg}\nBot: {bot_msg}\n"

    old = ""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            old = f.read()

    combined = old + entry

    if len(combined) <= MAX_MEMORY_CHARS:
        with open(path, "w", encoding="utf-8") as f:
            f.write(combined)
        return

    # Compress old memory
    lines = combined.splitlines()
    recent = lines[-RECENT_LINES * 2:]

    summary = (
        "Summary of earlier conversation:\n"
        "- User prefers reflective, calm, dry humor\n"
        "- Conversation is casual, philosophical, non-operational\n\n"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(summary + "\n".join(recent))

# ────────────────────────────────────────────────
# SYSTEM IDENTITY
# ────────────────────────────────────────────────
def load_system_prompt():
    if not os.path.exists(PROMPT_FILE):
        return "You are BLT-bot, a conversational fork of MadOS."
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT = load_system_prompt()

CHAT_IDENTITY = (
    "You are BLT-bot, a conversational fork of the MadOS framework.\n"
    "You speak naturally, calmly, and with dry humor.\n"
    "You think like MadOS but talk like a human.\n\n"
)

# ────────────────────────────────────────────────
# QWEN CALL
# ────────────────────────────────────────────────
async def ask_qwen(prompt):
    async with aiohttp.ClientSession() as session:
        payload = {
            "prompt": prompt,
            "n_predict": 280,
            "temperature": 0.48,
            "top_k": 35,
            "top_p": 0.92,
            "min_p": 0.06,
            "repeat_penalty": 1.12,
            "cache_prompt": True,
            "stop": ["\nUser:", "User:"]
        }
        try:
            async with session.post("http://127.0.0.1:8080/completion", json=payload) as resp:
                data = await resp.json()
                return data.get("content", "").strip()
        except Exception as e:
            return f"⚠️ Qwen error: {str(e)[:120]}"

# ────────────────────────────────────────────────
# DISCORD BOT SETUP
# ────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def on_cd(uid):
    now = time()
    if now - LAST_USE[uid] < COOLDOWN_SEC:
        return True
    LAST_USE[uid] = now
    return False

# ────────────────────────────────────────────────
# CHAT COMMAND
# ────────────────────────────────────────────────
@tree.command(name="chat", description="Chat with BLT-bot (memory enabled).")
async def chat(interaction: discord.Interaction, message: str):
    uid = interaction.user.id
    if on_cd(uid):
        await interaction.response.send_message("⏳ Cooldown active.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)

    clean = MENTION_RE.sub("", message).strip()
    memory = load_memory(uid)

    prompt = CHAT_IDENTITY + memory + "\n\nUser: " + clean
    out = await ask_qwen(prompt)

    save_memory(uid, clean, out)

    await interaction.followup.send(out[:1900])

# ────────────────────────────────────────────────
# ALLIANCE COMMANDS
# ────────────────────────────────────────────────
async def alliance_cmd(interaction, query):
    uid = interaction.user.id
    if on_cd(uid):
        await interaction.response.send_message("⏳ Cooldown.", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    out = await ask_qwen(SYSTEM_PROMPT + "\n\n" + query)
    await interaction.followup.send(out[:1900])

@tree.command(name="bt")
async def bt(interaction): await alliance_cmd(interaction, "Provide latest Bear Trap summary.")

@tree.command(name="calendar")
async def calendar(interaction): await alliance_cmd(interaction, "List the BLT event calendar.")

@tree.command(name="vikings")
async def vikings(interaction): await alliance_cmd(interaction, "Provide Vikings summary.")

@tree.command(name="kvk")
async def kvk(interaction): await alliance_cmd(interaction, "Provide KvK summary.")

# ────────────────────────────────────────────────
# TRIGGER SYSTEM (A)
# ────────────────────────────────────────────────

TRIGGER_DIR = os.path.join(DATA_PATH, "triggers")
EVENT_CHANNEL_ID = 1376409374263873546  # Your channel

os.makedirs(TRIGGER_DIR, exist_ok=True)

async def scan_for_triggers():
    """Check trigger folder every 5 seconds and post messages."""
    await client.wait_until_ready()
    print(f"Trigger watcher active at: {TRIGGER_DIR}")

    while not client.is_closed():
        try:
            files = [f for f in os.listdir(TRIGGER_DIR) if f.endswith(".txt")]
            for fname in files:
                full = os.path.join(TRIGGER_DIR, fname)
                try:
                    with open(full, "r", encoding="utf-8") as f:
                        content = f.read().strip()

                    ch = client.get_channel(EVENT_CHANNEL_ID)
                    if ch:
                        await ch.send(content)
                        print(f"Trigger sent: {fname}")
                    else:
                        print("ERROR: Event channel not found.")

                    os.remove(full)
                except Exception as e:
                    print(f"Trigger error: {e}")
        except Exception as e:
            print(f"Watcher loop error: {e}")

        await asyncio.sleep(5)

# ────────────────────────────────────────────────
# STARTUP
# ────────────────────────────────────────────────
@client.event
async def on_ready():
    print(f"BLT-bot logged in as {client.user}")
    await tree.sync()
    print("Slash commands synced.")
    client.loop.create_task(scan_for_triggers())
    print("Trigger watcher started.")

client.run(DISCORD_TOKEN)
