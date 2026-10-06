import json
from pathlib import Path

from canonical.runtime.k6_minimum_adequate_policy_cover_v1 import (
    PolicyCoverError,
    assignment_from_cover,
    compile_falsifiers,
    disjoint_separator_case,
    minimum_fixed_length_bits,
    minimum_policy_cover,
    pairwise_compatibility_trap,
    universal_policy_case,
    verify_assignment,
)


def test_universal_common_policy_requires_no_new_separator():
    out = universal_policy_case()
    assert out["tau"] == 1
    assert out["bits"] == 0
    assert out["assignment_valid"] is True


def test_disjoint_worlds_recover_one_bit_separator_lower_bound():
    out = disjoint_separator_case()
    assert out["tau"] == 2
    assert out["bits"] == 1


def test_pairwise_compatibility_is_not_global_sufficiency():
    out = pairwise_compatibility_trap()
    assert out["pairwise_intersections_all_nonempty"] is True
    assert out["global_common_policy_exists"] is False
    assert out["tau"] == 2


def test_minimum_cover_constructs_valid_policy_index_assignment():
    worlds = ("w0", "w1", "w2", "w3")
    policies = ("p0", "p1", "p2")
    adequate = {
        "w0": ("p0",),
        "w1": ("p0", "p1"),
        "w2": ("p1",),
        "w3": ("p2",),
    }
    cover = minimum_policy_cover(worlds, policies, adequate)
    assert len(cover) == 3
    assignment = assignment_from_cover(worlds, adequate, cover)
    assert verify_assignment(worlds, adequate, assignment) is True


def test_stochastic_policy_can_be_a_single_policy_element():
    worlds = ("w0", "w1")
    policies = ("stochastic_mix", "det0", "det1")
    adequate = {
        "w0": ("stochastic_mix", "det0"),
        "w1": ("stochastic_mix", "det1"),
    }
    cover = minimum_policy_cover(worlds, policies, adequate)
    assert cover == ("stochastic_mix",)
    assert minimum_fixed_length_bits(len(cover)) == 0


def test_fail_closed_when_world_has_no_adequate_owned_policy():
    try:
        minimum_policy_cover(("w0",), ("p0",), {"w0": ()})
    except PolicyCoverError as exc:
        assert str(exc) == "NO_ADEQUATE_POLICY:w0"
    else:
        raise AssertionError("expected PolicyCoverError")


def test_falsifier_bundle_zero_credit():
    out = compile_falsifiers()
    assert out["status"] == "PASS__FINITE_K6_MINIMUM_POLICY_COVER_FALSIFIERS"
    assert out["full_world_identification_not_necessary"] is True
    assert out["separator_lower_bound_recovered"] is True
    assert out["pairwise_compatibility_insufficient"] is True
    assert out["terminal_credit"] is False


def test_governance_generalizes_current_k6_information_cut_without_deleting_it():
    root = Path(__file__).resolve().parents[2]
    p = root / "canonical/governance/K6_MINIMUM_ADEQUATE_POLICY_COVER_THEOREM_20261006_V1.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["source_bindings"]["k6_information_resource_cut"]["git_blob_sha"] == "b5b99aa056011139396ab5358dfe8763ff4d7d7f"
    rel = d["relation_to_current_k6_information_cut"]
    assert "tau=N" in rel["special_case"]
    assert "tau_CAN_BE_STRICTLY_LESS_THAN_N" in rel["strictness"]
    assert d["candidate_compression"]["new_information_object"] == "K6P_RESOURCE_BOUNDED_ADEQUATE_POLICY_INDEX_ACQUISITION"
    assert d["accounting"]["terminal_credit_delta"] == 0


def test_governance_refines_current_decision_quotient_as_special_case():
    root = Path(__file__).resolve().parents[2]
    p = root / "canonical/governance/K6_MINIMUM_ADEQUATE_POLICY_COVER_THEOREM_20261006_V1.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["source_bindings"]["current_decision_quotient"]["git_blob_sha"] == "03baddc27d5ee9dd73656fdd801251e1f4fd8cc6"
    rel = d["relation_to_current_decision_quotient"]
    assert "ONE_STEP_POLICY_ELEMENT" in rel["deterministic_action_special_case"]
    assert "MINIMUM_ADEQUATE_POLICY_COVER_NUMBER_tau" in rel["exact_finite_refinement"]
    assert "STOCHASTIC_BRAIN_OWNED_POLICIES" in rel["policy_generalization"]
