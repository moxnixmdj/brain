#!/usr/bin/env python3
"""Execution — 8-stage argv pipeline, only-right-way composition without shell.

Hidden kernel: canonical/runtime/pipeline_exec_v1.py (188 lines, N argv-pipes,
allowlisted, no shell string, deadline-reaped, postcondition-checked).

Why max: shell strings cannot be allowlisted/promised/postcondition-checked.
Argv lists can. This is composition as N argvs piped via Popen, never a string
to sh — fail-closed, deterministic, parallel-ready, $0, 0 model.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_EXECUTION_PIPELINE_8STAGE_V1"
CAPABILITY_ID = "execution.pipeline.8stage.v1"
PROVIDES = ["execution.pipeline.completed", "execution.composition.shell_free"]
REQUIRES: list[str] = []

REPO = pathlib.Path(__file__).resolve().parents[3]

def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_pipeline_8stage.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _load_pipeline():
    import canonical.runtime.pipeline_exec_v1 as mod
    return mod

def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    pipe_mod = _load_pipeline()
    # No demo default: a pipeline verdict is about the caller's stages or nothing.
    stages = args.get("stages")
    if not stages or not isinstance(stages, list) or not all(isinstance(s, list) and s for s in stages):
        artifact = {"schema": SCHEMA, "capability_id": CAPABILITY_ID, "stages": stages,
                    "result": {"status": "STAGES_REQUIRED"}, "model_dependency_count": 0,
                    "incremental_spend_usd": 0, "verified": False}
        raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
        output.write_bytes(raw)
        return {"adapter": "execution_pipeline_8stage_v1", "output_path": str(output.relative_to(repo)),
                "output_sha256": hashlib.sha256(raw).hexdigest(), "output_verified": False,
                "verified": False, "reason": "STAGES_REQUIRED", "returncode": None,
                "model_dependency_count": 0, "incremental_spend_usd": 0}
    # hidden kernel is run_stages(argv_lists, cwd, timeout, max_bytes) — allowlist-checked in caller
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        code, out = pipe_mod.run_stages(stages, cwd=td, timeout=int(args.get("timeout_s", 10)))
        payload = {"returncode": code, "stdout": out.decode() if isinstance(out, bytes) else str(out)}
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
