import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
ACT = ROOT / "canonical/governance/CURSORBENCH_SUPPORTED_TRANSFORM_STRUCTURAL_AUTO_REFINEMENT_ACTIVATION_20261009_V1.json"
VERIFY = ROOT / "canonical/verification/CURSORBENCH_SUPPORTED_TRANSFORM_STRUCTURAL_AUTO_REFINEMENT_INDEPENDENT_VERIFICATION_20261009_V1.json"

def blob(path: Path) -> str:
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode("ascii")+b"\0"+data)
    return h.hexdigest()

def test_terminal_authority_binds_structural_atom_reduction_without_overclaim():
    auth=json.loads(AUTH.read_text(encoding="utf-8"))
    act=json.loads(ACT.read_text(encoding="utf-8"))
    verify=json.loads(VERIFY.read_text(encoding="utf-8"))
    src=auth["authoritative_sources"]["cursorbench_supported_transform_structural_auto_refinement_20261009_v1"]
    assert blob(ACT)==src["git_blob_sha"]
    assert blob(VERIFY)==src["independent_verification"]["git_blob_sha"]
    assert verify["result"]["total_tests_run"]==27
    assert verify["result"]["total_tests_passed"]==27
    live=auth["live_truth"]
    assert live["cursorbench_supported_transform_structural_auto_refinement_verified"] is True
    assert live["cursorbench_typed_acceptance_membership_atom_count_total"]==5
    assert live["cursorbench_typed_acceptance_membership_atom_count_structurally_internalized"]==1
    assert live["cursorbench_typed_acceptance_membership_atom_count_external_when_exact_model_passes"]==4
    assert set(live["cursorbench_typed_acceptance_remaining_external_membership_atoms"])==set(
        act["remaining_external_membership_atoms_when_structural_proof_passes"]
    )
    assert live["cursorbench_positive_adequacy_cover_closed"] is False
    assert live["cursorbench_dominance_closed"] is False
    assert live["cursorbench_acceptance_predicate_closed"] is False
    assert live["cursorbench_selector_work_authorized_now"] is False
    rec=auth["cursorbench_supported_transform_structural_auto_refinement_reconciliation_20261009_v1"]
    assert rec["prior_external_membership_atom_count"]==5
    assert rec["current_external_membership_atom_count"]==4
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
