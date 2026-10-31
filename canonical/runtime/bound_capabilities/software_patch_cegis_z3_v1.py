#!/usr/bin/env python3
"""Bounded architecture-search diagnostic, NOT source-patch synthesis.

Keep the legacy identifier for compatibility, but do not equate exact frontier
search (even a successful component plan) with an executed/proven code patch.
Use the measured-repair controller for its explicitly supported patch tasks.
"""
from __future__ import annotations
import pathlib
from typing import Any
from canonical.runtime.swe_task_artifacts_v1 import fresh_output, publish_report

SCHEMA = "PROJECT_BRAIN_SOFTWARE_PATCH_CEGIS_Z3_V1"
CAPABILITY_ID = "software.patch.synthesize.cegis.z3.v1"
PROVIDES = ["software.patch.synthesize.cegis.proven", "software.architect.synthesize.cegis.verified"]
REQUIRES: list[str] = ["python.fault.localization.symbol_ranked"]

REPO = pathlib.Path(__file__).resolve().parents[3]

def _load_cegis():
    import canonical.runtime.counterexample_guided_causal_architecture_synthesizer_v1 as mod
    return mod

def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = fresh_output(repo, args.get("output_path"), "canonical/tmp_patch_cegis.json")
    cegis = _load_cegis()
    manifest = args.get("manifest") or {
        "components": [
            {"id": "python.fault.localize.dynamic.dataflow.v1", "kind": "MECHANISM", "requires": ["python.source.file.available"], "provides": ["python.fault.localization.symbol_ranked"], "verified": True, "brain_owned": True, "donor_independent": True, "cost": {"wall_clock": 0.5, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}},
            {"id": "python.patch.search.test_guided.ast.v1", "kind": "MECHANISM", "requires": ["python.source.file.available"], "provides": ["python.patch.candidate.test_verified"], "verified": True, "brain_owned": True, "donor_independent": True, "cost": {"wall_clock": 0.6, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}},
            {"id": "evidence.oracle.concrete_execution.v1", "kind": "VERIFIER", "requires": ["python.source.file.available"], "provides": ["evidence.concrete_contract_violation"], "verified": True, "brain_owned": True, "donor_independent": True, "cost": {"wall_clock": 0.4, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}},
            {"id": "python.contract.check.crosshair.v1", "kind": "VERIFIER", "requires": ["python.source.file.available"], "provides": ["python.contract.verdict"], "verified": True, "brain_owned": True, "donor_independent": True, "cost": {"wall_clock": 1.0, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}},
        ],
        "counterexamples": args.get("counterexamples", []),
        "initial_facts": ["python.source.file.available", "python.test.corpus.available"],
        "target": {"required_effects": ["software.architect.synthesize.cegis.verified"], "forbidden_effects": [], "max_components": 12, "top_k": 3},
        "allow_candidate_components": False,
    }
    result = cegis.synthesize(manifest)
    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "adapter": "software_patch_cegis_z3_v1", "result": result,
        "status": "OPEN__SOURCE_PATCH_SYNTHESIS_NOT_IMPLEMENTED",
        "classification": result.get("classification"),
        "architecture_search_completed": result.get("exact_over_declared_frontier") is True,
        "architecture_search_pass": result.get("pass") is True,
        "patch_synthesized": False, "pass": False, "verified": False,
        "verification_scope": "DECLARED_COMPONENT_FRONTIER_ONLY",
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    return publish_report(repo, output, artifact)
