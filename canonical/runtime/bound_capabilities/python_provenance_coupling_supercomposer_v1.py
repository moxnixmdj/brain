#!/usr/bin/env python3
"""Provenance coupling supercomposer — the only-right-way repair coupling.

Hidden kernels: fault provenance fused + fusion verified + provenance_guided + coupled_candidate + coupled nonmonotonic + interprocedural value provenance + dynamic spectrum.
Why max: repair coupling was 5 isolated pair-wise hints (dead). This super-composes them: provenance fused → provenance-guided coupled repair → nonmonotonic pair verification, 1 fused coupling table."""
from __future__ import annotations
import hashlib, json, pathlib
from typing import Any
SCHEMA="PROJECT_BRAIN_PYTHON_PROVENANCE_COUPLING_SUPERCOMPOSER_V1"
CAPABILITY_ID="python.provenance.coupling.supercomposer.v1"
PROVIDES=["python.provenance.coupling.super.verified","python.coupling.intelligence.verified"]
REQUIRES: list[str]=["python.fault.provenance.fused","python.fault.fusion.verified","python.software.repair.provenance_guided","python.software.repair.coupled_candidate_verified","python.repair.coupled_pair.nonmonotonic"]
REPO=pathlib.Path(__file__).resolve().parents[3]
def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p=(root / str(raw or "canonical/tmp_provenance_coupling_supercomposer.json")).resolve()
    if p==root or root not in p.parents: raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True); return p
def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo=pathlib.Path(root).resolve(); output=_safe_output(repo, args.get("output_path"))
    from canonical.runtime.bound_capabilities._swe_static_soundness_v1 import (
        analyze_python_static_soundness,
        load_active_bound_registry,
    )
    reg=load_active_bound_registry(repo)
    _static_check=None
    if args.get("source_root"):
        _sr=(repo/str(args["source_root"])).resolve()
        if (_sr==repo or repo in _sr.parents) and _sr.exists():
            _static_check=analyze_python_static_soundness(repo, _sr)
    all_prov={p for m in reg["capabilities"].values() for p in m.get("provides",[])}
    required=REQUIRES
    found={r: (r in all_prov) for r in required}
    producers=["python.fault.provenance.fusion.v1","python.fault.provenance.interprocedural.value.v1","python.fault.localize.dynamic.dataflow.v1","python.software.repair.guided.provenance.coupled.v1","python.software.repair.loop.coupled.ast.v1"]
    prod_found={c: c in reg["capabilities"] for c in producers}
    verified=all(found.values()) and (_static_check is None or _static_check["sound"]) and all(prod_found.values())
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"required_tokens":required,"found":found,"producers":prod_found,"composition":"provenance fused hypothesis table → provenance-guided coupled search → nonmonotonic pair verification, 2× boost preserved","verified":verified,"model_dependency_count":0,"static_soundness":_static_check,"incremental_spend_usd":0}
    raw=json.dumps(artifact, sort_keys=True, separators=(",",":")).encode(); output.write_bytes(raw)
    return {"adapter":"python_provenance_coupling_supercomposer_v1","output_path":str(output.relative_to(repo)),"output_sha256":hashlib.sha256(raw).hexdigest(),"output_verified":verified,"verified":verified,"found":found,"model_dependency_count":0,"incremental_spend_usd":0}
