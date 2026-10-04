#!/usr/bin/env python3
"""Source-derived visible-description inverter for frozen LiveBench legacy IFEval.

Recognizes the 25 build_description surfaces in the frozen legacy registry from
visible prompt text only. It reads no hidden instruction ids, kwargs, case ids,
responses, or scorer feedback. A parse PASS is not a benchmark PASS.
"""
from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_DESCRIPTION_INVERTER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_LEGACY_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_LEGACY_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

ALL_LEGACY_IDS = (
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

FLAGS = re.IGNORECASE | re.MULTILINE | re.DOTALL

_PATTERN_SOURCE: dict[str, str] = {
    "keywords:existence":
        r"Include keywords (?P<keywords>\[[^\n]*?\]) in the response\.",
    "keywords:frequency":
        r"In your response, the word (?P<keyword>.+?) should appear "
        r"(?P<relation>less than|at least) (?P<frequency>\d+) times\.",
    "keywords:forbidden_words":
        r"Do not include keywords (?P<forbidden_words>\[[^\n]*?\]) in the response\.",
    "keywords:letter_frequency":
        r"In your response, the letter (?P<letter>[A-Za-z]) should appear "
        r"(?P<let_relation>less than|at least) (?P<let_frequency>\d+) times\.",
    "language:response_language":
        r"Your ENTIRE response should be in (?P<language_name>.+?) language, "
        r"no other language is allowed\.",
    "length_constraints:number_sentences":
        r"Your response should contain (?P<relation>less than|at least) "
        r"(?P<num_sentences>\d+) sentences\.",
    "length_constraints:number_paragraphs":
        r"There should be (?P<num_paragraphs>\d+) paragraphs\. "
        r"Paragraphs are separated with the markdown divider: \*\*\*",
    "length_constraints:number_words":
        r"Answer with (?P<relation>less than|at least) (?P<num_words>\d+) words\.",
    "length_constraints:nth_paragraph_first_word":
        r"There should be (?P<num_paragraphs>\d+) paragraphs\. "
        r"Paragraphs and only paragraphs are separated with each other by two "
        r"new lines as if it was '\\n\\n' in python\. "
        r"Paragraph (?P<nth_paragraph>\d+) must start with word "
        r"(?P<first_word>[^\s.]+)\.",
    "detectable_content:number_placeholders":
        r"The response must contain at least (?P<num_placeholders>\d+) placeholders "
        r"represented by square brackets, such as \[address\]\.",
    "detectable_content:postscript":
        r"At the end of your response, please explicitly add a postscript "
        r"starting with (?P<postscript_marker>\S+)",
    "detectable_format:number_bullet_lists":
        r"Your answer must contain exactly (?P<num_bullets>\d+) bullet points\. "
        r"Use the markdown bullet points such as:\s*"
        r"\* This is point 1\.\s*\* This is point 2",
    "detectable_format:constrained_response":
        r"Answer with one of the following options: "
        r"(?P<response_options>\[[^\n]*?\])",
    "detectable_format:number_highlighted_sections":
        r"Highlight at least (?P<num_highlights>\d+) sections in your answer with "
        r"markdown, i\.e\. \*highlighted section\*\.",
    "detectable_format:multiple_sections":
        r"Your response must have (?P<num_sections>\d+) sections\. Mark the beginning "
        r"of each section with (?P<section_spliter>[^\s]+) X, such as:\s*"
        r"(?P=section_spliter) 1\s*\[content of section 1\]\s*"
        r"(?P=section_spliter) 2\s*\[content of section 2\]",
    "detectable_format:json_format":
        r"Entire output should be wrapped in JSON format\. You can use markdown"
        r" ticks such as \x60\x60\x60\.",
    "detectable_format:title":
        r"Your answer must contain a title, wrapped in double angular brackets,"
        r" such as <<poem of joy>>\.",
    "combination:two_responses":
        r"Give two different responses\. Responses and only responses should"
        r" be separated by 6 asterisk symbols: \*\*\*\*\*\*\.",
    "combination:repeat_prompt":
        r"First repeat the request word for word without change,"
        r" then give your answer \(1\. do not say any words or characters"
        r" before repeating the request; 2\. the request you need to repeat"
        r" does not include this sentence\)",
    "startend:end_checker":
        r"Finish your response with this exact phrase (?P<end_phrase>.+?)\. "
        r"No other words should follow this phrase\.",
    "change_case:capital_word_frequency":
        r"In your response, words with all capital letters should appear "
        r"(?P<capital_relation>less than|at least) (?P<capital_frequency>\d+) times\.",
    "change_case:english_capital":
        r"Your entire response should be in English, and in all capital letters\.",
    "change_case:english_lowercase":
        r"Your entire response should be in English, and in all lowercase letters\. "
        r"No capital letters are allowed\.",
    "punctuation:no_comma":
        r"In your entire response, refrain from the use of any commas\.",
    "startend:quotation":
        r"Wrap your entire response with double quotation marks\.",
}

_PATTERNS = {
    instruction_id: re.compile(pattern, FLAGS)
    for instruction_id, pattern in _PATTERN_SOURCE.items()
}

_LIST_FIELDS = {"keywords", "forbidden_words", "response_options"}
_INT_FIELDS = {
    "frequency", "let_frequency", "num_sentences", "num_paragraphs",
    "num_words", "nth_paragraph", "num_placeholders", "num_bullets",
    "num_highlights", "num_sections", "capital_frequency",
}


@dataclass(frozen=True)
class LegacyDescriptionMatch:
    instruction_id: str
    start: int
    end: int
    matched_text: str
    kwargs_visible: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LegacyDescriptionInversionError(ValueError):
    pass


def _coerce(name: str, value: str) -> Any:
    value = str(value)
    if name in _INT_FIELDS:
        return int(value)
    if name in _LIST_FIELDS:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise LegacyDescriptionInversionError(
                "VISIBLE_LIST_LITERAL_PARSE_FAILED:" + name
            ) from exc
        if not isinstance(parsed, (list, tuple)):
            raise LegacyDescriptionInversionError(
                "VISIBLE_LIST_LITERAL_NOT_SEQUENCE:" + name
            )
        return list(parsed)
    return value.strip()


def invert_legacy_descriptions(prompt: str) -> dict[str, Any]:
    text = str(prompt or "")
    if not text.strip():
        raise LegacyDescriptionInversionError("PROMPT_REQUIRED")

    matches: list[LegacyDescriptionMatch] = []
    for instruction_id in ALL_LEGACY_IDS:
        regex = _PATTERNS[instruction_id]
        for found in regex.finditer(text):
            kwargs_visible = {
                key: _coerce(key, value)
                for key, value in found.groupdict().items()
                if value is not None
            }
            matches.append(
                LegacyDescriptionMatch(
                    instruction_id=instruction_id,
                    start=found.start(),
                    end=found.end(),
                    matched_text=found.group(0),
                    kwargs_visible=kwargs_visible,
                )
            )

    matches.sort(key=lambda item: (item.start, item.end, item.instruction_id))
    for left, right in zip(matches, matches[1:]):
        if left.start < right.end and right.start < left.end:
            raise LegacyDescriptionInversionError(
                "OVERLAPPING_DESCRIPTION_MATCHES:"
                + left.instruction_id + ":" + right.instruction_id
            )

    return {
        "schema": SCHEMA,
        "status": "PASS__VISIBLE_LEGACY_DESCRIPTIONS_INVERTED",
        "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "registry_instruction_count": len(ALL_LEGACY_IDS),
        "pattern_instruction_count": len(_PATTERNS),
        "source_registry_coverage_complete": set(_PATTERNS) == set(ALL_LEGACY_IDS),
        "matched_instruction_count": len(matches),
        "matches": [item.to_dict() for item in matches],
        "instruction_ids": [item.instruction_id for item in matches],
        "hidden_instruction_id_list_read": False,
        "hidden_kwargs_read": False,
        "case_id_read": False,
        "scorer_feedback_read": False,
        "model_dependency_count": 0,
        "hard_nonclaim": (
            "MATCH_COUNT_IS A VISIBLE_SOURCE_GRAMMAR RESULT; IT DOES NOT BY ITSELF "
            "PROVE THE FROZEN TARGET PROMPT POPULATION USES NO HISTORICAL WORDING "
            "VARIANTS OR THAT ANY SYNTHESIZED RESPONSE PASSES THE CHECKERS"
        ),
    }


def registry_coverage() -> dict[str, Any]:
    missing = sorted(set(ALL_LEGACY_IDS) - set(_PATTERNS))
    extra = sorted(set(_PATTERNS) - set(ALL_LEGACY_IDS))
    return {
        "schema": SCHEMA,
        "registry_instruction_count": len(ALL_LEGACY_IDS),
        "pattern_instruction_count": len(_PATTERNS),
        "missing": missing,
        "extra": extra,
        "complete": not missing and not extra,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return invert_legacy_descriptions(
        str(args.get("prompt") or args.get("instruction") or "")
    )


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    ns = parser.parse_args()
    print(json.dumps(invert_legacy_descriptions(ns.prompt), indent=2, sort_keys=True))
