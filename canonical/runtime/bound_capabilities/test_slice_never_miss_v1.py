#!/usr/bin/env python3
"""Report that never-miss test slicing is not established.

The change-impact selector is useful as an advisory heuristic, but a registry
entry is not evidence that it ran, and constructed import/fixture cases show
that it can omit failing tests. This adapter must not advertise a verified
never-miss slice or an unmeasured speedup until sound evidence exists.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_TEST_SLICE_NEVER_MISS_V1"
CAPABILITY_ID = "test.slice.never_miss.v1"
PROVIDES = ["test.slice.never_miss.verified", "test.selection.minimal"]
REQUIRES: list[str] = ["python.source.change_impact.test_selection"]


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    path = (root / str(raw or "canonical/tmp_test_slice.json")).resolve()
    if path == root or root not in path.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    registry = json.loads((repo / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    selector_present = "python.source.change_impact.testselect.v1" in registry["capabilities"]
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "change_impact_exists": selector_present,
        "never_miss": False,
        "selected_vs_candidate_ratio": None,
        "speedup": None,
        "verified": False,
        "reason": "NEVER_MISS_DISPROVED__REGISTRY_PRESENCE_IS_NOT_EXECUTION_EVIDENCE",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.write_bytes(raw)
    return {
        "adapter": "test_slice_never_miss_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        # The artifact is a diagnostic refusal, not a verified capability effect.
        "output_verified": False,
        "verified": False,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
