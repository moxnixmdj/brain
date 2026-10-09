import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REC=ROOT/"canonical/governance/CURSORBENCH_ROUTE_A_PUBLIC_SCORING_BLOCKER_REDUCTION_20261009_V1.json"
VER=ROOT/"canonical/verification/CURSORBENCH_ROUTE_A_PUBLIC_SCORING_BLOCKER_REDUCTION_INDEPENDENT_VERIFICATION_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_terminal_authority_binds_scoring_reduction_without_promoting_route_a():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    s=a["authoritative_sources"]["cursorbench_route_a_public_scoring_blocker_reduction_20261009_v1"]
    assert blob(REC)==s["git_blob_sha"]
    assert blob(VER)==s["independent_verification"]["git_blob_sha"]
    live=a["live_truth"]
    assert live["cursorbench_public_scoring_metric_family_bound"] is True
    assert live["cursorbench_exact_4_0_scoring_decomposition_bound"] is False
    assert live["cursorbench_exact_4_0_metric_continuity_from_3_x_proved"] is False
    assert live["cursorbench_threshold_lower_bound_route_state"]=="OPEN_BLOCKED"
    assert live["cursorbench_threshold_lower_bound_route_remaining_blocker_count"]==3
    assert len(live["cursorbench_threshold_lower_bound_route_remaining_blockers"])==3
    assert live["cursorbench_current_active_lane"]=="ROUTE_B_SCOPE_COMPLETE_STRONGER_PROOF"
    rec=a["cursorbench_route_a_public_scoring_blocker_reduction_reconciliation_20261009_v1"]
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
