from fractions import Fraction

from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proof


def test_content_bound_v3_universal_status_zero_reality():
    out=proof.prove()
    assert out["status"]=="PASS__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN_WITH_V3_EXACTNESS_REPAIR"
    assert out["scope"]["population_cases"]==27
    assert out["scope"]["production_cases_generated"]==0
    assert out["fresh_reality_required_for_this_exact_frozen_evaluator_claim"] is False
    assert out["production_execution_information_gain_for_this_exact_evaluator_claim"]==0
    assert out["exact_subject_blobs"]==proof.EXPECTED_BLOBS


def test_all_transfer_families_have_strict_discriminator_or_orientation():
    t=proof.prove()["transfer_proof"]
    assert t["all_six_families_universal"] is True
    assert t["max_transfer_probes"]==2
    assert t["full_rediscovery_probe_floor"]==3
    assert Fraction(t["affine_min_wrong_support_gap"])==Fraction(57,20)
    assert Fraction(t["complement_min_wrong_support_gap"])==Fraction(19,4)
    assert Fraction(t["sat_mono_conservative_min_wrong_support_gap"])>0
    assert Fraction(t["sign_shifted_distractor_min_on_negative_probe"])==Fraction(5,4)
    assert Fraction(t["step_wrong_side_margin"])==Fraction(51,20)
    assert Fraction(t["add2_min_wrong_support_gap"])==Fraction(3,2)
    assert t["add2_exact_float_order_repaired_by_v3"] is True
    assert t["add2_role_signatures"]=={
        "4":{"r0":[-1,1,-1],"r1":[1,-1,1]},
        "10":{"r0":[-1,1,-1],"r1":[1,-1,1]},
    }


def test_abstention_partition_universal():
    a=proof.prove()["abstention_proof"]
    assert a["all_three_classes_universal"] is True
    assert a["cases_per_class"]==5


def test_v2_counterexample_is_not_erased_or_relabelled_as_success():
    out=proof.prove()
    assert out["v2_counterexample_status"].startswith("PROVED_BY_REGRESSION_TEST")
    assert "V2_NOT_UNIVERSAL" in out["v2_counterexample_status"]
    assert out["v3_repair"]=="VISIBLE_ADD2_ROLE_SIGN_ORIENTATION_BEFORE_EXACT_QUERY_EVALUATION"


def test_no_open_world_or_acceptance_overclaim():
    out=proof.prove()
    assert any("NO_OPEN_WORLD" in x for x in out["hard_nonclaims"])
    assert out["accounting"]["acceptance_credit_delta"]==0
    assert out["accounting"]["family_credit_delta"]==0
    assert out["accounting"]["capability_credit_delta"]==0
    assert out["accounting"]["ownership_credit_delta"]==0
