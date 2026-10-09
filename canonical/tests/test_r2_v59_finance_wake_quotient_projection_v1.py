import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PATHS={
"q":"canonical/governance/R2_FINANCE_SEMANTIC_WAKE_INFORMATION_QUOTIENT_20261009_V2.json",
"qv":"canonical/verification/R2_FINANCE_SEMANTIC_WAKE_INFORMATION_QUOTIENT_REMOTE_VERIFY_20261009_V2.json",
"sched":"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V56.json",
"r2":"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
"one":"canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json",
"term":"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"}
EXPECTED={"q":"bb58795676f23e621d191cb9a30a5394a29c8ef6","qv":"3482b08dc8c2c75122b4620f564aaee993e4a646","sched":"1adc7e890100c5278b298dcf4fbec196e6c472ae","r2":"f2c982a62a4aab4dd82c77d2cb28eec01716809e","one":"566835669259307e87668f029738113b86c39cdf","term":"4ac58e8866f4da3d0f06c7690b1568bf8091cf16"}
def blob(p):
 d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def load(k):
 p=ROOT/PATHS[k]; assert blob(p)==EXPECTED[k],(k,blob(p),EXPECTED[k]); return json.loads(p.read_text())
def test_v59_projection_preserves_semantic_gains_and_stays_fail_closed():
 q=load("q"); qv=load("qv"); s=load("sched"); r2=load("r2"); one=load("one"); term=load("term")
 assert qv["result"]["assertions_passed"]==1
 assert len(q["normalization_map"])==11 and len(set(q["normalization_map"].values()))==3
 assert r2["status"].startswith("ACTIVE_CURRENT_R2_AUTHORITY__V59__")
 assert r2["scheduler_cut"]["git_blob_sha"]==EXPECTED["sched"]
 cell=r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
 ids={x["id"] for x in cell["verified_positive_subregions"]}
 assert "BOUND_REGCAP_LOSS_CUSHION_SAME_SENTENCE_CONTEXTUAL_RELATIVE_SELECTION" in ids
 assert "BOUND_REGCAP_CONTEXTUAL_SOURCE_FACT_PROOFS" in ids
 assert cell["state"]=="INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT"
 assert cell["information_theoretic_externality_proved"] is False
 assert cell["wake_information_quotient"]["decision_effect_class_count"]==3
 assert one["authority"]["current_r2_pointer_git_blob_sha"]==EXPECTED["r2"]
 assert one["authority"]["r2_v58_contextual_regcap_gains_preserved"] is True
 assert one["authority"]["r2_finance_tail_closed"] is False
 assert term["pointer_revision"]==104
 assert "ROOT_NAMESPACE_COLLISION_GUARDED" in term["status"]
 assert term["authoritative_sources"]["coverage_root_namespace_bridge"]["git_blob_sha"]=="fd45e0fcfdd238cdae022fc58ce418c9151186f1"
 assert "r2_v58_regcap_contextual_grounding_reconciliation_20261009_v1" in term
 assert term["live_truth"]["current_r2_pointer_git_blob_sha"]==EXPECTED["r2"]
 assert term["live_truth"]["r2_v58_contextual_regcap_gains_preserved"] is True
 assert term["live_truth"]["r2_finance_wake_decision_effect_class_count"]==3
 assert term["live_truth"]["r2_primary_internal_unsolved_count"]==1
 assert term["live_truth"]["r2_finance_semantic_tail_closed"] is False
 assert term["live_truth"]["terminal"] is False
 rec=term["r2_v59_finance_wake_information_quotient_reconciliation"]
 assert rec["root_namespace_collision_guard_preserved"] is True
 assert rec["v58_contextual_regcap_gains_preserved"] is True
 assert rec["r2_primary_internal_unsolved_count_before"]==rec["r2_primary_internal_unsolved_count_after"]==1
 assert rec["terminal_credit_delta"]==0
