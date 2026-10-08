"""Selected support truth certificate v9.

V9 preserves V8 whenever V8 resolves. Only when V8 is UNKNOWN does V9 attempt
bounded transitive source-declared equivalence over each evidence unit.

All evidence units must be resolved by the V2 equivalence checker for this fallback
to decide the support predicate. Any unresolved unit preserves UNKNOWN.
"""
from __future__ import annotations

import hashlib, json
from typing import Any, Mapping

from canonical.runtime.selected_support_truth_certificate_v8 import evaluate as evaluate_v8
from canonical.runtime.bounded_source_declared_equivalence_support_v2 import classify_support as classify_equiv_v2

SCHEMA="PROJECT_BRAIN_SELECTED_SUPPORT_TRUTH_CERTIFICATE_V9"
TRUE_POLICY="ASSERT_REQUIRED_CLAIM_AS_SUPPORTED_WITH_PROVENANCE"
FALSE_POLICY="DO_NOT_ASSERT_REQUIRED_CLAIM_AS_SUPPORTED__PRESERVE_UNCERTAINTY_OR_SEEK_EVIDENCE"

def _digest(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def evaluate(payload:Mapping[str,Any],*,allow_test_fixtures:bool=False)->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"PAYLOAD_MAPPING_REQUIRED",
                "predicate_truth":"UNKNOWN","terminal_authority":False,"terminal_credit_delta":0}
    base=evaluate_v8(payload,allow_test_fixtures=allow_test_fixtures)
    if base.get("pass") is True:
        out=dict(base);out["schema"]=SCHEMA;out["support_route_v9"]="V8_BASE";return out

    claim=payload.get("claim");evidence=payload.get("evidence")
    if not isinstance(claim,Mapping) or not isinstance(evidence,list):
        out=dict(base);out["schema"]=SCHEMA;out["support_route_v9"]="V8_FAIL_CLOSED";return out
    text=claim.get("text");cid=claim.get("claim_id")
    if not isinstance(text,str) or not text.strip():
        out=dict(base);out["schema"]=SCHEMA;out["support_route_v9"]="V8_FAIL_CLOSED";return out

    supports=[];conflicts=[];audit=[]
    for row in evidence:
        if not isinstance(row,Mapping):
            out=dict(base);out["schema"]=SCHEMA;out["support_route_v9"]="V8_FAIL_CLOSED";return out
        eid=row.get("evidence_id");et=row.get("text")
        if not isinstance(eid,str) or not isinstance(et,str):
            out=dict(base);out["schema"]=SCHEMA;out["support_route_v9"]="V8_FAIL_CLOSED";return out
        rel=classify_equiv_v2(text,et,evidence_id=eid)
        if rel.get("status")!="RESOLVED":
            out=dict(base)
            out["schema"]=SCHEMA
            out["support_route_v9"]="UNKNOWN_AFTER_V8_AND_TRANSITIVE_EQUIVALENCE"
            out["transitive_equivalence_unresolved"]={"evidence_id":eid,"result":rel}
            out["predicate_truth"]="UNKNOWN"
            out["truthful_precommitment_observation"]=False
            out["selected_policy_id"]=None
            return out
        relation=rel.get("relation")
        audit.append({"evidence_id":eid,"relation":relation,
                      "grammar":"SOURCE_DECLARED_EQUIVALENCE_V2_TRANSITIVE",
                      "proof":rel.get("proof")})
        if relation=="SUPPORTS":supports.append(eid)
        elif relation=="CONFLICTS":conflicts.append(eid)

    holds=bool(supports) and not conflicts
    truth="TRUE" if holds else "FALSE"
    binding=[{
        "evidence_id":r.get("evidence_id"),
        "text_sha256":hashlib.sha256(str(r.get("text") or "").encode()).hexdigest(),
        "verified":r.get("verified") is True,
        "provenance":r.get("provenance"),
    } for r in evidence]
    return {
        "schema":SCHEMA,"pass":True,
        "status":"PASS__SELECTED_SUPPORT_PREDICATE_V9_TRANSITIVE_EQUIVALENCE_PROVED_"+truth,
        "predicate_id":"support-portfolio-v9-transitive-equivalence-sha256:"+_digest({"claim":text,"evidence":binding}),
        "requested_predicate_id":payload.get("predicate_id"),"requested_predicate_id_authority":False,
        "claim_id":cid,"claim_text_sha256":hashlib.sha256(text.encode()).hexdigest(),
        "evidence_set_sha256":_digest(binding),
        "predicate_truth":truth,"truthful_precommitment_observation":True,
        "selected_policy_id":TRUE_POLICY if holds else FALSE_POLICY,
        "support_evidence_ids":sorted(supports),"conflict_evidence_ids":sorted(conflicts),
        "relation_audit":audit,"semantic_proof_audit":[],
        "support_route_v9":"SOURCE_DECLARED_EQUIVALENCE_V2_TRANSITIVE",
        "source_authorization_verified":False,"policy_adequacy_authority":False,
        "db_admission_authority":False,"u_subtraction_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,
        "boundary":"V8_PLUS_EXACT_ATOMIC_SOURCE_DECLARED_EQUIVALENCE_TRANSITIVE_CLOSURE_ONLY",
    }

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
