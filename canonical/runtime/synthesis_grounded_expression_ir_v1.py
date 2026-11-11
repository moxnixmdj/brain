"""Deterministic grounded-expression and constraint-realization route.

C2 boundary:
- upstream supplies already selected, source-grounded semantic content;
- this module does not decide truth, relevance, or source authority;
- it realizes that content without dropping or rewriting material content;
- unsupported constraints fail closed instead of being silently ignored.

This is a bounded owned mechanism candidate, not general writing parity.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SYNTHESIS_GROUNDED_EXPRESSION_IR_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_SYNTHESIS_C2_INPUT_V1"

_KINDS = {"CLAIM", "UNCERTAINTY", "CONFLICT"}
_FORMATS = {"BULLETS", "PARAGRAPHS", "SECTIONED_MARKDOWN"}
_ALLOWED_CONSTRAINT_KEYS = {
    "output_format",
    "citation_mode",
    "item_order",
    "required_sections",
    "allowed_sections",
    "max_items",
    "max_chars",
    "heading_level",
    "require_title",
    "style",
}
_SAFE_SOURCE = re.compile(r"^[A-Za-z0-9._:/-]+$")
_SAFE_LOCATOR = re.compile(r"^[^\[\]\n\r;@]{1,160}$")
_RESERVED_CITATION_MARKER = re.compile(r"\[src:", re.IGNORECASE)


def _fail(reason: str, *, details: Any = None) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "terminal_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
    if details is not None:
        out["details"] = details
    return out


def _clean_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + "_REQUIRED")
    if "\n" in value or "\r" in value:
        raise ValueError(label + "_MULTILINE_FORBIDDEN")
    return value.strip()


def _normalize_provenance(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError("PROVENANCE_REQUIRED")
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in value:
        if not isinstance(row, Mapping):
            raise ValueError("PROVENANCE_ROW_INVALID")
        source_id = _clean_text(row.get("source_id"), "SOURCE_ID")
        if not _SAFE_SOURCE.fullmatch(source_id):
            raise ValueError("SOURCE_ID_UNSAFE")
        locator_raw = row.get("locator")
        locator = ""
        if locator_raw is not None:
            locator = _clean_text(locator_raw, "LOCATOR")
            if not _SAFE_LOCATOR.fullmatch(locator):
                raise ValueError("LOCATOR_UNSAFE")
        key = (source_id, locator)
        if key in seen:
            continue
        seen.add(key)
        item = {"source_id": source_id}
        if locator:
            item["locator"] = locator
        out.append(item)
    if not out:
        raise ValueError("PROVENANCE_REQUIRED")
    return out


def _citation(provenance: Sequence[Mapping[str, str]]) -> str:
    parts = []
    for row in provenance:
        source_id = row["source_id"]
        locator = row.get("locator")
        parts.append(source_id + ("@" + locator if locator else ""))
    return "[src:" + ";".join(parts) + "]"


def _normalize_item(row: Any) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise ValueError("ITEM_INVALID")
    item_id = _clean_text(row.get("id"), "ITEM_ID")
    if not _SAFE_SOURCE.fullmatch(item_id):
        raise ValueError("ITEM_ID_UNSAFE")
    kind = _clean_text(row.get("kind"), "KIND").upper()
    if kind not in _KINDS:
        raise ValueError("KIND_UNSUPPORTED")
    text = _clean_text(row.get("text"), "TEXT")
    if _RESERVED_CITATION_MARKER.search(text):
        raise ValueError("TEXT_RESERVED_CITATION_MARKER")
    provenance = _normalize_provenance(row.get("provenance"))
    section_raw = row.get("section")
    section = None
    if section_raw is not None:
        section = _clean_text(section_raw, "SECTION")
        if "#" in section or _RESERVED_CITATION_MARKER.search(section):
            raise ValueError("SECTION_UNSAFE")
    return {
        "id": item_id,
        "kind": kind,
        "text": text,
        "provenance": provenance,
        "section": section,
    }


def _normalize_constraints(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("CONSTRAINTS_REQUIRED")
    unknown = sorted(set(value) - _ALLOWED_CONSTRAINT_KEYS)
    if unknown:
        raise ValueError("UNSUPPORTED_CONSTRAINT:" + ",".join(unknown))

    output_format = str(value.get("output_format") or "").upper()
    if output_format not in _FORMATS:
        raise ValueError("OUTPUT_FORMAT_UNSUPPORTED")

    citation_mode = str(value.get("citation_mode") or "").upper()
    if citation_mode != "INLINE_SOURCE_IDS":
        raise ValueError("CITATION_MODE_UNSUPPORTED")

    style = str(value.get("style") or "").upper()
    if style != "VERBATIM_GROUNDED":
        raise ValueError("STYLE_UNSUPPORTED")

    item_order = value.get("item_order", "INPUT")
    if item_order != "INPUT":
        if not isinstance(item_order, Sequence) or isinstance(item_order, (str, bytes)):
            raise ValueError("ITEM_ORDER_INVALID")
        item_order = [_clean_text(x, "ORDER_ITEM_ID") for x in item_order]

    required_sections = value.get("required_sections", [])
    allowed_sections = value.get("allowed_sections")
    if not isinstance(required_sections, Sequence) or isinstance(required_sections, (str, bytes)):
        raise ValueError("REQUIRED_SECTIONS_INVALID")
    required_sections = [_clean_text(x, "REQUIRED_SECTION") for x in required_sections]
    if allowed_sections is not None:
        if not isinstance(allowed_sections, Sequence) or isinstance(allowed_sections, (str, bytes)):
            raise ValueError("ALLOWED_SECTIONS_INVALID")
        allowed_sections = [_clean_text(x, "ALLOWED_SECTION") for x in allowed_sections]

    if "max_items" not in value:
        raise ValueError("MAX_ITEMS_REQUIRED")
    max_items_raw = value.get("max_items")
    if isinstance(max_items_raw, bool) or not isinstance(max_items_raw, int):
        raise ValueError("MAX_ITEMS_INVALID")
    max_items = max_items_raw
    if max_items < 0:
        raise ValueError("MAX_ITEMS_INVALID")

    max_chars_raw = value.get("max_chars")
    max_chars = None
    if max_chars_raw is not None:
        if isinstance(max_chars_raw, bool) or not isinstance(max_chars_raw, int):
            raise ValueError("MAX_CHARS_INVALID")
        max_chars = max_chars_raw
        if max_chars <= 0:
            raise ValueError("MAX_CHARS_INVALID")

    heading_level_raw = value.get("heading_level", 2)
    if isinstance(heading_level_raw, bool) or not isinstance(heading_level_raw, int):
        raise ValueError("HEADING_LEVEL_INVALID")
    heading_level = heading_level_raw
    if not 1 <= heading_level <= 6:
        raise ValueError("HEADING_LEVEL_INVALID")

    require_title = value.get("require_title", False)
    if not isinstance(require_title, bool):
        raise ValueError("REQUIRE_TITLE_INVALID")

    section_controls_active = (
        bool(required_sections)
        or allowed_sections is not None
        or "heading_level" in value
    )
    if output_format != "SECTIONED_MARKDOWN" and section_controls_active:
        raise ValueError("SECTION_CONSTRAINTS_REQUIRE_SECTIONED_MARKDOWN")

    return {
        "output_format": output_format,
        "citation_mode": citation_mode,
        "style": style,
        "item_order": item_order,
        "required_sections": list(required_sections),
        "allowed_sections": None if allowed_sections is None else list(allowed_sections),
        "max_items": max_items,
        "max_chars": max_chars,
        "heading_level": heading_level,
        "require_title": require_title,
    }


def _ordered_items(items: list[dict[str, Any]], order: Any) -> list[dict[str, Any]]:
    if order == "INPUT":
        return list(items)
    ids = [x["id"] for x in items]
    if len(order) != len(ids) or len(set(order)) != len(order) or set(order) != set(ids):
        raise ValueError("ITEM_ORDER_MUST_BE_EXACT_PERMUTATION")
    by_id = {x["id"]: x for x in items}
    return [by_id[x] for x in order]


def _render_item(item: Mapping[str, Any], bullet: bool) -> tuple[str, str]:
    prefix = ""
    if item["kind"] == "UNCERTAINTY":
        prefix = "Uncertainty: "
    elif item["kind"] == "CONFLICT":
        prefix = "Conflict: "
    citation = _citation(item["provenance"])
    body = prefix + item["text"] + " " + citation
    return ("- " + body if bullet else body), body


def solve(public: Mapping[str, Any]) -> dict[str, Any]:
    """Realize grounded selected content under the bounded C2 constraint language."""
    try:
        if not isinstance(public, Mapping) or public.get("schema") != INPUT_SCHEMA:
            return _fail("INPUT_SCHEMA")
        task = public.get("task")
        if not isinstance(task, Mapping):
            return _fail("TASK_REQUIRED")

        raw_items = task.get("items")
        if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)) or not raw_items:
            return _fail("ITEMS_REQUIRED")
        items = [_normalize_item(x) for x in raw_items]
        ids = [x["id"] for x in items]
        if len(ids) != len(set(ids)):
            return _fail("DUPLICATE_ITEM_IDS")

        constraints = _normalize_constraints(task.get("constraints"))
        if len(items) > constraints["max_items"]:
            return _fail("MAX_ITEMS_INFEASIBLE__NO_CONTENT_DROPPED")

        title = task.get("title")
        if title is not None:
            title = _clean_text(title, "TITLE")
            if _RESERVED_CITATION_MARKER.search(title):
                return _fail("TITLE_RESERVED_CITATION_MARKER")
        if constraints["require_title"] and title is None:
            return _fail("TITLE_REQUIRED")

        items = _ordered_items(items, constraints["item_order"])

        sections = [x["section"] for x in items if x["section"] is not None]
        if constraints["output_format"] == "SECTIONED_MARKDOWN" and any(x["section"] is None for x in items):
            return _fail("SECTION_REQUIRED_FOR_SECTIONED_MARKDOWN")
        missing_sections = [x for x in constraints["required_sections"] if x not in set(sections)]
        if missing_sections:
            return _fail("REQUIRED_SECTION_MISSING", details=missing_sections)
        if constraints["allowed_sections"] is not None:
            disallowed = sorted(set(sections) - set(constraints["allowed_sections"]))
            if disallowed:
                return _fail("SECTION_NOT_ALLOWED", details=disallowed)

        lines: list[str] = []
        trace: list[dict[str, Any]] = []
        fmt = constraints["output_format"]
        if title is not None:
            if fmt == "SECTIONED_MARKDOWN":
                title_level = max(1, constraints["heading_level"] - 1)
                lines.extend(["#" * title_level + " " + title, ""])
            else:
                lines.extend([title, ""])

        if fmt == "BULLETS":
            for item in items:
                rendered, body = _render_item(item, True)
                lines.append(rendered)
                trace.append({
                    "item_id": item["id"],
                    "kind": item["kind"],
                    "source_text": item["text"],
                    "rendered_body": body,
                    "provenance": item["provenance"],
                })
        elif fmt == "PARAGRAPHS":
            for index, item in enumerate(items):
                rendered, body = _render_item(item, False)
                if index:
                    lines.append("")
                lines.append(rendered)
                trace.append({
                    "item_id": item["id"],
                    "kind": item["kind"],
                    "source_text": item["text"],
                    "rendered_body": body,
                    "provenance": item["provenance"],
                })
        else:
            # Preserve the already-selected exact item order.  If a section
            # recurs non-contiguously, repeat its heading rather than silently
            # regrouping items and changing salience/order semantics.
            active_section = None
            for item in items:
                section = item["section"]
                if section != active_section:
                    if lines and lines[-1] != "":
                        lines.append("")
                    lines.append("#" * constraints["heading_level"] + " " + section)
                    lines.append("")
                    active_section = section
                rendered, body = _render_item(item, True)
                lines.append(rendered)
                trace.append({
                    "item_id": item["id"],
                    "kind": item["kind"],
                    "source_text": item["text"],
                    "rendered_body": body,
                    "provenance": item["provenance"],
                    "section": section,
                })

        rendered_text = "\n".join(lines).rstrip()
        max_chars = constraints["max_chars"]
        if max_chars is not None and len(rendered_text) > max_chars:
            return _fail(
                "MAX_CHARS_INFEASIBLE__NO_CONTENT_TRUNCATED",
                details={"required_chars": len(rendered_text), "max_chars": max_chars},
            )

        rendered_ids = [x["item_id"] for x in trace]
        if rendered_ids != [x["id"] for x in items]:
            return _fail("INTERNAL_ITEM_PRESERVATION_FAILURE")

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "rendered_text": rendered_text,
            "trace": trace,
            "audit": {
                "input_item_count": len(items),
                "rendered_item_count": len(trace),
                "dropped_item_count": 0,
                "rewritten_material_item_count": 0,
                "new_material_claim_count": 0,
                "all_items_provenance_bound": True,
                "uncertainty_conflict_state_rendered": True,
                "constraints_interpreted_without_unknown_keys": True,
                "format": fmt,
                "style": "VERBATIM_GROUNDED",
            },
            "scope": "BOUNDED_SELECTED_SOURCE_GROUNDED_CONTENT_TO_VERBATIM_TEXT_OR_MARKDOWN_REALIZATION",
            "terminal_authority": False,
            "promotion_authority": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }
    except ValueError as exc:
        return _fail(str(exc))
