import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
ACT=ROOT/"canonical/governance/CURSORBENCH_PREVERIFIER_INFORMATION_BOUNDARY_ATOM_ACTIVATION_20261009_V1.json"
VERIFY=ROOT/"canonical/verification/CURSORBENCH_PREVERIFIER_INFORMATION_BOUNDARY_ATOM_INDEPENDENT_VERIFICATION_20261009_V1.json"

def blob(path: Path) -> str:
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode("ascii")+b"\0"+data)
    return h.hexdigest()

def test_current_terminal_authority_binds_information_boundary_mechanism_without_atom_truth():
    auth=json.loads(AUTH.read_text(encoding="utf-8"))
    src=auth["authoritative_sources"]["cursorbench_preverifier_information_boundary_atom_20261009_v1"]
    assert blob(ACT)==src["git_blob_sha"]=="821b3714c444992177eec6ef8e1cc69630a2efaf"
    assert blob(VERIFY)==src["independent_verification"]["git_blob_sha"]=="8a9f85f2a18e7c861bca950ba8b6e3f18c63d94f"

    live=auth["live_truth"]
    assert live["cursorbench_no_hidden_verifier_atom_mechanism_ready"] is True
    assert live["cursorbench_no_hidden_verifier_atom_truth_proved_for_real_target_context"] is False
    assert live["cursorbench_no_hidden_verifier_atom_real_receipt_exists"] is False
    assert live["cursorbench_no_hidden_verifier_atom_missing_evidence_is_not_disproof"] is True
    assert live["cursorbench_typed_acceptance_membership_atom_count_external_when_exact_model_passes"]==4
    assert "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1" in live["cursorbench_typed_acceptance_remaining_external_membership_atoms"]

    assert live["cursorbench_threshold_lower_bound_route_state"]=="OPEN_BLOCKED"
    assert live["cursorbench_threshold_lower_bound_route_remaining_blocker_count"]==3
    assert live["cursorbench_current_active_lane"]=="ROUTE_B_SCOPE_COMPLETE_STRONGER_PROOF"
    assert auth["pointer_revision"]==82
