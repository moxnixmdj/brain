import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/"canonical/evidence/CURSORBENCH_4_0_CURRENT_ACCURACY_METRIC_IDENTITY_EVIDENCE_20261009_V1.json"
R=ROOT/"canonical/governance/CURSORBENCH_ROUTE_A_4_0_METRIC_IDENTITY_REDUCTION_20261009_V1.json"
P=ROOT/"canonical/governance/CURSORBENCH_ROUTE_A_PUBLIC_SCORING_BLOCKER_REDUCTION_20261009_V1.json"

def git_blob_sha(path):
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode()+b"\0"+data)
    return h.hexdigest()

def test_current_4_0_metric_identity_closes_only_accuracy_name():
    e=json.loads(E.read_text())
    r=json.loads(R.read_text())
    p=json.loads(P.read_text())
    assert r["predecessor"]["git_blob_sha"]==git_blob_sha(P)
    assert p["route_A_threshold_lower_bound"]["current_state"]=="OPEN_BLOCKED"
    assert len(p["route_A_threshold_lower_bound"]["exact_remaining_blocker"])==3
    assert e["deduction"]["cursorbench_4_0_metric_identity"]=="ACCURACY_PERCENT"
    assert e["deduction"]["cursorbench_4_0_metric_identity_bound"] is True
    assert e["deduction"]["requires_assuming_3_x_and_4_0_scoring_are_identical"] is False
    assert e["deduction"]["exact_per_task_grader_output_domain_bound"] is False
    assert e["deduction"]["exact_per_task_score_contribution_rule_bound"] is False
    assert e["deduction"]["exact_aggregation_weights_or_formula_bound"] is False
    assert r["route_A_threshold_lower_bound"]["metric_identity"].startswith("CLOSED__")
    assert len(r["route_A_threshold_lower_bound"]["exact_remaining_blocker"])==2
    assert r["route_A_threshold_lower_bound"]["threshold_lower_bound_ready"] is False
    assert r["accounting"]["acceptance_credit_delta"]==0
    assert r["accounting"]["terminal_credit_delta"]==0
