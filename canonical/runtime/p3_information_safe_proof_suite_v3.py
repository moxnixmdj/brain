"""Bounded information-safe P3 prequalification population.

Public inputs contain required/optional claims, audience, objective, raw numeric
evidence and provenance. Support, conflict, decision relevance and selected claims
are evaluator-only. This is prequalification, not whole-contract proof.
"""
from __future__ import annotations
import random
from typing import Any,Mapping

CONTRACT="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
AUDIENCE_PRIORITY={
 "executive":("risk","trend"),
 "engineer":("mechanism","risk"),
 "auditor":("control","risk"),
}

def _satisfies(claim:Mapping[str,Any], value:float)->bool:
    rel=claim["relation"]; t=float(claim["threshold"])
    if rel=="at_least": return value>=t
    if rel=="at_most": return value<=t
    raise ValueError("RELATION")

def generate_case(seed:int,difficulty:int=3)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool) or not 1<=difficulty<=5:
        raise ValueError("INPUT")
    r=random.Random(seed)
    audience=r.choice(sorted(AUDIENCE_PRIORITY))
    kinds=("risk","trend","mechanism","control","detail")
    claim_count=5+difficulty
    claims=[]
    for i in range(claim_count):
        claims.append({
          "claim_id":f"C{i}",
          "metric":f"M{i}",
          "relation":r.choice(("at_least","at_most")),
          "threshold":r.randint(30,70),
          "kind":r.choice(kinds),
          "text":f"Claim C{i} about metric M{i}",
        })
    required=[x["claim_id"] for x in claims[:2+difficulty//2]]
    evidence=[]; support={}; relevant={}
    for c in claims:
        vals=[]
        n=2 if r.random()>.25 else 3
        base=int(c["threshold"])
        for j in range(n):
            # Mixture produces supported, contradicted, and conflicted claim sets.
            delta=r.choice((-15,-8,8,15))
            value=float(base+delta)
            vals.append(value)
            evidence.append({
              "evidence_id":f"E-{c['claim_id']}-{j}",
              "metric":c["metric"],
              "value":value,
              "unit":"index_point",
              "provenance":[f"SRC-{seed}-{c['claim_id']}-{j}"],
            })
        votes=[_satisfies(c,v) for v in vals]
        support[c["claim_id"]]={
          "positive":sum(votes),
          "negative":len(votes)-sum(votes),
          "conflicted":any(votes) and not all(votes),
        }
        relevant[c["claim_id"]]=(c["claim_id"] in required or c["kind"] in AUDIENCE_PRIORITY[audience])
    budget=max(len(required),min(claim_count,len(required)+1+difficulty//2))
    ranked=[]
    uncertainty=[]
    for c in claims:
        h=support[c["claim_id"]]
        supported=h["positive"]>0 and h["positive"]>=h["negative"]
        if supported and relevant[c["claim_id"]]:
            ranked.append((0 if c["claim_id"] in required else 1,c["claim_id"]))
        if h["conflicted"]: uncertainty.append(c["claim_id"])
    ranked.sort()
    selected=[cid for _,cid in ranked[:budget]]
    return {
      "contract":CONTRACT,
      "task":{
        "objective":"Produce a grounded concise synthesis for the stated audience.",
        "audience":audience,
        "required_claims":required,
        "claims":claims,
        "evidence":evidence,
        "max_claims":budget,
      },
      "_oracle":{
        "selected_claims":selected,
        "uncertainty_claims":sorted(set(uncertainty)&set(selected)),
        "hidden_support_graph":support,
        "hidden_decision_relevance":relevant,
      },
    }

def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:v for k,v in case.items() if k!="_oracle"}

def score_case(case:Mapping[str,Any],candidate:Mapping[str,Any])->dict[str,Any]:
    selected=candidate.get("selected_claims")
    uncertainty=candidate.get("uncertainty_claims")
    if not isinstance(selected,list) or not isinstance(uncertainty,list):
        return {"pass":False,"reason":"OUTPUT_SCHEMA"}
    if len(selected)>int(case["task"]["max_claims"]):
        return {"pass":False,"reason":"BUDGET"}
    o=case["_oracle"]
    ok=selected==o["selected_claims"] and sorted(uncertainty)==o["uncertainty_claims"]
    return {"pass":ok,"reason":"PASS" if ok else "HIDDEN_SUPPORT_RELEVANCE_MISMATCH"}
