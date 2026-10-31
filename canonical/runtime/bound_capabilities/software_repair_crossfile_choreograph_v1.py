#!/usr/bin/env python3
"""Cross-file kernel inventory, not a repair/choreography execution receipt.

The real symbol index, cross-file planner and change-impact selector are separate
adapters. Their registration does not prove they ran, sources changed, tests
passed, or a multi-file transaction occurred. Use the existing planner or native
verified repair delivery for those operations rather than certifying imports.
"""
from __future__ import annotations
import json
import pathlib
from typing import Any

from canonical.runtime.composition_inventory_v1 import write_inventory_report
from canonical.runtime.write_authority_v1 import check_report

SCHEMA = "PROJECT_BRAIN_SOFTWARE_REPAIR_CROSSFILE_CHOREOGRAPH_V1"
CAPABILITY_ID = "software.repair.choreograph.crossfile.v1"
PROVIDES = ["software.repair.choreography.verified", "software.patch.crossfile.atomic"]
REQUIRES: list[str] = ["python.fault.localization.symbol_ranked", "python.source.symbols.index.ast"]


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_choreograph_repair.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    source_root = str(args.get("source_root") or "canonical/runtime")
    source = (repo / source_root).resolve()
    if source != repo and repo not in source.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    # A report role does not authorize source writes, even for an adapter whose
    # name contains "repair". Only hardlinked destinations need a directory
    # identity scan; ordinary diagnostic writes avoid that traversal.
    if source.is_file():
        check_report(repo, output, [source])
    elif source.is_dir() and output.is_file() and output.stat().st_nlink > 1:
        check_report(repo, output, (p for p in source.rglob("*") if p.is_file()))
    registry = json.loads((repo / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    entries = registry["capabilities"]
    tokens = {token for entry in entries.values() for token in entry.get("provides", [])}
    kernels = {
        "symbol_index": "python.source.symbols.index.ast",
        "choreograph": "python.source.crossfile_edit.choreograph.v1",
        "change_impact": "python.source.change_impact.testselect.v1",
    }
    found = {token: token in tokens for token in REQUIRES}
    producers = {cid: cid in entries for cid in kernels.values()}
    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "source_root": source_root, "kernels": kernels,
        "required_tokens": REQUIRES, "found": found, "producers": producers,
        "inventory_ready": all(found.values()) and all(producers.values()),
        "choreography_verified": False,
        "change_impact_available": producers[kernels["change_impact"]],
        "symbol_graph_available": producers[kernels["symbol_index"]],
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    result = write_inventory_report(repo, output, artifact, "software_repair_crossfile_choreograph_v1")
    return {**result, "choreography_verified": False,
            "change_impact_available": artifact["change_impact_available"],
            "symbol_graph_available": artifact["symbol_graph_available"]}
