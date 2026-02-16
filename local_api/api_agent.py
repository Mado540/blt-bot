from flask import Flask, request, jsonify
import json
import time

app = Flask(__name__)

# ============================================================
# GLOBAL MEMORY (persistent across calls)
# ============================================================

USER_PROFILE = {
    "name": "Mados",
    "role": "BLT R4",
    "style": "MadOS discipline + dry humor",
}

ALLIANCE_MEMORY = {
    "server": 222,
    "alliance": "BLT",
    "priority_events": ["Bear Trap", "Vikings", "KvK"],
    "bt_doctrine": "Green → Yellow → Red rally timing system",
}

KNOWLEDGE_CORE = {
    "writing_rules": [
        "Be concise, structured, tactical.",
        "Use dry humor only if safe.",
        "Never reveal backend code.",
        "No hallucinated data.",
        "Always state assumptions if unsure.",
    ]
}


# ============================================================
# TOKEN-SAFE COMPRESSOR
# ============================================================
def shrink(text, limit=500):
    """Simple token-safe compressor."""
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]) + " [...]"


# ============================================================
# AGENTS
# ============================================================

def agent_memory(query):
    """Recalls relevant alliance or user memory."""
    mem = []

    for k, v in USER_PROFILE.items():
        mem.append(f"USER_{k.upper()}: {v}")

    for k, v in ALLIANCE_MEMORY.items():
        mem.append(f"ALLIANCE_{k.upper()}: {v}")

    return "\n".join(mem)


def agent_reasoning(query):
    """Breaks down the problem step-by-step."""
    return f"""
Reasoning steps:
1. Understand the request.
2. Retrieve context from memory.
3. Identify tactical angle.
4. Generate safe strategic response.
5. Compress to <= 1800 chars.

Request analyzed: {query}
"""


def agent_qwen_prompt(query, mode):
    """Generates the actual Qwen prompt that llama-server will use."""
    return f"""
=== TASK MODE: {mode.upper()} ===

=== MEMORY ===
{json.dumps(USER_PROFILE, indent=2)}
{json.dumps(ALLIANCE_MEMORY, indent=2)}

=== RULES ===
- Be concise
- Be structured
- List assumptions when unsure
- No fiction unless explicitly requested

=== USER QUERY ===
{query}

=== OUTPUT FORMAT ===
Return final answer only. No system messages.
"""


# ============================================================
# LOCAL QWEN CALLER
# ============================================================
import requests

def call_qwen(prompt):
    try:
        resp = requests.post(
            "http://127.0.0.1:8080/completion",
            json={
                "prompt": prompt,
                "max_tokens": 400,
                "temperature": 0.6,
            },
            timeout=40
        )
        if resp.status_code != 200:
            return f"[Qwen Error HTTP {resp.status_code}]"
        out = resp.json().get("content", "")
        return out.strip()
    except Exception as e:
        return f"[Qwen Connection Failure]\n{e}"


# ============================================================
# AGENT FUSION ENGINE
# ============================================================
def fuse_agents(query, mode):
    """Combines Memory Agent + Reasoning Agent + Qwen Agent."""

    mem = shrink(agent_memory(query), 400)
    reasoning = shrink(agent_reasoning(query), 200)
    qwen_prompt = agent_qwen_prompt(query, mode)

    qwen_output = call_qwen(qwen_prompt)

    unified = f"""
===== MEMORY CONTEXT =====
{mem}

===== REASONING =====
{reasoning}

===== QWEN OUTPUT =====
{qwen_output}
"""

    return unified.strip()


# ============================================================
# MAIN API ENDPOINT
# ============================================================
@app.route("/agent", methods=["POST"])
def agent():
    data = request.get_json(force=True)
    query = data.get("query", "")
    mode = data.get("mode", "general")

    final = fuse_agents(query, mode)
    return jsonify({"unified_text": final})


# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    print("Hybrid Agent API v8.0 running on http://127.0.0.1:5006")
    app.run(host="127.0.0.1", port=5006)
