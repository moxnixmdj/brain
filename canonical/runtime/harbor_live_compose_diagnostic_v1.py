"""Live, non-authorizing Docker Compose diagnostic for pinned Harbor.

This calls the real Harbor DockerEnvironment's Compose ``ps`` and Docker
``inspect`` using the same Docker runtime and environment. Identity is sampled
before and after inspection, not atomically bound to a later exec. It cannot
prove egress, quiescence, verifier independence, or configuration permanence.
The owner-opted experimental path uses this as a configuration filter, not as
proof. No task command is executed by this diagnostic.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from canonical.runtime.harbor_docker_inspect_diagnostic_v1 import diagnose

_ID = re.compile(r"[0-9a-f]{64}\Z")
_MAX_INSPECT = 2_000_000


class ComposeDiagnosticError(RuntimeError):
    pass


def parse_single_id(output: Any) -> str:
    if not isinstance(output, str):
        raise ComposeDiagnosticError("COMPOSE_PS_OUTPUT_INVALID")
    lines = output.splitlines()
    if len(lines) != 1 or not _ID.fullmatch(lines[0]):
        raise ComposeDiagnosticError("COMPOSE_MAIN_CONTAINER_COUNT_OR_ID_INVALID")
    return lines[0]


def compose_labels_match(inspect: Any, *, project: str, service: str) -> bool:
    if not isinstance(inspect, list) or len(inspect) != 1 or not isinstance(inspect[0], dict):
        return False
    config = inspect[0].get("Config")
    labels = config.get("Labels") if isinstance(config, dict) else None
    return (isinstance(labels, dict) and labels.get("com.docker.compose.project") == project
            and labels.get("com.docker.compose.service") == service)


def _real_directory(value: Any) -> str:
    try:
        path = Path(value).resolve(strict=True)
        if not path.is_dir() or str(path) == "/":
            raise ValueError("invalid directory")
        return str(path)
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        raise ComposeDiagnosticError("HOST_DIRECTORY_INVALID") from exc


def _read_inspect(command: list[str], env: dict[str, str], *, timeout: float = 15) -> bytes:
    """Use the runtime's mediated subprocess entry point, off the event loop."""
    try:
        process = subprocess.run(command, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ComposeDiagnosticError("DOCKER_INSPECT_TIMEOUT") from exc
    except OSError as exc:
        raise ComposeDiagnosticError("DOCKER_INSPECT_UNAVAILABLE") from exc
    if process.returncode != 0 or len(process.stdout) > _MAX_INSPECT:
        raise ComposeDiagnosticError("DOCKER_INSPECT_FAILED_OR_TOO_LARGE")
    return process.stdout


async def inspect_compose_environment(environment: Any, *, brain_source: str) -> dict[str, Any]:
    """Sample the active Harbor Compose main container; do not authorize it.

    Requires pinned Harbor and Docker on the host. Only exact standard log
    source paths, derived from the environment's trial paths, may be mounted.
    Rejects extra mounts. Docker inspect may be task-influenced; do not log its
    raw document or use this as a trusted boundary or verifier result.
    """
    try:
        from harbor.constants import MAIN_SERVICE_NAME
        from harbor.environments.docker.docker import DockerEnvironment, _sanitize_docker_compose_project_name
    except ImportError as exc:
        raise ComposeDiagnosticError("PINNED_HARBOR_DOCKER_UNAVAILABLE") from exc
    if type(environment) is not DockerEnvironment or MAIN_SERVICE_NAME != "main":
        raise ComposeDiagnosticError("UNSUPPORTED_HARBOR_ENVIRONMENT")

    brain = _real_directory(brain_source)
    paths = environment.trial_paths
    expected_by_target = {
        "/logs/agent": paths.agent_dir,
        "/logs/verifier": paths.verifier_dir,
        "/logs/artifacts": paths.host_artifact_path(MAIN_SERVICE_NAME, "/logs/artifacts"),
    }
    logs: dict[str, str] = {}
    configured_mounts = environment._host_mounts
    if not isinstance(configured_mounts, list):
        raise ComposeDiagnosticError("HOST_MOUNTS_INVALID")
    for item in configured_mounts:
        if not isinstance(item, dict):
            raise ComposeDiagnosticError("HOST_MOUNT_INVALID")
        target = item.get("target")
        if target == "/opt/brain-ro":
            continue  # inspect checks exact source and actual read-only mode
        if not isinstance(target, str) or target not in expected_by_target or target in logs or item.get("type") != "bind":
            raise ComposeDiagnosticError("UNEXPECTED_HOST_MOUNT")
        actual = _real_directory(item.get("source"))
        expected = _real_directory(expected_by_target[target])
        if actual != expected:
            raise ComposeDiagnosticError("HARBOR_LOG_SOURCE_MISMATCH")
        logs[target] = expected

    async def get_id() -> str:
        result = await environment._run_docker_compose_command(
            ["ps", "--all", "--quiet", "--no-trunc", MAIN_SERVICE_NAME],
            check=False, timeout_sec=15)
        if result.return_code != 0:
            raise ComposeDiagnosticError("COMPOSE_PS_FAILED")
        return parse_single_id(result.stdout)

    before = await get_id()
    runtime = type(environment).runtime()
    # Cancellation of this coroutine cannot stop the thread immediately;
    # subprocess.run still kills and reaps the inspect command on its timeout.
    stdout = await asyncio.to_thread(_read_inspect, runtime.engine_cmd("inspect", before),
                                     environment._compose_env_vars(include_os_env=True))
    try:
        document = json.loads(stdout)
    except (ValueError, UnicodeError) as exc:
        raise ComposeDiagnosticError("DOCKER_INSPECT_INVALID_JSON") from exc
    after = await get_id()
    if before != after:
        raise ComposeDiagnosticError("COMPOSE_CONTAINER_CHANGED_DURING_INSPECTION")
    project = _sanitize_docker_compose_project_name(environment.session_id)
    if not compose_labels_match(document, project=project, service=MAIN_SERVICE_NAME):
        raise ComposeDiagnosticError("COMPOSE_LABELS_MISMATCH")
    result = diagnose(document, expected_id=before, expected_brain_source=brain,
                      expected_log_sources=logs)
    result.update({
        "compose_main_container_id": before,
        "host_log_mount_destinations": sorted(logs),
        "compose_identity_sampled_before_and_after": True,
        "compose_exec_atomically_bound": False,
        "execution_authorized": False,
        "verifier_independence_verified": False,
    })
    return result
