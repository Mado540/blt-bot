import discord
import asyncio
import datetime
from discord.ext import tasks

from config import DISCORD_TOKEN
import requests
import json
import os

CHANNEL_ID = 1376409374263873546   # <<< SET THIS to the channel ID where announcements go.


# -----------------------------
# Helper: send a message to Qwen server
# -----------------------------

def ask_qwen(prompt):
    url = "http://127.0.0.1:8080/completion"
    payload = {
        "prompt": prompt,
        "max_tokens": 400,
        "temperature": 0.55
    }
    r = requests.post(url, json=payload)
    try:
        return r.json().get("content", "No response.")
    except:
        return "Error contacting Qwen."


# -----------------------------
# Helper: build announcement context
# -----------------------------

def build_context():
    base = "You are BLT-bot. Create an event announcement.\n\n"
    folder = "bot_data"

    for fname in os.listdir(folder):
        path = os.path.join(folder, fname)

        if os.path.isdir(path):
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                base += f"\n--- {fname} ---\n{f.read()}\n"
        except:
            pass

    return base


# -----------------------------
# Bot Setup
# -----------------------------

intents = discord.Intents.default()
client = discord.Client(intents=intents)


# -----------------------------
# Scheduled tasks
# -----------------------------

@tasks.loop(minutes=1)
async def scheduler_task():
    now = datetime.datetime.now().strftime("%H:%M")

    # Example scheduled times:
    # 12:00 midday summary
    # 20:00 event reminder
    # 00:00 daily reset summary

    schedule_map = {
        "12:00": "Provide a midday BLT status summary.",
        "20:00": "Provide an evening event reminder for all BLT members.",
        "00:00": "Provide a daily BLT reset summary."
    }

    if now in schedule_map:
        ctx = build_context()
        prompt = ctx + f"\n\nUser Request: {schedule_map[now]}"
        msg = ask_qwen(prompt)

        channel = client.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(msg)


@client.event
async def on_ready():
    print(f"Scheduler logged in as {client.user}")
    scheduler_task.start()


client.run(DISCORD_TOKEN)
