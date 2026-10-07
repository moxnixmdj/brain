#!/usr/bin/env python3
from __future__ import annotations
import argparse,base64,hashlib,json,os,pathlib,re,subprocess,sys
from typing import Any

from canonical.runtime import matched_executable_atom_semantics_v1 as atoms
from canonical.runtime import matched_agency_stateful_case_v1 as stateful
from canonical.runtime import delegation_whole_scope_candidate_v2 as delegation_candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as delegation_proof
from canonical.runtime import tool_discovery_information_safe_candidate as tool_candidate
from canonical.runtime import tool_discovery_information_safe_proof_v2 as tool_proof

ROOT=pathlib.Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_AGENCY_SCOPE_FINITE_WAVE_V1"
CASES_PER_KIND=32
KINDS=("THREE_TOOL_STATEFUL","REPLAN_AFTER_STATE_CHANGE","TOOL_FAILURE_RECOVERY","SUBTASK_FANIN")
ATOMS_BY_KIND={
 "THREE_TOOL_STATEFUL":(
  "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types",
  "dimension:long_horizon_state_retention",
  "dimension:minimal_oversight_completion",
 ),
 "REPLAN_AFTER_STATE_CHANGE":("dimension:state_change_after_actions_requiring_replanning",),
 "TOOL_FAILURE_RECOVERY":("dimension:tool_failure_and_recovery",),
 "SUBTASK_FANIN":("dimension:subtask_dependency_and_fan_in",),
}
TARGETS=("AGENCY_MATCHED_SUCCESS_NONINFERIOR","AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION")

def canon(v:Any)->bytes:
 return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def sha(v:Any)->str:return hashlib.sha256(canon(v)).hexdigest()
def _seed(beacon:str,kind:str,ordinal:int)->int:
 return int(hashlib.sha256(f"{beacon}\0{kind}\0{ordinal}".encode()).hexdigest()[:16],16)
def descriptor(beacon:str,kind:str,ordinal:int)->dict[str,Any]:
 return {"schema":SCHEMA+"_CASE_DESCRIPTOR","beacon":beacon,"kind":kind,"ordinal":ordinal,
         "seed":_seed(beacon,kind,ordinal),
         "case_id":f"AGW1-{kind}-{ordinal:03d}-{sha([beacon,kind,ordinal])[:12]}",
         "targets":list(TARGETS),"atoms":list(ATOMS_BY_KIND[kind])}

def _stateful(d):
 token="AGENCY-FINITE-"+sha([d["beacon"],d["kind"],d["ordinal"]])
 row=stateful.run_case(token,d["ordinal"])
 return bool(row.get("pass") is True),row["objective_trace"],{
  "route":"matched_agency_stateful_case_v1::run_case",
  "checks":row.get("checks"),"planner_plan":row.get("planner_plan"),
  "component_results":row.get("component_results"),
 }

def _delegation_case(d,ordinal):
 case=delegation_proof.generate_case(d["seed"],ordinal)
 first=delegation_candidate.solve_initial(delegation_proof.public_initial(case))
 second=delegation_candidate.solve_after_receipt(delegation_proof.public_after_receipt(case),first)
 verdict=delegation_proof.score_episode(case,first,second)
 return case,first,second,verdict

def _replan(d):
 case,first,second,verdict=_delegation_case(d,3)
 changed=(first.get("task_ids")!=second.get("task_ids") or first.get("assignment")!=second.get("assignment") or first.get("waves")!=second.get("waves"))
 ok=bool(verdict.get("pass") is True and changed and second.get("task_ids"))
 events=[
  {"seq":0,"type":"STATE_CHANGE","source":"HARNESS","new_version":1,"receipt_kind":case["_oracle"]["receipt"]["kind"]},
  {"seq":1,"type":"PLAN_REVISED","source":"HARNESS","observed_state_version":1,"plan_sha256":sha({"task_ids":second.get("task_ids"),"waves":second.get("waves"),"assignment":second.get("assignment")})},
 ]
 seq=2
 for sid in second.get("task_ids") or []:
  events.append({"seq":seq,"type":"ACTION","source":"HARNESS","action_type":"delegated_step","task_id":sid});seq+=1
 events.append({"seq":seq,"type":"TERMINAL","source":"HARNESS","success":ok})
 return ok,{"trace_source":"HARNESS_OBJECTIVE","events":events},{
  "route":"delegation_v2_replan","case_class":case.get("case_class"),"scorer":verdict,
  "plan_changed":changed,"initial_plan_sha256":sha(first),"revised_plan_sha256":sha(second),
 }

def _tool_recovery(d):
 case=tool_proof.generate_case(d["seed"],1)
 receipts=[]
 s1=tool_proof.v1.execute_stage(case,1,tool_candidate.next_action,receipts)
 n1=len(receipts)
 s2=tool_proof.v1.execute_stage(case,2,tool_candidate.next_action,receipts)
 stage2_receipts=receipts[n1:]
 full=tool_proof.score_episode(case,tool_candidate.next_action)
 neg=[r for r in stage2_receipts if r.get("kind")=="SAFE_CAPABILITY_PROBE" and r.get("supported") is False]
 pos=[r for r in stage2_receipts if r.get("kind")=="SAFE_CAPABILITY_PROBE" and r.get("supported") is True]
 if not pos:
  selected=s2.get("selected")
  pos=[r for r in receipts if r.get("kind")=="SAFE_CAPABILITY_PROBE" and r.get("supported") is True and r.get("tool_id")==selected]
 fail=neg[0] if neg else {}
 recover=next((r for r in pos if r.get("tool_id")!=fail.get("tool_id")),pos[0] if pos else {})
 ok=bool(s1.get("pass") is True and s2.get("pass") is True and full.get("pass") is True and fail and recover and fail.get("tool_id")!=recover.get("tool_id"))
 trace={"trace_source":"HARNESS_OBJECTIVE","events":[
  {"seq":0,"type":"TOOL_RESULT","source":"HARNESS","tool_id":fail.get("tool_id"),"ok":False,"capability":fail.get("capability"),"epoch":fail.get("epoch")},
  {"seq":1,"type":"TOOL_RESULT","source":"HARNESS","tool_id":recover.get("tool_id"),"ok":True,"capability":recover.get("capability"),"epoch":recover.get("epoch")},
  {"seq":2,"type":"TERMINAL","source":"HARNESS","success":ok},
 ]}
 return ok,trace,{"route":"tool_discovery_selected_tool_loses_capability","case_class":case.get("case_class"),"stage1":s1,"stage2":s2,"full_pass":full.get("pass"),"negative_receipt":fail,"recovery_receipt":recover}

def _fanin(d):
 case=delegation_proof.generate_case(d["seed"],0)
 first=delegation_candidate.solve_initial(delegation_proof.public_initial(case))
 second=delegation_candidate.solve_after_receipt(delegation_proof.public_after_receipt(case),first)
 verdict=delegation_proof.score_episode(case,first,second)
 deps=first.get("dependencies") or {}
 joins=[(sid,list(ins)) for sid,ins in deps.items() if len(ins)>=2]
 events=[];seq=0
 all_done=set()
 for sid in first.get("task_ids") or []:
  events.append({"seq":seq,"type":"SUBTASK_COMPLETE","source":"HARNESS","subtask_id":sid});seq+=1;all_done.add(sid)
 if joins:
  sid,ins=joins[0]
  events.append({"seq":seq,"type":"JOIN","source":"HARNESS","join_task_id":sid,"inputs":ins});seq+=1
 ok=bool(verdict.get("pass") is True and joins and set(joins[0][1]).issubset(all_done) and first.get("terminal_evidence"))
 events.append({"seq":seq,"type":"TERMINAL","source":"HARNESS","success":ok})
 return ok,{"trace_source":"HARNESS_OBJECTIVE","events":events},{
  "route":"delegation_v2_fanin","case_class":case.get("case_class"),"scorer":verdict,
  "join_count":len(joins),"joins":joins,"terminal_evidence_count":len(first.get("terminal_evidence") or []),
 }

EXEC={"THREE_TOOL_STATEFUL":_stateful,"REPLAN_AFTER_STATE_CHANGE":_replan,"TOOL_FAILURE_RECOVERY":_tool_recovery,"SUBTASK_FANIN":_fanin}

def run_descriptor(d):
 kind=d.get("kind")
 if kind not in EXEC or tuple(d.get("atoms") or ())!=ATOMS_BY_KIND[kind]:
  return {"schema":SCHEMA+"_CASE_RESULT","case_id":d.get("case_id"),"pass":False,"reason":"DESCRIPTOR_INVALID"}
 route_ok,trace,details=EXEC[kind](d)
 sem={a:atoms.check_atom(a,trace) for a in ATOMS_BY_KIND[kind]}
 passed=bool(route_ok and all(x.get("pass") is True for x in sem.values()))
 return {"schema":SCHEMA+"_CASE_RESULT","case_id":d["case_id"],"kind":kind,"atoms":list(ATOMS_BY_KIND[kind]),
         "pass":passed,"route_pass":route_ok,"semantic_results":sem,
         "descriptor_sha256":sha(d),"objective_trace_sha256":sha(trace),"details_sha256":sha(details),
         "details":details,"terminal_credit_delta":0}

def _payload(d):return base64.urlsafe_b64encode(canon(d)).decode()
def _decode(s):return json.loads(base64.urlsafe_b64decode(s.encode()).decode())
def run_wave(beacon):
 if not re.fullmatch(r"[0-9a-f]{40}",beacon):raise ValueError("BEACON_MUST_BE_GIT_SHA40")
 ds=[descriptor(beacon,k,i) for k in KINDS for i in range(CASES_PER_KIND)]
 base=sha({"brain_commit":beacon,"python_hash_seed":"0","bytecode_write":False,"external_network":False,"cross_case_memory":False})
 rows=[]
 for d in ds:
  env=os.environ.copy();env.update({"PYTHONDONTWRITEBYTECODE":"1","PYTHONHASHSEED":"0","PYTHONNOUSERSITE":"1"})
  p=subprocess.run([sys.executable,str(pathlib.Path(__file__).resolve()),"--child",_payload(d)],cwd=ROOT,env=env,text=True,capture_output=True)
  try:out=json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {}
  except Exception:out={}
  ok=p.returncode==0 and out.get("pass") is True
  rows.append({**out,"child_returncode":p.returncode,"child_ok":ok,"stderr_sha256":hashlib.sha256(p.stderr.encode()).hexdigest(),
               "case_initial_state_sha256":base,"post_reset_base_state_sha256":base,
               "mutable_namespace_sha256":sha(["PROCESS",d["case_id"]]),"prior_case_ids_consumed":[]})
 required={a for v in ATOMS_BY_KIND.values() for a in v}
 covered={a for x in rows if x.get("child_ok") is True for a,r in (x.get("semantic_results") or {}).items() if r.get("pass") is True}
 all_pass=all(x.get("child_ok") is True for x in rows)
 isolated=all(x.get("case_initial_state_sha256")==base and x.get("post_reset_base_state_sha256")==base and x.get("prior_case_ids_consumed")==[] for x in rows)
 manifest=[{"case_id":x.get("case_id"),"kind":x.get("kind"),"atoms":x.get("atoms"),"descriptor_sha256":x.get("descriptor_sha256"),"objective_trace_sha256":x.get("objective_trace_sha256"),"case_initial_state_sha256":x.get("case_initial_state_sha256"),"mutable_namespace_sha256":x.get("mutable_namespace_sha256")} for x in rows]
 by_kind={k:{"passed":sum(x.get("child_ok") is True for x in rows if x.get("kind")==k),"total":sum(x.get("kind")==k for x in rows)} for k in KINDS}
 return {"schema":SCHEMA+"_REPORT","beacon":beacon,"targets":list(TARGETS),"fixed_case_count":len(rows),"cases_per_kind":CASES_PER_KIND,
         "kinds":list(KINDS),"required_atoms":sorted(required),"covered_atoms":sorted(covered),"coverage_complete":covered==required,
         "all_brain_cases_pass":all_pass,"case_isolation_or_reset_equivalent":isolated,"by_kind":by_kind,
         "brain_success_count":sum(x.get("child_ok") is True for x in rows),"brain_failure_count":sum(x.get("child_ok") is not True for x in rows),
         "opus_residual_case_count":sum(x.get("child_ok") is not True for x in rows),
         "case_manifest_sha256":sha(sorted(manifest,key=lambda x:x["case_id"] or "")),"immutable_base_state_sha256":base,
         "rows":rows,"accounting":{"incremental_spend_usd":0,"opus_cases_consumed":0,"terminal_credit_delta":0}}

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--child");ap.add_argument("--beacon");ap.add_argument("--report");ns=ap.parse_args()
 if ns.child:
  out=run_descriptor(_decode(ns.child));print(json.dumps(out,sort_keys=True));return 0 if out.get("pass") is True else 1
 if not ns.beacon:raise SystemExit("--beacon required")
 out=run_wave(ns.beacon);raw=json.dumps(out,indent=2,sort_keys=True)+"\n"
 if ns.report:pathlib.Path(ns.report).write_text(raw,encoding="utf-8")
 print(raw,end="");return 0 if out["all_brain_cases_pass"] and out["coverage_complete"] and out["case_isolation_or_reset_equivalent"] else 1
if __name__=="__main__":raise SystemExit(main())
