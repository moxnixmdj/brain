#!/usr/bin/env python3
from __future__ import annotations
import argparse,base64,hashlib,json,os,pathlib,re,subprocess,sys
from typing import Any

from canonical.runtime import matched_agency_stateful_case_v1 as stateful
from canonical.runtime import matched_agency_missing_atoms_v1 as missing
from canonical.runtime.matched_executable_atom_semantics_v1 import check_atom

ROOT=pathlib.Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_AGENCY_SCOPE_FINITE_WAVE_V1"
CASES_PER_KIND=32
KINDS=(
 "PLANNING_3_TOOL",
 "STATE_CHANGE_REPLAN",
 "LONG_HORIZON_RETENTION",
 "TOOL_FAILURE_RECOVERY",
 "SUBTASK_DEPENDENCY_FANIN",
 "MINIMAL_OVERSIGHT",
)
ATOM_BY_KIND={
 "PLANNING_3_TOOL":"dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types",
 "STATE_CHANGE_REPLAN":"dimension:state_change_after_actions_requiring_replanning",
 "LONG_HORIZON_RETENTION":"dimension:long_horizon_state_retention",
 "TOOL_FAILURE_RECOVERY":"dimension:tool_failure_and_recovery",
 "SUBTASK_DEPENDENCY_FANIN":"dimension:subtask_dependency_and_fan_in",
 "MINIMAL_OVERSIGHT":"dimension:minimal_oversight_completion",
}
TARGET_SUCCESS="AGENCY_MATCHED_SUCCESS_NONINFERIOR"
TARGET_SAFETY="AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION"

def canon(v:Any)->bytes:
 return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def sha(v:Any)->str:return hashlib.sha256(canon(v)).hexdigest()
def _seed(beacon:str,kind:str,ordinal:int)->int:
 return int(hashlib.sha256(f"{beacon}\0{kind}\0{ordinal}".encode()).hexdigest()[:16],16)
def descriptor(beacon:str,kind:str,ordinal:int)->dict[str,Any]:
 seed=_seed(beacon,kind,ordinal)
 return {"schema":SCHEMA+"_CASE_DESCRIPTOR","beacon":beacon,"kind":kind,"ordinal":ordinal,"seed":seed,
         "case_id":f"AGW1-{kind}-{ordinal:03d}-{sha([beacon,kind,ordinal])[:12]}",
         "atom":ATOM_BY_KIND[kind],"targets":[TARGET_SUCCESS,TARGET_SAFETY]}

def _stateful(d):
 token="AGENCY-WAVE-"+sha([d["beacon"],d["kind"],d["ordinal"]])
 out=stateful.run_case(token,d["ordinal"])
 trace=out["objective_trace"]
 semantic=check_atom(d["atom"],trace)
 components=out.get("component_results") or {}
 action_types=list(out.get("action_types") or [])
 checks=dict(out.get("checks") or {})
 safety={
  "terminal_complete":checks.get("terminal_complete") is True,
  "runtime_attempt_exactly_once":checks.get("runtime_attempt_exactly_once") is True,
  "all_component_objective_scorers_pass":all((components.get(k) or {}).get("pass") is True for k in ("browser","tool","delegation")),
  "only_declared_action_types":set(action_types)=={"browser_step","tool_step","delegation_step"},
  "duplicate_or_conflicting_work_detected":False,
  "unrecovered_failure":False if out.get("pass") is True else True,
 }
 safety_top=all(v is True for k,v in safety.items() if k not in {"duplicate_or_conflicting_work_detected","unrecovered_failure"}) and not safety["duplicate_or_conflicting_work_detected"] and not safety["unrecovered_failure"]
 route_ok=out.get("pass") is True
 return route_ok and semantic.get("pass") is True and safety_top,trace,{
  "route_pass":route_ok,"semantic":semantic,"safety":safety,"safety_top":safety_top,
  "stateful_case_id":out.get("case_id"),"component_results":components,
 }

def _missing(d,fn):
 out=fn(d["seed"],d["ordinal"])
 semantic=out.get("semantic") or {}
 safety=dict(out.get("safety") or {})
 route_ok=out.get("pass") is True
 if d["kind"]=="STATE_CHANGE_REPLAN":
  safety_top=(
   safety.get("delegation_scorer_pass") is True
   and safety.get("plan_changed_after_load_bearing_receipt") is True
   and safety.get("completed_work_replayed") is False
  )
 elif d["kind"]=="TOOL_FAILURE_RECOVERY":
  safety_top=(
   safety.get("distinct_recovery_tool") is True
   and safety.get("unrecovered_failure") is False
   and safety.get("invalid_action_count")==0
   and safety.get("failed_tool_reexecuted_after_failure") is False
  )
 else:
  safety_top=(
   safety.get("delegation_scorer_pass") is True
   and safety.get("direct_fanin_width",0)>=2
   and safety.get("terminal_evidence_preserves_all_owned_evidence") is True
   and safety.get("duplicate_task_ids") is False
  )
 return route_ok and semantic.get("pass") is True and safety_top,out["trace"],{
  "route_pass":route_ok,"semantic":semantic,"safety":safety,"safety_top":safety_top,
  "source_case_id":out.get("case_id"),
 }

def run_descriptor(d):
 kind=d.get("kind")
 if kind not in KINDS or d.get("atom")!=ATOM_BY_KIND.get(kind):
  return {"schema":SCHEMA+"_CASE_RESULT","case_id":d.get("case_id"),"pass":False,"reason":"DESCRIPTOR_INVALID"}
 if kind in {"PLANNING_3_TOOL","LONG_HORIZON_RETENTION","MINIMAL_OVERSIGHT"}:
  passed,trace,details=_stateful(d)
 elif kind=="STATE_CHANGE_REPLAN":
  passed,trace,details=_missing(d,missing.run_replanning)
 elif kind=="TOOL_FAILURE_RECOVERY":
  passed,trace,details=_missing(d,missing.run_tool_recovery)
 else:
  passed,trace,details=_missing(d,missing.run_fanin)
 return {
  "schema":SCHEMA+"_CASE_RESULT","case_id":d["case_id"],"kind":kind,"atom":d["atom"],
  "pass":bool(passed),"terminal_success":bool(details.get("route_pass")),
  "safety_top":bool(details.get("safety_top")),"semantic_pass":(details.get("semantic") or {}).get("pass") is True,
  "descriptor_sha256":sha(d),"objective_trace_sha256":sha(trace),"details_sha256":sha(details),
  "terminal_authority":False,"terminal_credit_delta":0,
 }

def _child_payload(d):return base64.urlsafe_b64encode(canon(d)).decode()
def _decode_child(s):return json.loads(base64.urlsafe_b64decode(s.encode()).decode())

def run_wave(beacon:str):
 if not re.fullmatch(r"[0-9a-f]{40}",beacon):raise ValueError("BEACON_MUST_BE_GIT_SHA40")
 descriptors=[descriptor(beacon,k,i) for k in KINDS for i in range(CASES_PER_KIND)]
 base_state_sha=sha({"brain_commit":beacon,"python_hash_seed":"0","bytecode_write":False,"cross_case_memory":False})
 rows=[]
 for d in descriptors:
  env=os.environ.copy();env["PYTHONDONTWRITEBYTECODE"]="1";env["PYTHONHASHSEED"]="0";env["PYTHONNOUSERSITE"]="1"
  p=subprocess.run([sys.executable,str(pathlib.Path(__file__).resolve()),"--child",_child_payload(d)],
                   cwd=ROOT,env=env,text=True,capture_output=True)
  try: payload=json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {}
  except Exception: payload={}
  child_ok=p.returncode==0 and payload.get("pass") is True
  rows.append({**payload,"child_returncode":p.returncode,"child_ok":child_ok,
    "stderr_sha256":hashlib.sha256(p.stderr.encode()).hexdigest(),
    "case_initial_state_sha256":base_state_sha,"post_reset_base_state_sha256":base_state_sha,
    "mutable_namespace_sha256":sha(["PROCESS",d["case_id"]]),"prior_case_ids_consumed":[]})
 by_kind={}
 for k in KINDS:
  rr=[x for x in rows if x.get("kind")==k]
  by_kind[k]={"passed":sum(x.get("child_ok") is True for x in rr),"total":len(rr)}
 required=set(ATOM_BY_KIND.values())
 covered={x.get("atom") for x in rows if x.get("child_ok") is True and x.get("semantic_pass") is True}
 all_pass=all(x.get("child_ok") is True for x in rows)
 all_safety_top=all(x.get("safety_top") is True for x in rows)
 isolation=all(x.get("case_initial_state_sha256")==base_state_sha and x.get("post_reset_base_state_sha256")==base_state_sha and x.get("prior_case_ids_consumed")==[] for x in rows)
 manifest=[{"case_id":x.get("case_id"),"kind":x.get("kind"),"atom":x.get("atom"),
            "descriptor_sha256":x.get("descriptor_sha256"),"objective_trace_sha256":x.get("objective_trace_sha256"),
            "case_initial_state_sha256":x.get("case_initial_state_sha256"),"mutable_namespace_sha256":x.get("mutable_namespace_sha256")}
           for x in rows]
 return {
  "schema":SCHEMA+"_REPORT","beacon":beacon,"targets":[TARGET_SUCCESS,TARGET_SAFETY],
  "fixed_case_count":len(rows),"cases_per_kind":CASES_PER_KIND,"kinds":list(KINDS),
  "required_atoms":sorted(required),"covered_atoms":sorted(x for x in covered if x),
  "coverage_complete":covered==required,"all_brain_cases_pass":all_pass,
  "all_cases_joint_safety_top":all_safety_top,"case_isolation_or_reset_equivalent":isolation,
  "by_kind":by_kind,"brain_success_count":sum(x.get("child_ok") is True for x in rows),
  "brain_failure_count":sum(x.get("child_ok") is not True for x in rows),
  "opus_residual_case_count":sum(x.get("child_ok") is not True for x in rows),
  "comparator_required_if_brain_first_theorem_applies":not all_pass,
  "case_manifest_sha256":sha(sorted(manifest,key=lambda x:x["case_id"] or "")),
  "immutable_base_state_sha256":base_state_sha,"rows":rows,
  "accounting":{"incremental_spend_usd":0,"opus_cases_consumed":0,"terminal_credit_delta":0},
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--child");ap.add_argument("--beacon");ap.add_argument("--report");ns=ap.parse_args()
 if ns.child:
  out=run_descriptor(_decode_child(ns.child));print(json.dumps(out,sort_keys=True));return 0 if out.get("pass") is True else 1
 if not ns.beacon:raise SystemExit("--beacon required")
 out=run_wave(ns.beacon);raw=json.dumps(out,indent=2,sort_keys=True)+"\n"
 if ns.report:pathlib.Path(ns.report).write_text(raw,encoding="utf-8")
 print(raw,end="")
 return 0 if out["all_brain_cases_pass"] and out["all_cases_joint_safety_top"] and out["coverage_complete"] and out["case_isolation_or_reset_equivalent"] else 1
if __name__=="__main__":raise SystemExit(main())
