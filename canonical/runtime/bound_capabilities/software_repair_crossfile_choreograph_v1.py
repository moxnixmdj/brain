#!/usr/bin/env python3
"""Cross-file repair choreography — index, choreograph, slice: one executed
composition over the caller's tree and edits.

Measured before (2026-10-28): this adapter imported three kernels and wrote
``verified: True`` without calling any of them.  It now runs the symbol
indexer, the collision-checked cross-file choreographer and the change-impact
selector on the caller's ``source_root`` / ``edits_path`` / ``changed_paths``
through ``composer_execution_v1``; verified only when all three verified.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = "PROJECT_BRAIN_SOFTWARE_REPAIR_CROSSFILE_CHOREOGRAPH_V1"
CAPABILITY_ID = "software.repair.choreograph.crossfile.v1"
PROVIDES = ["software.repair.choreography.verified", "software.patch.crossfile.atomic"]
REQUIRES: list[str] = ["python.fault.localization.symbol_ranked", "python.source.symbols.index.ast"]
PRODUCERS: list[str] = ["python.source.symbols.index.ast", "python.source.crossfile_edit.choreograph.v1",
                        "python.source.change_impact.testselect.v1"]
DEFAULT_OUTPUT = "canonical/tmp_repair_choreograph.json"
REPO = pathlib.Path(__file__).resolve().parents[3]


def _executor():
    try:
        from canonical.runtime import composer_execution_v1 as mod  # type: ignore
        return mod
    except Exception:
        spec = importlib.util.spec_from_file_location(
            "composer_execution_v1", REPO / "canonical" / "runtime" / "composer_execution_v1.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    result = _executor().compose(
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter="software_repair_crossfile_choreograph_v1",
        producers=PRODUCERS, requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description="symbol index -> cross-file choreography -> change-impact slice")
    result["choreography_verified"] = result["verified"]
    return result
