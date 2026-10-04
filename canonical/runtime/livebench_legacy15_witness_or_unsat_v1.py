#!/usr/bin/env python3
"""Fail-closed witness-or-UNSAT router for the frozen active legacy-15 LiveBench surface.

The corrected proof target is not "every conflict-compatible ID set has a
witness". Concrete visible slot values can make a structurally compatible set
unsatisfiable. This router therefore emits exactly one of:
1) a deterministic candidate witness that still requires exact pinned-checker
   postvalidation, or
2) a checker-semantics UNSAT certificate for an explicitly proved contradiction.

Runtime input is visible prompt text only. No terminal row content, hidden kwargs,
case IDs, prior responses, frequencies, or scores are consumed.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler
from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility
from canonical.runtime import livebench_legacy15_general_composer_v1 as general
from canonical.runtime import livebench_legacy15_special_composer_v1 as special

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_WITNESS_OR_UNSAT_V1"
_SPECIAL_ARCHETYPES = {"JSON", "REPEAT_PROMPT", "TWO_RESPONSES"}


def classify_constraints(constraints: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(c) for c in constraints]
    ids = [str(c.get("instruction_id") or "") for c in rows]
    if not rows:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_VISIBLE_CONSTRAINTS",
            "response": None,
            "terminal_data_used": False,
        }

    disposition = feasibility.classify_visible_contracts(rows)
    status = str(disposition.get("status") or "")
    if status == "PROVED_UNSAT":
        return {
            "schema": SCHEMA,
            "status": "PROVED_UNSAT_VISIBLE_CONTRACT",
            "instruction_ids": sorted(ids),
            "archetype": disposition.get("archetype"),
            "hard_unsat_reasons": list(disposition.get("hard_unsat_reasons") or []),
            "response": None,
            "requires_exact_pinned_checker_postvalidation": False,
            "requires_unsat_semantics_verification": True,
            "terminal_data_used": False,
            "hidden_kwargs_used": False,
            "acceptance_credit": False,
        }

    if status != "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": status or "SLOT_FEASIBILITY_CLASSIFICATION_FAILED",
            "instruction_ids": sorted(ids),
            "response": None,
            "terminal_data_used": False,
            "acceptance_credit": False,
        }

    arch = archetypes.archetype(ids)
    return {
        "schema": SCHEMA,
        "status": "WITNESS_REQUIRED",
        "instruction_ids": sorted(ids),
        "archetype": arch,
        "composer": "SPECIAL" if arch in _SPECIAL_ARCHETYPES else "GENERAL",
        "hard_unsat_reasons": [],
        "response": None,
        "terminal_data_used": False,
        "acceptance_credit": False,
    }


def solve(prompt: str) -> dict[str, Any]:
    parsed = compiler.compile_visible_constraints(str(prompt or ""))
    constraints = list(parsed.get("constraints") or [])
    compiler_complete = (
        parsed.get("status") == "PASS"
        and not list(parsed.get("parameter_incomplete") or [])
        and constraints
        and all(bool(c.get("parameter_complete")) for c in constraints)
    )
    if not compiler_complete:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "VISIBLE_COMPILER_NOT_COMPLETE",
            "response": None,
            "terminal_data_used": False,
            "acceptance_credit": False,
        }

    disposition = classify_constraints(constraints)
    if disposition["status"] != "WITNESS_REQUIRED":
        return disposition

    composer = disposition["composer"]
    if composer == "SPECIAL":
        candidate = special.compose_visible_prompt(prompt)
        expected = "PASS_CANDIDATE_SPECIAL_BRANCH"
    else:
        candidate = general.compose_visible_prompt(prompt)
        expected = "PASS_CANDIDATE_GENERAL_BRANCH"

    if candidate.get("status") != expected or not isinstance(candidate.get("response"), str):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(candidate.get("error") or candidate.get("status") or "COMPOSER_FAILED"),
            "instruction_ids": disposition["instruction_ids"],
            "archetype": disposition["archetype"],
            "composer": composer,
            "response": None,
            "terminal_data_used": False,
            "acceptance_credit": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE_WITNESS",
        "instruction_ids": disposition["instruction_ids"],
        "archetype": disposition["archetype"],
        "composer": composer,
        "response": candidate["response"],
        "requires_exact_pinned_checker_postvalidation": True,
        "requires_unsat_semantics_verification": False,
        "model_dependency_count": 0,
        "network_used": False,
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
        "terminal_case_content_used": False,
        "terminal_data_used": False,
        "acceptance_credit": False,
        "semantic_capability_credit": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return solve(str((args or {}).get("prompt") or ""))


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(solve(ns.prompt), ensure_ascii=False, indent=2, sort_keys=True))
