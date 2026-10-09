import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"

EXPECTED={
    "cursorbench_source_coverage_atoms_mechanism_20261009_v1": {
        "git_blob_sha": "2008028041450cdba9a8ad291d56d64c6a1429bf",
        "verification_git_blob_sha": "cc0795464a18326643c11494bcc7a93144ccd9b9",
    },
    "cursorbench_preverifier_information_boundary_mechanism_20261009_v1": {
        "git_blob_sha": "821b3714c444992177eec6ef8e1cc69630a2efaf",
        "verification_git_blob_sha": "8a9f85f2a18e7c861bca950ba8b6e3f18c63d94f",
    },
    "cursorbench_dependency_provenance_mechanism_20261009_v1": {
        "git_blob_sha": "3691f7e499146b6e42c9608fe585d1c7a5779f55",
        "verification_git_blob_sha": "59daf292a30f83557dfb05dcf1f72670a1d3b85d",
    },
}

def test_current_terminal_binds_all_atom_mechanisms_without_truth_credit():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    sources=a["authoritative_sources"]
    for key, expected in EXPECTED.items():
        row=sources[key]
        assert row["git_blob_sha"]==expected["git_blob_sha"]
        assert row["independent_verification"]["git_blob_sha"]==expected["verification_git_blob_sha"]

    live=a["live_truth"]
    assert live["cursorbench_all_remaining_typed_acceptance_atom_mechanisms_available"] is True
    assert live["cursorbench_remaining_typed_acceptance_mechanism_gap_count"]==0
    assert live["cursorbench_remaining_typed_acceptance_real_evidence_bundle_count"]==3
    assert live["cursorbench_source_coverage_real_receipt_bound"] is False
    assert live["cursorbench_preverifier_information_boundary_real_receipt_bound"] is False
    assert live["cursorbench_dependency_provenance_real_receipt_bound"] is False
    assert live["cursorbench_typed_semantics_atom_truth_proved"] is False
    assert live["cursorbench_failure_mode_completeness_atom_truth_proved"] is False
    assert live["cursorbench_no_hidden_verifier_access_atom_truth_proved"] is False
    assert live["cursorbench_dependency_provenance_atom_truth_proved"] is False
    assert live["cursorbench_typed_acceptance_membership_atom_count_external_when_exact_model_passes"]==4

    rec=a["cursorbench_all_atom_mechanisms_reconciliation_20261009_v1"]
    assert rec["mechanism_gap_count"]==0
    assert rec["real_evidence_bundle_count"]==3
    assert rec["real_atom_truth_delta"]==0
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
