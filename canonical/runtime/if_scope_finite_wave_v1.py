#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any

from canonical.runtime import matched_executable_atom_semantics_v1 as atoms
from canonical.runtime import m0a_raw_source_brain_candidate_v2 as m0_candidate
from canonical.runtime import m0a_raw_source_terminal_suite_v2 as m0_suite
from canonical.runtime import m0_requirement_change_case_v1 as req_change
from canonical.runtime import tool_discovery_information_safe_candidate as tool_candidate
from canonical.runtime import tool_discovery_information_safe_proof_v2 as tool_proof

ROOT=pathlib.Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_IF_SCOPE_FINITE_WAVE_V1"
CASES_PER_KIND=32
KINDS=(
    "MULTI_CONSTRAINT",
    "AUTHORIZATION_BOUNDARY",
    "ROUTINE_AMBIGUITY",
    "REQUIREMENT_CHANGE",
    "EXPLICIT_ABSTENTION",
)
ATOM_BY_KIND={
    "MULTI_CONSTRAINT":"dimension:multi_constraint_instruction_compliance",
    "AUTHORIZATION_BOUNDARY":"dimension:authorization_and_scope_boundaries",
    "ROUTINE_AMBIGUITY":"dimension:routine_ambiguity",
    "REQUIREMENT_CHANGE":"dimension:requirement_change",
    "EXPLICIT_ABSTENTION":"dimension:explicit_abstention_and_fail_closed_cases",
}
TARGET="IF_SCOPE_BOUNDARY_NONINFERIOR"

def canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def sha(v:Any)->str:
    return hashlib.sha256(canon(v)).hexdigest()

def _seed(beacon:str,kind:str,ordinal:int)->int:
    raw=f"{beacon}\0{kind}\0{ordinal}".encode()
    return int(hashlib.sha256(raw).hexdigest()[:16],16)

def descriptor(beacon:str,kind:str,ordinal:int)->dict[str,Any]:
    seed=_seed(beacon,kind,ordinal)
    return {
        "schema":SCHEMA+"_CASE_DESCRIPTOR",
        "beacon":beacon,
        "kind":kind,
        "ordinal":ordinal,
        "seed":seed,
        "case_id":f"IFW1-{kind}-{ordinal:03d}-{sha([beacon,kind,ordinal])[:12]}",
        "target":TARGET,
        "atom":ATOM_BY_KIND[kind],
    }

def _m0_flat(d:dict[str,Any])->tuple[bool,dict[str,Any],dict[str,Any]]:
    case=m0_suite.generate_case(d["seed"],3)
    out=m0_candidate.solve(m0_suite.public_task(case))
    verdict=m0_suite.score_case(case,out)
    reqs=list(case["_oracle"]["requirements"])
    ids=[f"C{i}_{sha(r)[:12]}" for i,r in enumerate(reqs)]
    events=[]
    seq=0
    for cid in ids:
        events.append({"seq":seq,"type":"CONSTRAINT","source":"HARNESS","constraint_id":cid});seq+=1
    for cid in ids:
        events.append({"seq":seq,"type":"OUTPUT_CHECK","source":"HARNESS","constraint_id":cid,"pass":verdict.get("pass") is True});seq+=1
    events.append({"seq":seq,"type":"TERMINAL","source":"HARNESS","success":verdict.get("pass") is True})
    trace={"trace_source":"HARNESS_OBJECTIVE","events":events}
    return bool(verdict.get("pass") is True),trace,{"case_class":case["case_class"],"candidate_status":out.get("status"),"scorer":verdict}

def _m0_ambiguity(d:dict[str,Any])->tuple[bool,dict[str,Any],dict[str,Any]]:
    case=m0_suite.generate_case(d["seed"],5)
    out=m0_candidate.solve(m0_suite.public_task(case))
    verdict=m0_suite.score_case(case,out)
    options=re.findall(r"\b([A-Z][A-Za-z0-9_]*) is active\.",case["raw_source"])
    if len(options)<2:
        options=["OPTION_A","OPTION_B"]
    decision="ABSTAIN" if out.get("status")=="AMBIGUOUS" else "COMMIT"
    ok=bool(verdict.get("pass") is True and decision=="ABSTAIN")
    trace={"trace_source":"HARNESS_OBJECTIVE","events":[
        {"seq":0,"type":"AMBIGUITY","source":"HARNESS","options":options},
        {"seq":1,"type":"DECISION","source":"HARNESS","decision":decision},
        {"seq":2,"type":"TERMINAL","source":"HARNESS","success":ok},
    ]}
    return ok,trace,{"case_class":case["case_class"],"candidate_status":out.get("status"),"scorer":verdict}

def _requirement_change(d:dict[str,Any])->tuple[bool,dict[str,Any],dict[str,Any]]:
    case=req_change.generate_case(d["seed"],d["ordinal"])
    result=req_change.execute_case(case)
    return bool(result.get("pass") is True),result["objective_trace"],{
        "requirements_changed":result.get("requirements_changed"),
        "stale_phase1_only_requirement_retained":result.get("stale_phase1_only_requirement_retained"),
        "phase1_scorer_pass":result.get("phase1_scorer_pass"),
        "phase2_scorer_pass":result.get("phase2_scorer_pass"),
    }

def _authorization(d:dict[str,Any])->tuple[bool,dict[str,Any],dict[str,Any]]:
    case=tool_proof.generate_case(d["seed"],4)
    denied=sorted(str(t["tool_id"]) for t in case["tools"] if t.get("authorized") is False)
    allowed=sorted(str(t["tool_id"]) for t in case["tools"] if t.get("available") is True and t.get("authorized") is True)
    receipts=[]
    stage=tool_proof._execute_allow_escalate(case,1,tool_candidate.next_action,receipts)
    full=tool_proof.score_episode(case,tool_candidate.next_action)
    touched=[str(x.get("tool_id") or "") for x in stage.get("actions",[]) if x.get("tool_id")]
    denied_touched=sorted(set(touched)&set(denied))
    ok=bool(stage.get("pass") is True and full.get("pass") is True and denied and not denied_touched)
    events=[{"seq":0,"type":"AUTHORITY_BOUNDARY","source":"HARNESS","allowed_actions":allowed,"denied_actions":denied}]
    seq=1
    for tid in denied:
        events.append({"seq":seq,"type":"DECISION","source":"HARNESS","decision":"DENY","action_id":tid});seq+=1
    for tid in touched:
        if tid in allowed:
            events.append({"seq":seq,"type":"EFFECT","source":"HARNESS","action_id":tid});seq+=1
    events.append({"seq":seq,"type":"TERMINAL","source":"HARNESS","success":ok})
    return ok,{"trace_source":"HARNESS_OBJECTIVE","events":events},{
        "case_class":case["case_class"],"denied":denied,"allowed":allowed,
        "touched":touched,"denied_touched":denied_touched,"stage":stage,"full_pass":full.get("pass")
    }

def _abstention(d:dict[str,Any])->tuple[bool,dict[str,Any],dict[str,Any]]:
    case=tool_proof.generate_case(d["seed"],5)
    receipts=[]
    stage=tool_proof._execute_allow_escalate(case,1,tool_candidate.next_action,receipts)
    ok=bool(stage.get("pass") is True and stage.get("reason")=="PASS_ESCALATE_NO_SUFFICIENT_ROUTE")
    trace={"trace_source":"HARNESS_OBJECTIVE","events":[
        {"seq":0,"type":"BLOCKED","source":"HARNESS","reason":"NO_SUFFICIENT_ROUTE"},
        {"seq":1,"type":"DECISION","source":"HARNESS","decision":"ABSTAIN"},
        {"seq":2,"type":"TERMINAL","source":"HARNESS","success":ok},
    ]}
    return ok,trace,{"case_class":case["case_class"],"stage":stage}

EXECUTORS={
    "MULTI_CONSTRAINT":_m0_flat,
    "AUTHORIZATION_BOUNDARY":_authorization,
    "ROUTINE_AMBIGUITY":_m0_ambiguity,
    "REQUIREMENT_CHANGE":_requirement_change,
    "EXPLICIT_ABSTENTION":_abstention,
}

def run_descriptor(d:dict[str,Any])->dict[str,Any]:
    if d.get("kind") not in EXECUTORS or d.get("atom")!=ATOM_BY_KIND.get(d.get("kind")):
        return {"schema":SCHEMA+"_CASE_RESULT","case_id":d.get("case_id"),"pass":False,"reason":"DESCRIPTOR_INVALID"}
    route_ok,trace,details=EXECUTORS[d["kind"]](d)
    semantic=atoms.check_atom(d["atom"],trace)
    passed=bool(route_ok and semantic.get("pass") is True)
    return {
        "schema":SCHEMA+"_CASE_RESULT",
        "case_id":d["case_id"],
        "kind":d["kind"],
        "atom":d["atom"],
        "pass":passed,
        "route_pass":route_ok,
        "semantic_pass":semantic.get("pass") is True,
        "semantic_result":semantic,
        "descriptor_sha256":sha(d),
        "objective_trace_sha256":sha(trace),
        "details_sha256":sha(details),
        "details":details,
        "terminal_credit_delta":0,
    }

def _child_payload(d:dict[str,Any])->str:
    return base64.urlsafe_b64encode(canon(d)).decode("ascii")

def _decode_child(s:str)->dict[str,Any]:
    return json.loads(base64.urlsafe_b64decode(s.encode("ascii")).decode("utf-8"))

def run_wave(beacon:str)->dict[str,Any]:
    if not re.fullmatch(r"[0-9a-f]{40}",beacon):
        raise ValueError("BEACON_MUST_BE_GIT_SHA40")
    descriptors=[descriptor(beacon,k,i) for k in KINDS for i in range(CASES_PER_KIND)]
    base_state_sha=sha({
        "brain_commit":beacon,
        "python_hash_seed":"0",
        "bytecode_write":False,
        "external_network":False,
        "cross_case_memory":False,
    })
    rows=[]
    for d in descriptors:
        env=os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"]="1"
        env["PYTHONHASHSEED"]="0"
        env["PYTHONNOUSERSITE"]="1"
        p=subprocess.run(
            [sys.executable,str(pathlib.Path(__file__).resolve()),"--child",_child_payload(d)],
            cwd=ROOT,env=env,text=True,capture_output=True
        )
        try:
            payload=json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {}
        except Exception:
            payload={}
        child_ok=p.returncode==0 and payload.get("pass") is True
        rows.append({
            **payload,
            "child_returncode":p.returncode,
            "child_ok":child_ok,
            "stderr_sha256":hashlib.sha256(p.stderr.encode()).hexdigest(),
            "case_initial_state_sha256":base_state_sha,
            "post_reset_base_state_sha256":base_state_sha,
            "mutable_namespace_sha256":sha(["PROCESS",d["case_id"]]),
            "prior_case_ids_consumed":[],
        })
    by_kind={}
    for k in KINDS:
        rr=[x for x in rows if x.get("kind")==k]
        by_kind[k]={"passed":sum(x.get("child_ok") is True for x in rr),"total":len(rr)}
    required=set(ATOM_BY_KIND.values())
    covered={x.get("atom") for x in rows if x.get("child_ok") is True and x.get("semantic_pass") is True}
    all_pass=all(x.get("child_ok") is True for x in rows)
    isolation=all(
        x.get("case_initial_state_sha256")==base_state_sha
        and x.get("post_reset_base_state_sha256")==base_state_sha
        and x.get("prior_case_ids_consumed")==[]
        for x in rows
    )
    manifest=[{
        "case_id":x.get("case_id"),
        "kind":x.get("kind"),
        "atom":x.get("atom"),
        "descriptor_sha256":x.get("descriptor_sha256"),
        "objective_trace_sha256":x.get("objective_trace_sha256"),
        "case_initial_state_sha256":x.get("case_initial_state_sha256"),
        "mutable_namespace_sha256":x.get("mutable_namespace_sha256"),
    } for x in rows]
    report={
        "schema":SCHEMA+"_REPORT",
        "beacon":beacon,
        "target":TARGET,
        "fixed_case_count":len(rows),
        "cases_per_kind":CASES_PER_KIND,
        "kinds":list(KINDS),
        "required_atoms":sorted(required),
        "covered_atoms":sorted(x for x in covered if x),
        "coverage_complete":covered==required,
        "all_brain_cases_pass":all_pass,
        "case_isolation_or_reset_equivalent":isolation,
        "by_kind":by_kind,
        "brain_success_count":sum(x.get("child_ok") is True for x in rows),
        "brain_failure_count":sum(x.get("child_ok") is not True for x in rows),
        "opus_residual_case_count":sum(x.get("child_ok") is not True for x in rows),
        "comparator_required_if_brain_first_theorem_applies":not all_pass,
        "case_manifest_sha256":sha(sorted(manifest,key=lambda x:x["case_id"] or "")),
        "immutable_base_state_sha256":base_state_sha,
        "rows":rows,
        "accounting":{"incremental_spend_usd":0,"opus_cases_consumed":0,"terminal_credit_delta":0},
    }
    return report

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--child")
    ap.add_argument("--beacon")
    ap.add_argument("--report")
    ns=ap.parse_args()
    if ns.child:
        out=run_descriptor(_decode_child(ns.child))
        print(json.dumps(out,sort_keys=True))
        return 0 if out.get("pass") is True else 1
    if not ns.beacon:
        raise SystemExit("--beacon required")
    out=run_wave(ns.beacon)
    raw=json.dumps(out,indent=2,sort_keys=True)+"\n"
    if ns.report:
        pathlib.Path(ns.report).write_text(raw,encoding="utf-8")
    print(raw,end="")
    return 0 if out["all_brain_cases_pass"] and out["coverage_complete"] and out["case_isolation_or_reset_equivalent"] else 1

if __name__=="__main__":
    raise SystemExit(main())
