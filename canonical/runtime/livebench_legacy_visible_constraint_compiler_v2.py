#!/usr/bin/env python3
"""Repeated-instance-safe visible compiler for legacy LiveBench IFEval.

V1 correctly recognizes the 25 public legacy description families, but treated
multiple visible instances of one family as ambiguous. That is not true of the
pinned public IFEval corpus: valid rows may carry two independently rendered
constraints from the same checker family (for example a lower and upper word
count bound).

V2 preserves every visible constraint instance. It changes no parsing grammar,
reads no hidden IDs/kwargs, and still fails closed on actual parse errors.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v1 as v1

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_CONSTRAINT_COMPILER_V2"
FROZEN_LIVEBENCH_COMMIT = v1.FROZEN_LIVEBENCH_COMMIT
FROZEN_INSTRUCTIONS_BLOB = v1.FROZEN_INSTRUCTIONS_BLOB
FROZEN_REGISTRY_BLOB = v1.FROZEN_REGISTRY_BLOB
LEGACY_REGISTERED_TYPE_COUNT = v1.LEGACY_REGISTERED_TYPE_COUNT


def compile_visible_constraints(prompt: str) -> dict[str, Any]:
    base = v1.compile_visible_constraints(str(prompt or ""))
    constraints = list(base.get("constraints") or [])
    parse_errors = list(base.get("parse_errors") or [])

    counts = Counter(str(item.get("instruction_id") or "") for item in constraints)
    repeated = {k: n for k, n in sorted(counts.items()) if k and n > 1}

    # Repetition is not ambiguity. Every instance carries its own source span and
    # recovered visible slots, so downstream solvers can satisfy the conjunction.
    status = "PASS" if not parse_errors else "FAIL_CLOSED"

    return {
        "schema": SCHEMA,
        "status": status,
        "constraints": constraints,
        "recognized_type_count": len([k for k in counts if k]),
        "recognized_instance_count": len(constraints),
        "parameter_complete_count": sum(
            1 for item in constraints if bool(item.get("parameter_complete"))
        ),
        "parameter_incomplete": [
            {
                "instruction_id": item.get("instruction_id"),
                "instance_index": i,
                "unresolved_parameters": list(item.get("unresolved_parameters") or []),
            }
            for i, item in enumerate(constraints)
            if not bool(item.get("parameter_complete"))
        ],
        "repeated_instruction_ids": sorted(repeated),
        "repeated_instruction_instance_counts": repeated,
        "v1_duplicate_fail_closed_would_trigger": bool(repeated),
        "parse_errors": parse_errors,
        "registered_legacy_type_count": LEGACY_REGISTERED_TYPE_COUNT,
        "model_dependency_count": 0,
        "network_used": False,
        "hidden_instruction_id_list_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
        "hard_nonclaim": (
            "VISIBLE_CONSTRAINT_RECOGNITION_ONLY__NO_CHECKER_PASS_SCORE_OR_"
            "SEMANTIC_CAPABILITY_CREDIT"
        ),
    }


def source_surface() -> dict[str, Any]:
    out = dict(v1.source_surface())
    out["schema"] = SCHEMA
    out["repeated_same_family_instances_supported"] = True
    out["repeated_instance_semantics"] = (
        "PRESERVE_EACH_VISIBLE_INSTANCE_AND_SOLVE_THE_CONJUNCTION"
    )
    return out


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    if args.get("surface_only"):
        return source_surface()
    return compile_visible_constraints(str(args.get("prompt") or args.get("text") or ""))


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="?", default="")
    ap.add_argument("--surface", action="store_true")
    ns = ap.parse_args()
    result = source_surface() if ns.surface else compile_visible_constraints(ns.prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
