"""Selected support truth certificate v8.

V8 preserves V7 exactly when V7 resolves the full evidence set. When V7 returns
UNKNOWN and the selected claim is an exact controlled set-membership claim, V8
may invoke a finite multi-evidence set-inclusion closure.

The closure accepts only explicit membership, complete finite-set enumeration,
and explicit subset edges. It cannot override a resolved V7 result and it
returns UNKNOWN if any evidence row falls outside its controlled graph grammar.
"""
from __future__ import annotations

import hashlib, json
from typing import Any, Mapping

from canonical.runtime.selected_support_truth_certificate_v7 import evaluate as evaluate_v7
from canonical.runtime.bounded_set_inclusion_membership_closure_v1 import evaluate as evaluate_membership_closure

SCHEMA="PROJECT_BRAIN_SELECTED_SUPPORT_TRUTH_CERTIFICATE_V8"
TRUE_POLICY="ASSERT_REQUIRED_CLAIM_AS_SUPPORTED_WITH_PROVENANCE"
FALSE_POLICY="DO_NOT_ASSERT_REQUIRED_CLAIM_AS_SUPPORTED__PRESERVE_UNCERTAINTY_OR_SEEK_EVIDENCE"

def _digest(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def evaluate(payload:Mapping[str,Any],*,allow_test_fixtures:bool=False)->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"PAYLOAD_MAPPING_REQUIRED",
                "predicate_truth":"UNKNOWN","terminal_authority":False,"terminal_credit_delta":0}

    base=evaluate_v7(payload,allow_test_fixtures=allow_test_fixtures)
    if base.get("pass") is True:
        out=dict(base)
        out["schema"]=SCHEMA
        out["support_route"]="V7_SINGLE_EVIDENCE_PORTFOLIO"
        return out

    claim=payload.get("claim")
    evidence=payload.get("evidence")
    if not isinstance(claim,Mapping) or not isinstance(evidence,list):
        out=dict(base);out["schema"]=SCHEMA;out["support_route"]="V7_FAIL_CLOSED"
        return out

    cid=claim.get("claim_id")
    text=claim.get("text")
    if not isinstance(text,str) or not text.strip():
        out=dict(base);out["schema"]=SCHEMA;out["support_route"]="V7_FAIL_CLOSED"
        return out

    closure_rows=[]
    for row in evidence:
        if not isinstance(row,Mapping):
            out=dict(base);out["schema"]=SCHEMA;out["support_route"]="V7_FAIL_CLOSED"
            return out
        closure_rows.append({"evidence_id":row.get("evidence_id"),"text":row.get("text")})

    closure=evaluate_membership_closure({"claim_text":text,"evidence":closure_rows})
    if closure.get("pass") is not True:
        out=dict(base)
        out["schema"]=SCHEMA
        out["support_route"]="UNKNOWN_AFTER_V7_AND_SET_CLOSURE"
        out["set_membership_closure"]=closure
        out["predicate_truth"]="UNKNOWN"
        out["truthful_precommitment_observation"]=False
        out["selected_policy_id"]=None
        out["terminal_authority"]=False
        out["terminal_credit_delta"]=0
        return out

    truth=closure.get("predicate_truth")
    if truth not in {"TRUE","FALSE"}:
        out=dict(base)
        out["schema"]=SCHEMA
        out["support_route"]="UNKNOWN_AFTER_V7_AND_SET_CLOSURE"
        out["set_membership_closure"]=closure
        out["predicate_truth"]="UNKNOWN"
        out["truthful_precommitment_observation"]=False
        out["selected_policy_id"]=None
        return out

    binding=[
        {
            "evidence_id":row.get("evidence_id"),
            "text_sha256":hashlib.sha256(str(row.get("text") or "").encode()).hexdigest(),
            "verified":row.get("verified") is True,
            "provenance":row.get("provenance"),
        }
        for row in evidence
    ]
    predicate_id="support-portfolio-v8-set-closure-sha256:"+_digest({
        "claim_text":text,
        "evidence":binding,
        "closure_scope":"FINITE_EXPLICIT_MEMBERSHIP_AND_SUBSET_GRAPH_ONLY",
    })

    support_ids=list(closure.get("support_evidence_ids") or [])
    conflict_ids=list(closure.get("conflict_evidence_ids") or [])
    relation_audit=[
        {"evidence_id":eid,"relation":"SUPPORT_PREMISE","grammar":"SET_MEMBERSHIP_CLOSURE_V1"}
        for eid in support_ids
    ]+[
        {"evidence_id":eid,"relation":"CONFLICTS","grammar":"SET_MEMBERSHIP_CLOSURE_V1"}
        for eid in conflict_ids
    ]

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__SELECTED_SUPPORT_PREDICATE_V8_SET_CLOSURE_PROVED_"+truth,
        "predicate_id":predicate_id,
        "requested_predicate_id":payload.get("predicate_id"),
        "requested_predicate_id_authority":False,
        "claim_id":cid,
        "claim_text_sha256":hashlib.sha256(text.encode()).hexdigest(),
        "evidence_set_sha256":_digest(binding),
        "predicate_truth":truth,
        "truthful_precommitment_observation":True,
        "selected_policy_id":TRUE_POLICY if truth=="TRUE" else FALSE_POLICY,
        "support_evidence_ids":support_ids,
        "conflict_evidence_ids":conflict_ids,
        "relation_audit":relation_audit,
        "semantic_proof_audit":[],
        "set_membership_closure":closure,
        "support_route":"FINITE_SET_INCLUSION_MEMBERSHIP_CLOSURE_V1",
        "source_authorization_verified":False,
        "policy_adequacy_authority":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "boundary":"V7_PLUS_FINITE_EXPLICIT_MEMBERSHIP_SUBSET_GRAPH_CLOSURE_ONLY",
    }

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
