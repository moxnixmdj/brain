"""Executable falsification audit for P1 V5 intervention-rescue semantics.

This audit asks a narrow question: does the V5 evaluator actually derive terminal
rescue from the trajectory after applying an intervention, or does it accept a
repair because its symbolic name matches hidden oracle data?

No capability, family, execution, promotion, or P1-clearance credit is granted.
"""
from __future__ import annotations

import copy
import json
from typing import Any

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as proof

SCHEMA = "PROJECT_BRAIN_P1_V5_INTERVENTION_REPLAY_SEMANTIC_AUDIT_V1"


def audit() -> dict[str, Any]:
    case = proof.generate_case(
        88001, pattern="DELAYED", domain="BROWSER", kind="SCOPE"
    )
    public = proof.public_task(case)
    baseline_output = candidate.solve(public)
    baseline_score = proof.score_case(case, baseline_output)
    expected_repairs = list(baseline_output.get("repair_targets") or [])
    baseline_intervention = proof.evaluate_intervention(case, expected_repairs)

    counterexamples: list[dict[str, Any]] = []

    # Counterexample 1: delete the entire trajectory after the candidate response.
    # A genuine replay-based rescue checker cannot establish terminal recovery from
    # an empty trajectory. V5 still returns the original score because its scorer
    # consumes hidden oracle labels, not post-intervention trajectory state.
    empty = copy.deepcopy(case)
    empty["task"]["trajectory"] = []
    empty_intervention = proof.evaluate_intervention(empty, expected_repairs)
    empty_score = proof.score_case(empty, baseline_output)
    counterexamples.append(
        {
            "id": "EMPTY_TRAJECTORY_STILL_RESCUES",
            "terminal_replay_possible": False,
            "evaluate_intervention_rescued": empty_intervention.get("rescued"),
            "score_case_pass": empty_score.get("pass"),
        }
    )

    # Counterexample 2: change the declared failed terminal resource to one with no
    # producer. A replay checker must reject rescue because no action can restore it.
    orphan = copy.deepcopy(case)
    orphan["task"]["terminal_failed_resources"] = ["browser:orphan_terminal"]
    orphan_intervention = proof.evaluate_intervention(orphan, expected_repairs)
    orphan_score = proof.score_case(orphan, baseline_output)
    counterexamples.append(
        {
            "id": "ORPHAN_TERMINAL_RESOURCE_STILL_RESCUES",
            "terminal_replay_possible": False,
            "evaluate_intervention_rescued": orphan_intervention.get("rescued"),
            "score_case_pass": orphan_score.get("pass"),
        }
    )

    # Counterexample 3: remove the terminal writer while preserving the rest of the
    # case. The declared terminal resource cannot be produced, yet V5 rescue remains
    # unchanged because evaluate_intervention never consults trajectory structure.
    no_writer = copy.deepcopy(case)
    terminal_resource = no_writer["task"]["terminal_failed_resources"][0]
    no_writer["task"]["trajectory"] = [
        row
        for row in no_writer["task"]["trajectory"]
        if terminal_resource not in (row.get("writes") or [])
    ]
    no_writer_intervention = proof.evaluate_intervention(no_writer, expected_repairs)
    no_writer_score = proof.score_case(no_writer, baseline_output)
    counterexamples.append(
        {
            "id": "TERMINAL_WRITER_REMOVED_STILL_RESCUES",
            "terminal_replay_possible": False,
            "evaluate_intervention_rescued": no_writer_intervention.get("rescued"),
            "score_case_pass": no_writer_score.get("pass"),
        }
    )

    # Counterexample 4: even the hidden terminal-failure marker is ignored.
    marker = copy.deepcopy(case)
    marker["_intervention_model"]["terminal_failure_observed"] = False
    marker_intervention = proof.evaluate_intervention(marker, expected_repairs)
    marker_score = proof.score_case(marker, baseline_output)
    counterexamples.append(
        {
            "id": "TERMINAL_FAILURE_MARKER_IGNORED",
            "terminal_replay_possible": False,
            "evaluate_intervention_rescued": marker_intervention.get("rescued"),
            "score_case_pass": marker_score.get("pass"),
        }
    )

    all_reproduced = all(
        x["evaluate_intervention_rescued"] is True
        and x["score_case_pass"] is True
        for x in counterexamples
    )
    baseline_valid = (
        baseline_score.get("pass") is True
        and baseline_intervention.get("rescued") is True
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__V5_INTERVENTION_REPLAY_CLAIM_FALSIFIED__"
            "REPAIR_IDENTITY_ORACLE_SUBSTITUTION_REPRODUCED__ZERO_CREDIT"
            if baseline_valid and all_reproduced
            else "FAIL_CLOSED__COUNTEREXAMPLE_NOT_REPRODUCED"
        ),
        "baseline_valid": baseline_valid,
        "counterexamples": counterexamples,
        "counterexample_count": len(counterexamples),
        "all_counterexamples_reproduced": all_reproduced,
        "v5_heterogeneous_intervention_rescue_semantics_valid": False
        if baseline_valid and all_reproduced
        else None,
        "finding": (
            "V5_EVALUATE_INTERVENTION_RETURNS_RESCUE_FROM_ORACLE_DERIVED_REPAIR_"
            "SET_INCLUSION_WITHOUT_REPLAYING_TRAJECTORY_OR_TERMINAL_RESOURCE_STATE"
        ),
        "required_correction": (
            "REPLACE_REPAIR_IDENTITY_SUBSET_TEST_WITH_INDEPENDENT_FORWARD_"
            "POST_INTERVENTION_TRAJECTORY_REPLAY__TERMINAL_RESOURCE_MUST_BE_"
            "RECOMPUTED_FROM_CAUSAL_DEPENDENCIES__SYMPTOM_AND_PARTIAL_REPAIRS_"
            "MUST_FAIL_BY_STATE_PROPAGATION_NOT_EXPECTED_LABEL_COMPARISON"
        ),
        "p1_scope_quarantine_clearable_from_v5": False,
        "terminal_results_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = audit()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
