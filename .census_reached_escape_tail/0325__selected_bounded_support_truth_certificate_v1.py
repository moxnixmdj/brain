"""Selected required-claim bounded-support truth certificate v1.

Recomputes one policy-changing predicate from visible evidence:
"this structurally required claim has at least one bounded-grammar support and
no bounded-grammar conflict."

Caller predicate labels, include flags, relevance labels, and support labels have
no authority. Unknown grammar stays UNKNOWN. Source authorization, policy adequacy,
U-subtraction, and terminality remain separate.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import bounded_claim_support as support

SCHEMA="PROJECT_BRAIN_SELECTED_BOUNDED_SUPPORT_TRUTH_CERTIFICATE_V1"
RULE="REQUIRED_CLAIM_HAS_SUPPORT_AND_ZERO_CONFLICTS__BOUNDED_FACT_GRAMMAR_V1"
TRUE_POLICY="ASSERT_REQUIRED_CLAIM_AS_SUPPORTED_WITH_PROVENANCE"
FALSE_POLICY="DO_NOT_ASSERT_REQUIRED_CLAIM_AS_SUPPORTED__PRESERVE_UNCERTAINTY_OR_SEEK_EVIDENCE"

_ALLOWED_CLAIM={"claim_id","text","required"}
_ALLOWED_EVIDENCE={"evidence_id","text","verified","provenance"}

def _digest(value:Any)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _fail(reason:str,**detail:Any)->dict[str,Any]:
    out={
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "predicate_truth":"UNKNOWN","truthful_precommitment_observation":False,
      "selected_policy_id":None,"source_authorization_verified":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    alias=payload.get("predicate_id")
    if not isinstance(alias,str) or not alias.strip():
        return _fail("PREDICATE_ALIAS_REQUIRED")
    claim=payload.get("claim")
    evidence=payload.get("evidence")
    if not isinstance(claim,Mapping):
        return _fail("CLAIM_REQUIRED")
    if set(claim)-_ALLOWED_CLAIM:
        return _fail("UNTRUSTED_CLAIM_METADATA_FORBIDDEN")
    cid=claim.get("claim_id"); text=claim.get("text")
    if not isinstance(cid,str) or not cid.strip() or not isinstance(text,str) or not text.strip():
        return _fail("CLAIM_FIELDS_REQUIRED")
    if claim.get("required") is not True:
        return _fail("CLAIM_NOT_STRUCTURALLY_REQUIRED")
    if not isinstance(evidence,Sequence) or isinstance(evidence,(str,bytes)) or not evidence:
        return _fail("EVIDENCE_SEQUENCE_REQUIRED")

    rows=[]; seen=set()
    for row in evidence:
        if not isinstance(row,Mapping):
            return _fail("EVIDENCE_ROW_INVALID")
        if set(row)-_ALLOWED_EVIDENCE:
            return _fail("UNTRUSTED_EVIDENCE_METADATA_FORBIDDEN")
        eid=row.get("evidence_id"); etext=row.get("text")
        if not isinstance(eid,str) or not eid.strip() or not isinstance(etext,str) or not etext.strip():
            return _fail("EVIDENCE_FIELDS_REQUIRED")
        if eid in seen:
            return _fail("DUPLICATE_EVIDENCE_ID")
        seen.add(eid)
        if row.get("verified") is not True:
            return _fail("UNVERIFIED_EVIDENCE_UNIT")
        prov=row.get("provenance")
        if not isinstance(prov,list) or not prov or not all(isinstance(p,Mapping) for p in prov):
            return _fail("EVIDENCE_PROVENANCE_REQUIRED")
        rows.append(dict(row))
    rows.sort(key=lambda r:r["evidence_id"])

    relations=[]; unresolved=[]; supports=[]; conflicts=[]
    for row in rows:
        rel=support.classify_support(text,row["text"],evidence_id=row["evidence_id"])
        if rel.get("status")!="RESOLVED":
            unresolved.append(row["evidence_id"])
            continue
        relation=rel.get("relation")
        relations.append({"evidence_id":row["evidence_id"],"relation":relation})
        if relation=="SUPPORTS": supports.append(row["evidence_id"])
        elif relation=="CONFLICTS": conflicts.append(row["evidence_id"])

    claim_descriptor={
      "rule":RULE,
      "claim_text_sha256":hashlib.sha256(text.encode("utf-8")).hexdigest(),
      "required":True,
    }
    verified_predicate_id="bounded-support-sha256:"+_digest(claim_descriptor)
    evidence_binding=[{
      "evidence_id":r["evidence_id"],
      "text_sha256":hashlib.sha256(r["text"].encode("utf-8")).hexdigest(),
      "verified":True,
      "provenance":r["provenance"],
    } for r in rows]
    evidence_sha=_digest(evidence_binding)

    if unresolved:
        return {
          "schema":SCHEMA,"pass":False,
          "status":"UNKNOWN__BOUNDED_SUPPORT_RELATION_UNRESOLVED",
          "reason":"ONE_OR_MORE_EVIDENCE_RELATIONS_OUTSIDE_CHECKED_GRAMMAR",
          "predicate_id":verified_predicate_id,
          "requested_predicate_id":alias,
          "requested_predicate_id_authority":False,
          "predicate_truth":"UNKNOWN",
          "claim_id":cid,"claim_text_sha256":claim_descriptor["claim_text_sha256"],
          "evidence_set_sha256":evidence_sha,
          "unresolved_evidence_ids":sorted(unresolved),
          "truthful_precommitment_observation":False,
          "selected_policy_id":None,
          "source_authorization_verified":False,
          "policy_adequacy_authority":False,"db_admission_authority":False,
          "u_subtraction_authority":False,"terminal_authority":False,
          "terminal_credit_delta":0,
        }

    holds=bool(supports) and not conflicts
    truth="TRUE" if holds else "FALSE"
    return {
      "schema":SCHEMA,"pass":True,
      "status":"PASS__BOUNDED_REQUIRED_CLAIM_SUPPORT_PREDICATE_PROVED_"+truth,
      "predicate_id":verified_predicate_id,
      "requested_predicate_id":alias,
      "requested_predicate_id_authority":False,
      "predicate_truth":truth,
      "claim_id":cid,
      "claim_text_sha256":claim_descriptor["claim_text_sha256"],
      "evidence_set_sha256":evidence_sha,
      "relation_audit":relations,
      "support_evidence_ids":sorted(supports),
      "conflict_evidence_ids":sorted(conflicts),
      "truthful_precommitment_observation":True,
      "selected_policy_id":TRUE_POLICY if holds else FALSE_POLICY,
      "source_authorization_verified":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,
      "boundary":"REQUIRED_CLAIM_SUPPORT_TRUTH_ONLY__BOUNDED_FACT_GRAMMAR__NO_GENERAL_RELEVANCE_OR_NLI_AUTHORITY",
    }

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
