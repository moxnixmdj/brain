"""Deterministic generic OSWorld policy V1.

This is a contamination-safe baseline policy. It consumes only the current user
instruction, current accessibility tree/screenshot identity, and its own prior
receipts. It contains no task IDs, benchmark answers, reference trajectories, or
external model/provider calls.
"""
from __future__ import annotations

import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Mapping

from canonical.runtime.text_ui_grounding_v1 import compile_click_action

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
        r'\bsearch(?:\s+for)?\s+["“”\']?(.+?)["“”\']?(?:\s+(?:and|then)\b|$)',
        r'\btype\s+["“”\'](.+?)["“”\']',
        r'\benter\s+["“”\'](.+?)["“”\']',
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


def _explicit_action_target(instruction: str) -> str | None:
    quoted = _quoted(instruction)
    action = re.search(
        r"\b(click|press|open|choose|select|check|enable|disable|submit|confirm)\b",
        instruction,
        re.I,
    )
    if not action:
        return None
    if quoted:
        # Quoted labels are the strongest explicit target evidence.
        after = [q for q in quoted if instruction.find(q) >= action.end()]
        if len(after) == 1:
            return after[0]
        if len(quoted) == 1:
            return quoted[0]
    tail = instruction[action.end():]
    m = re.match(
        r"\s+(?:the\s+)?(.+?)(?=\s+(?:and|then)\b|[.;]|$)",
        tail,
        re.I,
    )
    if not m:
        return None
    value = m.group(1).strip().strip('"“”\'')
    value = re.sub(
        r"\s+(?:button|link|menu|menu item|tab|item|option)$",
        "",
        value,
        flags=re.I,
    ).strip()
    return value or None


def _ocr_click(instruction: str, ocr: Any) -> dict[str, Any] | None:
    target = _explicit_action_target(instruction)
    if not target or not isinstance(ocr, Mapping):
        return None
    try:
        grounded = compile_click_action(ocr, target, match_mode="exact")
    except Exception:
        return None
    if grounded.get("pass") is not True:
        return None
    point = grounded.get("click_point")
    if not isinstance(point, Mapping):
        return None
    x, y = point.get("x"), point.get("y")
    if not isinstance(x, int) or isinstance(x, bool) or not isinstance(y, int) or isinstance(y, bool):
        return None
    return {
        "response": "click uniquely grounded OCR target",
        "actions": [{"type": "CLICK", "x": x, "y": y}],
    }


def _browser_history(state: Mapping[str, Any]) -> tuple[Mapping[str, Any] | None, Mapping[str, Any] | None]:
    history = state.get("history")
    if not isinstance(history, list):
        return None, None
    for row in reversed(history):
        if not isinstance(row, Mapping):
            continue
        result = row.get("browser_result")
        if isinstance(result, Mapping):
            submitted = row.get("submitted_operation")
            return result, submitted if isinstance(submitted, Mapping) else None
    return None, None


def _recent_browser_submitted(state: Mapping[str, Any], limit: int = 8) -> list[Mapping[str, Any]]:
    history = state.get("history")
    if not isinstance(history, list):
        return []
    out = []
    for row in reversed(history[-limit:]):
        if not isinstance(row, Mapping):
            continue
        submitted = row.get("submitted_operation")
        if isinstance(submitted, Mapping):
            out.append(submitted)
    return out


def _url_equivalent(observed: Any, target: str) -> bool:
    if not isinstance(observed, str):
        return False
    return observed.rstrip("/") == target.rstrip("/")


def _simple_url_goal(instruction: str, url: str) -> bool:
    remainder = instruction.replace(url, " ")
    remainder = re.sub(
        r"\b(?:open|navigate|go|visit|browse|to|the|website|webpage|page|site|url)\b",
        " ",
        remainder,
        flags=re.I,
    )
    remainder = re.sub(r"[^\w]+", " ", remainder).strip()
    return not remainder


def _control_label(control: Mapping[str, Any]) -> str:
    parts = [
        control.get("text"),
        control.get("aria_label"),
        control.get("placeholder"),
        control.get("name"),
    ]
    return " ".join(str(x).strip() for x in parts if isinstance(x, str) and x.strip())


def _unique_control(controls: Any, target: str) -> Mapping[str, Any] | None:
    if not isinstance(controls, list):
        return None
    q = _norm(target)
    exact = []
    for row in controls:
        if not isinstance(row, Mapping):
            continue
        values = [
            row.get("text"),
            row.get("aria_label"),
            row.get("placeholder"),
            row.get("name"),
        ]
        normalized = {_norm(str(v)) for v in values if isinstance(v, str) and v.strip()}
        if q in normalized:
            exact.append(row)
    return exact[0] if len(exact) == 1 else None


def _browser_click_action(control: Mapping[str, Any], target: str) -> dict[str, Any]:
    role = control.get("role")
    aria = control.get("aria_label")
    text = control.get("text")
    if isinstance(role, str) and role.strip():
        name = aria if isinstance(aria, str) and aria.strip() else text
        if isinstance(name, str) and name.strip():
            return {
                "type": "BROWSER_OP",
                "op": {
                    "type": "CLICK_ROLE",
                    "role": role.strip(),
                    "name": name.strip(),
                    "exact": True,
                },
            }
    label = text if isinstance(text, str) and text.strip() else target
    return {
        "type": "BROWSER_OP",
        "op": {"type": "CLICK_TEXT", "text": label.strip(), "exact": True},
    }


def _browser_search_control(controls: Any) -> Mapping[str, Any] | None:
    if not isinstance(controls, list):
        return None
    hits = []
    for row in controls:
        if not isinstance(row, Mapping):
            continue
        label = _norm(_control_label(row))
        typ = _norm(str(row.get("type") or ""))
        if "search" in label or typ == "search":
            hits.append(row)
    return hits[0] if len(hits) == 1 else None


def _browser_fill_action(control: Mapping[str, Any], value: str) -> dict[str, Any] | None:
    placeholder = control.get("placeholder")
    aria = control.get("aria_label")
    if isinstance(placeholder, str) and placeholder.strip():
        return {
            "type": "BROWSER_OP",
            "op": {
                "type": "FILL_PLACEHOLDER",
                "placeholder": placeholder.strip(),
                "value": value,
                "exact": True,
            },
        }
    if isinstance(aria, str) and aria.strip():
        return {
            "type": "BROWSER_OP",
            "op": {
                "type": "FILL_LABEL",
                "label": aria.strip(),
                "value": value,
                "exact": True,
            },
        }
    return None


def _browser_state_machine(state: Mapping[str, Any], instruction: str) -> dict[str, Any] | None:
    result, submitted = _browser_history(state)
    url_match = re.search(r"https?://[^\s<>\]\[)(']+", instruction)
    target_url = url_match.group(0) if url_match else None

    if target_url:
        result_type = str((result or {}).get("type") or "").upper()
        observed_url = (result or {}).get("active_url") or (result or {}).get("url")
        if _url_equivalent(observed_url, target_url):
            if result_type == "OBSERVE" and _simple_url_goal(instruction, target_url):
                return {"response": "explicit URL goal verified", "actions": [{"type": "DONE"}]}
            if result_type != "OBSERVE":
                return {
                    "response": "observe navigated page",
                    "actions": [{"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}],
                }
        elif not (
            isinstance(submitted, Mapping)
            and str(submitted.get("type") or "").upper() == "NAVIGATE"
            and submitted.get("url") == target_url
        ):
            return {
                "response": "open explicit URL",
                "actions": [{"type": "BROWSER_OP", "op": {"type": "NAVIGATE", "url": target_url}}],
            }

    if isinstance(submitted, Mapping):
        submitted_type = str(submitted.get("type") or "").upper()

        if re.search(r"\bsearch\b", instruction, re.I) and submitted_type in {
            "FILL_LABEL", "FILL_PLACEHOLDER", "FILL_SELECTOR"
        }:
            return {
                "response": "submit filled search",
                "actions": [{"type": "BROWSER_OP", "op": {"type": "PRESS", "key": "Enter"}}],
            }

        if submitted_type in {
            "NAVIGATE", "CLICK_TEXT", "CLICK_ROLE", "CLICK_SELECTOR",
            "FILL_LABEL", "FILL_PLACEHOLDER", "FILL_SELECTOR",
            "PRESS", "PRESS_SELECTOR", "SELECT_LABEL", "SELECT_SELECTOR",
            "CHECK_SELECTOR", "UNCHECK_SELECTOR",
        } and str((result or {}).get("type") or "").upper() != "OBSERVE":
            return {
                "response": "observe browser after mutation",
                "actions": [{"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}],
            }

    if isinstance(result, Mapping) and str(result.get("type") or "").upper() == "OBSERVE":
        controls = result.get("controls")

        if re.search(r"\bsearch\b", instruction, re.I):
            value = _search_value(instruction)
            if value:
                recent = _recent_browser_submitted(state)
                recent_types = [str(x.get("type") or "").upper() for x in recent]
                if "PRESS" in recent_types and any(
                    t in {"FILL_LABEL", "FILL_PLACEHOLDER", "FILL_SELECTOR"}
                    for t in recent_types
                ):
                    visible = _norm(str(result.get("visible_text") or ""))
                    if _norm(value) in visible:
                        return {
                            "response": "search result state observed",
                            "actions": [{"type": "DONE"}],
                        }
                    return None
                control = _browser_search_control(controls)
                if control is not None:
                    action = _browser_fill_action(control, value)
                    if action is not None:
                        return {"response": "fill uniquely observed search field", "actions": [action]}

        target = _explicit_action_target(instruction)
        if target:
            control = _unique_control(controls, target)
            if control is not None:
                return {
                    "response": "activate uniquely observed browser control",
                    "actions": [_browser_click_action(control, target)],
                }

    browser_terms = re.search(r"\b(browser|chrome|website|webpage|web page|site|tab)\b", instruction, re.I)
    if browser_terms and result is None:
        return {
            "response": "observe browser semantic state",
            "actions": [{"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}],
        }
    return None


_TEXT_FILE_EXTENSIONS = ("txt", "md", "csv", "json")
_DEFAULT_SHARE_ROOT = "/home/oai/share"


def _explicit_file_name(instruction: str) -> str | None:
    ext = "|".join(_TEXT_FILE_EXTENSIONS)
    quoted = re.findall(
        rf'["“”\']([^"“”\']+\.(?:{ext}))["“”\']',
        instruction,
        flags=re.I,
    )
    if len(quoted) == 1:
        return quoted[0].strip()
    absolute = re.findall(
        rf'(/[^\s"“”\']+\.(?:{ext}))',
        instruction,
        flags=re.I,
    )
    if len(absolute) == 1:
        return absolute[0].strip()
    tokens = re.findall(
        rf'(?<![\w.-])([A-Za-z0-9][A-Za-z0-9_.-]*\.(?:{ext}))(?![\w.-])',
        instruction,
        flags=re.I,
    )
    unique = []
    for value in tokens:
        if value.casefold() not in {x.casefold() for x in unique}:
            unique.append(value)
    return unique[0] if len(unique) == 1 else None


def _latest_guest_receipt(state: Mapping[str, Any]) -> tuple[Mapping[str, Any] | None, list[Mapping[str, Any]]]:
    history = state.get("history")
    if not isinstance(history, list):
        return None, []
    for row in reversed(history):
        if not isinstance(row, Mapping):
            continue
        result = row.get("guest_result")
        if isinstance(result, Mapping):
            submitted = row.get("submitted_operations")
            ops = [x for x in submitted if isinstance(x, Mapping)] if isinstance(submitted, list) else []
            return result, ops
    return None, []


def _listing_rows(output: str, root: str = _DEFAULT_SHARE_ROOT) -> list[Mapping[str, Any]] | None:
    prefix = "LIST_DIR:PASS:" + root + ":"
    for line in output.splitlines():
        if line.startswith(prefix):
            raw = line[len(prefix):]
            try:
                value = json.loads(raw)
            except Exception:
                return None
            if isinstance(value, list):
                return [x for x in value if isinstance(x, Mapping)]
    return None


def _resolved_text_path(instruction: str, filename: str, guest_result: Mapping[str, Any] | None) -> str | None:
    if filename.startswith("/"):
        return filename
    output = str((guest_result or {}).get("output") or "")
    rows = _listing_rows(output)
    if rows is not None:
        matches = [
            str(row.get("path"))
            for row in rows
            if isinstance(row.get("name"), str)
            and str(row.get("name")).casefold() == filename.casefold()
            and row.get("is_file") is True
        ]
        if len(matches) == 1:
            return matches[0]
        return None
    if re.search(r"\b(create|write|make|save)\b", instruction, re.I):
        return _DEFAULT_SHARE_ROOT + "/" + filename
    return None


def _quoted_values_excluding_filename(instruction: str, filename: str) -> list[str]:
    values = _quoted(instruction)
    return [x for x in values if _norm(x) != _norm(filename)]


def _file_state_machine(state: Mapping[str, Any], instruction: str) -> dict[str, Any] | None:
    filename = _explicit_file_name(instruction)
    if not filename:
        return None
    guest_result, submitted = _latest_guest_receipt(state)
    output = str((guest_result or {}).get("output") or "")

    if filename.casefold() in output.casefold() and (
        "ASSERT_TEXT_EQUALS:PASS:" in output
        or "ASSERT_TEXT_CONTAINS:PASS:" in output
    ):
        return {"response": "file postcondition verified", "actions": [{"type": "DONE"}]}

    path = _resolved_text_path(instruction, filename, guest_result)
    quoted = _quoted_values_excluding_filename(instruction, filename)

    if re.search(r"\breplace\b", instruction, re.I) and re.search(r"\bwith\b", instruction, re.I):
        if path is None:
            if _listing_rows(output) is None:
                return {
                    "response": "discover target file",
                    "actions": [{
                        "type": "STATE_OPS",
                        "ops": [{"type": "LIST_DIR", "path": _DEFAULT_SHARE_ROOT, "max_entries": 200}],
                    }],
                }
            return None
        if len(quoted) == 2:
            old, new = quoted
            return {
                "response": "perform exact text replacement and verify",
                "actions": [{
                    "type": "STATE_OPS",
                    "ops": [
                        {
                            "type": "TEXT_REPLACE",
                            "path": path,
                            "old": old,
                            "new": new,
                            "replace_all": True,
                        },
                        {"type": "ASSERT_TEXT_CONTAINS", "path": path, "text": new},
                    ],
                }],
            }
        return None

    create_like = re.search(r"\b(create|write|make|save)\b", instruction, re.I)
    content_signal = re.search(r"\b(containing|contains|content|contents|text|with)\b", instruction, re.I)
    if create_like and content_signal and path is not None and len(quoted) == 1:
        value = quoted[0]
        return {
            "response": "write explicit file content and verify",
            "actions": [{
                "type": "STATE_OPS",
                "ops": [
                    {"type": "WRITE_TEXT", "path": path, "text": value},
                    {"type": "ASSERT_TEXT_EQUALS", "path": path, "text": value},
                ],
            }],
        }
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
    file_action = _file_state_machine(state, instruction)
    if file_action is not None:
        return file_action

    elements = parse_a11y(state.get("a11y_tree"))
    ni = _norm(instruction)

    browser_action = _browser_state_machine(state, instruction)
    if browser_action is not None:
        return browser_action

    searchboxes = [e for e in elements if e.editable and ("search" in _norm(e.label) or e.tag.endswith("searchbox"))]
    if re.search(r"\bsearch\b", ni) and len(searchboxes) == 1 and not _same_state_repeat(state):
        value = _search_value(instruction)
        if value:
            return {
                "response": "fill unique search field",
                "actions": [{"type": "BROWSER_OP", "op": {"type": "FILL_LABEL", "label": searchboxes[0].label, "value": value}}],
            }

    field = _unique_exact_target(instruction, elements, editable=True)
    if field is not None and not _same_state_repeat(state):
        value = _fill_value(instruction, field)
        if value is not None:
            return {
                "response": "fill uniquely grounded field",
                "actions": [{"type": "BROWSER_OP", "op": {"type": "FILL_LABEL", "label": field.label, "value": value}}],
            }

    target = _unique_exact_target(instruction, elements, editable=False)
    action_verbs = re.search(r"\b(click|press|open|choose|select|check|enable|disable|submit|confirm)\b", ni)
    if target is not None and action_verbs and not _same_state_repeat(state):
        return {
            "response": "click uniquely grounded target",
            "actions": [{"type": "CLICK", "x": target.x, "y": target.y}],
        }

    if action_verbs and not _same_state_repeat(state):
        ocr_action = _ocr_click(instruction, state.get("ocr"))
        if ocr_action is not None:
            return ocr_action

    if _same_state_repeat(state):
        return {"response": "no progress from previous action", "actions": [{"type": "WAIT"}]}

    return {"response": "insufficient grounded evidence", "actions": [{"type": "WAIT"}]}
