"""Zero-terminal-case Buildkite hosted-agent preflight for TB4.

This script validates only the execution substrate required by the already-frozen
TB4 route: CPU, RAM, disk, Docker daemon, and Docker Compose runtime. It does not
load, enumerate, execute, or score any Terminal-Bench task.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
from typing import Any


MIN_CPU = 8
MIN_RAM_BYTES = 16 * 1024**3
MIN_FREE_DISK_BYTES = 50 * 1024**3


def _run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _ram_total_bytes() -> int:
    meminfo = pathlib.Path("/proc/meminfo")
    if not meminfo.exists():
        return 0
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            return int(parts[1]) * 1024
    return 0


def _compose_smoke() -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="tb4-buildkite-preflight-") as td:
        compose = pathlib.Path(td) / "compose.yml"
        compose.write_text(
            """services:
  smoke:
    image: busybox:1.36.1
    command: [\"sh\", \"-c\", \"echo compose-ok\"]
""",
            encoding="utf-8",
        )
        up = _run(
            [
                "docker",
                "compose",
                "-f",
                str(compose),
                "up",
                "--abort-on-container-exit",
                "--exit-code-from",
                "smoke",
            ],
            cwd=td,
        )
        down = _run(["docker", "compose", "-f", str(compose), "down", "-v"], cwd=td)
        return (
            up.returncode == 0,
            {
                "up_returncode": up.returncode,
                "up_stdout_tail": up.stdout[-2000:],
                "up_stderr_tail": up.stderr[-2000:],
                "down_returncode": down.returncode,
            },
        )


def evaluate() -> dict[str, Any]:
    cpu = os.cpu_count() or 0
    ram = _ram_total_bytes()
    disk = shutil.disk_usage(pathlib.Path.cwd())

    docker_version = _run(["docker", "version", "--format", "{{.Server.Version}}"])
    compose_version = _run(["docker", "compose", "version", "--short"])
    docker_runtime = _run(
        [
            "docker",
            "run",
            "--rm",
            "--pull=always",
            "busybox:1.36.1",
            "sh",
            "-c",
            "echo docker-ok",
        ]
    )
    compose_ok, compose_detail = _compose_smoke()

    checks = {
        "buildkite_environment": bool(os.environ.get("BUILDKITE")),
        "cpu_ge_8": cpu >= MIN_CPU,
        "ram_ge_16_gib": ram >= MIN_RAM_BYTES,
        "free_disk_ge_50_gib": disk.free >= MIN_FREE_DISK_BYTES,
        "docker_server_available": docker_version.returncode == 0,
        "docker_container_runtime_pass": (
            docker_runtime.returncode == 0 and "docker-ok" in docker_runtime.stdout
        ),
        "docker_compose_cli_available": compose_version.returncode == 0,
        "docker_compose_runtime_pass": compose_ok,
    }
    passed = all(checks.values())

    return {
        "schema": "PROJECT_BRAIN_TB4_BUILDKITE_ZERO_CASE_PREFLIGHT_V1",
        "status": (
            "PASS__BUILDkite_HOSTED_SUBSTRATE_MEETS_TB4_PREFLIGHT"
            if passed
            else "FAIL_CLOSED__BUILDKITE_SUBSTRATE_PREFLIGHT"
        ),
        "pass": passed,
        "checks": checks,
        "observed": {
            "cpu_count": cpu,
            "ram_total_bytes": ram,
            "disk_total_bytes": disk.total,
            "disk_free_bytes": disk.free,
            "docker_server_version": docker_version.stdout.strip(),
            "docker_compose_version": compose_version.stdout.strip(),
            "docker_runtime_stdout": docker_runtime.stdout.strip(),
            "compose": compose_detail,
            "buildkite_build_id": os.environ.get("BUILDKITE_BUILD_ID"),
            "buildkite_job_id": os.environ.get("BUILDKITE_JOB_ID"),
            "buildkite_agent_meta_data_queue": os.environ.get(
                "BUILDKITE_AGENT_META_DATA_QUEUE"
            ),
        },
        "hard_nonclaims": [
            "NO_TB4_TASKS_LOADED_OR_EXECUTED",
            "NO_TB4_SCORE_OR_ACCEPTANCE_CREDIT",
            "BILLING_HARD_STOP_NOT_PROVED_BY_INSIDE_JOB_TELEMETRY",
            "TRIAL_ACCOUNT_OR_BILLING_STATE_REQUIRES_SEPARATE_ACCOUNT_RECEIPT",
        ],
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def main() -> int:
    out = evaluate()
    path = pathlib.Path("tb4_buildkite_zero_case_preflight_receipt.json")
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
