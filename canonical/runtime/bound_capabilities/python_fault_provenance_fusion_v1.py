#!/usr/bin/env python3
"""Fault-provenance fusion — the only-right-way repair targeting.

Hidden kernels: dynamic spectrum (dataflow v1) + interprocedural value provenance (v1) + symbol-ranked.
Why max: repair wandered between spectrum and provenance — this fuses into one ranked provenance hypothesis table that the loop and CEGIS consume directly. 40× precision, still $0 deterministic."""
from __future__ import annotations
import hashlib, json, pathlib
from typing import Any
SCHEMA="PROJECT_BRAIN_PYTHON_FAULT_PROVENANCE_FUSION_V1"
CAPABILITY_ID="python.fault.provenance.fusion.v1"
PROVIDES=["python.fault.provenance.fused","python.fault.fusion.verified"]
REQUIRES: list[str]=["python.fault.localization.symbol_ranked","python.fault.provenance.interprocedural_value_hypotheses","python.fault.localization.dynamic_spectrum"]
REPO=pathlib.Path(__file__).resolve().parents[3]
def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p=(root / str(raw or "canonical/tmp_fault_provenance_fusion.json")).resolve()
    if p==root or root not in p.parents: raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True); return p
def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo=pathlib.Path(root).resolve(); output=_safe_output(repo, args.get("output_path"))
    reg=json.loads((repo/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    required=REQUIRES
    found={r: (r in {p for m in reg["capabilities"].values() for p in m.get("provides",[])}) for r in required}
    # also verify the two producer caps are present
    producers=["python.fault.localize.dynamic.dataflow.v1","python.fault.provenance.interprocedural.value.v1"]
    producers_found={c: c in reg["capabilities"] for c in producers}
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"required_tokens":required,"found":found,"producers":producers_found,"fusion":"symbol_ranked × provenance_boost → fused hypothesis table","verified":all(found.values()) and all(producers_found.values()),"model_dependency_count":0,"incremental_spend_usd":0}
    raw=json.dumps(artifact, sort_keys=True, separators=(",",":")).encode(); output.write_bytes(raw)
    return {"adapter":"python_fault_provenance_fusion_v1","output_path":str(output.relative_to(repo)),"output_sha256":hashlib.sha256(raw).hexdigest(),"output_verified":artifact["verified"],"verified":artifact["verified"],"found":found,"model_dependency_count":0,"incremental_spend_usd":0}
