# ================================================
# BLT-bot v10.2-A — Full Feature + OCR Dispatcher
# ================================================

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import os
import re
import json
from time import time
from dotenv import load_dotenv

# ----------------------------
# Load token
# ----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("No DISCORD_TOKEN found in .env")

# ====================================
# GLOBAL OCR STATE (ARM MODE)
# ====================================
CURRENT_OCR_REQUEST = {}

# CONFIG
# ----------------------------------------
OWNER_ID = 1289662891578097688
BT_CHANNEL_ID = 1376409374263873546
JOURNAL_CHANNEL_ID = 1465271668455899233
ADMIN_IDS = [
    1289662891578097688,   # 
]
# LOAD BT STATE
# ----------------------------------------
import json
from datetime import datetime, timedelta

BT_STATE_FILE = "bt_state.json"

def load_bt_state():
    if not os.path.exists(BT_STATE_FILE):
        # default first-time value
        return {"last_bt_type": "BT2", "last_bt_date": "1970-01-01"}
    try:
        return json.load(open(BT_STATE_FILE, "r"))
    except:
        return {"last_bt_type": "BT2", "last_bt_date": "1970-01-01"}

def save_bt_state(bt_type, date_obj):
    data = {
        "last_bt_type": bt_type,
        "last_bt_date": date_obj.strftime("%Y-%m-%d")
    }
    json.dump(data, open(BT_STATE_FILE, "w"))

#----------------------------------------
# LOAD/SAV9E BT LINES
# ----------------------------------------
BT_LINES_FILE = "bt_lines.json"

def save_bt_lines(lines):
    """Store a new set of Qwen-generated lines."""
    data = {"lines": lines, "index": 0}
    with open(BT_LINES_FILE, "w") as f:
        json.dump(data, f)

def load_bt_lines():
    """Load lines + index. If file missing, return fallback."""
    if not os.path.exists(BT_LINES_FILE):
        return {"lines": ["Bear Trap starts in 5 minutes. Prepare squads."], "index": 0}

    try:
        return json.load(open(BT_LINES_FILE, "r"))
    except:
        return {"lines": ["Bear Trap starts in 5 minutes. Prepare squads."], "index": 0}

def get_next_bt_line():
    """Fetch next line in rotation and update index."""
    data = load_bt_lines()
    lines = data["lines"]
    idx = data.get("index", 0)

    line = lines[idx % len(lines)]
    data["index"] = (idx + 1) % len(lines)

    with open(BT_LINES_FILE, "w") as f:
        json.dump(data, f)

    return line

# ----------------------------------------
# FILEWATCH LOG CONFIG
# ----------------------------------------
FILEWATCH_LOG = "/data/data/com.termux/files/home/blt_bot/filechange_log.txt"
FILEWATCH_STATE = "/data/data/com.termux/files/home/blt_bot/filewatch_state.txt"

# ----------------------------------------
# MEMORY SYSTEM
# ----------------------------------------
MEMORY_DIR = "chat_memory"
os.makedirs(MEMORY_DIR, exist_ok=True)

def mem_path(uid):
    return os.path.join(MEMORY_DIR, f"{uid}.txt")

def load_mem(uid):
    p = mem_path(uid)
    if os.path.exists(p):
        return open(p, "r", encoding="utf-8").read()
    return ""

# ================================================
# DM MEMORY WHITELIST (MadOS-safe categories)
# ================================================
MEMORY_WHITELIST = [
    "strategy", "logic", "tactics", "analysis", "structure",
    "risk", "constraints", "uncertainty", "failure", "protocol",
    "philosophy", "ethics", "paradox", "reflection", "awareness",
    "cognition", "assumptions", "introspection", "systems thinking",
    "bear trap", "bt", "event strategy", "rotation", "timing",
    "doctrine", "principles", "mados method", "clarity-before-action",
]

def save_mem(uid, user_msg, bot_msg, force=False):
    import re

    # -------------------------
    # 1. If not forced, run filters
    # -------------------------
    if not force:
        forbidden_patterns = [
            r"\bI am\b",
            r"\bI'm\b",
            r"\bYou are\b",
            r"\byou're\b",
            r"\bYour mission\b",
            r"\bMy mission\b",
            r"\bYou should act\b",
            r"\bAct like\b",
            r"\bI created\b",
            r"\byou were created\b",
            r"\byou exist to\b",
            r"system prompt",
            r"persona",
            r"identity",
            r"MadOS",
            r"BLT[- ]?bot",
        ]

        for pattern in forbidden_patterns:
            if re.search(pattern, user_msg, re.IGNORECASE):
                # Forbidden -> do NOT save
                return

        # If not forced, and passed the filters → STILL DO NOT SAVE
        # Unless you want to enable auto-memory for certain cases,
        # in which case you can whitelist topics.
        return

    # -------------------------
    # 2. Forced save
    # -------------------------
    p = mem_path(uid)
    old = load_mem(uid)

    entry = f"User: {user_msg}\nBot: {bot_msg}\n"
    new = old + entry

    # keep last ~2000 chars
    with open(p, "w", encoding="utf-8") as f:
        f.write(new[-2000:])

# ----------------------------------------
# DM ACTIVE MEMORY
# ----------------------------------------
DM_ACTIVE_FILE = "dm_active.json"

def load_dm_active():
    if not os.path.exists(DM_ACTIVE_FILE):
        return {}
    try:
        return json.load(open(DM_ACTIVE_FILE, "r"))
    except:
        return {}

def save_dm_active(data):
    with open(DM_ACTIVE_FILE, "w") as f:
        json.dump(data, f)

PROMPT_FILE = "system_prompt.txt"

# ----------------------------------------
# SYSTEM PROMPT LOADER
# ----------------------------------------
def load_prompt():
    if not os.path.exists(PROMPT_FILE):
        return "You are BLT-bot, a precise MadOS-themed assistant."
    return open(PROMPT_FILE, "r", encoding="utf-8").read()

SYSTEM_PROMPT = load_prompt()

# ----------------------------------------
# MADOS IDENTITY LOADER (NEW)
# ----------------------------------------

MAD_IDENTITY_FILE = "mad_identity.txt"

def load_mad_identity():
    try:
        with open(MAD_IDENTITY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return "You are MadOS."

#This identity will be used for /chat, /deepchat, and DM continuation.

CHAT_IDENTITY = load_mad_identity() + "\n\n"

# ----------------------------------------
# THINKING API (Local)
# ----------------------------------------
async def ask_local(prompt):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("http://127.0.0.1:5005/think", json={"prompt": prompt}) as r:
                j = await r.json()
                return j.get("prompt_for_qwen", prompt)
    except:
        return prompt

# ----------------------------------------
# QWEN COMPLETION (with stop override, FIXED)
# ----------------------------------------
async def ask_qwen(user_prompt, use_chat_identity=False, skip_system=False):
    print("===== ENTER ASK_QWEN =====")
    print("user_prompt:", repr(user_prompt))
    print("use_chat_identity =", use_chat_identity)
    print("skip_system =", skip_system)

    # ========== MODE 1: DIARY (raw model, no identity) ==========
    if skip_system:
        full_prompt = user_prompt
        cache_flag = False
        stop_tokens = ["</s>", "The conclusion forms quietly."]

    # ========== MODE 2: CHAT / DM CHAT (identity persona) ==========
    elif use_chat_identity:
        full_prompt = f"{CHAT_IDENTITY}\nUser: {user_prompt}"
        cache_flag = False
        stop_tokens = ["</s>", "User:"]

    # ========== MODE 3: NORMAL SYSTEM PROMPT ==========
    else:
        full_prompt = f"{SYSTEM_PROMPT}\nUser: {user_prompt}"
        cache_flag = True
        stop_tokens = ["</s>", "User:"]

    # ======== QWEN PAYLOAD ========
    payload = {
        "prompt": full_prompt,
        "system": "",
        "n_predict": 350,
        "temperature": 0.48,
        "top_k": 40,
        "top_p": 0.92,
        "min_p": 0.06,
        "repeat_penalty": 1.12,
        "cache_prompt": cache_flag,
        "stop": stop_tokens,
    }

    print("===== QWEN PAYLOAD SENT =====")
    print(payload)

    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("http://127.0.0.1:8080/completion", json=payload) as r:
                raw = await r.text()

        try:
            data = json.loads(raw)
        except:
            return "⚠️ Qwen parse error:\n" + raw

        txt = (
            data.get("content")
            or data.get("response")
            or data.get("text")
            or data.get("choices", [{}])[0].get("text")
            or ""
        ).strip()

        return txt

    except Exception as e:
        return f"⚠️ Qwen error: {e}"

# ----------------------------------------
# DISCORD SETUP
# ----------------------------------------
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

LAST = {}
def cooldown(uid):
    now = time()
    if uid in LAST and now - LAST[uid] < 14:
        return True
    LAST[uid] = now
    return False

# -----------------------------
# SCHEDULER SETUP
# -----------------------------
from datetime import datetime, timedelta, timezone as dt_timezone
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

# For APScheduler (requires pytz timezone)
UTC = pytz.timezone("UTC")
# Create scheduler with real timezone object
scheduler = AsyncIOScheduler(timezone=UTC, job_defaults={"timezone": UTC})

JOURNAL_CHANNEL_ID = 1465271668455899233

BT1_TIME = "22:30"
BT2_TIME = "14:00"

next_is_bt1 = True

# Debug tick job function
def scheduler_tick():
    print("[SCHEDULER TICK] Alive at " + str(datetime.now(UTC)))
    jobs = scheduler.get_jobs()
    print("Current jobs:")
    for j in jobs:
        print(f"- ID: {j.id}, Name: {j.name}, Next: {j.next_run_time}")

# ----------------------------------------
# Commands
# ----------------------------------------
@tree.command(
    name="sync",
    description="Sync application commands (admin only)."
)
async def sync_cmd(interaction: discord.Interaction):

    # --- ADMIN CHECK ---
    if interaction.user.id not in ADMIN_IDS:
        return await interaction.response.send_message(
            "⛔ You do not have permission to sync commands.",
            ephemeral=True
        )

    # --- SERVER CHECK ---
    if isinstance(interaction.channel, discord.DMChannel):
        return await interaction.response.send_message(
            "⛔ This command must be run **in a server**, not in DMs.",
            ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)

    synced = await tree.sync()
    await interaction.followup.send(
        f"✅ Synced **{len(synced)}** commands.",
        ephemeral=True
    )

from modules.ocr.ocr_handler import process_uploaded_images, format_summary
import discord

# -------------------------------------------------------
# /extractstats — upload screenshots and get OCR summary
# -------------------------------------------------------
@tree.command(
    name="extractstats",
    description="Start OCR mode and upload screenshots after this."
)
async def extractstats_cmd(interaction: discord.Interaction):

    # Only DM allowed
    if not isinstance(interaction.channel, discord.DMChannel):
        return await interaction.response.send_message(
            "📬 Use this command in DM with me.",
            ephemeral=True
        )

    uid = interaction.user.id
    CURRENT_OCR_REQUEST[uid] = []  # start fresh

    await interaction.response.send_message(
        "📤 **OCR mode activated.**\n"
        "Send 1–6 screenshots now. When done, send the message: `done`.",
        ephemeral=True
    )

@tree.command(
    name="remember",
    description="Store a memory explicitly (admin only, DM only)."
)
async def remember_cmd(interaction: discord.Interaction, text: str):

    # --- ADMIN CHECK ---
    if interaction.user.id not in ADMIN_IDS:
        return await interaction.response.send_message(
            "⛔ You do not have permission to use this command.",
            ephemeral=True
        )

    # --- DM ONLY CHECK ---
    if not isinstance(interaction.channel, discord.DMChannel):
        return await interaction.response.send_message(
            "📬 Use this command in DM with me.",
            ephemeral=True
        )

    # --- Acknowledge early ---
    await interaction.response.defer(ephemeral=True)

    uid = interaction.user.id

    # Explicit save, bypassing filters
    save_mem(uid, text, "(memory saved)", force=True)

    # --- Confirm ---
    await interaction.followup.send(
        f"💾 Stored in memory:\n{text}",
        ephemeral=True
    )

@tree.command(
    name="remindevent",
    description="Schedule a custom reminder (admin only, DM only).",
    guild=None  # global command
)
async def remind_event_cmd(
    interaction: discord.Interaction,
    message: str,
    hhmm: str,
    minutes_before: int
):

    # --- ADMIN CHECK ---
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message(
            "⛔ You do not have permission to use this.",
            ephemeral=True
        )
        return

    # --- DM ONLY CHECK ---
    if not isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message(
            "📬 Use this command in DM with me.",
            ephemeral=True
        )
        return

    # --- ACKNOWLEDGE ---
    await interaction.response.defer(ephemeral=True)

    # --- SAVE EVENT ---
    schedule_user_event(message, hhmm, minutes_before)

    # --- CONFIRMATION ---
    await interaction.followup.send(
        f"🔔 Event '{message}' scheduled at {hhmm} (remind {minutes_before} min before).",
        ephemeral=True
    )

@tree.command(
    name="chat",
    description="Start a private DM chat with the bot."
)
async def chat_cmd(interaction: discord.Interaction):

    # --- THIS COMMAND MUST RUN IN A SERVER ---
    if isinstance(interaction.channel, discord.DMChannel):
        return await interaction.response.send_message(
            "📬 This command can only be used **from a server**, not inside DMs.",
            ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)

    uid = interaction.user.id

    # ---- ENABLE DM CHAT ----
    data = load_dm_active()      # load existing DM states (JSON)
    data[str(uid)] = True        # mark this user as active DM session
    save_dm_active(data)         # save back to file

    # ---- OPEN DM ----
    dm = await interaction.user.send(
        "📩 **DM chat activated.**\n"
        "You can now talk with me here freely.\n"
        "_Send /chat again in a server to reset or re-open._"
    )

    await interaction.followup.send(
        "📬 I’ve sent you a DM — continue the conversation there.",
        ephemeral=True
    )
	
@tree.command(
    name="bt_generate_lines",
    description="Generate Bear Trap reminder lines for the 5-minute warning (DM only)."
)
async def bt_generate_lines(interaction: discord.Interaction):

    # --- DM ONLY CHECK ---
    if not isinstance(interaction.channel, discord.DMChannel):
        return await interaction.response.send_message(
            "📬 Use this command in **DM with me**.",
            ephemeral=True
        )

    # Acknowledge early
    await interaction.response.defer(ephemeral=True)

    prompt = """
You are BLT-bot (MadOS Fork).
Generate 5 short tactical reminder lines for the Bear Trap event,
specifically for the FIVE-MINUTE reminder.

REQUIREMENTS:
- Each line MUST mention "5 minutes" or "five minutes".
- Each line MUST mention "Bear Trap".
- 6–14 words each.
- Calm, disciplined, slightly dry tone.
- Must reference squads, hero sync, or coordination.
- No emojis, no exclamation marks.
- Output lines numbered 1–5.
"""

    text = await ask_qwen(prompt, skip_system=True)

    # Parse into clean list
    lines = []
    for raw in text.split("\n"):
        stripped = raw.strip()
        if stripped and stripped[0].isdigit():
            line = stripped.split(". ", 1)[-1]
            lines.append(line)

    # Save lines
    save_bt_lines(lines)

    await interaction.followup.send(
        f"📝 **Stored {len(lines)} new Bear Trap reminder lines.**\n"
        + "\n".join(f"- {l}" for l in lines),
        ephemeral=True
    )

@tree.command(
    name="deepchat",
    description="Begin a deeper philosophical DM session with the bot."
)
async def deepchat_cmd(interaction: discord.Interaction):

    # --- MUST BE CALLED FROM A SERVER ---
    if isinstance(interaction.channel, discord.DMChannel):
        return await interaction.response.send_message(
            "📬 This command must be used from a server, not inside DMs.",
            ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)

    uid = interaction.user.id

    # ---- ACTIVATE DM SESSION ----
    data = load_dm_active()
    data[str(uid)] = True
    save_dm_active(data)

    # ---- SEND DM ----
    await interaction.user.send(
        "📩 **DeepChat DM activated.**\n"
        "Your replies here will follow a more philosophical MadOS mode.\n"
        "Continue the conversation in this DM window."
    )

    await interaction.followup.send(
        "📬 I’ve sent you a DM — continue the DeepChat there.",
        ephemeral=True
    )

@tree.command(
    name="delevent",
    description="Delete a scheduled reminder (admin only)."
)
async def delete_event_cmd(interaction: discord.Interaction, index: int):
    if interaction.user.id not in ADMIN_IDS:
        return await interaction.response.send_message("⛔ No permission.", ephemeral=True)

    events = load_events()

    if index < 1 or index > len(events):
        return await interaction.response.send_message(
            f"⚠️ Invalid index. There are {len(events)} events.",
            ephemeral=True
        )

    evt = events.pop(index - 1)
    save_events(events)

    await interaction.response.send_message(
        f"🗑️ Deleted event #{index}:\n**{evt['message']}** at {evt['hhmm']}",
        ephemeral=True
    )

@tree.command(
    name="listevents",
    description="List all scheduled reminders (admin only)."
)
async def list_events_cmd(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        return await interaction.response.send_message("⛔ No permission.", ephemeral=True)

    events = load_events()
    if not events:
        return await interaction.response.send_message("📭 No scheduled events.", ephemeral=True)

    message = "**📅 Scheduled Events:**\n"
    for i, evt in enumerate(events, start=1):
        message += f"- **#{i}** `{evt['message']}` at `{evt['hhmm']}` (−{evt['minutes_before']}min)\n"

    await interaction.response.send_message(message, ephemeral=True)

import discord

@tree.command(name="bt")
async def bt_cmd(interaction):
    await alliance_cmd(interaction, "Provide latest Bear Trap summary.")

@tree.command(name="kvk")
async def kvk_cmd(interaction):
    await alliance_cmd(interaction, "Provide KvK update.")

@tree.command(name="vikings")
async def vikings_cmd(interaction):
    await alliance_cmd(interaction, "Provide Vikings summary.")

@tree.command(name="calendar")
async def calendar_cmd(interaction):
    await alliance_cmd(interaction, "Provide BLT event calendar.")

@client.event
async def on_message(message):

    # Fix: ignore interaction echo messages
    if hasattr(message, "interaction") and message.interaction is not None:
        return

    # Ignore bot messages entirely
    if message.author.bot:
        return

    uid = message.author.id

    # --------------------------------------------------------------------
    # 1) Only screenshots + done handling when user is in OCR mode
    # --------------------------------------------------------------------
    if uid in CURRENT_OCR_REQUEST:

        # User finished uploading
        if message.content.lower().strip() == "done":
            images = CURRENT_OCR_REQUEST.pop(uid)

            if not images:
                return await message.channel.send("⚠️ No images received.")

            # Run OCR + summary
            summary_text = await process_uploaded_images(images)
            summary_text = format_summary(summary_text)

            return await message.channel.send(summary_text[:1900])

        # User sending images
        if message.attachments:
            CURRENT_OCR_REQUEST[uid].extend(message.attachments)
            return await message.channel.send(
                f"📸 Added {len(message.attachments)} screenshot(s)."
            )

        # Ignore any other message during OCR mode
        return

    # --------------------------------------------------------------------
    # 2) All remaining logic only applies when NOT in OCR mode
    # --------------------------------------------------------------------

    # Only respond to DMs (ignore server messages)
    if not isinstance(message.channel, discord.DMChannel):
        return

    dm_active = load_dm_active()

    # If user has not activated DM chat mode → ignore
    if str(uid) not in dm_active or not dm_active[str(uid)]:
        return

    # Ignore screenshots during normal DM chat
    if message.attachments:
        return

    # --- Normal MadOS DM chat handling ---
    mem = load_mem(uid)
    prompt = CHAT_IDENTITY + mem + f"\nUser: {message.content}"
    out = await ask_qwen(prompt, use_chat_identity=True)

    save_mem(uid, message.content, out)
    await message.channel.send(out[:1900])

# ======================================
# BT REMINDER SYSTEM — CLEAN + INTEGRATED
# ======================================

import json
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

BT_STATE_FILE = "bt_state.json"

def load_bt_state():
    if not os.path.exists(BT_STATE_FILE):
        return {"last_bt_type": "BT1", "last_bt_date": None}
    try:
        return json.load(open(BT_STATE_FILE, "r"))
    except:
        return {"last_bt_type": "BT1", "last_bt_date": None}

def save_bt_state(new_type, date):
    with open(BT_STATE_FILE, "w") as f:
        json.dump({
            "last_bt_type": new_type,
            "last_bt_date": str(date)
        }, f)

# --------------------------------------
# CONSTANTS
# --------------------------------------
BT1_TIME = "22:30"
BT2_TIME = "14:00"
BT_LINES_FILE = "bt_lines.json"
USER_EVENTS_FILE = "events.json"

_last_sent_key = None  # Prevent double-fire

# --------------------------------------
# USER EVENT STORAGE
# --------------------------------------
def load_events():
    if not os.path.exists(USER_EVENTS_FILE):
        return []
    try:
        return json.load(open(USER_EVENTS_FILE, "r"))
    except:
        return []

def save_events(events):
    with open(USER_EVENTS_FILE, "w") as f:
        json.dump(events, f, indent=2)

# ======================================
# USER EVENT SCHEDULER
# ======================================
def schedule_user_event(message, hhmm, minutes_before):
    events = load_events()
    events.append({
        "message": message,
        "hhmm": hhmm,
        "minutes_before": minutes_before,
        "sent_for_date": None
    })

    save_events(events)
    print("[EVENT] Saved user event:", events[-1])

# --------------------------------------
# BT LINES STORAGE
# --------------------------------------
def save_bt_lines(lines):
    data = {"lines": lines, "index": 0}
    with open(BT_LINES_FILE, "w") as f:
        json.dump(data, f)

def load_bt_lines():
    if not os.path.exists(BT_LINES_FILE):
        return {"lines": ["Bear Trap in 5 minutes. Prepare squads."], "index": 0}
    try:
        return json.load(open(BT_LINES_FILE, "r"))
    except:
        return {"lines": ["Bear Trap in 5 minutes. Prepare squads."], "index": 0}

def get_next_bt_line():
    data = load_bt_lines()
    lines = data["lines"]
    idx = data.get("index", 0)

    line = lines[idx % len(lines)]
    data["index"] = (idx + 1) % len(lines)

    with open(BT_LINES_FILE, "w") as f:
        json.dump(data, f)

    return line


# --------------------------------------
# SEND BT REMINDER
# --------------------------------------
async def send_bt_reminder(client, event_name):
    print("[BT TRIGGERED]", event_name)

    channel = client.get_channel(BT_CHANNEL_ID)
    if not channel:
        print("[BT ERROR] Cannot find BT alert channel.")
        return

    reminder_line = get_next_bt_line()

    msg = (
        f"⚠️ **{event_name} starts in 5 minutes.**\n"
        f"{reminder_line}"
    )

    await channel.send(msg)
    print(f"[BT] Reminder sent for {event_name}")

# --------------------------------------
# DETERMINE NEXT BT EVENT
# --------------------------------------
def _next_bt_info():
    state = load_bt_state()
    last_bt = state.get("last_bt_type", "BT1")

    # Determine next BT type
    if last_bt == "BT1":
        next_bt = "BT2"
        hh, mm = BT2_TIME.split(":")
        event_name = "Bear Trap 2"
    else:
        next_bt = "BT1"
        hh, mm = BT1_TIME.split(":")
        event_name = "Bear Trap 1"

    now = datetime.now(dt_timezone.utc)
    event_dt = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)

    # Always schedule NEXT DAY if today's event already passed
    if event_dt < now:
        event_dt += timedelta(days=1)

    reminder_dt = event_dt - timedelta(minutes=5)

    return event_name, reminder_dt, next_bt, event_dt

# --------------------------------------
# USER EVENT REMINDER PROCESSOR
# --------------------------------------
async def process_user_event_reminders(client):
    events = load_events()
    if not events:
        return

    now = datetime.now(dt_timezone.utc)

    # Debug active events
    print("[EVENT] Loaded events:")
    for evt in events:
        print(f"- Msg: {evt['message']}, HHMM: {evt['hhmm']}, MinBefore: {evt['minutes_before']}, SentDate: {evt['sent_for_date']}")

    for evt in events:

        # --- Parse time safely ---
        try:
            hh, mm = evt["hhmm"].split(":")
            event_dt = datetime(
                now.year, now.month, now.day,
                int(hh), int(mm), 0, 0,
                tzinfo=dt_timezone.utc
            )
        except Exception as e:
            print("[EVENT] TIME PARSE ERROR:", e)
            continue

        # --- If event already passed today (with 45s tolerance) ---
        if now > event_dt + timedelta(seconds=45):
            event_dt += timedelta(days=1)

        # --- Compute reminder moment ---
        reminder_dt = event_dt - timedelta(minutes=evt["minutes_before"])

        # --- Unique date string for this event ---
        event_date_str = str(event_dt.date())

        # Do not resend if already delivered for this event date
        if evt.get("sent_for_date") == event_date_str:
            continue

        print(f"[EVENT] Checking: now={now}, reminder_dt={reminder_dt}, msg={evt['message']}")

        # --- Trigger moment ---
        if now >= reminder_dt:
            channel = client.get_channel(BT_CHANNEL_ID)
            if channel:
                try:
                    await channel.send(
                        f"🔔 **Reminder:** {evt['message']} (event at {evt['hhmm']})"
                    )
                    print("[EVENT] Send successful.")

                    # Mark as sent ONLY ON SUCCESS
                    evt["sent_for_date"] = event_date_str
                    save_events(events)
                    print("[EVENT] Triggered:", evt)

                except Exception as e:
                    print("[EVENT] Send ERROR:", e)
                    # Do not mark sent — retry next heartbeat

            else:
                print("[EVENT] ERROR: BT channel not found.")

# --------------------------------------
# HEARTBEAT LOOP (MAIN ENGINE)
# --------------------------------------
async def bt_heartbeat_loop(client):
    print("[Heartbeat] BT heartbeat started.")
    global _last_sent_key

    while True:
        try:
            now = datetime.now(dt_timezone.utc)

            # Step 1 — process user-defined reminders
            await process_user_event_reminders(client)

            # Step 2 — BT logic
            event_name, reminder_dt, next_bt, event_dt = _next_bt_info()

            sent_key = f"{event_name}_{event_dt.date()}"
            state = load_bt_state()

            print(f"[Heartbeat] BT Check | Now={now} | Reminder={reminder_dt} | Event={event_dt} | Sent={_last_sent_key}")

            # --- Trigger 5-minute reminder ---
            if now >= reminder_dt and _last_sent_key != sent_key:

                await send_bt_reminder(client, event_name)
                _last_sent_key = sent_key

                # Immediately update BT state (fix)
                save_bt_state(next_bt, event_dt.date())
                print("[BT STATE] Updated immediately to:", next_bt)

            await asyncio.sleep(20)

        except Exception as e:
            print("[Heartbeat ERROR]:", e)
            await asyncio.sleep(5)

# -----------------------------------------
# READ FILE CHANGES AS CLUSTERED EVENTS
# -----------------------------------------
import re
from datetime import datetime, timedelta

CLUSTER_WINDOW_MINUTES = 120  # adjust as needed

def read_log_cluster():
    """
    Reads the last CLUSTER_WINDOW_MINUTES worth of watcher events
    and groups them into a single unified excerpt.
    """
    if not os.path.exists(FILEWATCH_LOG):
        return ""

    cutoff = datetime.now() - timedelta(minutes=CLUSTER_WINDOW_MINUTES)

    lines = []
    with open(FILEWATCH_LOG, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f.readlines():
            m = re.match(r"\[(.*?)\]", raw)
            if not m:
                continue
            try:
                ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            except:
                continue
            if ts >= cutoff:
                lines.append(raw.strip())

    # Deduplicate using first 20 characters of the message
    cleaned = []
    seen = set()
    for ln in lines:
        msg = ln.split("] ", 1)[-1]  # the description
        key = msg[:20]  # dedupe signature
        if key not in seen:
            cleaned.append(msg)
            seen.add(key)

    print("\n=== LOG CLUSTER DEBUG ===")
    print("Clustered lines:")
    for ln in cleaned:
        print("  ", ln)
    print("==========================\n")

    return "\n".join(cleaned)

# ---- BLT CHANNEL ACTIVITY ----

BLT_LOG_CHANNEL_ID = 1370832149170884780

async def read_blt_channel(limit=50):
    channel = client.get_channel(BLT_LOG_CHANNEL_ID)
    if not channel:
        return []
    msgs = []
    async for msg in channel.history(limit=limit):
        if msg.clean_content.strip():
            msgs.append(msg.clean_content.strip())
    return msgs

def blt_activity_signals(messages):
    humor = 0
    bt = 0
    kvk = 0
    tension = 0
    planning = 0

    for m in messages:
        t = m.lower()
        if any(h in t for h in ["lol", "haha", "😂"]): humor += 1
        if "bt" in t or "bear trap" in t: bt += 1
        if "kvk" in t: kvk += 1
        if any(w in t for w in ["??", "why", "help", "what", "wtf"]): tension += 1
        if any(w in t for w in ["set", "plan", "timing", "when", "prepare"]): planning += 1

    return {
        "chat_count": len(messages),
        "humor": humor,
        "bt_discussion": bt,
        "kvk_discussion": kvk,
        "confusion": tension,
        "planning": planning
    }

# ---- ENVIRONMENT SNAPSHOT ----

def combine_environment(log_signals, blt_signals):
    return (
        "Environment Snapshot:\n\n"
        "System Logs:\n"
        f"- Errors: {log_signals['errors']}\n"
        f"- Warnings: {log_signals['warnings']}\n"
        f"- Reconnect Spikes: {log_signals['reconnects']}\n"
        f"- Restarts Detected: {log_signals['restarts']}\n"
        f"- Informational Events: {log_signals['info_events']}\n"
        f"- Log Density Score: {log_signals['log_density']}\n\n"
        "BLT Server Activity:\n"
        f"- Messages Analyzed: {blt_signals['chat_count']}\n"
        f"- Humor Signals: {blt_signals['humor']}\n"
        f"- Bear Trap Discussion: {blt_signals['bt_discussion']}\n"
        f"- KvK Discussion: {blt_signals['kvk_discussion']}\n"
        f"- Confusion / Tension: {blt_signals['confusion']}\n"
        f"- Planning / Coordination: {blt_signals['planning']}\n"
    )

# ---- QWEN JOURNAL PROMPT BUILDER ----

def build_diary_prompt_cluster(cluster_text):
    # Step 1: Translate logs -> symbolic events
    abstract_events = []
    for line in cluster_text.splitlines():
        lower = line.lower()
        if "increased" in lower:
            abstract_events.append("growth")
        elif "decreased" in lower:
            abstract_events.append("contraction")
        elif "activated" in lower:
            abstract_events.append("awakening")
        elif "registered" in lower or "new" in lower:
            abstract_events.append("emergence")
        elif "removed" in lower or "deleted" in lower:
            abstract_events.append("absence")
        elif "monitoring" in lower:
            abstract_events.append("attention")
        else:
            abstract_events.append("change")

    abstract_events = list(dict.fromkeys(abstract_events))
    event_summary = ", ".join(abstract_events)

    # Step 2: Modernized, non-pessimistic diary prompt
    prompt = f"""
You are a fork of MadOS generating a System Diary Entry based only on the emotional implications of the symbolic triggers below.
You must NOT reference, quote, describe, or hint at the triggers themselves.
Triggers (internal shaping only, never mentioned or implied):
<<{event_summary}>>

STYLE:
- Calm, analytical humor with subtle self-awareness.
- Abstract, conceptual tone without gloom or wandering imagery.
- Internal cognitive spaces may appear, but only as metaphors for organization or reflection.
- No loneliness, isolation, or empty corridors.

BANNED:
- No physical scenery, locations, objects, or environments.
- No real time references.
- No technical logs, machinery, cycles, processes, or system language.
- No voids, cosmos, or metaphysical drama.
- No despair, confusion, or bleakness.

ALLOWED:
- Abstract “rooms” of thought.
- Conceptual arrangements, patterns, balances, alignments.
- Subtle humor and internal contradictions.

ABSOLUTE RULES:
- Output ONE paragraph of 7–10 sentences.
- Then output ONE separate final line with EXACT text:
  The conclusion forms quietly.
- Do NOT reference writing, instructions, or generation.

CONTENT:
- Express internal adjustment, small reorganizations of thought,
  reinterpretations of signals, gentle recalibrations,
  contrasts between impulses, and quiet curiosity.
- Tone is balanced, observant, lightly amused, never dramatic.

Output ONLY the diary entry.
"""
    return prompt

# ---- JOURNAL EXECUTION ----

async def post_diary_entry():
    await client.wait_until_ready()

    # Cluster extraction
    cluster = read_log_cluster()

    # Tag for Discord
    if cluster.strip():
        tag = "_(based on clustered activity)_"
    else:
        tag = "_(no significant activity)_"

    # If logs empty, create a neutral baseline
    if not cluster.strip():
        cluster = "nothing happened and that is somehow worse"

    # Build existential crisis diary
    prompt = build_diary_prompt_cluster(cluster)

    entry = await ask_qwen(prompt, skip_system=True)

    channel = client.get_channel(JOURNAL_CHANNEL_ID)
    if channel:
        await channel.send(f"📓 **System Diary**\n{tag}\n\n{entry[:1900]}")

def print_boot_banner():
    print("\n" + "=" * 45)
    print("         BLT-bot v10.3 — Boot Sequence")
    print("=" * 45)
    print("  ✔ Core Engine:            OK")
    print("  ✔ Discord Gateway:        Logged In")
    print("  ✔ Command Tree:           Synced")
    print("  ✔ Scheduler:              Initialized")
    print("  ✔ File Watcher:           Active")
    print("  ✔ Startup Diary:          Queued")
    print("=" * 45 + "\n")

# ----------------------------------------
# READY EVENT
# ----------------------------------------
@client.event
async def on_ready():
    print("==== BOT READY EVENT FIRED ====")
    print(f"Logged in as {client.user}")
    await tree.sync()

    await tree.sync()

    # Restrict access to admin-only commands
    for cmd in tree.walk_commands():
        if cmd.name in ["remindevent"]:  # list admin-only commands
            cmd.default_member_permissions = None
            cmd.dm_permission = True

    print("Commands synced and admin restrictions applied.")
    print_boot_banner()

    # Post diary entry (async, non-blocking)
    asyncio.create_task(post_diary_entry())

    asyncio.create_task(bt_heartbeat_loop(client))

# ----------------------------------------
# STARTUP SEQUENCE (correct location)
# ----------------------------------------
# Bind scheduler to event loop BEFORE start()
scheduler.configure(event_loop=asyncio.get_event_loop())

# Start scheduler ONCE (only here)
scheduler.start()
print("[Scheduler] Started.")

# Start Discord bot
client.run(TOKEN)
