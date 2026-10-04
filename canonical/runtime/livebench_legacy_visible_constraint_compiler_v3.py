#!/usr/bin/env python3
"""Repeated-instance-safe extension of the legacy visible constraint compiler V2.

V2 closes the historical generator lineage and all 25 score-relevant parameter
types. V3 repairs one remaining false fail-closed condition inherited from V1:
multiple visible instances of the same checker family are not intrinsically
ambiguous when each instance has its own source span and recovered slots.

The pinned public Google IFEval corpus contains valid repeated-family rows, so
V3 preserves every instance for downstream conjunctive solving.
"""
from __future__ import annotations

import copy
from collections import Counter
from typing import Any

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v2 as v2

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_CONSTRAINT_COMPILER_V3"
FROZEN_LIVEBENCH_COMMIT = v2.FROZEN_LIVEBENCH_COMMIT
HISTORICAL_GENERATOR_COMMIT = v2.HISTORICAL_GENERATOR_COMMIT
HISTORICAL_GENERATOR_BLOB = v2.HISTORICAL_GENERATOR_BLOB
LEGACY_REGISTERED_TYPE_COUNT = v2.LEGACY_REGISTERED_TYPE_COUNT


def compile_visible_constraints(prompt: str) -> dict[str, Any]:
    base = v2.compile_visible_constraints(str(prompt or ""))
    out = copy.deepcopy(base)
    constraints = list(out.get("constraints") or [])
    parse_errors = list(out.get("parse_errors") or [])

    counts = Counter(str(c.get("instruction_id") or "") for c in constraints)
    repeated_counts = {k: n for k, n in sorted(counts.items()) if k and n > 1}

    # V1/V2 exposed repeated family IDs through duplicate_instruction_ids and
    # used them to force FAIL_CLOSED. That conflates family identity with
    # instance identity. Each parsed instance already carries a distinct span
    # and independent slots, so preserve the conjunction instead.
    prior_duplicate_ids = list(out.get("duplicate_instruction_ids") or [])
    out.update(
        {
            "schema": SCHEMA,
            "status": "PASS" if not parse_errors else "FAIL_CLOSED",
            "recognized_instance_count": len(constraints),
            "repeated_instruction_ids": sorted(repeated_counts),
            "repeated_instruction_instance_counts": repeated_counts,
            "v2_duplicate_instruction_ids_observed": prior_duplicate_ids,
            "duplicate_instruction_ids": [],
            "repeated_instances_are_constraints_not_ambiguity": True,
            "hidden_instruction_ids_used": False,
            "hidden_kwargs_used": False,
            "terminal_case_metadata_used": False,
            "terminal_case_content_used": False,
        }
    )
    return out


def source_surface() -> dict[str, Any]:
    out = dict(v2.source_surface())
    out.update(
        {
            "schema": SCHEMA,
            "repeated_same_family_instances_supported": True,
            "repeated_instance_semantics": (
                "PRESERVE_EACH_VISIBLE_INSTANCE_AND_SOLVE_THE_CONJUNCTION"
            ),
        }
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
