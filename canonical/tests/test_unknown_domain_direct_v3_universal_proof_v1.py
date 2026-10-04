from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proof


def test_universal_proof_is_content_bound_zero_reality():
    out=proof.prove()
    assert out["status"]=="PASS__UNIVERSAL_OVER_EXACT_COLLISION_TOTALIZED_V3_GENERATOR_DOMAIN"
    assert out["scope"]["production_population_cases"]==27
    assert out["scope"]["terminal_or_production_cases_generated"]==0
    assert out["fresh_reality_required_for_this_exact_v3_generator_claim"] is False
    assert out["production_execution_information_gain_for_this_exact_v3_generator_claim"]==0
    assert out["exact_subject_blobs"]==proof.EXPECTED_BLOBS


def test_identifier_construction_is_bijection_not_hash_uniqueness():
    out=proof.prove()["identifier_totality_proof"]
    assert out["status"]=="PROVED_BY_BIJECTION_CONSTRUCTION"
    assert out["uniqueness_depends_on_hash_collision_resistance"] is False
    assert out["uniform_randomness_required"] is False
    for n in out["permutation_sizes"]:
        for secret in (b"A"*32,b"B"*32,b"\x00"*32,b"\xff"*32):
            p=g3._perm(secret,"BEACON-VALID-0123456789",f"n={n}",n)
            assert len(p)==n
            assert len(set(p))==n
            assert set(p)==set(range(n))


def test_transfer_structural_margins_are_strict():
    out=proof.prove()["transfer_proof"]
    assert out["all_six_families_universal"] is True
    assert out["max_transfer_probes"]==2
    assert out["full_rediscovery_probe_floor"]==3
    assert out["affine_min_wrong_support_output_gap"]>2.84
    assert out["complement_min_wrong_support_output_gap"]>=4.75
    assert out["sat_mono_conservative_min_wrong_support_output_gap"]>out["sat_mono_max_candidate_close_tolerance"]
    assert out["sign_negative_probe_min_shifted_distractor_value"]>0
    assert out["step_min_wrong_side_margin"]>2.54
    assert out["add2_min_wrong_support_first_probe_gap"]>=1.5
    assert out["add2_true_support_role_swap_safe"] is True


def test_abstention_classes_are_collision_totalized():
    out=proof.prove()["abstention_proof"]
    assert out["all_three_classes_universal"] is True
    assert out["identifier_collision_can_change_class_semantics"] is False
    assert "INTENTIONALLY_SHARE" in out["identifiable"]
    assert "STRUCTURALLY_DISTINCT" in out["nonidentifiable"]
    assert "UNIQUE_MINIMUM_COST" in out["underspecified"]


def test_nonproduction_fixture_regression_multiple_beacons():
    # This is regression evidence only, not the universal proof. The theorem is
    # structural and does not infer universality from these samples.
    for beacon in (
        "V3-QUALIFICATION-ALPHA-0001",
        "V3-QUALIFICATION-BETA-0002",
        "V3-QUALIFICATION-GAMMA-0003",
    ):
        packet=g3.generate_qualification_fixture_population(beacon=beacon)
        assert packet["production"] is False
        assert packet["case_count"]==27
        assert packet["identifier_totality"]==g3.IDENTIFIER_TOTALITY
        rows=[]
        for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
            out=harness.execute_case(
                candidate_step=candidate.step,
                case_visible=visible,
                hidden_record=hidden,
            )
            rows.append(out["scorer_result"])
        agg=scorer.aggregate(rows)
        assert agg["all_27_cases_pass"] is True


def test_no_credit_and_no_open_world_overclaim():
    out=proof.prove()
    assert out["accounting"]["acceptance_credit_delta"]==0
    assert out["accounting"]["capability_credit_delta"]==0
    assert out["accounting"]["ownership_credit_delta"]==0
    assert any("OPEN_WORLD" in x for x in out["hard_nonclaims"])
    assert any("FALSE_V2" in x for x in out["hard_nonclaims"])
    assert any("INDEPENDENT_CONTENT_BOUND_VERIFICATION" in x for x in out["hard_nonclaims"])
