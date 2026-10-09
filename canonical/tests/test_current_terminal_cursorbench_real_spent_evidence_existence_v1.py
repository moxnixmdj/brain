import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REC=ROOT/"canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_REAL_EVIDENCE_SPENT_CONTEXT_RECONCILIATION_20261009_V1.json"
VER=ROOT/"canonical/verification/CURSORBENCH_REACT_LEAD_FORM_CORRECTED_REAL_EVIDENCE_REPLAY_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_terminal_distinguishes_real_evidence_existence_from_cursorbench_membership():
    a=json.loads(AUTH.read_text())
    src=a["authoritative_sources"]["cursorbench_typed_acceptance_real_spent_context_evidence_20261009_v1"]
    assert blob(REC)==src["git_blob_sha"]
    assert blob(VER)==src["corrected_independent_replay"]["git_blob_sha"]
    live=a["live_truth"]
    assert live["cursorbench_typed_acceptance_real_evidence_existence_gap_closed"] is True
    assert live["cursorbench_typed_acceptance_real_same_model_spent_context_evidence_proved"] is True
    assert live["cursorbench_typed_acceptance_spent_context_historical_candidate_reward"]==0
    assert live["cursorbench_typed_acceptance_spent_context_historical_candidate_passed"] is False
    assert live["cursorbench_typed_acceptance_spent_context_failure_class"]=="SPEC_OVERCONSTRAINT"
    assert live["cursorbench_typed_acceptance_spent_context_all_five_atoms_proved"] is True
    assert live["cursorbench_typed_acceptance_spent_context_is_cursorbench_task"] is False
    assert live["cursorbench_target_context_real_evidence_bundle_count_remaining"]==3
    assert live["cursorbench_acceptance_predicate_closed"] is False
    rec=a["cursorbench_real_spent_context_evidence_terminal_reconciliation_20261009_v1"]
    assert rec["cursorbench_membership_delta"]==0
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
