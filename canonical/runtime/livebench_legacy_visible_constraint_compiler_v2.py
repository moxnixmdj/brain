#!/usr/bin/env python3
"""Legacy LiveBench visible constraint compiler V2.

V1 remains the exact pinned-source description compiler. V2 composes it with a
prompt-only structural detector for the one legacy scorer parameter that the
canonical description does not render: combination:repeat_prompt.prompt_to_repeat.

This wrapper deliberately avoids mutating V1 so concurrent source-grammar work
can evolve independently. Runtime outputs are promoted to parameter-complete
only when structural segmentation and the existing public-corpus recovery agree.
"""
from __future__ import annotations

from typing import Any

from canonical.runtime.livebench_legacy_visible_constraint_compiler_v1 import (
    LEGACY_REGISTERED_TYPE_COUNT,
    compile_visible_constraints as compile_visible_constraints_v1,
    source_surface as source_surface_v1,
)
from canonical.runtime.livebench_legacy_repeat_prompt_self_detector_v1 import (
    detect_and_recover_legacy_repeat_prompt,
)

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_CONSTRAINT_COMPILER_V2"


def _repeat_constraint(recovery: dict[str, Any]) -> dict[str, Any]:
    return {
        "instruction_id": "combination:repeat_prompt",
        "start": int(recovery["meta_start"]),
        "end": int(recovery["meta_end"]),
        "matched_text": str(recovery["meta_text"]),
        "slots": {"prompt_to_repeat": str(recovery["prompt_to_repeat"])},
        "parameter_complete": True,
        "unresolved_parameters": [],
    }


def compile_visible_constraints(prompt: str) -> dict[str, Any]:
    text = str(prompt or "")
    base = compile_visible_constraints_v1(text)

    constraints = [dict(item) for item in base.get("constraints", [])]
    errors = [dict(item) for item in base.get("parse_errors", [])]
    recovery = detect_and_recover_legacy_repeat_prompt(text)

    repeat_indexes = [
        i for i, item in enumerate(constraints)
        if item.get("instruction_id") == "combination:repeat_prompt"
    ]

    if recovery.get("status") == "PASS":
        recovered = _repeat_constraint(recovery)
        if len(repeat_indexes) > 1:
            errors.append({
                "instruction_id": "combination:repeat_prompt",
                "error": "MULTIPLE_V1_REPEAT_PROMPT_MATCHES",
            })
        elif len(repeat_indexes) == 1:
            constraints[repeat_indexes[0]] = recovered
        else:
            constraints.append(recovered)
    elif recovery.get("status") == "FAIL_CLOSED":
        errors.append({
            "instruction_id": "combination:repeat_prompt",
            "error": str(recovery.get("reason") or "REPEAT_PROMPT_RECOVERY_FAILED"),
        })

    constraints.sort(key=lambda x: (
        int(x.get("start", 0)),
        int(x.get("end", 0)),
        str(x.get("instruction_id", "")),
    ))
    ids = [str(item.get("instruction_id")) for item in constraints]
    duplicates = sorted({x for x in ids if ids.count(x) > 1})
    incomplete = [
        {
            "instruction_id": item["instruction_id"],
            "unresolved_parameters": list(item.get("unresolved_parameters") or []),
        }
        for item in constraints
        if not bool(item.get("parameter_complete"))
    ]

    status = "PASS"
    if base.get("status") != "PASS" or errors or duplicates:
        status = "FAIL_CLOSED"

    return {
        **base,
        "schema": SCHEMA,
        "status": status,
        "constraints": constraints,
        "recognized_type_count": len(set(ids)),
        "parameter_complete_count": sum(
            1 for item in constraints if bool(item.get("parameter_complete"))
        ),
        "parameter_incomplete": incomplete,
        "duplicate_instruction_ids": duplicates,
        "parse_errors": errors,
        "repeat_prompt_structural_recovery": {
            "status": recovery.get("status"),
            "reason": recovery.get("reason"),
            "target_side": recovery.get("target_side"),
            "hidden_kwargs_used": False,
            "instruction_id_list_used": False,
            "terminal_case_metadata_used": False,
        },
        "model_dependency_count": 0,
        "network_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
    }


def source_surface() -> dict[str, Any]:
    base = source_surface_v1()
    return {
        **base,
        "schema": SCHEMA + "_SURFACE",
        "structural_prompt_recovery_types": ["combination:repeat_prompt"],
        "runtime_parameter_complete_type_upper_bound": LEGACY_REGISTERED_TYPE_COUNT,
        "hidden_kwargs_required_for_repeat_prompt": False,
    }


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
    out = source_surface() if ns.surface else compile_visible_constraints(ns.prompt)
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
