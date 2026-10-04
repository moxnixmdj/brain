"""Deduction-before-observation primitives for Universal Learning V7.

Only independently verified, exact-byte-bound facts and rules may enter the
deductive closure. Anything not derivable remains an explicit empirical frontier.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_DEDUCTIVE_CLOSURE_V7"

class DeductiveClosureError(ValueError):
    pass

def _s(x:Any)->str:
    return " ".join(str(x or "").split())

def _items(xs)->list[str]:
    return sorted({_s(x) for x in (xs or []) if _s(x)})

def fact_digest(*,scope_id:str,fact:str)->str:
    scope=_s(scope_id); f=_s(fact)
    if not scope or not f:
        raise DeductiveClosureError("SCOPE_AND_FACT_REQUIRED")
    body=json.dumps({"scope_id":scope,"fact":f},sort_keys=True,separators=(",",":")).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def rule_digest(*,scope_id:str,rule_id:str,premises,conclusion:str)->str:
    scope=_s(scope_id); rid=_s(rule_id); c=_s(conclusion); ps=_items(premises)
    if not scope or not rid or not c:
        raise DeductiveClosureError("RULE_ID_SCOPE_AND_CONCLUSION_REQUIRED")
    body=json.dumps(
        {"scope_id":scope,"rule_id":rid,"premises":ps,"conclusion":c},
        sort_keys=True,separators=(",",":")
    ).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def _verified_fact(raw:Mapping[str,Any],scope_id:str)->tuple[str,str]:
    fact=_s(raw.get("fact"))
    rec=raw.get("verification_receipt")
    if not fact or not isinstance(rec,Mapping):
        raise DeductiveClosureError("VERIFIED_FACT_AND_RECEIPT_REQUIRED")
    if rec.get("independent_verified") is not True or rec.get("exact_byte_bound") is not True or rec.get("conclusion")!="success":
        raise DeductiveClosureError("FACT_RECEIPT_INVALID:"+fact)
    if _s(rec.get("scope_id"))!=scope_id or _s(rec.get("fact"))!=fact:
        raise DeductiveClosureError("FACT_RECEIPT_BINDING_MISMATCH:"+fact)
    if rec.get("fact_sha256")!=fact_digest(scope_id=scope_id,fact=fact):
        raise DeductiveClosureError("FACT_RECEIPT_DIGEST_MISMATCH:"+fact)
    rid=_s(rec.get("receipt_id"))
    if not rid:
        raise DeductiveClosureError("FACT_RECEIPT_ID_REQUIRED:"+fact)
    return fact,rid

def _verified_rule(raw:Mapping[str,Any],scope_id:str)->dict[str,Any]:
    rid=_s(raw.get("id")); ps=_items(raw.get("premises")); c=_s(raw.get("conclusion"))
    if not rid or not c:
        raise DeductiveClosureError("RULE_ID_AND_CONCLUSION_REQUIRED")
    rec=raw.get("verification_receipt")
    if not isinstance(rec,Mapping):
        raise DeductiveClosureError("RULE_RECEIPT_REQUIRED:"+rid)
    if rec.get("independent_verified") is not True or rec.get("exact_byte_bound") is not True or rec.get("conclusion")!="success":
        raise DeductiveClosureError("RULE_RECEIPT_INVALID:"+rid)
    if rec.get("sound_on_claimed_scope") is not True:
        raise DeductiveClosureError("RULE_SOUNDNESS_NOT_PROVED:"+rid)
    if _s(rec.get("scope_id"))!=scope_id or _s(rec.get("rule_id"))!=rid:
        raise DeductiveClosureError("RULE_RECEIPT_SCOPE_OR_ID_MISMATCH:"+rid)
    digest=rule_digest(scope_id=scope_id,rule_id=rid,premises=ps,conclusion=c)
    if rec.get("rule_sha256")!=digest:
        raise DeductiveClosureError("RULE_RECEIPT_DIGEST_MISMATCH:"+rid)
    receipt_id=_s(rec.get("receipt_id"))
    if not receipt_id:
        raise DeductiveClosureError("RULE_RECEIPT_ID_REQUIRED:"+rid)
    return {"id":rid,"premises":ps,"conclusion":c,"rule_sha256":digest,"receipt_id":receipt_id}

def derive(*,scope_id:str,verified_facts:Sequence[Mapping[str,Any]],verified_rules:Sequence[Mapping[str,Any]],required_facts=())->dict[str,Any]:
    scope=_s(scope_id)
    if not scope:
        raise DeductiveClosureError("SCOPE_ID_REQUIRED")
    facts=set()
    proofs={}
    for raw in verified_facts:
        fact,receipt=_verified_fact(raw,scope)
        if fact in facts:
            raise DeductiveClosureError("SOURCE_FACT_DUPLICATE:"+fact)
        facts.add(fact)
        proofs[fact]={"type":"SOURCE_VERIFIED_FACT","receipt_id":receipt}

    rules=[];seen=set()
    for raw in verified_rules:
        rule=_verified_rule(raw,scope)
        if rule["id"] in seen:
            raise DeductiveClosureError("RULE_ID_DUPLICATE:"+rule["id"])
        seen.add(rule["id"]); rules.append(rule)

    changed=True
    applied=[]
    while changed:
        changed=False
        for rule in rules:
            if rule["conclusion"] in facts:
                continue
            if set(rule["premises"])<=facts:
                facts.add(rule["conclusion"])
                proofs[rule["conclusion"]]={
                    "type":"DEDUCTIVE_RULE",
                    "rule_id":rule["id"],
                    "rule_receipt_id":rule["receipt_id"],
                    "premises":rule["premises"],
                }
                applied.append(rule["id"])
                changed=True

    required=_items(required_facts)
    unresolved=sorted(set(required)-facts)
    return {
        "schema":SCHEMA,
        "status":"PROOF_SUFFICIENT_NO_EMPIRICAL_FRONTIER" if required and not unresolved else "EMPIRICAL_FRONTIER_REMAINS",
        "scope_id":scope,
        "closure":sorted(facts),
        "proofs":{k:proofs[k] for k in sorted(proofs)},
        "applied_rule_ids":applied,
        "required_facts":required,
        "empirical_frontier":unresolved,
        "empirical_action_required":bool(unresolved),
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }
