import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
A=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
R=ROOT/"canonical/governance/CURSORBENCH_TYPED_SPECIALIST_TARGET_MEMBERSHIP_TRANSFER_TERMINAL_RECONCILIATION_20261009_V1.json"
T=ROOT/"canonical/governance/CURSORBENCH_TYPED_SPECIALIST_TARGET_MEMBERSHIP_TRANSFER_FALSIFICATION_20261009_V1.json"
V=ROOT/"canonical/verification/CURSORBENCH_TYPED_SPECIALIST_TARGET_MEMBERSHIP_TRANSFER_FALSIFICATION_INDEPENDENT_VERIFICATION_20261009_V1.json"

def blob(path):
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode()+b"\0"+data)
    return h.hexdigest()

def test_terminal_scheduler_advances_only_after_verified_transfer_falsification():
    a=json.loads(A.read_text())
    r=json.loads(R.read_text())
    assert a["pointer_revision"]==99
    assert blob(T)=="d3f9801a9ef130ed0140a558cd37e0815e80693f"
    assert blob(V)=="620ed7c5447797a60dfcacc23c2531c96518df54"
    assert blob(R)=="520875feeb5bb1ec5d1adb08d5daea1d7d846409"
    assert r["predecessor_terminal_authority"]["git_blob_sha"]=="3040629444e2d1dea179424baf4d2985eca3db6e"
    assert r["predecessor_terminal_authority"]["pointer_revision"]==98
    lt=a["live_truth"]
    assert lt["cursorbench_typed_specialist_public_metadata_transfer_falsified"] is True
    assert lt["cursorbench_actual_private_target_membership_route"]=="EVENT_DRIVEN_ONLY_UNDER_CURRENT_OWNER_POLICY"
    assert lt["cursorbench_public_task_prompt_repository_search_authorized_now"] is False
    assert lt["cursorbench_scope_complete_transfer_from_public_metadata_proved"] is False
    assert lt["cursorbench_first_positive_region_hidden_task_membership_proved"] is False
    assert lt["cursorbench_positive_adequacy_cover_closed"] is False
    assert lt["cursorbench_current_active_lane"]=="ROUTE_B_SCOPE_COMPLETE_STRONGER_PROOF"
    assert lt["cursorbench_next_proof_object"].startswith("CODING_SPEC_SCOPE_COMPLETE_AUTHENTICATED_POLICY_ADEQUACY_COVER")
    assert a["cursorbench_typed_specialist_target_membership_transfer_falsification_reconciliation_20261009_v1"]["terminal_credit_delta"]==0

def test_reconciliation_preserves_scope_and_zero_credit():
    a=json.loads(A.read_text())
    r=json.loads(R.read_text())
    assert a["live_truth"]["cursorbench_scope_completeness_proved"] is True
    assert "CURSORBENCH_SCOPE_COMPLETENESS_PROVED" in r["preserved_truth"]
    assert "CURSORBENCH_POSITIVE_ADEQUACY_COVER_REMAINS_OPEN" in r["preserved_truth"]
    assert r["accounting"]["acceptance_credit_delta"]==0
    assert r["accounting"]["terminal_credit_delta"]==0
    assert r["promotion_authority"] is False
    assert r["terminal_authority"] is False
