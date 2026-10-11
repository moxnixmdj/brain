"""Generic deterministic OSWorld policy V3.

Uses only the current instruction, active accessibility tree, and prior receipts.
No task identifiers, reference trajectories, or external cognition.
"""
from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Mapping

STATE_NS = "https://accessibility.ubuntu.example.org/ns/state"
COMP_NS = "https://accessibility.ubuntu.example.org/ns/component"

CLICKABLE = ("button", "link", "item", "menu", "tab", "check-box", "combo-box", "row")
EDITABLE = ("entry", "searchbox", "textbox", "textfield", "textarea")


@dataclass(frozen=True)
class Element:
    tag: str
    label: str
    x: int
    y: int
    clickable: bool
    editable: bool


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def center(node: ET.Element):
    pos = node.get(f"{{{COMP_NS}}}screencoord")
    size = node.get(f"{{{COMP_NS}}}size")
    if not pos or not size:
        return None
    a = re.fullmatch(r"\((-?\d+),\s*(-?\d+)\)", pos)
    b = re.fullmatch(r"\((-?\d+),\s*(-?\d+)\)", size)
    if not a or not b:
        return None
    x, y = int(a.group(1)), int(a.group(2))
    w, h = int(b.group(1)), int(b.group(2))
    if min(x, y) < 0 or w <= 0 or h <= 0:
        return None
    return x + w // 2, y + h // 2


def active_apps(root: ET.Element):
    apps = [x for x in list(root) if x.tag.rsplit("}", 1)[-1].lower() == "application"]
    active = []
    for app in apps:
        if any(child.get(f"{{{STATE_NS}}}active") == "true" for child in list(app)):
            active.append(app)
    return active or apps


def parse_tree(xml_text):
    if not isinstance(xml_text, str) or not xml_text.strip():
        return [], []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return [], []

    selected = active_apps(root)
    names = [str(x.get("name") or "").strip() for x in selected]
    names = [x for x in names if x]
    elements = []

    for app in selected:
        for node in app.iter():
            if node.get(f"{{{STATE_NS}}}visible") == "false":
                continue
            if node.get(f"{{{STATE_NS}}}showing") == "false":
                continue
            pt = center(node)
            if pt is None:
                continue
            name = str(node.get("name") or "").strip()
            body = str(node.text or "").strip()
            label = name if not body or body == name else ((name + " " + body) if name else body)
            if not label:
                continue
            tag = node.tag.rsplit("}", 1)[-1].lower()
            elements.append(Element(
                tag=tag,
                label=label,
                x=pt[0],
                y=pt[1],
                clickable=any(tag.endswith(x) for x in CLICKABLE),
                editable=any(tag.endswith(x) for x in EDITABLE),
            ))
    return names, elements


def browser_active(names):
    return any("chrome" in norm(x) or "chromium" in norm(x) for x in names)


def repeated_state(state):
    history = state.get("history")
    return (
        isinstance(history, list)
        and bool(history)
        and isinstance(history[-1], Mapping)
        and history[-1].get("screenshot_sha256") == state.get("screenshot_sha256")
    )


def clean(value):
    return value.strip().strip(" \t\r\n\"'.,;")


def search_value(instruction):
    m = re.search(
        r"\bsearch(?:\s+for)?\s+(.+?)(?=\s+(?:and then|then|and)\b|$)",
        instruction,
        re.I,
    )
    return clean(m.group(1)) if m and clean(m.group(1)) else None


def unique_target(instruction, elements, editable):
    query = norm(instruction)
    found = []
    for e in elements:
        if editable and not e.editable:
            continue
        if not editable and not e.clickable:
            continue
        label = norm(e.label)
        if len(label) >= 2 and re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", query):
            found.append(e)
    if not found:
        return None
    longest = max(len(norm(x.label)) for x in found)
    winners = [x for x in found if len(norm(x.label)) == longest]
    return winners[0] if len(winners) == 1 else None


def field_value(instruction, label):
    escaped = re.escape(label)
    patterns = (
        rf"\b(?:set|change)\s+(?:the\s+)?{escaped}\s+(?:to|as)\s+(.+?)(?:[.;]|$)",
        rf"\bfill\s+(?:the\s+)?{escaped}\s+with\s+(.+?)(?:[.;]|$)",
        rf"\b(?:type|enter|input)\s+(.+?)\s+(?:in|into)\s+(?:the\s+)?{escaped}\b",
    )
    for pattern in patterns:
        m = re.search(pattern, instruction, re.I)
        if m:
            value = clean(m.group(1))
            if value:
                return value
    return None


def decide(state: Mapping[str, Any]):
    if not isinstance(state, Mapping):
        raise ValueError("STATE_NOT_OBJECT")
    instruction = state.get("instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError("INSTRUCTION_REQUIRED")
    if repeated_state(state):
        return {"response": "no progress", "actions": [{"type": "WAIT"}]}

    names, elements = parse_tree(state.get("a11y_tree"))
    in_browser = browser_active(names)
    normalized = norm(instruction)

    if in_browser:
        url = re.search(r"https?://[^\s]+", instruction)
        if url:
            return {"response": "open explicit URL", "actions": [{"type": "BROWSER_OPEN_URL", "url": url.group(0)}]}

        boxes = [e for e in elements if e.editable and ("search" in norm(e.label) or e.tag.endswith("searchbox"))]
        query = search_value(instruction) if "search" in normalized else None
        if len(boxes) == 1 and query:
            return {
                "response": "fill unique search field",
                "actions": [{"type": "BROWSER_FILL", "label": boxes[0].label, "value": query}],
            }

    field = unique_target(instruction, elements, editable=True)
    if field:
        value = field_value(instruction, field.label)
        if value:
            if in_browser:
                return {
                    "response": "fill unique browser field",
                    "actions": [{"type": "BROWSER_FILL", "label": field.label, "value": value}],
                }
            return {
                "response": "fill unique desktop field",
                "actions": [
                    {"type": "CLICK", "x": field.x, "y": field.y},
                    {"type": "TYPE", "text": value},
                ],
            }

    target = unique_target(instruction, elements, editable=False)
    if target and re.search(r"\b(click|press|open|choose|select|check|enable|disable|submit|confirm)\b", normalized):
        return {
            "response": "click unique grounded target",
            "actions": [{"type": "CLICK", "x": target.x, "y": target.y}],
        }

    return {"response": "insufficient grounded evidence", "actions": [{"type": "WAIT"}]}
