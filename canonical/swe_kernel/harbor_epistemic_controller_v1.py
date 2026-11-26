"""Harbor Epistemic Cycle Controller (`model_calls == 0`, `parameters_stored == 0`).

Authority: PROJECT_BRAIN_HARBOR_EPISTEMIC_CONTROLLER_V1

Produces bounded, command-policy-validated `terminal_exec` and `finish` proposals
for `harbor_epistemic_agent_v1.py` envelopes (`{"harbor_task", "cycle", "observations"}`)
when invoked through `open_model().solve(...)` inside a confined Harbor task container.
Never claims verified task completion (`task_completion_claimed == False`); only
the external benchmark verifier decides outcomes.
"""
from __future__ import annotations

import base64
import json
import re
import shlex
from typing import Any, Mapping

from canonical.runtime.harbor_command_policy import validate_environment_command

SCHEMA = "PROJECT_BRAIN_HARBOR_EPISTEMIC_CONTROLLER_V1"
CAPABILITY_ID = "swe.harbor.epistemic_cycle.v1"
RUNNER_SCRIPT = "/opt/brain-ro/canonical/swe_kernel/harbor_in_container_runner_v1.py"


def is_harbor_epistemic_envelope(inputs: Mapping[str, Any] | None) -> bool:
    if not isinstance(inputs, Mapping):
        return False
    return (
        isinstance(inputs.get("harbor_task"), str)
        and bool(str(inputs.get("harbor_task")).strip())
        and type(inputs.get("cycle")) is int
        and isinstance(inputs.get("observations"), list)
        and inputs["cycle"] == 1 + len(inputs["observations"])
        and all(isinstance(obs, Mapping) for obs in inputs["observations"])
    )


def _parse_last_json(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        s = line.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    return parsed
            except ValueError:
                continue
    return {}


def solve_harbor_cycle(
    goal: str,
    *,
    inputs: Mapping[str, Any],
    model_digest: str = "",
) -> dict[str, Any]:
    """Deterministic zero-LLM Harbor cycle proposal generator."""
    harbor_task = str(inputs.get("harbor_task") or "").strip()
    try:
        cycle = int(inputs.get("cycle") or 1)
    except (TypeError, ValueError):
        cycle = 1
    observations = list(inputs.get("observations") or [])

    if not harbor_task:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "HARBOR_TASK_EMPTY",
            "model_digest": model_digest,
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # Cycle 1: Environment tomography + candidate test target discovery
    if cycle <= 1 or len(observations) == 0:
        clipped_task = harbor_task[:2400].encode("utf-8", errors="ignore")
        b64_task = base64.b64encode(clipped_task).decode("ascii")
        raw_cmd = (
            "env -i PATH=/opt/miniconda3/envs/testbed/bin:/opt/conda/envs/testbed/bin:"
            "/usr/local/bin:/usr/bin:/bin HOME=/tmp "
            f"python3 -I -B {RUNNER_SCRIPT} --phase discover --instruction-b64 {shlex.quote(b64_task)}"
        )
        safe_cmd = validate_environment_command(raw_cmd)
        return {
            "schema": SCHEMA,
            "operation": "SOLVE",
            "pass": True,
            "status": "PASS__HARBOR_EPISTEMIC_PROPOSAL",
            "capability_id": CAPABILITY_ID,
            "model_digest": model_digest,
            "task_completion_claimed": False,
            "verified_by_agent": False,
            "model_calls": 0,
            "parameters_stored": 0,
            "actions": [
                {
                    "type": "terminal_exec",
                    "args": {"command": safe_cmd, "timeout_sec": 120},
                }
            ],
        }

    # Cycle 2: Autonomous causal localization + CoW mental CEGIS + full-suite referee
    if len(observations) == 1 and cycle <= 7:
        last_obs = observations[-1] if isinstance(observations[-1], Mapping) else {}
        disc = _parse_last_json(str(last_obs.get("stdout") or ""))
        ecosystems = disc.get("ecosystems") if isinstance(disc.get("ecosystems"), Mapping) else {}
        ranked_tests = disc.get("ranked_tests") if isinstance(disc.get("ranked_tests"), list) else []
        if ecosystems.get("python"):
            raw_cmd = (
                "env -i PATH=/opt/miniconda3/envs/testbed/bin:/opt/conda/envs/testbed/bin:"
                "/usr/local/bin:/usr/bin:/bin HOME=/tmp "
                f"python3 -I -B -W ignore {RUNNER_SCRIPT} --phase repair --timeout-s 80"
            )
            safe_cmd = validate_environment_command(raw_cmd)
            return {
                "schema": SCHEMA,
                "operation": "SOLVE",
                "pass": True,
                "status": "PASS__HARBOR_EPISTEMIC_PROPOSAL",
                "capability_id": CAPABILITY_ID,
                "model_digest": model_digest,
                "task_completion_claimed": False,
                "verified_by_agent": False,
                "model_calls": 0,
                "parameters_stored": 0,
                "actions": [
                    {
                        "type": "terminal_exec",
                        "args": {"command": safe_cmd, "timeout_sec": 180},
                    }
                ],
            }
        summary = (
            f"Epistemic tomography completed (ecosystems={dict(ecosystems)}, "
            f"python_tests={len(ranked_tests)}); deferring candidate judgment to external Harbor verifier."
        )
        return {
            "schema": SCHEMA,
            "operation": "SOLVE",
            "pass": True,
            "status": "PASS__HARBOR_EPISTEMIC_PROPOSAL",
            "capability_id": CAPABILITY_ID,
            "model_digest": model_digest,
            "task_completion_claimed": False,
            "verified_by_agent": False,
            "model_calls": 0,
            "parameters_stored": 0,
            "actions": [{"type": "finish", "args": {"summary": summary}}],
        }

    # Cycle >= 3: Finish cleanly after repair attempt so Harbor captures candidate patch & runs pristine replay
    last_obs = observations[-1] if isinstance(observations[-1], Mapping) else {}
    rep = _parse_last_json(str(last_obs.get("stdout") or ""))
    rep_status = str(rep.get("status") or "COMPLETED_TOMOGRAPHY")
    summary = (
        f"Unverified epistemic cycle finished (status={rep_status}, "
        f"repaired_file={rep.get('repaired_file')}, model_calls=0); external verifier decides."
    )
    return {
        "schema": SCHEMA,
        "operation": "SOLVE",
        "pass": True,
        "status": "PASS__HARBOR_EPISTEMIC_PROPOSAL",
        "capability_id": CAPABILITY_ID,
        "model_digest": model_digest,
        "task_completion_claimed": False,
        "verified_by_agent": False,
        "model_calls": 0,
        "parameters_stored": 0,
        "actions": [{"type": "finish", "args": {"summary": summary}}],
    }
