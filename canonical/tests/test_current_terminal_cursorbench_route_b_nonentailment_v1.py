import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
THM=ROOT/"canonical/governance/CURSORBENCH_ROUTE_B_CURRENT_EVIDENCE_NONENTAILMENT_20261009_V1.json"
VER=ROOT/"canonical/verification/CURSORBENCH_ROUTE_B_CURRENT_EVIDENCE_NONENTAILMENT_INDEPENDENT_VERIFICATION_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_terminal_binds_route_b_nonentailment_without_false_externality():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    src=a["authoritative_sources"]["cursorbench_route_b_current_evidence_nonentailment_20261009_v1"]
    assert blob(THM)==src["git_blob_sha"]
    assert blob(VER)==src["independent_verification"]["git_blob_sha"]
    live=a["live_truth"]
    assert live["cursorbench_route_b_current_evidence_entails_scope_complete_positive_cover"] is False
    assert live["cursorbench_route_b_current_evidence_entails_scope_complete_cover_failure"] is False
    assert live["cursorbench_route_b_current_evidence_information_underdetermined"] is True
    assert live["cursorbench_route_b_more_internal_mechanism_without_new_adequacy_information_authorized"] is False
    assert live["cursorbench_route_b_load_bearing_escape_classes"]==[
        "CONSTRUCTIVE_SCOPE_THEOREM",
        "TARGET_RELEVANT_COMPLETE_ADEQUACY_EVIDENCE",
        "ROUTE_A_SCORE_LOWER_BOUND",
    ]
    rec=a["cursorbench_route_b_current_evidence_nonentailment_reconciliation_20261009_v1"]
    assert rec["route_b_impossible_claimed"] is False
    assert rec["route_b_closed_claimed"] is False
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
    assert a["live_truth"]["cursorbench_positive_adequacy_cover_closed"] is False
    assert a["live_truth"]["cursorbench_acceptance_predicate_closed"] is False
