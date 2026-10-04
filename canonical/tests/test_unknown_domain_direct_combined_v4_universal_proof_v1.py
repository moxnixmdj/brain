from canonical.runtime import unknown_domain_direct_candidate_v3 as candidate
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as generator
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_combined_v4_universal_proof_v1 as proof

def test_combined_universal_proof_is_zero_reality_and_content_bound():
    out=proof.prove()
    assert out["status"]=="PASS__UNIVERSAL_COLLISION_TOTAL_AND_EXACT_FLOAT_SAFE_OVER_EXACT_V3_GENERATOR_DOMAIN"
    assert out["scope"]["terminal_or_production_cases_generated"]==0
    assert out["repairs"]["v2_identifier_collision_quantifier_hole"] is True
    assert out["repairs"]["v2_add2_exact_binary64_role_order_counterexample"] is True
    assert out["repairs"]["scorer_or_harness_relaxed"] is False
    assert out["exact_subject_blobs"]==proof.EXPECTED_BLOBS

def test_v3_qualification_population_passes_unchanged_frozen_scorer():
    packet=generator.generate_qualification_fixture_population(
        beacon="COMBINED-V4-QUALIFICATION-BEACON-0001"
    )
    assert packet["production"] is False
    results=[]
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
        run=harness.execute_case(
            candidate_step=candidate.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        assert run["scorer_result"]["pass"] is True,(visible["case_id"],run)
        results.append(run["scorer_result"])
    agg=scorer.aggregate(results)
    assert agg["all_27_cases_pass"] is True

def test_identifier_totality_proof_covers_real_case_tag_sizes():
    ident=proof.prove()["identifier_totality_proof"]
    assert 12 in ident["covered_permutation_sizes"]
    assert 15 in ident["covered_permutation_sizes"]
    assert ident["hmac_collision_resistance_required_for_identifier_uniqueness"] is False

def test_add2_exact_float_repair_does_not_relax_evaluator():
    t=proof.prove()["transfer_proof"]
    assert t["scorer_v1_exact_equality_preserved"] is True
    assert t["add2_exact_binary64_order"]=="CANDIDATE_AND_GENERATOR_BOTH_EVALUATE_BIAS_PLUS_R0_THEN_PLUS_R1"
