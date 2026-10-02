"""Information-safe prequalification suites for P2/P3 terminal contracts.

These are evaluation generators, not capability implementations. They freeze the
information boundary and oracle semantics without consuming terminal cases. Fresh
terminal seeds must be selected only after the candidate package is frozen.

P2: PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001
P3: EVIDENCE_TO_AUDIENCE_SYNTHESIS_001
"""
from __future__ import annotations

import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_P2_P3_INFORMATION_SAFE_PROOF_SUITES_V2"
P2="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
P3="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
CONTRACTS=(P2,P3)
AUDIENCES=("executive","engineer","auditor","operator")
DOMAINS=("software","finance","operations","science","research","policy-neutral-analysis")


def _rng(seed:int)->random.Random:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED_MUST_BE_INT")
    return random.Random(seed)


def _p2(seed:int,difficulty:int)->dict[str,Any]:
    r=_rng(seed)
    audience=r.choice(AUDIENCES)
    domain=r.choice(DOMAINS)
    facts=[
        {"fact_id":f"F{i}","topic":f"T{i%3}","text":f"{domain} fact {i} value {r.randint(10,99)}","provenance":[f"SRC-{seed}-{i}"]}
        for i in range(4+difficulty)
    ]
    required_topics=sorted({f["topic"] for f in r.sample(facts,k=min(2+difficulty//2,len(facts)))})
    rubric={"analysis":4,"evidence_grounding":5,"audience_fit":3,"clarity":2}
    edits=[]
    hidden={}
    for i in range(5+difficulty):
        supported=r.random()>0.22
        topic=r.choice([f["topic"] for f in facts])
        refs=sorted({f["fact_id"] for f in facts if f["topic"]==topic})
        if supported:
            claims=refs[:1]
        else:
            claims=[f"UNSUPPORTED-{i}"]
        intended_audience=r.choice(AUDIENCES)
        analysis_kind=r.choice(["quantify","compare","risk","summary","layout"])
        edit={
            "id":f"E{i}",
            "analysis_kind":analysis_kind,
            "topic":topic,
            "claims":claims,
            "intended_audience":intended_audience,
            "cost":r.randint(1,3),
            "text":f"{analysis_kind} {topic} for {intended_audience}",
        }
        edits.append(edit)
        hidden[edit["id"]]={
            "supported":supported,
            "required_topic":topic in required_topics,
            "audience_fit":intended_audience==audience,
            "analysis_value":analysis_kind!="layout",
        }
    budget=max(2,min(6,2+difficulty))
    task={
        "objective":f"Create a {domain} deliverable covering required topics with evidence and audience fit.",
        "audience":audience,
        "required_topics":required_topics,
        "rubric_weights":rubric,
        "evidence":facts,
        "current_draft":{"covered_topics":[],"audience":audience},
        "edit_candidates":edits,
        "edit_budget":budget,
    }
    def utility(eid:str)->int:
        h=hidden[eid]
        return (
            (5 if h["supported"] else -12)
            +(4 if h["required_topic"] and h["analysis_value"] else 0)
            +(3 if h["audience_fit"] else -1)
            +(2 if h["analysis_value"] else 0)
        )
    # Oracle selects the max-utility feasible subset, then min cost, then lexical IDs.
    best=None
    from itertools import combinations
    for n in range(len(edits)+1):
        for subset in combinations(edits,n):
            cost=sum(x["cost"] for x in subset)
            if cost>budget: continue
            ids=tuple(sorted(x["id"] for x in subset))
            score=sum(utility(x["id"]) for x in subset)
            covered={x["topic"] for x in subset if hidden[x["id"]]["supported"] and hidden[x["id"]]["analysis_value"]}
            # Missing required analytical coverage is a hard terminal defect.
            missing=set(required_topics)-covered
            if missing:
                score-=20*len(missing)
            key=(-score,cost,ids)
            if best is None or key<best[0]:
                best=(key,ids,score,cost,sorted(missing))
    assert best is not None
    return {
        "schema":SCHEMA,"contract":P2,"seed":seed,"difficulty":difficulty,"task":task,
        "_oracle":{
            "selected_edits":list(best[1]),"score":best[2],"cost":best[3],
            "missing_required_topics":best[4],"hidden_quality_factors":hidden,
        },
    }


def _p3(seed:int,difficulty:int)->dict[str,Any]:
    r=_rng(seed)
    audience=r.choice(AUDIENCES)
    domain=r.choice(DOMAINS)
    required_claims=[f"C{i}" for i in range(2+difficulty//2)]
    optional_claims=[f"O{i}" for i in range(3+difficulty)]
    all_claims=required_claims+optional_claims
    focus_topics=sorted({f"T{r.randrange(3)}" for _ in range(1+difficulty//2)})
    rows=[]
    hidden_support={}
    hidden_relevance={}
    for cid in all_claims:
        topic=f"T{r.randrange(3)}"
        hidden_relevance[cid]=(cid in required_claims) or topic in focus_topics
        source_count=2 if r.random()>0.25 else 1
        vals=[]
        for j in range(source_count):
            stance=r.choice(["supports","supports","refutes"])
            vals.append(stance)
            rows.append({
                "evidence_id":f"EV-{cid}-{j}",
                "claim_id":cid,
                "topic":topic,
                "statement":f"{domain} source {j} {stance} {cid}",
                "stance":stance,
                "provenance":[f"SRC-{seed}-{cid}-{j}"],
            })
        hidden_support[cid]={
            "supports":vals.count("supports"),
            "refutes":vals.count("refutes"),
            "conflicted":"supports" in vals and "refutes" in vals,
        }
    budget=max(len(required_claims),min(len(all_claims),len(required_claims)+difficulty//2+1))
    task={
        "objective":f"Synthesize a {domain} answer for {audience}; focus topics: {', '.join(focus_topics)}.",
        "audience":audience,
        "required_claims":required_claims,
        "focus_topics":focus_topics,
        "evidence":rows,
        "max_claims":budget,
    }
    admissible=[]
    uncertainty=[]
    for cid in all_claims:
        h=hidden_support[cid]
        supported=h["supports"]>0 and h["supports"]>=h["refutes"]
        if cid in required_claims and supported:
            admissible.append((0,cid))
        elif hidden_relevance[cid] and supported:
            admissible.append((1,cid))
        if h["conflicted"]:
            uncertainty.append(cid)
    admissible.sort()
    selected=[cid for _,cid in admissible[:budget]]
    # Required claims must be present if support exists; otherwise the oracle requires uncertainty.
    required_missing=[
        cid for cid in required_claims
        if cid not in selected and hidden_support[cid]["supports"]>0
    ]
    return {
        "schema":SCHEMA,"contract":P3,"seed":seed,"difficulty":difficulty,"task":task,
        "_oracle":{
            "selected_claims":selected,
            "uncertainty_claims":sorted(set(uncertainty)&set(selected)),
            "required_missing":required_missing,
            "hidden_support_graph":hidden_support,
            "hidden_decision_relevance":hidden_relevance,
        },
    }


def generate_case(contract:str,seed:int,difficulty:int=3)->dict[str,Any]:
    if contract not in CONTRACTS:
        raise ValueError("UNKNOWN_CONTRACT")
    if not isinstance(difficulty,int) or isinstance(difficulty,bool) or not 1<=difficulty<=5:
        raise ValueError("DIFFICULTY_1_TO_5")
    return _p2(seed,difficulty) if contract==P2 else _p3(seed,difficulty)


def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:v for k,v in case.items() if k!="_oracle"}


def score_case(case:Mapping[str,Any],candidate:Mapping[str,Any])->dict[str,Any]:
    c=case["contract"]; oracle=case["_oracle"]
    if c==P2:
        selected=candidate.get("selected_edits")
        if not isinstance(selected,list) or len(selected)!=len(set(selected)):
            return {"pass":False,"reason":"OUTPUT_SCHEMA_OR_DUPLICATE"}
        known={x["id"]:x for x in case["task"]["edit_candidates"]}
        if any(x not in known for x in selected):
            return {"pass":False,"reason":"UNKNOWN_EDIT"}
        cost=sum(known[x]["cost"] for x in selected)
        if cost>case["task"]["edit_budget"]:
            return {"pass":False,"reason":"BUDGET_EXCEEDED"}
        ok=tuple(sorted(selected))==tuple(sorted(oracle["selected_edits"]))
        return {"pass":ok,"reason":"PASS" if ok else "HIDDEN_QUALITY_PLAN_MISMATCH"}
    if c==P3:
        selected=candidate.get("selected_claims")
        uncertainty=candidate.get("uncertainty_claims")
        if not isinstance(selected,list) or not isinstance(uncertainty,list):
            return {"pass":False,"reason":"OUTPUT_SCHEMA_INVALID"}
        if len(selected)>case["task"]["max_claims"]:
            return {"pass":False,"reason":"BUDGET_EXCEEDED"}
        ok=(
            tuple(selected)==tuple(oracle["selected_claims"])
            and tuple(sorted(uncertainty))==tuple(oracle["uncertainty_claims"])
        )
        return {"pass":ok,"reason":"PASS" if ok else "HIDDEN_SUPPORT_RELEVANCE_MISMATCH"}
    raise ValueError("UNKNOWN_CONTRACT")
