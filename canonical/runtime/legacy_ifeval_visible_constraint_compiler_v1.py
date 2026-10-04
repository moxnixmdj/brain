#!/usr/bin/env python3
"""Compile the frozen LiveBench legacy IFEval visible instruction grammar.

This module intentionally consumes only the user-visible prompt text. It never
accepts benchmark kwargs, instruction ids, hidden references, or terminal-case
metadata. Parsed constraints can be applied around an existing semantic seed;
that route preserves the seed verbatim and therefore cannot manufacture
semantic capability from a scorer-only witness.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_LEGACY_IFEVAL_VISIBLE_CONSTRAINT_COMPILER_V1"
PUBLIC_CHECKER_COUNT = 25


class VisibleConstraintError(RuntimeError):
    pass


@dataclass(frozen=True)
class VisibleConstraint:
    kind: str
    params: dict[str, Any]
    matched_text: str


def _list_literal(raw: str) -> list[str]:
    try:
        value = ast.literal_eval(raw)
    except Exception as exc:
        raise VisibleConstraintError("LIST_LITERAL_PARSE_FAILED") from exc
    if not isinstance(value, (list, tuple)) or not all(isinstance(x, str) for x in value):
        raise VisibleConstraintError("LIST_LITERAL_INVALID")
    return list(value)


def _add(out: list[VisibleConstraint], kind: str, m: re.Match[str], **params: Any) -> None:
    out.append(VisibleConstraint(kind=kind, params=params, matched_text=m.group(0)))


def compile_visible_constraints(prompt: str) -> list[VisibleConstraint]:
    text = str(prompt or "")
    if not text.strip():
        raise VisibleConstraintError("PROMPT_REQUIRED")
    out: list[VisibleConstraint] = []

    patterns: list[tuple[str, str, Any]] = [
        ("keywords:existence", r"Include keywords (\[[^\n]*?\]) in the response\.", lambda m: {"keywords": _list_literal(m.group(1))}),
        ("keywords:frequency", r"In your response, the word (.+?) should appear (less than|at least) (\d+) times\.", lambda m: {"keyword": m.group(1).strip(), "relation": m.group(2), "frequency": int(m.group(3))}),
        ("keywords:forbidden_words", r"Do not include keywords (\[[^\n]*?\]) in the response\.", lambda m: {"forbidden_words": _list_literal(m.group(1))}),
        ("keywords:letter_frequency", r"In your response, the letter ([A-Za-z]) should appear (less than|at least) (\d+) times\.", lambda m: {"letter": m.group(1).lower(), "relation": m.group(2), "frequency": int(m.group(3))}),
        ("language:response_language", r"Your ENTIRE response should be in (.+?) language, no other language is allowed\.", lambda m: {"language_name": m.group(1).strip()}),
        ("length_constraints:number_sentences", r"Your response should contain (less than|at least) (\d+) sentences\.", lambda m: {"relation": m.group(1), "num_sentences": int(m.group(2))}),
        ("length_constraints:number_paragraphs", r"There should be (\d+) paragraphs\. Paragraphs are separated with the markdown divider: \*\*\*", lambda m: {"num_paragraphs": int(m.group(1))}),
        ("length_constraints:number_words", r"Answer with (less than|at least) (\d+) words\.", lambda m: {"relation": m.group(1), "num_words": int(m.group(2))}),
        ("length_constraints:nth_paragraph_first_word", r"There should be (\d+) paragraphs\. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '[^']+' in python\. Paragraph (\d+) must start with word ([^\.\s]+)\.", lambda m: {"num_paragraphs": int(m.group(1)), "nth_paragraph": int(m.group(2)), "first_word": m.group(3).lower()}),
        ("detectable_content:number_placeholders", r"The response must contain at least (\d+) placeholders represented by square brackets, such as \[address\]\.", lambda m: {"num_placeholders": int(m.group(1))}),
        ("detectable_content:postscript", r"At the end of your response, please explicitly add a postscript starting with ([^\n]+?)(?=(?:\n|$))", lambda m: {"postscript_marker": m.group(1).strip()}),
        ("detectable_format:number_bullet_lists", r"Your answer must contain exactly (\d+) bullet points\. Use the markdown bullet points such as:", lambda m: {"num_bullets": int(m.group(1))}),
        ("detectable_format:constrained_response", r"Answer with one of the following options: \('My answer is yes\.', 'My answer is no\.', 'My answer is maybe\.'\)", lambda m: {}),
        ("detectable_format:number_highlighted_sections", r"Highlight at least (\d+) sections in your answer with markdown, i\.e\. \*highlighted section\*\.", lambda m: {"num_highlights": int(m.group(1))}),
        ("detectable_format:multiple_sections", r"Your response must have (\d+) sections\. Mark the beginning of each section with (Section|SECTION) X, such as:", lambda m: {"num_sections": int(m.group(1)), "section_splitter": m.group(2)}),
        ("detectable_format:json_format", r"Entire output should be wrapped in JSON format\. You can use markdown ticks such as \`\`\`\.", lambda m: {}),
        ("detectable_format:title", r"Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>\.", lambda m: {}),
        ("combination:two_responses", r"Give two different responses\. Responses and only responses should be separated by 6 asterisk symbols: \*\*\*\*\*\*\.", lambda m: {}),
        ("startend:end_checker", r"Finish your response with this exact phrase (.+?)\. No other words should follow this phrase\.", lambda m: {"end_phrase": m.group(1).strip()}),
        ("change_case:capital_word_frequency", r"In your response, words with all capital letters should appear (less than|at least) (\d+) times\.", lambda m: {"relation": m.group(1), "frequency": int(m.group(2))}),
        ("change_case:english_capital", r"Your entire response should be in English, and in all capital letters\.", lambda m: {}),
        ("change_case:english_lowercase", r"Your entire response should be in English, and in all lowercase letters\. No capital letters are allowed\.", lambda m: {}),
        ("punctuation:no_comma", r"In your entire response, refrain from the use of any commas\.", lambda m: {}),
        ("startend:quotation", r"Wrap your entire response with double quotation marks\.", lambda m: {}),
    ]

    for kind, pattern, parser in patterns:
        for m in re.finditer(pattern, text, flags=re.S):
            _add(out, kind, m, **parser(m))

    repeat_pattern = (
        r"First repeat the request word for word without change, then give your answer "
        r"\(1\. do not say any words or characters before repeating the request; "
        r"2\. the request you need to repeat does not include this sentence\)"
    )
    for m in re.finditer(repeat_pattern, text, flags=re.S):
        request = (text[:m.start()] + text[m.end():]).strip()
        _add(out, "combination:repeat_prompt", m, prompt_to_repeat=request)

    out.sort(key=lambda c: (text.find(c.matched_text), c.kind))
    return out


def kinds(prompt: str) -> tuple[str, ...]:
    return tuple(c.kind for c in compile_visible_constraints(prompt))


def coverage_report(prompt: str) -> dict[str, Any]:
    cs = compile_visible_constraints(prompt)
    unique = sorted({c.kind for c in cs})
    return {
        "schema": SCHEMA,
        "status": "PARSED" if cs else "NO_PUBLIC_LEGACY_CONSTRAINTS_FOUND",
        "constraint_count": len(cs),
        "unique_constraint_type_count": len(unique),
        "constraint_types": unique,
        "public_checker_universe_count": PUBLIC_CHECKER_COUNT,
        "hidden_benchmark_metadata_used": False,
        "terminal_case_content_required": False,
        "network_used": False,
        "model_dependency_count": 0,
        "acceptance_credit": False,
        "capability_credit": False,
        "constraints": [asdict(c) for c in cs],
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return coverage_report(str((args or {}).get("prompt") or ""))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(coverage_report(ns.prompt), indent=2, sort_keys=True))
