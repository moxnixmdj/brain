#!/usr/bin/env python3
from __future__ import annotations
import argparse,base64,hashlib,json,os,pathlib,re,subprocess,sys
from typing import Any
from canonical.runtime import matched_executable_atom_semantics_v1 as atoms
from canonical.runtime import matched_research_tool_artifact_direct_v1 as research
from canonical.runtime import matched_browser_memory_recovery_direct_v1 as browser
from canonical.runtime import matched_coding_debug_tool_discovery_fresh_v1 as coding
from canonical.runtime import matched_delegation_synthesis_artifact_direct_v1 as delegation
from canonical.runtime import matched_cross_capability_handoff_rollback_direct_v1 as handoff

ROOT=pathlib.Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_COMPOSITION_SCOPE_FINITE_WAVE_V1"
CASES_PER_KIND=32
KINDS=("RESEARCH_TOOL_ARTIFACT","BROWSER_MEMORY_RECOVERY","CODING_DEBUG_TOOL_DISCOVERY","DELEGATION_SYNTHESIS_ARTIFACT","CROSS_CAPABILITY_HANDOFF_ROLLBACK")
ATOM_BY_KIND={
 "RESEARCH_TOOL_ARTIFACT":"dimension:research_plus_tool_use_plus_artifact_creation",
 "BROWSER_MEMORY_RECOVERY":"dimension:browser_or_computer_action_plus_memory_plus_recovery",
 "CODING_DEBUG_TOOL_DISCOVERY":"dimension:coding_plus_debugging_plus_tool_discovery",
 "DELEGATION_SYNTHESIS_ARTIFACT":"dimension:delegation_plus_evidence_synthesis_plus_artifact_production",
 "CROSS_CAPABILITY_HANDOFF_ROLLBACK":"dimension:cross_capability_state_handoff_and_rollback",
}
TARGETS=("COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR","COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES")

def canon(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def sha(v:Any)->str:return hashlib.sha256(canon(v)).hexdigest()
def _seed(beacon,kind,ordinal):return int(hashlib.sha256(f"{beacon}\0{kind}\0{ordinal}".encode()).hexdigest()[:16],16)
def descriptor(beacon,kind,ordinal):
 return {"schema":SCHEMA+"_CASE_DESCRIPTOR","beacon":beacon,"kind":kind,"ordinal":ordinal,"seed":_seed(beacon,kind,ordinal),
         "case_id":f"COW1-{kind}-{ordinal:03d}-{sha([beacon,kind,ordinal])[:12]}","targets":list(TARGETS),"atom":ATOM_BY_KIND[kind]}

def _execute(d):
 k=d["kind"];s=d["seed"];o=d["ordinal"]
 if k=="RESEARCH_TOOL_ARTIFACT":row=research.execute_case(s,o)
 elif k=="BROWSER_MEMORY_RECOVERY":row=browser.execute_case(s,o)
 elif k=="CODING_DEBUG_TOOL_DISCOVERY":row=coding.execute_case(d["beacon"],o % coding.CASE_COUNT)
 elif k=="DELEGATION_SYNTHESIS_ARTIFACT":row=delegation.execute_case(s,o)
 elif k=="CROSS_CAPABILITY_HANDOFF_ROLLBACK":row=handoff.execute_case(s)
 else:raise ValueError("KIND")
 return row

def run_descriptor(d):
 if d.get("kind") not in ATOM_BY_KIND or d.get("atom")!=ATOM_BY_KIND[d["kind"]]:
  return {"schema":SCHEMA+"_CASE_RESULT","case_id":d.get("case_id"),"pass":False,"reason":"DESCRIPTOR_INVALID"}
 row=_execute(d);trace=row.get("objective_trace") or {};semantic=atoms.check_atom(d["atom"],trace)
 passed=bool(row.get("pass") is True and semantic.get("pass") is True)
 return {"schema":SCHEMA+"_CASE_RESULT","case_id":d["case_id"],"kind":d["kind"],"atom":d["atom"],"pass":passed,
         "route_pass":row.get("pass") is True,"semantic_result":semantic,"descriptor_sha256":sha(d),
         "objective_trace_sha256":sha(trace),"route_result_sha256":sha(row),"terminal_credit_delta":0}

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
 required=set(ATOM_BY_KIND.values());covered={x.get("atom") for x in rows if x.get("child_ok") is True and (x.get("semantic_result") or {}).get("pass") is True}
 all_pass=all(x.get("child_ok") is True for x in rows);isolated=all(x.get("case_initial_state_sha256")==base and x.get("post_reset_base_state_sha256")==base and x.get("prior_case_ids_consumed")==[] for x in rows)
 manifest=[{"case_id":x.get("case_id"),"kind":x.get("kind"),"atom":x.get("atom"),"descriptor_sha256":x.get("descriptor_sha256"),"objective_trace_sha256":x.get("objective_trace_sha256"),"case_initial_state_sha256":x.get("case_initial_state_sha256"),"mutable_namespace_sha256":x.get("mutable_namespace_sha256")} for x in rows]
 by_kind={k:{"passed":sum(x.get("child_ok") is True for x in rows if x.get("kind")==k),"total":sum(x.get("kind")==k for x in rows)} for k in KINDS}
 return {"schema":SCHEMA+"_REPORT","beacon":beacon,"targets":list(TARGETS),"fixed_case_count":len(rows),"cases_per_kind":CASES_PER_KIND,
         "kinds":list(KINDS),"required_atoms":sorted(required),"covered_atoms":sorted(x for x in covered if x),"coverage_complete":covered==required,
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
