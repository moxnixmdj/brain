"""Selected required-claim support truth certificate v6.

Checked support portfolio, in strict precedence order:
1. source-declared simple equivalence where definition-bearing evidence is present;
2. exact arbitrary-proposition attestation/denial;
3. exact Decimal numeric relations over bounded entity/field/value facts;
4. exact entity/field/value equality facts;
5. mechanically checked successful-launch event nominalization, only if 1-4 are unresolved;\n6. proof-carrying whole-proposition forward entailment, only if 1-5 are unresolved.

Resolved existing grammars cannot be overridden by caller-proposed semantic proofs.
No guessed paraphrase, synonymy, source authority, optional relevance, policy
adequacy, DB admission, U subtraction, or terminal credit is inferred.
"""
from __future__ import annotations

import hashlib, json, re
from typing import Any, Mapping, Sequence

from canonical.runtime import bounded_claim_support as facts
from canonical.runtime import bounded_attestation_support_v1 as attest
from canonical.runtime import bounded_source_declared_equivalence_support_v1 as defined
from canonical.runtime import bounded_numeric_relation_support_v1 as numeric
from canonical.runtime.proof_carrying_proposition_entailment_v1 import verify_entailment\nfrom canonical.runtime import bounded_successful_launch_event_entailment_v1 as launch_event

SCHEMA="PROJECT_BRAIN_SELECTED_SUPPORT_TRUTH_CERTIFICATE_V6"
RULE="REQUIRED_CLAIM_SUPPORT_PORTFOLIO__ATTESTATION_DEFINED_EQUIVALENCE_NUMERIC_RELATION_FACT_SUCCESSFUL_LAUNCH_EVENT_PROOF_CARRYING_ENTAILMENT"
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
         "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
    if detail: out["detail"]=detail
    return out

def _classify_existing(claim:str,evidence:str,eid:str)->tuple[str|None,str]:
    if re.search(r"\b(?:means|refers to|is defined as)\b",evidence,re.I):
        out=defined.classify_support(claim,evidence,evidence_id=eid)
        if out.get("status")=="RESOLVED":
            return out.get("relation"),"SOURCE_DECLARED_EQUIVALENCE_V1"
        return None,"UNRESOLVED_DEFINITION_BEARING_EVIDENCE"

    out=attest.classify_support(claim,evidence,evidence_id=eid)
    if out.get("status")=="RESOLVED" and out.get("relation") in {"SUPPORTS","CONFLICTS"}:
        return out.get("relation"),"EXACT_ATTESTATION_V1"

    nclaim=numeric.parse_numeric_relation_claim(claim)
    if nclaim.get("claim_in_scope") is True:
        nout=numeric.classify_support(claim,evidence,evidence_id=eid)
        if nout.get("status")=="RESOLVED":
            return nout.get("relation"),"NUMERIC_RELATION_V1"
        return None,"UNRESOLVED_NUMERIC_RELATION_EVIDENCE"

    if out.get("status")=="RESOLVED":
        return out.get("relation"),"EXACT_ATTESTATION_V1"

    fout=facts.classify_support(claim,evidence,evidence_id=eid)
    if fout.get("status")=="RESOLVED":
        return fout.get("relation"),"ENTITY_FIELD_VALUE_FACT_V1"
    return None,"UNRESOLVED"

def evaluate(payload:Mapping[str,Any],*,allow_test_fixtures:bool=False)->dict[str,Any]:
    if not isinstance(payload,Mapping): return _fail("PAYLOAD_MAPPING_REQUIRED")
    alias=payload.get("predicate_id")
    if not isinstance(alias,str) or not alias.strip(): return _fail("PREDICATE_ALIAS_REQUIRED")
    claim=payload.get("claim"); evidence=payload.get("evidence")
    semantic_proofs=payload.get("semantic_proofs",{})
    if not isinstance(claim,Mapping): return _fail("CLAIM_REQUIRED")
    if set(claim)-_ALLOWED_CLAIM: return _fail("UNTRUSTED_CLAIM_METADATA_FORBIDDEN")
    if not isinstance(semantic_proofs,Mapping): return _fail("SEMANTIC_PROOFS_MAPPING_REQUIRED")
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
    extra=sorted(set(semantic_proofs)-seen)
    if extra: return _fail("SEMANTIC_PROOF_FOR_UNKNOWN_EVIDENCE",extra=extra)
    rows.sort(key=lambda r:r["evidence_id"])

    supports=[];conflicts=[];unresolved=[];audit=[];proof_audit=[]
    for row in rows:
        eid=row["evidence_id"]
        relation,grammar=_classify_existing(text,row["text"],eid)
        if relation is None:
            eout=launch_event.classify_support(text,row["text"],evidence_id=eid)
            if eout.get("status")=="RESOLVED":
                relation=eout.get("relation"); grammar="SUCCESSFUL_LAUNCH_EVENT_ENTAILMENT_V1"
        if relation is None and eid in semantic_proofs:
            proof=semantic_proofs[eid]
            if not isinstance(proof,Mapping):
                return _fail("SEMANTIC_PROOF_ROW_INVALID",evidence_id=eid)
            ent=verify_entailment(
                {"evidence_text":row["text"],"claim_text":text,"steps":proof.get("steps")},
                allow_test_fixtures=allow_test_fixtures,
            )
            proof_audit.append({"evidence_id":eid,"status":ent.get("status"),"pass":ent.get("pass"),
                                "step_count":ent.get("step_count"),"step_audit":ent.get("step_audit")})
            if ent.get("pass") is True and ent.get("predicate_truth")=="TRUE":
                relation="SUPPORTS"; grammar="PROOF_CARRYING_PROPOSITION_ENTAILMENT_V1"
        if relation is None:
            unresolved.append(eid);continue
        audit.append({"evidence_id":eid,"relation":relation,"grammar":grammar})
        if relation=="SUPPORTS": supports.append(eid)
        elif relation=="CONFLICTS": conflicts.append(eid)

    claim_sha=hashlib.sha256(text.encode()).hexdigest()
    predicate_id="support-portfolio-v6-sha256:"+_digest({"rule":RULE,"claim_text_sha256":claim_sha,"required":True})
    binding=[]
    for r in rows:
        b={"evidence_id":r["evidence_id"],"text_sha256":hashlib.sha256(r["text"].encode()).hexdigest(),
           "verified":True,"provenance":r["provenance"]}
        if r["evidence_id"] in semantic_proofs:
            b["semantic_proof_sha256"]=_digest(semantic_proofs[r["evidence_id"]])
        binding.append(b)
    evidence_sha=_digest(binding)
    base={"schema":SCHEMA,"predicate_id":predicate_id,"requested_predicate_id":alias,
          "requested_predicate_id_authority":False,"claim_id":cid,"claim_text_sha256":claim_sha,
          "evidence_set_sha256":evidence_sha,"source_authorization_verified":False,
          "policy_adequacy_authority":False,"db_admission_authority":False,
          "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
    if unresolved:
        return {**base,"pass":False,"status":"UNKNOWN__SUPPORT_RELATION_OUTSIDE_CHECKED_PORTFOLIO_V6",
                "reason":"ONE_OR_MORE_RELATIONS_UNRESOLVED","predicate_truth":"UNKNOWN",
                "truthful_precommitment_observation":False,"selected_policy_id":None,
                "unresolved_evidence_ids":sorted(unresolved),"relation_audit":audit,
                "semantic_proof_audit":proof_audit}

    holds=bool(supports) and not conflicts
    truth="TRUE" if holds else "FALSE"
    return {**base,"pass":True,"status":"PASS__SELECTED_SUPPORT_PREDICATE_V6_PROVED_"+truth,
            "predicate_truth":truth,"truthful_precommitment_observation":True,
            "selected_policy_id":TRUE_POLICY if holds else FALSE_POLICY,
            "support_evidence_ids":sorted(supports),"conflict_evidence_ids":sorted(conflicts),
            "relation_audit":audit,"semantic_proof_audit":proof_audit,
            "boundary":"V4_PORTFOLIO_PLUS_CHECKED_SUCCESSFUL_LAUNCH_EVENT_ENTAILMENT_PLUS_VERIFIED_WHOLE_PROPOSITION_FORWARD_ENTAILMENT_ONLY__NO_GENERAL_NLI"}

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
