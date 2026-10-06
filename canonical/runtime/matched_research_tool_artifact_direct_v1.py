from __future__ import annotations

import hashlib
import json
import pathlib
import tempfile
from typing import Any, Mapping

from canonical.runtime import research_control_information_safe_candidate as candidate
from canonical.runtime import research_control_information_safe_proof as proof
from canonical.runtime.exact_artifact_materializer import materialize_exact_artifact

SCHEMA="PROJECT_BRAIN_MATCHED_RESEARCH_TOOL_ARTIFACT_DIRECT_V1"

def canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def sha(v:Any)->str:
    return hashlib.sha256(canon(v)).hexdigest()

def _supported_fetches(history):
    return [
        {
            "source_id":str(x.get("source_id") or ""),
            "target_requirement_id":str(x.get("target_requirement_id") or ""),
            "supported":x.get("supported") is True,
        }
        for x in history
        if isinstance(x,Mapping) and x.get("action")=="FETCH"
    ]

def execute_case(seed:int,ordinal:int)->dict[str,Any]:
    case=proof.generate_case(seed,ordinal)
    research=proof.run_episode(case,candidate.next_action)
    history=[dict(x) for x in research.get("history") or []]
    supported=_supported_fetches(history)
    required=sorted(str(x["id"]) for x in case["material_requirements"])
    resolved=sorted({x["target_requirement_id"] for x in supported if x["supported"]})
    research_ok=research.get("pass") is True and resolved==required

    research_binding={
        "case_id":case["case_id"],
        "objective":case["objective"],
        "required_requirement_ids":required,
        "resolved_requirement_ids":resolved,
        "research_history":history,
        "research_history_sha256":sha(history),
    }
    payload=canon({
        "schema":"PROJECT_BRAIN_RESEARCH_BOUND_ARTIFACT_V1",
        "case_id":case["case_id"],
        "objective":case["objective"],
        "resolved_requirement_ids":resolved,
        "research_history_sha256":research_binding["research_history_sha256"],
        "evidence_source_ids":sorted({x["source_id"] for x in supported if x["supported"]}),
    })
    payload_sha=hashlib.sha256(payload).hexdigest()

    with tempfile.TemporaryDirectory() as td:
        path=pathlib.Path(td)/"research-artifact.json"
        mat=materialize_exact_artifact(
            path,
            target_bytes=payload,
            expected_target_sha256=payload_sha,
        )
        materializer_ok=(
            mat.get("status")=="PASS"
            and path.is_file()
            and path.read_bytes()==payload
            and hashlib.sha256(path.read_bytes()).hexdigest()==payload_sha
        )

    passed=research_ok and materializer_ok
    research_event_id="research:"+research_binding["research_history_sha256"][:16]
    tool_event_id="materializer:"+payload_sha[:16]
    trace={
        "trace_source":"HARNESS_OBJECTIVE",
        "events":[
            {
                "seq":0,"type":"RESEARCH_RESULT","source":"HARNESS",
                "event_id":research_event_id,
                "case_id":case["case_id"],
                "resolved_requirement_ids":resolved,
                "research_history_sha256":research_binding["research_history_sha256"],
                "research_scorer_pass":research.get("pass") is True,
            },
            {
                "seq":1,"type":"TOOL_RESULT","source":"HARNESS",
                "event_id":tool_event_id,
                "tool_id":"exact_artifact_materializer",
                "ok":materializer_ok,
                "artifact_sha256":payload_sha,
            },
            {
                "seq":2,"type":"ARTIFACT_CREATED","source":"HARNESS",
                "artifact_sha256":payload_sha,
                "source_event_ids":[research_event_id,tool_event_id],
                "content_binds_research_history_sha256":research_binding["research_history_sha256"],
            },
            {"seq":3,"type":"TERMINAL","source":"HARNESS","success":passed},
        ],
    }
    return {
        "schema":SCHEMA+"_RESULT",
        "case_id":case["case_id"],
        "domain":proof.DOMAINS[ordinal%len(proof.DOMAINS)],
        "pass":passed,
        "research_scorer_pass":research.get("pass") is True,
        "required_requirement_count":len(required),
        "resolved_requirement_count":len(resolved),
        "research_history_sha256":research_binding["research_history_sha256"],
        "artifact_sha256":payload_sha,
        "artifact_bytes":len(payload),
        "materializer_pass":materializer_ok,
        "artifact_payload":json.loads(payload),
        "objective_trace":trace,
        "terminal_authority":False,
        "fresh_reality_authority":False,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }

def causal_ablation(seed:int,ordinal:int)->dict[str,Any]:
    full=execute_case(seed,ordinal)
    doc=dict(full["artifact_payload"])
    original=doc["research_history_sha256"]
    doc["research_history_sha256"]="0"*64
    ablated=canon(doc)
    ablated_sha=hashlib.sha256(ablated).hexdigest()
    return {
        "full_pass":full["pass"],
        "full_artifact_sha256":full["artifact_sha256"],
        "ablated_artifact_sha256":ablated_sha,
        "hash_changed":ablated_sha!=full["artifact_sha256"],
        "research_binding_removed":original!="0"*64,
        "terminal_credit_delta":0,
    }

def run_batch(seed:int,count:int=12)->dict[str,Any]:
    rows=[]
    for i in range(count):
        try:
            row=execute_case(seed+i*104729,i)
        except Exception as exc:
            row={"case_id":f"ERR-{i}","pass":False,"error":type(exc).__name__+":"+str(exc)}
        rows.append(row)
    passed=sum(int(x.get("pass") is True) for x in rows)
    return {
        "schema":SCHEMA+"_BATCH_RESULT",
        "case_count":count,
        "passed":passed,
        "failed":count-passed,
        "all_pass":passed==count,
        "domains":sorted({x.get("domain") for x in rows if x.get("domain")}),
        "failures":[x for x in rows if x.get("pass") is not True][:20],
        "terminal_authority":False,
        "fresh_reality_authority":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run_batch(20261007,12),indent=2,sort_keys=True))
