"""TB4 threshold indistinguishability certificate.

Proves only a current-evidence statement: when the bound TB4 frontier contains
fewer certified success slots than the target, yet enough uncertified capacity
remains to make either a pass or a fail completion possible, the threshold
predicate is not determined by the current bound evidence.

This is not a claim that no stronger future theorem can exist. Any new theorem
must add a genuinely new cross-slot premise that distinguishes the two worlds.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TB4_THRESHOLD_INDISTINGUISHABILITY_V1"
FRONTIER_PATH = "canonical/governance/TB4_CURRENT_RESEARCH_FRONTIER_20261008_V1.json"
EVIDENCE_SCAN_PATH = "canonical/governance/TB4_EXISTING_SUCCESS_EVIDENCE_EXHAUSTION_20261008_V1.json"
PARAMETRICITY_PATH = "canonical/governance/TB4_TRIAL_PARAMETRICITY_TRUTH_REPAIR_20261008_V1.json"


def _load(root: Path, relative: str) -> Mapping[str, Any]:
    target=(root/relative).resolve(strict=True)
    target.relative_to(root)
    value=json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("JSON_OBJECT_REQUIRED:"+relative)
    return value


def certify(*, repo_root: str | Path) -> dict[str, Any]:
    try:
        root=Path(repo_root).resolve(strict=True)
        frontier=_load(root, FRONTIER_PATH)
        scan=_load(root, EVIDENCE_SCAN_PATH)
        param=_load(root, PARAMETRICITY_PATH)

        empirical=frontier.get("current_empirical_route")
        stronger=frontier.get("stronger_proof_frontier")
        if not isinstance(empirical, Mapping) or not isinstance(stronger, Mapping):
            raise ValueError("FRONTIER_SHAPE_INVALID")

        k=empirical.get("current_certified_success_slots")
        t=empirical.get("required_success_slots")
        c=empirical.get("current_creditable_slot_capacity")
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (k,t,c)):
            raise ValueError("CARDINALITY_INVALID")
        if not (0 <= k < t <= c):
            raise ValueError("INDETERMINACY_PRECONDITION_FALSE")
        if empirical.get("capacity_is_not_observed_success") is not True:
            raise ValueError("CAPACITY_TRUTH_BINDING_MISSING")

        arithmetic=scan.get("arithmetic")
        conclusion=scan.get("conclusion")
        if not isinstance(arithmetic, Mapping) or not isinstance(conclusion, Mapping):
            raise ValueError("EVIDENCE_SCAN_SHAPE_INVALID")
        if arithmetic.get("existing_certified_success_slots") != k:
            raise ValueError("EXISTING_SUCCESS_COUNT_MISMATCH")
        if arithmetic.get("required_success_slots") != t:
            raise ValueError("TARGET_COUNT_MISMATCH")
        if conclusion.get("existing_internal_evidence_shortcut_exhausted") is not True:
            raise ValueError("EXISTING_EVIDENCE_SEARCH_NOT_EXHAUSTED")

        trial=param.get("trial_parametricity") if isinstance(param.get("trial_parametricity"), Mapping) else None
        # The truth-repair file stores this at top level in current bytes.
        if trial is None:
            legal=param.get("legal_reuse")
            falsified=param.get("falsified_shortcut")
            if not isinstance(legal, Mapping) or not isinstance(falsified, Mapping):
                raise ValueError("PARAMETRICITY_BINDING_INVALID")
            forbidden=set(legal.get("forbidden") or [])
            if "MULTIPLY_ONE_EMPIRICAL_SUCCESS_RECEIPT_BY_FIVE" not in forbidden:
                raise ValueError("ONE_TO_FIVE_SHORTCUT_NOT_REJECTED")
            if falsified.get("verdict") != "NOT_ENTAILED_BY_THE_FROZEN_HARNESS":
                raise ValueError("CROSS_TRIAL_ENTAILMENT_REJECTION_MISSING")

        remaining=stronger.get("remaining_load_bearing_premises")
        if not isinstance(remaining, list) or not remaining:
            raise ValueError("OPEN_THRESHOLD_PREMISE_NOT_BOUND")

        unknown_capacity=c-k
        pass_needed=t-k
        if pass_needed <= 0 or pass_needed > unknown_capacity:
            raise ValueError("PASS_WORLD_CONSTRUCTION_INVALID")

        fail_world={
            "certified_success_slots": k,
            "assigned_additional_successes": 0,
            "assigned_additional_failures_or_unknown_as_failure": unknown_capacity,
            "total_successes": k,
            "threshold_met": False,
        }
        pass_world={
            "certified_success_slots": k,
            "assigned_additional_successes": pass_needed,
            "assigned_remaining_non_successes": unknown_capacity-pass_needed,
            "total_successes": t,
            "threshold_met": True,
        }
        if fail_world["total_successes"] >= t:
            raise ValueError("FAIL_WORLD_DOES_NOT_FAIL")
        if pass_world["total_successes"] < t:
            raise ValueError("PASS_WORLD_DOES_NOT_PASS")

        return {
            "schema": SCHEMA,
            "status": "PASS__CURRENT_BOUND_TB4_EVIDENCE_IS_THRESHOLD_INDETERMINATE",
            "pass": True,
            "predicate": frontier.get("predicate"),
            "known_certified_success_slots": k,
            "required_success_slots": t,
            "creditable_slot_capacity": c,
            "unconstrained_capacity_after_known_success": unknown_capacity,
            "minimum_additional_successes_for_pass_world": pass_needed,
            "fail_world": fail_world,
            "pass_world": pass_world,
            "both_worlds_satisfy_current_cardinality_bounds": True,
            "current_bound_evidence_decides_threshold": False,
            "information_theoretic_indistinguishability_proved": True,
            "current_internal_threshold_derivation_exhausted": True,
            "required_new_information_class": (
                "DISTINGUISHING_TB4_SLOT_OUTCOMES_OR_NEW_SCOPE_COMPLETE_CROSS_SLOT_PREMISE"
            ),
            "future_stronger_theorem_reopens": True,
            "benchmark_execution_authority": False,
            "acceptance_credit_delta": 0,
            "terminal_authority": False,
            "bindings": {
                "frontier": FRONTIER_PATH,
                "existing_evidence_scan": EVIDENCE_SCAN_PATH,
                "trial_parametricity_truth_repair": PARAMETRICITY_PATH,
                "remaining_load_bearing_premises": deepcopy(remaining),
            },
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__+":"+str(exc),
            "information_theoretic_indistinguishability_proved": False,
            "current_internal_threshold_derivation_exhausted": False,
            "benchmark_execution_authority": False,
            "acceptance_credit_delta": 0,
            "terminal_authority": False,
        }
