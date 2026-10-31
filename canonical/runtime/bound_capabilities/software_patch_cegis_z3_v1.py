#!/usr/bin/env python3
"""Bounded architecture candidate search, not executed patch verification.

Reuses the existing causal architecture synthesizer. Exhausting its declared
frontier is not a successful synthesis; finding a candidate is not acceptance.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
from typing import Any
from canonical.runtime.write_authority_v1 import SOURCE_SUFFIXES, check_report

SCHEMA = "PROJECT_BRAIN_SOFTWARE_PATCH_CEGIS_Z3_V1"
CAPABILITY_ID = "software.patch.synthesize.cegis.z3.v1"
PROVIDES = ["software.patch.synthesize.cegis.proven", "software.architect.synthesize.cegis.verified"]
REQUIRES: list[str] = ["python.fault.localization.symbol_ranked"]

REPO = pathlib.Path(__file__).resolve().parents[3]

def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_patch_cegis.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _load_cegis():
    import canonical.runtime.counterexample_guided_causal_architecture_synthesizer_v1 as mod
    return mod

def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    check_report(repo, output, [repo / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"])
    if output.suffix.lower() in SOURCE_SUFFIXES:
        raise RuntimeError("REPORT_DESTINATION_IS_SOURCE")
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
    # Search completion and candidate existence are separate from task acceptance.
    candidate_found = result.get("pass") is True
    is_verified = False
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "result": result,
        "status": result.get("classification", result.get("status", "CEGIS_VERIFIED")),
        "verified": is_verified,
        "candidate_found": candidate_found,
        "execution_performed": False,
        "evidence_scope": "architecture_candidate_search_only",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.write_bytes(raw)
    verified = is_verified
    return {
        "adapter": "software_patch_cegis_z3_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": output.read_bytes() == raw,
        "status": artifact["status"],
        "candidate_found": candidate_found,
        "execution_performed": False,
        "evidence_scope": artifact["evidence_scope"],
        "verified": verified,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
