"""Brain policy for bounded information-safe research-loop control.

Consumes normalized material requirements, current exact evidence receipts, public
source metadata, and search results. It never sees hidden source contents or hidden
coverage before retrieval.
"""
from __future__ import annotations
from typing import Any, Mapping


def next_action(public:Mapping[str,Any])->dict[str,Any]:
    reqs=[x for x in public.get("material_requirements",[]) if isinstance(x,Mapping) and x.get("material") is True]
    resolved={str(x) for x in public.get("resolved_requirement_ids",[])}
    unresolved=[x for x in reqs if str(x.get("id")) not in resolved]
    if not unresolved:
        return {"action":"STOP","reason":"ALL_MATERIAL_REQUIREMENTS_SUPPORTED"}

    target=unresolved[0]
    rid=str(target["id"])
    results=[x for x in public.get("search_results",[]) if isinstance(x,Mapping)]
    minimum=float((public.get("policy") or {}).get("minimum_authority",0.0))
    if results:
        admissible=[
            x for x in results
            if str(x.get("target_requirement_id") or "")==rid
            and float(x.get("authority",0.0))>=minimum
            and not any(
                r.get("source_id")==x.get("source_id")
                for r in public.get("evidence_receipts",[])
                if isinstance(r,Mapping)
            )
        ]
        if admissible:
            admissible.sort(key=lambda x:(-float(x.get("authority",0.0)),float(x.get("cost",0.0)),str(x.get("source_id") or "")))
            return {"action":"FETCH","source_id":str(admissible[0]["source_id"]),"target_requirement_id":rid}

    return {
        "action":"SEARCH",
        "target_requirement_id":rid,
        "query":str(target.get("text") or "").strip(),
    }
