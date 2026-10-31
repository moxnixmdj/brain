#!/usr/bin/env python3
"""Diagnose cross-file repair wiring without claiming a repair was executed.

Imports are not a choreography, an atomic patch, or verification evidence.
This adapter has no authenticated execution path and therefore fails closed.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_SOFTWARE_REPAIR_CROSSFILE_CHOREOGRAPH_V1"
CAPABILITY_ID = "software.repair.choreograph.crossfile.v1"
PROVIDES = ["software.repair.choreography.verified", "software.patch.crossfile.atomic"]
REQUIRES: list[str] = ["python.fault.localization.symbol_ranked", "python.source.symbols.index.ast"]

REPO = pathlib.Path(__file__).resolve().parents[3]

def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_choreograph_repair.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    # Imports identify the existing kernels; they do not execute them.
    import canonical.runtime.bound_capabilities.python_change_impact_testselect as ci_mod  # noqa
    import canonical.runtime.bound_capabilities.python_crossfile_edit_choreograph as choreo_mod  # noqa
    import canonical.runtime.bound_capabilities.python_source_symbol_index as idx_mod  # noqa
    source_root = args.get("source_root") or "canonical/runtime"
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "source_root": source_root,
        "kernels": {
            "symbol_index": getattr(idx_mod, "CAPABILITY_ID", "python.source.symbols.index.ast"),
            "choreograph": getattr(choreo_mod, "CAPABILITY_ID", "python.source.crossfile_edit.choreograph.v1"),
            "change_impact": getattr(ci_mod, "CAPABILITY_ID", "python.source.change_impact.testselect.v1"),
        },
        "choreography_verified": False,
        "reason": "REPAIR_AND_VERIFICATION_NOT_EXECUTED",
        "change_impact_available": False,
        "symbol_graph_available": False,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "verified": False,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.write_bytes(raw)
    return {
        "adapter": "software_repair_crossfile_choreograph_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": False,
        "reason": "REPAIR_AND_VERIFICATION_NOT_EXECUTED",
        "verified": False,
        "choreography_verified": False,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
