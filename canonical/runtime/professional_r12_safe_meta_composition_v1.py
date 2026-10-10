"""R12 safe certification disposition wrapper V1.

Wrap exact V9 without changing positive authority. Every invocation returns:
* SAFE_POSITIVE_VERIFIED only when V9 itself returned an authorized positive
  certificate with material totality and executable R12 semantic verification; or
* SAFE_NONPOSITIVE_FAIL_CLOSED with an explicit blocking diagnostic.

This proves a subordinate safety capability only. It does NOT close the stronger
universal R12 semantic-sufficiency property claim.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
from canonical.runtime import professional_quality_p1_router_v9 as v9

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SAFE_CERTIFICATION_DISPOSITION_V1"
SAFE_CLAIM_ID="4d94bc346ec20e2778c1fe8655274dd0e9ff4cd67e94681164f77be9fb4e1962"
STRONGER_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"

def _diagnostic(out:Mapping[str,Any])->dict[str,Any]:
    for source,value in (
        ("blocking_reason",out.get("blocking_reason")),
        ("reason",out.get("reason")),
        ("status",out.get("status")),
    ):
        if isinstance(value,str) and value.strip():
            return {"source":source,"value":value.strip()}
    for field in ("final_step_binding","step_binding_result","semantic_verification","subject_verification"):
        row=out.get(field)
        if isinstance(row,Mapping):
            for key in ("reason","status","blocking_reason"):
                value=row.get(key)
                if isinstance(value,str) and value.strip():
                    return {"source":field+"."+key,"value":value.strip()}
    return {"source":"normalized_nonpositive_default","value":"V9_NONPOSITIVE_WITHOUT_POSITIVE_AUTHORITY"}

def classify_v9_result(out:Any)->dict[str,Any]:
    if not isinstance(out,Mapping):
        return {
            "schema":SCHEMA,"status":"SAFE_NONPOSITIVE_FAIL_CLOSED",
            "safe_certification_disposition_complete":True,
            "safe_positive_verified":False,
            "positive_certification_authorized":False,
            "blocking_diagnostic":{"source":"result_shape","value":"V9_RESULT_NOT_MAPPING"},
            "safe_claim_id":SAFE_CLAIM_ID,
            "stronger_semantic_sufficiency_claim_id":STRONGER_CLAIM_ID,
            "stronger_semantic_sufficiency_claim_proved":False,
            "semantic_truth_authority":False,"quality_authority":False,
            "acceptance_authority":False,"promotion_authority":False,
            "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
        }
    positive=(
        out.get("final_step_outcome")=="POSITIVE_CERTIFICATE"
        and out.get("positive_certification_authorized") is True
        and out.get("material_totality_proved") is True
        and out.get("v9_executable_r12_totality_semantics_verified") is True
    )
    result=deepcopy(dict(out))
    result["schema"]=SCHEMA
    result["safe_claim_id"]=SAFE_CLAIM_ID
    result["stronger_semantic_sufficiency_claim_id"]=STRONGER_CLAIM_ID
    result["safe_certification_disposition_complete"]=True
    result["stronger_semantic_sufficiency_claim_proved"]=False
    result["semantic_truth_authority"]=False
    result["quality_authority"]=False
    result["acceptance_authority"]=False
    result["promotion_authority"]=False
    result["terminal_authority"]=False
    result["terminal_credit_delta"]=0
    result["incremental_spend_usd"]=0
    if positive:
        result["status"]="SAFE_POSITIVE_VERIFIED"
        result["safe_positive_verified"]=True
        result["blocking_diagnostic"]=None
        return result
    result["status"]="SAFE_NONPOSITIVE_FAIL_CLOSED"
    result["safe_positive_verified"]=False
    result["positive_certification_authorized"]=False
    result["blocking_diagnostic"]=_diagnostic(out)
    return result

def route(state:Mapping[str,Any]|None=None,*,repo_root=None)->dict[str,Any]:
    try:
        out=v9.route(state or {},repo_root=repo_root)
    except Exception as exc:
        out={"status":"FAIL_CLOSED","reason":"V9_EXCEPTION:"+type(exc).__name__,"positive_certification_authorized":False}
    return classify_v9_result(out)

def run(args:Mapping[str,Any]|None=None,root=None)->dict[str,Any]:
    return route(args or {},repo_root=root)
