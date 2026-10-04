#!/usr/bin/env python3
"""Single contamination-safe entrypoint for the frozen active15 LiveBench surface.

This module does one thing: compile only the visible historical prompt envelope,
route every conflict-compatible active15 identity shape to the existing
constructive composer for its structural archetype, and fail closed otherwise.

It never consumes terminal instruction IDs, kwargs, question IDs, references,
responses, scores, or case metadata. The seven-archetype partition is public
checker/generator structure; this wrapper creates no acceptance credit by itself.
"""
from __future__ import annotations

from typing import Any, Iterable

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler
from canonical.runtime import livebench_legacy15_special_composer_v1 as special
from canonical.runtime import livebench_legacy15_general_composer_v1 as general
from canonical.runtime.livebench_legacy15_composition_archetypes_v1 import (
    archetype,
    compatible,
)

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_UNIFIED_COMPOSER_V1"
ACTIVE_SET_COMMITMENT = "af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"
SPECIAL_ARCHETYPES = frozenset({"JSON", "REPEAT_PROMPT", "TWO_RESPONSES"})
GENERAL_ARCHETYPES = frozenset({"NTH_PARAGRAPH", "STAR_PARAGRAPH", "SENTENCE", "PLAIN"})
SUPPORTED_ARCHETYPES = SPECIAL_ARCHETYPES | GENERAL_ARCHETYPES


def route_for_ids(ids: Iterable[str]) -> str:
    values = tuple(str(x) for x in ids)
    if not values:
        raise ValueError("NO_ACTIVE_IDS")
    if not compatible(values):
        raise ValueError("CONFLICT_INCOMPATIBLE_OR_UNKNOWN_ID_SET")
    mode = archetype(values)
    if mode in SPECIAL_ARCHETYPES:
        return "SPECIAL"
    if mode in GENERAL_ARCHETYPES:
        return "GENERAL"
    raise ValueError("UNSUPPORTED_ARCHETYPE:" + mode)


def compose_visible_prompt(prompt: str) -> dict[str, Any]:
    text = str(prompt or "")
    parsed = compiler.compile_visible_constraints(text)
    if parsed.get("status") != "PASS":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "VISIBLE_COMPILER_NOT_PASS",
            "response": None,
            "terminal_case_content_used": False,
            "terminal_case_metadata_used": False,
            "hidden_instruction_ids_used": False,
            "hidden_kwargs_used": False,
            "acceptance_credit": False,
        }

    constraints = list(parsed.get("constraints") or [])
    ids = tuple(str(c.get("instruction_id")) for c in constraints)
    try:
        route = route_for_ids(ids)
        mode = archetype(ids)
    except ValueError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "instruction_ids": sorted(set(ids)),
            "response": None,
            "terminal_case_content_used": False,
            "terminal_case_metadata_used": False,
            "hidden_instruction_ids_used": False,
            "hidden_kwargs_used": False,
            "acceptance_credit": False,
        }

    result = (
        special.compose_visible_prompt(text)
        if route == "SPECIAL"
        else general.compose_visible_prompt(text)
    )
    response = result.get("response")
    if not str(result.get("status") or "").startswith("PASS") or response is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(result.get("error") or "UNDERLYING_COMPOSER_NOT_PASS"),
            "route": route,
            "archetype": mode,
            "instruction_ids": sorted(set(ids)),
            "response": None,
            "terminal_case_content_used": False,
            "terminal_case_metadata_used": False,
            "hidden_instruction_ids_used": False,
            "hidden_kwargs_used": False,
            "acceptance_credit": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE_UNIFIED_ACTIVE15",
        "route": route,
        "archetype": mode,
        "instruction_ids": sorted(set(ids)),
        "response": response,
        "active_set_commitment": ACTIVE_SET_COMMITMENT,
        "model_dependency_count": 0,
        "network_used": False,
        "terminal_case_content_used": False,
        "terminal_case_metadata_used": False,
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
        "semantic_capability_credit": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return compose_visible_prompt(str((args or {}).get("prompt") or ""))


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(compose_visible_prompt(ns.prompt), ensure_ascii=False, indent=2, sort_keys=True))
