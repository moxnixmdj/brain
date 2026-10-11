"""Deterministic generic OSWorld policy V1.

This is a contamination-safe baseline policy. It consumes only the current user
instruction, current accessibility tree/screenshot identity, and its own prior
receipts. It contains no task IDs, benchmark answers, reference trajectories, or
external model/provider calls.
"""
from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Mapping

STATE_NS = "https://accessibility.ubuntu.example.org/ns/state"
COMP_NS = "https://accessibility.ubuntu.example.org/ns/component"

CLICKABLE_SUFFIXES = (
    "button", "link", "item", "menu", "menuitem", "tab", "tabelement",
    "check-box", "combo-box", "row",
)
EDITABLE_SUFFIXES = ("entry", "searchbox", "textbox", "textfield", "textarea")


class GenericPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class UiElement:
    tag: str
    label: str
    x: int
    y: int
    clickable: bool
    editable: bool


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def _visible(node: ET.Element) -> bool:
    visible = node.get(f"{{{STATE_NS}}}visible")
    showing = node.get(f"{{{STATE_NS}}}showing")
    return visible != "false" and showing != "false"


def _center(node: ET.Element) -> tuple[int, int] | None:
    pos = node.get(f"{{{COMP_NS}}}screencoord")
    size = node.get(f"{{{COMP_NS}}}size")
    if not pos or not size:
        return None
    m1 = re.fullmatch(r"\((-?\d+),\s*(-?\d+)\)", pos)
    m2 = re.fullmatch(r"\((-?\d+),\s*(-?\d+)\)", size)
    if not m1 or not m2:
        return None
    x, y = int(m1.group(1)), int(m1.group(2))
    w, h = int(m2.group(1)), int(m2.group(2))
    if x < 0 or y < 0 or w <= 0 or h <= 0:
        return None
    return x + w // 2, y + h // 2


def parse_a11y(xml_text: str | None) -> list[UiElement]:
    if not isinstance(xml_text, str) or not xml_text.strip():
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    out: list[UiElement] = []
    for node in root.iter():
        if not _visible(node):
            continue
        center = _center(node)
        if center is None:
            continue
        name = str(node.get("name") or "").strip()
        body = str(node.text or "").strip()
        label = name if not body or body == name else (name + " " + body if name else body)
        if not label:
            continue
        tag = node.tag.rsplit("}", 1)[-1].lower()
        out.append(UiElement(
            tag=tag,
            label=label,
            x=center[0],
            y=center[1],
            clickable=any(tag.endswith(x) for x in CLICKABLE_SUFFIXES),
            editable=any(tag.endswith(x) for x in EDITABLE_SUFFIXES),
        ))
    return out


def _quoted(instruction: str) -> list[str]:
    vals = re.findall(r'["“”\']([^"“”\']{1,1000})["“”\']', instruction)
    return [v.strip() for v in vals if v.strip()]


def _unique_exact_target(instruction: str, elements: list[UiElement], *, editable: bool | None = None) -> UiElement | None:
    ni = _norm(instruction)
    candidates: list[UiElement] = []
    for e in elements:
        if editable is True and not e.editable:
            continue
        if editable is False and not e.clickable:
            continue
        nl = _norm(e.label)
        if len(nl) >= 2 and re.search(r"(?<!\w)" + re.escape(nl) + r"(?!\w)", ni):
            candidates.append(e)
    if not candidates:
        return None
    longest = max(len(_norm(x.label)) for x in candidates)
    winners = [x for x in candidates if len(_norm(x.label)) == longest]
    return winners[0] if len(winners) == 1 else None


def _search_value(instruction: str) -> str | None:
    patterns = (
        r"\bsearch(?:\s+for)?\s+["“”']?(.+?)["“”']?(?:\s+(?:and|then)\b|$)",
        r"\btype\s+["“”'](.+?)["“”']",
        r"\benter\s+["“”'](.+?)["“”']",
    )
    for pattern in patterns:
        m = re.search(pattern, instruction, re.I)
        if m:
            value = m.group(1).strip()
            if value:
                return value
    qs = _quoted(instruction)
    return qs[0] if len(qs) == 1 else None


def _fill_value(instruction: str, field: UiElement) -> str | None:
    q = _quoted(instruction)
    nf = _norm(field.label)
    filtered = [x for x in q if _norm(x) != nf]
    if len(filtered) == 1:
        return filtered[0]
    patterns = (
        r"\b(?:enter|type|input)\s+(.+?)\s+(?:in|into)\s+(?:the\s+)?"
        + re.escape(field.label) + r"\b",
        r"\b(?:set|change)\s+(?:the\s+)?" + re.escape(field.label)
        + r"\s+(?:to|as)\s+(.+?)(?:[.;]|$)",
        r"\bfill\s+(?:the\s+)?" + re.escape(field.label)
        + r"\s+with\s+(.+?)(?:[.;]|$)",
    )
    for pattern in patterns:
        m = re.search(pattern, instruction, re.I)
        if m:
            value = m.group(1).strip().strip('"“”\'')
            if value:
                return value
    return None


def _same_state_repeat(state: Mapping[str, Any]) -> bool:
    history = state.get("history")
    if not isinstance(history, list) or not history:
        return False
    last = history[-1]
    return isinstance(last, Mapping) and last.get("screenshot_sha256") == state.get("screenshot_sha256")


def decide(state: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        raise GenericPolicyError("STATE_NOT_OBJECT")
    instruction = state.get("instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        raise GenericPolicyError("INSTRUCTION_REQUIRED")
    elements = parse_a11y(state.get("a11y_tree"))
    ni = _norm(instruction)

    url = re.search(r"https?://[^\s<>\]\[)(']+", instruction)
    if url and not _same_state_repeat(state):
        return {"response": "open explicit URL", "actions": [{"type": "BROWSER_OPEN_URL", "url": url.group(0)}]}

    searchboxes = [e for e in elements if e.editable and ("search" in _norm(e.label) or e.tag.endswith("searchbox"))]
    if re.search(r"\bsearch\b", ni) and len(searchboxes) == 1 and not _same_state_repeat(state):
        value = _search_value(instruction)
        if value:
            return {
                "response": "fill unique search field",
                "actions": [{"type": "BROWSER_FILL", "label": searchboxes[0].label, "value": value}],
            }

    field = _unique_exact_target(instruction, elements, editable=True)
    if field is not None and not _same_state_repeat(state):
        value = _fill_value(instruction, field)
        if value is not None:
            return {
                "response": "fill uniquely grounded field",
                "actions": [{"type": "BROWSER_FILL", "label": field.label, "value": value}],
            }

    target = _unique_exact_target(instruction, elements, editable=False)
    action_verbs = re.search(r"\b(click|press|open|choose|select|check|enable|disable|submit|confirm)\b", ni)
    if target is not None and action_verbs and not _same_state_repeat(state):
        return {
            "response": "click uniquely grounded target",
            "actions": [{"type": "CLICK", "x": target.x, "y": target.y}],
        }

    if _same_state_repeat(state):
        return {"response": "no progress from previous action", "actions": [{"type": "WAIT"}]}

    return {"response": "insufficient grounded evidence", "actions": [{"type": "WAIT"}]}
