# modules/ocr/format_blt_summary.py

def format_blt_summary(players, total_damage):

    # players is a dict: {"PEiPEi": 989176381, ...}

    # Safety check
    if not players:
        return (
            "📊 **Bear Trap Damage Summary**\n"
            "⚠️ No valid players detected from OCR.\n"
            f"Total damage detected: **{total_damage:,}**"
        )

    # Sort by damage DESC
    sorted_players = sorted(players.items(), key=lambda x: x[1], reverse=True)

    # Build output
    lines = ["📊 **Bear Trap Damage Summary**\n"]

    if total_damage:
        lines.append(f"🏹 **Alliance Damage:** {total_damage:,}\n")

    for name, dmg in sorted_players:
        lines.append(f"• **{name}** — {dmg:,}")

    return "\n".join(lines)
