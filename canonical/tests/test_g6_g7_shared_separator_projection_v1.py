import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def test_current_two_unbound_generators():
    d=load("canonical/governance/TERMINAL_GENERATOR_BASIS_CANDIDATE_20261006_V1.json")
    unbound=[g["id"] for g in d["generators"] if g["status"]=="UNBOUND_RESIDUAL_GENERATOR"]
    assert unbound==[
        "G6_TASK_CONDITIONED_JUDGMENT_PLANNING_REASONING_AND_SYNTHESIS",
        "G7_MULTIMODAL_PERCEPTION_ACTION_AND_ARTIFACT_INTERFACE",
    ]

def test_g0_reduces_to_s0():
    d=load("canonical/governance/G0_DEPENDENCY_COMPRESSION_V1.json")
    assert d["new_state"]["independent_mechanism_residual"] is False
    assert "S0_RAW_CONTEXT_TO_TYPED_FACT_TEMPLATE_AND_EFFECT_MODEL" in d["dependencies"]

def test_global_graph_shared_projection():
    d=load("canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json")
    assert d["open_mechanism_residual_count"]==0
    assert set(d["proof_only_shared_cross_lane_mechanisms"])=={
        "S0_RAW_CONTEXT_TO_TYPED_FACT_TEMPLATE_AND_EFFECT_MODEL",
        "G0_NOVEL_TYPED_TEMPLATE_AND_EFFECT_MODEL_SYNTHESIS",
    }

def test_saturation_tails_are_semantic():
    d=load("canonical/governance/S0_G0_ZERO_REALITY_SATURATION_V1.json")
    tails=d["surviving_unmeasured_tails"]
    assert len(tails)==3
    assert any("TEXT_SEMANTICS" in x for x in tails)
    assert any("VISUAL_OR_MULTIMODAL_SEMANTIC_BINDING" in x for x in tails)
    assert any("NOVEL_PRIMITIVE" in x for x in tails)

def test_information_cut_targets_separator_kernel():
    d=load("canonical/governance/MINIMUM_CAPABILITY_KERNEL_INFORMATION_CUT_20261006_V1.json")
    assert d["scheduler_consequence"]["new_primary_object"]=="MINIMUM_INFORMATION_AND_OPERATOR_SEPARATOR_KERNEL"

def test_projection_is_zero_credit_candidate():
    d=load("canonical/governance/G6_G7_SHARED_SEPARATOR_PROJECTION_20261006_V1.json")
    assert d["candidate_basis"]["candidate_generator_count"]==6
    assert d["candidate_basis"]["candidate_owned_count"]==5
    assert d["candidate_basis"]["candidate_unbound_count"]==1
    assert d["accounting"]["terminal_credit_delta"]==0
