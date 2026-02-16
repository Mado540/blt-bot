import os
import re
import difflib
import pypinyin
from modules.ocr.name_matcher import fuzzy_fix_name

# -----------------------------------------------------------
# LOAD PLAYER NAMES
# -----------------------------------------------------------

BASE = os.path.dirname(__file__)
NAMES_FILE = os.path.join(BASE, "player_names.txt")

with open(NAMES_FILE, "r", encoding="utf8") as f:
    VALID_NAMES = [line.strip() for line in f if line.strip()]

LATIN_NAMES = [n for n in VALID_NAMES if re.search(r"[A-Za-z]", n)]
CJK_NAMES = [n for n in VALID_NAMES if re.search(r"[\u4e00-\u9fff\uac00-\ud7af]", n)]

# MilkTea fixes
MILKTEA_ALIASES = {
    "奶茶", "奶⻢", "奶木", "奶茗", "奶苶", "奶查", "奶苽",
    "MilkTea", "Milk Tea", "milk tea", "milk-tea",
    "奶 茶MilkTea", "紅茶拿鐵無糖去冰MilkTea"
}

# PEiPEi Greek OCR failures
SPECIAL_ALIASES = {
    "ΡΕΪΡΕΙ": "PEiPEi",
    "ΡΕΙΡΕΙ": "PEiPEi",
    "ΡEΙΡΕΙ": "PEiPEi",
    "PEΙPEΙ": "PEiPEi",
    "ΡΕlΡΕl": "PEiPEi",
    "REIREI": "PEiPEi",
    "P E I P E I": "PEiPEi",
}

# -----------------------------------------------------------
# HELPERS
# -----------------------------------------------------------

def is_cjk(s):
    return bool(re.search(r"[\u4e00-\u9fff\uac00-\ud7af]", s))


def clean_number(raw):
    raw = raw.replace("O", "0").replace(" ", "").replace(",", "").replace(".", "")
    raw = re.sub(r"[^0-9]", "", raw)
    return int(raw) if raw.isdigit() else None


def clean_name(raw):
    if not raw:
        return ""

    raw = (
        raw.replace("[BLT]", "")
           .replace("BLT]", "")
           .replace("[BLT", "")
           .replace("#", "")
           .replace("|", "")
           .replace("¢", "")
           .replace("@", "")
           .strip()
    )

    raw = re.sub(r"^(o?\d+|[sS]?\d+|il|b=|[%<>=¥]\s*)", "", raw)
    raw = re.sub(r"[^\w\u4e00-\u9fff\uac00-\ud7af\s()]", "", raw)

    return raw.strip()


def inline_name_ok(name):
    if not name:
        return False
    if "damage" in name.lower():
        return False

    letters = re.sub(r"[^A-Za-z\u4e00-\u9fff\uac00-\ud7af]", "", name)
    return len(letters) >= 1


def canonical_name(name):
    if not name:
        return None

    # MilkTea override
    if name in MILKTEA_ALIASES:
        return "奶茶 (MilkTea)"

    # PEiPEi Greek OCR aliases
    if name in SPECIAL_ALIASES:
        return SPECIAL_ALIASES[name]

    return name


def match_name(name):
    if not name:
        return None

    # Normalize special/canonical names
    fixed = canonical_name(name)
    if fixed != name:
        return fixed

    # CJK fuzzy (pinyin)
    if is_cjk(name):
        name_py = " ".join(pypinyin.lazy_pinyin(name))
        valid_py = [" ".join(pypinyin.lazy_pinyin(v)) for v in CJK_NAMES]

        matches = difflib.get_close_matches(name_py, valid_py, n=1, cutoff=0.6)
        if matches:
            idx = valid_py.index(matches[0])
            return canonical_name(CJK_NAMES[idx])

        return fuzzy_fix_name(name)

    # Latin fuzzy
    matches = difflib.get_close_matches(name, LATIN_NAMES, n=1, cutoff=0.6)
    if matches:
        return canonical_name(matches[0])

    return fuzzy_fix_name(name)


# -----------------------------------------------------------
# OCR POST-PROCESSING
# -----------------------------------------------------------

def postprocess_ocr(blocks):

    players = {}
    total_damage = None
    last_name = None

    DAMAGE_REGEX = re.compile(
        r"(Damage\s*Points|Damage\|Points|DamagePoints|Damage\s*\|\s*Points|Damage Points:)",
        re.IGNORECASE
    )

    # ---------------------------------------------------
    # MERGE ALL OCR BLOCKS INTO UNIQUE LINES
    # ---------------------------------------------------
    all_text = "\n".join(block["text"].strip() for block in blocks if block.get("text"))
    lines = list(dict.fromkeys(l.strip() for l in all_text.split("\n") if l.strip()))

    # ---------------------------------------------------
    # PARSE LINES
    # ---------------------------------------------------
    for line in lines:

        # ---------- TOTAL DAMAGE ----------
        if "Total Alliance Damage" in line:
            m = re.search(r"([\d,\.]{6,})", line)
            if m:
                total_damage = clean_number(m.group(1))
            continue

        # ---------- NAME ONLY LINE ----------
        if "Damage" not in line and not re.search(r"\d", line):
            nm = clean_name(line)
            if nm and len(nm) > 1:
                last_name = nm
            continue

        # ---------- DAMAGE LINE ----------
        if DAMAGE_REGEX.search(line):

            match = DAMAGE_REGEX.search(line)
            inline_raw = clean_name(line[:match.start()].strip()) if match else ""
            dmg_raw = line[match.end():].strip()

            dmg_digits = re.sub(r"[^0-9]", "", dmg_raw)
            if not dmg_digits.isdigit():
                continue

            dmg = int(dmg_digits)
            raw_name = inline_name_ok(inline_raw) and inline_raw or last_name
            if not raw_name:
                continue

            fixed = match_name(raw_name)
            if not fixed:
                continue

            # Insert or update (keep highest value)
            if fixed in players:
                players[fixed] = max(players[fixed], dmg)
            else:
                players[fixed] = dmg

            last_name = None

    return players, total_damage
