#!/usr/bin/env python3
"""Run the existing concrete contract oracle on the actual caller's source.

A completed check, a counterexample, and satisfaction on a finite sample are
separate outcomes. No demo substitutes for absent source. Uses the same bounded
worker as the Hypothesis adapter; neither adapter constitutes an OS sandbox or
an independent semantic implementation of the shared contract evaluator.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

from canonical.runtime.bound_capabilities import evidence_oracle_hypothesis_v1 as property_oracle

SCHEMA = "PROJECT_BRAIN_EVIDENCE_ORACLE_CONCRETE_V1"
CAPABILITY_ID = "evidence.oracle.concrete_execution.v1"
PROVIDES = ["evidence.concrete_contract_violation", "evidence.oracle.independent_second"]
REQUIRES = ["python.source.file.available"]


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    return property_oracle._safe_output(root, raw or "canonical/tmp_evidence_concrete.json")


def _load_oracle():
    return property_oracle._load_contract_oracle()


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    source = args.get("source")
    if source is None and args.get("source_path"):
        path = (repo / str(args["source_path"])).resolve()
        if path == repo or repo not in path.parents:
            raise ValueError("PATH_OUTSIDE_REPOSITORY")
        if path == output:
            raise ValueError("OUTPUT_ALIASES_SOURCE")
        source = path.read_text(encoding="utf-8")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("SOURCE_REQUIRED")
    if len(source.encode("utf-8")) > 1 << 20:
        raise ValueError("SOURCE_TOO_LARGE")
    if output.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    timeout = property_oracle._integer(args, "timeout_s", 10, 1, 120)
    observation = property_oracle._run_worker({"source": source, "engine": "concrete"}, timeout)
    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "result": observation, "status": observation["status"],
        "checked": observation["checked"], "violations": observation["violations"],
        "check_completed": observation["check_completed"],
        "verified": observation["verified"], "proves_absence": False,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(raw)
    return {**artifact, "adapter": "evidence_oracle_concrete_v1",
            "output_path": str(output.relative_to(repo)),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
            "output_verified": artifact["verified"] is True}
