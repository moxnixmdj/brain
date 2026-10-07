from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import pathlib
import sys
from typing import Any, Mapping

from canonical.runtime import same_identity_supervisor_credited_v1 as supervisor
from canonical.runtime import root3_production_astra_launcher_v1 as root3_launcher

SCHEMA = "PROJECT_BRAIN_CONTINUITY_ROOT3_INPROCESS_EXECUTOR_V1"
EXPECTED_REQUESTED_RUNTIME = "canonical/runtime/astra_runtime.py"

class ContinuityRoot3Error(RuntimeError):
    pass

@contextlib.contextmanager
def _bound_process_context(cwd: pathlib.Path, env: Mapping[str, str]):
    old_cwd = pathlib.Path.cwd()
    old_env = dict(os.environ)
    try:
        os.chdir(cwd)
        os.environ.clear()
        os.environ.update({str(k): str(v) for k, v in env.items()})
        yield
    finally:
        os.chdir(old_cwd)
        os.environ.clear()
        os.environ.update(old_env)

def execute(
    requested_argv: list[str],
    cwd: pathlib.Path,
    env: dict[str, str],
) -> supervisor.RuntimeResult:
    if not isinstance(requested_argv, list) or len(requested_argv) != 3:
        raise ContinuityRoot3Error("REQUESTED_COMMAND_SHAPE_INVALID")
    if requested_argv[1] != EXPECTED_REQUESTED_RUNTIME:
        raise ContinuityRoot3Error("REQUESTED_RUNTIME_NOT_BOUND_ASTRA")
    mission = str(requested_argv[2])
    if not mission or mission.startswith("/") or ".." in pathlib.PurePosixPath(mission).parts:
        raise ContinuityRoot3Error("MISSION_PATH_INVALID")
    if not env.get("PROJECT_BRAIN_AGENT_ID") or not env.get("PROJECT_BRAIN_TASK_ID"):
        raise ContinuityRoot3Error("CONTINUITY_IDENTITY_ENV_MISSING")

    stdout = io.StringIO()
    stderr = io.StringIO()
    with _bound_process_context(pathlib.Path(cwd), env):
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = int(root3_launcher.main([mission]) or 0)
    return supervisor.RuntimeResult(code, stdout.getvalue(), stderr.getvalue())

def run_once(
    *,
    root: pathlib.Path,
    tasks_dir: pathlib.Path,
    state_dir: pathlib.Path,
    evidence_dir: pathlib.Path,
    agent_id: str = supervisor.DEFAULT_AGENT_ID,
    task_path: pathlib.Path | None = None,
):
    return supervisor.run_once(
        root=root,
        tasks_dir=tasks_dir,
        state_dir=state_dir,
        evidence_dir=evidence_dir,
        agent_id=agent_id,
        task_path=task_path,
        executor=execute,
    )

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(supervisor.ROOT))
    parser.add_argument("--tasks-dir", default="canonical/same_identity_worker/tasks")
    parser.add_argument("--state-dir", default="canonical/same_identity_worker/state")
    parser.add_argument("--evidence-dir", default="canonical/same_identity_worker/evidence")
    parser.add_argument("--agent-id", default=supervisor.DEFAULT_AGENT_ID)
    parser.add_argument("--task")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    tasks_dir = supervisor._repo_path(root, args.tasks_dir)
    state_dir = supervisor._repo_path(root, args.state_dir)
    evidence_dir = supervisor._repo_path(root, args.evidence_dir)
    task_path = supervisor._repo_path(root, args.task) if args.task else None
    try:
        code, receipt = run_once(
            root=root,
            tasks_dir=tasks_dir,
            state_dir=state_dir,
            evidence_dir=evidence_dir,
            agent_id=args.agent_id,
            task_path=task_path,
        )
    except supervisor.NoCausallyReadyTask as exc:
        print(json.dumps({"status":"NO_CAUSALLY_READY_TASK","error":str(exc)}))
        return 20
    except supervisor.TaskAlreadyTerminal as exc:
        print(json.dumps({"status":"TASK_ALREADY_TERMINAL","terminal_state":str(exc)}))
        return 21
    except (supervisor.SupervisorError, ContinuityRoot3Error) as exc:
        print(json.dumps({"status":"CONTINUITY_ROOT3_BLOCKED","error":str(exc)}))
        return 22
    print(json.dumps({
        **receipt,
        "deployment_executor_schema": SCHEMA,
        "deployment_executor": "IN_PROCESS_ROOT3_PRODUCTION_ASTRA_LAUNCHER_V1",
    }, sort_keys=True))
    return int(code)

if __name__ == "__main__":
    raise SystemExit(main())
