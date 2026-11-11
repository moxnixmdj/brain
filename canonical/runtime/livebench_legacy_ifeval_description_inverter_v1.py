#!/usr/bin/env python3
"""Prompt-only inverter for the exact frozen legacy IFEval description grammar.

Source binding:
  LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091
  livebench/if_runner/instruction_following_eval/instructions.py
    blob 4997bab885a676d92545fd91a9a20b48d234a2b2
  livebench/if_runner/instruction_following_eval/instructions_registry.py
    blob 903ed738398648c7cfac61d5ffa478c22f1f0891

Runtime recognition consumes only the visible prompt. It never receives hidden kwargs,
instruction_id_list, question ids, or terminal answers.
"""
from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_IFEVAL_DESCRIPTION_INVERTER_V1"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LEGACY_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
LEGACY_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"

LANGUAGE_NAME_TO_CODE = {
    "English": "en", "Spanish": "es", "Portuguese": "pt", "Arabic": "ar",
    "Hindi": "hi", "French": "fr", "Russian": "ru", "German": "de",
    "Japanese": "ja", "Italian": "it", "Bengali": "bn", "Ukrainian": "uk",
    "Thai": "th", "Urdu": "ur", "Tamil": "ta", "Telugu": "te",
    "Bulgarian": "bg", "Korean": "ko", "Polish": "pl", "Hebrew": "he",
    "Persian": "fa", "Vietnamese": "vi", "Nepali": "ne", "Swahili": "sw",
    "Kannada": "kn", "Marathi": "mr", "Gujarati": "gu", "Punjabi": "pa",
    "Malayalam": "ml", "Finnish": "fi",
}

@dataclass(frozen=True)
class Match:
    instruction_id: str
    start: int
    end: int
    matched_text: str
    slots: dict[str, Any]
    route: str = "PINNED_SOURCE_TEMPLATE"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE | re.DOTALL)


PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "keywords:existence": (
        _rx(r"Include\s+keywords\s+(?P<keywords>\[[^\]]*\])\s+in\s+the\s+response\."),
    ),
    "keywords:frequency": (
        _rx(r"In\s+your\s+response,\s+the\s+word\s+(?P<keyword>.+?)\s+should\s+appear\s+(?P<relation>less\s+than|at\s+least)\s+(?P<frequency>\d+)\s+times\."),
    ),
    "keywords:forbidden_words": (
        _rx(r"Do\s+not\s+include\s+keywords\s+(?P<forbidden_words>\[[^\]]*\])\s+in\s+the\s+response\."),
    ),
    "keywords:letter_frequency": (
        _rx(r"In\s+your\s+response,\s+the\s+letter\s+(?P<letter>[A-Za-z])\s+should\s+appear\s+(?P<relation>less\s+than|at\s+least)\s+(?P<frequency>\d+)\s+times\."),
    ),
    "language:response_language": (
        _rx(r"Your\s+ENTIRE\s+response\s+should\s+be\s+in\s+(?P<language_name>[A-Za-z]+)\s+language,\s+no\s+other\s+language\s+is\s+allowed\."),
    ),
    "length_constraints:number_sentences": (
        _rx(r"Your\s+response\s+should\s+contain\s+(?P<relation>less\s+than|at\s+least)\s+(?P<num_sentences>\d+)\s+sentences\."),
    ),
    "length_constraints:number_paragraphs": (
        _rx(r"There\s+should\s+be\s+(?P<num_paragraphs>\d+)\s+paragraphs\.\s+Paragraphs\s+are\s+separated\s+with\s+the\s+markdown\s+divider:\s*\*\*\*"),
    ),
    "length_constraints:number_words": (
        _rx(r"Answer\s+with\s+(?P<relation>less\s+than|at\s+least)\s+(?P<num_words>\d+)\s+words\."),
    ),
    "length_constraints:nth_paragraph_first_word": (
        _rx(r"There\s+should\s+be\s+(?P<num_paragraphs>\d+)\s+paragraphs\.\s+Paragraphs\s+and\s+only\s+paragraphs\s+are\s+separated\s+with\s+each\s+other\s+by\s+two\s+new\s+lines\s+as\s+if\s+it\s+was\s+'\\n\\n'\s+in\s+python\.\s+Paragraph\s+(?P<nth_paragraph>\d+)\s+must\s+start\s+with\s+word\s+(?P<first_word>[^\s.]+)\."),
    ),
    "detectable_content:number_placeholders": (
        _rx(r"The\s+response\s+must\s+contain\s+at\s+least\s+(?P<num_placeholders>\d+)\s+placeholders\s+represented\s+by\s+square\s+brackets,\s+such\s+as\s+\[address\]\."),
    ),
    "detectable_content:postscript": (
        _rx(r"At\s+the\s+end\s+of\s+your\s+response,\s+please\s+explicitly\s+add\s+a\s+postscript\s+starting\s+with\s+(?P<postscript>\S+)"),
    ),
    "detectable_format:number_bullet_lists": (
        _rx(r"Your\s+answer\s+must\s+contain\s+exactly\s+(?P<num_bullets>\d+)\s+bullet\s+points\.\s+Use\s+the\s+markdown\s+bullet\s+points\s+such\s+as:"),
    ),
    "detectable_format:constrained_response": (
        _rx(r"Answer\s+with\s+one\s+of\s+the\s+following\s+options:\s*\('My answer is yes\.',\s*'My answer is no\.',\s*'My answer is maybe\.'\)"),
    ),
    "detectable_format:number_highlighted_sections": (
        _rx(r"Highlight\s+at\s+least\s+(?P<num_highlights>\d+)\s+sections\s+in\s+your\s+answer\s+with\s+markdown,\s+i\.e\.\s+\*highlighted\s+section\*\."),
    ),
    "detectable_format:multiple_sections": (
        _rx(r"Your\s+response\s+must\s+have\s+(?P<num_sections>\d+)\s+sections\.\s+Mark\s+the\s+beginning\s+of\s+each\s+section\s+with\s+(?P<section_splitter>Section|SECTION)\s+X,\s+such\s+as:"),
    ),
    "detectable_format:json_format": (
        _rx(r"Entire\s+output\s+should\s+be\s+wrapped\s+in\s+JSON\s+format\.\s+You\s+can\s+use\s+markdown\s+ticks\s+such\s+as\s+...\."),
    ),
    "detectable_format:title": (
        _rx(r"Your\s+answer\s+must\s+contain\s+a\s+title,\s+wrapped\s+in\s+double\s+angular\s+brackets,\s+such\s+as\s+<<poem\s+of\s+joy>>\."),
    ),
    "combination:two_responses": (
        _rx(r"Give\s+two\s+different\s+responses\.\s+Responses\s+and\s+only\s+responses\s+should\s+be\s+separated\s+by\s+6\s+asterisk\s+symbols:\s*\*\*\*\*\*\*\."),
    ),
    "combination:repeat_prompt": (
        _rx(r"First\s+repeat\s+the\s+request\s+word\s+for\s+word\s+without\s+change,\s+then\s+give\s+your\s+answer\s+\(1\.\s+do\s+not\s+say\s+any\s+words\s+or\s+characters\s+before\s+repeating\s+the\s+request;\s+2\.\s+the\s+request\s+you\s+need\s+to\s+repeat\s+does\s+not\s+include\s+this\s+sentence\)"),
    ),
    "startend:end_checker": (
        _rx(r"Finish\s+your\s+response\s+with\s+this\s+exact\s+phrase\s+(?P<end_phrase>.+?)\.\s+No\s+other\s+words\s+should\s+follow\s+this\s+phrase\."),
    ),
    "change_case:capital_word_frequency": (
        _rx(r"In\s+your\s+response,\s+words\s+with\s+all\s+capital\s+letters\s+should\s+appear\s+(?P<relation>less\s+than|at\s+least)\s+(?P<frequency>\d+)\s+times\."),
    ),
    "change_case:english_capital": (
        _rx(r"Your\s+entire\s+response\s+should\s+be\s+in\s+English,\s+and\s+in\s+all\s+capital\s+letters\."),
    ),
    "change_case:english_lowercase": (
        _rx(r"Your\s+entire\s+response\s+should\s+be\s+in\s+English,\s+and\s+in\s+all\s+lowercase\s+letters\.\s+No\s+capital\s+letters\s+are\s+allowed\."),
    ),
    "punctuation:no_comma": (
        _rx(r"In\s+your\s+entire\s+response,\s+refrain\s+from\s+the\s+use\s+of\s+any\s+commas\."),
    ),
    "startend:quotation": (
        _rx(r"Wrap\s+your\s+entire\s+response\s+with\s+double\s+quotation\s+marks\."),
    ),
}

LEGACY_IDS = frozenset(PATTERNS)
assert len(LEGACY_IDS) == 25

_INT_FIELDS = {
    "frequency", "num_sentences", "num_paragraphs", "num_words",
    "nth_paragraph", "num_placeholders", "num_bullets", "num_highlights",
    "num_sections",
}
_LIST_FIELDS = {"keywords", "forbidden_words"}


def _coerce_slots(instruction_id: str, raw: dict[str, str]) -> dict[str, Any]:
    slots: dict[str, Any] = {}
    for key, value in raw.items():
        value = value.strip()
        if key in _INT_FIELDS:
            slots[key] = int(value)
        elif key in _LIST_FIELDS:
            parsed = ast.literal_eval(value)
            if not isinstance(parsed, (list, tuple)) or not all(isinstance(x, str) for x in parsed):
                raise ValueError("INVALID_PUBLIC_LIST_LITERAL")
            slots[key] = list(parsed)
        else:
            slots[key] = value
    if instruction_id == "language:response_language":
        name = str(slots["language_name"])
        code = LANGUAGE_NAME_TO_CODE.get(name.title())
        if code is None:
            raise ValueError("UNKNOWN_PUBLIC_LANGUAGE_NAME")
        slots["language_code"] = code
    return slots


def recognize(prompt: str) -> list[dict[str, Any]]:
    prompt = str(prompt or "")
    if not prompt:
        return []
    found: list[Match] = []
    for instruction_id, patterns in PATTERNS.items():
        for pattern in patterns:
            for match in pattern.finditer(prompt):
                try:
                    slots = _coerce_slots(instruction_id, {
                        k: v for k, v in match.groupdict().items() if v is not None
                    })
                except Exception:
                    continue
                if instruction_id == "combination:repeat_prompt":
                    prefix = prompt[:match.start()].rstrip()
                    if prefix:
                        slots["prompt_to_repeat"] = prefix
                found.append(Match(
                    instruction_id=instruction_id,
                    start=match.start(),
                    end=match.end(),
                    matched_text=match.group(0),
                    slots=slots,
                ))
    found.sort(key=lambda x: (x.instruction_id, -(x.end-x.start), x.start))
    dedup: list[Match] = []
    seen: set[str] = set()
    for item in found:
        if item.instruction_id not in seen:
            dedup.append(item)
            seen.add(item.instruction_id)
    dedup.sort(key=lambda x: (x.start, x.end, x.instruction_id))
    return [x.to_dict() for x in dedup]


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    prompt = str((args or {}).get("prompt") or (args or {}).get("instruction") or "")
    matches = recognize(prompt)
    return {
        "schema": SCHEMA,
        "matches": matches,
        "recognized_instruction_ids": [x["instruction_id"] for x in matches],
        "legacy_registry_size": len(LEGACY_IDS),
        "hidden_kwargs_used": False,
        "instruction_id_list_used": False,
        "terminal_case_ids_used": False,
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
    }


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(run({"prompt": ns.prompt}), indent=2, ensure_ascii=False, sort_keys=True))
