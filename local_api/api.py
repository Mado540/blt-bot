from flask import Flask, request, jsonify
import os

app = Flask(__name__)

BASE = "/data/data/com.termux/files/home/blt_bot/local_api"

# -------------------------------
# Helper: Safe file reading
# -------------------------------
def read_file(path):
    full = os.path.join(BASE, path)
    if not os.path.exists(full):
        return ""
    try:
        with open(full, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return ""

# -------------------------------
# Helper: simple compression
# -------------------------------
def shorten(text, limit=800):
    """Limit text to ~800 words to avoid token explosions."""
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]) + "\n[...shortened by local API...]"

# -------------------------------
# Load memory and rules
# -------------------------------
def load_global_memory():
    return read_file("global_memory.txt")

def load_rules():
    return read_file("rules.txt")

def load_strategy(mode):
    """Load strategy file based on mode."""
    modes = {
        "bt": "strategies/bt.txt",
        "kvk": "strategies/kvk.txt",
        "vikings": "strategies/vikings.txt",
    }
    if mode in modes:
        return read_file(modes[mode])
    return ""

# -------------------------------
# /think — main route
# -------------------------------
@app.route("/think", methods=["POST"])
def think():
    data = request.json or {}
    prompt = data.get("prompt", "")
    mode = data.get("mode", "general")

    gm = load_global_memory()
    rules = load_rules()
    strategy = load_strategy(mode)

    # Choose correct strategy section header
    if mode in ["bt", "kvk", "vikings"]:
        strategy_block = f"=== STRATEGY ({mode.upper()}) ===\n{strategy}\n\n"
    else:
        strategy_block = ""

    final_prompt = f"""=== GLOBAL MEMORY ===
{gm}

=== RULES ===
{rules}

{strategy_block}=== USER PROMPT (COMPRESSED) ===
{shorten(prompt, 800)}
"""

    return jsonify({"prompt_for_qwen": final_prompt})


# -------------------------------
# Run Local API
# -------------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5005)
