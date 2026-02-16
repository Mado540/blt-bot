import re

# Very small, safe pseudo-Levenshtein
def _dist(a, b):
    """Simple edit distance good enough for OCR names."""
    dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(len(a)+1): dp[i][0] = i
    for j in range(len(b)+1): dp[0][j] = j
    for i in range(1, len(a)+1):
        for j in range(1, len(b)+1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(
                dp[i-1][j] + 1,
                dp[i][j-1] + 1,
                dp[i-1][j-1] + cost
            )
    return dp[-1][-1]


def fuzzy_fix_name(name, VALID_NAMES=None):
    """
    Universal fuzzy matcher.
    - VALID_NAMES is an optional list passed by postprocess.py
    - If omitted, we fall back to entire player list from disk.
    """

    # Late import to avoid circular imports
    from modules.ocr.postprocess import VALID_NAMES as GLOBAL_LIST

    # Choose list
    candidates = VALID_NAMES if VALID_NAMES else GLOBAL_LIST
    if not candidates:
        return None

    # Exact match first
    if name in candidates:
        return name

    n = name.lower()

    best = None
    best_score = 999

    for cand in candidates:
        c = cand.lower()
        d = _dist(n, c)

        # Hard limits to avoid garbage matches
        if d < best_score and d <= max(2, len(c)//3):
            best = cand
            best_score = d

    return best
