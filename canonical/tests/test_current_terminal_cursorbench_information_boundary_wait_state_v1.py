import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
W=ROOT/"canonical/governance/CURSORBENCH_CURRENT_INFORMATION_BOUNDARY_WAIT_STATE_RECONCILIATION_20261010_V1.json"

def blob(path):
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode()+b"\0"+data)
    return h.hexdigest()

def test_cursorbench_information_boundary_wait_state_is_live_without_credit():
    p=json.loads(P.read_text())
    w=json.loads(W.read_text())
    lt=p["live_truth"]
    assert p["pointer_revision"]==128
    assert blob(W)=="4f1df11b30d9b69090c31e234449975eb7cdfd89"
    assert lt["cursorbench_information_boundary_wait_state_bound"] is True
    assert lt["cursorbench_information_boundary_wait_state_git_blob_sha"]==blob(W)
    assert lt["cursorbench_current_active_lane"]=="DORMANT_INFORMATION_BOUNDARY__EVENT_DRIVEN_REACTIVATION"
    assert lt["cursorbench_internal_execution_state"]=="DORMANT_INFORMATION_BOUNDARY"
    assert lt["cursorbench_immediate_internal_cursorbench_job"] is None
    assert lt["cursorbench_route_a_same_static_public_surface_work_authorized_now"] is False
    assert lt["cursorbench_target_membership_same_public_metadata_work_authorized_now"] is False
    assert lt["cursorbench_constructive_scope_same_information_retry_authorized_now"] is False
    assert lt["cursorbench_sixth_region_work_authorized_now"] is False
    assert len(lt["cursorbench_reactivation_triggers"])==4
    assert lt["cursorbench_positive_adequacy_cover_closed"] is False
    assert lt["cursorbench_threshold_lower_bound_route_state"]=="OPEN_BLOCKED"
    assert lt["cursorbench_threshold_lower_bound_route_remaining_blocker_count"]==2
    assert w["accounting"]["acceptance_credit_delta"]==0
    assert w["accounting"]["terminal_credit_delta"]==0
    rec=p["cursorbench_information_boundary_wait_state_reconciliation_20261010_v1"]
    assert rec["source"]["git_blob_sha"]==blob(W)
    assert rec["score_threshold_proved"] is False
    assert rec["whole_positive_cover_closed"] is False
    assert rec["target_membership_created"] is False
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
