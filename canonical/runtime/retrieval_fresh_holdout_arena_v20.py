#!/usr/bin/env python3
"""Fresh live holdout for frozen V19 + V20 retrieval executor.

Critical sequencing:
1. load/validate the frozen request manifest and exact request bytes;
2. execute every network retrieval request without loading the answer key;
3. only after all retrieval calls finish, load the isolated answer key;
4. score immutable results.

The answer key therefore cannot influence query generation, provider selection,
route generation, or network control flow.
"""
from __future__ import annotations

import hashlib
import json
import statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import retrieval_verified_route_executor_v1 as executor

SCHEMA="PROJECT_BRAIN_RETRIEVAL_V20_FRESH_HOLDOUT_ARENA_V1"
MANIFEST="canonical/governance/RETRIEVAL_V20_FRESH_HOLDOUT_MANIFEST_V1.json"
ANSWER_KEY="canonical/governance/RETRIEVAL_V20_FRESH_HOLDOUT_ANSWER_KEY_V1.json"

def _blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _load_json(root:Path,rel:str)->dict[str,Any]:
    return json.loads((root/rel).read_text(encoding="utf-8"))

def _norm(x:Any)->str:
    return " ".join(str(x or "").strip().split()).casefold()

def _request_rows(root:Path,manifest:Mapping[str,Any])->list[dict[str,Any]]:
    rows=[]
    for item in manifest.get("requests") or []:
        rel=str(item["path"])
        raw=(root/rel).read_bytes()
        got=_blob(raw)
        if got!=item.get("git_blob_sha"):
            raise ValueError("HOLDOUT_REQUEST_BLOB_MISMATCH:"+str(item.get("episode_id")))
        row=json.loads(raw.decode("utf-8"))
        if row.get("episode_id")!=item.get("episode_id"):
            raise ValueError("HOLDOUT_EPISODE_ID_MISMATCH")
        if row.get("target_identity_present") is not False:
            raise ValueError("TARGET_IDENTITY_PRESENCE_FLAG_INVALID")
        qa=row.get("query_action") or {}
        if "target" in qa or "expected_target_answer_key" in qa:
            raise ValueError("ANSWER_KEY_FIELD_PRESENT_IN_REQUEST")
        rows.append(row)
    if len(rows)!=int(manifest.get("request_count") or 0):
        raise ValueError("HOLDOUT_REQUEST_COUNT_MISMATCH")
    return rows

def validate_freeze(root:Path)->dict[str,Any]:
    manifest=_load_json(root,MANIFEST)
    frozen=manifest.get("frozen_executor") or {}
    exec_path=str(frozen.get("path") or "")
    if _blob((root/exec_path).read_bytes())!=frozen.get("git_blob_sha"):
        raise ValueError("FROZEN_EXECUTOR_BLOB_MISMATCH")
    receipt=str(frozen.get("verification_path") or "")
    if _blob((root/receipt).read_bytes())!=frozen.get("verification_git_blob_sha"):
        raise ValueError("FROZEN_EXECUTOR_VERIFICATION_BLOB_MISMATCH")
    rows=_request_rows(root,manifest)
    return {"manifest":manifest,"requests":rows}

def _execute_group(root:Path,rows:list[Mapping[str,Any]],timeout:float)->list[dict[str,Any]]:
    out=[]
    for row in rows:
        result=executor.execute_request(
            root=root,
            query_action=row["query_action"],
            source=row["source"],
            timeout=timeout,
        )
        out.append({
            "episode_id":row["episode_id"],
            "difficulty":row["difficulty"],
            "provider":row["source"].get("provider"),
            "source_id":row["source"].get("source_id"),
            "query":row["query_action"].get("query"),
            "retrieval":result,
        })
    return out

def execute_all_requests(root:Path,rows:list[Mapping[str,Any]],*,timeout:float=20.0)->list[dict[str,Any]]:
    grouped=defaultdict(list)
    for row in rows:
        grouped[str((row.get("source") or {}).get("provider") or "UNKNOWN")].append(row)
    events=[]
    with ThreadPoolExecutor(max_workers=max(1,min(8,len(grouped)))) as pool:
        futs=[
            pool.submit(_execute_group,root,group,timeout)
            for _,group in sorted(grouped.items())
        ]
        for fut in as_completed(futs):
            events.extend(fut.result())
    order={str(row["episode_id"]):i for i,row in enumerate(rows)}
    events.sort(key=lambda x:order[x["episode_id"]])
    return events

def _validate_no_target_leak(rows:list[Mapping[str,Any]],targets:Mapping[str,Any])->None:
    by_id={str(x["episode_id"]):x for x in rows}
    if set(by_id)!=set(targets):
        raise ValueError("ANSWER_KEY_EPISODE_SET_MISMATCH")
    for eid,target_raw in targets.items():
        target=_norm(target_raw)
        basename=target.rsplit("/",1)[-1].rsplit(":",1)[-1]
        row=by_id[eid]
        qa=row["query_action"]
        texts=[str(qa.get("query") or "")]
        for key in ("language_variants","bridge_variants"):
            for item in qa.get(key) or []:
                texts.append(str(item.get("text") if isinstance(item,Mapping) else item))
        hay=_norm(" ".join(texts))
        if target and target in hay:
            raise ValueError("TARGET_IDENTITY_LEAKED_IN_REQUEST:"+eid)
        if len(basename)>=4 and basename in hay:
            raise ValueError("TARGET_BASENAME_LEAKED_IN_REQUEST:"+eid)

def score(events:list[Mapping[str,Any]],targets:Mapping[str,Any])->dict[str,Any]:
    scored=[]
    for event in events:
        eid=str(event["episode_id"])
        target=_norm(targets[eid])
        retrieval=event["retrieval"]
        candidates=[_norm(x) for x in retrieval.get("candidate_ids") or [] if _norm(x)]
        hit=target in candidates
        rank=candidates.index(target)+1 if hit else None

        first_action=None
        cumulative=0.0
        usable=False
        for idx,route in enumerate(retrieval.get("events") or [],1):
            cumulative+=float(route.get("latency_seconds") or 0.0)
            if route.get("status")=="SUCCESS":
                usable=True
            route_ids={_norm(x) for x in route.get("candidate_ids") or [] if _norm(x)}
            if first_action is None and target in route_ids:
                first_action={
                    "action_index":idx,
                    "action_id":route.get("action_id"),
                    "strategy_id":route.get("strategy_id"),
                    "cumulative_measured_route_latency_seconds":cumulative,
                }

        scored.append({
            "episode_id":eid,
            "difficulty":event["difficulty"],
            "provider":event["provider"],
            "target_hit":hit,
            "target_rank_in_union":rank,
            "transport_usable":usable,
            "candidate_count":len(candidates),
            "planned_action_count":retrieval.get("planned_action_count"),
            "first_hit":first_action,
            "retrieval_status":retrieval.get("status"),
        })

    usable=[x for x in scored if x["transport_usable"]]
    hits=[x for x in usable if x["target_hit"]]
    misses=[x for x in usable if not x["target_hit"]]
    failures=[x for x in scored if not x["transport_usable"]]

    def metrics(key:str)->dict[str,Any]:
        out={}
        for value in sorted({str(x[key]) for x in scored}):
            rr=[x for x in scored if str(x[key])==value]
            uu=[x for x in rr if x["transport_usable"]]
            hh=[x for x in uu if x["target_hit"]]
            out[value]={
                "case_count":len(rr),
                "usable_case_count":len(uu),
                "hit_count":len(hh),
                "recall_on_usable_cases":len(hh)/len(uu) if uu else None,
            }
        return out

    first_actions=[x["first_hit"]["action_index"] for x in hits if x["first_hit"]]
    first_lat=[x["first_hit"]["cumulative_measured_route_latency_seconds"] for x in hits if x["first_hit"]]
    return {
        "case_count":len(scored),
        "usable_case_count":len(usable),
        "failed_retryable_case_count":len(failures),
        "hit_count":len(hits),
        "miss_count":len(misses),
        "portfolio_union_recall_on_usable_cases":len(hits)/len(usable) if usable else None,
        "miss_episode_ids":[x["episode_id"] for x in misses],
        "failed_episode_ids":[x["episode_id"] for x in failures],
        "mean_first_hit_action_index":statistics.mean(first_actions) if first_actions else None,
        "mean_first_hit_measured_route_latency_seconds":statistics.mean(first_lat) if first_lat else None,
        "difficulty_metrics":metrics("difficulty"),
        "provider_metrics":metrics("provider"),
        "cases":scored,
    }

def run(*,root:Path|None=None,timeout:float=20.0)->dict[str,Any]:
    root=root or Path(__file__).resolve().parents[2]
    frozen=validate_freeze(root)

    # CRITICAL: all live retrieval finishes before the answer key is loaded.
    events=execute_all_requests(root,frozen["requests"],timeout=timeout)

    answer=_load_json(root,ANSWER_KEY)
    targets=answer.get("targets") or {}
    _validate_no_target_leak(frozen["requests"],targets)
    scored=score(events,targets)

    return {
        "schema":SCHEMA,
        "status":"FRESH_HOLDOUT_MEASUREMENT_COMPLETE",
        "executor_git_blob_sha":frozen["manifest"]["frozen_executor"]["git_blob_sha"],
        "answer_key_loaded_only_after_all_retrieval_execution":True,
        "answer_key_identity_used_for_query_generation":False,
        "answer_key_identity_used_for_route_generation":False,
        "answer_key_identity_used_for_provider_selection":False,
        "measurement":scored,
        "raw_events":events,
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "THIS_IS_THE_FIRST_FROZEN_V20_HOLDOUT_RESULT",
            "NO_POST_HOC_ROUTE_CHANGE_MAY_RECLASSIFY_THIS_RESULT",
            "MISSES_ARE_PERMANENT_GENERALIZATION_EVIDENCE",
            "TRANSPORT_FAILURES_ARE_EXCLUDED_FROM_RECALL_DENOMINATOR_AND_REMAIN_RETRYABLE",
            "FINITE_HOLDOUT_RECALL_IS_NOT_OPEN_WORLD_COMPLETENESS"
        ],
    }

def main()->int:
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["measurement"]["usable_case_count"]>0 else 1

if __name__=="__main__":
    raise SystemExit(main())
