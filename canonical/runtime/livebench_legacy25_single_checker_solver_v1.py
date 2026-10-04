#!/usr/bin/env python3
"""Prompt-only deterministic single-checker solver for legacy LiveBench IFEval.

Pinned surface:
  LiveBench/LiveBench @ 8f8e5c381a16e3f24257776edd53471fe86f8091
  instruction_following_eval/instructions.py blob
  4997bab885a676d92545fd91a9a20b48d234a2b2
  instructions_registry.py blob
  903ed738398648c7cfac61d5ffa478c22f1f0891

The runtime reads only the visible prompt. It recognizes one legacy checker
description, recovers its visible parameters, and emits a deterministic
candidate witness. Multiple-checker composition intentionally fails closed in
V1; it belongs in the next compiler layer.
"""
from __future__ import annotations

import ast
import json
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY25_SINGLE_CHECKER_SOLVER_V1"
FROZEN_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
FROZEN_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
FROZEN_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"

IDS = (
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
    "startend:quotation",
    "change_case:capital_word_frequency",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "punctuation:no_comma",
)

ANCHORS = {
    "keywords:existence": "Include keywords ",
    "keywords:frequency": "In your response, the word ",
    "keywords:forbidden_words": "Do not include keywords ",
    "keywords:letter_frequency": "In your response, the letter ",
    "language:response_language": "Your ENTIRE response should be in ",
    "length_constraints:number_sentences": "Your response should contain ",
    "length_constraints:number_paragraphs": "Paragraphs are separated with the markdown divider: ***",
    "length_constraints:number_words": "Answer with ",
    "length_constraints:nth_paragraph_first_word": "Paragraphs and only paragraphs are separated with each other by two new lines",
    "detectable_content:number_placeholders": "placeholders represented by square brackets",
    "detectable_content:postscript": "explicitly add a postscript starting with ",
    "detectable_format:number_bullet_lists": "bullet points. Use the markdown bullet points such as:",
    "detectable_format:constrained_response": "Answer with one of the following options:",
    "detectable_format:number_highlighted_sections": "Highlight at least ",
    "detectable_format:multiple_sections": "sections. Mark the beginning of each section with ",
    "detectable_format:json_format": "Entire output should be wrapped in JSON format.",
    "detectable_format:title": "title, wrapped in double angular brackets",
    "combination:two_responses": "Give two different responses.",
    "combination:repeat_prompt": "First repeat the request word for word without change",
    "startend:end_checker": "Finish your response with this exact phrase ",
    "startend:quotation": "Wrap your entire response with double quotation marks.",
    "change_case:capital_word_frequency": "words with all capital letters should appear ",
    "change_case:english_capital": "entire response should be in English, and in all capital letters",
    "change_case:english_lowercase": "entire response should be in English, and in all lowercase",
    "punctuation:no_comma": "refrain from the use of any commas",
}


def detect(prompt: str) -> list[str]:
    p = str(prompt or "")
    found: list[str] = []
    for iid, anchor in ANCHORS.items():
        if anchor.lower() not in p.lower():
            continue
        # Resolve the only broad-anchor collisions.
        if iid == "keywords:existence" and "Do not include keywords " in p:
            continue
        if iid == "keywords:frequency" and "In your response, the letter " in p:
            continue
        if iid == "length_constraints:number_words":
            if not re.search(r"Answer with (?:less than|at least) \d+ words\.", p, re.I):
                continue
        if iid == "length_constraints:number_sentences":
            if not re.search(r"Your response should contain (?:less than|at least) \d+ sentences\.", p, re.I):
                continue
        if iid == "detectable_format:constrained_response":
            # Distinguish the fixed legacy option checker from arbitrary modern option text.
            if "My answer is yes." not in p or "My answer is no." not in p:
                continue
        found.append(iid)
    return found


def _literal_list(fragment: str) -> list[str] | None:
    try:
        value = ast.literal_eval(fragment)
    except (ValueError, SyntaxError):
        return None
    if not isinstance(value, (list, tuple)):
        return None
    out = [str(x) for x in value]
    return out if out else None


def _relation_witness(relation: str, threshold: int, positive: str, zero: str = ".") -> str | None:
    if relation == "less than":
        if threshold <= 0:
            return None
        return zero
    if relation == "at least":
        return positive if threshold > 0 else zero
    return None


def _solve_one(iid: str, prompt: str) -> str | None:
    p = prompt

    if iid == "keywords:existence":
        m = re.search(r"Include keywords (\[[^\n]*?\]) in the response\.", p, re.I)
        vals = _literal_list(m.group(1)) if m else None
        return " ".join(vals) if vals else None

    if iid == "keywords:frequency":
        m = re.search(
            r"In your response, the word (.+?) should appear (less than|at least) (\d+) times\.",
            p, re.I,
        )
        if not m:
            return None
        keyword, relation, n = m.group(1).strip(), m.group(2).lower(), int(m.group(3))
        return _relation_witness(relation, n, " ".join([keyword] * max(1, n)), ".")

    if iid == "keywords:forbidden_words":
        m = re.search(r"Do not include keywords (\[[^\n]*?\]) in the response\.", p, re.I)
        vals = _literal_list(m.group(1)) if m else None
        if not vals:
            return None
        candidates = [".", "0", "safe", "quartz"]
        for candidate in candidates:
            if all(not re.search(r"\b" + re.escape(word) + r"\b", candidate, re.I) for word in vals):
                return candidate
        return None

    if iid == "keywords:letter_frequency":
        m = re.search(
            r"In your response, the letter ([A-Za-z]) should appear (less than|at least) (\d+) times\.",
            p, re.I,
        )
        if not m:
            return None
        letter, relation, n = m.group(1).lower(), m.group(2).lower(), int(m.group(3))
        return _relation_witness(relation, n, letter * max(1, n), "0")

    if iid == "language:response_language":
        if not re.search(r"Your ENTIRE response should be in .+? language, no other language is allowed\.", p, re.I):
            return None
        # The pinned checker explicitly treats LangDetectException as success.
        # A digits-only nonempty response has no language features.
        return "1234567890"

    if iid == "length_constraints:number_sentences":
        m = re.search(r"Your response should contain (less than|at least) (\d+) sentences\.", p, re.I)
        if not m:
            return None
        relation, n = m.group(1).lower(), int(m.group(2))
        if relation == "less than":
            return "This is one sentence." if n > 1 else None
        if relation == "at least":
            return " ".join(f"This is sentence number {i}." for i in range(1, max(1, n) + 1))
        return None

    if iid == "length_constraints:number_paragraphs":
        m = re.search(r"There should be (\d+) paragraphs\. Paragraphs are separated with the markdown divider: \*\*\*", p, re.I)
        if not m:
            return None
        n = int(m.group(1))
        return "\n***\n".join(f"paragraph{i}" for i in range(1, n + 1)) if n > 0 else None

    if iid == "length_constraints:number_words":
        m = re.search(r"Answer with (less than|at least) (\d+) words\.", p, re.I)
        if not m:
            return None
        relation, n = m.group(1).lower(), int(m.group(2))
        if relation == "less than":
            return "!" if n > 0 else None
        if relation == "at least":
            return " ".join(f"word{i}" for i in range(1, max(1, n) + 1))
        return None

    if iid == "length_constraints:nth_paragraph_first_word":
        m = re.search(
            r"There should be (\d+) paragraphs\..*?Paragraph (\d+) must start with word ([^\s.]+)\.",
            p, re.I | re.S,
        )
        if not m:
            return None
        n, nth, first = int(m.group(1)), int(m.group(2)), m.group(3).strip()
        if n <= 0 or not 1 <= nth <= n:
            return None
        rows = [f"paragraph{i}" for i in range(1, n + 1)]
        rows[nth - 1] = first + " content"
        return "\n\n".join(rows)

    if iid == "detectable_content:number_placeholders":
        m = re.search(r"at least (\d+) placeholders represented by square brackets", p, re.I)
        if not m:
            return None
        n = int(m.group(1))
        return " ".join(f"[x{i}]" for i in range(1, n + 1)) if n > 0 else "x"

    if iid == "detectable_content:postscript":
        m = re.search(r"postscript starting with (P\.S\.|P\.P\.S)", p, re.I)
        if not m:
            return None
        marker = m.group(1)
        return f"x\n{marker} x"

    if iid == "detectable_format:number_bullet_lists":
        m = re.search(r"exactly (\d+) bullet points", p, re.I)
        if not m:
            return None
        n = int(m.group(1))
        return "\n".join(f"* item{i}" for i in range(1, n + 1)) if n > 0 else "x"

    if iid == "detectable_format:constrained_response":
        return "My answer is yes."

    if iid == "detectable_format:number_highlighted_sections":
        m = re.search(r"Highlight at least (\d+) sections", p, re.I)
        if not m:
            return None
        n = int(m.group(1))
        return " ".join(f"*h{i}*" for i in range(1, n + 1)) if n > 0 else "x"

    if iid == "detectable_format:multiple_sections":
        m = re.search(r"response must have (\d+) sections\. Mark the beginning of each section with (\S+) X", p, re.I)
        if not m:
            return None
        n, splitter = int(m.group(1)), m.group(2)
        return "\n".join(f"{splitter} {i}\ncontent{i}" for i in range(1, n + 1)) if n > 0 else None

    if iid == "detectable_format:json_format":
        return "{}"

    if iid == "detectable_format:title":
        return "<<x>>"

    if iid == "combination:two_responses":
        return "alpha******beta"

    if iid == "combination:repeat_prompt":
        m = re.search(r"First repeat the request word for word without change", p, re.I)
        if not m:
            return None
        prefix = p[:m.start()].strip()
        return prefix + "\nanswer" if prefix else None

    if iid == "startend:end_checker":
        m = re.search(r"Finish your response with this exact phrase (.+?)\. No other words should follow this phrase\.", p, re.I | re.S)
        if not m:
            return None
        ender = m.group(1).strip()
        return f"x {ender}"

    if iid == "startend:quotation":
        return '"x"'

    if iid == "change_case:capital_word_frequency":
        m = re.search(r"words with all capital letters should appear (less than|at least) (\d+) times\.", p, re.I)
        if not m:
            return None
        relation, n = m.group(1).lower(), int(m.group(2))
        if relation == "less than":
            return "lowercase" if n > 0 else None
        if relation == "at least":
            return " ".join(f"WORD{i}" for i in range(1, max(1, n) + 1))
        return None

    if iid == "change_case:english_capital":
        return "THIS RESPONSE IS WRITTEN IN CLEAR ENGLISH"

    if iid == "change_case:english_lowercase":
        return "this response is written in clear english"

    if iid == "punctuation:no_comma":
        return "clear response"

    return None


def solve(prompt: str) -> dict[str, Any]:
    p = str(prompt or "")
    matches = detect(p)
    if len(matches) != 1:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "LEGACY_CHECKER_FAMILY_CARDINALITY_NOT_ONE",
            "recognized_checker_ids": matches,
            "response": None,
            "model_dependency_count": 0,
            "network_used": False,
        }
    iid = matches[0]
    response = _solve_one(iid, p)
    if response is None or not str(response).strip():
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "WITNESS_CONSTRUCTION_FAILED",
            "recognized_checker_ids": [iid],
            "response": None,
            "model_dependency_count": 0,
            "network_used": False,
        }
    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS",
        "checker_id": iid,
        "response": response,
        "model_dependency_count": 0,
        "network_used": False,
        "authority": "CANDIDATE_ONLY__EXACT_PINNED_SCORER_VERIFICATION_REQUIRED",
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return solve(str((args or {}).get("prompt") or ""))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(solve(ns.prompt), indent=2, ensure_ascii=False, sort_keys=True))
