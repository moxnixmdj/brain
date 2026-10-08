"""P3 real-context admission v3: verified mechanically-closed fast path + V2 fallback.

This adapter reuses the independently exercised mechanically closed P3 common-policy
cell before attempting the V2 semantic-certificate route. It creates no new semantic
oracle. A context is positively admitted only when the closed-cell verifier itself
passes; otherwise control falls back to V2, which remains fail-closed on unverified
semantic-completeness certificates.

No source authorization, policy adequacy, DB admission, U-subtraction, or terminal
authority is minted here.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.p3_mechanically_closed_common_policy_cell_v1 import (
    evaluate as evaluate_closed_cell,
)
from canonical.runtime.p3_real_context_v3_admission_v2 import evaluate as evaluate_v2

SCHEMA = "PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V3"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "v3_admission_authorized": False,
        "top_law_eligible": False,
        "source_authorization_verified": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    context_id = payload.get("context_id")
    if not isinstance(context_id, str) or not context_id.strip():
        return _fail("CONTEXT_ID_REQUIRED")
    v3_input = payload.get("v3_input")
    if not isinstance(v3_input, Mapping):
        return _fail("V3_INPUT_REQUIRED")

    closed = evaluate_closed_cell({"v3_input": v3_input})
    if closed.get("pass") is True:
        if (
            closed.get("mechanically_closed_cell") is not True
            or closed.get("v3_admission_authorized") is not True
            or closed.get("top_law_eligible") is not True
            or closed.get("terminal_authority") is not False
            or closed.get("terminal_credit_delta") != 0
        ):
            return _fail("CLOSED_CELL_RECEIPT_AUTHORITY_BOUNDARY_INVALID")
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__P3_REAL_CONTEXT_MECHANICALLY_CLOSED_COMMON_POLICY_FAST_PATH",
            "route": "MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1",
            "context_id": context_id,
            "semantic_certificates_required": False,
            "semantic_predicates_eliminated_by_structure": dict(
                closed.get("semantic_predicates_eliminated_by_structure") or {}
            ),
            "v3_runtime_pass": True,
            "v3_admission_authorized": True,
            "top_law_eligible": True,
            "source_authorization_verified": False,
            "policy_adequacy_authority": False,
            "db_admission_authority": False,
            "u_subtraction_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "closed_cell_receipt": closed,
            "boundary": (
                "NARROW_VERIFIED_FORMAL_COMMON_POLICY_CELL_ONLY__"
                "NO_GENERAL_CONTEXT_SEMANTIC_COMPLETENESS__"
                "NO_SOURCE_AUTHORITY_DB_U_OR_TERMINAL_CREDIT"
            ),
        }

    fallback = evaluate_v2(payload)
    out = dict(fallback)
    out["schema"] = SCHEMA
    out["route"] = "V2_SEMANTIC_FALLBACK"
    out["mechanically_closed_fast_path_pass"] = False
    out["mechanically_closed_fast_path_reason"] = closed.get("reason") or closed.get("status")
    out["source_authorization_verified"] = False
    out["terminal_authority"] = False
    out["terminal_credit_delta"] = 0
    return out


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {})
