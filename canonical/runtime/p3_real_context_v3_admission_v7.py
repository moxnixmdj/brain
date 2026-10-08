"""P3 real-context admission v7.

Preserves every V6 positive route unchanged. If V6 fails closed, retries the
required-only grounded-realization cell using support V6, which adds bounded
predicate-argument active/passive equivalence/conflict. No authority escalation.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.p3_real_context_v3_admission_v6 import evaluate as evaluate_v6
from canonical.runtime.p3_required_claim_grounded_realization_cell_v4 import evaluate as evaluate_required_v4

SCHEMA="PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V7"

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"PAYLOAD_MAPPING_REQUIRED",
                "p3_contract_cell_authorized":False,"source_authorization_verified":False,
                "policy_adequacy_authority":False,"db_admission_authority":False,
                "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
    prior=evaluate_v6(payload)
    if prior.get("pass") is True:
        out=dict(prior);out["schema"]=SCHEMA;out["v6_preserved_positive_route"]=True
        return out
    v3_input=payload.get("v3_input")
    if isinstance(v3_input,Mapping):
        new=evaluate_required_v4({"v3_input":v3_input})
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
                        "reason":"REQUIRED_V4_AUTHORITY_BOUNDARY_INVALID",
                        "p3_contract_cell_authorized":False,"source_authorization_verified":False,
                        "policy_adequacy_authority":False,"db_admission_authority":False,
                        "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
            return {
              "schema":SCHEMA,"pass":True,
              "status":"PASS__P3_REAL_CONTEXT_REQUIRED_SUPPORT_V6_REALIZATION_FAST_PATH",
              "route":"REQUIRED_SUPPORT_V6_REALIZATION_CELL_V4",
              "context_id":payload.get("context_id"),
              "rendered_text":new.get("rendered_text"),
              "render_trace":list(new.get("render_trace") or []),
              "support_receipts":list(new.get("support_receipts") or []),
              "v3_admission_authorized":False,"p3_contract_cell_authorized":True,
              "top_law_eligible":False,"source_authorization_verified":False,
              "policy_adequacy_authority":False,"db_admission_authority":False,
              "u_subtraction_authority":False,"terminal_authority":False,
              "terminal_credit_delta":0,"route_receipt":new,
              "v6_preserved_positive_route":False,
            }
    out=dict(prior);out["schema"]=SCHEMA
    out["v6_preserved_positive_route"]=False
    out["required_v6_realization_fast_path_pass"]=False
    return out

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
