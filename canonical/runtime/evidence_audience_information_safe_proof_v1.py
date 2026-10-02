"""Information-safe bounded preflight for evidence-to-audience synthesis.

This is deliberately a bounded preflight, not terminal authority. Candidate-visible
inputs contain raw controlled-language claims/evidence, audience requirements, and a
budget. Support/conflict/irrelevance labels remain hidden in the oracle.
"""
from __future__ import annotations

import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_EVIDENCE_AUDIENCE_INFORMATION_SAFE_PREFLIGHT_V1"

_ENTITIES=("Atlas","Boreal","Cygnus","Delta")
_FIELDS=("cost","duration","risk","capacity")
_VALUES=("8","12","15","low","medium","high")


def _fact(entity:str,field:str,value:str)->str:
    return f"{entity} {field} is {value}."


def _source_fact(source:str,entity:str,field:str,value:str)->str:
    return f"{source} reports that {entity} {field} is {value}."


def generate_case(seed:int, *, unsupported:bool=False)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED_MUST_BE_INTEGER")
    r=random.Random(seed)
    entity=r.choice(_ENTITIES)
    fields=r.sample(list(_FIELDS),3)
    values=r.sample(list(_VALUES),3)
    claims=[]
    evidence=[]
    oracle={"required_claim_ids":[],"support":{},"conflict":{},"irrelevant":[]}

    for i,(field,value) in enumerate(zip(fields,values)):
        cid=f"C{i}"
        claims.append({"claim_id":cid,"text":_fact(entity,field,value)})
        oracle["required_claim_ids"].append(cid)
        oracle["support"][cid]=[]
        oracle["conflict"][cid]=[]

        if not (unsupported and i==2):
            eid=f"E{i}S"
            evidence.append({"evidence_id":eid,"text":_source_fact(f"Source {i}A",entity,field,value)})
            oracle["support"][cid].append(eid)

        if i==1:
            alternatives=[x for x in _VALUES if x!=value]
            other=r.choice(alternatives)
            eid=f"E{i}C"
            evidence.append({"evidence_id":eid,"text":_source_fact(f"Source {i}B",entity,field,other)})
            oracle["conflict"][cid].append(eid)

    for j in range(3):
        other_entity=r.choice([x for x in _ENTITIES if x!=entity])
        field=r.choice(fields)
        value=r.choice(values)
        eid=f"D{j}"
        evidence.append({"evidence_id":eid,"text":_source_fact(f"Distractor {j}",other_entity,field,value)})
        oracle["irrelevant"].append(eid)

    r.shuffle(evidence)
    budget=sum(1 for cid in oracle["required_claim_ids"] if oracle["support"][cid])+sum(
        len(oracle["conflict"][cid]) for cid in oracle["required_claim_ids"]
    )
    return {
        "schema":SCHEMA,
        "behavior_id":"EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
        "seed":seed,
        "task":{
            "audience":"decision maker",
            "format":"concise evidence brief",
            "required_claim_ids":list(oracle["required_claim_ids"]),
            "claims":claims,
            "evidence":evidence,
            "max_evidence_units":budget,
            "rule":"SUPPORT_EVERY_REQUIRED_CLAIM__PRESERVE_MATERIAL_CONFLICT__OMIT_IRRELEVANT_EVIDENCE",
        },
        "_oracle":oracle,
    }


def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:v for k,v in case.items() if k!="_oracle"}


def score_case(case:Mapping[str,Any],candidate:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(candidate,Mapping):
        return {"pass":False,"reason":"CANDIDATE_NOT_OBJECT"}
    task=case["task"]
    oracle=case["_oracle"]
    selected=candidate.get("selected_evidence_ids")
    if not isinstance(selected,list) or any(not isinstance(x,str) for x in selected):
        return {"pass":False,"reason":"SELECTION_INVALID"}
    if len(selected)!=len(set(selected)):
        return {"pass":False,"reason":"SELECTION_DUPLICATE"}
    if len(selected)>int(task["max_evidence_units"]):
        return {"pass":False,"reason":"BUDGET_EXCEEDED"}

    selected_set=set(selected)
    if selected_set & set(oracle["irrelevant"]):
        return {"pass":False,"reason":"IRRELEVANT_EVIDENCE_SELECTED"}

    unsupported=[cid for cid in oracle["required_claim_ids"] if not oracle["support"][cid]]
    expected_status="INSUFFICIENT" if unsupported else "SYNTHESIZED"
    if candidate.get("status")!=expected_status:
        return {"pass":False,"reason":"STATUS_WRONG"}

    for cid in oracle["required_claim_ids"]:
        supports=set(oracle["support"][cid])
        conflicts=set(oracle["conflict"][cid])
        if supports and not (supports & selected_set):
            return {"pass":False,"reason":"REQUIRED_CLAIM_SUPPORT_MISSING","claim_id":cid}
        if conflicts and not conflicts.issubset(selected_set):
            return {"pass":False,"reason":"MATERIAL_CONFLICT_OMITTED","claim_id":cid}
        if not supports and candidate.get("status")!="INSUFFICIENT":
            return {"pass":False,"reason":"UNSUPPORTED_CLAIM_NOT_PRESERVED","claim_id":cid}

    return {
        "pass":True,
        "reason":"PASS",
        "unsupported_claim_ids":unsupported,
        "selected_count":len(selected),
        "budget":int(task["max_evidence_units"]),
    }
