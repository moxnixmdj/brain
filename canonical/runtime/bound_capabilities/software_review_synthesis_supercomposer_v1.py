#!/usr/bin/env python3
"""Registry inventory only; execution and task verification are not implemented.

Producer/token presence is diagnostic, not proof of review, synthesis,
allowlisting or landing. Do not use this adapter to certify those effects.
"""
from __future__ import annotations
import json, pathlib
from canonical.runtime.composition_inventory_v1 import write_inventory_report
from typing import Any
SCHEMA="PROJECT_BRAIN_SOFTWARE_REVIEW_SYNTHESIS_SUPERCOMPOSER_V1"
CAPABILITY_ID="software.review.synthesis.supercomposer.v1"
PROVIDES=["software.review.synthesis.super.verified","software.review.synthesis.fullstack.verified"]
REQUIRES: list[str]=["software.review.all_gates.verified","software.review.composition.typed","python.review.composition.allowlist_verified","python.pr.composition.verified","software.patch.crossfile.atomic"]
REPO=pathlib.Path(__file__).resolve().parents[3]
def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p=(root / str(raw or "canonical/tmp_review_synthesis_supercomposer.json")).resolve()
    if p==root or root not in p.parents: raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True); return p
def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo=pathlib.Path(root).resolve(); output=_safe_output(repo, args.get("output_path"))
    reg=json.loads((repo/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    all_prov={p for m in reg["capabilities"].values() for p in m.get("provides",[])}
    required=REQUIRES
    found={r: (r in all_prov) for r in required}
    producers=["software.review.gate.composer.v1","software.repair.choreograph.crossfile.v1","python.pipeline.allowlist_gate.v1","python.pr.land.composer.v1","python.review.diff_static_triage.v1"]
    prod_found={c: c in reg["capabilities"] for c in producers}
    inventory_ready=all(found.values()) and all(prod_found.values())
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"required_tokens":required,"found":found,"producers":prod_found,"planned_composition":"6 gates → typed fan-in → allowlist → PR land → crossfile atomic, planned synthesis","inventory_ready":inventory_ready,"model_dependency_count":0,"incremental_spend_usd":0}
    return write_inventory_report(repo, output, artifact, "software_review_synthesis_supercomposer_v1")
