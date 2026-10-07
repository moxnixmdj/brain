from __future__ import annotations

import argparse
import json
import pathlib

from canonical.runtime import continuity_root3_inprocess_executor_v1 as adapter
from canonical.runtime import same_identity_supervisor_credited_v1 as supervisor

SCHEMA="PROJECT_BRAIN_CONTINUITY_ROOT3_FIXED_ENTRY_V2"
ROOT=supervisor.ROOT.resolve()
TASKS_DIR=ROOT/"canonical/same_identity_worker/tasks"
STATE_DIR=ROOT/"canonical/same_identity_worker/state"
EVIDENCE_DIR=ROOT/"canonical/same_identity_worker/evidence"

def _task_path(raw: str | None) -> pathlib.Path | None:
    if raw is None:
        return None
    path=supervisor._repo_path(ROOT,raw)
    tasks_root=TASKS_DIR.resolve()
    try:
        path.resolve().relative_to(tasks_root)
    except ValueError as exc:
        raise supervisor.SupervisorError("TASK_PATH_OUTSIDE_CANONICAL_TASK_QUEUE") from exc
    if path.suffix.lower()!=".json":
        raise supervisor.SupervisorError("TASK_PATH_NOT_JSON")
    return path

def run(task: str | None = None):
    return adapter.run_once(
        root=ROOT,
        tasks_dir=TASKS_DIR,
        state_dir=STATE_DIR,
        evidence_dir=EVIDENCE_DIR,
        agent_id=supervisor.DEFAULT_AGENT_ID,
        task_path=_task_path(task),
    )

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--task")
    args=parser.parse_args(argv)
    try:
        code,receipt=run(args.task)
    except supervisor.NoCausallyReadyTask as exc:
        print(json.dumps({"status":"NO_CAUSALLY_READY_TASK","error":str(exc)}))
        return 20
    except supervisor.TaskAlreadyTerminal as exc:
        print(json.dumps({"status":"TASK_ALREADY_TERMINAL","terminal_state":str(exc)}))
        return 21
    except (supervisor.SupervisorError, adapter.ContinuityRoot3Error) as exc:
        print(json.dumps({"status":"CONTINUITY_ROOT3_BLOCKED","error":str(exc)}))
        return 22
    print(json.dumps({
        **receipt,
        "deployment_entry_schema":SCHEMA,
        "fixed_root":str(ROOT),
        "fixed_tasks_dir":str(TASKS_DIR),
        "fixed_state_dir":str(STATE_DIR),
        "fixed_evidence_dir":str(EVIDENCE_DIR),
    },sort_keys=True))
    return int(code)

if __name__=="__main__":
    raise SystemExit(main())
