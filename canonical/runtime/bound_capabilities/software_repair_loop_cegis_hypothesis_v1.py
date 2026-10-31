#!/usr/bin/env python3
"""Inventory of repair-loop kernels, not evidence of task execution.

Use the existing semantic acceptance controller for bounded repair execution.
The former wrapper ran default examples without forwarding the caller's task.
Kernel availability cannot establish synthesized patches or accepted repairs.
"""
from __future__ import annotations
import json
import pathlib
from typing import Any
from canonical.runtime.composition_inventory_v1 import write_inventory_report

SCHEMA = "PROJECT_BRAIN_SOFTWARE_REPAIR_LOOP_CEGIS_HYPOTHESIS_V1"
CAPABILITY_ID = "software.repair.loop.cegis_hypothesis.v1"
PROVIDES = ["software.repair.loop.cegis_verified", "software.repair.synthesis.triad_proven"]
REQUIRES: list[str] = ["python.fault.localization.symbol_ranked"]
REPO = pathlib.Path(__file__).resolve().parents[3]


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = (repo / str(args.get("output_path") or "canonical/tmp_repair_loop_cegis.json")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    budget = int(args.get("budget", 3))
    if budget < 0:
        raise ValueError("BUDGET_NEGATIVE")
    registry_path = repo / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    entries = json.loads(registry_path.read_text())["capabilities"] if registry_path.is_file() else {}
    kernels = ["software.patch.synthesize.cegis.z3.v1", "evidence.oracle.hypothesis_property.v1",
               "evidence.oracle.concrete_execution.v1", "software.repair.choreograph.crossfile.v1"]
    found = {cid: cid in entries for cid in kernels}
    artifact = {"schema": SCHEMA, "capability_id": CAPABILITY_ID,
                "budget": budget, "iterations": [], "found": found,
                "inventory_ready": all(found.values())}
    # Shared helper protects source destinations and keeps execution claims false.
    output.parent.mkdir(parents=True, exist_ok=True)
    result = write_inventory_report(repo, output, artifact, "software_repair_loop_cegis_hypothesis_v1")
    return {**result, "iterations": 0}
