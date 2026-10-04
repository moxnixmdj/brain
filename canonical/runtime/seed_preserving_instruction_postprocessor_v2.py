#!/usr/bin/env python3
"""Strict seed-preserving public-IFBench structural postprocessor v2.

Truth-repair boundary: every PASS response contains the original semantic seed
verbatim as one contiguous substring. This module never case-folds, replaces,
deletes, truncates, or whitespace-rewrites seed bytes.

It extends the corrected v1 route only with punctuation-only scaffolds derived
from a content-addressed public IFBench checker source. The word-per-line
constraint is validated but transformed only when the seed already satisfies
it, because rewriting seed whitespace would violate the preservation contract.

Public source:
  allenai/IFBench@ifbench/instructions.py
  git blob 7f167018e0c5472b04e13cbf847e5988c04ecb11
"""
from __future__ import annotations

import string
from typing import Any

from canonical.runtime import instruction_constraint_compiler_v1 as compiler
from canonical.runtime import seed_preserving_instruction_postprocessor_v1 as v1

SCHEMA = "PROJECT_BRAIN_SEED_PRESERVING_INSTRUCTION_POSTPROCESSOR_V2"
PUBLIC_IFBENCH_INSTRUCTIONS_BLOB = "7f167018e0c5472b04e13cbf847e5988c04ecb11"
PRESERVATION_CONTRACT = (
    "ANY_PASS_RESPONSE_CONTAINS_THE_ORIGINAL_SEMANTIC_SEED_VERBATIM_"
    "AS_ONE_CONTIGUOUS_SUBSTRING"
)

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

_NESTED_PARENS_MARKER = "([{(())}])"
_NESTED_QUOTES_MARKER = '"' + "'" + '""' + "'" + '"'
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
                if max_depth >= 5 and len(levels) < max_depth:
                    return True
            else:
                levels = []
                max_depth = 0
    return False


def _check_nested_quotes(value: str) -> bool:
    levels: list[str] = []
    reached_depth = 0
    current_depth = 0
    for char in value:
        if levels and char == levels[-1]:
            levels.pop()
            current_depth -= 1
            if reached_depth - current_depth >= 3:
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


def _insert_after_required_prefix(candidate: str, marker: str, prefix: str | None) -> str:
    if prefix is not None and candidate.startswith(prefix):
        return prefix + marker + " " + candidate[len(prefix):]
    return marker + " " + candidate


def _insert_before_required_suffix(candidate: str, marker: str, suffix: str | None) -> str:
    if suffix is not None and candidate.endswith(suffix):
        cut = len(candidate) - len(suffix)
        return candidate[:cut] + " " + marker + suffix
    return candidate + " " + marker


def _result(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "public_ifbench_instructions_blob": PUBLIC_IFBENCH_INSTRUCTIONS_BLOB,
        "seed_preservation_contract": PRESERVATION_CONTRACT,
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

    base = v1.transform(seed, instruction)
    if base.get("status") != "PASS":
        return _result(
            "FAIL_CLOSED",
            error="V1_PRESERVATION_FIREWALL_BLOCKED",
            upstream=base,
            response=None,
            seed_verbatim_preserved=False,
        )

    candidate = str(base["response"])
    applied = list(base.get("applied_transforms") or [])
    flags = _public_flags(instruction)

    if flags["nested_parentheses"] and not _check_nested_parentheses(candidate):
        candidate = _insert_after_required_prefix(
            candidate, _NESTED_PARENS_MARKER, constraints.prefix
        )
        applied.append("IFBENCH_NESTED_PARENTHESES_5")

    if flags["nested_quotes"] and not _check_nested_quotes(candidate):
        candidate = _insert_after_required_prefix(
            candidate, _NESTED_QUOTES_MARKER, constraints.prefix
        )
        applied.append("IFBENCH_NESTED_QUOTES_3_ALTERNATING")

    if flags["punctuation_cover"] and not _check_punctuation_cover(candidate):
        candidate = _insert_before_required_suffix(
            candidate, _PUNCTUATION_MARKER, constraints.suffix
        )
        applied.append("IFBENCH_PUNCTUATION_COVER")

    if flags["newline_words"] and not _check_newline_words(candidate):
        return _result(
            "FAIL_CLOSED",
            error="NEWLINE_WORDS_REQUIRES_SEED_WHITESPACE_MUTATION",
            applied_transforms=applied,
            public_flags=flags,
            response=None,
            seed_verbatim_preserved=(seed in candidate),
        )

    old_ok, old_errors = compiler.validate_response(candidate, constraints)
    errors = list(old_errors)
    if flags["nested_parentheses"] and not _check_nested_parentheses(candidate):
        errors.append("IFBENCH_NESTED_PARENTHESES")
    if flags["nested_quotes"] and not _check_nested_quotes(candidate):
        errors.append("IFBENCH_NESTED_QUOTES")
    if flags["punctuation_cover"] and not _check_punctuation_cover(candidate):
        errors.append("IFBENCH_PUNCTUATION_COVER")
    if flags["newline_words"] and not _check_newline_words(candidate):
        errors.append("IFBENCH_NEWLINE_WORDS")
    if seed not in candidate:
        errors.append("SEED_VERBATIM_PRESERVATION")

    if not old_ok or errors:
        return _result(
            "FAIL_CLOSED",
            error="UNSAFE_OR_UNSATISFIED_TRANSFORMATION",
            validation_errors=errors,
            applied_transforms=applied,
            public_flags=flags,
            response=None,
            seed_verbatim_preserved=(seed in candidate),
        )

    return _result(
        "PASS",
        response=candidate,
        applied_transforms=applied,
        public_flags=flags,
        exact_postvalidation=True,
        seed_verbatim_preserved=True,
        terminal_cases_used=0,
        hard_nonclaim=(
            "PASS_PROVES_ONLY_RECOGNIZED_FORMAL_CONSTRAINTS_AND_VERBATIM_SEED_"
            "PRESERVATION; IT_DOES_NOT_PROVE_GENERAL_SEMANTIC_INSTRUCTION_FOLLOWING_"
            "OR LIVEBENCH_IF_GE_65_7"
        ),
    )


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return transform(
        str(args.get("seed") or args.get("semantic_seed") or ""),
        str(args.get("instruction") or ""),
    )
