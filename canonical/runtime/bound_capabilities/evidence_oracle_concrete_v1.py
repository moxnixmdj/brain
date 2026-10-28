#!/usr/bin/env python3
"""Task-bound, finite concrete counterexample witness.

The underlying interpreter accepts a deliberately restricted numeric subset;
it shares that interpreter with the Hypothesis adapter and is not independent
of it. A clean sample is not a proof, and no user source is executed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_EVIDENCE_ORACLE_CONCRETE_V1"
CAPABILITY_ID = "evidence.oracle.concrete_execution.v1"
PROVIDES = ["evidence.concrete_contract_violation"]
REQUIRES: list[str] = ["python.source.file.available"]


def _load_oracle():
    path = pathlib.Path(__file__).with_name("concrete_execution_oracle.py")
    spec = importlib.util.spec_from_file_location("_brain_concrete_execution_oracle", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("CONCRETE_ORACLE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = (repo / str(args.get("output_path") or "canonical/tmp_evidence_concrete.json")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if output.is_file() and (output.suffix == ".py" or output.stat().st_nlink > 1):
        raise RuntimeError("OUTPUT_OVERLAPS_INPUT")
    source = args.get("source")
    if args.get("source_path"):
        path = (repo / str(args["source_path"])).resolve()
        if path == repo or repo not in path.parents:
            raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
        if path == output or (path.exists() and output.exists() and path.samefile(output)):
            raise RuntimeError("OUTPUT_OVERLAPS_INPUT")
        if source is None:
            source = path.read_text(encoding="utf-8")
    if source is None:
        result = {"status": "SOURCE_REQUIRED", "checked": 0, "violations": [],
                  "proves_absence": False, "independent_of_hypothesis_adapter": False}
    else:
        oracle = _load_oracle()
        sample = args.get("sample")
        result = oracle.check_source(source) if sample is None else oracle.check_source(source, sample)
    witness = (result.get("status") == "CONTRACT_VIOLATION_FOUND"
               and result.get("checked", 0) > 0 and bool(result.get("violations")))
    artifact = {"schema": SCHEMA, "capability_id": CAPABILITY_ID,
                "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest() if isinstance(source, str) else None,
                "result": result, "verified": witness, "counterexample_found": witness,
                "model_dependency_count": 0, "incremental_spend_usd": 0}
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {"adapter": "evidence_oracle_concrete_v1", "output_path": str(output.relative_to(repo)),
            "output_sha256": hashlib.sha256(raw).hexdigest(), "output_verified": output.read_bytes() == raw,
            "status": result.get("status"), "checked": result.get("checked", 0),
            "violations": result.get("violations", []), "verified": witness,
            "counterexample_found": witness, "proves_absence": False,
            "independent_of_hypothesis_adapter": False,
            "model_dependency_count": 0, "incremental_spend_usd": 0}
