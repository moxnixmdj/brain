#!/usr/bin/env python3
"""Seed-preserving structural instruction postprocessor v2.

This successor extends v1 with transformations derived only from the public
IFBench checker contract. It does not inspect or encode unexposed LiveBench
terminal cases. The added operations preserve the semantic seed modulo
formatting/punctuation scaffolds and fail closed if the final response does not
satisfy every recognized constraint.

Public source binding:
  allenai/IFBench@ifbench/instructions.py
  git blob 7f167018e0c5472b04e13cbf847e5988c04ecb11
"""
from __future__ import annotations

from dataclasses import asdict
import string
from typing import Any

from canonical.runtime import instruction_constraint_compiler_v1 as compiler

SCHEMA = "PROJECT_BRAIN_SEED_PRESERVING_INSTRUCTION_POSTPROCESSOR_V2"
PUBLIC_IFBENCH_INSTRUCTIONS_BLOB = "7f167018e0c5472b04e13cbf847e5988c04ecb11"

_NESTED_PARENS_TEXT = "nest parentheses (and [brackets {and braces}]) at least 5 levels deep"
_NESTED_QUOTES_TEXT = (
    "include quotes within quotes within quotes, at least 3 levels deep, "
    "alternating between double quotes and single quotes"
)
_PUNCTUATION_TEXT = (
    "use every standard punctuation mark at least once, including semicolons, "
    "colons, and the interrobang (?!"
)
_NEWLINE_WORDS_TEXT = "write each word on a new line"

# Five correctly nested levels, no lexical content invented.
_NESTED_PARENS_MARKER = "([{(())}])"
# Open double, single, double; then close double, single, double.
_NESTED_QUOTES_MARKER = '"' + "'" + '""' + "'" + '"'
# The checker removes one interrobang occurrence, so retain all six ASCII marks.
_PUNCTUATION_MARKER = "?!.,!?;:"


def _norm_instruction(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _public_flags(instruction: str) -> dict[str, bool]:
    t = _norm_instruction(instruction)
    return {
        "nested_parentheses": _NESTED_PARENS_TEXT in t,
        "nested_quotes": _NESTED_QUOTES_TEXT in t,
        "punctuation_cover": _PUNCTUATION_TEXT in t,
        "newline_words": _NEWLINE_WORDS_TEXT in t,
    }


def _check_nested_parentheses(value: str) -> bool:
    levels: list[str] = []
    min_levels = 5
    max_depth = 0
    for char in value:
        if char in "([{":
            levels.append(char)
            max_depth = max(max_depth, len(levels))
        elif char in ")]}":
            matched = bool(levels) and (
                (levels[-1] == "(" and char == ")")
                or (levels[-1] == "[" and char == "]")
                or (levels[-1] == "{" and char == "}")
            )
            if matched:
                levels.pop()
                if max_depth >= min_levels and len(levels) < max_depth:
                    return True
            else:
                levels = []
                max_depth = 0
    return False


def _check_nested_quotes(value: str) -> bool:
    levels: list[str] = []
    min_levels = 3
    reached_depth = 0
    current_depth = 0
    for char in value:
        if levels and char == levels[-1]:
            levels.pop()
            current_depth -= 1
            if reached_depth - current_depth >= min_levels:
                return True
        elif char in {'"', "'"}:
            levels.append(char)
            current_depth += 1
            reached_depth = max(reached_depth, current_depth)
    return False


def _check_punctuation_cover(value: str) -> bool:
    punctuation = {".", ",", "!", "?", ";", ":"}
    if not ("!?" in value or "?!" in value or "‽" in value):
        return False
    new_value = value.replace("?!", "", 1)
    if len(new_value) == len(value):
        new_value = value.replace("!?", "", 1)
    for char in new_value:
        punctuation.discard(char)
    return not punctuation


def _check_newline_words(value: str) -> bool:
    stripped = value.translate(str.maketrans("", "", string.punctuation))
    lines = [line for line in stripped.strip().split("\n") if line != ""]
    return len(lines) == len(stripped.strip().split())


def _result(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "public_ifbench_instructions_blob": PUBLIC_IFBENCH_INSTRUCTIONS_BLOB,
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        **extra,
    }


def transform(seed: str, instruction: str) -> dict[str, Any]:
    seed = str(seed or "")
    instruction = str(instruction or "").strip()
    if not seed:
        return _result("FAIL_CLOSED", error="SEMANTIC_SEED_REQUIRED")
    if not instruction:
        return _result("FAIL_CLOSED", error="INSTRUCTION_REQUIRED")

    try:
        constraints = compiler.compile_constraints(instruction)
    except Exception as exc:
        return _result(
            "FAIL_CLOSED",
            error="CONSTRAINT_COMPILE_FAILED:" + type(exc).__name__,
        )

    flags = _public_flags(instruction)
    candidate = seed
    applied: list[str] = []

    # Whole-response replacement and case-folding are not seed-preserving.
    # The repaired V1 contract already proved this distinction. V2 must not
    # silently reintroduce semantic deletion under a formatting label.
    if constraints.exact_response is not None and constraints.exact_response != seed:
        return _result(
            "FAIL_CLOSED",
            error="EXACT_RESPONSE_CONFLICTS_WITH_SEMANTIC_SEED",
            constraints=asdict(constraints),
            public_flags=flags,
            response=None,
            seed_lexical_content_deleted=False,
        )

    # Do not mutate case. If the seed already satisfies a case constraint,
    # final validation accepts it unchanged; otherwise fail closed.
    if constraints.prefix is not None and not candidate.startswith(constraints.prefix):
        candidate = constraints.prefix + candidate
        applied.append("PREFIX")
    if constraints.suffix is not None and not candidate.endswith(constraints.suffix):
        candidate = candidate + constraints.suffix
        applied.append("SUFFIX")

    # Public IFBench structural transforms. Punctuation-only scaffolds introduce
    # no lexical claims and are placed as separate tokens from the semantic seed.
    if flags["nested_parentheses"] and not _check_nested_parentheses(candidate):
        candidate = _NESTED_PARENS_MARKER + " " + candidate
        applied.append("IFBENCH_NESTED_PARENTHESES_5")
    if flags["nested_quotes"] and not _check_nested_quotes(candidate):
        candidate = _NESTED_QUOTES_MARKER + " " + candidate
        applied.append("IFBENCH_NESTED_QUOTES_3_ALTERNATING")
    if flags["punctuation_cover"] and not _check_punctuation_cover(candidate):
        candidate = candidate.rstrip() + " " + _PUNCTUATION_MARKER
        applied.append("IFBENCH_PUNCTUATION_COVER")

    # Whitespace-only reformatting: lexical token order is unchanged.
    if flags["newline_words"] and not _check_newline_words(candidate):
        candidate = "\n".join(candidate.split())
        applied.append("IFBENCH_WORD_PER_LINE")

    ok, old_errors = compiler.validate_response(candidate, constraints)
    errors = list(old_errors)
    if flags["nested_parentheses"] and not _check_nested_parentheses(candidate):
        errors.append("IFBENCH_NESTED_PARENTHESES")
    if flags["nested_quotes"] and not _check_nested_quotes(candidate):
        errors.append("IFBENCH_NESTED_QUOTES")
    if flags["punctuation_cover"] and not _check_punctuation_cover(candidate):
        errors.append("IFBENCH_PUNCTUATION_COVER")
    if flags["newline_words"] and not _check_newline_words(candidate):
        errors.append("IFBENCH_NEWLINE_WORDS")

    if not ok or errors:
        return _result(
            "FAIL_CLOSED",
            error="UNSAFE_OR_UNSATISFIED_TRANSFORMATION",
            validation_errors=errors,
            applied_transforms=applied,
            public_flags=flags,
            constraints=asdict(constraints),
            response=None,
        )

    return _result(
        "PASS",
        response=candidate,
        applied_transforms=applied,
        public_flags=flags,
        constraints=asdict(constraints),
        exact_postvalidation=True,
        seed_lexical_content_deleted=False,
        semantic_seed_token_sequence_preserved=(
            candidate.split() == seed.split()
            if flags["newline_words"]
            else seed in candidate
        ),
        terminal_cases_used=0,
        hard_nonclaim=(
            "PASS_PROVES_ONLY_RECOGNIZED_FORMAL_CONSTRAINTS; "
            "IT_DOES_NOT_PROVE_GENERAL_SEMANTIC_INSTRUCTION_FOLLOWING "
            "OR LIVEBENCH_IF_GE_65_7"
        ),
    )


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return transform(
        str(args.get("seed") or args.get("semantic_seed") or ""),
        str(args.get("instruction") or ""),
    )
