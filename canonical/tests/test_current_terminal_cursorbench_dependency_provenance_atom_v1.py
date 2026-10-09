import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"

def test_cursorbench_dependency_provenance_mechanism_bound_without_truth_promotion():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    src=a["authoritative_sources"]["cursorbench_dependency_provenance_atom_mechanism_20261009_v1"]
    assert src["git_blob_sha"]=="3691f7e499146b6e42c9608fe585d1c7a5779f55"
    assert src["independent_verification"]["git_blob_sha"]=="59daf292a30f83557dfb05dcf1f72670a1d3b85d"
    live=a["live_truth"]
    assert live["cursorbench_dependency_provenance_atom_mechanism_verified"] is True
    assert live["cursorbench_dependency_provenance_real_receipt_bound"] is False
    assert live["cursorbench_dependency_provenance_atom_truth_proved"] is False
    assert live["cursorbench_dependency_provenance_missing_binding_state"]=="OPEN_NOT_FALSE"
    assert live["cursorbench_typed_acceptance_membership_atom_count_external_when_exact_model_passes"]==4
    assert "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1" in live["cursorbench_typed_acceptance_remaining_external_membership_atoms"]
    assert a["pointer_revision"]==82
