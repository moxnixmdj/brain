#!/usr/bin/env python3
"""Prompt-only compiler for the pinned legacy LiveBench / IFEval description surface.

Source authority:
  LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091
  livebench/if_runner/instruction_following_eval/instructions.py
  livebench/if_runner/instruction_following_eval/instructions_registry.py

The runtime receives only visible prompt text. It never reads terminal
instruction_id_list, kwargs, question ids, responses, or hidden checker state.

This module is deliberately recognition-only. Matching a public source template
does not itself prove that every score-relevant instruction in a prompt was
recognized, and it does not authorize a response witness.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_CONSTRAINT_COMPILER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

ACTIVE_IDS = (
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

LANGUAGE_NAME_TO_CODE = {
    "English":"en","Spanish":"es","Portuguese":"pt","Arabic":"ar","Hindi":"hi",
    "French":"fr","Russian":"ru","German":"de","Japanese":"ja","Italian":"it",
    "Bengali":"bn","Ukrainian":"uk","Thai":"th","Urdu":"ur","Tamil":"ta",
    "Telugu":"te","Bulgarian":"bg","Korean":"ko","Polish":"pl","Hebrew":"he",
    "Persian":"fa","Vietnamese":"vi","Nepali":"ne","Swahili":"sw","Kannada":"kn",
    "Marathi":"mr","Gujarati":"gu","Punjabi":"pa","Malayalam":"ml","Finnish":"fi",
}

@dataclass(frozen=True)
class Match:
    instruction_id: str
    start: int
    end: int
    matched_text: str
    kwargs: dict[str, Any]
    parameter_derivation: str = "VISIBLE_SOURCE_TEMPLATE"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _literal_list(text: str) -> list[str] | None:
    try:
        value = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(value, (list, tuple)):
        return None
    if not all(isinstance(x, str) for x in value):
        return None
    return list(value)


def _add(out: list[Match], instruction_id: str, m: re.Match[str], kwargs: dict[str, Any]) -> None:
    out.append(Match(
        instruction_id=instruction_id,
        start=m.start(),
        end=m.end(),
        matched_text=m.group(0),
        kwargs=kwargs,
    ))


def recognize(prompt: str) -> list[dict[str, Any]]:
    text = str(prompt or "")
    if not text:
        return []
    out: list[Match] = []

    for m in re.finditer(r"Include keywords (\[[^\n]*?\]) in the response\.", text):
        values = _literal_list(m.group(1))
        if values is not None:
            _add(out, "keywords:existence", m, {"keywords": values})

    for m in re.finditer(
        r"In your response, the word (.+?) should appear (less than|at least) (\d+) times\.",
        text,
    ):
        _add(out, "keywords:frequency", m, {
            "keyword": m.group(1).strip(),
            "frequency": int(m.group(3)),
            "relation": m.group(2),
        })

    for m in re.finditer(r"Do not include keywords (\[[^\n]*?\]) in the response\.", text):
        values = _literal_list(m.group(1))
        if values is not None:
            _add(out, "keywords:forbidden_words", m, {"forbidden_words": values})

    for m in re.finditer(
        r"In your response, the letter ([A-Za-z]) should appear (less than|at least) (\d+) times\.",
        text,
    ):
        _add(out, "keywords:letter_frequency", m, {
            "letter": m.group(1).lower(),
            "let_frequency": int(m.group(3)),
            "let_relation": m.group(2),
        })

    for m in re.finditer(
        r"Your ENTIRE response should be in ([A-Za-z]+) language, no other language is allowed\.",
        text,
    ):
        name = m.group(1)
        code = LANGUAGE_NAME_TO_CODE.get(name)
        if code is not None:
            _add(out, "language:response_language", m, {"language": code, "language_name": name})

    for m in re.finditer(
        r"Your response should contain (less than|at least) (\d+) sentences\.",
        text,
    ):
        _add(out, "length_constraints:number_sentences", m, {
            "relation": m.group(1),
            "num_sentences": int(m.group(2)),
        })

    for m in re.finditer(
        r"There should be (\d+) paragraphs\. Paragraphs are separated with the markdown divider: \*\*\*",
        text,
    ):
        _add(out, "length_constraints:number_paragraphs", m, {"num_paragraphs": int(m.group(1))})

    for m in re.finditer(r"Answer with (less than|at least) (\d+) words\.", text):
        _add(out, "length_constraints:number_words", m, {
            "relation": m.group(1),
            "num_words": int(m.group(2)),
        })

    para_first = re.compile(
        r"There should be (\d+) paragraphs\. "
        r"Paragraphs and only paragraphs are separated with each other by two new lines "
        r"as if it was '\\n\\n' in python\. Paragraph (\d+) must start with word ([^\s.]+)\."
    )
    for m in para_first.finditer(text):
        _add(out, "length_constraints:nth_paragraph_first_word", m, {
            "num_paragraphs": int(m.group(1)),
            "nth_paragraph": int(m.group(2)),
            "first_word": m.group(3).lower(),
        })

    for m in re.finditer(
        r"The response must contain at least (\d+) placeholders represented by square brackets, such as \[address\]\.",
        text,
    ):
        _add(out, "detectable_content:number_placeholders", m, {"num_placeholders": int(m.group(1))})

    for m in re.finditer(
        r"At the end of your response, please explicitly add a postscript starting with (P\.S\.|P\.P\.S)",
        text,
    ):
        _add(out, "detectable_content:postscript", m, {"postscript_marker": m.group(1)})

    bullet_pattern = re.compile(
        r"Your answer must contain exactly (\d+) bullet points\. "
        r"Use the markdown bullet points such as:\n"
        r"\* This is point 1\. ?\n"
        r"\* This is point 2"
    )
    for m in bullet_pattern.finditer(text):
        _add(out, "detectable_format:number_bullet_lists", m, {"num_bullets": int(m.group(1))})

    constrained = (
        "Answer with one of the following options: "
        "('My answer is yes.', 'My answer is no.', 'My answer is maybe.')"
    )
    for m in re.finditer(re.escape(constrained), text):
        _add(out, "detectable_format:constrained_response", m, {})

    for m in re.finditer(
        r"Highlight at least (\d+) sections in your answer with markdown, i\.e\. \*highlighted section\*\.",
        text,
    ):
        _add(out, "detectable_format:number_highlighted_sections", m, {"num_highlights": int(m.group(1))})

    section_pattern = re.compile(
        r"Your response must have (\d+) sections\. Mark the beginning of each section with (Section|SECTION) X, such as:\n"
        r"(?:Section|SECTION) 1\n"
        r"\[content of section 1\]\n"
        r"(?:Section|SECTION) 2\n"
        r"\[content of section 2\]"
    )
    for m in section_pattern.finditer(text):
        _add(out, "detectable_format:multiple_sections", m, {
            "num_sections": int(m.group(1)),
            "section_spliter": m.group(2),
        })

    json_literal = "Entire output should be wrapped in JSON format. You can use markdown ticks such as " + chr(96) * 3 + "."
    for m in re.finditer(re.escape(json_literal), text):
        _add(out, "detectable_format:json_format", m, {})

    for m in re.finditer(
        re.escape("Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>."),
        text,
    ):
        _add(out, "detectable_format:title", m, {})

    for m in re.finditer(
        re.escape("Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******."),
        text,
    ):
        _add(out, "combination:two_responses", m, {})

    repeat_text = (
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; 2. the request "
        "you need to repeat does not include this sentence)"
    )
    for m in re.finditer(re.escape(repeat_text), text):
        _add(out, "combination:repeat_prompt", m, {
            "prompt_to_repeat": None,
            "parameter_status": "VISIBLE_DESCRIPTION_DOES_NOT_ENCODE_HIDDEN_VALUE",
        })

    end_re = re.compile(
        r"Finish your response with this exact phrase ([\s\S]+?)\. "
        r"No other words should follow this phrase\."
    )
    for m in end_re.finditer(text):
        _add(out, "startend:end_checker", m, {"end_phrase": m.group(1).strip()})

    for m in re.finditer(
        r"In your response, words with all capital letters should appear (less than|at least) (\d+) times\.",
        text,
    ):
        _add(out, "change_case:capital_word_frequency", m, {
            "capital_relation": m.group(1),
            "capital_frequency": int(m.group(2)),
        })

    for instruction_id, literal in (
        ("change_case:english_capital", "Your entire response should be in English, and in all capital letters."),
        ("change_case:english_lowercase", "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed."),
        ("punctuation:no_comma", "In your entire response, refrain from the use of any commas."),
        ("startend:quotation", "Wrap your entire response with double quotation marks."),
    ):
        for m in re.finditer(re.escape(literal), text):
            _add(out, instruction_id, m, {})

    out.sort(key=lambda x: (x.start, x.end, x.instruction_id))
    dedup: list[Match] = []
    seen: set[tuple[str, int, int]] = set()
    for item in out:
        key = (item.instruction_id, item.start, item.end)
        if key not in seen:
            seen.add(key)
            dedup.append(item)
    return [x.to_dict() for x in dedup]


def source_surface_coverage() -> dict[str, Any]:
    recognized_ids = set(ACTIVE_IDS)
    return {
        "schema": SCHEMA,
        "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "active_registry_type_count": len(ACTIVE_IDS),
        "recognizer_type_count": len(recognized_ids),
        "all_active_registry_ids_have_recognizer": len(recognized_ids) == 25,
        "repeat_prompt_hidden_parameter_residual": True,
        "hidden_terminal_metadata_read": False,
        "response_witness_authorized": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return {
        "schema": SCHEMA,
        "matches": recognize(str(args.get("prompt") or "")),
        "surface": source_surface_coverage(),
        "terminal_data_used": False,
    }


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(run({"prompt": " ".join(sys.argv[1:])}), indent=2, ensure_ascii=False))
