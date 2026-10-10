"""R2 direct adequacy for provenance-bearing knowledge consistency assessment.

Bounded family only:
- one repository-local request manifest listing knowledge evidence artifacts;
- each evidence artifact must satisfy PROJECT_BRAIN_KNOWLEDGE_EVIDENCE_V1;
- producer is the already-verified runtime-native knowledge.consistency.assess
  action implemented by astra_runtime;
- independent acceptance recomputes evidence validity, canonical values,
  canonical source identities, freshness, counts, and terminal status.

Valid assessment outcomes are SUPPORTED, CONFLICTED, STALE, and INSUFFICIENT.
SUPPORTED here means agreement among at least two distinct URL+JSON-path source
identities under the bounded contract. It does not prove organizational
independence, source authority, factual truth, causality, or completeness.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

from canonical.runtime import astra_runtime
from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA="PROJECT_BRAIN_R2_KNOWLEDGE_CONSISTENCY_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::PROVENANCE_KNOWLEDGE_CONSISTENCY_FAMILY_V1"
CAPABILITY_ID="knowledge.consistency.assess"
ROOT=Path(__file__).resolve().parents[2]
_PATH=r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR=re.compile(
    r"^Assess knowledge consistency using manifest (?P<manifest>"+_PATH+r"\.json) "
    r"and save the verified assessment to (?P<output>"+_PATH+r"\.json)\.?$",
    re.IGNORECASE,
)
TERMINAL={"SUPPORTED","CONFLICTED","STALE","INSUFFICIENT"}


def _base(status:str, passed:bool=False)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,"pass":passed,"matched":False,
        "semantic_acceptance_complete":False,
        "actual_goal_satisfaction_verified":False,
        "direct_adequacy_authority":False,"execution_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _inside(root:Path, rel:str)->Path:
    rr=root.resolve(); p=(rr/str(rel)).resolve()
    if p==rr or rr not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _sha(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def _source_identity(url:str,json_path:Any)->str:
    raw=str(url or "")
    try:
        parsed=urlsplit(raw)
        scheme=parsed.scheme.lower()
        host=(parsed.hostname or "").lower()
        port=parsed.port
        netloc=host
        if port is not None and not (
            (scheme=="http" and port==80) or (scheme=="https" and port==443)
        ):
            netloc=f"{host}:{port}"
        canonical=urlunsplit((scheme,netloc,parsed.path or "/",parsed.query,""))
    except Exception:
        canonical=raw
    path_spec=json_path if isinstance(json_path,list) else []
    return sha256(
        json.dumps(
            {"url":canonical,"json_path":path_spec},
            sort_keys=True,separators=(",",":"),ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _parse_manifest(value:Any)->dict[str,Any]:
    if not isinstance(value,Mapping):
        raise ValueError("MANIFEST_NOT_OBJECT")
    if value.get("schema")!="PROJECT_BRAIN_KNOWLEDGE_CONSISTENCY_REQUEST_V1":
        raise ValueError("MANIFEST_SCHEMA_INVALID")
    paths=value.get("evidence_paths")
    if (
        not isinstance(paths,list) or not paths or len(paths)>32
        or any(not isinstance(x,str) or not x.strip() for x in paths)
    ):
        raise ValueError("EVIDENCE_PATHS_INVALID")
    if len(set(paths))!=len(paths):
        raise ValueError("EVIDENCE_PATHS_DUPLICATE")
    max_age=value.get("max_age_s")
    if max_age is not None:
        if isinstance(max_age,bool):
            raise ValueError("MAX_AGE_INVALID")
        try: max_age=float(max_age)
        except Exception as exc: raise ValueError("MAX_AGE_INVALID") from exc
        if not (0.0 < max_age <= 315_576_000.0):
            raise ValueError("MAX_AGE_OUT_OF_RANGE")
    return {"evidence_paths":list(paths),"max_age_s":max_age}


def _validate_record(item:Any,path:str,reference:datetime,max_age_s:float|None)->dict[str,Any]:
    if not isinstance(item,Mapping) or item.get("schema")!="PROJECT_BRAIN_KNOWLEDGE_EVIDENCE_V1":
        raise ValueError("EVIDENCE_SCHEMA_INVALID:"+path)
    source_url=str(item.get("source_url") or "")
    final_url=str(item.get("final_url") or source_url)
    json_path=item.get("json_path") if isinstance(item.get("json_path"),list) else None
    body_sha=str(item.get("body_sha256") or "").lower()
    source_type=str(item.get("source_type") or "")
    status=item.get("http_status")
    if (
        not source_url.startswith(("https://","http://"))
        or not final_url.startswith(("https://","http://"))
        or json_path is None
        or not re.fullmatch(r"[0-9a-f]{64}",body_sha)
        or source_type not in {"external_json","authoritative_external_json"}
        or not isinstance(status,int) or isinstance(status,bool)
        or not (200<=status<300)
    ):
        raise ValueError("EVIDENCE_CONTRACT_INVALID:"+path)
    retrieved=str(item.get("retrieved_at_utc") or "")
    try:
        ts=datetime.fromisoformat(retrieved.replace("Z","+00:00"))
        if ts.tzinfo is None:
            raise ValueError("naive")
        ts=ts.astimezone(timezone.utc)
    except Exception as exc:
        raise ValueError("EVIDENCE_TIMESTAMP_INVALID:"+path) from exc
    age=max(0.0,(reference-ts).total_seconds())
    stale=False
    if max_age_s is not None:
        if abs(age-max_age_s)<2.0:
            raise ValueError("FRESHNESS_BOUNDARY_TOO_CLOSE_FOR_INDEPENDENT_REPLAY:"+path)
        stale=age>max_age_s
    return {
        "path":path,"source_url":source_url,"final_url":final_url,
        "source_type":source_type,"json_path":json_path,
        "source_identity":_source_identity(final_url,json_path),
        "retrieved_at_utc":retrieved,"value":item.get("value"),
        "body_sha256":body_sha,"stale":stale,"age_s":age,
    }


def _recompute(
    root:Path, evidence_paths:list[str], max_age_s:float|None, reference:datetime
)->dict[str,Any]:
    records=[]
    for rel in evidence_paths:
        p=_inside(root,rel)
        if not p.is_file():
            raise ValueError("EVIDENCE_MISSING:"+rel)
        try: item=json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc: raise ValueError("EVIDENCE_JSON_INVALID:"+rel) from exc
        records.append(_validate_record(item,rel,reference,max_age_s))
    fresh=[x for x in records if not x["stale"]]
    canonical={}
    for rec in fresh:
        key=json.dumps(rec["value"],sort_keys=True,separators=(",",":"),ensure_ascii=False)
        canonical.setdefault(key,[]).append(rec["path"])
    identities={x["source_identity"] for x in fresh}
    if records and not fresh:
        status="STALE"
    elif len(fresh)<2:
        status="INSUFFICIENT"
    elif len(canonical)>1:
        status="CONFLICTED"
    elif len(identities)<2:
        status="INSUFFICIENT"
    else:
        status="SUPPORTED"
    return {
        "status":status,"evidence_count":len(records),"fresh_evidence_count":len(fresh),
        "distinct_fresh_values":len(canonical),
        "distinct_fresh_source_identities":len(identities),
        "records":records,
    }


def _raw_contract(goal:str)->dict[str,Any]:
    contract=compile_contract(
        goal,source_id="user",routing_target_effects=["knowledge.consistency.assess"]
    )
    if contract.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    ids=list((contract.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
    if not ids:
        raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
    return contract


def preflight(request:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request,Mapping):
        return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
    task_id=str(request.get("task_id") or "").strip()
    goal=str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
    match=GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"),"matched":False}
    try:
        manifest_rel=match.group("manifest"); output_rel=match.group("output")
        manifest_path=_inside(root,manifest_rel); output_path=_inside(root,output_rel)
        if manifest_path==output_path:
            raise ValueError("MANIFEST_OUTPUT_COLLISION")
        if not manifest_path.is_file():
            raise ValueError("MANIFEST_MISSING")
        spec=_parse_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
        evidence_shas={}
        for rel in spec["evidence_paths"]:
            p=_inside(root,rel)
            if not p.is_file():
                raise ValueError("EVIDENCE_MISSING:"+rel)
            evidence_shas[rel]=_sha(p)
            # Contract validation now; freshness is re-evaluated during run.
            item=json.loads(p.read_text(encoding="utf-8"))
            _validate_record(item,rel,datetime.now(timezone.utc),None)

        registry=live_bound.load_verified_registry()
        entry=registry.get(CAPABILITY_ID)
        if not isinstance(entry,Mapping) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            raise ValueError("KNOWLEDGE_CONSISTENCY_VERIFIED_CAPABILITY_REQUIRED")
        if str(entry.get("adapter") or entry.get("adapter_module") or "") not in {
            "runtime_native_action",""
        }:
            raise ValueError("KNOWLEDGE_CONSISTENCY_ADAPTER_MISMATCH")
        ver=entry.get("verification")
        if not isinstance(ver,Mapping):
            raise ValueError("KNOWLEDGE_CONSISTENCY_VERIFICATION_REQUIRED")

        contract=_raw_contract(goal)
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),"matched":True,"route_id":ROUTE_ID,
            "task_id":task_id,"goal":goal,
            "goal_sha256":sha256(goal.encode("utf-8")).hexdigest(),
            "policy_id":goal_scoped_policy_id(CAPABILITY_ID,goal),
            "capability_id":CAPABILITY_ID,
            "manifest_path":manifest_rel,"manifest_sha256":_sha(manifest_path),
            "evidence_paths":spec["evidence_paths"],"evidence_sha256":evidence_shas,
            "max_age_s":spec["max_age_s"],"output_path":output_rel,
            "raw_acceptance_obligation_ids":list(contract["acceptance_contract"]["required_obligation_ids"]),
            "semantic_scope":"PROVENANCE_BEARING_EXTERNAL_JSON_VALUE_CONSISTENCY_OVER_DISTINCT_URL_AND_JSON_PATH_IDENTITIES",
            "preflight_execution_authority":False,
        }
    except Exception as exc:
        return {**_base("FAIL_CLOSED"),"matched":True,"route_id":ROUTE_ID,
                "reason":type(exc).__name__+":"+str(exc)}


def _restore(path:Path,existed:bool,original:bytes|None)->None:
    if existed:
        path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(original or b"")
    elif path.exists():
        path.unlink()


def run(request:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    pf=preflight(request,repo_root=root)
    if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED":
        return pf
    manifest_path=_inside(root,pf["manifest_path"])
    output_path=_inside(root,pf["output_path"])
    existed=output_path.is_file(); original=output_path.read_bytes() if existed else None
    try:
        if _sha(manifest_path)!=pf["manifest_sha256"]:
            raise RuntimeError("MANIFEST_DRIFT_BEFORE_EXECUTION")
        for rel,expected in pf["evidence_sha256"].items():
            if _sha(_inside(root,rel))!=expected:
                raise RuntimeError("EVIDENCE_DRIFT_BEFORE_EXECUTION:"+rel)

        producer=astra_runtime._goal_action({
            "type":"assess_knowledge_consistency",
            "args":{
                "evidence_paths":pf["evidence_paths"],
                "output_path":pf["output_path"],
                **({"max_age_s":pf["max_age_s"]} if pf["max_age_s"] is not None else {}),
            },
        })
        if (
            not isinstance(producer,Mapping)
            or producer.get("verified") is not True
            or producer.get("status") not in TERMINAL
            or producer.get("output_path")!=pf["output_path"]
        ):
            raise RuntimeError("KNOWLEDGE_CONSISTENCY_PRODUCER_FAILED:"+str(producer))
        if not output_path.is_file():
            raise RuntimeError("ASSESSMENT_OUTPUT_MISSING")
        assessment=json.loads(output_path.read_text(encoding="utf-8"))
        if assessment.get("schema")!="PROJECT_BRAIN_KNOWLEDGE_ASSESSMENT_V1":
            raise RuntimeError("ASSESSMENT_SCHEMA_INVALID")
        if assessment.get("status") not in TERMINAL:
            raise RuntimeError("ASSESSMENT_STATUS_INVALID")
        assessed=str(assessment.get("assessed_at_utc") or "")
        try:
            reference=datetime.fromisoformat(assessed.replace("Z","+00:00"))
            if reference.tzinfo is None: raise ValueError("naive")
            reference=reference.astimezone(timezone.utc)
        except Exception as exc:
            raise RuntimeError("ASSESSMENT_TIMESTAMP_INVALID") from exc

        independent=_recompute(root,pf["evidence_paths"],pf["max_age_s"],reference)
        for field in (
            "status","evidence_count","fresh_evidence_count",
            "distinct_fresh_values","distinct_fresh_source_identities",
        ):
            if assessment.get(field)!=independent[field]:
                raise RuntimeError("INDEPENDENT_ASSESSMENT_MISMATCH:"+field)
        observed_records=assessment.get("records")
        if not isinstance(observed_records,list) or len(observed_records)!=len(independent["records"]):
            raise RuntimeError("ASSESSMENT_RECORD_COUNT_MISMATCH")
        obs_by={str(x.get("path") or ""):x for x in observed_records if isinstance(x,Mapping)}
        if set(obs_by)!=set(pf["evidence_paths"]):
            raise RuntimeError("ASSESSMENT_RECORD_PATH_SET_MISMATCH")
        for rec in independent["records"]:
            obs=obs_by[rec["path"]]
            for field in (
                "source_url","final_url","source_type","json_path","source_identity",
                "retrieved_at_utc","value","body_sha256","stale",
            ):
                if obs.get(field)!=rec[field]:
                    raise RuntimeError("ASSESSMENT_RECORD_FIELD_MISMATCH:"+rec["path"]+":"+field)

        if _sha(manifest_path)!=pf["manifest_sha256"]:
            raise RuntimeError("MANIFEST_MUTATED_BY_PRODUCER")
        for rel,expected in pf["evidence_sha256"].items():
            if _sha(_inside(root,rel))!=expected:
                raise RuntimeError("EVIDENCE_MUTATED_BY_PRODUCER:"+rel)

        contract=_raw_contract(str(request["goal"]))
        accepted=list(contract["acceptance_contract"]["required_obligation_ids"])
        if accepted!=pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")

        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),
            "matched":True,"route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,
            "selected_policy_id":pf["policy_id"],"goal_sha256":pf["goal_sha256"],
            "manifest_path":pf["manifest_path"],"manifest_sha256":pf["manifest_sha256"],
            "evidence_paths":pf["evidence_paths"],"evidence_sha256":pf["evidence_sha256"],
            "max_age_s":pf["max_age_s"],"assessment_status":independent["status"],
            "evidence_count":independent["evidence_count"],
            "fresh_evidence_count":independent["fresh_evidence_count"],
            "distinct_fresh_values":independent["distinct_fresh_values"],
            "distinct_fresh_source_identities":independent["distinct_fresh_source_identities"],
            "output_path":pf["output_path"],"output_sha256":_sha(output_path),
            "semantic_scope":pf["semantic_scope"],"semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,"direct_adequacy_authority":True,
            "accepted_raw_obligation_ids":accepted,"raw_acceptance_obligation_count":len(accepted),
            "producer_result":dict(producer),
            "acceptance_receipt":{
                "verified":True,"producer_independent":True,
                "verifier":"independent_contract_source_identity_value_freshness_status_recomputation",
                "assessment_status":independent["status"],
                "distinct_fresh_values":independent["distinct_fresh_values"],
                "distinct_fresh_source_identities":independent["distinct_fresh_source_identities"],
                "inputs_immutable":True,
            },
            "execution_attempted":True,"retry_by_other_route_authorized":False,
            "transaction_committed":True,"transaction_rolled_back":False,
            "authority_boundary":(
                "KNOWLEDGE_CONSISTENCY_OVER_PROJECT_BRAIN_KNOWLEDGE_EVIDENCE_V1_ONLY;"
                "SUPPORTED_REQUIRES_AT_LEAST_TWO_FRESH_DISTINCT_URL_PLUS_JSON_PATH_IDENTITIES_WITH_ONE_CANONICAL_VALUE;"
                "CONFLICTED_STALE_AND_INSUFFICIENT_ARE_VALID_ASSESSMENT_OUTCOMES;"
                "NO_ORGANIZATIONAL_INDEPENDENCE_SOURCE_AUTHORITY_FACTUAL_TRUTH_CAUSALITY_OR_COMPLETENESS_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(output_path,existed,original)
        return {**_base("FAIL_CLOSED"),"matched":True,"route_id":ROUTE_ID,
                "capability_id":CAPABILITY_ID,"policy_id":pf.get("policy_id"),
                "goal_sha256":pf.get("goal_sha256"),"reason":type(exc).__name__+":"+str(exc),
                "execution_attempted":True,"retry_by_other_route_authorized":False,
                "transaction_rolled_back":True}
