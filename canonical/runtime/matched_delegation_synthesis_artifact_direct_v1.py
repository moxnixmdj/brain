from __future__ import annotations

import hashlib
import json
import pathlib
import tempfile
from typing import Any, Mapping

from canonical.runtime import delegation_receipt_history_candidate_v3 as delegation_candidate
from canonical.runtime import delegation_structural_variety_proof_v3 as delegation_proof
from canonical.runtime import contract_native_brain_candidate as synthesis_candidate
from canonical.runtime import contract_native_proof_suites as synthesis_proof
from canonical.runtime.exact_artifact_materializer import materialize_exact_artifact

SCHEMA="PROJECT_BRAIN_MATCHED_DELEGATION_SYNTHESIS_ARTIFACT_DIRECT_V1"
SYNTHESIS_CONTRACT="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"

def canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def sha(v:Any)->str:
    return hashlib.sha256(canon(v)).hexdigest()

def _delegation(seed:int,ordinal:int)->tuple[dict[str,Any],dict[str,Any]]:
    # DUAL_ROOT_FANIN is class index 3. Preserve structural variety while forcing
    # at least two concurrently ready roots that must be assigned to distinct workers.
    case=delegation_proof.generate_case(seed,3 + 5*ordinal)
    public=delegation_proof.public_case(case)
    plan=delegation_candidate.solve_initial(public)
    verdict=delegation_proof.score_case(case,plan)
    if verdict.get("pass") is not True:
        raise RuntimeError("DELEGATION_PLAN_FAILED:"+str(verdict.get("reason")))
    return case,plan

def _evidence_records(case:Mapping[str,Any],plan:Mapping[str,Any])->list[dict[str,Any]]:
    steps={str(x["id"]):x for x in case["task"]["steps"]}
    rows=[]
    for sid in plan["task_ids"]:
        worker=str(plan["assignment"][sid])
        for eid in steps[sid].get("evidence_outputs") or []:
            rows.append({
                "evidence_id":str(eid),
                "worker_id":worker,
                "task_id":str(sid),
                "payload_sha256":sha({"worker_id":worker,"task_id":sid,"evidence_id":eid}),
            })
    rows.sort(key=lambda x:(x["task_id"],x["evidence_id"]))
    if len({x["worker_id"] for x in rows})<2:
        raise RuntimeError("MULTI_WORKER_EVIDENCE_NOT_ESTABLISHED")
    return rows

def _synthesis_case(evidence:list[dict[str,Any]], *, drop_evidence_id:str|None=None)->dict[str,Any]:
    all_ids=[x["evidence_id"] for x in evidence]
    visible=[x for x in evidence if x["evidence_id"]!=drop_evidence_id]
    task_evidence=[
        {
            "claim_id":x["evidence_id"],
            "role":"required",
            "support":"supported",
            "provenance":[x["worker_id"],x["task_id"],x["payload_sha256"]],
            "audience":"operator",
        }
        for x in visible
    ]
    return {
        "schema":"PROJECT_BRAIN_CONTRACT_NATIVE_PROOF_SUITE_V1",
        "contract":SYNTHESIS_CONTRACT,
        "seed":0,
        "task":{
            "audience":"operator",
            "evidence":task_evidence,
            "format_constraints":{"max_claims":len(all_ids),"ordered_required_first":True},
        },
        "_oracle":{
            "required":sorted(all_ids),
            "allowed_optional":[],
            "forbidden":[],
            "uncertainty":[],
        },
    }

def _run_synthesis(case:Mapping[str,Any])->tuple[dict[str,Any],dict[str,Any]]:
    public=synthesis_proof.public_task(case)
    out=synthesis_candidate.solve_synthesis(public)
    verdict=synthesis_proof.score_case(case,out)
    return out,verdict

def execute_case(seed:int,ordinal:int)->dict[str,Any]:
    dcase,plan=_delegation(seed,ordinal)
    evidence=_evidence_records(dcase,plan)
    scase=_synthesis_case(evidence)
    synthesis,sv=_run_synthesis(scase)
    synthesis_ok=sv.get("pass") is True
    selected=sorted(str(x) for x in synthesis.get("selected_claims") or [])
    expected=sorted(x["evidence_id"] for x in evidence)
    provenance={
        x["evidence_id"]:{
            "worker_id":x["worker_id"],
            "task_id":x["task_id"],
            "payload_sha256":x["payload_sha256"],
        }
        for x in evidence
    }
    artifact_doc={
        "schema":"PROJECT_BRAIN_DELEGATED_SYNTHESIS_ARTIFACT_V1",
        "delegation_case_id":dcase["case_id"],
        "selected_claims":selected,
        "delegated_evidence":provenance,
        "synthesis_sha256":sha(synthesis),
        "delegation_plan_sha256":sha({
            "assignment":plan["assignment"],
            "waves":plan["waves"],
            "terminal_evidence":plan["terminal_evidence"],
        }),
    }
    payload=canon(artifact_doc)
    payload_sha=hashlib.sha256(payload).hexdigest()
    with tempfile.TemporaryDirectory() as td:
        target=pathlib.Path(td)/"delegated-synthesis.json"
        mat=materialize_exact_artifact(
            target,target_bytes=payload,expected_target_sha256=payload_sha
        )
        artifact_ok=(
            mat.get("status")=="PASS"
            and target.is_file()
            and target.read_bytes()==payload
            and hashlib.sha256(target.read_bytes()).hexdigest()==payload_sha
        )

    full_ok=(
        synthesis_ok
        and selected==expected
        and artifact_ok
        and len({x["worker_id"] for x in evidence})>=2
    )
    workers=sorted({x["worker_id"] for x in evidence})
    events=[]
    seq=0
    for worker in workers:
        events.append({"seq":seq,"type":"DELEGATE","source":"HARNESS","worker_id":worker})
        seq+=1
    for row in evidence:
        events.append({
            "seq":seq,"type":"EVIDENCE_RECEIVED","source":"HARNESS",
            "worker_id":row["worker_id"],"evidence_id":row["evidence_id"],
            "task_id":row["task_id"],"payload_sha256":row["payload_sha256"],
        })
        seq+=1
    synthesis_id="synthesis:"+sha(synthesis)[:16]
    events.append({
        "seq":seq,"type":"SYNTHESIS","source":"HARNESS",
        "synthesis_id":synthesis_id,"evidence_ids":selected,
        "synthesis_scorer_pass":synthesis_ok,
    }); seq+=1
    events.append({
        "seq":seq,"type":"ARTIFACT_CREATED","source":"HARNESS",
        "synthesis_id":synthesis_id,"artifact_sha256":payload_sha,
        "artifact_binds_evidence_ids":expected,
    }); seq+=1
    events.append({"seq":seq,"type":"TERMINAL","source":"HARNESS","success":full_ok})

    missing_id=expected[0]
    ablated_case=_synthesis_case(evidence,drop_evidence_id=missing_id)
    _,ablated_verdict=_run_synthesis(ablated_case)
    ablation_ok=ablated_verdict.get("pass") is False

    return {
        "schema":SCHEMA+"_RESULT",
        "case_id":dcase["case_id"],
        "pass":full_ok and ablation_ok,
        "delegation_case_class":dcase["case_class"],
        "delegation_worker_count":len(workers),
        "delegation_plan_pass":True,
        "evidence_count":len(evidence),
        "synthesis_pass":synthesis_ok,
        "selected_claims":selected,
        "artifact_pass":artifact_ok,
        "artifact_sha256":payload_sha,
        "missing_evidence_ablation_id":missing_id,
        "missing_evidence_ablation_fails":ablation_ok,
        "objective_trace":{"trace_source":"HARNESS_OBJECTIVE","events":events},
        "terminal_authority":False,
        "fresh_reality_authority":False,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }

def run_batch(seed:int,count:int=10)->dict[str,Any]:
    rows=[]
    for i in range(count):
        try: rows.append(execute_case(seed+i*16127,i))
        except Exception as exc:
            rows.append({"case_id":f"ERR-{i}","pass":False,"error":type(exc).__name__+":"+str(exc)})
    passed=sum(int(x.get("pass") is True) for x in rows)
    return {
        "schema":SCHEMA+"_BATCH_RESULT",
        "case_count":count,"passed":passed,"failed":count-passed,
        "all_pass":passed==count,
        "failures":[x for x in rows if x.get("pass") is not True][:20],
        "terminal_authority":False,"fresh_reality_authority":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run_batch(20261007,10),indent=2,sort_keys=True))
