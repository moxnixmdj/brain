"""Brain proposal candidate for P3 information-safe v3.

No evaluator imports and no hidden support/relevance labels. The candidate derives
claim support/conflict from raw numeric evidence and ranks optional claims from the
visible audience and claim kind. Prequalification only.
"""
from __future__ import annotations
from typing import Any,Mapping

CONTRACT="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
AUDIENCE_PRIORITY={
 "executive":("risk","trend"),
 "engineer":("mechanism","risk"),
 "auditor":("control","risk"),
}

def _satisfies(claim:Mapping[str,Any],value:float)->bool:
    t=float(claim["threshold"])
    if claim["relation"]=="at_least": return value>=t
    if claim["relation"]=="at_most": return value<=t
    raise ValueError("RELATION")

def solve(public:Mapping[str,Any])->dict[str,Any]:
    if public.get("contract")!=CONTRACT or not isinstance(public.get("task"),Mapping):
        raise ValueError("TASK")
    t=public["task"]; audience=str(t.get("audience") or "")
    required=[str(x) for x in t.get("required_claims",[])]
    claims=[x for x in t.get("claims",[]) if isinstance(x,Mapping)]
    evidence=[x for x in t.get("evidence",[]) if isinstance(x,Mapping)]
    by_metric={}
    for e in evidence:
        by_metric.setdefault(str(e.get("metric") or ""),[]).append(float(e["value"]))
    ranked=[]; uncertainty=[]
    prefs=set(AUDIENCE_PRIORITY.get(audience,()))
    for c in claims:
        cid=str(c.get("claim_id") or "")
        vals=by_metric.get(str(c.get("metric") or ""),[])
        votes=[_satisfies(c,v) for v in vals]
        if not votes: continue
        supported=sum(votes)>0 and sum(votes)>=len(votes)-sum(votes)
        relevant=cid in required or str(c.get("kind") or "") in prefs
        if supported and relevant: ranked.append((0 if cid in required else 1,cid))
        if any(votes) and not all(votes): uncertainty.append(cid)
    ranked.sort()
    selected=[cid for _,cid in ranked[:int(t.get("max_claims") or 0)]]
    return {
      "selected_claims":selected,
      "uncertainty_claims":sorted(set(uncertainty)&set(selected)),
      "terminal_authority":False,
    }
