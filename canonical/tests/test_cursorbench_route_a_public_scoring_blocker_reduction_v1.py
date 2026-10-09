import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/"canonical/evidence/CURSORBENCH_PUBLIC_SCORING_SEMANTICS_EVIDENCE_20261009_V1.json"
R=ROOT/"canonical/governance/CURSORBENCH_ROUTE_A_PUBLIC_SCORING_BLOCKER_REDUCTION_20261009_V1.json"

def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()

def test_public_cursorbench_scoring_evidence_narrows_but_does_not_close_route_a():
    e=json.loads(E.read_text(encoding="utf-8"))
    r=json.loads(R.read_text(encoding="utf-8"))
    assert blob(E)==r["source"]["git_blob_sha"]
    d=e["deduction"]
    assert d["public_metric_family_bound"] is True
    assert d["exact_cursorbench_4_0_scoring_decomposition_bound"] is False
    assert d["exact_cursorbench_4_0_metric_continuity_from_3_x_proved"] is False
    assert d["threshold_lower_bound_route_ready"] is False
    a=r["route_A_threshold_lower_bound"]
    assert a["sufficient"] is True
    assert a["current_state"]=="OPEN_BLOCKED"
    assert len(a["exact_remaining_blocker"])==3
    assert r["route_B_scope_complete_stronger_proof"]["remains_current_active_lane"] is True
    assert r["accounting"]["acceptance_credit_delta"]==0
    assert r["accounting"]["terminal_credit_delta"]==0
