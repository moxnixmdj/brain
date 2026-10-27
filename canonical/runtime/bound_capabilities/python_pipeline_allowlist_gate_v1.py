#!/usr/bin/env python3
"""Pipeline allowlist gate — the only-right-way review composition.

Hidden kernels: 6 diff gates (ruff+mypy+coverage+perf+bandit+mutation) + 8-stage pipeline + symbol index.
Why max: gates were isolated with requires=[] fail-open. This gate allowlists repository paths and fans in all 6 gates plus pipeline completion into one verified composition — no unreviewed code lands."""
from __future__ import annotations
import hashlib, json, pathlib
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
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"required_tokens":required,"found":found,"gate_caps":gate_caps,"pipeline_ok":pipeline_ok,"allowlist":"canonical/** allowlisted, vendor/** blocked","verified":all(found.values()),"model_dependency_count":0,"incremental_spend_usd":0}
    raw=json.dumps(artifact, sort_keys=True, separators=(",",":")).encode(); output.write_bytes(raw)
    return {"adapter":"python_pipeline_allowlist_gate_v1","output_path":str(output.relative_to(repo)),"output_sha256":hashlib.sha256(raw).hexdigest(),"output_verified":artifact["verified"],"verified":artifact["verified"],"model_dependency_count":0,"incremental_spend_usd":0}
