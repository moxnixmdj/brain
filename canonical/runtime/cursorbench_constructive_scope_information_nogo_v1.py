from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

EXPECTED = {
    "canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V1.json":
        "7401589da3b30954104145dc4959e534ab8cd641",
    "canonical/governance/CURSORBENCH_4_0_OBSERVABLE_TRACE_SCOPE_LIFT_20261009_V1.json":
        "a7bd8397f0c5f7c36acc18fc20d56be76db92680",
    "canonical/governance/CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json":
        "d58c41a8e93fc95df6667e955e291b3f36c8942f",
    "canonical/governance/CURSORBENCH_4_0_PUBLIC_SCORE_ROUTE_NONIDENTIFIABILITY_20261009_V1.json":
        "9812efaa5098eaab3c758563a5825d5e43f6696b",
    "canonical/governance/CODING_V5_TERMINAL_SOUNDNESS_VS_CONSTRUCTIVE_ADEQUACY_SEPARATION_20261009_V1.json":
        "67d4a1878cbbdf4619dea457fd78c56e32c0fdf1",
    "canonical/governance/CURSORBENCH_ROUTE_B_POLICY_COALESCENCE_DISJUNCTION_TRUTH_REPAIR_20261009_V1.json":
        "2342783490431bc36ba98d81606326192ad2fa69",
}

def _blob(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value

def two_world_countermodel(*, same_preterminal_view: bool, accepting_sets_disjoint: bool) -> dict[str, Any]:
    errors: list[str] = []
    if not same_preterminal_view:
        errors.append("WORLDS_DISTINGUISHABLE_PRETERMINALLY")
    if not accepting_sets_disjoint:
        errors.append("ACCEPTING_SETS_NOT_DISJOINT")
    valid = not errors
    return {
        "pass": valid,
        "errors": errors,
        "deterministic_all_members_guarantee_possible": False if valid else None,
        "randomized_probability_one_both_worlds_possible": False if valid else None,
        "proof": (
            "ONE_CONDITIONAL_OUTPUT_DISTRIBUTION_CANNOT_ASSIGN_PROBABILITY_ONE_TO_TWO_DISJOINT_ACCEPTING_SETS"
            if valid else None
        ),
    }

def verify() -> dict[str, Any]:
    errors: list[str] = []
    for rel, expected in EXPECTED.items():
        full = ROOT / rel
        if not full.is_file():
            errors.append("SOURCE_MISSING:" + rel)
        elif _blob(full) != expected:
            errors.append("SOURCE_DRIFT:" + rel)

    if errors:
        return {
            "schema": "PROJECT_BRAIN_CURSORBENCH_CONSTRUCTIVE_SCOPE_NOGO_VERIFIER_V1",
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": errors,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    scope = _load("canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V1.json")
    lift = _load("canonical/governance/CURSORBENCH_4_0_OBSERVABLE_TRACE_SCOPE_LIFT_20261009_V1.json")
    owner = _load("canonical/governance/CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json")
    nonid = _load("canonical/governance/CURSORBENCH_4_0_PUBLIC_SCORE_ROUTE_NONIDENTIFIABILITY_20261009_V1.json")
    sep = _load("canonical/governance/CODING_V5_TERMINAL_SOUNDNESS_VS_CONSTRUCTIVE_ADEQUACY_SEPARATION_20261009_V1.json")
    repair = _load("canonical/governance/CURSORBENCH_ROUTE_B_POLICY_COALESCENCE_DISJUNCTION_TRUTH_REPAIR_20261009_V1.json")

    if scope.get("scope_complete") is not True:
        errors.append("CURSORBENCH_SCOPE_NOT_CLOSED")
    if scope.get("positive_adequacy_cover_closed") is not False:
        errors.append("ADEQUACY_COVER_ALREADY_CLOSED")
    defs = lift.get("definitions") or {}
    if "EXTERNALLY_MEASURABLE_OUTCOME" not in str(defs.get("S_TRACE", "")):
        errors.append("OPAQUE_OUTCOME_PREDICATE_SCOPE_NOT_BOUND")
    owner_facts = set(owner.get("owner_facts") or [])
    if "PRIVATE_AND_HELDOUT_TASKS_STAY_PRIVATE" not in owner_facts:
        errors.append("PRIVATE_HELDOUT_BOUNDARY_NOT_BOUND")
    if (nonid.get("critical_scope_boundary") or {}).get("exact_internal_missing_object") != (
        "SCOPE_COMPLETE_AUTHENTICATED_BRAIN_OWNED_POSITIVE_POLICY_ADEQUACY_CERTIFICATE"
    ):
        errors.append("CURRENT_INTERNAL_MISSING_OBJECT_DRIFT")
    if (sep.get("formal_separation") or {}).get("consequence") != (
        "FORMAL_ALL_MEMBERS_MODE_REQUIRES_AN_ADDITIONAL_CONSTRUCTIVE_LIVENESS_OR_TOTAL_CORRECTNESS_PREMISE_NOT_PRESENT_IN_THE_CURRENT_V5_COMPLETION_CONTRACT"
    ):
        errors.append("V5_SOUNDNESS_LIVENESS_SEPARATION_DRIFT")
    frontier = repair.get("current_global_route_b_frontier") or {}
    if frontier.get("mandatory_next_proof_object") != "CODING_SPEC_SCOPE_COMPLETE_AUTHENTICATED_POLICY_ADEQUACY_COVER":
        errors.append("ROUTE_B_FRONTIER_DRIFT")

    cm = two_world_countermodel(
        same_preterminal_view=True,
        accepting_sets_disjoint=True,
    )
    if cm.get("pass") is not True:
        errors.extend("COUNTERMODEL:" + e for e in cm.get("errors", []))

    passed = not errors
    return {
        "schema": "PROJECT_BRAIN_CURSORBENCH_CONSTRUCTIVE_SCOPE_NOGO_VERIFIER_V1",
        "pass": passed,
        "status": (
            "PASS__CURRENT_INFORMATION_DOES_NOT_ENTAIL_FORMAL_ALL_MEMBERS_ADEQUACY__NEW_TARGET_RELEVANT_INFORMATION_REQUIRED__ZERO_CREDIT"
            if passed else "FAIL_CLOSED"
        ),
        "errors": errors,
        "countermodel": cm,
        "scope_complete": True if passed else False,
        "positive_adequacy_cover_closed": False,
        "actual_cursorbench_conflict_pair_claimed": False,
        "v5_inadequacy_claimed": False,
        "constructive_scope_theorem_from_current_information_only_authorized": False,
        "new_target_relevant_information_required_to_exclude_countermodel": True if passed else None,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
