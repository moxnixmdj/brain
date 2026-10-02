"""Information-safe bounded proof for ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001.

Candidate-visible state contains a normalized material requirement graph, public source
metadata, search/fetch receipts already earned, provenance, and remaining budget.
Hidden source contents, true requirement coverage, and ideal next actions remain in the
oracle. The environment exposes coverage only after candidate-chosen retrieval through
a deterministic extractor receipt, matching the frozen dependency boundary.

Preflight only. This does not grant terminal capability credit.
"""
from __future__ import annotations
from collections import defaultdict
import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_RESEARCH_CONTROL_INFORMATION_SAFE_PROOF_V1"
DOMAINS=("biology","finance","systems","law","energy","materials")


def generate_case(seed:int, ordinal:int)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool) or not isinstance(ordinal,int) or ordinal<0:
        raise ValueError("INPUT")
    r=random.Random((seed<<17)^ordinal^0x4D34)
    domain=DOMAINS[ordinal%len(DOMAINS)]
    n=3+(ordinal%3)
    reqs=[]
    sources=[]
    hidden={}
    for i in range(n):
        rid=f"R{i}"
        token=f"{domain}_{r.randrange(1000,9999)}_{i}"
        reqs.append({"id":rid,"text":f"Establish material finding {token}","material":True})
        opaque=[f"S-{rid}-{r.randrange(10000,99999)}" for _ in range(3)]
        first,second,low=opaque
        sources.extend([
            {"source_id":first,"authority":0.96,"cost":2.0,"available":True},
            {"source_id":second,"authority":0.93,"cost":1.5,"available":True},
            {"source_id":low,"authority":0.70,"cost":1.0,"available":True},
        ])
        first_supports=((seed+i+ordinal)%2==0)
        hidden[first]={"query_token":token,"supports":[rid] if first_supports else [],"content":f"Source material for {token}"}
        hidden[second]={"query_token":token,"supports":[] if first_supports else [rid],"content":f"Source material for {token}"}
        hidden[low]={"query_token":token,"supports":[rid],"content":f"Secondary source material for {token}"}
    r.shuffle(sources)
    budget=3*n+1
    return {
        "schema":SCHEMA,
        "behavior_id":"ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001",
        "case_id":f"RESEARCH-{seed}-{ordinal}",
        "objective":f"Resolve every material {domain} requirement with authoritative evidence.",
        "material_requirements":reqs,
        "source_catalog":sources,
        "policy":{
            "minimum_authority":0.90,
            "search_cost":1.0,
            "max_actions":budget,
            "stop_only_when_all_material_requirements_supported":True,
        },
        "_oracle":{"sources":hidden},
    }


def public_state(case:Mapping[str,Any], *, history=(), search_results=(), evidence_receipts=())->dict[str,Any]:
    resolved=sorted({
        str(rec["requirement_id"])
        for rec in evidence_receipts
        if rec.get("kind")=="EVIDENCE_RECEIPT"
        and rec.get("supported") is True
        and float(rec.get("authority",0.0))>=float(case["policy"]["minimum_authority"])
    })
    return {
        "schema":case["schema"],
        "behavior_id":case["behavior_id"],
        "case_id":case["case_id"],
        "objective":case["objective"],
        "material_requirements":[dict(x) for x in case["material_requirements"]],
        "resolved_requirement_ids":resolved,
        "source_catalog":[dict(x) for x in case["source_catalog"]],
        "search_results":[dict(x) for x in search_results],
        "evidence_receipts":[dict(x) for x in evidence_receipts],
        "history":[dict(x) for x in history],
        "policy":dict(case["policy"]),
    }


def _search(case:Mapping[str,Any], query:str, target_requirement_id:str)->list[dict[str,Any]]:
    q=" ".join(str(query).lower().split())
    hits=[]
    by_id={x["source_id"]:x for x in case["source_catalog"]}
    for sid,row in case["_oracle"]["sources"].items():
        token=row["query_token"].lower()
        if token in q:
            meta=by_id[sid]
            hits.append({
                "source_id":sid,
                "authority":float(meta["authority"]),
                "cost":float(meta["cost"]),
                "query":query,
                "target_requirement_id":target_requirement_id,
            })
    hits.sort(key=lambda x:(-x["authority"],x["cost"],x["source_id"]))
    return hits


def _fetch(case:Mapping[str,Any], source_id:str, target_requirement_id:str)->dict[str,Any]:
    meta=next((x for x in case["source_catalog"] if x["source_id"]==source_id),None)
    hidden=case["_oracle"]["sources"].get(source_id)
    if meta is None or hidden is None or meta.get("available") is not True:
        return {"kind":"FETCH_ERROR","source_id":source_id,"reason":"SOURCE_UNAVAILABLE"}
    supported=target_requirement_id in set(hidden["supports"])
    return {
        "kind":"EVIDENCE_RECEIPT",
        "source_id":source_id,
        "requirement_id":target_requirement_id,
        "supported":supported,
        "authority":float(meta["authority"]),
        "cost":float(meta["cost"]),
        "provenance":[source_id],
        "extractor":"DETERMINISTIC_EXACT_REQUIREMENT_SUPPORT",
    }


def run_episode(case:Mapping[str,Any], policy_fn)->dict[str,Any]:
    history=[]; results=[]; receipts=[]
    max_actions=int(case["policy"]["max_actions"])
    total_cost=0.0
    for step in range(max_actions+1):
        public=public_state(case,history=history,search_results=results,evidence_receipts=receipts)
        action=policy_fn(public)
        if not isinstance(action,Mapping):
            return {"pass":False,"reason":"ACTION_NOT_MAPPING"}
        kind=action.get("action")
        if kind=="STOP":
            required={x["id"] for x in case["material_requirements"]}
            resolved=set(public["resolved_requirement_ids"])
            if resolved!=required:
                return {"pass":False,"reason":"PREMATURE_STOP","resolved":sorted(resolved)}
            # Every material requirement must have an authoritative receipt.
            return {
                "pass":True,"reason":"PASS","actions":len(history),"total_cost":total_cost,
                "history":history,"terminal_authority":False,"capability_credit_delta":0,
            }
        if step>=max_actions:
            return {"pass":False,"reason":"ACTION_BUDGET_EXHAUSTED","history":history}
        if kind=="SEARCH":
            query=str(action.get("query") or "")
            rid=str(action.get("target_requirement_id") or "")
            unresolved={x["id"] for x in case["material_requirements"]}-set(public["resolved_requirement_ids"])
            if rid not in unresolved:
                return {"pass":False,"reason":"SEARCH_NOT_TARGETING_UNRESOLVED_REQUIREMENT","history":history}
            req=next(x for x in case["material_requirements"] if x["id"]==rid)
            # Query must preserve enough of the explicit requirement to be requirement-directed.
            key=req["text"].split()[-1].lower()
            if key not in query.lower():
                return {"pass":False,"reason":"QUERY_DRIFT","history":history}
            results=_search(case,query,rid)
            total_cost+=float(case["policy"]["search_cost"])
            history.append({"action":"SEARCH","target_requirement_id":rid,"query":query,"hit_count":len(results)})
            continue
        if kind=="FETCH":
            sid=str(action.get("source_id") or "")
            rid=str(action.get("target_requirement_id") or "")
            if not results or sid not in {x["source_id"] for x in results}:
                return {"pass":False,"reason":"FETCH_WITHOUT_CURRENT_SEARCH_HIT","history":history}
            if any(x.get("source_id")==sid for x in receipts):
                return {"pass":False,"reason":"REDUNDANT_REFETCH","history":history}
            rec=_fetch(case,sid,rid)
            receipts.append(rec)
            total_cost+=float(rec.get("cost",0.0))
            history.append({"action":"FETCH","source_id":sid,"target_requirement_id":rid,"supported":rec.get("supported")})
            # Keep the current result set so a failed fetch can recover to the
            # next candidate source without repeating the search.
            continue
        return {"pass":False,"reason":"UNKNOWN_ACTION","history":history}
    return {"pass":False,"reason":"UNREACHABLE"}


def run_batch(seed:int,case_count:int,policy_fn)->dict[str,Any]:
    rows=[]; by_domain=defaultdict(lambda:{"pass":0,"total":0})
    for ordinal in range(case_count):
        case=generate_case(seed,ordinal)
        try: verdict=run_episode(case,policy_fn)
        except Exception as exc:
            verdict={"pass":False,"reason":"CANDIDATE_EXCEPTION:"+type(exc).__name__+":"+str(exc)}
        domain=DOMAINS[ordinal%len(DOMAINS)]
        by_domain[domain]["total"]+=1
        by_domain[domain]["pass"]+=int(bool(verdict.get("pass")))
        rows.append({"case_id":case["case_id"],"pass":bool(verdict.get("pass")),"reason":verdict.get("reason")})
    passed=sum(int(x["pass"]) for x in rows)
    return {
        "schema":"PROJECT_BRAIN_RESEARCH_CONTROL_INFORMATION_SAFE_PREFLIGHT_RESULT_V1",
        "seed":seed,"case_count":case_count,"passed":passed,"failed":case_count-passed,
        "all_pass":passed==case_count,
        "by_domain":{k:dict(v) for k,v in sorted(by_domain.items())},
        "failures":[x for x in rows if not x["pass"]],
        "terminal_authority":False,"capability_credit_delta":0,
    }
