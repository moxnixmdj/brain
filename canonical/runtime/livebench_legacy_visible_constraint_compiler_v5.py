#!/usr/bin/env python3
"""Multiplicity-safe historical-envelope compiler for frozen legacy LiveBench.

V5 composes the V4 historical suffix isolation with the V3 correction that
same-family instruction instances are valid evaluator inputs. It changes no
recognizer semantics and reads no hidden ids, kwargs, question ids, terminal
responses, scores, case frequencies, or terminal case content.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as v4

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_CONSTRAINT_COMPILER_V5"


def compile_visible_constraints(prompt: str) -> dict[str, Any]:
    out = dict(v4.compile_visible_constraints(str(prompt or "")))
    constraints = list(out.get("constraints") or [])
    counts = Counter(str(c.get("instruction_id") or "") for c in constraints)
    duplicates = {k: v for k, v in sorted(counts.items()) if v > 1}
    parse_errors = list(out.get("parse_errors") or [])
    incomplete = list(out.get("parameter_incomplete") or [])

    # V4 intentionally inherited V1's duplicate-family rejection. The pinned
    # evaluator, however, iterates instruction instances by position. Preserve
    # every instance and fail closed only for an actual parse/parameter failure.
    ok = (
        out.get("error") is None
        and not parse_errors
        and not incomplete
        and bool(constraints)
    )
    out.update(
        {
            "schema": SCHEMA,
            "status": "PASS" if ok else "FAIL_CLOSED",
            "duplicate_instruction_ids": sorted(duplicates),
            "duplicate_instruction_id_counts": duplicates,
            "duplicate_same_family_supported": True,
            "recognized_instruction_instance_count": len(constraints),
            "recognized_instruction_type_count": len(counts),
            "all_recognized_parameters_complete": not incomplete,
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


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    values = args or {}
    return compile_visible_constraints(
        str(values.get("prompt") or values.get("text") or "")
    )


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(
        compile_visible_constraints(ns.prompt),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))
