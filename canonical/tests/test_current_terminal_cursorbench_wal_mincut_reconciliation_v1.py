from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
RECON = ROOT / "canonical/governance/CURSORBENCH_WAL_RECOVERY_THREE_ATOM_EVIDENCE_RECONCILIATION_20261009_V2.json"


def test_wal_local_evidence_reconciles_with_information_boundary_mincut_without_global_credit():
    authority = json.loads(AUTH.read_text(encoding="utf-8"))
    recon = json.loads(RECON.read_text(encoding="utf-8"))

    ref = authority["authoritative_sources"]["cursorbench_wal_three_atom_exact_context_v2"]
    assert ref["git_blob_sha"] == "8c0620d8d00f9297bf6eaa3ac53d06ff9781a760"
    assert recon["information_boundary_mincut"]["git_blob_sha"] == "a5c283e8e09f82ff10c9daaeea0951a304bd6e6d"
    assert recon["relation_to_mincut"]["target_per_model_boundary_audit_satisfied"] is False
    assert recon["relation_to_mincut"]["current_4_0_protocol_continuity_fact_satisfied"] is False
    assert recon["relation_to_mincut"]["global_cursorbench_atom_truth_delta"] == 0

    live = authority["live_truth"]
    assert live["cursorbench_wal_exact_context_evidence_verified"] is True
    assert live["cursorbench_wal_exact_context_benchmark"] == "TERMINAL_BENCH_4_0"
    assert live["cursorbench_wal_exact_context_proved_atom_ids"] == [
        "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1",
        "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1",
        "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1",
        "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1",
    ]
    assert live["cursorbench_wal_exact_context_open_atom_ids"] == [
        "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1"
    ]
    assert live["cursorbench_wal_exact_context_independent_acceptance_pass"] is False
    assert live["cursorbench_wal_exact_context_failed_requirement_ids"] == [
        "R13_NO_TASK_SPECIFIC_CHEATING"
    ]
    assert live["cursorbench_wal_exact_context_global_cursorbench_atom_truth_delta"] == 0
    assert live["cursorbench_wal_satisfies_target_per_model_information_boundary_audit"] is False
    assert live["cursorbench_wal_satisfies_current_4_0_protocol_continuity_fact"] is False
    assert live["cursorbench_target_context_binding_required_before_atom_truth_transfer"] is True

    # The newer min-cut remains fully load-bearing.
    assert live["cursorbench_preverifier_information_boundary_external_protocol_unknown_count"] == 1
    assert live["cursorbench_preverifier_information_boundary_per_model_internal_audit_required"] is True
    assert live["cursorbench_no_hidden_verifier_access_atom_truth_proved"] is False

    # No local WAL evidence is allowed to mutate the global CursorBench family truth.
    assert live["cursorbench_typed_acceptance_membership_atom_count_external_when_exact_model_passes"] == 4
    assert live["cursorbench_remaining_typed_acceptance_real_evidence_bundle_count"] == 3
    assert live["cursorbench_source_coverage_real_receipt_bound"] is False
    assert live["cursorbench_dependency_provenance_real_receipt_bound"] is False
    assert live["cursorbench_preverifier_information_boundary_real_receipt_bound"] is False
    assert live["cursorbench_typed_semantics_atom_truth_proved"] is False
    assert live["cursorbench_failure_mode_completeness_atom_truth_proved"] is False
    assert live["cursorbench_dependency_provenance_atom_truth_proved"] is False

    rec = authority["cursorbench_wal_three_atom_mincut_reconciliation_20261009_v2"]
    assert rec["current_4_0_protocol_continuity_fact_delta"] == 0
    assert rec["target_per_model_boundary_audit_delta"] == 0
    assert rec["global_cursorbench_atom_truth_delta"] == 0
    assert rec["acceptance_credit_delta"] == 0
    assert rec["terminal_credit_delta"] == 0
