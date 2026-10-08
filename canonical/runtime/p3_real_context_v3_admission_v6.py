"""P3 real-context admission v6.

Route order:
1. mechanically closed structural cell;
2. explicit-weight salience/order cell;
3. required-only support-V5 grounded realization cell;
4. fail-closed V2 semantic-certificate fallback.

No route mints source authorization, policy adequacy, DB admission, U-subtraction,
or terminal authority.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.p3_mechanically_closed_common_policy_cell_v1 import evaluate as evaluate_closed_cell
from canonical.runtime.p3_explicit_weighted_salience_cell_v1 import evaluate as evaluate_weighted_cell
from canonical.runtime.p3_required_claim_grounded_realization_cell_v3 import (
    evaluate as evaluate_required_realization,
    validate_v3_contract_surface,
)
from canonical.runtime.p3_real_context_v3_admission_v2 import evaluate as evaluate_v2

SCHEMA="PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V6"

def _fail(reason:str,**detail:Any)->dict[str,Any]:
    out={
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "v3_admission_authorized":False,"p3_contract_cell_authorized":False,
      "top_law_eligible":False,"source_authorization_verified":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
    }
    if detail:out["detail"]=detail
    return out

def _legacy_boundary_ok(r:Mapping[str,Any])->bool:
    return (
      r.get("pass") is True
      and r.get("v3_admission_authorized") is True
      and r.get("top_law_eligible") is True
      and r.get("policy_adequacy_authority") is False
      and r.get("db_admission_authority") is False
      and r.get("u_subtraction_authority") is False
      and r.get("terminal_authority") is False
      and r.get("terminal_credit_delta")==0
    )

def _required_boundary_ok(r:Mapping[str,Any])->bool:
    return (
      r.get("pass") is True
      and r.get("p3_contract_cell_authorized") is True
      and r.get("source_authorization_verified") is False
      and r.get("policy_adequacy_authority") is False
      and r.get("db_admission_authority") is False
      and r.get("u_subtraction_authority") is False
      and r.get("terminal_authority") is False
      and r.get("terminal_credit_delta")==0
    )

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):return _fail("PAYLOAD_MAPPING_REQUIRED")
    if set(payload)-{"context_id","v3_input","objective_weights","semantic_certificates"}:
        return _fail("UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS")
    context_id=payload.get("context_id")
    if not isinstance(context_id,str) or not context_id.strip():return _fail("CONTEXT_ID_REQUIRED")
    v3_input=payload.get("v3_input")
    if not isinstance(v3_input,Mapping):return _fail("V3_INPUT_REQUIRED")
    contract_failure=validate_v3_contract_surface(v3_input)
    if contract_failure is not None:return _fail(contract_failure)

    # Explicit objective weights are binding on selection AND output order.
    # Never take an unweighted shortcut while a weighted contract is present.
    weighted=None
    if "objective_weights" in payload:
        weights=payload["objective_weights"]
        if not isinstance(weights,Mapping):
            return _fail("OBJECTIVE_WEIGHTS_INVALID")
        weighted=evaluate_weighted_cell({"v3_input":v3_input,"objective_weights":weights})
        if weighted.get("pass") is not True:
            return _fail(
                "OBJECTIVE_WEIGHTS_UNSATISFIED",
                weighted_reason=weighted.get("reason") or weighted.get("status"),
            )
        if not _legacy_boundary_ok(weighted):
            return _fail("WEIGHTED_CELL_AUTHORITY_BOUNDARY_INVALID")
        return {
          "schema":SCHEMA,"pass":True,
          "status":"PASS__P3_REAL_CONTEXT_EXPLICIT_WEIGHT_FAST_PATH",
          "route":"EXPLICIT_WEIGHTED_SALIENCE_CELL_V1","context_id":context_id,
          "selected_claim_ids":list(weighted.get("selected_claim_ids") or []),
          "claim_order":list(weighted.get("claim_order") or []),
          "objective_value":weighted.get("objective_value"),
          "v3_admission_authorized":True,"p3_contract_cell_authorized":True,"top_law_eligible":True,
          "source_authorization_verified":False,"policy_adequacy_authority":False,
          "db_admission_authority":False,"u_subtraction_authority":False,
          "terminal_authority":False,"terminal_credit_delta":0,"route_receipt":weighted,
        }

    closed=evaluate_closed_cell({"v3_input":v3_input})
    if closed.get("pass") is True:
        if not _legacy_boundary_ok(closed):return _fail("CLOSED_CELL_AUTHORITY_BOUNDARY_INVALID")
        return {
          "schema":SCHEMA,"pass":True,
          "status":"PASS__P3_REAL_CONTEXT_STRUCTURAL_COMMON_POLICY_FAST_PATH",
          "route":"MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1","context_id":context_id,
          "v3_admission_authorized":True,"p3_contract_cell_authorized":True,"top_law_eligible":True,
          "source_authorization_verified":False,"policy_adequacy_authority":False,
          "db_admission_authority":False,"u_subtraction_authority":False,
          "terminal_authority":False,"terminal_credit_delta":0,"route_receipt":closed,
        }

    required=evaluate_required_realization({"v3_input":v3_input})
    if required.get("pass") is True:
        if not _required_boundary_ok(required):return _fail("REQUIRED_REALIZATION_AUTHORITY_BOUNDARY_INVALID")
        return {
          "schema":SCHEMA,"pass":True,
          "status":"PASS__P3_REAL_CONTEXT_REQUIRED_SUPPORT_V5_REALIZATION_FAST_PATH",
          "route":"REQUIRED_SUPPORT_V5_REALIZATION_CELL_V3","context_id":context_id,
          "rendered_text":required.get("rendered_text"),
          "render_trace":list(required.get("render_trace") or []),
          "support_receipts":list(required.get("support_receipts") or []),
          "v3_admission_authorized":False,
          "p3_contract_cell_authorized":True,
          "top_law_eligible":False,
          "source_authorization_verified":False,"policy_adequacy_authority":False,
          "db_admission_authority":False,"u_subtraction_authority":False,
          "terminal_authority":False,"terminal_credit_delta":0,
          "route_receipt":required,
          "boundary":"POSITIVE_REQUIRED_ONLY_P3_CONTRACT_CELL__NOT_SYNTHESIS_V3_TOP_LAW_PROMOTION",
        }

    fallback=evaluate_v2(payload)
    out=dict(fallback)
    out["schema"]=SCHEMA
    out["route"]="V2_SEMANTIC_FALLBACK"
    out["closed_fast_path_pass"]=False
    out["closed_fast_path_reason"]=closed.get("reason") or closed.get("status")
    out["weighted_fast_path_pass"]=False
    out["weighted_fast_path_reason"]=(weighted.get("reason") or weighted.get("status")) if weighted is not None else "OBJECTIVE_WEIGHTS_NOT_SUPPLIED"
    out["required_realization_fast_path_pass"]=False
    out["required_realization_fast_path_reason"]=required.get("reason") or required.get("status")
    out["p3_contract_cell_authorized"]=False
    out["source_authorization_verified"]=False
    out["terminal_authority"]=False
    out["terminal_credit_delta"]=0
    return out

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
