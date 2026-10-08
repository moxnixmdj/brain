"""Root-bound wrapper for P3 robust CEGAR selected semantic truth.

This wrapper adds one authority fact only: the policy and fact bytes used by the
selected truth checker are losslessly derived from exact upstream root-task bytes.
It preserves the unavoidable root-of-trust boundary and grants no global U credit.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.p3_selected_truth_root_contract_v1 import compile_root_task
from canonical.runtime.p3_cegar_selected_truth_bridge_v1 import evaluate as evaluate_bridge

SCHEMA = "PROJECT_BRAIN_P3_ROOT_BOUND_CEGAR_SELECTED_TRUTH_V1"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "root_task_source_binding_verified": False,
        "source_authorization_verified_relative_to_root_task": False,
        "root_task_authority_self_proved": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != {"root_task", "cegar_problem"}:
        return _fail("PAYLOAD_FIELDS_INVALID")
    root = compile_root_task(payload.get("root_task"))
    if root.get("pass") is not True:
        return _fail("ROOT_TASK_BINDING_FAILED", root_binding=root)

    out = evaluate_bridge({
        "cegar_problem": payload.get("cegar_problem"),
        "truth_input": root["truth_input"],
    })
    if out.get("pass") is not True:
        return _fail("CEGAR_TRUTH_BRIDGE_FAILED", root_binding=root, bridge=out)

    result = dict(out)
    result.update({
        "schema": SCHEMA,
        "status": (
            "PASS__ROOT_BOUND_SELECTED_TRUTH__COMMON_POLICY_RECOMPILED"
            if out.get("truthful_selected_discriminator_bound") is True
            else "PASS__ROOT_BOUND_COMMON_POLICY__NO_TRUTH_REQUIRED"
        ),
        "root_task_sha256": root["root_task_sha256"],
        "root_binding_receipt_sha256": root["root_binding_receipt_sha256"],
        "root_task_source_binding_verified": True,
        "source_authorization_verified_relative_to_root_task": True,
        "root_task_authority_self_proved": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "root_authority_boundary": root["boundary"],
    })
    return result
