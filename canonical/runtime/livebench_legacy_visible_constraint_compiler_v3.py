#!/usr/bin/env python3
"""Multiplicity-safe visible compiler for legacy LiveBench IFEval.

V3 corrects one input-validity error inherited from V1/V2: repeated instances
of the same instruction_id are not intrinsically invalid. The pinned evaluator
iterates instruction_id_list by position and scores each instance with its own
kwargs. Public classic IFEval contains repeated same-family instances.

This module preserves every recognized visible constraint in prompt order and
fails closed only on actual parse errors. It reads no hidden instruction ids,
kwargs, case ids, terminal prompts, responses, or scores.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v2 as v2

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_CONSTRAINT_COMPILER_V3"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_EVALUATOR_SEMANTICS = (
    "FOR_EACH_INDEX_IN_instruction_id_list__BUILD_CHECKER_WITH_kwargs[index]"
)


def compile_visible_constraints(prompt: str) -> dict[str, Any]:
    out = dict(v2.compile_visible_constraints(str(prompt or "")))
    constraints = list(out.get("constraints") or [])
    counts = Counter(str(c.get("instruction_id")) for c in constraints)
    duplicates = {k: v for k, v in sorted(counts.items()) if v > 1}
    parse_errors = list(out.get("parse_errors") or [])

    # V1 treated self-conflict in the generator conflict registry as an input
    # invalidity rule. That is not evaluator semantics. Preserve multiplicity.
    out.update(
        {
            "schema": SCHEMA,
            "status": "PASS" if not parse_errors else "FAIL_CLOSED",
            "duplicate_instruction_ids": sorted(duplicates),
            "duplicate_instruction_id_counts": duplicates,
            "duplicate_same_family_supported": True,
            "recognized_instruction_instance_count": len(constraints),
            "recognized_instruction_type_count": len(counts),
            "multiplicity_semantics": PINNED_EVALUATOR_SEMANTICS,
            "generation_conflict_registry_used_as_input_validity_rule": False,
            "terminal_data_used": False,
            "hidden_instruction_ids_used": False,
            "hidden_kwargs_used": False,
            "terminal_case_metadata_used": False,
            "terminal_case_content_used": False,
            "model_dependency_count": 0,
            "network_used": False,
        }
    )
    return out


def source_surface() -> dict[str, Any]:
    out = dict(v2.source_surface())
    out.update(
        {
            "schema": SCHEMA,
            "duplicate_same_family_supported": True,
            "multiplicity_semantics": PINNED_EVALUATOR_SEMANTICS,
            "generation_conflict_registry_used_as_input_validity_rule": False,
            "terminal_data_used": False,
        }
    )
    return out


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    if args.get("surface_only"):
        return source_surface()
    return compile_visible_constraints(
        str(args.get("prompt") or args.get("text") or "")
    )


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="?", default="")
    ap.add_argument("--surface", action="store_true")
    ns = ap.parse_args()
    result = source_surface() if ns.surface else compile_visible_constraints(ns.prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
