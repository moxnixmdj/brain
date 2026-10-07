from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import pathlib
import sys
from typing import Mapping

from canonical.runtime import same_identity_supervisor_credited_v1 as supervisor
from canonical.runtime import root3_production_astra_launcher_v1 as root3_launcher

SCHEMA = "PROJECT_BRAIN_CONTINUITY_ROOT3_INPROCESS_EXECUTOR_V1"
DEPLOYMENT_RECEIPT_SCHEMA = "PROJECT_BRAIN_CONTINUITY_ROOT3_DEPLOYMENT_RECEIPT_V1"
EXPECTED_REQUESTED_RUNTIME = "canonical/runtime/astra_runtime.py"
MODULE_ROOT = pathlib.Path(__file__).resolve().parents[2]

EXPECTED_DEPENDENCY_BLOBS = {
    "canonical/runtime/same_identity_supervisor_credited_v1.py": "47c461f502e840def0c38728e1bfd7c6401cb804",
    "canonical/runtime/root3_production_astra_launcher_v1.py": "3ac42e7be5a391cfda738131ecb0d3d600fa2147",
    "canonical/runtime/root3_strict_current_bootstrap_v2.py": "7d6e4f4e00fda4eae6ff1974f68f970ceee69c2e",
    "canonical/runtime/root3_two_class_attempt_authorizer_v1.py": "5aac8664433115c47d24e0fbbca15b81126753ee",
    "canonical/runtime/root3_subprocess_mediator_v2.py": "80560cdfa91c11a4b47b9ee2161af726b2f9bccf",
    "canonical/runtime/root3_read_only_local_file_query_executor_v1.py": "74166a80c47ed8ddce7bae7b61a3a3610ac2ef8a",
    "canonical/runtime/root3_pdf_raster_temp_executor_v1.py": "c07c632ac43e591bdde139f3440bdbe288ea930c",
    "canonical/runtime/zero_ambient_namespace_launcher_v1.py": "6e687527e9c4da82fb5d974a729aaa263ee73ea8",
    "canonical/runtime/root3_child_process_channel_registry_v1.py": "fc737c1ff5d767d590a5ac52b604890f5d22b1c5",
    "canonical/runtime/root3_subprocess_callsite_classifier_v1.py": "e654b264096dba724d82f04e5adef0dc6d6c90f7",
    "canonical/runtime/root3_subprocess_effect_class_registry_v1.py": "24e00a3e6b70d0879cab664a8512f243973c6196",
    "canonical/runtime/astra_runtime.py": "3567cfd77eae06e2d384c5e0b18972b2d3a62c3b",
}


class ContinuityRoot3Error(RuntimeError):
    pass


def _git_blob_sha(raw: bytes) -> str:
    header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
    return hashlib.sha1(header + raw).hexdigest()


def _verify_dependency_blobs(root: pathlib.Path = MODULE_ROOT) -> dict[str, str]:
    observed: dict[str, str] = {}
    for rel, expected in EXPECTED_DEPENDENCY_BLOBS.items():
        path = root / rel
        if not path.is_file():
            raise ContinuityRoot3Error("DEPENDENCY_MISSING:" + rel)
        actual = _git_blob_sha(path.read_bytes())
        observed[rel] = actual
        if actual != expected:
            raise ContinuityRoot3Error(
                f"DEPENDENCY_BLOB_DRIFT:{rel}:{actual}:expected:{expected}"
            )
    return observed


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

    _verify_dependency_blobs()

    stdout = io.StringIO()
    stderr = io.StringIO()
    with _bound_process_context(pathlib.Path(cwd), env):
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = int(root3_launcher.main([mission]) or 0)
    return supervisor.RuntimeResult(code, stdout.getvalue(), stderr.getvalue())


def _deployment_receipt(
    *,
    root: pathlib.Path,
    evidence_dir: pathlib.Path,
    receipt: dict,
) -> tuple[dict, pathlib.Path]:
    task_id = str(receipt.get("task_id") or "").strip()
    attempt = int(receipt.get("runtime_attempt_count", 0))
    if not task_id or attempt <= 0:
        raise ContinuityRoot3Error("DEPLOYMENT_RECEIPT_BINDING_INVALID")

    observed = _verify_dependency_blobs()
    out = {
        "schema": DEPLOYMENT_RECEIPT_SCHEMA,
        "task_id": task_id,
        "task_sha256": receipt.get("task_sha256"),
        "mission_path": receipt.get("mission_path"),
        "mission_sha256": receipt.get("mission_sha256"),
        "runtime_attempt_count": attempt,
        "requested_runtime_command": receipt.get("runtime_command"),
        "actual_executor": "IN_PROCESS_ROOT3_PRODUCTION_ASTRA_LAUNCHER_V1",
        "adapter_path": "canonical/runtime/continuity_root3_inprocess_executor_v1.py",
        "adapter_git_blob_sha": _git_blob_sha(pathlib.Path(__file__).read_bytes()),
        "root3_launcher_path": "canonical/runtime/root3_production_astra_launcher_v1.py",
        "dependency_git_blobs": observed,
        "same_identity_bound": receipt.get("same_identity_bound") is True,
        "terminal_state": receipt.get("terminal_state"),
        "incremental_spend_usd": receipt.get("incremental_spend_usd", 0),
        "promotion_claim": False,
        "p_real_claim": 0,
    }
    path = evidence_dir / f"{task_id}__DEPLOYMENT_{attempt}.json"
    supervisor._write_json_atomic(path, out)
    return out, path


def run_once(
    *,
    root: pathlib.Path,
    tasks_dir: pathlib.Path,
    state_dir: pathlib.Path,
    evidence_dir: pathlib.Path,
    agent_id: str = supervisor.DEFAULT_AGENT_ID,
    task_path: pathlib.Path | None = None,
):
    code, receipt = supervisor.run_once(
        root=root,
        tasks_dir=tasks_dir,
        state_dir=state_dir,
        evidence_dir=evidence_dir,
        agent_id=agent_id,
        task_path=task_path,
        executor=execute,
    )
    if "runtime_command" not in receipt:
        return code, receipt

    deployment, path = _deployment_receipt(
        root=root,
        evidence_dir=evidence_dir,
        receipt=receipt,
    )
    enriched = dict(receipt)
    try:
        enriched["deployment_receipt_path"] = str(path.relative_to(root))
    except ValueError:
        enriched["deployment_receipt_path"] = str(path)
    enriched["deployment_executor"] = deployment["actual_executor"]
    enriched["deployment_adapter_git_blob_sha"] = deployment["adapter_git_blob_sha"]
    return code, enriched


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
        print(json.dumps({"status": "NO_CAUSALLY_READY_TASK", "error": str(exc)}))
        return 20
    except supervisor.TaskAlreadyTerminal as exc:
        print(json.dumps({"status": "TASK_ALREADY_TERMINAL", "terminal_state": str(exc)}))
        return 21
    except (supervisor.SupervisorError, ContinuityRoot3Error) as exc:
        print(json.dumps({"status": "CONTINUITY_ROOT3_BLOCKED", "error": str(exc)}))
        return 22
    print(json.dumps({
        **receipt,
        "deployment_executor_schema": SCHEMA,
    }, sort_keys=True))
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
