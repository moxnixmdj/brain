"""Find the target by what it looks like, not only by what it says.

THE FAILURE THIS REPLACES
-------------------------
r122/r123 measured 5 of 10 MiniWob tasks failing, and every failure was the same
class: the target was not a text-labelled element in the DOM.

  click-color   the goal names a colour as a RENDERED SWATCH 60% of the time
                (`miniwob/html/miniwob/click-color.html` line 51). innerText is empty.
  click-dialog  the target is the glyph "x".
  click-link    the anchor's text is not exposed as an accessible name.
  choose-list   the options do not exist in the DOM until the select is opened.

In each case the information the agent needed was ON THE PAGE and the channel only
read its text. The 2026 consensus calls the fix "hybrid": take the accessibility
tree when it has something, and fall back to rendered appearance when it does not
(accessibility-only 73.1% vs hybrid 89.1% on WebVoyager, zylos 2026-02/2026-10;
"use the accessibility tree when it exists, fall back to Set-of-Marks where the
tree is empty").

WHAT THIS MODULE IS
-------------------
A resolver over a candidate set. The caller supplies candidates that already carry
BOTH kinds of address:

    {"text": ..., "aria": ..., "title": ..., "alt": ...,
     "bg": "rgb(r, g, b)", "glyph": ..., "tag": ..., "type": ...,
     "checked": bool, "x": float, "y": float}

and a goal sentence. The resolver works out WHICH KIND of question the goal is
asking, and answers it with the matching kind of evidence:

    goal names a colour    -> match on computed background colour
    goal is a bare swatch  -> read the swatch's own colour, then match it
    goal quotes a string   -> match text, aria, title, alt, then glyph
    goal names a glyph     -> match glyph

THE HONEST LINE
---------------
Reading the GOAL's rendering is not oracle access. The goal is the user's
instruction, and a human reads a colour swatch in an instruction the same way. What
would be oracle access is reading the page's answer variable -- MiniWob leaves
`correctElement` in scope, and this module never looks for it. The distinction is:
read the instruction and the screen; never read the grader.

WHAT IT CANNOT DO
-----------------
It cannot match a colour that is absent from the text AND rendered as an image with
no computable style (a photo, a canvas pixel). It cannot open a collapsed menu, and
it cannot read a glyph that is drawn as a background-image. Those remain genuinely
unaddressed and the resolver says so with a named refusal rather than guessing.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_APPEARANCE_ADDRESS_V1"

COLOURS = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
    "green": (0, 255, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0),
    "olive": (128, 128, 0), "purple": (128, 0, 128), "orange": (255, 165, 0),
    "brown": (165, 42, 42), "gray": (128, 128, 128), "grey": (128, 128, 128),
    "cyan": (0, 255, 255), "magenta": (255, 0, 255), "navy": (0, 0, 128),
    "teal": (0, 128, 128), "lime": (0, 255, 0), "maroon": (128, 0, 0),
    "silver": (192, 192, 192), "gold": (255, 215, 0),
}

RESOLVED = "RESOLVED"
NO_CANDIDATES = "NO_CANDIDATES"
NO_MODALITY = "GOAL_MODALITY_UNKNOWN"
NO_MATCH = "NO_APPEARANCE_MATCH"
AMBIGUOUS = "MULTIPLE_EQUAL_MATCHES"


class AddressError(ValueError):
    pass


def parse_rgb(value: Any) -> tuple[int, int, int] | None:
    """Accept 'rgb(r, g, b)', 'rgba(r, g, b, a)', '#rrggbb'. None if not a colour."""
    if not isinstance(value, str):
        return None
    m = re.search(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", value)
    if m:
        r, g, b = (int(x) for x in m.groups())
        return (r, g, b)
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", value.strip())
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return None


def is_transparent(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    m = re.search(r"rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9.]+)\s*\)", value)
    return bool(m) and float(m.group(1)) == 0.0


def colour_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def named_colour(word: str) -> tuple[int, int, int] | None:
    return COLOURS.get(str(word or "").strip().lower())


def goal_modality(goal: str, goal_swatch_rgb: tuple[int, int, int] | None) -> str:
    """Which kind of question is this goal asking?

    A goal swatch counts as an explicit colour instruction: the user is pointing at a
    colour rather than naming it. This is the click-color case, and it is why the
    modality is decided from the rendered goal and not from the text alone.
    """
    text = str(goal or "")
    if re.search(r"colou?red box", text, re.I) and (
        goal_swatch_rgb is not None or _named_colour_in(text) is not None
    ):
        return "COLOUR"
    if _named_colour_in(text) is not None and re.search(r"box|swatch|tile", text, re.I):
        return "COLOUR"
    quoted = re.search(r'"([^"]+)"|\u201c([^\u201d]+)\u201d', text)
    if quoted:
        token = (quoted.group(1) or quoted.group(2) or "").strip()
        if len(token) == 1:
            return "GLYPH"
        return "TEXT"
    return "TEXT"


def _named_colour_in(text: str) -> str | None:
    for word in COLOURS:
        if re.search(r"\b" + re.escape(word) + r"\b", text, re.I):
            return word
    return None


def resolve(
    goal: str,
    candidates: Sequence[Mapping[str, Any]],
    *,
    goal_swatch_rgb: tuple[int, int, int] | None = None,
    tolerance: int = 40,
) -> dict[str, Any]:
    """Pick the candidate the goal points at, using the modality the goal implies."""
    cands = [c for c in candidates if isinstance(c, Mapping)]
    if not cands:
        return {"schema": SCHEMA, "status": NO_CANDIDATES, "target": None,
                "reason": "no candidates were supplied"}

    modality = goal_modality(goal, goal_swatch_rgb)
    base = {"schema": SCHEMA, "modality": modality, "considered": len(cands)}

    if modality == "COLOUR":
        want = goal_swatch_rgb
        source = "goal_swatch"
        if want is None:
            word = _named_colour_in(goal)
            want = named_colour(word) if word else None
            source = "goal_text:" + str(word)
        if want is None:
            return {**base, "status": NO_MODALITY, "target": None,
                    "reason": "goal names a colour but neither the text nor the goal "
                              "swatch yields one"}
        scored = []
        for c in cands:
            rgb = parse_rgb(c.get("bg"))
            if rgb is None or is_transparent(c.get("bg")):
                continue
            d = colour_distance(rgb, want)
            if d <= tolerance:
                scored.append((d, c))
        if not scored:
            return {**base, "status": NO_MATCH, "target": None,
                    "reason": "no visible candidate background is within "
                              + str(tolerance) + " of " + str(want),
                    "wanted": want, "colour_source": source}
        scored.sort(key=lambda t: t[0])
        best = scored[0][0]
        # Near-ties are not a resolution. Two greens one unit apart are the same green
        # to a person and must not be silently separated by a rounding difference; an
        # exact-tie-only rule let (255,0,0) win over (254,0,0) during r124 development.
        tied = [c for d, c in scored if d - best <= 8]
        if len(tied) > 1:
            return {**base, "status": AMBIGUOUS, "target": None,
                    "reason": "two or more candidates sit within 8 L1 units of the best "
                              "colour distance " + str(best) + "; they are the same colour "
                              "to a person",
                    "wanted": want, "matches": len(tied)}
        return {**base, "status": RESOLVED, "target": dict(scored[0][1]),
                "distance": best, "wanted": want, "colour_source": source,
                "reason": "nearest visible background colour to the goal colour"}

    # TEXT / GLYPH: try every textual address the element exposes, in order of
    # specificity, and only then fall back to the glyph.
    m = re.search(r'"([^"]+)"', str(goal or ""))
    token = (m.group(1).strip() if m else "").strip()
    if not token:
        m2 = re.search(r"\b(?:Select|Click on|Close|Enter)\s+([A-Za-z0-9_\-\s]{1,40}?)(?:\s+and\b|\.|$)",
                       str(goal or ""))
        token = (m2.group(1).strip() if m2 else "").strip().strip('"')
    if not token:
        return {**base, "status": NO_MODALITY, "target": None,
                "reason": "no addressable token could be extracted from the goal"}

    fields = ("text", "aria", "title", "alt", "glyph")
    for field in fields:
        hits = [c for c in cands if str(c.get(field) or "").strip() == token]
        if len(hits) == 1:
            return {**base, "status": RESOLVED, "target": dict(hits[0]),
                    "matched_field": field, "token": token,
                    "reason": "exact match on " + field}
        if len(hits) > 1:
            return {**base, "status": AMBIGUOUS, "target": None, "matched_field": field,
                    "reason": "multiple candidates share this " + field, "token": token}
    for field in fields:
        hits = [c for c in cands
                if str(c.get(field) or "").strip().lower() == token.lower()]
        if len(hits) == 1:
            return {**base, "status": RESOLVED, "target": dict(hits[0]),
                    "matched_field": field + ":casefold", "token": token,
                    "reason": "case-insensitive match on " + field}
    return {**base, "status": NO_MATCH, "target": None, "token": token,
            "reason": "no candidate exposes this token in text, aria, title, alt or glyph"}
