#!/usr/bin/env python3
"""Registry inventory only; execution and task verification are not implemented.

Producer/token presence is diagnostic, not proof of review, synthesis,
allowlisting or landing. Do not use this adapter to certify those effects.
"""
from __future__ import annotations
import json, pathlib
from canonical.runtime.composition_inventory_v1 import write_inventory_report
from typing import Any
SCHEMA="PROJECT_BRAIN_PYTHON_PIPELINE_ALLOWLIST_GATE_V1"
CAPABILITY_ID="python.pipeline.allowlist_gate.v1"
PROVIDES=["python.pipeline.allowlist.verified","python.review.composition.allowlist_verified"]
REQUIRES: list[str]=["python.review.diff_static_triage","python.review.diff_type_gate","python.review.diff_coverage_gate","python.review.diff_security_gate"]
REPO=pathlib.Path(__file__).resolve().parents[3]
def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p=(root / str(raw or "canonical/tmp_pipeline_allowlist.json")).resolve()
    if p==root or root not in p.parents: raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True); return p
def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo=pathlib.Path(root).resolve(); output=_safe_output(repo, args.get("output_path"))
    reg=json.loads((repo/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    required=REQUIRES
    found={r: (r in {p for m in reg["capabilities"].values() for p in m.get("provides",[])}) for r in required}
    gates=["python.review.diff_static_triage.v1","python.review.diff_type_gate.v1","python.review.diff_coverage_gate.v1","python.review.diff_perf_gate.v1","python.review.diff_security_gate.v1","python.review.diff_mutation_gate.v1"]
    gate_caps={g: g in reg["capabilities"] for g in gates}
    pipeline_ok="execution.pipeline.8stage.v1" in reg["capabilities"] or "execution.pipeline.completed" in {p for m in reg["capabilities"].values() for p in m.get("provides",[])}
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"required_tokens":required,"found":found,"gate_caps":gate_caps,"pipeline_ok":pipeline_ok,"planned_allowlist":"canonical/** allowlisted, vendor/** blocked","inventory_ready":all(found.values()) and all(gate_caps.values()) and pipeline_ok,"model_dependency_count":0,"incremental_spend_usd":0}
    return write_inventory_report(repo, output, artifact, "python_pipeline_allowlist_gate_v1")
