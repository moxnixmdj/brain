"""Locate a word inside a text run, geometrically. The link is not a node.

MEASURED, click-collapsible-2: after opening Section #1 the accessibility tree gives ONE
StaticText, ' cursus a fusce ullamcorper lectus sem s...', spanning (6,75)-(146,130). The
link the goal names is five words in. There is no node for it. Clicking the StaticText's
centre clicks the wrong word.

So: the text run is a rectangle of wrapped monospace-ish prose. Given the word to find and its
index in the run, the position is arithmetic on line count and character offset. This is a
GEOMETRIC estimate, it is reported as such, and it is verified afterwards by the pixel gate --
which is the only thing entitled to say whether the click landed.
"""
from __future__ import annotations

import math
import re
from typing import Any


def locate_word(node: dict, word: str, *, char_width: float | None = None,
                line_height: float | None = None) -> dict[str, Any]:
    """Best-effort rectangle for `word` inside a text run described by `node`.

    Parameters are inferred from the node's own box when not supplied: MiniWob prose is a
    fixed font, so character width is recoverable from the longest line and line height from
    the wrapped-line count. Every inference is returned so a caller can see how much of this
    is measurement and how much is guess.
    """
    text = node.get("name") or ""
    box = node.get("box") or {}
    low = text.lower()
    idx = low.find(word.lower())
    if idx < 0 or not box:
        return {"found": False, "why": "word not in this run"}

    w = box.get("w") or (box.get("x1", 0) - box.get("x0", 0))
    h = box.get("h") or (box.get("y1", 0) - box.get("y0", 0))
    lines = [ln for ln in text.split("\n")] if "\n" in text else None
    if lines:
        n_lines = max(1, len(lines))
        longest = max((len(ln) for ln in lines), default=1) or 1
    else:
        n_lines = max(1, round(h / 15.0)) if h else 1
        longest = max(1, math.ceil(len(text) / n_lines))
    cw = char_width or (w / longest if longest else 7.0)
    lh = line_height or (h / n_lines if n_lines else 15.0)

    chars_per_line = max(1, int(w / cw)) if cw else max(1, longest)
    line_no = idx // chars_per_line
    col = idx % chars_per_line
    x = box["x0"] + (col + len(word) / 2.0) * cw
    y = box["y0"] + (line_no + 0.5) * lh
    return {
        "found": True, "x": round(x, 1), "y": round(y, 1), "role": node.get("role"),
        "in_run": text[max(0, idx - 20): idx + len(word) + 20],
        "estimate": {"char_width": round(cw, 2), "line_height": round(lh, 2),
                     "line": line_no, "col": col, "lines": n_lines},
        "confidence": "GEOMETRIC_ESTIMATE" if cw else "WEAK",
    }


def best_run(nodes: list[dict], word: str) -> dict[str, Any] | None:
    """The tightest text run containing the word, excluding the instruction itself.

    The goal sentence is rendered on the page and contains every target word. Excluding it by
    phrase is safer than by role, because the instruction appears in more than one node."""
    cands = []
    want = re.sub(r"[^a-z0-9]", "", word.lower()) or word.lower()
    for n in nodes:
        nm = (n.get("name") or "")
        # WORD BOUNDARY, not substring. 'nec' is inside 'donec' and inside 'nec'; choosing
        # 'donec risus,' scored 0.000 while the true node scored 0.85. This is r68's lesson
        # in a new place: a matcher that accepts everything finds the wrong thing.
        if not nm or not re.search(r"\b" + re.escape(want) + r"\b", nm.lower()):
            continue
        low = nm.lower()
        if "find and click" in low or "expand the" in low or "click on the" in low:
            continue
        if re.search(r"\bsec\b|/ 10sec|last reward|episodes done|time left", low):
            continue      # the benchmark's own clock is not page content
        cands.append(n)
    if not cands:
        return None
    # PER-WORD NODES EXIST in this app: 'Amet,' at (6,75), 'lectus' at (39,75). Choosing the
    # LONGEST run (my first heuristic) threw them away and clicked paragraph centres.
    # Prefer an exact word match; fall back to the tightest run.
    def core(x: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (x or "").lower())

    exact = [n for n in cands if core(n.get("name")) == core(want)]
    if exact:
        return min(exact, key=lambda n: (n.get("box") or {}).get("w", 1e9))
    # any node whose WHOLE text is one word (with punctuation) is still a word node
    single = [n for n in cands if len((n.get("name") or "").split()) == 1]
    if single:
        one = [n for n in single
               if re.sub(r"[^a-z0-9]", "", (n.get("name") or "").lower()) == re.sub(r"[^a-z0-9]", "", want)]
        return min(one or single, key=lambda n: len(n.get("name") or ""))
    # no word node: locate the word geometrically inside the phrase rather than clicking
    # the phrase centre, which is a different word and scores -1.
    phrase = min(cands, key=lambda n: len(n.get("name") or ""))
    return phrase
