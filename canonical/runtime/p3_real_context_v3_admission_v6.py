"""P3 real-context admission v6.

Preserves every V5 positive route unchanged. If V5 fails closed, retries the
required-only grounded-realization cell using the verified support V5 portfolio,
which adds exact set-membership/categorical relations. No authority escalation.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.p3_real_context_v3_admission_v5 import evaluate as evaluate_v5
from canonical.runtime.p3_required_claim_grounded_realization_cell_v3 import evaluate as evaluate_required_v3
from canonical.runtime.p3_declared_contract_surface_guard_v1 import validate_outer

SCHEMA="PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V6"

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    contract_failure=validate_outer(payload)
    if contract_failure is not None:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":contract_failure,
                "p3_contract_cell_authorized":False,"source_authorization_verified":False,
                "policy_adequacy_authority":False,"db_admission_authority":False,
                "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
    prior=evaluate_v5(payload)
    if prior.get("pass") is True:
        out=dict(prior);out["schema"]=SCHEMA;out["v5_preserved_positive_route"]=True
        return out
    # A supplied objective must never fall through to an unweighted route.
    if "objective_weights" in payload:
        out=dict(prior);out["schema"]=SCHEMA
        out["v5_preserved_positive_route"]=False
        return out
    v3_input=payload.get("v3_input")
    if isinstance(v3_input,Mapping):
        new=evaluate_required_v3({"v3_input":v3_input})
        if new.get("pass") is True:
            if (
                new.get("p3_contract_cell_authorized") is not True
                or new.get("source_authorization_verified") is not False
                or new.get("policy_adequacy_authority") is not False
                or new.get("db_admission_authority") is not False
                or new.get("u_subtraction_authority") is not False
                or new.get("terminal_authority") is not False
                or new.get("terminal_credit_delta") != 0
            ):
                return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED",
                        "reason":"REQUIRED_V3_AUTHORITY_BOUNDARY_INVALID",
                        "p3_contract_cell_authorized":False,"source_authorization_verified":False,
                        "policy_adequacy_authority":False,"db_admission_authority":False,
                        "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
            return {
              "schema":SCHEMA,"pass":True,
              "status":"PASS__P3_REAL_CONTEXT_REQUIRED_SUPPORT_V5_REALIZATION_FAST_PATH",
              "route":"REQUIRED_SUPPORT_V5_REALIZATION_CELL_V3",
              "context_id":payload.get("context_id"),
              "rendered_text":new.get("rendered_text"),
              "render_trace":list(new.get("render_trace") or []),
              "support_receipts":list(new.get("support_receipts") or []),
              "v3_admission_authorized":False,"p3_contract_cell_authorized":True,
              "top_law_eligible":False,"source_authorization_verified":False,
              "policy_adequacy_authority":False,"db_admission_authority":False,
              "u_subtraction_authority":False,"terminal_authority":False,
              "terminal_credit_delta":0,"route_receipt":new,
              "v5_preserved_positive_route":False,
            }
    out=dict(prior);out["schema"]=SCHEMA
    out["v5_preserved_positive_route"]=False
    out["required_v5_realization_fast_path_pass"]=False
    return out

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
