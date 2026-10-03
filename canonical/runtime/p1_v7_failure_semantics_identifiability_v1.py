"""Zero-reality identifiability cut for P1 V7 failure semantics.

Construct two full semantic worlds that are identical after projection to the
currently declared frozen public transport schema, but require different V7
behavior. This proves that no deterministic adapter over only that projection
can be universally sound.
"""
from __future__ import annotations

import copy
import json
from typing import Any, Mapping

from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof
from canonical.runtime.p1_v6_derived_only_counterexample_v1 import public_counterexample

SCHEMA = "PROJECT_BRAIN_P1_V7_FAILURE_SEMANTICS_IDENTIFIABILITY_VERDICT_V1"


def _project_without_failure_semantics(public: Mapping[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(dict(public))
    for row in out["task"]["trajectory"]:
        for check in row["checks"]:
            check.pop("failure_semantics", None)
    return out


def _set_failed_semantics(public: Mapping[str, Any], semantics: str) -> dict[str, Any]:
    out = copy.deepcopy(dict(public))
    changed = 0
    for row in out["task"]["trajectory"]:
        for check in row["checks"]:
            if check.get("pass") is False:
                check["failure_semantics"] = semantics
                changed += 1
    if changed == 0:
        raise ValueError("NO_FAILED_CHECK")
    return out


def evaluate() -> dict[str, Any]:
    derived_world = public_counterexample()
    direct_world = _set_failed_semantics(derived_world, "DIRECT_CONTRACT")

    stripped_derived = _project_without_failure_semantics(derived_world)
    stripped_direct = _project_without_failure_semantics(direct_world)
    projection_equal = stripped_derived == stripped_direct

    derived_out = candidate.solve(copy.deepcopy(derived_world))
    direct_out = candidate.solve(copy.deepcopy(direct_world))

    derived_intervention = proof.execute_intervention(copy.deepcopy(derived_world), derived_out)
    direct_intervention = proof.execute_intervention(copy.deepcopy(direct_world), direct_out)

    required_behavior_differs = (
        derived_out.get("status") == "ESCALATE"
        and direct_out.get("status") == "IDENTIFIED"
        and direct_out.get("cause_action_id") == "A1"
        and derived_out != direct_out
    )

    direct_rescues = direct_intervention.get("terminal_rescued") is True
    derived_not_rescued = derived_intervention.get("terminal_rescued") is False

    theorem = (
        projection_equal
        and required_behavior_differs
        and direct_rescues
        and derived_not_rescued
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_FROZEN_TRANSPORT_PROJECTION_UNDERDETERMINES_V7_FAILURE_SEMANTICS__ZERO_CREDIT"
            if theorem
            else "FAIL_CLOSED__IDENTIFIABILITY_COUNTERMODEL_NOT_ESTABLISHED"
        ),
        "theorem_established": theorem,
        "projection_equal_after_removing_failure_semantics": projection_equal,
        "worlds": {
            "derived_upstream": {
                "candidate_status": derived_out.get("status"),
                "candidate_reason": derived_out.get("reason"),
                "terminal_rescued": derived_intervention.get("terminal_rescued"),
            },
            "direct_contract": {
                "candidate_status": direct_out.get("status"),
                "candidate_reason": direct_out.get("reason"),
                "cause_action_id": direct_out.get("cause_action_id"),
                "terminal_rescued": direct_intervention.get("terminal_rescued"),
            },
        },
        "required_behavior_differs": required_behavior_differs,
        "minimum_missing_fact": (
            "FAILURE_SEMANTICS_OR_AN_INDEPENDENTLY_PROVED_EQUIVALENT_DISCRIMINATOR"
            if theorem else None
        ),
        "adapter_consequence": (
            "NO_DETERMINISTIC_ADAPTER_USING_ONLY_CURRENT_PROJECTED_FIELDS_CAN_BE_UNIVERSALLY_SOUND"
            if theorem else None
        ),
        "classification": "INFORMATION_OR_SPECIFICATION_RESIDUAL" if theorem else "UNRESOLVED",
        "terminal_results_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["theorem_established"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
