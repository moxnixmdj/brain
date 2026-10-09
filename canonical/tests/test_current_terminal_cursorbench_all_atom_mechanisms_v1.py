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


    wal=sources["cursorbench_wal_three_atom_exact_context"]
    assert wal["git_blob_sha"]=="ed80bcbd499444a8cfd9a7940f02d2541e7e3bcd"
    assert wal["committed_replay"]["git_blob_sha"]=="2804b791aca93354e3465f7a01f56a6499996e26"

    # Exact WAL context evidence is real but must not silently transfer across
    # benchmark/task membership. Global CursorBench truth stays unchanged.
    assert live["cursorbench_wal_exact_context_evidence_verified"] is True
    assert live["cursorbench_wal_exact_context_proved_atom_ids"]==[
        "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1",
        "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1",
        "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1",
        "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1",
    ]
    assert live["cursorbench_wal_exact_context_open_atom_ids"]==[
        "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1"
    ]
    assert live["cursorbench_wal_exact_context_information_boundary_open"] is True
    assert live["cursorbench_wal_exact_context_independent_acceptance_pass"] is False
    assert live["cursorbench_wal_exact_context_failed_requirement_ids"]==[
        "R13_NO_TASK_SPECIFIC_CHEATING"
    ]
    assert live["cursorbench_wal_exact_context_hidden_cursorbench_task_membership_proved"] is False
    assert live["cursorbench_wal_exact_context_global_cursorbench_atom_truth_delta"]==0
    assert live["cursorbench_target_context_binding_or_scope_transfer_required_before_reusing_wal_atom_truth"] is True

    # The global target-family frontier remains four atoms / three real bundles
    # until target binding or a valid transfer theorem exists.
    assert live["cursorbench_typed_acceptance_membership_atom_count_external_when_exact_model_passes"]==4
    assert live["cursorbench_remaining_typed_acceptance_real_evidence_bundle_count"]==3
    assert live["cursorbench_typed_semantics_atom_truth_proved"] is False
    assert live["cursorbench_failure_mode_completeness_atom_truth_proved"] is False
    assert live["cursorbench_dependency_provenance_atom_truth_proved"] is False
    assert live["cursorbench_no_hidden_verifier_access_atom_truth_proved"] is False
