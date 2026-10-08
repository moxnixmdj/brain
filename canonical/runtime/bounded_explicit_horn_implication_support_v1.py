"""Bounded explicit Horn implication support v1.

Checked fragment:
- fact evidence in Brain's existing entity/field/value grammar;
- explicit single-antecedent rules:
    "If <fact>, then <fact>."
    "<source> states [that] if <fact>, then <fact>."
    "<source> reports [that] if <fact>, then <fact>."
- deterministic forward chaining across finitely many facts/rules.

A claim is supported only if its exact normalized fact is derivable. It conflicts
only if a derivable fact has the same entity+field and a different value.
Unknown/malformed rule-shaped evidence fails closed to UNRESOLVED.

No contraposition, converse inference, negation-as-failure, ontology inference,
source authorization, policy adequacy, or general natural-language entailment.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from canonical.runtime import bounded_claim_support as facts

SCHEMA="PROJECT_BRAIN_BOUNDED_EXPLICIT_HORN_IMPLICATION_SUPPORT_V1"
MAX_ROWS=128
MAX_STEPS=256

_PREFIXES=(
    re.compile(r"^(?P<source>.+?)\s+reports\s+(?:that\s+)?(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>.+?)\s+states\s+(?:that\s+)?(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>[^:]+):\s*(?P<body>.+)$",re.I),
)
_RULE=re.compile(r"^if\s+(?P<antecedent>.+?),\s*then\s+(?P<consequent>.+?)\s*\.?$",re.I)
_HINT=re.compile(r"\bif\b.+\bthen\b",re.I)


def _strip_prefix(text:str)->tuple[str,str|None]:
    raw=" ".join(text.strip().split())
    for pat in _PREFIXES:
        m=pat.fullmatch(raw)
        if m:
            return m.group("body").strip(), " ".join(m.group("source").split())
    return raw,None


def _fact_key(row:Mapping[str,Any])->tuple[str,str,str]:
    return (str(row["entity"]),str(row["field"]),str(row["value"]))


def parse_rule(text:str,*,default_source:str|None=None)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"TEXT_REQUIRED","rule_in_scope":False}
    body,source=_strip_prefix(text)
    if source is None:
        source=default_source
    m=_RULE.fullmatch(body)
    if not m:
        return {
            "schema":SCHEMA,"status":"UNRESOLVED",
            "reason":"OUTSIDE_EXPLICIT_HORN_RULE_GRAMMAR",
            "rule_in_scope":bool(_HINT.search(body)),
            "terminal_authority":False,
        }
    a=facts.parse_fact(m.group("antecedent"),default_source=source or "RULE")
    c=facts.parse_fact(m.group("consequent"),default_source=source or "RULE")
    if a.get("status")!="RESOLVED" or c.get("status")!="RESOLVED":
        return {
            "schema":SCHEMA,"status":"UNRESOLVED","rule_in_scope":True,
            "reason":"RULE_FACT_OUTSIDE_BOUNDED_FACT_GRAMMAR",
            "antecedent_status":a.get("status"),"consequent_status":c.get("status"),
            "terminal_authority":False,
        }
    return {
        "schema":SCHEMA,"status":"RESOLVED","rule_in_scope":True,
        "antecedent":{k:a["fact"][k] for k in ("entity","field","value")},
        "consequent":{k:c["fact"][k] for k in ("entity","field","value")},
        "source":source,
        "terminal_authority":False,
    }


def evaluate_support(claim_text:str,evidence:Sequence[Mapping[str,Any]])->dict[str,Any]:
    claim=facts.parse_fact(claim_text,default_source="CLAIM")
    if claim.get("status")!="RESOLVED":
        return {
            "schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
            "reason":"CLAIM_OUTSIDE_BOUNDED_FACT_GRAMMAR",
            "claim_in_scope":False,"terminal_authority":False,
        }
    if not isinstance(evidence,Sequence) or isinstance(evidence,(str,bytes)) or not evidence:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","relation":"UNKNOWN","reason":"EVIDENCE_SEQUENCE_REQUIRED","terminal_authority":False}
    if len(evidence)>MAX_ROWS:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","relation":"UNKNOWN","reason":"EVIDENCE_ROW_BOUND_EXCEEDED","terminal_authority":False}

    base_facts:dict[tuple[str,str,str],set[str]]={}
    rules:list[dict[str,Any]]=[]
    unresolved:list[str]=[]
    rule_count=0

    for i,row in enumerate(evidence):
        if not isinstance(row,Mapping):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","relation":"UNKNOWN","reason":f"EVIDENCE_ROW_INVALID:{i}","terminal_authority":False}
        eid=row.get("evidence_id"); text=row.get("text")
        if not isinstance(eid,str) or not eid or not isinstance(text,str) or not text.strip():
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","relation":"UNKNOWN","reason":f"EVIDENCE_FIELDS_REQUIRED:{i}","terminal_authority":False}

        rule=parse_rule(text,default_source=eid)
        if rule.get("status")=="RESOLVED":
            rule_count+=1
            rules.append({"evidence_id":eid,**rule})
            continue
        if rule.get("rule_in_scope") is True:
            unresolved.append(eid)
            continue

        fact=facts.parse_fact(text,default_source=eid)
        if fact.get("status")!="RESOLVED":
            unresolved.append(eid)
            continue
        key=_fact_key(fact["fact"])
        base_facts.setdefault(key,set()).add(eid)

    if rule_count==0:
        return {
            "schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
            "reason":"NO_EXPLICIT_HORN_RULE_PRESENT","claim_in_scope":True,
            "unresolved_evidence_ids":sorted(unresolved),"terminal_authority":False,
        }
    if unresolved:
        return {
            "schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
            "reason":"ONE_OR_MORE_EVIDENCE_ROWS_OUTSIDE_HORN_FACT_GRAMMAR",
            "claim_in_scope":True,"unresolved_evidence_ids":sorted(unresolved),
            "terminal_authority":False,
        }

    derived={k:set(v) for k,v in base_facts.items()}
    applied:set[tuple[int,tuple[str,str,str]]]=set()
    steps=0
    changed=True
    while changed:
        changed=False
        for idx,rule in enumerate(rules):
            ak=_fact_key(rule["antecedent"]); ck=_fact_key(rule["consequent"])
            if ak not in derived:
                continue
            marker=(idx,ak)
            if marker in applied:
                continue
            applied.add(marker)
            steps+=1
            if steps>MAX_STEPS:
                return {"schema":SCHEMA,"status":"FAIL_CLOSED","relation":"UNKNOWN","reason":"FORWARD_CHAIN_STEP_BOUND_EXCEEDED","terminal_authority":False}
            proof=set(derived[ak]); proof.add(rule["evidence_id"])
            before=len(derived.get(ck,set()))
            derived.setdefault(ck,set()).update(proof)
            if len(derived[ck])!=before:
                changed=True

    c=claim["fact"]; ckey=_fact_key(c)
    supports=sorted(derived.get(ckey,set()))
    conflicts=[]
    for (entity,field,value),proof in derived.items():
        if entity==c["entity"] and field==c["field"] and value!=c["value"]:
            conflicts.extend(proof)
    conflicts=sorted(set(conflicts))

    if supports and conflicts:
        relation="BOTH"
    elif supports:
        relation="SUPPORTS"
    elif conflicts:
        relation="CONFLICTS"
    else:
        relation="UNRELATED"

    return {
        "schema":SCHEMA,"status":"RESOLVED","relation":relation,"claim_in_scope":True,
        "claim":{"entity":c["entity"],"field":c["field"],"value":c["value"]},
        "support_evidence_ids":supports,
        "conflict_evidence_ids":conflicts,
        "rule_count":rule_count,
        "base_fact_count":len(base_facts),
        "derived_fact_count":len(derived),
        "forward_chain_steps":steps,
        "terminal_authority":False,
        "scope":"EXPLICIT_SINGLE_ANTECEDENT_HORN_RULES_OVER_BOUNDED_ENTITY_FIELD_VALUE_FACTS_ONLY",
        "boundary":"NO_CONTRAPOSITION_CONVERSE_CLOSED_WORLD_NEGATION_ONTOLOGY_OR_GENERAL_NLI",
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    args=args or {}
    return evaluate_support(str(args.get("claim_text") or ""),args.get("evidence") or [])
