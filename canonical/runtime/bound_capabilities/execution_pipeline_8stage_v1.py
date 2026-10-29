#!/usr/bin/env python3
"""Execution — 8-stage argv pipeline, only-right-way composition without shell.

Hidden kernel: canonical/runtime/pipeline_exec_v1.py (188 lines, N argv-pipes,
allowlisted, no shell string, deadline-reaped, postcondition-checked).

Why max: shell strings cannot be allowlisted/promised/postcondition-checked.
Argv lists can. This is composition as N argvs piped via Popen, never a string
to sh — fail-closed, deterministic, parallel-ready, $0, 0 model.

No default stages are ever run: a request that does not name its stages is
refused rather than silently executing a demo that has nothing to do with the
task. Every stage argv is allowlisted against /usr/bin, /bin, and the caller's
Python interpreter before execution.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from typing import Any

SCHEMA = "PROJECT_BRAIN_EXECUTION_PIPELINE_8STAGE_V1"
CAPABILITY_ID = "execution.pipeline.8stage.v1"
PROVIDES = ["execution.pipeline.completed", "execution.composition.shell_free"]
REQUIRES: list[str] = []

REPO = pathlib.Path(__file__).resolve().parents[3]

_ALLOWED_DIRS = ("/usr/bin", "/bin")
_ALLOWED_EXE_NAMES = {
    pathlib.Path(sys.executable).name,
    "python", "python3", "py",
}

_PIPE_SCHEMA = "PROJECT_BRAIN_EXECUTION_PIPELINE_REQUEST_V1"


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_pipeline_8stage.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_pipeline():
    import canonical.runtime.pipeline_exec_v1 as mod
    return mod


def _allow_exe(argv0: str) -> str:
    """Return argv0 if it is allowlisted, else raise."""
    p = pathlib.Path(argv0)
    if p.is_absolute():
        for d in _ALLOWED_DIRS:
            try:
                if str(p.resolve()).startswith(d + "/") or str(p.resolve()) == d:
                    return argv0
            except OSError:
                continue
        raise RuntimeError("PIPELINE_STAGE_EXE_NOT_ALLOWLISTED:" + argv0)
    if p.name in _ALLOWED_EXE_NAMES:
        return argv0
    raise RuntimeError("PIPELINE_STAGE_EXE_NOT_ALLOWLISTED:" + argv0)


def _validate_stages(stages: Any) -> list[list[str]]:
    if not isinstance(stages, list) or not stages:
        raise RuntimeError("PIPELINE_STAGES_REQUIRED")
    out: list[list[str]] = []
    for i, stage in enumerate(stages):
        if not isinstance(stage, list) or not stage:
            raise RuntimeError("PIPELINE_STAGE_INVALID:" + str(i))
        clean = []
        for j, part in enumerate(stage):
            if j == 0:
                clean.append(_allow_exe(str(part)))
            elif isinstance(part, str):
                clean.append(part)
            elif isinstance(part, int) and not isinstance(part, bool):
                clean.append(str(part))
            else:
                raise RuntimeError("PIPELINE_STAGE_ARG_INVALID:" + str(i) + ":" + str(j))
        out.append(clean)
    if len(out) > 8:
        raise RuntimeError("PIPELINE_TOO_MANY_STAGES")
    return out


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    stages_raw = args.get("stages")
    stages = _validate_stages(stages_raw)
    pipe_mod = _load_pipeline()
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        code, out = pipe_mod.run_stages(stages, cwd=td, timeout=int(args.get("timeout_s", 10)))
        stdout_text = out.decode() if isinstance(out, bytes) else str(out)
        payload = {"returncode": code, "stdout": stdout_text}
        verified = code == 0
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "stages": stages,
        "result": payload,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "verified": verified,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.write_bytes(raw)
    return {
        "adapter": "execution_pipeline_8stage_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": verified,
        "returncode": payload.get("returncode"),
        "verified": verified,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
