#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata

ROOT=pathlib.Path(__file__).resolve().parent
TASK="canonical/tasks/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json"
MISSION="canonical/astra_runtime/missions/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json"
RUNTIME="canonical/runtime/astra_runtime.py"
AUTH="canonical/action_intents/2026-09-30_EXECUTE_GUARDED_HTTP2_PARENT_TASK_A_V1.json"
PLAN="guarded_http2_parent_task_a_plan.json"

def sha256_file(rel):
    return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()

mission=json.loads((ROOT/MISSION).read_text(encoding="utf-8"))
goal=str(mission["goal"])
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
problem_sha256=hashlib.sha256(("goal_text_v1\0"+norm).encode("utf-8")).hexdigest()

plan={
  "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
  "goal_text":goal,
  "frozen":{
    "gate_id":"BRAIN-PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-20260930-003-V1",
    "problem_sha256":problem_sha256,
    "task_sha256":sha256_file(TASK),
    "runtime_sha256":sha256_file(RUNTIME),
    "canonical_base":"f0f87c981d77b552caa21844e6bcc7b83116f339",
    "authorization_sha256":sha256_file(AUTH)
  },
  "pinned_files":[
  {
    "path": "canonical/tasks/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json",
    "git_blob_sha1": "539cadd30e7e8ac548638157b7f36a1814b97dcd"
  },
  {
    "path": "canonical/astra_runtime/missions/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json",
    "git_blob_sha1": "fac316bc6d273bf84e06843a6850d358fd3a2e56"
  },
  {
    "path": "canonical/runtime/astra_runtime.py",
    "git_blob_sha1": "e60345e3814deacc5b79ffd7fcf713febfee0425"
  },
  {
    "path": "canonical/action_intents/2026-09-30_EXECUTE_GUARDED_HTTP2_PARENT_TASK_A_V1.json",
    "git_blob_sha1": "0fd94d0b522053161a99da66265d375da5a3aa6c"
  },
  {
    "path": "execution_guard/github_actions_guarded_run_live.py",
    "git_blob_sha1": "30ea2fd2cc548444477c7b234a59129ff8386235"
  },
  {
    "path": "execution_guard/actions_admission.py",
    "git_blob_sha1": "6c46abef66c036f5382d5792b11a82a289b4dd94"
  },
  {
    "path": "execution_guard/github_ref_store_live.py",
    "git_blob_sha1": "a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"
  },
  {
    "path": "run_guarded_http2_parent_task_once.py",
    "git_blob_sha1": "4fc72237ef53aa958805fab81ab5585517e339d9"
  }
],
  "command":["bash","-lc","ASTRA_DISABLE_MODEL_PLANNER=1 python run_guarded_http2_parent_task_once.py"],
  "authority":{
    "brain_pr_freeze":455,
    "brain_pr_lease":458,
    "brain_action_intent":"canonical/action_intents/2026-09-30_EXECUTE_GUARDED_HTTP2_PARENT_TASK_A_V1.json",
    "prior_unguarded_pr":456,
    "prior_unguarded_evidence_authority":"PRESTART_REJECTED__EXECUTION_COUNT_0"
  }
}
(ROOT/PLAN).write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":problem_sha256,"task_sha256":plan["frozen"]["task_sha256"],"runtime_sha256":plan["frozen"]["runtime_sha256"],"authorization_sha256":plan["frozen"]["authorization_sha256"]},sort_keys=True))
