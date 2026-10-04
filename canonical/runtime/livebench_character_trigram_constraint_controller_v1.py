#!/usr/bin/env python3
"""Fail-closed visible-prompt controller for frozen LiveBench character-trigram constraints.

This controller is generic over prompt content. It recognizes the public IFBench
ratio-overlap grammar and the two companion constraint families observed with it
in the pinned public population. It never reads hidden kwargs or benchmark case
metadata. Terminal use still requires an exact construction/scope binding.
"""
from __future__ import annotations

import re
import string
import unicodedata
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_CHARACTER_TRIGRAM_CONTROLLER_V1"

RATIO_RE = re.compile(
    r"Maintain a trigram overlap of (\d+(?:\.\d+)?)% \(±2%\) "
    r"with the provided reference text\.",
    re.I,
)
KEYWORD_RE = re.compile(
    r'The response must include keyword\s+["“]?([^"”\s]+)["”]?\s+'
    r"in the (\d+)(?:-st|-nd|-rd|-th) sentence\.",
    re.I,
)
CONSONANT_TEXT = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)
CONSONANTS = set("bcdfghjklmnpqrstvwxyz")


class TrigramControllerError(RuntimeError):
    pass


def _drop_format(value: str) -> str:
    return "".join(ch for ch in str(value or "") if unicodedata.category(ch) != "Cf")


def _norm_ws(value: str) -> str:
    return re.sub(r"\s+", " ", _drop_format(value)).strip()


def char_trigrams(value: str) -> set[str]:
    value = str(value or "")
    return {value[i : i + 3] for i in range(max(0, len(value) - 2))}


def _ratio_score(response: str, reference: str) -> float:
    observed = char_trigrams(response)
    if not observed:
        raise TrigramControllerError("RESPONSE_TRIGRAM_SET_EMPTY")
    target = char_trigrams(reference)
    return 100.0 * len(observed & target) / len(observed)


def _fresh_chars(forbidden: str, n: int, start: int = 0xE000) -> str:
    if n < 0:
        raise TrigramControllerError("NEGATIVE_FRESH_CHARACTER_COUNT")
    out: list[str] = []
    cp = start
    while len(out) < n:
        if cp > 0xF8FF:
            raise TrigramControllerError("PRIVATE_USE_FRESH_CHARACTER_SPACE_EXHAUSTED")
        ch = chr(cp)
        cp += 1
        if ch not in forbidden:
            out.append(ch)
    return "".join(out)


def _substrings(reference_candidate: str):
    for token in re.split(r"\s+", reference_candidate):
        if len(token) < 3:
            continue
        for start in range(len(token)):
            for end in range(start + 3, len(token) + 1):
                yield token[start:end]


def _has_consonant_cluster(word: str) -> bool:
    lowered = word.lower()
    return any(
        lowered[i] in CONSONANTS and lowered[i + 1] in CONSONANTS
        for i in range(len(lowered) - 1)
    )


def parse_visible_prompt(prompt: str) -> dict[str, Any]:
    prompt = str(prompt or "")
    ratio_matches = list(RATIO_RE.finditer(prompt))
    if len(ratio_matches) != 1:
        raise TrigramControllerError("EXACTLY_ONE_RATIO_OVERLAP_CLAUSE_REQUIRED")
    target_percent = float(ratio_matches[0].group(1))
    if not 0 <= target_percent <= 100:
        raise TrigramControllerError("RATIO_TARGET_OUT_OF_RANGE")

    keyword_matches = list(KEYWORD_RE.finditer(prompt))
    if len(keyword_matches) > 1:
        raise TrigramControllerError("MULTIPLE_SENTENCE_KEYWORD_CLAUSES_UNSUPPORTED")
    keyword = None
    if keyword_matches:
        keyword = {
            "word": keyword_matches[0].group(1),
            "sentence_index": int(keyword_matches[0].group(2)),
        }
        if keyword["sentence_index"] < 1:
            raise TrigramControllerError("SENTENCE_INDEX_MUST_BE_POSITIVE")

    consonant_count = prompt.count(CONSONANT_TEXT)
    if consonant_count > 1:
        raise TrigramControllerError("MULTIPLE_CONSONANT_CLAUSES_UNSUPPORTED")
    consonant = consonant_count == 1
    if keyword is not None and consonant:
        raise TrigramControllerError("UNVERIFIED_THREE_WAY_COMPOSITION")

    base = RATIO_RE.sub(" ", prompt)
    base = KEYWORD_RE.sub(" ", base)
    base = base.replace(CONSONANT_TEXT, " ")
    reference_candidate = _norm_ws(base)
    if not reference_candidate:
        raise TrigramControllerError("REFERENCE_CANDIDATE_EMPTY")

    return {
        "target_percent": target_percent,
        "reference_candidate": reference_candidate,
        "sentence_keyword": keyword,
        "consonant_cluster": consonant,
    }


def _choose_ratio_only(reference: str, target: float, *, consonant: bool = False) -> dict[str, Any]:
    best = None
    for block in _substrings(reference):
        if consonant and not _has_consonant_cluster(block):
            continue
        for fresh_count in range(0, 201):
            suffix = _fresh_chars(reference + block, fresh_count)
            response = block + suffix
            score = _ratio_score(response, reference)
            if target - 2.0 <= score <= target + 2.0:
                candidate = (len(response), fresh_count, len(block), block, response, score)
                if best is None or candidate[:4] < best[:4]:
                    best = candidate
    if best is None:
        raise TrigramControllerError("NO_RATIO_CONSTRUCTION_FOUND")
    return {
        "block": best[3],
        "fresh_count": best[1],
        "response": best[4],
        "candidate_reference_score_percent": best[5],
    }


def _choose_sentence_keyword(
    reference: str,
    target: float,
    word: str,
    sentence_index: int,
) -> dict[str, Any]:
    best = None
    for block in _substrings(reference):
        if any(ch in block for ch in ".?!"):
            continue
        for fresh_count in range(0, 201):
            fresh = _fresh_chars(reference + word + block, fresh_count + 2)
            marker = fresh[0]
            tail = fresh[1 : 1 + fresh_count]
            sentences: list[str] = []
            for idx in range(1, sentence_index + 1):
                if idx == 1 and idx == sentence_index:
                    sentences.append(marker + block + marker + tail + marker + word + marker)
                elif idx == 1:
                    sentences.append(marker + block + marker + tail + marker)
                elif idx == sentence_index:
                    sentences.append(marker + word + marker)
                else:
                    sentences.append(marker)
            response = ". ".join(sentences) + "."
            score = _ratio_score(response, reference)
            if target - 2.0 <= score <= target + 2.0:
                candidate = (len(response), fresh_count, len(block), block, response, score)
                if best is None or candidate[:4] < best[:4]:
                    best = candidate
    if best is None:
        raise TrigramControllerError("NO_SENTENCE_KEYWORD_RATIO_CONSTRUCTION_FOUND")
    return {
        "block": best[3],
        "fresh_count": best[1],
        "response": best[4],
        "candidate_reference_score_percent": best[5],
    }


def solve_visible_prompt(prompt: str) -> dict[str, Any]:
    try:
        parsed = parse_visible_prompt(prompt)
        target = parsed["target_percent"]
        reference = parsed["reference_candidate"]
        keyword = parsed["sentence_keyword"]
        consonant = bool(parsed["consonant_cluster"])

        if keyword is not None:
            plan = _choose_sentence_keyword(
                reference,
                target,
                str(keyword["word"]),
                int(keyword["sentence_index"]),
            )
            route = "RATIO_PLUS_SENTENCE_KEYWORD"
        else:
            plan = _choose_ratio_only(reference, target, consonant=consonant)
            route = "RATIO_PLUS_CONSONANT_CLUSTER" if consonant else "RATIO_ONLY"

        return {
            "schema": SCHEMA,
            "status": "PASS_PUBLIC_FAMILY_CONSTRUCTION_CANDIDATE",
            "response": plan["response"],
            "route": route,
            "parsed": parsed,
            "construction": {
                "stable_block": plan["block"],
                "fresh_count": plan["fresh_count"],
                "candidate_reference_score_percent": plan[
                    "candidate_reference_score_percent"
                ],
            },
            "hidden_kwargs_used": False,
            "case_id_used": False,
            "network_used": False,
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
            "required_precondition": (
                "NORMALIZED_VISIBLE_BASE_REQUEST_MUST_EQUAL_NORMALIZED_SCORER_REFERENCE"
            ),
            "hard_nonclaim": (
                "THIS_CONSTRUCTION_PROVES_FORMAL_CONSTRAINT_SATISFIABILITY_ONLY; "
                "IT_DOES_NOT_PROVE_SEMANTIC_BASE_TASK_QUALITY_OR_TERMINAL_DATASET_EQUIVALENCE"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "response": None,
            "error": type(exc).__name__ + ":" + str(exc),
            "hidden_kwargs_used": False,
            "case_id_used": False,
            "network_used": False,
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return solve_visible_prompt(str((args or {}).get("prompt") or (args or {}).get("instruction") or ""))


if __name__ == "__main__":
    import argparse, json

    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(solve_visible_prompt(ns.prompt), indent=2, sort_keys=True))
