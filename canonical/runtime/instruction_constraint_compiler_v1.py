#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_INSTRUCTION_CONSTRAINT_COMPILER_V1"


class ConstraintError(RuntimeError):
    pass


@dataclass
class ConstraintSet:
    exact_response: str | None = None
    prefix: str | None = None
    suffix: str | None = None
    min_words: int | None = None
    max_words: int | None = None
    min_unique_words: int | None = None
    exact_numbers: int | None = None
    lowercase_only: bool = False
    uppercase_only: bool = False
    required_literals: tuple[str, ...] = ()
    forbidden_literals: tuple[str, ...] = ()


_QUOTED = r'["“](.+?)["”]'


def _ints(pattern: str, text: str) -> tuple[int, ...] | None:
    m = re.search(pattern, text, flags=re.I | re.S)
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def _quoted(pattern: str, text: str) -> str | None:
    m = re.search(pattern.replace("{Q}", _QUOTED), text, flags=re.I | re.S)
    return m.group(1).strip() if m else None


def compile_constraints(instruction: str) -> ConstraintSet:
    text = " ".join(str(instruction or "").split())
    if not text:
        raise ConstraintError("INSTRUCTION_REQUIRED")

    exact = _quoted(r'(?:respond|reply|answer|output|write|say)\s+(?:with\s+)?exactly\s+{Q}', text)
    if exact is None:
        # Safe unquoted exact-literal route: one atom only. Sentence-final
        # punctuation is syntax, not part of the requested response.
        m = re.fullmatch(
            r'(?:respond|reply|answer|output|write|say)\s+(?:with\s+)?exactly\s+([A-Za-z0-9_][A-Za-z0-9_:-]{0,255})[.!?]?',
            text,
            flags=re.I,
        )
        if m:
            exact = m.group(1)
    prefix = _quoted(r'(?:response|answer|reply)\s+(?:must\s+)?(?:start|begin)\s+with\s+{Q}', text)
    suffix = _quoted(r'(?:response|answer|reply)\s+(?:must\s+)?(?:end|finish)\s+with\s+{Q}', text)

    min_words = max_words = None
    pair = _ints(r'between\s+(\d+)\s+and\s+(\d+)\s+words?', text)
    if pair:
        min_words, max_words = pair
    else:
        exact_words = _ints(r'exactly\s+(\d+)\s+words?', text)
        if exact_words:
            min_words = max_words = exact_words[0]
        at_least = _ints(r'at\s+least\s+(\d+)\s+words?', text)
        if at_least:
            min_words = at_least[0]
        at_most = _ints(r'(?:at\s+most|no\s+more\s+than)\s+(\d+)\s+words?', text)
        if at_most:
            max_words = at_most[0]

    unique = _ints(r'at\s+least\s+(\d+)\s+unique\s+words?', text)
    exact_numbers = _ints(r'exactly\s+(\d+)\s+numbers?', text)

    lower = bool(re.search(r'(?:all|entire(?:ly)?)\s+lowercase|lowercase\s+only', text, re.I))
    upper = bool(re.search(r'(?:all|entire(?:ly)?)\s+uppercase|uppercase\s+only', text, re.I))
    if lower and upper:
        raise ConstraintError("CONTRADICTORY_CASE_CONSTRAINTS")

    required = []
    forbidden = []
    forbidden_pattern = r'(?:must\s+not\s+include|do\s+not\s+include|must\s+not\s+contain|do\s+not\s+contain)\s+(?:the\s+)?(?:word|phrase)\s+{Q}'
    forbidden_spans = []
    for m in re.finditer(forbidden_pattern.replace("{Q}", _QUOTED), text, flags=re.I | re.S):
        value = m.group(1).strip()
        forbidden_spans.append(m.span())
        if value and value not in forbidden:
            forbidden.append(value)

    required_pattern = r'(?<!not\s)(?:must\s+include|include|contain)\s+(?:the\s+)?(?:word|phrase)\s+{Q}'
    for m in re.finditer(required_pattern.replace("{Q}", _QUOTED), text, flags=re.I | re.S):
        if any(a <= m.start() and m.end() <= b for a, b in forbidden_spans):
            continue
        value = m.group(1).strip()
        if value and value not in required:
            required.append(value)

    if min_words is not None and max_words is not None and min_words > max_words:
        raise ConstraintError("WORD_RANGE_CONTRADICTION")
    if unique and max_words is not None and unique[0] > max_words:
        raise ConstraintError("UNIQUE_WORD_REQUIREMENT_EXCEEDS_MAX_WORDS")

    return ConstraintSet(
        exact_response=exact,
        prefix=prefix,
        suffix=suffix,
        min_words=min_words,
        max_words=max_words,
        min_unique_words=(unique[0] if unique else None),
        exact_numbers=(exact_numbers[0] if exact_numbers else None),
        lowercase_only=lower,
        uppercase_only=upper,
        required_literals=tuple(required),
        forbidden_literals=tuple(forbidden),
    )


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text, flags=re.UNICODE)


def validate_response(response: str, c: ConstraintSet) -> tuple[bool, list[str]]:
    value = str(response or "")
    errors = []
    if c.exact_response is not None and value != c.exact_response:
        errors.append("EXACT_RESPONSE")
    if c.prefix is not None and not value.startswith(c.prefix):
        errors.append("PREFIX")
    if c.suffix is not None and not value.endswith(c.suffix):
        errors.append("SUFFIX")
    words = _word_tokens(value)
    if c.min_words is not None and len(words) < c.min_words:
        errors.append("MIN_WORDS")
    if c.max_words is not None and len(words) > c.max_words:
        errors.append("MAX_WORDS")
    if c.min_unique_words is not None and len({w.lower() for w in words}) < c.min_unique_words:
        errors.append("MIN_UNIQUE_WORDS")
    if c.exact_numbers is not None and len(re.findall(r"\b\d+\b", value)) != c.exact_numbers:
        errors.append("EXACT_NUMBERS")
    if c.lowercase_only and value != value.lower():
        errors.append("LOWERCASE_ONLY")
    if c.uppercase_only and value != value.upper():
        errors.append("UPPERCASE_ONLY")
    for lit in c.required_literals:
        if lit not in value:
            errors.append("REQUIRED_LITERAL:" + lit)
    for lit in c.forbidden_literals:
        if lit in value:
            errors.append("FORBIDDEN_LITERAL:" + lit)
    return (not errors, errors)


_FILLER = (
    "amber birch cedar delta ember frost granite harbor ivory juniper kinetic "
    "lumen meadow nectar orbit prairie quartz river summit timber umber velvet "
    "willow xenon yarrow zephyr"
).split()


def synthesize_formal_only(instruction: str) -> dict:
    c = compile_constraints(instruction)

    # Exact response is a true zero-semantic-dependency route.
    if c.exact_response is not None:
        candidate = c.exact_response
        if c.lowercase_only:
            candidate = candidate.lower()
        if c.uppercase_only:
            candidate = candidate.upper()
        ok, errors = validate_response(candidate, c)
        return {
            "schema": SCHEMA,
            "status": "PASS" if ok else "BLOCKED",
            "response": candidate if ok else None,
            "constraints": asdict(c),
            "validation_errors": errors,
            "semantic_seed_required": False,
            "model_dependency_count": 0,
        }

    # For non-exact prompts, only synthesize when every requested feature is structural.
    # This deliberately does NOT pretend to answer an open semantic/content request.
    structural_signal = any([
        c.prefix, c.suffix, c.min_words is not None, c.max_words is not None,
        c.min_unique_words is not None, c.exact_numbers is not None,
        c.lowercase_only, c.uppercase_only, c.required_literals, c.forbidden_literals,
    ])
    if not structural_signal:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "response": None,
            "constraints": asdict(c),
            "validation_errors": ["NO_FORMAL_CONSTRAINT_ROUTE"],
            "semantic_seed_required": True,
            "model_dependency_count": 0,
        }

    target_words = c.min_words or 1
    if c.max_words is not None:
        target_words = min(target_words, c.max_words)
    if c.min_unique_words is not None:
        target_words = max(target_words, c.min_unique_words)
    if c.max_words is not None and target_words > c.max_words:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "response": None,
            "constraints": asdict(c),
            "validation_errors": ["UNSATISFIABLE_WORD_CONSTRAINTS"],
            "semantic_seed_required": True,
            "model_dependency_count": 0,
        }

    words = []
    if c.prefix:
        words.extend(_word_tokens(c.prefix))
    for lit in c.required_literals:
        words.extend(_word_tokens(lit))

    required_number_slots = c.exact_numbers or 0
    if c.max_words is not None and required_number_slots > c.max_words:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "response": None,
            "constraints": asdict(c),
            "validation_errors": ["EXACT_NUMBERS_EXCEED_MAX_WORDS"],
            "semantic_seed_required": True,
            "model_dependency_count": 0,
        }

    i = 0
    while len(words) < max(target_words - required_number_slots, 0):
        words.append(_FILLER[i % len(_FILLER)])
        i += 1
    for n in range(required_number_slots):
        words.append(str(n + 1))
    while len(words) < target_words:
        words.append(_FILLER[i % len(_FILLER)])
        i += 1
    candidate = " ".join(words)
    if c.prefix and not candidate.startswith(c.prefix):
        candidate = c.prefix + (" " if candidate else "") + candidate
    if c.suffix:
        candidate = candidate.rstrip() + (" " if candidate else "") + c.suffix
    if c.lowercase_only:
        candidate = candidate.lower()
    if c.uppercase_only:
        candidate = candidate.upper()

    ok, errors = validate_response(candidate, c)
    return {
        "schema": SCHEMA,
        "status": "FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED" if ok else "BLOCKED",
        "response": candidate if ok else None,
        "constraints": asdict(c),
        "validation_errors": errors,
        "semantic_seed_required": True,
        "model_dependency_count": 0,
    }


def run(args: dict, root=None) -> dict:
    instruction = str((args or {}).get("instruction") or "")
    return synthesize_formal_only(instruction)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("instruction")
    ns = ap.parse_args()
    print(json.dumps(synthesize_formal_only(ns.instruction), indent=2, sort_keys=True))
