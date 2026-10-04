#!/usr/bin/env python3
"""Visible-prompt compiler for the exact legacy LiveBench IFEval grammar.

This module is source-derived from the 25 registered legacy instruction classes
at LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091.
It never reads question_id, instruction_id_list, kwargs, answers, or terminal
case metadata. It recognizes the public rendered instruction descriptions in
the visible prompt and recovers only parameters present in those descriptions.

One legacy family, combination:repeat_prompt, intentionally remains parameter-
incomplete: its scorer parameter prompt_to_repeat is not rendered in its public
description. The compiler marks that gap rather than guessing.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import re
from typing import Any, Callable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_CONSTRAINT_COMPILER_V1"
FROZEN_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
FROZEN_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
FROZEN_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
LEGACY_REGISTERED_TYPE_COUNT = 25

_LANGUAGE_NAME_TO_CODE = {
    "English":"en","Spanish":"es","Portuguese":"pt","Arabic":"ar","Hindi":"hi",
    "French":"fr","Russian":"ru","German":"de","Japanese":"ja","Italian":"it",
    "Bengali":"bn","Ukrainian":"uk","Thai":"th","Urdu":"ur","Tamil":"ta",
    "Telugu":"te","Bulgarian":"bg","Korean":"ko","Polish":"pl","Hebrew":"he",
    "Persian":"fa","Vietnamese":"vi","Nepali":"ne","Swahili":"sw","Kannada":"kn",
    "Marathi":"mr","Gujarati":"gu","Punjabi":"pa","Malayalam":"ml","Finnish":"fi",
}

@dataclass(frozen=True)
class Constraint:
    instruction_id: str
    start: int
    end: int
    matched_text: str
    slots: dict[str, Any]
    parameter_complete: bool
    unresolved_parameters: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["unresolved_parameters"] = list(self.unresolved_parameters)
        return out

def _literal_string_list(text: str) -> list[str]:
    value = ast.literal_eval(text)
    if not isinstance(value, (list, tuple)) or not all(isinstance(x, str) for x in value):
        raise ValueError("STRING_SEQUENCE_REQUIRED")
    return list(value)

def _int(v: str) -> int:
    return int(v)

def _language(v: str) -> str:
    if v not in _LANGUAGE_NAME_TO_CODE:
        raise ValueError("UNKNOWN_LANGUAGE_NAME")
    return _LANGUAGE_NAME_TO_CODE[v]

def _identity(v: str) -> str:
    return v.strip()

# id -> (pattern, slot converters, unresolved scorer parameters)
# Patterns are literal renderings of the pinned public build_description methods.
_SPECS: dict[str, tuple[str, dict[str, Callable[[str], Any]], tuple[str, ...]]] = {
    "keywords:existence": (
        r"Include keywords (?P<keywords>\[[^\n]*?\]) in the response\.",
        {"keywords": _literal_string_list}, (),
    ),
    "keywords:frequency": (
        r"In your response, the word (?P<keyword>.+?) should appear (?P<relation>less than|at least) (?P<frequency>\d+) times\.",
        {"keyword": _identity, "relation": _identity, "frequency": _int}, (),
    ),
    "keywords:forbidden_words": (
        r"Do not include keywords (?P<forbidden_words>\[[^\n]*?\]) in the response\.",
        {"forbidden_words": _literal_string_list}, (),
    ),
    "keywords:letter_frequency": (
        r"In your response, the letter (?P<letter>[A-Za-z]) should appear (?P<let_relation>less than|at least) (?P<let_frequency>\d+) times\.",
        {"letter": lambda v: v.lower(), "let_relation": _identity, "let_frequency": _int}, (),
    ),
    "language:response_language": (
        r"Your ENTIRE response should be in (?P<language_name>[A-Za-z]+) language, no other language is allowed\.",
        {"language_name": _identity}, (),
    ),
    "length_constraints:number_sentences": (
        r"Your response should contain (?P<relation>less than|at least) (?P<num_sentences>\d+) sentences\.",
        {"relation": _identity, "num_sentences": _int}, (),
    ),
    "length_constraints:number_paragraphs": (
        r"There should be (?P<num_paragraphs>\d+) paragraphs\. Paragraphs are separated with the markdown divider: \*\*\*",
        {"num_paragraphs": _int}, (),
    ),
    "length_constraints:number_words": (
        r"Answer with (?P<relation>less than|at least) (?P<num_words>\d+) words\.",
        {"relation": _identity, "num_words": _int}, (),
    ),
    "length_constraints:nth_paragraph_first_word": (
        r"There should be (?P<num_paragraphs>\d+) paragraphs\. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\n\\n' in python\. Paragraph (?P<nth_paragraph>\d+) must start with word (?P<first_word>[^.\s]+)\.",
        {"num_paragraphs": _int, "nth_paragraph": _int, "first_word": lambda v: v.lower()}, (),
    ),
    "detectable_content:number_placeholders": (
        r"The response must contain at least (?P<num_placeholders>\d+) placeholders represented by square brackets, such as \[address\]\.",
        {"num_placeholders": _int}, (),
    ),
    "detectable_content:postscript": (
        r"At the end of your response, please explicitly add a postscript starting with (?P<postscript_marker>[^\n]+?)(?=\s*(?:$|Your |The |There |Answer |In your |Finish |Give |First |Wrap |Highlight |Entire ))",
        {"postscript_marker": _identity}, (),
    ),
    "detectable_format:number_bullet_lists": (
        r"Your answer must contain exactly (?P<num_bullets>\d+) bullet points\.",
        {"num_bullets": _int}, (),
    ),
    "detectable_format:constrained_response": (
        r"Answer with one of the following options: \('My answer is yes\.', 'My answer is no\.', 'My answer is maybe\.'\)",
        {}, (),
    ),
    "detectable_format:number_highlighted_sections": (
        r"Highlight at least (?P<num_highlights>\d+) sections in your answer with markdown, i\.e\. \*highlighted section\*\.",
        {"num_highlights": _int}, (),
    ),
    "detectable_format:multiple_sections": (
        r"Your response must have (?P<num_sections>\d+) sections\. Mark the beginning of each section with (?P<section_spliter>Section|SECTION) X, such as:",
        {"num_sections": _int, "section_spliter": _identity}, (),
    ),
    "detectable_format:json_format": (
        r"Entire output should be wrapped in JSON format\. You can use markdown ticks such as ```\.",
        {}, (),
    ),
    "detectable_format:title": (
        r"Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>\.",
        {}, (),
    ),
    "combination:two_responses": (
        r"Give two different responses\. Responses and only responses should be separated by 6 asterisk symbols: \*\*\*\*\*\*\.",
        {}, (),
    ),
    "combination:repeat_prompt": (
        r"First repeat the request word for word without change, then give your answer \(1\. do not say any words or characters before repeating the request; 2\. the request you need to repeat does not include this sentence\)",
        {}, ("prompt_to_repeat",),
    ),
    "startend:end_checker": (
        r"Finish your response with this exact phrase (?P<end_phrase>.+?)\. No other words should follow this phrase\.",
        {"end_phrase": _identity}, (),
    ),
    "change_case:capital_word_frequency": (
        r"In your response, words with all capital letters should appear (?P<capital_relation>less than|at least) (?P<capital_frequency>\d+) times\.",
        {"capital_relation": _identity, "capital_frequency": _int}, (),
    ),
    "change_case:english_capital": (
        r"Your entire response should be in English, and in all capital letters\.",
        {}, (),
    ),
    "change_case:english_lowercase": (
        r"Your entire response should be in English, and in all lowercase letters\. No capital letters are allowed\.",
        {}, (),
    ),
    "punctuation:no_comma": (
        r"In your entire response, refrain from the use of any commas\.",
        {}, (),
    ),
    "startend:quotation": (
        r'Wrap your entire response with double quotation marks\.',
        {}, (),
    ),
}

_COMPILED = {k: re.compile(v[0], flags=re.DOTALL) for k, v in _SPECS.items()}

def _constraint(instruction_id: str, match: re.Match[str]) -> Constraint:
    _, converters, unresolved = _SPECS[instruction_id]
    slots: dict[str, Any] = {}
    for name, raw in match.groupdict().items():
        if raw is None:
            continue
        slots[name] = converters[name](raw)
    if instruction_id == "language:response_language":
        name = str(slots.pop("language_name"))
        slots["language"] = _language(name)
        slots["language_name"] = name
    return Constraint(
        instruction_id=instruction_id,
        start=match.start(),
        end=match.end(),
        matched_text=match.group(0),
        slots=slots,
        parameter_complete=not unresolved,
        unresolved_parameters=unresolved,
    )

def compile_visible_constraints(prompt: str) -> dict[str, Any]:
    prompt = str(prompt or "")
    matches: list[Constraint] = []
    errors: list[dict[str, str]] = []
    for instruction_id, pattern in _COMPILED.items():
        for m in pattern.finditer(prompt):
            try:
                matches.append(_constraint(instruction_id, m))
            except Exception as exc:
                errors.append({"instruction_id": instruction_id, "error": type(exc).__name__})
    matches.sort(key=lambda x: (x.start, x.end, x.instruction_id))

    # Duplicate instances of the same public instruction family are forbidden by
    # the pinned conflict registry. If the visible text appears to contain one,
    # fail closed instead of arbitrarily choosing an instance.
    ids = [m.instruction_id for m in matches]
    duplicates = sorted({x for x in ids if ids.count(x) > 1})

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors and not duplicates else "FAIL_CLOSED",
        "constraints": [m.to_dict() for m in matches],
        "recognized_type_count": len(set(ids)),
        "parameter_complete_count": sum(1 for m in matches if m.parameter_complete),
        "parameter_incomplete": [
            {"instruction_id": m.instruction_id, "unresolved_parameters": list(m.unresolved_parameters)}
            for m in matches if not m.parameter_complete
        ],
        "duplicate_instruction_ids": duplicates,
        "parse_errors": errors,
        "registered_legacy_type_count": LEGACY_REGISTERED_TYPE_COUNT,
        "model_dependency_count": 0,
        "network_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
    }

def source_surface() -> dict[str, Any]:
    ids = sorted(_SPECS)
    return {
        "schema": SCHEMA,
        "instruction_ids": ids,
        "recognized_public_type_count": len(ids),
        "registered_legacy_type_count": LEGACY_REGISTERED_TYPE_COUNT,
        "all_registered_types_covered_by_recognizers": len(ids) == LEGACY_REGISTERED_TYPE_COUNT,
        "fully_visible_parameter_type_count": sum(1 for _, _, u in _SPECS.values() if not u),
        "parameter_incomplete_type_count": sum(1 for _, _, u in _SPECS.values() if u),
        "parameter_incomplete_types": sorted(k for k, (_, _, u) in _SPECS.items() if u),
        "terminal_data_used": False,
    }

def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    if args.get("surface_only"):
        return source_surface()
    return compile_visible_constraints(str(args.get("prompt") or args.get("text") or ""))

if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="?", default="")
    ap.add_argument("--surface", action="store_true")
    ns = ap.parse_args()
    out = source_surface() if ns.surface else compile_visible_constraints(ns.prompt)
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
