#!/usr/bin/env python3
"""Inspect registry declarations only; this adapter does not execute a workflow."""
from __future__ import annotations
import hashlib, json, pathlib
from typing import Any
SCHEMA="PROJECT_BRAIN_PYTHON_EVIDENCE_CONTRACT_SUPERCOMPOSER_V1"
CAPABILITY_ID="python.evidence.contract.supercomposer.v1"
PROVIDES=["python.evidence.contract.super.verified","python.evidence.contract.family.verified"]
REQUIRES: list[str]=["evidence.evidence.family.super.verified","evidence.synthesis.super.verified","evidence.hypothesis.property_violation","evidence.oracle.independent_second","python.contract.issue.composition.verified"]
REPO=pathlib.Path(__file__).resolve().parents[3]
def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p=(root / str(raw or "canonical/tmp_evidence_contract_supercomposer.json")).resolve()
    if p==root or root not in p.parents: raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True); return p
def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo=pathlib.Path(root).resolve(); output=_safe_output(repo, args.get("output_path"))
    reg=json.loads((repo/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    all_prov={p for m in reg["capabilities"].values() for p in m.get("provides",[])}
    required=REQUIRES
    found={r: (r in all_prov) for r in required}
    producers=["software.evidence.synthesis.supercomposer.v1","evidence.oracle.hypothesis_property.v1","evidence.oracle.concrete_execution.v1","python.contract.issue_orchestration.fusion.v1"]
    prod_found={c: c in reg["capabilities"] for c in producers}
    registry_ready=all(found.values()) and all(prod_found.values())
    # Registry declarations are not execution or verification evidence.
    verified=False
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"required_tokens":required,"found":found,"producers":prod_found,"composition":"hypothesis violation → oracle independent second → evidence family super → synthesis super → contract issue composition","verified":verified,"registry_ready":registry_ready,"reason":"DEPENDENCIES_NOT_EXECUTED","model_dependency_count":0,"incremental_spend_usd":0}
    raw=json.dumps(artifact, sort_keys=True, separators=(",",":")).encode(); output.write_bytes(raw)
    return {"adapter":"python_evidence_contract_supercomposer_v1","output_path":str(output.relative_to(repo)),"output_sha256":hashlib.sha256(raw).hexdigest(),"output_verified":verified,"verified":verified,"reason":"DEPENDENCIES_NOT_EXECUTED","found":found,"model_dependency_count":0,"incremental_spend_usd":0}
