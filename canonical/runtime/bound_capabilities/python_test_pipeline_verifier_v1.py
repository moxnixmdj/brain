#!/usr/bin/env python3
"""Report whether the declared test pipeline is actually verified.

This adapter can inspect the registry but does not execute the claimed pipeline.
Registry names and effects therefore cannot establish a verified test run.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_PYTHON_TEST_PIPELINE_VERIFIER_V1"
CAPABILITY_ID = "python.test.pipeline.verifier.v1"
PROVIDES = ["python.test.pipeline.verified", "python.test.intelligence.verified"]
REQUIRES: list[str] = [
    "test.slice.never_miss.verified", "test.selection.minimal", "execution.pipeline.completed",
    "python.test.measurement.objective", "python.tests.audit",
]


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    path = (root / str(raw or "canonical/tmp_test_pipeline_verifier.json")).resolve()
    if path == root or root not in path.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    registry = json.loads((repo / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    capabilities = registry["capabilities"]
    all_provides = {effect for entry in capabilities.values() for effect in entry.get("provides", [])}
    found = {effect: effect in all_provides for effect in REQUIRES}
    producers = [
        "test.slice.never_miss.v1", "python.source.change_impact.testselect.v1",
        "execution.pipeline.8stage.v1", "python.repository.acceptance.measure.v1",
        "python.tests.audit.unittest",
    ]
    producer_found = {capability: capability in capabilities for capability in producers}
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "required_tokens": REQUIRES,
        "found": found,
        "producers": producer_found,
        "verified": False,
        "reason": "PIPELINE_NOT_EXECUTED__REGISTRY_PRESENCE_IS_NOT_VERIFICATION",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.write_bytes(raw)
    return {
        "adapter": "python_test_pipeline_verifier_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": False,
        "verified": False,
        "found": found,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
