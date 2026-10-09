import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
RED=ROOT/"canonical/governance/CURSORBENCH_ROUTE_A_4_0_METRIC_IDENTITY_REDUCTION_20261009_V1.json"
VER=ROOT/"canonical/verification/CURSORBENCH_ROUTE_A_4_0_METRIC_IDENTITY_INDEPENDENT_VERIFICATION_20261009_V1.json"
EVID=ROOT/"canonical/evidence/CURSORBENCH_4_0_CURRENT_ACCURACY_METRIC_IDENTITY_EVIDENCE_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_terminal_authority_binds_4_0_metric_identity_without_lower_bound_credit():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    src=a["authoritative_sources"]["cursorbench_4_0_metric_identity_reduction_20261009_v1"]
    assert blob(RED)==src["git_blob_sha"]
    assert blob(VER)==src["independent_verification"]["git_blob_sha"]
    assert blob(EVID)==src["evidence"]["git_blob_sha"]
    live=a["live_truth"]
    assert live["cursorbench_4_0_metric_identity_bound"] is True
    assert live["cursorbench_4_0_metric_identity"]=="ACCURACY_PERCENT"
    assert live["cursorbench_threshold_lower_bound_route_state"]=="OPEN_BLOCKED"
    assert live["cursorbench_threshold_lower_bound_route_remaining_blocker_count"]==2
    assert len(live["cursorbench_threshold_lower_bound_route_remaining_blockers"])==2
    assert live["cursorbench_remaining_typed_acceptance_mechanism_gap_count"]==0
    assert live["cursorbench_remaining_typed_acceptance_real_evidence_bundle_count"]==3
    rec=a["cursorbench_4_0_metric_identity_terminal_reconciliation_20261009_v1"]
    assert rec["prior_route_a_blocker_count"]==3
    assert rec["current_route_a_blocker_count"]==2
    assert rec["route_a_ready"] is False
    assert rec["route_b_three_bundle_fallback_preserved"] is True
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
