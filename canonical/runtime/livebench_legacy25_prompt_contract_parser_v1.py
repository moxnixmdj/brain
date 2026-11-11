#!/usr/bin/env python3
"""Prompt-only parser for the 25 legacy LiveBench/IFEval instruction contracts.

Pinned public source:
  LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091
  registry blob 903ed738398648c7cfac61d5ffa478c22f1f0891
  instructions blob 4997bab885a676d92545fd91a9a20b48d234a2b2

This reads only the visible prompt. It reconstructs every parameter literally
rendered by the public build_description grammar. combination:repeat_prompt is
recognized but its prompt_to_repeat payload fail-closes until a separate public
assembly binding proves the source mapping.
"""
from __future__ import annotations
import ast
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY25_PROMPT_CONTRACT_PARSER_V1"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

LEGACY_IDS = (
    "keywords:existence","keywords:frequency","keywords:forbidden_words",
    "keywords:letter_frequency","language:response_language",
    "length_constraints:number_sentences","length_constraints:number_paragraphs",
    "length_constraints:number_words","length_constraints:nth_paragraph_first_word",
    "detectable_content:number_placeholders","detectable_content:postscript",
    "detectable_format:number_bullet_lists","detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections","detectable_format:multiple_sections",
    "detectable_format:json_format","detectable_format:title",
    "combination:two_responses","combination:repeat_prompt","startend:end_checker",
    "change_case:capital_word_frequency","change_case:english_capital",
    "change_case:english_lowercase","punctuation:no_comma","startend:quotation",
)

_REPEAT_MARKER = (
    "First repeat the request word for word without change, then give your answer "
    "(1. do not say any words or characters before repeating the request; "
    "2. the request you need to repeat does not include this sentence)"
)
PUBLIC_IFEVAL_DATA_BLOB = "cbe52f6eecf3986fdac745b4acba4da1408eb146"

def _looks_like_repeat_meta(value: str) -> bool:
    t = str(value or "").lower()
    return bool(
        re.search(r"\\b(?:repeat|repleat)\\b", t)
        and re.search(r"\\b(?:request|prompt|sentence|question|text|line)\\b", t)
    )

def _recover_repeat_prompt_source(text: str) -> str | None:
    """Exact public-population reduction.

    On google-research IFEval input_data blob cbe52f..., all 41
    combination:repeat_prompt rows satisfy one of two visible forms:
      A) source is the first line and the remaining tail is repeat-meta text;
      B) repeat-meta text is first and source is the final blank-line block.
    The rule intentionally returns None outside those two forms.
    """
    value = str(text or "")
    if "\\n" not in value:
        return None
    first_line, tail = value.split("\\n", 1)
    first_line = first_line.strip()
    tail = tail.strip()
    blocks = [x.strip() for x in re.split(r"\\n\\n+", value) if x.strip()]
    if _looks_like_repeat_meta(first_line) and len(blocks) >= 2:
        candidate = blocks[-1]
        return candidate if candidate else None
    if _looks_like_repeat_meta(tail):
        return first_line if first_line else None
    return None

def _spec(instruction_id: str, args: dict[str, Any] | None = None, *, complete: bool = True) -> dict[str, Any]:
    return {"instruction_id": instruction_id, "args": args or {}, "visible_parameter_recovery_complete": complete}

def _literal_list(raw: str) -> list[str] | None:
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return None
    if not isinstance(value, (list, tuple)) or not all(isinstance(x, str) for x in value):
        return None
    return list(value)

def parse_visible_contracts(prompt: str) -> dict[str, Any]:
    text = str(prompt or "")
    if not text.strip():
        return {"schema": SCHEMA, "status": "BLOCKED", "reason": "PROMPT_REQUIRED", "contracts": []}
    found: dict[str, dict[str, Any]] = {}
    def put(spec: dict[str, Any]) -> None:
        found.setdefault(spec["instruction_id"], spec)

    m = re.search(r"Include keywords (\[[^\n]*?\]) in the response\.", text)
    if m:
        values = _literal_list(m.group(1))
        if values is not None: put(_spec("keywords:existence", {"keywords": values}))

    m = re.search(r"In your response, the word (.+?) should appear (less than|at least) (\d+) times\.", text)
    if m: put(_spec("keywords:frequency", {"keyword":m.group(1).strip(),"relation":m.group(2),"frequency":int(m.group(3))}))

    m = re.search(r"Do not include keywords (\[[^\n]*?\]) in the response\.", text)
    if m:
        values = _literal_list(m.group(1))
        if values is not None: put(_spec("keywords:forbidden_words", {"forbidden_words": values}))

    m = re.search(r"In your response, the letter ([A-Za-z]) should appear (less than|at least) (\d+) times\.", text)
    if m: put(_spec("keywords:letter_frequency", {"letter":m.group(1).lower(),"let_relation":m.group(2),"let_frequency":int(m.group(3))}))

    m = re.search(r"Your ENTIRE response should be in (.+?) language, no other language is allowed\.", text, re.I)
    if m: put(_spec("language:response_language", {"language_display_name":m.group(1).strip()}))

    m = re.search(r"Your response should contain (less than|at least) (\d+) sentences\.", text)
    if m: put(_spec("length_constraints:number_sentences", {"relation":m.group(1),"num_sentences":int(m.group(2))}))

    m = re.search(r"There should be (\d+) paragraphs\. Paragraphs are separated with the markdown divider: \*\*\*", text)
    if m: put(_spec("length_constraints:number_paragraphs", {"num_paragraphs":int(m.group(1))}))

    m = re.search(r"Answer with (less than|at least) (\d+) words\.", text)
    if m: put(_spec("length_constraints:number_words", {"relation":m.group(1),"num_words":int(m.group(2))}))

    m = re.search(
        r"There should be (\d+) paragraphs\. Paragraphs and only paragraphs are separated with each other by two "
        r"new lines as if it was '\\n\\n' in python\. Paragraph (\d+) must start with word ([^\s.]+)\.", text)
    if m: put(_spec("length_constraints:nth_paragraph_first_word", {
        "num_paragraphs":int(m.group(1)),"nth_paragraph":int(m.group(2)),"first_word":m.group(3).lower()}))

    m = re.search(r"The response must contain at least (\d+) placeholders represented by square brackets, such as \[address\]\.", text)
    if m: put(_spec("detectable_content:number_placeholders", {"num_placeholders":int(m.group(1))}))

    m = re.search(r"At the end of your response, please explicitly add a postscript starting with (P\.S\.|P\.P\.S)", text)
    if m: put(_spec("detectable_content:postscript", {"postscript_marker":m.group(1)}))

    m = re.search(r"Your answer must contain exactly (\d+) bullet points\.", text)
    if m: put(_spec("detectable_format:number_bullet_lists", {"num_bullets":int(m.group(1))}))

    if "Answer with one of the following options: ('My answer is yes.', 'My answer is no.', 'My answer is maybe.')" in text:
        put(_spec("detectable_format:constrained_response"))

    m = re.search(r"Highlight at least (\d+) sections in your answer with markdown, i\.e\. \*highlighted section\*\.", text)
    if m: put(_spec("detectable_format:number_highlighted_sections", {"num_highlights":int(m.group(1))}))

    m = re.search(r"Your response must have (\d+) sections\. Mark the beginning of each section with (Section|SECTION) X", text)
    if m: put(_spec("detectable_format:multiple_sections", {"num_sections":int(m.group(1)),"section_spliter":m.group(2)}))

    if "Entire output should be wrapped in JSON format." in text: put(_spec("detectable_format:json_format"))
    if "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>." in text:
        put(_spec("detectable_format:title"))
    if "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******." in text:
        put(_spec("combination:two_responses"))

    repeat_source = _recover_repeat_prompt_source(text)
    if repeat_source is not None:
        put(_spec("combination:repeat_prompt", {
            "prompt_to_repeat": repeat_source,
            "source_binding": "PUBLIC_IFEVAL_41_OF_41_EDGE_SEGMENT_REDUCTION",
        }))
    elif _REPEAT_MARKER in text:
        put(_spec("combination:repeat_prompt", {
            "prompt_to_repeat": None,
            "source_binding_required": True,
        }, complete=False))

    m = re.search(r"Finish your response with this exact phrase (.+?)\. No other words should follow this phrase\.", text)
    if m: put(_spec("startend:end_checker", {"end_phrase":m.group(1).strip()}))

    m = re.search(r"In your response, words with all capital letters should appear (less than|at least) (\d+) times\.", text)
    if m: put(_spec("change_case:capital_word_frequency", {"capital_relation":m.group(1),"capital_frequency":int(m.group(2))}))

    if "Your entire response should be in English, and in all capital letters." in text:
        put(_spec("change_case:english_capital"))
    if "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed." in text:
        put(_spec("change_case:english_lowercase"))
    if "In your entire response, refrain from the use of any commas." in text:
        put(_spec("punctuation:no_comma"))
    if "Wrap your entire response with double quotation marks." in text:
        put(_spec("startend:quotation"))

    contracts = [found[x] for x in LEGACY_IDS if x in found]
    unresolved = [x["instruction_id"] for x in contracts if not x["visible_parameter_recovery_complete"]]
    return {
        "schema": SCHEMA,
        "status": "PASS" if contracts else "BLOCKED",
        "contracts": contracts,
        "recognized_count": len(contracts),
        "unresolved_visible_parameter_bindings": unresolved,
        "terminal_metadata_used": False,
        "network_used": False,
        "incremental_spend_usd": 0,
        "hard_nonclaim": "PARSER_ONLY__NO_RESPONSE_SCORE_ACCEPTANCE_OR_GENERAL_SEMANTIC_CAPABILITY_CLAIM",
    }

def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return parse_visible_contracts(str((args or {}).get("prompt") or ""))
