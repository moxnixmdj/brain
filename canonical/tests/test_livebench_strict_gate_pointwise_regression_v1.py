from canonical.runtime.livebench_legacy15_pointwise_certificate_v1 import certify


def test_strict_sentence_lt_one_subset_closes_pointwise_optimality():
    contracts = [
        {
            "instruction_id": "length_constraints:number_sentences",
            "slots": {"num_sentences": 1, "relation": "less than"},
        },
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": ["omega"]},
        },
    ]
    result = certify(contracts, [False, True])
    assert result["status"] == "PASS__POINTWISE_SCORE_OPTIMAL_GIVEN_EXACT_CANDIDATE_CHECKER_RESULTS"
    assert result["pointwise_optimal"] is True
    assert result["candidate_exact_score_numerator"] == 1
    assert result["candidate_exact_score_denominator"] == 4
    assert result["required_next_cardinality_subset_count"] == 1
    reasons = result["semantic_unsat_evidence"][0]["hard_unsat_reasons"]
    assert "STRICT_EVALUATOR_SENTENCE_LT_ONE_UNSAT" in reasons
