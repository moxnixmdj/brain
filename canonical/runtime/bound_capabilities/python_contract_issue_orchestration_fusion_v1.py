#!/usr/bin/env python3
"""Inspect registry declarations only; this adapter does not execute a workflow."""
from __future__ import annotations
import hashlib, json, pathlib
from typing import Any
SCHEMA="PROJECT_BRAIN_PYTHON_CONTRACT_ISSUE_ORCHESTRATION_FUSION_V1"
CAPABILITY_ID="python.contract.issue_orchestration.fusion.v1"
PROVIDES=["python.orchestration.fused.verified","python.contract.issue.composition.verified"]
REQUIRES: list[str]=["python.contract.verdict","python.issue.natural_language.edit_intent","python.software.issue_to_pr.orchestration"]
REPO=pathlib.Path(__file__).resolve().parents[3]
def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p=(root / str(raw or "canonical/tmp_contract_issue_fusion.json")).resolve()
    if p==root or root not in p.parents: raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True); return p
def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo=pathlib.Path(root).resolve(); output=_safe_output(repo, args.get("output_path"))
    reg=json.loads((repo/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    all_prov={p for m in reg["capabilities"].values() for p in m.get("provides",[])}
    required=REQUIRES
    found={r: (r in all_prov) for r in required}
    producers=["python.contract.check.crosshair.v1","python.issue.natural_language.parse_edit_intent.v1","python.software.issue_to_pr.orchestrate.v1"]
    prod_found={c: c in reg["capabilities"] for c in producers}
    registry_ready=all(found.values()) and all(prod_found.values())
    # Registry declarations are not execution or verification evidence.
    verified=False
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"required_tokens":required,"found":found,"producers":prod_found,"composition":"contract.verdict gates NL edit_intent → issue_to_pr HTN → decision_synthesis typed","verified":verified,"registry_ready":registry_ready,"reason":"DEPENDENCIES_NOT_EXECUTED","model_dependency_count":0,"incremental_spend_usd":0}
    raw=json.dumps(artifact, sort_keys=True, separators=(",",":")).encode(); output.write_bytes(raw)
    return {"adapter":"python_contract_issue_orchestration_fusion_v1","output_path":str(output.relative_to(repo)),"output_sha256":hashlib.sha256(raw).hexdigest(),"output_verified":verified,"verified":verified,"reason":"DEPENDENCIES_NOT_EXECUTED","found":found,"model_dependency_count":0,"incremental_spend_usd":0}
