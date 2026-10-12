import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/JIT_KNOWLEDGE_CAPABILITY_NONSMUGGLING_BOUNDARY_20261007_V1.json"

def load():
    return json.loads(P.read_text(encoding="utf-8"))

def test_goal_unchanged():
    assert load()["terminal_objective"]=="PERMANENTLY_INTERNALIZE_CONFIGURE_VERIFY_AND_OWN_ALL_USEFUL_OPUS_5_5_CAPABILITIES_AT_EQUAL_OR_BETTER_LEVEL__KNOWLEDGE_EXTERNAL_JIT_ONLY"

def test_opaque_dynamic_solver_not_knowledge():
    d=load()
    assert any("DYNAMICALLY SOLVING THE TARGET TASK" in x or "DYNAMICALLY_SOLVING_THE_TARGET_TASK" in x for x in d["not_admissible_as_mere_knowledge"])

def test_exogenous_discriminator_remains_allowed():
    d=load()
    assert any("EXOGENOUS WORLD STATE" in x or "EXOGENOUS_WORLD_STATE" in x for x in d["admissible_jit_knowledge"])

def test_counterfactual_provider_test_present():
    d=load()
    assert "GENERIC_INSTRUCTION_FOLLOW_EXTERNAL_OUTPUT" in d["ownership_counterfactual_test"]["rule"] or "GENERIC INSTRUCTION FOLLOW EXTERNAL OUTPUT" in d["ownership_counterfactual_test"]["rule"]

def test_pstar_zero_cannot_outsource_policy():
    d=load()
    assert "OPAQUE EXTERNAL JIT CALL" in d["relation_to_p_star"]["disallowed_shortcut"] or "OPAQUE_EXTERNAL_JIT_CALL" in d["relation_to_p_star"]["disallowed_shortcut"]

def test_zero_credit():
    d=load()
    for k,v in d["accounting"].items():
        if k.endswith("_delta"):
            assert v==0
