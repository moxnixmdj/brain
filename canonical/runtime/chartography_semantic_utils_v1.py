from __future__ import annotations

import math
import re
from typing import Any, Iterable, Mapping

_NUM = re.compile(r"(?<![A-Za-z0-9])([+\\-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+))(?![A-Za-z0-9])")


class ChartSemanticUtilityError(ValueError):
    pass


def prompt_numbers(text: str) -> list[float]:
    out: list[float] = []
    for match in _NUM.finditer(text.replace("−", "-")):
        try:
            value = float(match.group(1))
        except ValueError:
            continue
        if math.isfinite(value):
            out.append(value)
    return out


def numeric_overlap(left: Iterable[float], right: Iterable[float]) -> int:
    candidates = list(right)
    used: set[int] = set()
    count = 0
    for a in left:
        for index, b in enumerate(candidates):
            if index in used:
                continue
            tolerance = max(1e-8, 1e-4 * max(1.0, abs(a), abs(b)))
            if abs(a - b) <= tolerance:
                used.add(index)
                count += 1
                break
    return count


def line_groups(words: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
    for word in words:
        key = (word.get("block_num"), word.get("par_num"), word.get("line_num"))
        groups.setdefault(key, []).append(dict(word))
    out = []
    for group in groups.values():
        ordered = sorted(group, key=lambda row: float(row["left"]))
        left = min(float(row["left"]) for row in ordered)
        top = min(float(row["top"]) for row in ordered)
        right = max(float(row["left"]) + float(row["width"]) for row in ordered)
        bottom = max(float(row["top"]) + float(row["height"]) for row in ordered)
        out.append({
            "text": " ".join(str(row["text"]) for row in ordered),
            "words": ordered,
            "bbox": [left, top, right, bottom],
            "cy": (top + bottom) / 2.0,
        })
    return out


def format_requested_rounding(prompt: str, value: float) -> str:
    low = prompt.lower()
    match = re.search(r"(\\d+)\\s*decimal place", low)
    if match:
        return f"{value:.{int(match.group(1))}f}"
    if "nearest 10" in low or "nearest ten" in low:
        return str(int(round(value / 10.0) * 10))
    if "nearest integer" in low or "nearest whole" in low:
        return str(int(round(value)))
    return format(value, ".6g")
