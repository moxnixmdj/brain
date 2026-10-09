import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_REAL_EVIDENCE_SPENT_CONTEXT_RECONCILIATION_20261009_V1.json"

def blob(path):
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode()+b"\0"+data)
    return h.hexdigest()

def test_spent_context_real_evidence_is_bound_without_cursorbench_credit():
    j=json.loads(P.read_text())
    assert j["validation_context"]["benchmark"]=="Terminal-Bench 4.0"
    assert j["validation_context"]["exact_cursorbench_task"] is False
    assert j["runtime_gate"]["all_five_atoms_true"] is True
    assert j["p3_composition"]["pass"] is True
    assert j["p3_composition"]["selected_policy_id"]=="BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"
    assert j["p3_composition"]["policy_adequacy_authority"] is True
    assert j["p3_composition"]["source_authorization_verified"] is False
    assert j["p3_composition"]["db_admission_authority"] is False
    assert j["p3_composition"]["u_subtraction_authority"] is False
    assert j["p3_composition"]["terminal_authority"] is False
    assert j["deduction"]["hidden_cursorbench_task_membership_proved"] is False
    assert j["deduction"]["transfer_from_this_terminal_bench_context_to_all_cursorbench_v5_contexts_proved"] is False
    assert j["deduction"]["cursorbench_positive_adequacy_cover_closed"] is False
    assert j["deduction"]["cursorbench_threshold_met"] is False
    assert j["current_main_runtime_replay"]["all_atom_gates_pass"] is True
    assert j["current_main_runtime_replay"]["p3_pass"] is True
    assert j["current_main_runtime_replay"]["selected_policy_id"]=="BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"
    assert j["current_main_runtime_replay"]["source_authorization_verified"] is False
    assert j["current_main_runtime_replay"]["terminal_authority"] is False
    assert j["accounting"]["acceptance_credit_delta"]==0
    assert j["accounting"]["terminal_credit_delta"]==0

def test_all_content_addressed_subjects_are_exact():
    j=json.loads(P.read_text())
    refs=[
        j["frozen_model"],
        j["source_contract"],
        j["runtime_gate"],
        j["hidden_audit"],
        j["p3_composition"],
        j["current_main_runtime_replay"],
        j["real_evidence_bundles"]["source_coverage"]["receipt"],
        j["real_evidence_bundles"]["source_coverage"]["verification"],
        j["real_evidence_bundles"]["dependency_provenance"]["receipt"],
        j["real_evidence_bundles"]["dependency_provenance"]["verification"],
        j["real_evidence_bundles"]["preverifier_information_boundary"]["receipt"],
        j["real_evidence_bundles"]["preverifier_information_boundary"]["verification"],
    ]
    for ref in refs:
        p=ROOT/ref["path"]
        assert p.is_file(), ref["path"]
        assert blob(p)==ref["git_blob_sha"], ref["path"]

def test_next_cut_does_not_rebuild_closed_atom_mechanisms():
    j=json.loads(P.read_text())
    assert "DO_NOT_REBUILD_THE_THREE_ATOM_MECHANISMS" in j["next_proof_object"]
    assert "BIND_AN_ACTUAL_CURSORBENCH_V5_TARGET_CONTEXT" in j["next_proof_object"]
