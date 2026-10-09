import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PATHS={
 "q":"canonical/governance/R2_FINANCE_SEMANTIC_WAKE_INFORMATION_QUOTIENT_20261009_V1.json",
 "qv":"canonical/verification/R2_FINANCE_SEMANTIC_WAKE_INFORMATION_QUOTIENT_REMOTE_VERIFY_20261009_V1.json",
 "sched":"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V56.json",
 "r2":"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
 "one":"canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json",
 "term":"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
}
EXPECTED={
 "q":"cb56e4cda2d8f9fec7f19cb0f82dea1afec1a6ff",
 "qv":"e89e7b823ab114897c0a63e1e0ec7c2cb2c7545f",
 "sched":"4a2dbec85d6f863f182d8afb2e41cd0afc6b0cd4",
 "r2":"0145af60a86b82f12968a46f6196e59fff25bf48",
 "one":"2647c87c6507e30b2d2d4a752eeeb6a5e9af19e7",
 "term":"630274f98c80a18965e908fd65eb87d4d9e37911",
}
def blob(path):
    data=path.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(data)).encode()+b"\0"+data); return h.hexdigest()
def load(k):
    p=ROOT/PATHS[k]; assert blob(p)==EXPECTED[k], (k,blob(p),EXPECTED[k])
    return json.loads(p.read_text(encoding="utf-8"))

def test_v58_projection_rebased_over_namespace_guard():
    q=load("q"); qv=load("qv"); sched=load("sched"); r2=load("r2"); one=load("one"); term=load("term")
    assert qv["result"]["assertions_passed"]==2
    assert len(q["normalization_map"])==11
    assert len(set(q["normalization_map"].values()))==3
    assert r2["status"].startswith("ACTIVE_CURRENT_R2_AUTHORITY__V58__")
    assert r2["scheduler_cut"]["git_blob_sha"]==EXPECTED["sched"]
    cell=r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
    assert cell["state"]=="INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT"
    assert cell["information_theoretic_externality_proved"] is False
    assert one["authority"]["current_r2_pointer_git_blob_sha"]==EXPECTED["r2"]
    assert one["authority"]["r2_finance_wake_effect_class_count"]==3
    assert one["authority"]["r2_finance_tail_closed"] is False
    assert term["pointer_revision"]==103
    assert "ROOT_NAMESPACE_COLLISION_GUARDED" in term["status"]
    bridge=term["authoritative_sources"]["coverage_root_namespace_bridge"]
    assert bridge["git_blob_sha"]=="fd45e0fcfdd238cdae022fc58ce418c9151186f1"
    assert term["live_truth"]["current_r2_pointer_git_blob_sha"]==EXPECTED["r2"]
    assert term["live_truth"]["r2_finance_wake_decision_effect_class_count"]==3
    assert term["live_truth"]["r2_primary_internal_unsolved_count"]==1
    assert term["live_truth"]["r2_finance_semantic_tail_closed"] is False
    assert term["live_truth"]["terminal"] is False
    rec=term["r2_v58_finance_wake_information_quotient_reconciliation"]
    assert rec["root_namespace_collision_guard_preserved"] is True
    assert rec["r2_primary_internal_unsolved_count_before"]==1
    assert rec["r2_primary_internal_unsolved_count_after"]==1
    assert rec["terminal_credit_delta"]==0
