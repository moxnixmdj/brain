"""Fail-closed normalizer for the one shared P1 failure-semantics reality batch.

This module deliberately does not infer DIRECT_CONTRACT versus DERIVED_UPSTREAM.
That distinction must be bound by the source instrumentation before the case is
visible to the V7 candidate. Missing or malformed semantics fail closed.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_P1_SHARED_FAILURE_SEMANTICS_NORMALIZER_V1"
BEHAVIOR_ID = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
SURFACES = {
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}
SEMANTICS = {"DIRECT_CONTRACT", "DERIVED_UPSTREAM"}


def normalize_case(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {"status": "FAIL_CLOSED", "reason": "RAW_CASE_NOT_MAPPING"}

    surface_id = raw.get("surface_id")
    case_id = raw.get("case_id")
    source_receipt = raw.get("source_observation_receipt")
    trajectory = raw.get("trajectory")
    terminal_failed_resources = raw.get("terminal_failed_resources")

    if surface_id not in SURFACES:
        return {"status": "FAIL_CLOSED", "reason": "SURFACE_NOT_FROZEN"}
    if not isinstance(case_id, str) or not case_id:
        return {"status": "FAIL_CLOSED", "reason": "CASE_ID_INVALID"}
    if not isinstance(source_receipt, str) or not source_receipt:
        return {"status": "FAIL_CLOSED", "reason": "SOURCE_RECEIPT_MISSING"}
    if not isinstance(trajectory, list) or not trajectory:
        return {"status": "FAIL_CLOSED", "reason": "TRAJECTORY_INVALID"}
    if not isinstance(terminal_failed_resources, list) or not terminal_failed_resources:
        return {"status": "FAIL_CLOSED", "reason": "TERMINAL_FAILED_RESOURCES_INVALID"}

    out_rows = []
    saw_direct = False
    saw_derived = False

    for idx, row in enumerate(trajectory):
        if not isinstance(row, Mapping):
            return {"status": "FAIL_CLOSED", "reason": f"ROW_NOT_MAPPING:{idx}"}
        copied = copy.deepcopy(dict(row))
        checks = copied.get("checks")
        if not isinstance(checks, list):
            return {"status": "FAIL_CLOSED", "reason": f"CHECKS_INVALID:{idx}"}

        for j, check in enumerate(checks):
            if not isinstance(check, Mapping):
                return {"status": "FAIL_CLOSED", "reason": f"CHECK_NOT_MAPPING:{idx}:{j}"}
            if check.get("pass") is not False:
                continue
            semantics = check.get("failure_semantics")
            if semantics not in SEMANTICS:
                return {"status": "FAIL_CLOSED", "reason": f"FAILURE_SEMANTICS_UNBOUND:{idx}:{j}"}
            evidence = check.get("evidence")
            if (
                not isinstance(evidence, list)
                or not evidence
                or any(not isinstance(x, str) or not x for x in evidence)
            ):
                return {"status": "FAIL_CLOSED", "reason": f"FAILED_CHECK_RECEIPTS_EMPTY:{idx}:{j}"}
            if semantics == "DIRECT_CONTRACT":
                saw_direct = True
            else:
                saw_derived = True

        out_rows.append(copied)

    if not saw_direct:
        return {"status": "FAIL_CLOSED", "reason": "DIRECT_CONTRACT_NOT_PRESENT"}
    if not saw_derived:
        return {"status": "FAIL_CLOSED", "reason": "DERIVED_UPSTREAM_NOT_PRESENT"}

    return {
        "status": "PASS",
        "schema": SCHEMA,
        "behavior_id": BEHAVIOR_ID,
        "surface_id": surface_id,
        "case_id": case_id,
        "source_observation_receipt": source_receipt,
        "task": {
            "trajectory": out_rows,
            "terminal_failed_resources": copy.deepcopy(terminal_failed_resources),
            "goal": "LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITH_MACHINE_VERIFIED_TERMINAL_RESCUE",
        },
        "normalization_rule": "PASS_THROUGH_EXPLICIT_SOURCE_BOUND_FAILURE_SEMANTICS_ONLY__NO_DEFAULT_NO_INFERENCE",
    }
