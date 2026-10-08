"""Bounded named-container requirement equivalence for spreadsheet tasks.

Recognizes only a deliberately narrow class:
  * source directives requiring a tab/sheet/worksheet with an exact title/name;
  * rubric checks requiring a workbook to contain a tab/sheet/worksheet with that exact title/name.

It normalizes {tab,sheet,worksheet} to WORKSHEET and compares only the explicit
quoted title. It does not infer any other content, ordering, second-tab semantics,
file identity, or general paraphrase entailment.
"""
from __future__ import annotations

import re
from typing import Any, Mapping


SCHEMA = "PROJECT_BRAIN_BOUNDED_NAMED_CONTAINER_EQUIVALENCE_V1"


_SOURCE_PATTERNS = (
    re.compile(
        r"""\b(?:include|put|place|provide|create|add)\b.*?\b(?:in|as)\s+(?:a\s+)?(?:second\s+)?(?:tab|sheet|worksheet)\s+(?:titled|named|called)\s+[\"'‘’“”](?P<title>[^\"'‘’“”]+)[\"'‘’“”]""",
        re.I,
    ),
    re.compile(
        r"""\b(?:create|add|provide)\s+(?:a\s+)?(?:tab|sheet|worksheet)\s+(?:titled|named|called)\s+[\"'‘’“”](?P<title>[^\"'‘’“”]+)[\"'‘’“”]""",
        re.I,
    ),
    re.compile(
        r"""\b(?:tab|sheet|worksheet)\s*\d*\s*:\s*.*?\b(?:titled|named|called)\s+[\"'‘’“”](?P<title>[^\"'‘’“”]+)[\"'‘’“”]""",
        re.I,
    ),
)

_RUBRIC_PATTERNS = (
    re.compile(
        r"""\b(?:workbook|spreadsheet)\b.*?\b(?:contains|includes|has)\b.*?\b(?:worksheet|sheet|tab)\b.*?\b(?:named|titled|called)\s+(?:exactly\s+)?[\"'‘’“”](?P<title>[^\"'‘’“”]+)[\"'‘’“”]""",
        re.I,
    ),
    re.compile(
        r"""\b(?:worksheet|sheet|tab)\b\s+(?:named|titled|called)\s+(?:exactly\s+)?[\"'‘’“”](?P<title>[^\"'‘’“”]+)[\"'‘’“”].*?\b(?:exists|is present)\b""",
        re.I,
    ),
)


def _canon_title(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def _parse(text: str, patterns: tuple[re.Pattern[str], ...], side: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {"status": "FAIL_CLOSED", "reason": f"{side}_TEXT_REQUIRED"}
    for pat in patterns:
        m = pat.search(text)
        if m:
            raw = m.group("title")
            title = _canon_title(raw)
            if not title:
                return {"status": "FAIL_CLOSED", "reason": f"{side}_TITLE_EMPTY"}
            return {
                "status": "RESOLVED",
                "container_type": "WORKSHEET",
                "title": title,
                "title_raw": raw,
                "span": [m.start(), m.end()],
            }
    return {"status": "UNRESOLVED", "reason": f"{side}_OUTSIDE_NAMED_CONTAINER_GRAMMAR"}


def compare(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "PAYLOAD_MAPPING_REQUIRED", "terminal_authority": False}
    source = _parse(payload.get("source_requirement"), _SOURCE_PATTERNS, "SOURCE")
    rubric = _parse(payload.get("rubric_criterion"), _RUBRIC_PATTERNS, "RUBRIC")

    base = {
        "schema": SCHEMA,
        "source": source,
        "rubric": rubric,
        "semantic_scope": "EXACT_NAMED_SPREADSHEET_CONTAINER_EXISTENCE_ONLY",
        "general_paraphrase_authority": False,
        "content_requirement_authority": False,
        "ordering_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if source.get("status") != "RESOLVED" or rubric.get("status") != "RESOLVED":
        return {**base, "status": "UNKNOWN__OUTSIDE_CHECKED_GRAMMAR", "equivalent": None}

    equivalent = (
        source["container_type"] == rubric["container_type"]
        and source["title"] == rubric["title"]
    )
    return {
        **base,
        "status": "PASS__EQUIVALENT_NAMED_CONTAINER_REQUIREMENT" if equivalent else "PASS__DISTINCT_NAMED_CONTAINER_REQUIREMENT",
        "equivalent": equivalent,
        "proved_relation": (
            "SOURCE_REQUIRES_EXISTENCE_OF_WORKSHEET_WITH_EXACT_NORMALIZED_TITLE__"
            "RUBRIC_CHECKS_EXISTENCE_OF_WORKSHEET_WITH_SAME_EXACT_NORMALIZED_TITLE"
            if equivalent else
            "EXPLICIT_NAMED_CONTAINER_TITLES_DIFFER"
        ),
    }
