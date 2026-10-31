#!/usr/bin/env python3
"""Inspect SWE declarations; never credit inspection as software delivery.

This legacy wrapper does not execute producers. Declarations can resolve even
when their adapters refuse or do not implement the claimed behavior. Its
registry-facing success fields therefore remain false until a real end-to-end
workflow is implemented and qualified. No task or PR is silently fabricated.
"""
from __future__ import annotations
import json, pathlib
from typing import Any
from canonical.runtime.swe_task_artifacts_v1 import fresh_output, publish_report
SCHEMA="PROJECT_BRAIN_SOFTWARE_HARDCORE_SWE_SUPERCOMPOSER_V1"
CAPABILITY_ID="software.hardcore.swe.supercomposer.v1"
PROVIDES=["software.hardcore.swe.composed.verified","software.hardcore.swe.fullstack.verified"]
REQUIRES: list[str]=["python.pipeline.allowlist.verified","python.pr.land.verified","python.transformation.fused.verified","software.hardcore.kernel.verified","software.repair.loop.cegis_verified"]
REPO=pathlib.Path(__file__).resolve().parents[3]
def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo=pathlib.Path(root).resolve(); output=fresh_output(repo, args.get("output_path"), "canonical/tmp_swe_supercomposer.json")
    reg=json.loads((repo/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    all_prov={p for m in reg["capabilities"].values() for p in m.get("provides",[])}
    required=REQUIRES
    found={r: (r in all_prov) for r in required}
    producers=["software.hardcore.kernel.orchestrate.v1","software.patch.synthesize.cegis.z3.v1","software.repair.loop.cegis_hypothesis.v1","python.pipeline.allowlist_gate.v1","python.pr.land.composer.v1","python.refactor.test_scaffold.fusion.v1"]
    prod_found={c: c in reg["capabilities"] for c in producers}
    resolved = all(found.values()) and all(prod_found.values())
    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "adapter": "software_hardcore_swe_supercomposer_v1",
        "required_tokens": required, "found": found, "producers": prod_found,
        "declarations_resolve": resolved, "workflow_executed": False,
        "status": "OPEN__DECLARATIONS_ONLY_NOT_SOFTWARE_DELIVERY",
        "pass": False, "verified": False, "fullstack_verified": False,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    return publish_report(repo, output, artifact)
