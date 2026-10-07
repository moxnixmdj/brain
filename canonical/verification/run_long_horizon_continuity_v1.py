#!/usr/bin/env python3
import hashlib, importlib.util, json, pathlib, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parents[2]
SUPERVISOR=ROOT/"canonical/runtime/same_identity_supervisor.py"
AGENT="SUPERWORKER-UNIFIED-1"
TASK_ID="OPUS55-LONG-HORIZON-CONTINUITY-FRESH-001"

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(pathlib.Path(p).read_bytes())
def canonical_json_sha(v):
    return sha_bytes(json.dumps(v,sort_keys=True,separators=(",",":")).encode())

def child_code(root, task_path, state_dir, evidence_dir, expect_checkpoint):
    return f"""
import importlib.util, pathlib, sys
p=pathlib.Path({str(SUPERVISOR)!r})
spec=importlib.util.spec_from_file_location("sis_child",p)
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
root=pathlib.Path({str(root)!r})
task_path=pathlib.Path({str(task_path)!r})
state=pathlib.Path({str(state_dir)!r})
evidence=pathlib.Path({str(evidence_dir)!r})
task,_=m.claim_task(root,task_path,state,{AGENT!r})
if {expect_checkpoint!r}:
    def never(*a,**k): raise AssertionError("runtime must not execute before checkpoint")
    code,receipt=m.execute_claimed_task(root,task,state,evidence,{AGENT!r},never)
    assert code==75 and receipt["status"]=="CHECKPOINTED_RELAUNCH_REQUIRED"
else:
    seen={{}}
    def ok(argv,cwd,env):
        seen["argv"]=list(argv)
        seen["agent"]=env.get("PROJECT_BRAIN_AGENT_ID")
        seen["task"]=env.get("PROJECT_BRAIN_TASK_ID")
        return m.RuntimeResult(0,"ok\\n","")
    code,receipt=m.execute_claimed_task(root,task,state,evidence,{AGENT!r},ok)
    assert code==0 and receipt["terminal_state"]=="COMPLETE"
    assert receipt["same_identity_bound"] is True
    assert seen["agent"]=={AGENT!r}
    assert seen["task"]=={TASK_ID!r}
    assert seen["argv"]==[sys.executable,"canonical/runtime/root3_production_astra_launcher_v1.py","canonical/missions/mission.json"]
print("PASS")
"""

def run_child(code):
    p=subprocess.run([sys.executable,"-c",code],cwd=ROOT,text=True,capture_output=True)
    if p.returncode!=0:
        raise SystemExit("child failed\nSTDOUT:\n"+p.stdout+"\nSTDERR:\n"+p.stderr)
    return {"returncode":p.returncode,"stdout_sha256":sha_bytes(p.stdout.encode()),"stderr_sha256":sha_bytes(p.stderr.encode())}

def main():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        (root/"canonical/missions").mkdir(parents=True)
        (root/"canonical/tasks").mkdir(parents=True)
        state=root/"canonical/state"
        evidence=root/"canonical/evidence"
        mission=root/"canonical/missions/mission.json"
        mission.write_text(json.dumps({"mission":"continuity-test"},sort_keys=True)+"\n",encoding="utf-8")
        task_path=root/"canonical/tasks/task.json"
        task={
            "schema":"PROJECT_BRAIN_SAME_IDENTITY_TASK_V1",
            "task_id":TASK_ID,
            "agent_id":AGENT,
            "incremental_spend_usd":0,
            "mission_path":"canonical/missions/mission.json",
            "mission_sha256":sha_file(mission),
            "priority":100,
            "prerequisites":[],
            "checkpoint_before_runtime_once":True,
        }
        task_path.write_text(json.dumps(task,indent=2,sort_keys=True)+"\n",encoding="utf-8")

        proc_a=run_child(child_code(root,task_path,state,evidence,True))
        proc_b=run_child(child_code(root,task_path,state,evidence,False))

        state_path=state/(TASK_ID+".json")
        final=json.loads(state_path.read_text())
        attempt=json.loads((evidence/(TASK_ID+"__ATTEMPT_1.json")).read_text())
        checkpoint=json.loads((evidence/(TASK_ID+"__CHECKPOINT.json")).read_text())
        events=[e["type"] for e in final["events"]]
        expected_events=["TASK_ACQUIRED","CHECKPOINT_CREATED","TASK_RESUMED","ASTRA_RUNTIME_STARTED","TASK_COMPLETE"]
        checks={
            "supervisor_blob_sha256":sha_file(SUPERVISOR),
            "agent_identity_preserved":final["agent_id"]==AGENT==attempt["agent_id"]==checkpoint["agent_id"],
            "task_identity_preserved":final["task_id"]==TASK_ID==attempt["task_id"]==checkpoint["task_id"],
            "task_manifest_hash_preserved":final["task_sha256"]==canonical_json_sha(task)==attempt["task_sha256"]==checkpoint["task_sha256"],
            "mission_hash_preserved":final["mission_sha256"]==task["mission_sha256"]==attempt["mission_sha256"]==checkpoint["mission_sha256"],
            "checkpoint_exactly_once":final["checkpoint_count"]==1 and attempt["checkpoint_count"]==1,
            "runtime_attempt_exactly_once":final["runtime_attempt_count"]==1 and attempt["runtime_attempt_count"]==1,
            "claim_count_two_processes":final["claim_count"]==2,
            "terminal_complete":final["status"]=="COMPLETE" and attempt["terminal_state"]=="COMPLETE",
            "same_identity_bound":attempt["same_identity_bound"] is True and checkpoint["same_identity_bound"] is True,
            "event_order_exact":events==expected_events,
            "no_promotion_claim":final["promotion_claim"] is False and attempt["promotion_claim"] is False,
            "zero_spend":attempt["incremental_spend_usd"]==0 and checkpoint["incremental_spend_usd"]==0,
        }
        report={
            "schema":"PROJECT_BRAIN_LONG_HORIZON_CONTINUITY_FRESH_VERIFICATION_V1",
            "capability":"LONG_HORIZON_MEMORY_AND_CONTINUITY",
            "scope":"DURABLE_CROSS_SESSION_STATE__CHECKPOINT_RELAUNCH__SAME_MISSION_RESUME_WITHOUT_DUPLICATE_COMPLETED_WORK",
            "process_a":proc_a,
            "process_b":proc_b,
            "process_c":"THIS_INDEPENDENT_LEDGER_RECOMPUTATION",
            "checks":checks,
            "all_pass":all(v if isinstance(v,bool) else True for k,v in checks.items()),
            "event_types":events,
            "incremental_spend_usd":0,
            "claim_limits":["NO_AUTONOMOUS_WAKE_CLAIM","NO_GENERAL_SEMANTIC_MEMORY_QUALITY_CLAIM","NO_GENERAL_COGNITION_CLAIM"],
        }
        out=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/"LONG_HORIZON_CONTINUITY_REPORT.json"
        out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps(report,indent=2,sort_keys=True))
        if not report["all_pass"]: raise SystemExit(1)

if __name__=="__main__":
    main()
