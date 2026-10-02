"""Brain candidate adapter for information-safe P2/P3 prequalification.

This is a proposal route only. It uses candidate-visible evidence, objective,
audience and constraints. It never imports the evaluator or hidden oracle.
Terminal capability credit requires fresh post-freeze results.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Mapping

P2="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
P3="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"


def _p2(task:Mapping[str,Any])->dict[str,Any]:
    audience=str(task.get("audience") or "")
    required=set(str(x) for x in task.get("required_topics",[]))
    evidence=task.get("evidence") or []
    facts={str(x.get("fact_id")):x for x in evidence if isinstance(x,Mapping)}
    edits=[x for x in (task.get("edit_candidates") or []) if isinstance(x,Mapping)]
    budget=int(task.get("edit_budget") or 0)
    # Candidate-side judgment from allowed visible information only.
    def estimate(e:Mapping[str,Any])->int:
        claims=[str(x) for x in (e.get("claims") or [])]
        grounded=bool(claims) and all(x in facts for x in claims)
        topic=str(e.get("topic") or "")
        analysis=str(e.get("analysis_kind") or "")
        fit=str(e.get("intended_audience") or "")==audience
        return (
            (5 if grounded else -12)
            +(4 if grounded and topic in required and analysis!="layout" else 0)
            +(3 if fit else -1)
            +(2 if analysis!="layout" else 0)
        )
    best=None
    for n in range(len(edits)+1):
        for subset in combinations(edits,n):
            try: cost=sum(int(x.get("cost")) for x in subset)
            except Exception: continue
            if cost>budget: continue
            ids=tuple(sorted(str(x.get("id")) for x in subset))
            score=sum(estimate(x) for x in subset)
            covered={
                str(x.get("topic")) for x in subset
                if estimate(x)>0 and str(x.get("analysis_kind") or "")!="layout"
            }
            score-=20*len(required-covered)
            key=(-score,cost,ids)
            if best is None or key<best[0]:
                best=(key,ids)
    return {"selected_edits":list(best[1] if best else ()),"terminal_authority":False}


def _p3(task:Mapping[str,Any])->dict[str,Any]:
    required=[str(x) for x in task.get("required_claims",[])]
    focus=set(str(x) for x in task.get("focus_topics",[]))
    evidence=[x for x in (task.get("evidence") or []) if isinstance(x,Mapping)]
    max_claims=int(task.get("max_claims") or 0)
    by_claim={}
    topic={}
    for row in evidence:
        cid=str(row.get("claim_id") or "")
        if not cid: continue
        by_claim.setdefault(cid,[]).append(str(row.get("stance") or ""))
        topic[cid]=str(row.get("topic") or "")
    ranked=[]; uncertainty=[]
    for cid,stances in by_claim.items():
        s=stances.count("supports"); r=stances.count("refutes")
        supported=s>0 and s>=r
        if not supported: continue
        priority=0 if cid in required else (1 if topic.get(cid) in focus else 2)
        if priority<2: ranked.append((priority,cid))
        if s and r: uncertainty.append(cid)
    ranked.sort()
    selected=[cid for _,cid in ranked[:max_claims]]
    return {
        "selected_claims":selected,
        "uncertainty_claims":sorted(set(uncertainty)&set(selected)),
        "terminal_authority":False,
    }


def solve(public:Mapping[str,Any])->dict[str,Any]:
    contract=public.get("contract"); task=public.get("task")
    if not isinstance(task,Mapping): raise ValueError("TASK_INVALID")
    if contract==P2: return _p2(task)
    if contract==P3: return _p3(task)
    raise ValueError("UNSUPPORTED_CONTRACT")
