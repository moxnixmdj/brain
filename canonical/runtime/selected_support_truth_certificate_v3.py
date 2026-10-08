"""Selected required-claim support truth certificate v3.

Classifier portfolio:
1. bounded entity/field/value fact relation;
2. exact arbitrary-proposition attestation/denial;\n3. one checked launch-event nominalization entailment.

Every visible evidence relation must resolve in at least one checked grammar.
No general paraphrase entailment, source authority, optional relevance, adequacy, or
terminal credit is inferred.
"""
from __future__ import annotations

import hashlib, json
from typing import Any, Mapping, Sequence

from canonical.runtime import bounded_claim_support as facts
from canonical.runtime import bounded_attestation_support_v1 as attest\nfrom canonical.runtime import bounded_event_nominalization_support_v1 as event_nom

SCHEMA="PROJECT_BRAIN_SELECTED_SUPPORT_TRUTH_CERTIFICATE_V3"
RULE="REQUIRED_CLAIM_SUPPORT_PORTFOLIO__FACT_V1_OR_EXACT_ATTESTATION_V1_OR_EVENT_NOMINALIZATION_V1"
TRUE_POLICY="ASSERT_REQUIRED_CLAIM_AS_SUPPORTED_WITH_PROVENANCE"
FALSE_POLICY="DO_NOT_ASSERT_REQUIRED_CLAIM_AS_SUPPORTED__PRESERVE_UNCERTAINTY_OR_SEEK_EVIDENCE"
_ALLOWED_CLAIM={"claim_id","text","required"}
_ALLOWED_EVIDENCE={"evidence_id","text","verified","provenance"}

def _digest(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _fail(reason:str,**detail:Any)->dict[str,Any]:
    out={"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
         "predicate_truth":"UNKNOWN","truthful_precommitment_observation":False,
         "selected_policy_id":None,"source_authorization_verified":False,
         "policy_adequacy_authority":False,"db_admission_authority":False,
         "u_subtraction_authority":False,"terminal_authority":False,
         "terminal_credit_delta":0}
    if detail: out["detail"]=detail
    return out

def _classify(claim:str,evidence:str,eid:str)->tuple[str|None,str]:
    first=facts.classify_support(claim,evidence,evidence_id=eid)
    if first.get("status")=="RESOLVED":
        return first.get("relation"),"ENTITY_FIELD_VALUE_FACT_V1"
    second=attest.classify_support(claim,evidence,evidence_id=eid)
    if second.get("status")=="RESOLVED":
        return second.get("relation"),"EXACT_ATTESTATION_V1"
    third=event_nom.classify_support(claim,evidence,evidence_id=eid)\n    if third.get("status")=="RESOLVED":\n        return third.get("relation"),"EVENT_NOMINALIZATION_V1"\n    return None,"UNRESOLVED"

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping): return _fail("PAYLOAD_MAPPING_REQUIRED")
    alias=payload.get("predicate_id")
    if not isinstance(alias,str) or not alias.strip(): return _fail("PREDICATE_ALIAS_REQUIRED")
    claim=payload.get("claim"); evidence=payload.get("evidence")
    if not isinstance(claim,Mapping): return _fail("CLAIM_REQUIRED")
    if set(claim)-_ALLOWED_CLAIM: return _fail("UNTRUSTED_CLAIM_METADATA_FORBIDDEN")
    cid=claim.get("claim_id"); text=claim.get("text")
    if not isinstance(cid,str) or not cid.strip() or not isinstance(text,str) or not text.strip():
        return _fail("CLAIM_FIELDS_REQUIRED")
    if claim.get("required") is not True: return _fail("CLAIM_NOT_STRUCTURALLY_REQUIRED")
    if not isinstance(evidence,Sequence) or isinstance(evidence,(str,bytes)) or not evidence:
        return _fail("EVIDENCE_SEQUENCE_REQUIRED")
    rows=[];seen=set()
    for row in evidence:
        if not isinstance(row,Mapping): return _fail("EVIDENCE_ROW_INVALID")
        if set(row)-_ALLOWED_EVIDENCE: return _fail("UNTRUSTED_EVIDENCE_METADATA_FORBIDDEN")
        eid=row.get("evidence_id");et=row.get("text")
        if not isinstance(eid,str) or not eid.strip() or not isinstance(et,str) or not et.strip():
            return _fail("EVIDENCE_FIELDS_REQUIRED")
        if eid in seen: return _fail("DUPLICATE_EVIDENCE_ID")
        seen.add(eid)
        if row.get("verified") is not True: return _fail("UNVERIFIED_EVIDENCE_UNIT")
        prov=row.get("provenance")
        if not isinstance(prov,list) or not prov or not all(isinstance(p,Mapping) for p in prov):
            return _fail("EVIDENCE_PROVENANCE_REQUIRED")
        rows.append(dict(row))
    rows.sort(key=lambda r:r["evidence_id"])

    supports=[];conflicts=[];unresolved=[];audit=[]
    for row in rows:
        relation,grammar=_classify(text,row["text"],row["evidence_id"])
        if relation is None:
            unresolved.append(row["evidence_id"]);continue
        audit.append({"evidence_id":row["evidence_id"],"relation":relation,"grammar":grammar})
        if relation=="SUPPORTS": supports.append(row["evidence_id"])
        elif relation=="CONFLICTS": conflicts.append(row["evidence_id"])

    claim_sha=hashlib.sha256(text.encode()).hexdigest()
    predicate_id="support-portfolio-sha256:"+_digest({"rule":RULE,"claim_text_sha256":claim_sha,"required":True})
    binding=[{"evidence_id":r["evidence_id"],"text_sha256":hashlib.sha256(r["text"].encode()).hexdigest(),
              "verified":True,"provenance":r["provenance"]} for r in rows]
    evidence_sha=_digest(binding)
    base={
      "schema":SCHEMA,"predicate_id":predicate_id,"requested_predicate_id":alias,
      "requested_predicate_id_authority":False,"claim_id":cid,"claim_text_sha256":claim_sha,
      "evidence_set_sha256":evidence_sha,"source_authorization_verified":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
    }
    if unresolved:
        return {**base,"pass":False,"status":"UNKNOWN__SUPPORT_RELATION_OUTSIDE_CHECKED_PORTFOLIO",
                "reason":"ONE_OR_MORE_RELATIONS_UNRESOLVED","predicate_truth":"UNKNOWN",
                "truthful_precommitment_observation":False,"selected_policy_id":None,
                "unresolved_evidence_ids":sorted(unresolved),"relation_audit":audit}
    holds=bool(supports) and not conflicts
    truth="TRUE" if holds else "FALSE"
    return {**base,"pass":True,"status":"PASS__SELECTED_SUPPORT_PREDICATE_PROVED_"+truth,
            "predicate_truth":truth,"truthful_precommitment_observation":True,
            "selected_policy_id":TRUE_POLICY if holds else FALSE_POLICY,
            "support_evidence_ids":sorted(supports),"conflict_evidence_ids":sorted(conflicts),
            "relation_audit":audit,
            "boundary":"FACT_EXACT_ATTESTATION_OR_CHECKED_EVENT_NOMINALIZATION_ONLY__NO_GENERAL_PARAPHRASE_NLI_OR_GENERAL_RELEVANCE"}

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
