"""Guarded typed-acceptance specialist policy.

The historical independent_acceptance_model is intentionally permissive about
unknown transform kinds because it is a generic lower-level gate. This wrapper
internalizes the supported-transform structural precondition for the registered
CursorBench coding specialist and rechecks it at invocation time.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import (
    verify as verify_supported_transform_atom,
)
from canonical.runtime.independent_acceptance_model import assess as assess_base

SCHEMA = "PROJECT_BRAIN_GUARDED_TYPED_ACCEPTANCE_POLICY_V1"


def assess(model: Mapping[str, Any]) -> dict[str, Any]:
    structural = verify_supported_transform_atom(model)
    if structural.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__STRUCTURAL_POLICY_PRECONDITION_UNPROVED",
            "structural_precondition": structural,
            "base_policy_executed": False,
            "terminal_submission_authorized_by_this_gate": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    base = assess_base(dict(model))
    return {
        "schema": SCHEMA,
        "pass": base.get("pass") is True,
        "status": (
            "PASS__STRUCTURAL_PRECONDITION_AND_INDEPENDENT_ACCEPTANCE_GATE"
            if base.get("pass") is True
            else "FAIL_CLOSED__INDEPENDENT_ACCEPTANCE_GATE"
        ),
        "structural_precondition": structural,
        "base_policy_executed": True,
        "base_result": base,
        "terminal_submission_authorized_by_this_gate": (
            base.get("terminal_submission_authorized_by_this_gate") is True
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
