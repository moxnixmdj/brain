import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
GATE = ROOT / "canonical/runtime/coding_v5_positive_adequacy_certificate_gate_v1.py"
BOUNDARY = ROOT / "canonical/governance/CODING_V5_POSITIVE_ADEQUACY_CURRENT_EVIDENCE_BOUNDARY_20261009_V1.json"
VERIFY = ROOT / "canonical/verification/CODING_V5_POSITIVE_ADEQUACY_CERTIFICATE_GATE_INDEPENDENT_VERIFICATION_20261009_V1.json"

def blob(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode() + b"\0" + data)
    return h.hexdigest()

def test_terminal_authority_binds_gate_without_promoting_certificate():
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    src = auth["authoritative_sources"]["coding_v5_positive_adequacy_certificate_gate_20261009_v1"]

    assert blob(GATE) == src["git_blob_sha"] == "c777c4a2c9e34cb3e37ae8ed75565c5a3aefa390"
    assert blob(VERIFY) == src["independent_verification"]["git_blob_sha"] == "ec006e826547d810aa3fe61e77871ed0dc35e131"
    assert blob(BOUNDARY) == src["current_evidence_boundary"]["git_blob_sha"] == "ab28e64d73392bd7810a579ce5a1ed346c9e2925"

    live = auth["live_truth"]
    assert live["coding_v5_positive_adequacy_certificate_gate_verified"] is True
    assert live["coding_v5_positive_adequacy_certificate_ready"] is False
    assert live["coding_v5_positive_adequacy_current_evidence_gate_result"] == "FAIL_CLOSED__FINITE_CELL_COMPLETENESS_UNPROVED"
    assert live["coding_v5_positive_adequacy_remaining_evidence_class"] == "FORMAL_ALL_MEMBERS_THEOREM_OR_COMPLETE_FINITE_CELL"
    assert live["coding_v5_positive_adequacy_posthoc_acceptance_cell_allowed"] is False
    assert live["coding_v5_positive_adequacy_one_success_generalization_allowed"] is False
    assert live["coding_v5_positive_adequacy_selector_work_authorized_now"] is False
    assert live["cursorbench_next_proof_object"] == "CODING_V5_AUTHENTICATED_POSITIVE_ADEQUACY_CERTIFICATE_V1"

    rec = auth["coding_v5_positive_adequacy_gate_reconciliation_20261009_v1"]
    assert rec["acceptance_credit_delta"] == 0
    assert rec["terminal_credit_delta"] == 0
