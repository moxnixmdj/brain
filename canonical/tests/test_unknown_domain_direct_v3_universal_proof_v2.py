from fractions import Fraction

from canonical.runtime import unknown_domain_direct_v3_universal_proof_v2 as proof


def test_namespace_total_universal_status_zero_reality():
    out=proof.prove()
    assert out["status"]=="PASS__UNIVERSAL_OVER_EVERY_STRUCTURALLY_VALID_POPULATION_EMITTED_BY_NAMESPACE_TOTAL_GENERATOR_V3"
    assert out["scope"]["population_cases"]==27
    assert out["scope"]["production_cases_generated"]==0
    assert out["fresh_reality_required_for_this_exact_emitted_population_claim"] is False
    assert out["production_execution_information_gain_for_this_exact_emitted_population_claim"]==0
    assert out["exact_subject_blobs"]==proof.EXPECTED_BLOBS


def test_numeric_and_add2_exactness_theorem_is_preserved():
    t=proof.prove()["transfer_proof"]
    assert t["all_six_families_universal"] is True
    assert t["max_transfer_probes"]==2
    assert Fraction(t["affine_min_wrong_support_gap"])==Fraction(57,20)
    assert Fraction(t["complement_min_wrong_support_gap"])==Fraction(19,4)
    assert Fraction(t["sat_mono_conservative_min_wrong_support_gap"])>0
    assert Fraction(t["sign_shifted_distractor_min_on_negative_probe"])==Fraction(5,4)
    assert Fraction(t["step_wrong_side_margin"])==Fraction(51,20)
    assert Fraction(t["add2_min_wrong_support_gap"])==Fraction(3,2)
    assert t["add2_exact_float_order_repaired_by_v3"] is True


def test_namespace_proof_has_no_probability_assumption():
    n=proof.prove()["namespace_proof"]
    assert n["probabilistic_collision_freeness_assumed"] is False
    assert n["role_role_collision_emitted"] is False
    assert n["distractor_distractor_collision_emitted"] is False
    assert n["duplicate_transfer_probe_id_emitted"] is False
    assert n["duplicate_abstention_probe_id_emitted"] is False
    assert n["nonidentifiable_action_collision_emitted"] is False
    assert n["guard_behavior"]=="FAIL_CLOSED_BEFORE_POPULATION_EMISSION"


def test_scope_is_exact_and_does_not_overclaim_total_secret_emission():
    out=proof.prove()
    assert "EVERY_POPULATION_SUCCESSFULLY_EMITTED" in out["scope"]["quantifier"]
    assert any("NO_CLAIM_THAT_EVERY_ARBITRARY_SECRET" in x for x in out["hard_nonclaims"])
    assert out["accounting"]["acceptance_credit_delta"]==0
    assert out["accounting"]["capability_credit_delta"]==0
