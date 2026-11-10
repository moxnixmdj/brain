"""A generic, model-free policy for named-widget tasks. No per-task code, no answers.

This is the whole point of the ladder: if a page declares role=button name="ok", then
'Click on the "ok" button' is not a machine-learning problem. It is a lookup.

The policy is deliberately narrow and its limits are the interesting part. It can:
    click a named button/link
    click a named option/tab/listitem/menuitem
    type a quoted string into a textbox
    type into a textbox when the goal says what to enter
It cannot: drag, draw, copy one field into another, do arithmetic, or answer a question whose
answer is in the page's data rather than its structure. Those are counted as failures, not
excused.
"""
from __future__ import annotations

import re
from typing import Any

QUOTED = re.compile(r'["\u201c\u2018]([^"\u201d\u2019]{1,80})["\u201d\u2019]')
CLICKABLE = ("button", "link", "option", "tab", "menuitem", "listitem", "radio", "checkbox",
             "listbox", "switch")
TYPEABLE = ("textbox", "combobox", "searchbox")


def centre(node: dict) -> tuple[float, float]:
    """ax_nodes reports a box, not a point. Every click bug in this file came from forgetting."""
    b = node.get("box") or {}
    if "x" in node and "y" in node:
        return float(node["x"]), float(node["y"])
    return ((b["x0"] + b["x1"]) / 2.0, (b["y0"] + b["y1"]) / 2.0)


def quoted(goal: str) -> list[str]:
    return [m.group(1).strip() for m in QUOTED.finditer(goal)]


SELECT_CUE = re.compile(
    r"\b(select|choose|pick|click(?: on)?(?: the)?|find(?: and click)?)\b(?: the)?\s*",
    re.I)


def bare_target(goal: str) -> str | None:
    """'Select ETaZ2K8 and click Submit.' -- the target is unquoted and is a page-generated
    token. Read it as the first capitalised-looking word after the selecting verb, stopping
    at any connective. This is parsing the instruction, not guessing the answer."""
    g = goal.strip()
    m = SELECT_CUE.search(g)
    if not m:
        return None
    rest = g[m.end():]
    rest = re.split(r"\s+(?:and|then|from|in|into|on|below|above)\b", rest, maxsplit=1)[0]
    rest = rest.strip(" .,;:\u201c\u201d\"'")
    if not rest or len(rest) > 40 or rest.lower() in ("submit", "the", "a", "an"):
        return None
    if rest.lower().startswith(("all ", "words ", "the ")):
        return None
    return rest


def want(goal: str) -> dict[str, Any]:
    g = goal.strip()
    low = g.lower()
    q = quoted(g)
    if low.startswith("enter") and q:
        return {"kind": "type_named", "text": q[0]}
    if low.startswith("type") and q:
        return {"kind": "type_named", "text": q[0]}
    if "select" in low[:30] and q:
        return {"kind": "click_named", "name": q[0]}
    if low.startswith("click") and q:
        return {"kind": "click_named", "name": q[0]}
    if low.startswith("click") and re.search(r"tab\s*#?\s*(\d+)", low):
        n = int(re.search(r"tab\s*#?\s*(\d+)", low).group(1))
        return {"kind": "click_nth_tab", "n": n}
    if low.startswith("click") and "button" in low and "one" in low and "two" in low:
        return {"kind": "click_two", "names": ["ONE", "TWO"]}
    if "select" in low[:30] or low.startswith(("choose", "pick")):
        b = bare_target(g)
        if b:
            return {"kind": "click_named", "name": b}
    if low.startswith("click"):
        return {"kind": "click_first", "name": None}
    return {"kind": "unknown"}


def choose(nodes: list[dict], plan: dict[str, Any]) -> dict | None:
    kind = plan["kind"]
    name = plan.get("name")
    if kind in ("click_named", "type_named"):
        low = name.lower()
        pool = [n for n in nodes if n["role"] in CLICKABLE + TYPEABLE]
        exact = [n for n in pool if n["name"].strip().lower() == low]
        if exact:
            return exact[0]
        loose = [n for n in pool if low in n["name"].strip().lower()]
        return loose[0] if loose else None
    if kind == "click_nth_tab":
        tabs = [n for n in nodes if n["role"] in ("tab", "listitem", "option", "link")]
        k = plan["n"]
        return tabs[k - 1] if 0 < k <= len(tabs) else None
    if kind == "click_first":
        pool = [n for n in nodes if n["role"] in ("button", "link")]
        return pool[0] if pool else None
    if kind == "type_named":
        pool = [n for n in nodes if n["role"] in TYPEABLE]
        return pool[0] if pool else None
    return None


def textbox(nodes: list[dict]) -> dict | None:
    for n in nodes:
        if n["role"] in TYPEABLE:
            return n
    return None


def submit_button(nodes: list[dict]) -> dict | None:
    for n in nodes:
        if n["role"] == "button" and n["name"].strip().lower() in (
                "submit", "ok", "okay", "send", "go", "done", "save", "apply", "enter"):
            return n
    return None
