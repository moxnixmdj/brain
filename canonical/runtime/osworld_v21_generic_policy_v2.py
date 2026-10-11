"""Contamination-safe generic OSWorld policy baseline V2."""
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


def parse_a11y(xml_text: str | None) -> tuple[list[str], list[UiElement]]:
    if not isinstance(xml_text, str) or not xml_text.strip():
        return [], []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return [], []

    apps: list[str] = []
    out: list[UiElement] = []
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1].lower()
        if tag == "application":
            name = str(node.get("name") or "").strip()
            if name:
                apps.append(name)

        visible = node.get(f"{{{STATE_NS}}}visible")
        showing = node.get(f"{{{STATE_NS}}}showing")
        if visible == "false" or showing == "false":
            continue
        center = _center(node)
        if center is None:
            continue

        name = str(node.get("name") or "").strip()
        body = str(node.text or "").strip()
        label = name if not body or body == name else (name + " " + body if name else body)
        if not label:
            continue

        out.append(UiElement(
            tag=tag,
            label=label,
            x=center[0],
            y=center[1],
            clickable=any(tag.endswith(x) for x in CLICKABLE_SUFFIXES),
            editable=any(tag.endswith(x) for x in EDITABLE_SUFFIXES),
        ))
    return apps, out


def _browser_active(apps: list[str]) -> bool:
    return any(("chrome" in _norm(x) or "chromium" in _norm(x)) for x in apps)


def _same_state_repeat(state: Mapping[str, Any]) -> bool:
    history = state.get("history")
    if not isinstance(history, list) or not history:
        return False
    last = history[-1]
    return isinstance(last, Mapping) and last.get("screenshot_sha256") == state.get("screenshot_sha256")


def _clean_value(value: str) -> str:
    return value.strip().strip(" \t\r\n\"'“”‘’.,;")


def _search_value(instruction: str) -> str | None:
    low = _norm(instruction)
    marker = "search for "
    pos = low.find(marker)
    if pos < 0:
        marker = "search "
        pos = low.find(marker)
    if pos < 0:
        return None
    raw = instruction[pos + len(marker):]
    for sep in (" and then ", " then ", " and "):
        idx = _norm(raw).find(sep.strip())
        if idx >= 0:
            raw = raw[:idx]
            break
    value = _clean_value(raw)
    return value or None


def _unique_target(instruction: str, elements: list[UiElement], *, editable: bool) -> UiElement | None:
    ni = _norm(instruction)
    candidates: list[UiElement] = []
    for e in elements:
        if editable and not e.editable:
            continue
        if not editable and not e.clickable:
            continue
        nl = _norm(e.label)
        if len(nl) < 2:
            continue
        if re.search(r"(?<!\w)" + re.escape(nl) + r"(?!\w)", ni):
            candidates.append(e)
    if not candidates:
        return None
    max_len = max(len(_norm(x.label)) for x in candidates)
    winners = [x for x in candidates if len(_norm(x.label)) == max_len]
    return winners[0] if len(winners) == 1 else None


def _field_value(instruction: str, field_label: str) -> str | None:
    ni = _norm(instruction)
    label = _norm(field_label)
    label_pos = ni.find(label)
    if label_pos < 0:
        return None
    tail = instruction[label_pos + len(field_label):]
    ntail = _norm(tail)
    for marker in (" to ", " with ", " as "):
        pos = ntail.find(marker.strip())
        if pos >= 0:
            raw = tail[pos + len(marker.strip()):]
            value = _clean_value(raw)
            if value:
                return value

    for verb in ("type ", "enter ", "input "):
        p = ni.find(verb)
        if p >= 0:
            segment = instruction[p + len(verb):]
            lower_segment = _norm(segment)
            for marker in (" into ", " in "):
                q = lower_segment.find(marker.strip())
                if q >= 0:
                    value = _clean_value(segment[:q])
                    if value:
                        return value
    return None


def decide(state: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        raise GenericPolicyError("STATE_NOT_OBJECT")
    instruction = state.get("instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        raise GenericPolicyError("INSTRUCTION_REQUIRED")
    if _same_state_repeat(state):
        return {"response": "no progress from previous action", "actions": [{"type": "WAIT"}]}

    apps, elements = parse_a11y(state.get("a11y_tree"))
    browser = _browser_active(apps)
    ni = _norm(instruction)

    url = re.search(r"https?://[^\s<>\]\[)(']+", instruction)
    if browser and url:
        return {"response": "open explicit URL", "actions": [{"type": "BROWSER_OPEN_URL", "url": url.group(0)}]}

    if browser and "search" in ni:
        searchboxes = [
            e for e in elements
            if e.editable and ("search" in _norm(e.label) or e.tag.endswith("searchbox"))
        ]
        value = _search_value(instruction)
        if len(searchboxes) == 1 and value:
            return {
                "response": "fill unique browser search field",
                "actions": [{"type": "BROWSER_FILL", "label": searchboxes[0].label, "value": value}],
            }

    field = _unique_target(instruction, elements, editable=True)
    if field is not None:
        value = _field_value(instruction, field.label)
        if value:
            if browser:
                return {
                    "response": "fill uniquely grounded browser field",
                    "actions": [{"type": "BROWSER_FILL", "label": field.label, "value": value}],
                }
            return {
                "response": "fill uniquely grounded desktop field",
                "actions": [
                    {"type": "CLICK", "x": field.x, "y": field.y},
                    {"type": "TYPE", "text": value},
                ],
            }

    target = _unique_target(instruction, elements, editable=False)
    if target is not None and re.search(
        r"\b(click|press|open|choose|select|check|enable|disable|submit|confirm)\b",
        ni,
    ):
        return {
            "response": "click uniquely grounded target",
            "actions": [{"type": "CLICK", "x": target.x, "y": target.y}],
        }

    return {"response": "insufficient grounded evidence", "actions": [{"type": "WAIT"}]}
