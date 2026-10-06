import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "canonical/governance/G6_G7_SINGLE_SEMANTIC_RESIDUAL_REDUCTION_20261006_V1.json"

EXPECTED_SOURCES = {
    "generator_basis": "87909e9defe4ec12627c552c80cabb873c0c5f7c",
    "observable_trace_superset": "333bdc8306a19f005a600a47b415a4bd9cf9868c",
    "image_surface_mapping": "fceb02c70aa49b5e07ba7dc49fa092dad2570fc8",
    "role_basis_falsification": "6e270d6715e20b6f9a2c19f7368bbda27b545780",
}


def load():
    return json.loads(P.read_text(encoding="utf-8"))


def test_exact_source_bindings_are_frozen():
    d = load()
    got = {
        k: v["git_blob_sha"]
        for k, v in d["source_bindings"].items()
    }
    assert got == EXPECTED_SOURCES


def test_candidate_reduces_two_unbound_semantic_labels_to_one():
    d = load()
    c = d["candidate_compression"]
    assert c["prior_generator_count"] == 7
    assert c["prior_unbound_semantic_generator_count"] == 2
    assert c["candidate_generator_count"] == 6
    assert c["candidate_unbound_semantic_generator_count"] == 1
    assert c["verified_owned_generator_count_preserved"] == 5


def test_new_residual_is_trace_policy_not_modality_label():
    d = load()
    g = d["reduction"]["new_residual_generator"]
    assert g["id"] == "G6U_TASK_CONDITIONED_TRACE_POLICY_INFERENCE_AND_PROPOSAL"
    assert g["status"] == "UNBOUND_RESIDUAL_GENERATOR"
    assert "MECHANICAL_INPUT_OUTPUT_CODEC_OR_EFFECT_TRANSPORT" in g["does_not_own"]


def test_resource_and_ownership_remain_load_bearing():
    d = load()
    r = d["terminally_load_bearing_remaining_problem"]
    assert "RESOURCE" in r["resource"]
    assert "BRAIN_OWNED" in r["ownership"]


def test_no_performance_or_terminal_credit_is_created():
    d = load()
    assert "NO_CLAIM_G6U_IS_IMPLEMENTED_OR_OWNED" in d["hard_nonclaims"]
    assert "NO_CLAIM_A_LOCAL_QWEN_OR_ANY_OTHER_MODEL_EQUALS_OPUS55" in d["hard_nonclaims"]
    for k, v in d["accounting"].items():
        if k.endswith("_delta"):
            assert v == 0
