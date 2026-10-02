"""Fail-closed terminal-goal closure reducer for Project Brain.

This module does not estimate progress. It answers exactly one question:
does the supplied terminal closure manifest prove every required predicate?

Unknown, null, malformed, duplicate, open, contaminated, donor-dependent,
or otherwise unresolved state always reduces to NOT ACHIEVED.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_FAMILY_COUNT = 19
REQUIRED_COUNTERS = (
    "uncontracted_required_behaviors",
    "unproved_required_behaviors",
    "donor_dependent_required_behaviors",
    "unresolved_verifier_mutations",
    "unresolved_composition_failures",
    "contaminated_promotion_evidence",
    "resource_or_authority_violations",
)
REQUIRED_PREDICATES = (
    "exact_target_family_count_19",
    "every_required_behavior_contracted",
    "every_required_behavior_has_admissible_proof",
    "donor_dependent_required_behaviors_zero",
    "unexplained_required_behaviors_zero",
    "unresolved_verifier_mutations_zero",
    "unresolved_composition_failures_zero",
    "contaminated_evidence_used_for_promotion_zero",
    "resource_or_authority_violations_zero",
    "all_frozen_opus_acceptance_predicates_pass",
    "final_donor_deletion_cleanroom_pass",
    "proof_bundle_frozen",
)


def evaluate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    if manifest.get("expected_family_count") != REQUIRED_FAMILY_COUNT:
        failures.append("EXPECTED_FAMILY_COUNT_NOT_19")

    families = manifest.get("families")
    if not isinstance(families, list):
        families = []
        failures.append("FAMILIES_NOT_LIST")

    ids: list[str] = []
    for index, family in enumerate(families):
        if not isinstance(family, dict):
            failures.append(f"FAMILY_{index}_MALFORMED")
            continue
        fid = family.get("id")
        if not isinstance(fid, str) or not fid.strip():
            failures.append(f"FAMILY_{index}_ID_INVALID")
            continue
        ids.append(fid)
        if family.get("closure_state") != "PASS":
            failures.append(f"FAMILY_OPEN:{fid}")

    if len(families) != REQUIRED_FAMILY_COUNT:
        failures.append(f"ACTUAL_FAMILY_COUNT:{len(families)}")
    if len(ids) != len(set(ids)):
        failures.append("DUPLICATE_FAMILY_ID")
    if manifest.get("actual_family_count") != len(families):
        failures.append("DECLARED_ACTUAL_FAMILY_COUNT_MISMATCH")

    counters = manifest.get("counters")
    if not isinstance(counters, dict):
        counters = {}
        failures.append("COUNTERS_NOT_OBJECT")
    for name in REQUIRED_COUNTERS:
        value = counters.get(name)
        if type(value) is not int:
            failures.append(f"COUNTER_UNKNOWN_OR_NONINTEGER:{name}")
        elif value != 0:
            failures.append(f"COUNTER_NONZERO:{name}:{value}")

    predicates = manifest.get("terminal_predicates")
    if not isinstance(predicates, dict):
        predicates = {}
        failures.append("TERMINAL_PREDICATES_NOT_OBJECT")
    for name in REQUIRED_PREDICATES:
        if predicates.get(name) is not True:
            failures.append(f"PREDICATE_NOT_TRUE:{name}")

    # Cross-check counter-backed predicates. A handwritten true may not override
    # a missing/nonzero counter.
    counter_predicates = {
        "donor_dependent_required_behaviors": "donor_dependent_required_behaviors_zero",
        "unresolved_verifier_mutations": "unresolved_verifier_mutations_zero",
        "unresolved_composition_failures": "unresolved_composition_failures_zero",
        "contaminated_promotion_evidence": "contaminated_evidence_used_for_promotion_zero",
        "resource_or_authority_violations": "resource_or_authority_violations_zero",
    }
    for counter, predicate in counter_predicates.items():
        if counters.get(counter) != 0 and predicates.get(predicate) is True:
            failures.append(f"COUNTER_PREDICATE_CONTRADICTION:{counter}:{predicate}")

    unique_failures = sorted(set(failures))
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_CLOSURE_VERDICT_V1",
        "achieved": not unique_failures,
        "failed_predicates": unique_failures,
        "family_count": len(families),
        "closed_family_count": sum(
            1 for family in families
            if isinstance(family, dict) and family.get("closure_state") == "PASS"
        ),
        "rule": "ACHIEVED_IFF_FAILED_PREDICATES_EMPTY",
    }



def evaluate_frontier_state(
    active_hierarchy: dict[str, Any],
    global_universe: dict[str, Any],
    prequalification: dict[str, Any],
) -> dict[str, Any]:
    """Reduce live execution authority from receipt-derived frontier projections.

    The three input manifests are projections, not independent authorities.
    Any disagreement about implementation authority, prequalification, or
    terminal-evidence admission fails closed instead of scheduling more work.
    """
    failures: list[str] = []

    if not all(
        isinstance(x, dict)
        for x in (active_hierarchy, global_universe, prequalification)
    ):
        return {
            "schema": "PROJECT_BRAIN_FRONTIER_STATE_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "execution_authority": False,
            "fresh_terminal_evidence_allowed": False,
            "failed_invariants": ["FRONTIER_INPUT_NOT_OBJECT"],
            "next_action": "RECONCILE_RECEIPT_DERIVED_STATE",
        }

    active_frontier = active_hierarchy.get("atomic_preproof_frontier")
    global_frontier = global_universe.get("atomic_preproof_frontier")
    global_cut = global_universe.get("global_cut")
    global_exec = global_universe.get("execution_authority")
    preq_progress = prequalification.get("prequalification_progress")

    if not isinstance(active_frontier, dict):
        active_frontier = {}
        failures.append("ACTIVE_ATOMIC_FRONTIER_MISSING")
    if not isinstance(global_frontier, dict):
        global_frontier = {}
        failures.append("GLOBAL_ATOMIC_FRONTIER_MISSING")
    if not isinstance(global_cut, dict):
        global_cut = {}
        failures.append("GLOBAL_CUT_MISSING")
    if not isinstance(global_exec, dict):
        global_exec = {}
        failures.append("GLOBAL_EXECUTION_AUTHORITY_MISSING")
    if not isinstance(preq_progress, dict):
        preq_progress = {}
        failures.append("PREQUALIFICATION_PROGRESS_MISSING")

    active_count = active_frontier.get("implementation_authority_count")
    global_count = global_frontier.get(
        "implementation_authority_count",
        global_cut.get("atomic_preproof_survivor_count"),
    )

    if type(active_count) is not int or active_count < 0:
        failures.append("ACTIVE_IMPLEMENTATION_AUTHORITY_COUNT_INVALID")
    if type(global_count) is not int or global_count < 0:
        failures.append("GLOBAL_IMPLEMENTATION_AUTHORITY_COUNT_INVALID")
    if (
        type(active_count) is int
        and type(global_count) is int
        and active_count != global_count
    ):
        failures.append(
            f"IMPLEMENTATION_AUTHORITY_COUNT_CONTRADICTION:{active_count}:{global_count}"
        )

    zero_preproof = preq_progress.get("zero_preproof_implementation_residuals")
    if type(zero_preproof) is not bool:
        failures.append("PREQUALIFICATION_ZERO_PREPROOF_FLAG_INVALID")
    elif type(active_count) is int and zero_preproof != (active_count == 0):
        failures.append(
            "PREQUALIFICATION_ZERO_PREPROOF_CONTRADICTS_ACTIVE_FRONTIER"
        )

    active_execute_now = active_frontier.get("execute_now")
    global_execute_now = global_frontier.get("execute_now")
    if type(active_execute_now) is not bool:
        failures.append("ACTIVE_EXECUTE_NOW_INVALID")
    if type(global_execute_now) is not bool:
        failures.append("GLOBAL_EXECUTE_NOW_INVALID")
    if (
        type(active_execute_now) is bool
        and type(global_execute_now) is bool
        and active_execute_now != global_execute_now
    ):
        failures.append("EXECUTE_NOW_CONTRADICTION")

    preq_authority = prequalification.get("execution_authority")
    if type(preq_authority) is not bool:
        failures.append("PREQUALIFICATION_EXECUTION_AUTHORITY_INVALID")

    global_fresh = global_exec.get("fresh_terminal_evidence_allowed")
    if type(global_fresh) is not bool:
        failures.append("GLOBAL_FRESH_TERMINAL_EVIDENCE_FLAG_INVALID")

    expected_fresh = bool(
        type(preq_authority) is bool
        and preq_authority
        and type(active_count) is int
        and active_count == 0
    )
    if type(global_fresh) is bool and global_fresh != expected_fresh:
        failures.append("FRESH_TERMINAL_EVIDENCE_AUTHORITY_CONTRADICTION")

    unique_failures = sorted(set(failures))
    if unique_failures:
        return {
            "schema": "PROJECT_BRAIN_FRONTIER_STATE_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "execution_authority": False,
            "fresh_terminal_evidence_allowed": False,
            "failed_invariants": unique_failures,
            "implementation_authority_count": (
                active_count if type(active_count) is int else None
            ),
            "next_action": "RECONCILE_RECEIPT_DERIVED_STATE",
        }

    if active_count > 0:
        next_action = "EXECUTE_ONLY_CURRENT_AUTHORIZED_PREPROOF_RESIDUALS"
    elif not preq_authority:
        next_action = "COMPLETE_EXACT_FOUR_PORTFOLIO_PREQUALIFICATION"
    else:
        next_action = "EXECUTE_T0_T1_T2_T3_IN_PARALLEL"

    return {
        "schema": "PROJECT_BRAIN_FRONTIER_STATE_VERDICT_V1",
        "status": "PASS",
        "execution_authority": bool(preq_authority and active_count == 0),
        "fresh_terminal_evidence_allowed": expected_fresh,
        "failed_invariants": [],
        "implementation_authority_count": active_count,
        "prequalification_execution_authority": preq_authority,
        "next_action": next_action,
        "rule": (
            "DERIVED_MANIFEST_DISAGREEMENT_FAILS_CLOSED__"
            "NO_MANIFEST_HAS_INDEPENDENT_AUTHORITY"
        ),
    }


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path)
    parser.add_argument(
        "--frontier",
        nargs=3,
        metavar=("ACTIVE_HIERARCHY", "GLOBAL_UNIVERSE", "PREQUALIFICATION"),
        type=Path,
    )
    args = parser.parse_args()

    if args.frontier:
        if args.manifest is not None:
            parser.error("manifest and --frontier are mutually exclusive")
        active, universe, prequalification = map(_load_json, args.frontier)
        verdict = evaluate_frontier_state(active, universe, prequalification)
        print(json.dumps(verdict, indent=2, sort_keys=True))
        return 0 if verdict["status"] == "PASS" else 1

    if args.manifest is None:
        parser.error("provide manifest or --frontier")
    verdict = evaluate_manifest(_load_json(args.manifest))
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["achieved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
