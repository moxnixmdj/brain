import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/K6_DECISION_PARTITION_REFINEMENT_PROJECTION_20261006_V2.json"
def load(): return json.loads(P.read_text(encoding="utf-8"))
def test_one_unbound_generator_remains():
    d=load(); c=d["candidate_global_compression"]
    assert c["verified_owned_generator_count"]==5
    assert c["unbound_semantic_generator_count"]==1
    assert c["unbound_semantic_generator"]=="K6_TARGET_RELATIVE_DECISION_PARTITION_REFINEMENT"
def test_faithful_world_model_requirement_deleted():
    d=load()
    assert d["truth_repair"]["deleted_overstrong_requirement"]=="FAITHFUL_OR_GENERAL_TASK_SUFFICIENT_WORLD_MODEL"
def test_exact_stopping_condition_is_common_acceptability():
    d=load(); n=d["k6_normal_form"]
    assert "INTERSECTION" in n["stopping_condition"]
    assert "NONEMPTY" in n["stopping_condition"]
def test_v_d_p_unified_and_u_not_magic():
    d=load(); s=d["information_sources"]
    assert len(s["unified_refinement_sources"])==3
    assert "ABSTENTION" in s["uncertainty_rule"]
    assert "ACTION" in s["uncertainty_rule"]
def test_fail_closed_zero_credit():
    d=load()
    assert d["accounting"]["terminal_credit_delta"]==0
    assert any("NO_CLAIM_THE_REFINEMENT_OPERATOR_IS_IMPLEMENTED_OR_OWNED"==x for x in d["hard_nonclaims"])
