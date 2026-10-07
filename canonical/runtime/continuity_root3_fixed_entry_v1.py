from __future__ import annotations

import argparse
import json
import pathlib

from canonical.runtime import continuity_root3_inprocess_executor_v1 as adapter
from canonical.runtime import same_identity_supervisor_credited_v1 as supervisor

SCHEMA="PROJECT_BRAIN_CONTINUITY_ROOT3_FIXED_ENTRY_V2"
ROOT=supervisor.ROOT.resolve()

TASKS_REL="canonical/same_identity_worker/tasks"
STATE_REL="canonical/same_identity_worker/state"
EVIDENCE_REL="canonical/same_identity_worker/evidence"
BRIDGE_REL="canonical/same_identity_worker/external_tool_bridge"

def _fixed_repo_dir(rel: str) -> pathlib.Path:
    return supervisor._repo_path(ROOT, rel)

def _task_path(raw: str | None) -> pathlib.Path | None:
    if raw is None:
        return None
    return supervisor._repo_path(ROOT, raw)

def _bound_dirs() -> tuple[pathlib.Path,pathlib.Path,pathlib.Path,pathlib.Path]:
    # Resolve through the supervisor's repository-confinement primitive before
    # any continuity mutation. This rejects pre-existing base-prefix symlinks
    # that resolve outside the canonical repository.
    return (
        _fixed_repo_dir(TASKS_REL),
        _fixed_repo_dir(STATE_REL),
        _fixed_repo_dir(EVIDENCE_REL),
        _fixed_repo_dir(BRIDGE_REL),
    )

def run(task: str | None = None):
    tasks_dir,state_dir,evidence_dir,_bridge_base=_bound_dirs()
    return adapter.run_once(
        root=ROOT,
        tasks_dir=tasks_dir,
        state_dir=state_dir,
        evidence_dir=evidence_dir,
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
    tasks_dir,state_dir,evidence_dir,bridge_base=_bound_dirs()
    print(json.dumps({
        **receipt,
        "deployment_entry_schema":SCHEMA,
        "fixed_root":str(ROOT),
        "fixed_tasks_dir":str(tasks_dir),
        "fixed_state_dir":str(state_dir),
        "fixed_evidence_dir":str(evidence_dir),
        "fixed_bridge_dir":str(bridge_base),
    },sort_keys=True))
    return int(code)

if __name__=="__main__":
    raise SystemExit(main())
