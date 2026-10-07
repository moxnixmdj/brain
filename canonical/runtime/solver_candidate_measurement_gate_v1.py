from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SOLVER_CANDIDATE_MEASUREMENT_GATE_V1"

# These verifier classes evaluate abstract values supplied by the proposal itself.
# They are valid relation/interpreter primitives, but they do not independently
# establish that those values were measured from an external artifact or world state.
UNBOUND_CANDIDATE_VALUE_VERIFIERS = {
    "TYPED_ACCEPTANCE_PROGRAM_V1",
    "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1",
}


def audit_problem(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "PROBLEM_NOT_OBJECT",
            "terminal_authority": False,
        }

    capabilities = problem.get("capabilities")
    if (
        not isinstance(capabilities, Sequence)
        or isinstance(capabilities, (str, bytes))
        or not capabilities
    ):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "CAPABILITIES_REQUIRED",
            "terminal_authority": False,
        }

    blocked = []
    observed = []
    for index, cap in enumerate(capabilities):
        if not isinstance(cap, Mapping):
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "CAPABILITY_NOT_OBJECT",
                "index": index,
                "terminal_authority": False,
            }
        cid = cap.get("id")
        action = cap.get("action")
        if not isinstance(cid, str) or not cid or not isinstance(action, Mapping):
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "CAPABILITY_ID_OR_ACTION_INVALID",
                "index": index,
                "terminal_authority": False,
            }
        verifier_id = str(action.get("verifier_id") or "")
        observed.append({"capability_id": cid, "verifier_id": verifier_id})
        if verifier_id in UNBOUND_CANDIDATE_VALUE_VERIFIERS:
            blocked.append({
                "capability_id": cid,
                "verifier_id": verifier_id,
                "reason": "PROPOSAL_SUPPLIED_VALUES_NOT_INDEPENDENTLY_MEASURED",
            })

    if blocked:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__UNBOUND_CANDIDATE_MEASUREMENT",
            "reason": "ONE_OR_MORE_VERIFIERS_CAN_ONLY_EVALUATE_PROPOSAL_SUPPLIED_ABSTRACT_VALUES",
            "blocked": blocked,
            "observed": observed,
            "repair_boundary": (
                "USE_THESE_VERIFIERS_AS_NONAUTHORITATIVE_RELATION_CHECKERS_ONLY_UNTIL_"
                "EVERY_CANDIDATE_FIELD_IS_PRODUCED_BY_A_BRAIN_OWNED_CONTENT_ADDRESSED_"
                "MEASUREMENT_ADAPTER_BOUND_TO_THE_ACTUAL_ARTIFACT_OR_WORLD_STATE"
            ),
            "terminal_authority": False,
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__NO_UNBOUND_CANDIDATE_VALUE_VERIFIER",
        "blocked": [],
        "observed": observed,
        "terminal_authority": False,
    }
