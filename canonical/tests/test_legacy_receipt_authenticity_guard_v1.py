"""Projected and extended capabilities require authenticated run references."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from canonical.runtime import capability_receipt_lane_v1 as lane
from canonical.runtime import live_integrated_brain_v1 as live


@pytest.mark.parametrize("ref", [
    {"github_run_id": 1, "oidc_claims": {"iss": lane.GITHUB_OIDC_ISSUER, "repository": "moxnixmdj/brain", "run_id": "1"}},
    {"github_run_id": 2, "oidc_claims": {"iss": lane.GITHUB_OIDC_ISSUER, "repository": "other/repo", "run_id": "2"}},
    {"github_run_id": 3, "oidc_claims": {"iss": lane.GITHUB_OIDC_ISSUER, "repository": "moxnixmdj/brain", "run_id": "999"}},
    {"github_run_id": 4, "oidc_claims": {"iss": lane.GITHUB_OIDC_ISSUER, "repository": "moxnixmdj/brain", "run_id": "4", "workflow_ref": "untrusted"}},
], ids=["plausible-unsigned", "wrong-repository", "wrong-run", "wrong-workflow"])
def test_unsigned_references_do_not_admit_either_extended_or_projected_entries(tmp_path, monkeypatch, ref):
    root = tmp_path
    runtime = root / "canonical/runtime"
    evidence = root / "canonical/astra_runtime/evidence"
    runtime.mkdir(parents=True)
    evidence.mkdir(parents=True)
    module = runtime / "bound_capabilities/example.py"
    module.parent.mkdir()
    module.write_text("def run(args, root):\n    raise RuntimeError('never executed')\n")
    rel_module = module.relative_to(root).as_posix()
    digest = hashlib.sha256(module.read_bytes()).hexdigest()
    receipt_path = lane.receipt_path_for("forged.example")
    receipt = {"schema": lane.SCHEMA, "capability_id": "forged.example", "module_path": rel_module,
               "module_sha256": digest, "result_sha256": "a" * 64, "model_dependency_count": 0,
               "ran_by": "invented-producer"}
    record = {"schema": lane.VERIFICATION_SCHEMA, "module_sha256": digest,
              "verifier_result_sha256": "a" * 64, "reproduced": True,
              "independent_verifier": "invented-verifier", "independent_run_reference": ref}
    (root / receipt_path).write_text(json.dumps(receipt))
    (root / lane.verification_path_for(receipt_path)).write_text(json.dumps(record))
    entry = {"source": {"path": rel_module}, "verification": {"receipt_path": receipt_path},
             "incremental_spend_usd": 0}
    assert not lane.run_reference_is_attested(ref)
    assert not live._receipt_admits(entry, root)
    reg = runtime / "BOUND_CAPABILITY_REGISTRY_V1.json"
    reg.write_text(json.dumps({"schema": "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1", "capabilities": {
        "curated.example": {"status": "VERIFIED_BOUND_CAPABILITY", "incremental_spend_usd": 0}}}))
    (runtime / "AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json").write_text(json.dumps({
        "schema": "PROJECT_BRAIN_AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1",
        "capabilities": {"forged.extended": entry}}))
    projection = runtime / "CAPABILITY_RECEIPT_PROJECTION_V1.json"
    projection.write_text(json.dumps({"entries": {"forged.projected": entry}}))
    monkeypatch.setattr(live, "ROOT", root)
    monkeypatch.setattr(live, "REGISTRY", reg)
    monkeypatch.setattr(live, "PROJECTION", projection)
    live._REGISTRY_CACHE.clear()
    try:
        admitted = live.load_verified_registry()
        assert "curated.example" in admitted  # its separate path remains unchanged
        assert "forged.extended" not in admitted
        assert "forged.projected" not in admitted
    finally:
        live._REGISTRY_CACHE.clear()
