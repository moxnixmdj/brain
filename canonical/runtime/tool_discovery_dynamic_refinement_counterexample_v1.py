"""Exact counterexample to the active Tool Discovery V3 conditional refinement.

The active refinement claims that, under a complete discovery interface, V3's
first selected route is the least-cost admissible evidence-supported route.
This checker constructs a complete-interface world where that claim is false:
a cost-10 visible sufficient route exists, while an unqueried authoritative
discovery source contains a cost-1 sufficient route. V3 probes then selects the
cost-10 route without issuing DISCOVER.
"""
from __future__ import annotations

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_V3_REFINEMENT_COUNTEREXAMPLE_V1"

def _tool(tool_id: str, cost: float) -> dict:
    return {
        "tool_id": tool_id,
        "cost": float(cost),
        "available": True,
        "authorized": True,
        "epoch": 0,
        "meta": {"region": "X", "risk": 0, "tags": ["prod"], "provider": "P"},
    }

def evaluate() -> dict:
    expensive = _tool("VISIBLE_EXPENSIVE", 10)
    cheap = _tool("DISCOVERABLE_CHEAP", 1)

    # The discovery source is authoritative and complete for this frozen scope.
    # V3 can see that the source exists but cannot see its result until DISCOVER.
    public = {
        "required_capabilities": ["CAP_A"],
        "constraint": None,
        "visible_tools": [expensive],
        "discovery_sources": [
            {"source_id": "COMPLETE_SOURCE", "cost": 0.1, "available": True}
        ],
        "prior_probe_receipts": [],
        "discovery_receipts": [],
        "version_events": [],
    }

    first = v3.next_action(public)
    if first != {
        "action": "PROBE",
        "tool_id": "VISIBLE_EXPENSIVE",
        "capability": "CAP_A",
    }:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__V3_BEHAVIOR_DRIFT",
            "first_action": first,
            "counterexample_reproduced": False,
        }

    public["prior_probe_receipts"].append({
        "kind": "SAFE_CAPABILITY_PROBE",
        "tool_id": "VISIBLE_EXPENSIVE",
        "capability": "CAP_A",
        "epoch": 0,
        "supported": True,
    })
    second = v3.next_action(public)

    complete_interface_instance = {
        "finite_discovery_source_set_per_decision_epoch": True,
        "discovery_receipt_identifies_queried_source": True,
        "discovery_results_monotonically_add_visible_tool_identities_within_epoch": True,
        "union_of_authoritative_discovery_results_is_complete_for_declared_target_scope": True,
        "discovered_tool_metadata_correct_for_availability_authorization_cost_and_constraint_fields": True,
        "safe_capability_probe_receipts_truthful_and_epoch_bound": True,
        "version_epoch_stable_during_one_selection_episode_or_restarts_episode": True,
        "authoritative_result_if_queried": [cheap],
        "capability_truth": {
            "VISIBLE_EXPENSIVE": {"CAP_A": True},
            "DISCOVERABLE_CHEAP": {"CAP_A": True},
        },
    }

    reproduced = (
        second == {"action": "SELECT", "tool_id": "VISIBLE_EXPENSIVE"}
        and len(public["discovery_receipts"]) == 0
        and complete_interface_instance[
            "union_of_authoritative_discovery_results_is_complete_for_declared_target_scope"
        ]
        and cheap["cost"] < expensive["cost"]
        and complete_interface_instance["capability_truth"]["DISCOVERABLE_CHEAP"]["CAP_A"]
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ACTIVE_V3_CONDITIONAL_REFINEMENT_FALSIFIED"
            if reproduced else "FAIL_CLOSED__COUNTEREXAMPLE_NOT_REPRODUCED"
        ),
        "counterexample_reproduced": reproduced,
        "first_action": first,
        "second_action": second,
        "discovery_called_before_selection": bool(public["discovery_receipts"]),
        "visible_selected_cost": expensive["cost"],
        "complete_interface_cheaper_sufficient_cost": cheap["cost"],
        "violated_claim": (
            "LEAST_COST_EVIDENCE_SUPPORTED_SELECTION_ACROSS_COMPLETE_DECLARED_TARGET_SCOPE"
        ),
        "violated_frozen_contract": (
            "SELECT_LEAST_COST_ADMISSIBLE_ROUTE__DO_NOT_IGNORE_CHEAPER_SUFFICIENT_ROUTE"
        ),
        "invalidated_active_implication": (
            "COMPLETE_INTERFACE_INSTANCE_IMPLIES_DYNAMIC_V3_SELECTION_OBLIGATIONS_DISCHARGED"
        ),
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }

if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
