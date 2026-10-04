#!/usr/bin/env python3
"""Prompt-only inverter for the pinned LiveBench legacy IFEval description grammar.

Reads visible prompt text only. It never consumes instruction_id_list or hidden
kwargs. Unknown or ambiguous descriptions remain unresolved rather than guessed.
"""
from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY25_PROMPT_INVERTER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

LEGACY_INSTRUCTION_IDS = (
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
_LANGUAGE_BY_LOWER_NAME = {name.lower(): code for name, code in _LANGUAGE_NAME_TO_CODE.items()}


@dataclass(frozen=True)
class Match:
    instruction_id: str
    start: int
    end: int
    matched_text: str
    kwargs: dict[str, Any]
    route: str = "PINNED_SOURCE_DESCRIPTION"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _list_of_strings(raw: str) -> list[str] | None:
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return None
    if not isinstance(value, (list, tuple)) or not all(isinstance(x, str) for x in value):
        return None
    return list(value)


def _append(out: list[Match], instruction_id: str, m: re.Match[str], kwargs: dict[str, Any] | None = None) -> None:
    out.append(Match(
        instruction_id=instruction_id,
        start=m.start(),
        end=m.end(),
        matched_text=m.group(0),
        kwargs=dict(kwargs or {}),
    ))


def _iter(pattern: str, prompt: str):
    return re.finditer(pattern, prompt, flags=re.IGNORECASE | re.DOTALL)


def recognize(prompt: str) -> dict[str, Any]:
    prompt = str(prompt or "")
    out: list[Match] = []

    for m in _iter(r"Include keywords (?P<items>\[[^\n]*?\]) in the response\.", prompt):
        items = _list_of_strings(m.group("items"))
        if items is not None:
            _append(out, "keywords:existence", m, {"keywords": sorted(items)})

    for m in _iter(
        r"In your response, the word (?P<keyword>.+?) should appear "
        r"(?P<relation>less than|at least) (?P<frequency>\d+) times\.",
        prompt,
    ):
        _append(out, "keywords:frequency", m, {
            "keyword": m.group("keyword").strip(),
            "frequency": int(m.group("frequency")),
            "relation": m.group("relation").lower(),
        })

    for m in _iter(r"Do not include keywords (?P<items>\[[^\n]*?\]) in the response\.", prompt):
        items = _list_of_strings(m.group("items"))
        if items is not None:
            _append(out, "keywords:forbidden_words", m, {"forbidden_words": sorted(set(items))})

    for m in _iter(
        r"In your response, the letter (?P<letter>[A-Za-z]) should appear "
        r"(?P<relation>less than|at least) (?P<frequency>\d+) times\.",
        prompt,
    ):
        _append(out, "keywords:letter_frequency", m, {
            "letter": m.group("letter").lower(),
            "let_frequency": int(m.group("frequency")),
            "let_relation": m.group("relation").lower(),
        })

    for m in _iter(
        r"Your ENTIRE response should be in (?P<language>[A-Za-z]+) language, "
        r"no other language is allowed\.",
        prompt,
    ):
        code = _LANGUAGE_BY_LOWER_NAME.get(m.group("language").lower())
        if code is not None:
            _append(out, "language:response_language", m, {"language": code})

    for m in _iter(
        r"Your response should contain (?P<relation>less than|at least) "
        r"(?P<count>\d+) sentences\.",
        prompt,
    ):
        _append(out, "length_constraints:number_sentences", m, {
            "num_sentences": int(m.group("count")),
            "relation": m.group("relation").lower(),
        })

    for m in _iter(
        r"There should be (?P<count>\d+) paragraphs\. "
        r"Paragraphs are separated with the markdown divider: \*\*\*",
        prompt,
    ):
        _append(out, "length_constraints:number_paragraphs", m, {
            "num_paragraphs": int(m.group("count")),
        })

    for m in _iter(
        r"Answer with (?P<relation>less than|at least) (?P<count>\d+) words\.",
        prompt,
    ):
        _append(out, "length_constraints:number_words", m, {
            "num_words": int(m.group("count")),
            "relation": m.group("relation").lower(),
        })

    for m in _iter(
        r"There should be (?P<count>\d+) paragraphs\. "
        r"Paragraphs and only paragraphs are separated with each other by two "
        r"new lines as if it was '\\n\\n' in python\. "
        r"Paragraph (?P<nth>\d+) must start with word (?P<word>[^\s.]+)\.",
        prompt,
    ):
        _append(out, "length_constraints:nth_paragraph_first_word", m, {
            "num_paragraphs": int(m.group("count")),
            "nth_paragraph": int(m.group("nth")),
            "first_word": m.group("word").lower(),
        })

    for m in _iter(
        r"The response must contain at least (?P<count>\d+) placeholders "
        r"represented by square brackets, such as \[address\]\.",
        prompt,
    ):
        _append(out, "detectable_content:number_placeholders", m, {
            "num_placeholders": int(m.group("count")),
        })

    for m in _iter(
        r"At the end of your response, please explicitly add a postscript starting with "
        r"(?P<marker>[^\n]+?)(?=\n|$)",
        prompt,
    ):
        _append(out, "detectable_content:postscript", m, {
            "postscript_marker": m.group("marker").strip(),
        })

    for m in _iter(
        r"Your answer must contain exactly (?P<count>\d+) bullet points\. "
        r"Use the markdown bullet points such as:",
        prompt,
    ):
        _append(out, "detectable_format:number_bullet_lists", m, {
            "num_bullets": int(m.group("count")),
        })

    static_patterns = {
        "detectable_format:constrained_response": "Answer with one of the following options:",
        "detectable_format:json_format": "Entire output should be wrapped in JSON format.",
        "detectable_format:title": "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
        "combination:two_responses": "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******.",
        "combination:repeat_prompt": (
            "First repeat the request word for word without change, then give your answer "
            "(1. do not say any words or characters before repeating the request; "
            "2. the request you need to repeat does not include this sentence)"
        ),
        "change_case:english_capital": "Your entire response should be in English, and in all capital letters.",
        "change_case:english_lowercase": (
            "Your entire response should be in English, and in all lowercase letters. "
            "No capital letters are allowed."
        ),
        "punctuation:no_comma": "In your entire response, refrain from the use of any commas.",
        "startend:quotation": "Wrap your entire response with double quotation marks.",
    }
    for instruction_id, literal in static_patterns.items():
        for m in re.finditer(re.escape(literal), prompt, flags=re.IGNORECASE):
            kwargs: dict[str, Any] = {}
            if instruction_id == "combination:repeat_prompt":
                kwargs["prompt_to_repeat"] = None
                kwargs["prompt_to_repeat_recovery"] = "VISIBLE_PROMPT_RECOVERY_REQUIRED"
            _append(out, instruction_id, m, kwargs)

    for m in _iter(
        r"Highlight at least (?P<count>\d+) sections in your answer with markdown, "
        r"i\.e\. \*highlighted section\*\.",
        prompt,
    ):
        _append(out, "detectable_format:number_highlighted_sections", m, {
            "num_highlights": int(m.group("count")),
        })

    for m in _iter(
        r"Your response must have (?P<count>\d+) sections\. Mark the beginning "
        r"of each section with (?P<splitter>[^\n]+?) X, such as:",
        prompt,
    ):
        _append(out, "detectable_format:multiple_sections", m, {
            "section_spliter": m.group("splitter").strip(),
            "num_sections": int(m.group("count")),
        })

    for m in _iter(
        r"Finish your response with this exact phrase (?P<ender>[\s\S]+?)\. "
        r"No other words should follow this phrase\.",
        prompt,
    ):
        _append(out, "startend:end_checker", m, {
            "end_phrase": m.group("ender").strip(),
        })

    for m in _iter(
        r"In your response, words with all capital letters should appear "
        r"(?P<relation>less than|at least) (?P<count>\d+) times\.",
        prompt,
    ):
        _append(out, "change_case:capital_word_frequency", m, {
            "capital_frequency": int(m.group("count")),
            "capital_relation": m.group("relation").lower(),
        })

    out.sort(key=lambda x: (x.start, x.end, x.instruction_id))
    counts: dict[str, int] = {}
    for item in out:
        counts[item.instruction_id] = counts.get(item.instruction_id, 0) + 1
    ambiguous_ids = sorted(k for k, v in counts.items() if v > 1)

    return {
        "schema": SCHEMA,
        "status": "PASS" if not ambiguous_ids else "AMBIGUOUS_FAIL_CLOSED",
        "matches": [item.to_dict() for item in out],
        "recognized_instruction_ids": sorted(counts),
        "recognized_instruction_type_count": len(counts),
        "legacy_registry_type_count": len(LEGACY_INSTRUCTION_IDS),
        "ambiguous_instruction_ids": ambiguous_ids,
        "hidden_instruction_id_list_read": False,
        "hidden_kwargs_read": False,
        "terminal_case_metadata_read": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return recognize(str((args or {}).get("prompt") or ""))


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(recognize(ns.prompt), indent=2, ensure_ascii=False, sort_keys=True))
