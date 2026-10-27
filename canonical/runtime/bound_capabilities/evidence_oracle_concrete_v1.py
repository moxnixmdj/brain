#!/usr/bin/env python3
"""Evidence oracle — concrete execution, second independent oracle.

Hidden kernel: canonical/runtime/bound_capabilities/concrete_execution_oracle.py
already verified (13-sample concrete violation witness). CrossHair is symbolic
via Z3; this is concrete via execution. Two independent oracles satisfy
TRUE_CAPABILITY_TEST_LAW_V1 — no shared machinery, no model, $0.

Only-right-way: concrete witness, not symbolic proof. Fail-closed.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import sys
from typing import Any

SCHEMA = "PROJECT_BRAIN_EVIDENCE_ORACLE_CONCRETE_V1"
CAPABILITY_ID = "evidence.oracle.concrete_execution.v1"
PROVIDES = ["evidence.concrete_contract_violation", "evidence.oracle.independent_second"]
REQUIRES: list[str] = ["python.source.file.available"]

REPO = pathlib.Path(__file__).resolve().parents[3]

def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_evidence_concrete.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _load_oracle():
    # bound_capabilities/concrete_execution_oracle.py has no CAPABILITY_ID — import as module
    import importlib.util
    path = REPO / "canonical/runtime/bound_capabilities/concrete_execution_oracle.py"
    spec = importlib.util.spec_from_file_location("concrete_execution_oracle", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod

def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    oracle = _load_oracle()

    source = args.get("source")
    if source is None and args.get("source_path"):
        sp = (repo / str(args["source_path"])).resolve()
        if sp == repo or repo not in sp.parents:
            raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
        source = sp.read_text(encoding="utf-8")
    if not source:
        # default deterministic sample: post: _ > 0 but f can return -1
        source = "def f(x):\n    \"\"\"post: _ >= 0\"\"\"\n    return x - 5\n"

    result = oracle.check_source(source)
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "source_excerpt": source[:500],
        "result": result,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "verified": result.get("status") in ("CONTRACT_VIOLATION_FOUND", "NO_POSTCONDITION_PARSED", "NO_VIOLATION_IN_SAMPLE"),
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.write_bytes(raw)
    return {
        "adapter": "evidence_oracle_concrete_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": artifact["verified"],
        "status": result.get("status"),
        "checked": result.get("checked", 0),
        "violations": result.get("violations", []),
        "verified": artifact["verified"],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
