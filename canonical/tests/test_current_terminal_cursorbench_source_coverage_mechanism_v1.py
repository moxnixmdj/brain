import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REC = ROOT / "canonical/governance/CURSORBENCH_SOURCE_COVERAGE_MECHANISM_TERMINAL_RECONCILIATION_20261009_V1.json"
ACT = ROOT / "canonical/governance/CURSORBENCH_SOURCE_COVERAGE_ATOMS_ACTIVATION_20261009_V1.json"
VERIFY = ROOT / "canonical/verification/CURSORBENCH_SOURCE_COVERAGE_ATOMS_INDEPENDENT_VERIFICATION_20261009_V1.json"

def blob(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def test_current_terminal_binds_source_coverage_mechanism_without_truth_credit():
    auth=json.loads(AUTH.read_text())
    rec=json.loads(REC.read_text())
    src=auth["authoritative_sources"]["cursorbench_source_coverage_semantic_atoms_mechanism_20261009_v1"]

    assert blob(REC)==src["git_blob_sha"]=="0eb9227b491c28cb6396de5a296e9d16913a7735"
    assert blob(ACT)==src["activation"]["git_blob_sha"]=="2008028041450cdba9a8ad291d56d64c6a1429bf"
    assert blob(VERIFY)==src["independent_verification"]["git_blob_sha"]=="cc0795464a18326643c11494bcc7a93144ccd9b9"

    live=auth["live_truth"]
    assert live["cursorbench_source_coverage_semantic_atoms_mechanism_verified"] is True
    assert live["cursorbench_typed_semantics_atom_mechanism_verified"] is True
    assert live["cursorbench_failure_mode_completeness_atom_mechanism_verified"] is True
    assert live["cursorbench_source_coverage_real_target_relevant_receipt_bound"] is False
    assert live["cursorbench_typed_semantics_atom_truth_proved"] is False
    assert live["cursorbench_failure_mode_completeness_atom_truth_proved"] is False
    assert live["cursorbench_source_coverage_missing_binding_state"]=="OPEN_NOT_FALSE"
    assert live["cursorbench_source_coverage_malformed_binding_state"]=="FAIL_CLOSED"
    assert live["cursorbench_positive_adequacy_cover_closed"] is False
    assert live["cursorbench_acceptance_predicate_closed"] is False

    assert rec["effect"]["external_membership_atom_count_delta"]==0
    assert rec["accounting"]["acceptance_credit_delta"]==0
    assert rec["accounting"]["terminal_credit_delta"]==0
    assert auth["pointer_revision"]==84
