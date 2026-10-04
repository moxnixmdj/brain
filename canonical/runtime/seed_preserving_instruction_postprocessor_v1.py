#!/usr/bin/env python3
"""Fail-closed postprocessor for applying formal response constraints to a real semantic seed.

This module is benchmark-agnostic. It imports the existing instruction constraint
compiler, applies only transformations that are explicitly semantics-preserving
under this contract, and verifies the final response. Constraints that would
require inventing, deleting, or truncating semantic content fail closed.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from canonical.runtime import instruction_constraint_compiler_v1 as compiler

SCHEMA = "PROJECT_BRAIN_SEED_PRESERVING_INSTRUCTION_POSTPROCESSOR_V1"


class SeedPostprocessError(RuntimeError):
    pass


def _result(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
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

    candidate = seed
    applied: list[str] = []

    # Exact-output instructions define the whole admissible response surface.
    if constraints.exact_response is not None:
        candidate = constraints.exact_response
        applied.append("EXACT_RESPONSE")

    # Case conversion preserves lexical token identity for the compiler's
    # supported structural contract.
    if constraints.lowercase_only:
        candidate = candidate.lower()
        applied.append("LOWERCASE")
    if constraints.uppercase_only:
        candidate = candidate.upper()
        applied.append("UPPERCASE")

    # Prefix/suffix insertion is permitted only because the instruction itself
    # explicitly requires those literal wrappers.
    if constraints.prefix is not None and not candidate.startswith(constraints.prefix):
        candidate = constraints.prefix + candidate
        applied.append("PREFIX")
    if constraints.suffix is not None and not candidate.endswith(constraints.suffix):
        candidate = candidate + constraints.suffix
        applied.append("SUFFIX")

    # Do not invent or delete semantic material merely to satisfy numeric,
    # length, uniqueness, required-literal, or forbidden-literal constraints.
    # If the seed already satisfies them, validation below accepts it.
    ok, errors = compiler.validate_response(candidate, constraints)
    if not ok:
        return _result(
            "FAIL_CLOSED",
            error="UNSAFE_TRANSFORMATION_REQUIRED",
            validation_errors=errors,
            applied_transforms=applied,
            constraints=asdict(constraints),
            response=None,
            seed_preserved=False,
        )

    return _result(
        "PASS",
        response=candidate,
        applied_transforms=applied,
        constraints=asdict(constraints),
        seed_preserved=(candidate == seed),
        exact_postvalidation=True,
        hard_nonclaim=(
            "PASS_PROVES_ONLY_THE_EXISTING_COMPILER_CONSTRAINTS; "
            "IT_DOES_NOT_PROVE_GENERAL_NATURAL_LANGUAGE_INSTRUCTION_FOLLOWING"
        ),
    )


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return transform(
        str(args.get("seed") or args.get("semantic_seed") or ""),
        str(args.get("instruction") or ""),
    )


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("seed")
    ap.add_argument("instruction")
    ns = ap.parse_args()
    print(json.dumps(transform(ns.seed, ns.instruction), indent=2, sort_keys=True))
