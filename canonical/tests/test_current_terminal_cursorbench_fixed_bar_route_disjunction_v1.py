import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REC=ROOT/"canonical/governance/CURSORBENCH_FIXED_BAR_ROUTE_DISJUNCTION_RECONCILIATION_20261009_V1.json"
VERIFY=ROOT/"canonical/verification/CURSORBENCH_FIXED_BAR_ROUTE_DISJUNCTION_INDEPENDENT_VERIFICATION_20261009_V1.json"

def blob(path: Path) -> str:
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode("ascii")+b"\0"+data)
    return h.hexdigest()

def test_terminal_authority_binds_cursorbench_fixed_bar_route_disjunction_without_credit():
    auth=json.loads(AUTH.read_text(encoding="utf-8"))
    rec=json.loads(REC.read_text(encoding="utf-8"))
    verify=json.loads(VERIFY.read_text(encoding="utf-8"))

    src=auth["authoritative_sources"]["cursorbench_fixed_bar_route_disjunction_20261009_v1"]
    assert blob(REC)==src["git_blob_sha"]=="7e9e5c1070696888913bc3189ffd07ffe2746f20"
    assert blob(VERIFY)==src["independent_verification"]["git_blob_sha"]=="8387e09408c80460f5c088435f74ac6732fc2962"
    assert verify["result"]["tests_passed"]==1
    assert verify["result"]["tests_failed"]==0

    live=auth["live_truth"]
    assert live["cursorbench_fixed_bar_route_disjunction_verified"] is True
    assert live["cursorbench_threshold_lower_bound_route_defined"] is True
    assert live["cursorbench_threshold_lower_bound_route_sufficient"] is True
    assert live["cursorbench_threshold_lower_bound_route_ready"] is False
    assert live["cursorbench_whole_scope_positive_adequacy_logically_necessary_for_fixed_bar"] is False
    assert live["cursorbench_scope_complete_stronger_proof_route_sufficient"] is True
    assert live["cursorbench_current_active_proof_lane"]=="ROUTE_B_SCOPE_COMPLETE_STRONGER_PROOF"
    assert "EXACT_CURSORBENCH_4_0_SCORE_DECOMPOSITION" in live["cursorbench_threshold_lower_bound_route_blocker"]
    assert live["cursorbench_positive_adequacy_cover_closed"] is False
    assert live["cursorbench_dominance_closed"] is False
    assert live["cursorbench_acceptance_predicate_closed"] is False
    assert len(live["cursorbench_typed_acceptance_remaining_external_membership_atoms"])==4

    assert rec["route_disjunction"]["route_A_threshold_lower_bound"]["current_state"]=="OPEN_BLOCKED"
    assert rec["route_disjunction"]["route_B_scope_complete_stronger_proof"]["current_state"]=="OPEN_INTERNAL"
    assert rec["accounting"]["acceptance_credit_delta"]==0
    assert rec["accounting"]["terminal_credit_delta"]==0
    assert auth["pointer_revision"]==80
