"""UVCK V2 shadow integration over the existing R2 fixed-point controller.

This seam does not change R2 routing, pass/fail, authority, or execution.
It runs the current R2 fixed-point controller unchanged, then compiles the
result into a V2 assurance status beside it.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime import assurance_closure_compiler_v1 as assurance
from canonical.runtime import general_adequate_decision_fixed_point_v2 as r2

SCHEMA = "PROJECT_BRAIN_R2_UVCK_V2_SHADOW_INTEGRATION_V1"


def run(request: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    r2_result = r2.run(request, **kwargs)
    assurance_result = assurance.evaluate_controller_result(r2_result)
    return {
        "schema": SCHEMA,
        "status": "PASS__SHADOW_INTEGRATION_EXECUTED",
        "pass": True,
        "r2_result": deepcopy(r2_result),
        "assurance_result": deepcopy(assurance_result),
        "r2_pass_unchanged": r2_result.get("pass") is True,
        "r2_status_unchanged": r2_result.get("status"),
        "assurance_is_shadow_only": True,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
