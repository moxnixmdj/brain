import json
from pathlib import Path

from canonical.runtime.k6_policy_cover_information_boundary_current_v1 import verify


ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "canonical/governance/K6_POLICY_COVER_INFORMATION_BOUNDARY_CURRENT_20261006_V1.json"


def load():
    return json.loads(P.read_text(encoding="utf-8"))


def test_current_normal_form_verifier_passes():
    out = verify()
    assert out["pass"] is True, out
    assert out["owned_implementation_generator_count"] == 5
    assert out["unbound_preproof_implementation_generator_count"] == 0
    assert out["conditional_information_boundary_count"] == 1
    assert out["terminal_credit_delta"] == 0


def test_capability_and_information_gap_firewall_is_explicit():
    d = load()
    fw = d["first_principles_firewall"]
    assert "F(w)_IS_EMPTY" in fw["capability_gap"]
    assert "CAPABILITY" in fw["capability_gap"]
    assert "F(w)_IS_NONEMPTY" in fw["information_gap"]
    assert "INFORMATION" in fw["information_gap"]


def test_tau_replaces_world_identity_as_finite_information_target():
    d = load()
    f = d["finite_information_target"]
    assert f["exact_minimum_semantic_label_count"] == "tau"
    assert f["tight_fixed_length_policy_index_bits"] == "CEIL_LOG2_tau"
    assert "tau=N_WORLDS" in f["predecessor_special_case"]


def test_generic_k6_implementation_is_forbidden_preproof():
    d = load()
    assert d["current_normal_form"]["current_unbound_preproof_implementation_generator_count"] == 0
    assert d["current_normal_form"]["conditional_information_interface"]["not_a_capability_box"] is True
    assert "DO_NOT_IMPLEMENT_GENERIC_K6_AS_A_SIXTH_CAPABILITY_GENERATOR_PREPROOF." in d["scheduler_consequence"]
    assert d["execution_authority"] is False
    assert d["promotion_authority"] is False
