import discord
from discord import app_commands
import aiohttp
import asyncio
import os
import re
from time import time
from datetime import datetime
import pytesseract
from PIL import Image
import io

# ───────────────────────────────────────────────
# CONFIG
# ───────────────────────────────────────────────
OWNER_ID = 1289662891578097688
BT_CHANNEL_ID = 1399681073977491463

from config import DISCORD_TOKEN, PROMPT_FILE

# ───────────────────────────────────────────────
# MEMORY
# ───────────────────────────────────────────────
MEMORY_DIR = "chat_memory"
os.makedirs(MEMORY_DIR, exist_ok=True)

MAX_MEMORY_CHARS = 1500
RECENT_LINES = 16

def mem_path(uid):
    return os.path.join(MEMORY_DIR, f"{uid}.txt")

def load_mem(uid):
    p = mem_path(uid)
    if not os.path.exists(p):
        return ""
    return open(p, "r", encoding="utf-8").read()

def save_mem(uid, user_msg, bot_msg):
    p = mem_path(uid)
    entry = f"User: {user_msg}\nBot: {bot_msg}\n"

    old = ""
    if os.path.exists(p):
        old = open(p, "r", encoding="utf-8").read()

    combined = old + entry

    if len(combined) <= MAX_MEMORY_CHARS:
        open(p, "w", encoding="utf-8").write(combined)
        return

    # Compress memory
    lines = combined.splitlines()
    recent = lines[-RECENT_LINES*2:]

    summary = (
        "Earlier convo summary:\n"
        "- Light chat, dry humor.\n"
        "- Non-strategic context.\n\n"
    )

    open(p, "w", encoding="utf-8").write(summary + "\n".join(recent))

# ───────────────────────────────────────────────
# SYSTEM PROMPT
# ───────────────────────────────────────────────
def load_system_prompt():
    if not os.path.exists(PROMPT_FILE):
        return "You are BLT-bot, a polite MadOS-style assistant."
    return open(PROMPT_FILE, "r", encoding="utf-8").read()

SYSTEM_PROMPT = load_system_prompt()

CHAT_IDENTITY = (
    "You are BLT-bot, a conversational fork of MadOS.\n"
    "Tone: calm, precise, dry humor.\n\n"
)

# ───────────────────────────────────────────────
# LOCAL API
# ───────────────────────────────────────────────
async def ask_local_api(prompt):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://127.0.0.1:5005/think", json={"prompt": prompt}) as resp:
                data = await resp.json()
                return data.get("prompt_for_qwen", prompt)
    except:
        return prompt

# ───────────────────────────────────────────────
# QWEN COMPLETION
# ───────────────────────────────────────────────
async def ask_qwen(prompt):
    payload = {
        "prompt": prompt,
        "n_predict": 260,
        "temperature": 0.48,
        "top_k": 40,
        "top_p": 0.92,
        "min_p": 0.06,
        "repeat_penalty": 1.12,
        "cache_prompt": True,
        "stop": ["</s>", "User:"]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://127.0.0.1:8080/completion",
                                    json=payload) as resp:
                data = await resp.json()
                return (data.get("content") or "").strip()
    except Exception as e:
        return f"⚠️ Qwen error: {e}"

# ───────────────────────────────────────────────
# DISCORD CLIENT
# ───────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

LAST = {}
COOLDOWN = 14

def on_cd(uid):
    now = time()
    if uid in LAST and now - LAST[uid] < COOLDOWN:
        return True
    LAST[uid] = now
    return False

# ───────────────────────────────────────────────
# /sync
# ───────────────────────────────────────────────
@tree.command(name="sync", description="Force-refresh slash commands.")
async def sync_cmd(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("No permission.", ephemeral=True)
    await tree.sync()
    return await interaction.response.send_message("Commands synced.", ephemeral=True)

# ───────────────────────────────────────────────
# /perf
# ───────────────────────────────────────────────
@tree.command(name="perf", description="Measure Qwen speed.")
async def perf(interaction):
    await interaction.response.defer(thinking=True)
    t0 = time()
    out = await ask_qwen("Say 'OK' once.")
    t1 = time()
    await interaction.followup.send(f"⚡ Qwen responded in **{round(t1-t0,2)} sec**\nOutput: `{out}`")

# ───────────────────────────────────────────────
# CHAT COMMANDS
# ───────────────────────────────────────────────
@tree.command(name="chat")
async def chat(interaction, message: str):
    uid = interaction.user.id
    if on_cd(uid):
        return await interaction.response.send_message("Cooldown.", ephemeral=True)
    await interaction.response.defer(thinking=True)

    memory = load_mem(uid)
    prompt = CHAT_IDENTITY + memory + f"\nUser: {message}"
    out = await ask_qwen(prompt)

    save_mem(uid, message, out)
    await interaction.followup.send(out[:1900])

@tree.command(name="deepchat")
async def deepchat(interaction, query: str):
    uid = interaction.user.id
    if on_cd(uid):
        return await interaction.response.send_message("Cooldown.", ephemeral=True)
    await interaction.response.defer(thinking=True)

    memory = load_mem(uid)
    enriched = await ask_local_api(CHAT_IDENTITY + memory + f"\nUser: {query}")
    out = await ask_qwen(enriched)

    save_mem(uid, query, out)
    await interaction.followup.send(out[:1900])

# ───────────────────────────────────────────────
# ALLIANCE COMMANDS
# ───────────────────────────────────────────────
async def alliance_cmd(interaction, query):
    uid = interaction.user.id
    if on_cd(uid):
        return await interaction.response.send_message("Cooldown.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    enriched = await ask_local_api("Alliance request:\n" + query)
    out = await ask_qwen(enriched)

    await interaction.followup.send(out[:1900])

@tree.command(name="bt")
async def bt(interaction):
    await alliance_cmd(interaction, "Provide latest Bear Trap summary.")

@tree.command(name="kvk")
async def kvk(interaction):
    await alliance_cmd(interaction, "Provide KvK update.")

@tree.command(name="vikings")
async def vikings(interaction):
    await alliance_cmd(interaction, "Provide Vikings summary.")

@tree.command(name="calendar")
async def calendar(interaction):
    await alliance_cmd(interaction, "Provide BLT event calendar.")

# ───────────────────────────────────────────────
# OCR v9.4 — Kingshot Screenshot Parser (single-image mode)
# ───────────────────────────────────────────────

BT_RESULTS_FILE = "bot_data/bear_trap_history.txt"
os.makedirs("bot_data", exist_ok=True)

def save_bt_result(text):
    """Append formatted OCR result to file."""
    with open(BT_RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write("\n=== OCR BT Result ===\n")
        f.write(text.strip() + "\n")
        f.write(f"(Saved {datetime.now()})\n\n")


# Clean number: 592,142,846 → 592142846
def clean_number(numstr):
    return int(numstr.replace(",", "").replace(".", ""))


# Detect: Name + Damage Points
NAME_DAMAGE_RE = re.compile(
    r"([A-Za-z0-9\[\] _\-]{2,20})[^\d]*([0-9][0-9,\.]{4,})"
)


def extract_bt_data(raw_text):
    """
    Extracts ranked entries from a Kingshot Bear Trap screenshot.
    ONLY works per screenshot. No merging.
    """

    lines = raw_text.splitlines()

    total_damage = None
    total_rallies = None

    players = []

    for line in lines:
        ln = line.strip()
        if not ln:
            continue

        # Extract total alliance damage
        if "Total Alliance Damage" in ln:
            m = re.search(r"([\d,\.]+)", ln)
            if m:
                total_damage = clean_number(m.group(1))
            continue

        # Extract number of rallies
        if "Rallies" in ln:
            m = re.search(r"(\d+)", ln)
            if m:
                total_rallies = int(m.group(1))
            continue

        # Extract player entries
        m = NAME_DAMAGE_RE.search(ln)
        if m:
            name_raw = m.group(1).strip()
            dmg_raw = m.group(2)

            # Filter garbage lines
            if len(name_raw) < 2:
                continue

            dmg = clean_number(dmg_raw)
            players.append((name_raw, dmg))

    # Sort descending
    players.sort(key=lambda x: x[1], reverse=True)

    # Build output
    out = []

    if total_rallies:
        out.append(f"Rallies: {total_rallies}")

    if total_damage:
        out.append(f"Total Alliance Damage: {total_damage:,}")

    out.append("\nTop Damage:")

    rank = 1
    for name, dmg in players:
        out.append(f"{rank}) {name} — {dmg:,}")
        rank += 1
        if rank > 20:
            break

    return "\n".join(out)


async def run_ocr(attachment):
    """Full OCR pipeline for a single screenshot."""
    try:
        img_bytes = await attachment.read()
        img = Image.open(io.BytesIO(img_bytes))

        raw = pytesseract.image_to_string(img, lang="eng+chi_sim")

        result = extract_bt_data(raw)

        # Save always
        save_bt_result(result)

        return result

    except Exception as e:
        return f"⚠️ OCR error: {e}"

# ───────────────────────────────────────────────
# /bt_ocr — manual OCR
# ───────────────────────────────────────────────
@tree.command(name="bt_ocr", description="OCR Bear Trap screenshot.")
async def bt_ocr_cmd(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    out = await run_ocr(image)
    await interaction.followup.send(f"```\n{out}\n```")

# ───────────────────────────────────────────────
# AUTO-OCR ON MESSAGE
# ───────────────────────────────────────────────
@client.event
async def on_message(message):

    # Ignore bot's own messages
    if message.author.id == client.user.id:
        return

    # AUTO-OCR: Only inside BT channel
    if message.channel.id == BT_CHANNEL_ID:

        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type and "image" in attachment.content_type:
                    print("[OCR] Screenshot detected → running OCR.")
                    out = await run_ocr(attachment)
                    print("[OCR] Done.")

    # IMPORTANT:
    # Do NOT call client.process_application_commands
    # Your Discord.py version does not require it
    # Slash commands work independently
    return

# ───────────────────────────────────────────────
# READY
# ───────────────────────────────────────────────
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    await tree.sync()
    print("Commands synced.")

client.run(DISCORD_TOKEN)
