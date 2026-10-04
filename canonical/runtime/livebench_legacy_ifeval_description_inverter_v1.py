#!/usr/bin/env python3
"""Prompt-only inversion of the pinned legacy LiveBench/IFEval grammar.

Authority boundary:
- grammar is derived only from the exact public LiveBench legacy IFEval source
  pinned at LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091;
- runtime receives only visible prompt text;
- it never receives instruction_id_list, kwargs, terminal case IDs, or scores;
- unknown wording fails closed rather than being guessed.

The legacy registry contains 25 enabled instruction types.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_IFEVAL_DESCRIPTION_INVERTER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_UTIL_BLOB = "8ce01747887ec0792c8f024e1972e34ece781676"
LEGACY_DISPATCH_BOUNDARY = "2025-11-25"

ENABLED_INSTRUCTION_IDS = (
    "keywords:existence",
    "keywords:frequency",
    "keywords:forbidden_words",
    "keywords:letter_frequency",
    "language:response_language",
    "length_constraints:number_sentences",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:number_placeholders",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "detectable_format:title",
    "combination:two_responses",
    "combination:repeat_prompt",
    "startend:end_checker",
    "change_case:capital_word_frequency",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "punctuation:no_comma",
    "startend:quotation",
)

_LANGUAGE_NAME_TO_CODE = {
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _literal_list(raw: str) -> list[str] | None:
    try:
        value = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(value, (list, tuple)):
        return None
    return [str(x) for x in value]


def _base_request(prompt: str) -> str:
    for marker in ("-------\n", "-------\r\n"):
        if marker in prompt:
            return prompt.split(marker, 1)[0].strip()
    return ""


def _m(
    instruction_id: str,
    pattern: str,
    prompt: str,
    *,
    flags: int = re.IGNORECASE | re.DOTALL,
    converter=None,
) -> list[Match]:
    out: list[Match] = []
    for match in re.finditer(pattern, prompt, flags=flags):
        slots: dict[str, Any] = {
            k: v.strip() for k, v in match.groupdict().items() if v is not None
        }
        if converter is not None:
            converted = converter(dict(slots))
            if converted is None:
                continue
            slots = converted
        out.append(Match(instruction_id, match.start(), match.end(), match.group(0), slots))
    return out


def _ints(*names: str):
    def convert(slots: dict[str, Any]) -> dict[str, Any] | None:
        try:
            for name in names:
                if name in slots:
                    slots[name] = int(slots[name])
        except ValueError:
            return None
        return slots
    return convert


def _list_slot(name: str):
    def convert(slots: dict[str, Any]) -> dict[str, Any] | None:
        values = _literal_list(str(slots.get(name, "")))
        if values is None:
            return None
        slots[name] = values
        return slots
    return convert


def recognize(prompt: str) -> list[dict[str, Any]]:
    prompt = str(prompt or "")
    if not prompt:
        return []

    found: list[Match] = []

    found += _m(
        "keywords:existence",
        r"Include keywords\s+(?P<keywords>\[[^\n]*?\])\s+in the response\.",
        prompt,
        converter=_list_slot("keywords"),
    )
    found += _m(
        "keywords:frequency",
        r"In your response, the word\s+(?P<keyword>.+?)\s+should appear\s+"
        r"(?P<relation>less than|at least)\s+(?P<frequency>\d+)\s+times\.",
        prompt,
        converter=_ints("frequency"),
    )
    found += _m(
        "keywords:forbidden_words",
        r"Do not include keywords\s+(?P<forbidden_words>\[[^\n]*?\])\s+in the response\.",
        prompt,
        converter=_list_slot("forbidden_words"),
    )
    found += _m(
        "keywords:letter_frequency",
        r"In your response, the letter\s+(?P<letter>\S)\s+should appear\s+"
        r"(?P<relation>less than|at least)\s+(?P<frequency>\d+)\s+times\.",
        prompt,
        converter=_ints("frequency"),
    )
    found += _m(
        "language:response_language",
        r"Your ENTIRE response should be in\s+(?P<language_name>[A-Za-z]+)\s+language,"
        r"\s+no other language is allowed\.",
        prompt,
        converter=lambda s: (
            {**s, "language": _LANGUAGE_NAME_TO_CODE[s["language_name"]]}
            if s.get("language_name") in _LANGUAGE_NAME_TO_CODE else None
        ),
    )
    found += _m(
        "length_constraints:number_sentences",
        r"Your response should contain\s+(?P<relation>less than|at least)\s+"
        r"(?P<num_sentences>\d+)\s+sentences\.",
        prompt,
        converter=_ints("num_sentences"),
    )
    found += _m(
        "length_constraints:number_paragraphs",
        r"There should be\s+(?P<num_paragraphs>\d+)\s+paragraphs\.\s+"
        r"Paragraphs are separated with the markdown divider:\s+\*\*\*",
        prompt,
        converter=_ints("num_paragraphs"),
    )
    found += _m(
        "length_constraints:number_words",
        r"Answer with\s+(?P<relation>less than|at least)\s+"
        r"(?P<num_words>\d+)\s+words\.",
        prompt,
        converter=_ints("num_words"),
    )
    found += _m(
        "length_constraints:nth_paragraph_first_word",
        r"There should be\s+(?P<num_paragraphs>\d+)\s+paragraphs\.\s+"
        r"Paragraphs and only paragraphs are separated with each other by two\s+"
        r"new lines as if it was ['\"]\\n\\n['\"] in python\.\s+"
        r"Paragraph\s+(?P<nth_paragraph>\d+)\s+must start with word\s+"
        r"(?P<first_word>[^\.\s]+)\.",
        prompt,
        converter=_ints("num_paragraphs", "nth_paragraph"),
    )
    found += _m(
        "detectable_content:number_placeholders",
        r"The response must contain at least\s+(?P<num_placeholders>\d+)\s+"
        r"placeholders represented by square brackets, such as \[address\]\.",
        prompt,
        converter=_ints("num_placeholders"),
    )
    found += _m(
        "detectable_content:postscript",
        r"At the end of your response, please explicitly add a postscript\s+"
        r"starting with\s+(?P<postscript_marker>P\.S\.|P\.P\.S|\S+)",
        prompt,
    )
    found += _m(
        "detectable_format:number_bullet_lists",
        r"Your answer must contain exactly\s+(?P<num_bullets>\d+)\s+bullet points\.",
        prompt,
        converter=_ints("num_bullets"),
    )
    found += _m(
        "detectable_format:constrained_response",
        r"Answer with one of the following options:\s+"
        r"My answer is yes\.,\s+My answer is no\.,\s+My answer is maybe\.",
        prompt,
    )
    found += _m(
        "detectable_format:number_highlighted_sections",
        r"Highlight at least\s+(?P<num_highlights>\d+)\s+sections in your answer with markdown,"
        r"\s+i\.e\.\s+\*highlighted section\*\.",
        prompt,
        converter=_ints("num_highlights"),
    )
    found += _m(
        "detectable_format:multiple_sections",
        r"Your response must have\s+(?P<num_sections>\d+)\s+sections\.\s+Mark the beginning\s+"
        r"of each section with\s+(?P<section_spliter>Section|SECTION)\s+X,",
        prompt,
        converter=_ints("num_sections"),
    )
    found += _m(
        "detectable_format:json_format",
        r"Entire output should be wrapped in JSON format\.\s+You can use markdown"
        r"\s+ticks such as ```\.",
        prompt,
    )
    found += _m(
        "detectable_format:title",
        r"Your answer must contain a title, wrapped in double angular brackets,"
        r"\s+such as <<poem of joy>>\.",
        prompt,
    )
    found += _m(
        "combination:two_responses",
        r"Give two different responses\.\s+Responses and only responses should"
        r"\s+be separated by 6 asterisk symbols:\s+\*\*\*\*\*\*\.",
        prompt,
    )
    repeat_matches = _m(
        "combination:repeat_prompt",
        r"First repeat the request word for word without change,\s+"
        r"then give your answer\s*\(1\. do not say any words or characters\s+"
        r"before repeating the request;\s*2\. the request you need to repeat\s+"
        r"does not include this sentence\)",
        prompt,
    )
    base = _base_request(prompt)
    if base:
        repeat_matches = [
            Match(x.instruction_id, x.start, x.end, x.matched_text, {"prompt_to_repeat": base})
            for x in repeat_matches
        ]
    else:
        repeat_matches = []
    found += repeat_matches
    found += _m(
        "startend:end_checker",
        r"Finish your response with this exact phrase\s+(?P<end_phrase>[\s\S]+?)\.\s+"
        r"No other words should follow this phrase\.",
        prompt,
    )
    found += _m(
        "change_case:capital_word_frequency",
        r"In your response, words with all capital letters should appear\s+"
        r"(?P<relation>less than|at least)\s+(?P<frequency>\d+)\s+times\.",
        prompt,
        converter=_ints("frequency"),
    )
    found += _m(
        "change_case:english_capital",
        r"Your entire response should be in English, and in all capital letters\.",
        prompt,
    )
    found += _m(
        "change_case:english_lowercase",
        r"Your entire response should be in English, and in all lowercase\s+"
        r"letters\.\s+No capital letters are allowed\.",
        prompt,
    )
    found += _m(
        "punctuation:no_comma",
        r"In your entire response, refrain from the use of any commas\.",
        prompt,
    )
    found += _m(
        "startend:quotation",
        r"Wrap your entire response with double quotation marks\.",
        prompt,
    )

    long_ranges = [(m.start, m.end) for m in found
                   if m.instruction_id == "length_constraints:nth_paragraph_first_word"]
    if long_ranges:
        found = [
            m for m in found
            if not (
                m.instruction_id == "length_constraints:number_paragraphs"
                and any(m.start >= a and m.end <= b for a, b in long_ranges)
            )
        ]

    dedup: dict[tuple[str, int, int], Match] = {}
    for item in found:
        dedup[(item.instruction_id, item.start, item.end)] = item
    ordered = sorted(dedup.values(), key=lambda x: (x.start, x.end, x.instruction_id))
    return [x.to_dict() for x in ordered]


def coverage_summary(prompt: str) -> dict[str, Any]:
    matches = recognize(prompt)
    return {
        "schema": SCHEMA,
        "recognized_count": len(matches),
        "recognized_instruction_ids": [m["instruction_id"] for m in matches],
        "matches": matches,
        "enabled_instruction_type_count": len(ENABLED_INSTRUCTION_IDS),
        "runtime_hidden_kwargs_used": False,
        "runtime_terminal_case_id_used": False,
        "runtime_network_used": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return coverage_summary(str(args.get("prompt") or args.get("instruction") or args.get("text") or ""))


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(coverage_summary(ns.prompt), indent=2, ensure_ascii=False, sort_keys=True))
