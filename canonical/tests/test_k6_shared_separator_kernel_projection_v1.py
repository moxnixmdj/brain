import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "canonical/governance/K6_SHARED_SEPARATOR_KERNEL_PROJECTION_20261006_V1.json"

EXPECTED_SOURCES = {
    "generator_basis": "87909e9defe4ec12627c552c80cabb873c0c5f7c",
    "single_semantic_residual": "fe9c5a159fef01d13169c82426f9bacf15d1b0ef",
    "single_semantic_residual_verification": "12202a45268884244f42b5ce7a88e8020a01ecc2",
    "g0_compression": "4b074eece26214405c858312fe4f83e26220c3bc",
    "s0_g0_saturation": "31effb16940e6d5c0c95259871b2e3c00cb5e400",
    "global_obligation_graph": "eebdeb6de3b3cfaed30a3bc991dae0548d25e7f5",
    "information_cut": "2b6c8150db5c635eb34c35c4041b99c7fc9c5dd5",
}


def load():
    return json.loads(P.read_text(encoding="utf-8"))


def test_exact_source_bindings():
    d = load()
    got = {k: v["git_blob_sha"] for k, v in d["source_bindings"].items()}
    assert got == EXPECTED_SOURCES


def test_single_unbound_generator_projection():
    d = load()
    c = d["candidate_global_compression"]
    assert c["current_structural_generator_count"] == 6
    assert c["verified_owned_generator_count"] == 5
    assert c["unbound_semantic_generator_count"] == 1
    assert c["unbound_semantic_generator"] == "K6_TASK_SUFFICIENT_MODEL_AND_SEPARATOR_ACQUISITION"


def test_k6_absorbs_only_semantic_model_separator_work():
    d = load()
    loc = d["localization"]
    assert "GENERAL_TEXT_SEMANTIC_BINDING" in loc["absorbs"]
    assert "RAW_VISUAL_OR_MULTIMODAL_SEMANTIC_BINDING" in loc["absorbs"]
    assert "NOVEL_TYPED_SEMANTIC_STRUCTURE_OR_TEMPLATE_ACQUISITION" in loc["absorbs"]
    assert "PERSISTENT_STATE_STORAGE" in loc["does_not_absorb"]
    assert "VERIFICATION_DEBUGGING_AND_RECOVERY" in loc["does_not_absorb"]
    assert "EXACT_DETERMINISTIC_COMPUTATION" in loc["does_not_absorb"]


def test_information_cut_routes_are_complete_as_declared_normal_form():
    d = load()
    assert [x["id"] for x in d["minimum_separator_routes"]] == [
        "V_ABSOLUTE_VERIFIER_OR_EXPERIMENT",
        "D_AUTHORIZED_DISCRIMINATOR",
        "P_OWNED_PRIOR_OR_MODEL",
        "U_UNCERTAINTY_PRESERVATION",
    ]


def test_fixed_point_attacks_separator_before_prior():
    d = load()
    steps = d["next_falsification_fixed_point"]
    assert "TRY_V_THEN_D_THEN_U_BEFORE_DECLARING_PERSISTENT_PRIOR_INFORMATION_NECESSARY." in steps
    assert any("SMALLEST_PAIR_OF_PRECOMMITMENT_INDISTINGUISHABLE_WORLDS" in x for x in steps)


def test_fail_closed_zero_credit():
    d = load()
    assert d["execution_authority"] is False
    assert d["promotion_authority"] is False
    assert d["fresh_reality_authority"] is False
    assert "NO_CLAIM_K6_IS_IMPLEMENTED_OR_OWNED." in d["hard_nonclaims"]
    assert "NO_CLAIM_V_D_U_ELIMINATE_P_FOR_EVERY_TASK." in d["hard_nonclaims"]
    for k, v in d["accounting"].items():
        if k.endswith("_delta"):
            assert v == 0
