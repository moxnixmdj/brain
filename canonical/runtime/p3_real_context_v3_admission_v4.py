"""P3 real-context admission v4.

Route order:
1. mechanically closed structural cell;
2. explicit-weight salience/order cell when objective_weights are supplied;
3. fail-closed V2 semantic fallback.

The wrapper never upgrades source authority, policy adequacy, DB admission,
U-subtraction, or terminality.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.p3_mechanically_closed_common_policy_cell_v1 import (
    evaluate as evaluate_closed_cell,
)
from canonical.runtime.p3_explicit_weighted_salience_cell_v1 import (
    evaluate as evaluate_weighted_cell,
)
from canonical.runtime.p3_real_context_v3_admission_v2 import evaluate as evaluate_v2

SCHEMA="PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V4"

def _fail(reason:str,**detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "v3_admission_authorized":False,"top_law_eligible":False,
        "source_authorization_verified":False,"policy_adequacy_authority":False,
        "db_admission_authority":False,"u_subtraction_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out

def _boundary_ok(receipt:Mapping[str,Any])->bool:
    return (
        receipt.get("pass") is True
        and receipt.get("v3_admission_authorized") is True
        and receipt.get("top_law_eligible") is True
        and receipt.get("policy_adequacy_authority") is False
        and receipt.get("db_admission_authority") is False
        and receipt.get("u_subtraction_authority") is False
        and receipt.get("terminal_authority") is False
        and receipt.get("terminal_credit_delta")==0
    )

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    context_id=payload.get("context_id")
    if not isinstance(context_id,str) or not context_id.strip():
        return _fail("CONTEXT_ID_REQUIRED")
    v3_input=payload.get("v3_input")
    if not isinstance(v3_input,Mapping):
        return _fail("V3_INPUT_REQUIRED")

    closed=evaluate_closed_cell({"v3_input":v3_input})
    if closed.get("pass") is True:
        if not _boundary_ok(closed):
            return _fail("CLOSED_CELL_AUTHORITY_BOUNDARY_INVALID")
        return {
            "schema":SCHEMA,"pass":True,
            "status":"PASS__P3_REAL_CONTEXT_STRUCTURAL_COMMON_POLICY_FAST_PATH",
            "route":"MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1",
            "context_id":context_id,
            "v3_admission_authorized":True,"top_law_eligible":True,
            "source_authorization_verified":False,"policy_adequacy_authority":False,
            "db_admission_authority":False,"u_subtraction_authority":False,
            "terminal_authority":False,"terminal_credit_delta":0,
            "route_receipt":closed,
        }

    weights=payload.get("objective_weights")
    weighted=None
    if isinstance(weights,Mapping):
        weighted=evaluate_weighted_cell({"v3_input":v3_input,"objective_weights":weights})
        if weighted.get("pass") is True:
            if not _boundary_ok(weighted):
                return _fail("WEIGHTED_CELL_AUTHORITY_BOUNDARY_INVALID")
            return {
                "schema":SCHEMA,"pass":True,
                "status":"PASS__P3_REAL_CONTEXT_EXPLICIT_WEIGHT_FAST_PATH",
                "route":"EXPLICIT_WEIGHTED_SALIENCE_CELL_V1",
                "context_id":context_id,
                "selected_claim_ids":list(weighted.get("selected_claim_ids") or []),
                "claim_order":list(weighted.get("claim_order") or []),
                "objective_value":weighted.get("objective_value"),
                "v3_admission_authorized":True,"top_law_eligible":True,
                "source_authorization_verified":False,"policy_adequacy_authority":False,
                "db_admission_authority":False,"u_subtraction_authority":False,
                "terminal_authority":False,"terminal_credit_delta":0,
                "route_receipt":weighted,
            }

    fallback=evaluate_v2(payload)
    out=dict(fallback)
    out["schema"]=SCHEMA
    out["route"]="V2_SEMANTIC_FALLBACK"
    out["closed_fast_path_pass"]=False
    out["closed_fast_path_reason"]=closed.get("reason") or closed.get("status")
    if weighted is not None:
        out["weighted_fast_path_pass"]=False
        out["weighted_fast_path_reason"]=weighted.get("reason") or weighted.get("status")
    else:
        out["weighted_fast_path_pass"]=False
        out["weighted_fast_path_reason"]="OBJECTIVE_WEIGHTS_NOT_SUPPLIED"
    out["source_authorization_verified"]=False
    out["terminal_authority"]=False
    out["terminal_credit_delta"]=0
    return out

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
