"""Conservative task-agnostic app-operation overlay for OSWorld 2.1.

This layer is intentionally narrow. It recognizes only explicit generic commands
whose arguments can be extracted without task IDs, benchmark answers, reference
trajectories, hidden evaluator data, or model calls. All other instructions fall
back to the independently verified model-independent V1 policy.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Mapping

from canonical.runtime.osworld_v21_generic_policy_v1 import decide as base_decide

STATE_NS = "https://accessibility.ubuntu.example.org/ns/state"


def _active_app_name(xml_text: Any) -> str:
    if not isinstance(xml_text, str) or not xml_text.strip():
        return ""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ""
    apps = [x for x in list(root) if x.tag.rsplit("}", 1)[-1].lower() == "application"]
    for app in apps:
        if any(child.get(f"{{{STATE_NS}}}active") == "true" for child in list(app)):
            return str(app.get("name") or "").strip().casefold()
    if len(apps) == 1:
        return str(apps[0].get("name") or "").strip().casefold()
    return ""


def _app(name: str) -> str | None:
    s = name.casefold()
    if "writer" in s:
        return "libreoffice_writer"
    if "calc" in s:
        return "libreoffice_calc"
    if "impress" in s:
        return "libreoffice_impress"
    if "visual studio code" in s or s == "code" or "vscode" in s:
        return "code"
    if "vlc" in s:
        return "vlc"
    return None


def _quoted(text: str) -> list[str]:
    return [
        x.strip()
        for x in re.findall(r'["“]([^"”]{1,1000})["”]|\'([^\']{1,1000})\'', text)
        for x in x
        if isinstance(x, str) and x.strip()
    ]


def _first_path(text: str) -> str | None:
    quoted = _quoted(text)
    for value in quoted:
        if value.startswith("/") or value.startswith("file://") or value.startswith("http://") or value.startswith("https://"):
            return value
    m = re.search(r"(?<!\w)(/[^\s,;]+)", text)
    return m.group(1).rstrip(".") if m else None


def _num_after(text: str, phrase: str) -> int | None:
    m = re.search(re.escape(phrase) + r"\s*(?:to\s*)?(\d+)", text, re.I)
    return int(m.group(1)) if m else None


def _app_op(app: str, operation: str, args: Mapping[str, Any] | None = None, response: str = ""):
    return {
        "response": response or f"{app}:{operation}",
        "actions": [{
            "type": "APP_OP",
            "app": app,
            "operation": operation,
            "args": dict(args or {}),
        }],
        "_policy_receipt": {
            "route": "GENERIC_APP_OPERATION_OVERLAY_V1",
            "task_specific_policy_data": False,
            "external_model_dependency": False,
        },
    }


def _writer(instruction: str):
    low = instruction.casefold()
    q = _quoted(instruction)

    if "export" in low and "pdf" in low:
        return _app_op("libreoffice_writer", "export_to_pdf")
    if re.search(r"\bsave\b", low) and "save as" not in low:
        return _app_op("libreoffice_writer", "save")
    m = re.search(r"line\s+spacing\D{0,12}(\d+(?:\.\d+)?)", instruction, re.I)
    if m:
        return _app_op("libreoffice_writer", "set_line_spacing", {"spacing_value": float(m.group(1))})
    m = re.search(r"(?:default\s+font|set\s+the\s+default\s+font).*?(?:to|as)\s+([^,.;]+)", instruction, re.I)
    if m:
        return _app_op("libreoffice_writer", "set_default_font", {"font_name": m.group(1).strip()})
    m = re.search(r"(?:change|set).*?font.*?(?:to|as)\s+([^,.;]+)", instruction, re.I)
    if m and "size" not in low and "default" not in low:
        return _app_op("libreoffice_writer", "set_font", {"font_name": m.group(1).strip()})
    m = re.search(r"(?:align|alignment).*?\b(left|center|right|justify)\b", instruction, re.I)
    if m:
        return _app_op("libreoffice_writer", "set_paragraph_alignment", {"alignment": m.group(1).lower()})
    if "remove" in low and "highlight" in low:
        return _app_op("libreoffice_writer", "remove_highlighting")
    if "capitalize" in low and ("word" in low or "text" in low):
        return _app_op("libreoffice_writer", "capitalize_words")
    if "page break" in low and ("insert" in low or "add" in low):
        pos = "end_of_document" if "end of" in low else "at_cursor"
        return _app_op("libreoffice_writer", "insert_page_break", {"position": pos})
    if "page number" in low and ("add" in low or "insert" in low):
        positions = {
            "bottom left":"bottom_left", "bottom center":"bottom_center", "bottom right":"bottom_right",
            "top left":"top_left", "top center":"top_center", "top right":"top_right",
        }
        pos = next((v for k,v in positions.items() if k in low), None)
        if pos:
            args = {"position": pos}
            start = _num_after(instruction, "start")
            if start is not None:
                args["start_number"] = start
            return _app_op("libreoffice_writer", "add_page_numbers", args)
    if ("find" in low or "replace" in low) and len(q) >= 2:
        return _app_op("libreoffice_writer", "find_and_replace", {"pattern": re.escape(q[0]), "replacement": q[1]})
    m = re.search(r"font\s+size\D{0,12}(\d+(?:\.\d+)?)", instruction, re.I)
    if m and q:
        return _app_op("libreoffice_writer", "set_font_size", {"font_size": float(m.group(1)), "pattern": re.escape(q[0])})
    if "strikethrough" in low and q:
        return _app_op("libreoffice_writer", "set_strikethrough", {"pattern": re.escape(q[0])})
    return None


def _calc(instruction: str):
    low = instruction.casefold()
    q = _quoted(instruction)

    if "export" in low and "csv" in low:
        return _app_op("libreoffice_calc", "export_to_csv")
    if "export" in low and "pdf" in low:
        return _app_op("libreoffice_calc", "export_to_pdf")
    if re.search(r"\bsave\b", low) and "save as" not in low:
        return _app_op("libreoffice_calc", "save")
    m = re.search(r"merge\s+(?:cells?\s+)?([A-Z]+\d+:[A-Z]+\d+)", instruction, re.I)
    if m:
        return _app_op("libreoffice_calc", "merge_cells", {"range_str": m.group(1).upper()})
    m = re.search(r'''(?:set|put|write).*?\b([A-Z]+\d+)\b.*?(?:to|as|=)\s+["']?([^"';]+)''', instruction, re.I)
    if m:
        return _app_op("libreoffice_calc", "set_cell_value", {"cell": m.group(1).upper(), "value": m.group(2).strip()})
    m = re.search(r"sort.*?column\s+([A-Z]+).*?\b(ascending|descending)\b", instruction, re.I)
    if m:
        return _app_op("libreoffice_calc", "sort_column", {"column_name": m.group(1).upper(), "ascending": m.group(2).lower()=="ascending"})
    m = re.search(r'''rename\s+(?:the\s+)?sheet\s+["']?([^"']+?)["']?\s+to\s+["']?([^"']+?)["']?(?:[.;]|$)''', instruction, re.I)
    if m:
        return _app_op("libreoffice_calc", "rename_sheet", {"old_name": m.group(1).strip(), "new_name": m.group(2).strip()})
    m = re.search(r"zoom.*?(\d{2,3})\s*%?", instruction, re.I)
    if m:
        return _app_op("libreoffice_calc", "set_zoom_level", {"zoom_percentage": int(m.group(1))})
    m = re.search(r"transpose\s+([A-Z]+\d+:[A-Z]+\d+).*?(?:to|at)\s+([A-Z]+\d+)", instruction, re.I)
    if m:
        return _app_op("libreoffice_calc", "transpose_range", {"source_range": m.group(1).upper(), "target_cell": m.group(2).upper()})
    m = re.search(r'''(?:switch|go).*?sheet\s+["']?([^"'.;]+)''', instruction, re.I)
    if m:
        return _app_op("libreoffice_calc", "switch_active_sheet", {"sheet_name": m.group(1).strip()})
    return None


def _impress(instruction: str):
    low = instruction.casefold()
    q = _quoted(instruction)

    if re.search(r"\bsave\b", low) and "save as" not in low:
        return _app_op("libreoffice_impress", "save")
    m = re.search(r"(?:go|navigate|switch).*?slide\s+(\d+)", instruction, re.I)
    if m:
        return _app_op("libreoffice_impress", "go_to_slide", {"slide_index": int(m.group(1))})
    m = re.search(r"duplicate\s+(?:slide\s+)?(\d+)", instruction, re.I)
    if m:
        return _app_op("libreoffice_impress", "duplicate_slide", {"slide_index": int(m.group(1))})
    m = re.search(r"(?:orientation).*?\b(landscape|portrait)\b", instruction, re.I)
    if m:
        return _app_op("libreoffice_impress", "set_slide_orientation", {"orientation": m.group(1).lower()})
    if "save as" in low:
        path = _first_path(instruction)
        if path:
            return _app_op("libreoffice_impress", "save_as", {"file_path": path, "overwrite": True})
    if "insert" in low and "image" in low:
        path = _first_path(instruction)
        m = re.search(r"slide\s+(\d+)", instruction, re.I)
        if path and m:
            return _app_op("libreoffice_impress", "insert_image", {"slide_index": int(m.group(1)), "image_path": path})
    return None


def _code(instruction: str):
    low = instruction.casefold()
    q = _quoted(instruction)

    if "update" in low and "extension" in low:
        return _app_op("code", "update_extensions")
    if ("list" in low or "show" in low) and "extension" in low:
        return _app_op("code", "list_extensions")
    m = re.search(r'''(install|uninstall|disable).*?extension\s+["']?([A-Za-z0-9_.-]+)''', instruction, re.I)
    if m:
        op = {"install":"install_extension","uninstall":"uninstall_extension","disable":"disable_extension"}[m.group(1).lower()]
        return _app_op("code", op, {"extension_id": m.group(2)})
    m = re.search(r"(?:sync|synchronization).*?\b(on|off)\b", instruction, re.I)
    if m:
        return _app_op("code", "toggle_sync", {"state": m.group(1).lower()})
    if "compare" in low and len(q) >= 2:
        return _app_op("code", "compare_files", {"file1": q[0], "file2": q[1]})
    path = _first_path(instruction)
    if path and ("open" in low or "launch" in low) and ("code" in low or "vscode" in low or "visual studio" in low):
        return _app_op("code", "launch_vscode", {"path": path})
    return None


def _vlc(instruction: str):
    low = instruction.casefold()
    if re.search(r"\bpause\b", low):
        return _app_op("vlc", "pause")
    if re.search(r"\bplay\b", low) and "playlist" not in low:
        return _app_op("vlc", "play")
    if re.search(r"\bnext\b", low):
        return _app_op("vlc", "next")
    if re.search(r"\bprevious\b|\bprev\b", low):
        return _app_op("vlc", "previous")
    if "fullscreen" in low or "full screen" in low:
        enable = False if ("exit" in low or "disable" in low or "off" in low) else True if ("enable" in low or "enter" in low or "on" in low) else None
        args = {} if enable is None else {"enable": enable}
        return _app_op("vlc", "toggle_fullscreen", args)
    if "playlist" in low and ("add" in low or "open" in low):
        path = _first_path(instruction)
        if path:
            return _app_op("vlc", "add_to_playlist", {"uri": path})
    return None


def decide(state: Mapping[str, Any]) -> Mapping[str, Any]:
    instruction = state.get("instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        return base_decide(state)

    app = _app(_active_app_name(state.get("a11y_tree")))
    route = {
        "libreoffice_writer": _writer,
        "libreoffice_calc": _calc,
        "libreoffice_impress": _impress,
        "code": _code,
        "vlc": _vlc,
    }.get(app)
    if route is not None:
        candidate = route(instruction)
        if candidate is not None:
            return candidate
    return base_decide(state)
