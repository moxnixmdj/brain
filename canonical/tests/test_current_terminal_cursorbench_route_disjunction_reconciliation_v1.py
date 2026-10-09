import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REC=ROOT/"canonical/governance/CURSORBENCH_FIXED_BAR_ROUTE_DISJUNCTION_RECONCILIATION_20261009_V1.json"
VER=ROOT/"canonical/verification/CURSORBENCH_FIXED_BAR_ROUTE_DISJUNCTION_INDEPENDENT_VERIFICATION_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_current_terminal_binds_cursorbench_route_disjunction_without_credit():
    a=json.loads(AUTH.read_text()); r=json.loads(REC.read_text())
    s=a["authoritative_sources"]["cursorbench_fixed_bar_route_disjunction_20261009_v1"]
    assert blob(REC)==s["git_blob_sha"]
    assert blob(VER)==s["independent_verification"]["git_blob_sha"]
    live=a["live_truth"]
    assert live["cursorbench_threshold_lower_bound_route_sufficient"] is True
    assert live["cursorbench_threshold_lower_bound_route_whole_scope_adequacy_required"] is False
    assert live["cursorbench_threshold_lower_bound_route_state"]=="OPEN_BLOCKED"
    assert live["cursorbench_stronger_scope_complete_route_state"]=="OPEN_INTERNAL"
    assert live["cursorbench_current_active_lane"]=="ROUTE_B_SCOPE_COMPLETE_STRONGER_PROOF"
    assert live["cursorbench_positive_adequacy_cover_closed"] is False
    assert live["cursorbench_acceptance_predicate_closed"] is False
    assert r["accounting"]["acceptance_credit_delta"]==0
    assert r["accounting"]["terminal_credit_delta"]==0
