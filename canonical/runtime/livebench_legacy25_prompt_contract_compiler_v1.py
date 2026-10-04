#!/usr/bin/env python3
"""Prompt-only contract compiler for the pinned legacy LiveBench IFEval scorer.

Scope:
  LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091
  livebench/if_runner/instruction_following_eval instructions registry and checker source.

This recognizes the 25 ACTIVE legacy registry descriptions from visible prompt
text. It does not consume instruction_id_list or kwargs at inference time.
Unknown text is ignored rather than guessed.

This is score-surface machinery only. It grants no semantic capability credit.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, asdict
import re
from typing import Any, Callable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY25_PROMPT_CONTRACT_COMPILER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

ACTIVE_LEGACY_IDS = (
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

class ContractCompileError(ValueError):
    pass

@dataclass(frozen=True)
class Contract:
    instruction_id: str
    start: int
    end: int
    slots: dict[str, Any]
    matched_text: str
    source: str = "PINNED_LEGACY_BUILD_DESCRIPTION"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()

def _literal_list(value: str) -> list[str]:
    try:
        parsed = ast.literal_eval(value)
    except Exception as exc:
        raise ContractCompileError("INVALID_VISIBLE_LITERAL_LIST") from exc
    if not isinstance(parsed, (list, tuple, set)):
        raise ContractCompileError("VISIBLE_LITERAL_LIST_REQUIRED")
    return [str(x) for x in parsed]

def _typed(d: dict[str, str]) -> dict[str, Any]:
    integer_keys = {
        "frequency","let_frequency","num_sentences","num_paragraphs","num_words",
        "nth_paragraph","num_placeholders","num_bullets","num_highlights",
        "num_sections","capital_frequency",
    }
    out: dict[str, Any] = {}
    for key, value in d.items():
        if value is None:
            continue
        out[key] = int(value) if key in integer_keys else value.strip()
    return out

def _keywords(d: dict[str, str]) -> dict[str, Any]:
    return {"keywords": _literal_list(d["keywords"])}

def _forbidden(d: dict[str, str]) -> dict[str, Any]:
    return {"forbidden_words": _literal_list(d["forbidden_words"])}

def _language(d: dict[str, str]) -> dict[str, Any]:
    name = d["language"].strip()
    code = LANGUAGE_NAME_TO_CODE.get(name)
    if code is None:
        raise ContractCompileError("UNKNOWN_PINNED_LANGUAGE_NAME:" + name)
    return {"language": code, "language_name": name}

def _fixed(_: dict[str, str]) -> dict[str, Any]:
    return {}

_SPECS: tuple[
    tuple[str, re.Pattern[str], Callable[[dict[str, str]], dict[str, Any]]], ...
] = (
    ("keywords:existence",
     re.compile(r"(?<!not )Include keywords (?P<keywords>\[[^\]]*\]) in the response\.", re.I),
     _keywords),
    ("keywords:frequency",
     re.compile(r"In your response, the word (?P<keyword>.+?) should appear (?P<relation>less than|at least) (?P<frequency>\d+) times\.", re.I),
     _typed),
    ("keywords:forbidden_words",
     re.compile(r"Do not include keywords (?P<forbidden_words>\[[^\]]*\]) in the response\.", re.I),
     _forbidden),
    ("keywords:letter_frequency",
     re.compile(r"In your response, the letter (?P<letter>[A-Za-z]) should appear (?P<let_relation>less than|at least) (?P<let_frequency>\d+) times\.", re.I),
     _typed),
    ("language:response_language",
     re.compile(r"Your ENTIRE response should be in (?P<language>.+?) language, no other language is allowed\.", re.I),
     _language),
    ("length_constraints:number_sentences",
     re.compile(r"Your response should contain (?P<relation>less than|at least) (?P<num_sentences>\d+) sentences\.", re.I),
     _typed),
    ("length_constraints:number_paragraphs",
     re.compile(r"There should be (?P<num_paragraphs>\d+) paragraphs\. Paragraphs are separated with the markdown divider: \*\*\*", re.I),
     _typed),
    ("length_constraints:number_words",
     re.compile(r"Answer with (?P<relation>less than|at least) (?P<num_words>\d+) words\.", re.I),
     _typed),
    ("length_constraints:nth_paragraph_first_word",
     re.compile(r"There should be (?P<num_paragraphs>\d+) paragraphs\. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\n\\n' in python\. Paragraph (?P<nth_paragraph>\d+) must start with word (?P<first_word>[^.\s]+)\.", re.I),
     _typed),
    ("detectable_content:number_placeholders",
     re.compile(r"The response must contain at least (?P<num_placeholders>\d+) placeholders represented by square brackets, such as \[address\]\.", re.I),
     _typed),
    ("detectable_content:postscript",
     re.compile(r"At the end of your response, please explicitly add a postscript starting with (?P<postscript_marker>\S+)", re.I),
     _typed),
    ("detectable_format:number_bullet_lists",
     re.compile(r"Your answer must contain exactly (?P<num_bullets>\d+) bullet points\. Use the markdown bullet points such as:", re.I),
     _typed),
    ("detectable_format:constrained_response",
     re.compile(r"Answer with one of the following options: \('My answer is yes\.', 'My answer is no\.', 'My answer is maybe\.'\)", re.I),
     _fixed),
    ("detectable_format:number_highlighted_sections",
     re.compile(r"Highlight at least (?P<num_highlights>\d+) sections in your answer with markdown, i\.e\. \*highlighted section\*\.", re.I),
     _typed),
    ("detectable_format:multiple_sections",
     re.compile(r"Your response must have (?P<num_sections>\d+) sections\. Mark the beginning of each section with (?P<section_spliter>Section|SECTION) X, such as:", re.I),
     _typed),
    ("detectable_format:json_format",
     re.compile(r"Entire output should be wrapped in JSON format\.", re.I),
     _fixed),
    ("detectable_format:title",
     re.compile(r"Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>\.", re.I),
     _fixed),
    ("combination:two_responses",
     re.compile(r"Give two different responses\. Responses and only responses should be separated by 6 asterisk symbols: \*\*\*\*\*\*\.", re.I),
     _fixed),
    ("combination:repeat_prompt",
     re.compile(r"First repeat the request word for word without change, then give your answer \(1\. do not say any words or characters before repeating the request; 2\. the request you need to repeat does not include this sentence\)", re.I),
     _fixed),
    ("startend:end_checker",
     re.compile(r"Finish your response with this exact phrase (?P<end_phrase>.+?)\. No other words should follow this phrase\.", re.I),
     _typed),
    ("change_case:capital_word_frequency",
     re.compile(r"In your response, words with all capital letters should appear (?P<capital_relation>less than|at least) (?P<capital_frequency>\d+) times\.", re.I),
     _typed),
    ("change_case:english_capital",
     re.compile(r"Your entire response should be in English, and in all capital letters\.", re.I),
     _fixed),
    ("change_case:english_lowercase",
     re.compile(r"Your entire response should be in English, and in all lowercase letters\. No capital letters are allowed\.", re.I),
     _fixed),
    ("punctuation:no_comma",
     re.compile(r"In your entire response, refrain from the use of any commas\.", re.I),
     _fixed),
    ("startend:quotation",
     re.compile(r"Wrap your entire response with double quotation marks\.", re.I),
     _fixed),
)

assert tuple(spec[0] for spec in _SPECS) == ACTIVE_LEGACY_IDS

def recognize(prompt: str) -> list[dict[str, Any]]:
    text = _norm(prompt)
    candidates: list[Contract] = []
    for instruction_id, pattern, decoder in _SPECS:
        for match in pattern.finditer(text):
            raw = {k:v for k,v in match.groupdict().items() if v is not None}
            candidates.append(Contract(
                instruction_id=instruction_id,
                start=match.start(),
                end=match.end(),
                slots=decoder(raw),
                matched_text=match.group(0),
            ))
    candidates.sort(key=lambda c: (c.start, c.end, c.instruction_id))
    return [c.to_dict() for c in candidates]

def compile_prompt(prompt: str) -> dict[str, Any]:
    contracts = recognize(prompt)
    return {
        "schema": SCHEMA,
        "status": "PASS" if contracts else "NO_LEGACY_CONTRACT_RECOGNIZED",
        "contracts": contracts,
        "recognized_instruction_ids": [c["instruction_id"] for c in contracts],
        "recognized_count": len(contracts),
        "active_registry_size": len(ACTIVE_LEGACY_IDS),
        "terminal_metadata_used": False,
        "hidden_kwargs_used": False,
        "semantic_capability_credit": False,
    }

def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return compile_prompt(str((args or {}).get("prompt") or ""))

if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    ns = parser.parse_args()
    print(json.dumps(compile_prompt(ns.prompt), indent=2, sort_keys=True))
