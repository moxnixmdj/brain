#!/usr/bin/env python3
"""Deterministic pointwise candidate planner for frozen active legacy-15 LiveBench.

The frozen scorer depends only on how many of at most five checkers are true.
This planner uses visible prompt constraints only. It searches constraint subsets
from largest to smallest, discards a subset only when the canonical semantic
kernel proves that subset jointly UNSAT, and emits one deterministic candidate
for the first remaining subset for which the bounded generator succeeds.

It does not inspect hidden terminal rows, hidden kwargs, scores, case IDs, prior
responses, or terminal frequencies. Exact pinned-checker postvalidation and the
pointwise optimality certificate remain separate verification steps.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler
from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_joint_candidate_generator_v1 as generator
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_POINTWISE_CANDIDATE_PLANNER_V1"
MAX_CHECKERS = 5


def _choose_candidate(candidates: Sequence[str], constraints: Sequence[Mapping[str, Any]]) -> str | None:
    if not candidates:
        return None
    sentence = next(
        (c for c in constraints if c.get("instruction_id") == "length_constraints:number_sentences"),
        None,
    )
    if sentence is None:
        return str(candidates[0])
    slots = dict(sentence.get("slots") or {})
    relation = str(slots.get("relation") or "")
    try:
        target = int(slots.get("num_sentences"))
    except (TypeError, ValueError):
        return None

    # The current bounded generator encodes its controllable sentence fillers as
    # bare "!" marks. For an "at least" contract, choose the first candidate
    # with at least target explicit unconditional sentence breaks. For a strict
    # upper bound, choose the candidate with the fewest explicit breaks.
    if relation == "at least":
        for candidate in candidates:
            if str(candidate).count("!") >= target:
                return str(candidate)
        return None
    if relation == "less than":
        return min((str(x) for x in candidates), key=lambda x: (x.count("!"), len(x), x))
    return None


def plan_constraints(constraints: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(c) for c in constraints]
    ids = [str(c.get("instruction_id") or "") for c in rows]
    if not rows or len(rows) > MAX_CHECKERS:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "CONSTRAINT_COUNT_OUT_OF_FROZEN_RANGE",
            "response": None,
            "terminal_data_used": False,
        }
    if len(ids) != len(set(ids)) or not archetypes.compatible(ids):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "DUPLICATE_UNKNOWN_OR_CONFLICTING_ID_SET",
            "response": None,
            "terminal_data_used": False,
        }
    if any(c.get("parameter_complete") is not True for c in rows):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "PARAMETER_INCOMPLETE",
            "response": None,
            "terminal_data_used": False,
        }

    certified_unsat: list[dict[str, Any]] = []
    attempted_subset_count = 0
    n = len(rows)

    for size in range(n, 0, -1):
        for index_tuple in combinations(range(n), size):
            subset = [rows[i] for i in index_tuple]
            disposition = feasibility.classify_visible_contracts(subset)
            if disposition.get("status") == "PROVED_UNSAT":
                certified_unsat.append({
                    "indices": list(index_tuple),
                    "instruction_ids": [ids[i] for i in index_tuple],
                    "hard_unsat_reasons": list(disposition.get("hard_unsat_reasons") or []),
                })
                continue
            if disposition.get("status") != "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED":
                continue

            attempted_subset_count += 1
            generated = generator.generate(subset)
            if generated.get("status") != "PASS_CANDIDATES":
                continue
            candidate = _choose_candidate(list(generated.get("candidates") or []), subset)
            if candidate is None:
                continue
            return {
                "schema": SCHEMA,
                "status": "PASS_POINTWISE_CANDIDATE_PLAN",
                "response": candidate,
                "full_constraint_count": n,
                "selected_constraint_count": size,
                "selected_indices": list(index_tuple),
                "selected_instruction_ids": [ids[i] for i in index_tuple],
                "visible_constraints": rows,
                "certified_unsat_subsets_seen_before_selection": certified_unsat,
                "attempted_satisfiable_or_unknown_subset_count": attempted_subset_count,
                "requires_exact_pinned_checker_postvalidation": True,
                "requires_pointwise_optimality_certificate": True,
                "hidden_instruction_ids_used": False,
                "hidden_kwargs_used": False,
                "terminal_case_metadata_used": False,
                "terminal_data_used": False,
                "network_used": False,
                "model_dependency_count": 0,
                "acceptance_credit": False,
            }

    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "error": "NO_CONSTRUCTIVE_NONUNSAT_SUBSET_FOUND",
        "full_constraint_count": n,
        "certified_unsat_subsets_seen_before_selection": certified_unsat,
        "response": None,
        "terminal_data_used": False,
        "acceptance_credit": False,
    }


def solve(prompt: str) -> dict[str, Any]:
    parsed = compiler.compile_visible_constraints(str(prompt or ""))
    constraints = list(parsed.get("constraints") or [])
    complete = (
        parsed.get("status") == "PASS"
        and not list(parsed.get("parameter_incomplete") or [])
        and constraints
        and all(c.get("parameter_complete") is True for c in constraints)
    )
    if not complete:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "VISIBLE_COMPILER_NOT_COMPLETE",
            "response": None,
            "terminal_data_used": False,
            "acceptance_credit": False,
        }
    return plan_constraints(constraints)


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return solve(str((args or {}).get("prompt") or ""))


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(solve(ns.prompt), ensure_ascii=False, indent=2, sort_keys=True))
