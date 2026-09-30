#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
TASK_ID="PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003"
MISSION="canonical/astra_runtime/missions/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json"
REPORT=ROOT/"http2-parent-task-terminal.json"
STATE=ROOT/"canonical/astra_runtime/state"/(TASK_ID+".json")

report={
  "schema":"PROJECT_BRAIN_GUARDED_PARENT_TASK_TERMINAL_V1",
  "task_id":TASK_ID,
  "task_executed":True,
  "execution_count":1,
  "replay_allowed":False,
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "entrypoint":"canonical/runtime/astra_runtime.py <canonical mission path>",
  "direct_goal_compiler_harness_used":False
}

env=os.environ.copy()
env["ASTRA_DISABLE_MODEL_PLANNER"]="1"
proc=subprocess.run(
  [sys.executable,"canonical/runtime/astra_runtime.py",MISSION],
  cwd=ROOT,text=True,capture_output=True,timeout=780,env=env
)
report["runtime_returncode"]=proc.returncode
report["runtime_stdout_tail"]=proc.stdout[-20000:]
report["runtime_stderr_tail"]=proc.stderr[-20000:]

if STATE.is_file():
    try:
        report["runtime_state"]=json.loads(STATE.read_text(encoding="utf-8"))
    except Exception as exc:
        report["runtime_state_parse_error"]=type(exc).__name__+":"+str(exc)

state=report.get("runtime_state")
if proc.returncode==0 and isinstance(state,dict) and state.get("status")=="COMPLETE":
    report["status"]="PRODUCER_SEMANTIC_COMPLETION_PENDING_INDEPENDENT_ORACLE"
    report["parent_capability_credit_authorized"]=False
    report["next_required_action"]="INDEPENDENT_ORACLE_ONLY__NO_REPLAY"
    code=0
else:
    blocker=(state or {}).get("blocker") if isinstance(state,dict) else None
    report["status"]="FAIL_FIRST_CAUSAL_GAP"
    report["first_causal_blocker"]=blocker or ("RUNTIME_RETURN_CODE_"+str(proc.returncode))
    report["parent_capability_credit_authorized"]=False
    report["next_required_action"]="RECONCILE_FIRST_CAUSAL_GAP__NO_REPLAY"
    code=2

REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(code)
