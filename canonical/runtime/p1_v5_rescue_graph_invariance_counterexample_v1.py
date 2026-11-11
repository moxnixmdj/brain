"""Executable falsifier for the P1 V5 rescue predicate.

V5 advertises heterogeneous intervention rescue, but evaluate_intervention() does
not execute the visible causal graph. This witness changes the terminal target to
a resource produced before the injected fault. A graph-sensitive intervention
evaluator must change its rescue judgment; V5 does not.
"""
from __future__ import annotations
import copy
import json

from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as v5


def evaluate() -> dict:
    case = v5.generate_case(92001, pattern="SINGLE", domain="CODE", kind="SCOPE")
    root_repair = list(case["_intervention_model"]["required_root_repairs"])

    original = v5.evaluate_intervention(case, root_repair)

    counterexample = copy.deepcopy(case)
    # The terminal objective is now the seed resource written by A0, upstream of
    # the A1 SCOPE fault. Repairing A1 cannot be causal for this terminal target.
    counterexample["task"]["terminal_failed_resources"] = ["code:seed"]
    mutated = v5.evaluate_intervention(counterexample, root_repair)

    return {
        "schema": "PROJECT_BRAIN_P1_V5_RESCUE_GRAPH_INVARIANCE_COUNTEREXAMPLE_V1",
        "status": (
            "COUNTEREXAMPLE__V5_RESCUE_PREDICATE_IS_GRAPH_INSENSITIVE"
            if original.get("rescued") is True and mutated.get("rescued") is True
            else "COUNTEREXAMPLE_NOT_REPRODUCED"
        ),
        "original_terminal_failed_resources": case["task"]["terminal_failed_resources"],
        "mutated_terminal_failed_resources": counterexample["task"]["terminal_failed_resources"],
        "applied_repairs": root_repair,
        "original_v5_verdict": original,
        "mutated_v5_verdict": mutated,
        "load_bearing_fact": (
            "V5_EVALUATE_INTERVENTION_DOES_NOT_READ_TASK_TRAJECTORY_OR_TERMINAL_FAILED_RESOURCES__"
            "ITS_RESCUE_RESULT_IS_DERIVED_FROM_PRECOMPUTED_REQUIRED_ROOT_REPAIRS"
        ),
        "implication": (
            "V5_CANNOT_BY_ITSELF_DISCHARGE_P1_HETEROGENEOUS_INTERVENTION_RESCUE__"
            "A_RESCUE_CARRIER_MUST_APPLY_THE_INTERVENTION_TO_CAUSAL_STATE_AND_RECOMPUTE_TERMINAL_OUTCOME"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
