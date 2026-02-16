import discord
from discord import app_commands
import aiohttp
import asyncio
import os
import re
from time import time
from datetime import datetime

# ───────────────────────────────────────────────
# CONFIG
# ───────────────────────────────────────────────
OWNER_ID = 1289662891578097688
TEST_CHANNEL_ID = 1465271667042553939

from config import DISCORD_TOKEN, PROMPT_FILE

# -------------------------------------------
# DISCORD CLIENT + SLASH TREE
# -------------------------------------------
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ───────────────────────────────────────────────
# COOLDOWN
# ───────────────────────────────────────────────
LAST_USE = {}
COOLDOWN = 20

def on_cd(uid):
    now = time()
    last = LAST_USE.get(uid, 0)
    if now - last < COOLDOWN:
        return True
    LAST_USE[uid] = now
    return False

# ───────────────────────────────────────────────
# MEMORY SYSTEM
# ───────────────────────────────────────────────
MEMORY_DIR = "chat_memory"
os.makedirs(MEMORY_DIR, exist_ok=True)

def mem_path(uid): return os.path.join(MEMORY_DIR, f"{uid}.txt")

def load_memory(uid):
    fp = mem_path(uid)
    if os.path.exists(fp):
        return open(fp, "r", encoding="utf-8").read()
    return ""

def save_memory(uid, user, bot):
    fp = mem_path(uid)
    entry = f"User: {user}\nBot: {bot}\n"
    old = load_memory(uid)
    new = (old + entry)[-1800:]
    open(fp, "w", encoding="utf-8").write(new)

# ───────────────────────────────────────────────
# SYSTEM PROMPT
# ───────────────────────────────────────────────
def load_system_prompt():
    if not os.path.exists(PROMPT_FILE):
        return "You are BLT-bot, a clean conversational fork of MadOS."
    return open(PROMPT_FILE, "r", encoding="utf-8").read()

SYSTEM_PROMPT = load_system_prompt()

CHAT_IDENTITY = (
    "You are BLT-bot, a calm, structured variant of MadOS.\n"
    "Dry humor allowed. Clarity first.\n\n"
)

# ───────────────────────────────────────────────
# LOCAL API CALL
# ───────────────────────────────────────────────
async def ask_local_api(prompt, mode="general"):
    url = "http://127.0.0.1:5005/think"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"prompt": prompt, "mode": mode}) as resp:
                data = await resp.json()
                return data.get("prompt_for_qwen", prompt)
    except:
        return prompt

# ───────────────────────────────────────────────
# QWEN SERVER CALL
# ───────────────────────────────────────────────
async def ask_qwen(prompt):
    payload = {
        "prompt": prompt,
        "n_predict": 260,
        "temperature": 0.45,
        "top_k": 35,
        "top_p": 0.92,
        "min_p": 0.06,
        "repeat_penalty": 1.12,
        "cache_prompt": True,
        "stop": ["User:", "\nUser:"]
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://127.0.0.1:8080/completion", json=payload) as resp:
                data = await resp.json()
                return data.get("content", "").strip()
    except:
        return "⚠ Qwen connection error."

# ───────────────────────────────────────────────
# DISCORD CLIENT
# ───────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
MENTION_RE = re.compile(r"<@!?(\d+)>")

# ───────────────────────────────────────────────
# COMMAND: /ping
# ───────────────────────────────────────────────
@tree.command(name="ping", description="Test if bot is alive.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!", ephemeral=True)

# ───────────────────────────────────────────────
# COMMAND: /sync  (owner only)
# ───────────────────────────────────────────────
@tree.command(name="sync", description="Sync slash commands (owner only).")
async def sync_cmd(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    synced = await tree.sync()
    await interaction.response.send_message(
        f"Commands synced: {len(synced)}",
        ephemeral=True
    )

# ───────────────────────────────────────────────
# COMMAND: /chat  (fast mode)
# ───────────────────────────────────────────────
@tree.command(name="chat", description="Light fast chat with memory.")
async def chat(interaction, message: str):
    uid = interaction.user.id
    if on_cd(uid):
        await interaction.response.send_message("Cooldown.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)

    clean = MENTION_RE.sub("", message).strip()
    memory = load_memory(uid)

    prompt = CHAT_IDENTITY + memory + "\nUser: " + clean
    out = await ask_qwen(prompt)

    save_memory(uid, clean, out)
    await interaction.followup.send(out[:1900])

# ───────────────────────────────────────────────
# COMMAND: /deepchat  (local API → Qwen)
# ───────────────────────────────────────────────
@tree.command(name="deepchat", description="Deep reasoning using local API + Qwen.")
async def deepchat(interaction, query: str):
    uid = interaction.user.id

    if on_cd(uid):
        await interaction.response.send_message("Cooldown.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)

    clean = MENTION_RE.sub("", query).strip()
    memory = load_memory(uid)

    base = CHAT_IDENTITY + memory + "\nUser: " + clean
    enriched = await ask_local_api(base, mode="general")
    out = await ask_qwen(enriched)

    if not out:
        out = "⚠ Empty response."

    save_memory(uid, clean, out)
    await interaction.followup.send(out[:1900])

# ───────────────────────────────────────────────
# HYBRID ALLIANCE COMMANDS
# ───────────────────────────────────────────────
async def alliance_cmd(interaction, query):
    uid = interaction.user.id
    if on_cd(uid):
        await interaction.response.send_message("Cooldown.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)

    enriched = await ask_local_api(f"Alliance request:\n{query}", mode="general")
    out = await ask_qwen(enriched)

    await interaction.followup.send(out[:1900])

@tree.command(name="bt", description="Bear Trap summary.")
async def bt(interaction): await alliance_cmd(interaction, "Provide Bear Trap summary.")

@tree.command(name="kvk", description="KvK summary.")
async def kvk(interaction): await alliance_cmd(interaction, "Provide KvK summary.")

@tree.command(name="vikings", description="Vikings summary.")
async def vikings(interaction): await alliance_cmd(interaction, "Provide Vikings summary.")

@tree.command(name="calendar", description="Event calendar.")
async def calendar(interaction): await alliance_cmd(interaction, "Provide BLT event calendar.")

# ───────────────────────────────────────────────
# READY EVENT
# ───────────────────────────────────────────────
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    synced = await tree.sync()
    print(f"Commands synced: {len(synced)}")

# ───────────────────────────────────────────────
# RUN BOT
# ───────────────────────────────────────────────
client.run(DISCORD_TOKEN)
