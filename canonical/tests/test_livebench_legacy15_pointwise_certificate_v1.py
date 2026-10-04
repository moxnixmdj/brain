from canonical.runtime.livebench_legacy15_pointwise_certificate_v1 import certify


def test_nth_forbidden_collision_makes_one_of_two_pointwise_optimal():
    contracts = [
        {
            "instruction_id": "length_constraints:nth_paragraph_first_word",
            "slots": {"num_paragraphs": 2, "nth_paragraph": 1, "first_word": "alpha"},
        },
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": ["alpha"]},
        },
    ]
    result = certify(contracts, [True, False])
    assert result["status"].startswith("PASS__POINTWISE_SCORE_OPTIMAL")
    assert result["pointwise_optimal"] is True
    assert result["candidate_exact_score_numerator"] == 1
    assert result["candidate_exact_score_denominator"] == 4


def test_end_forbidden_collision_makes_k_minus_one_optimal():
    contracts = [
        {
            "instruction_id": "startend:end_checker",
            "slots": {"end_phrase": "Any other questions?"},
        },
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": ["questions"]},
        },
        {
            "instruction_id": "keywords:existence",
            "slots": {"keywords": ["river"]},
        },
    ]
    result = certify(contracts, [True, False, True])
    assert result["pointwise_optimal"] is True
    assert result["required_next_cardinality_subset_count"] == 1


def test_unknown_semantic_gap_fails_closed():
    contracts = [
        {
            "instruction_id": "keywords:existence",
            "slots": {"keywords": ["river"]},
        },
        {
            "instruction_id": "detectable_format:title",
            "slots": {},
        },
    ]
    result = certify(contracts, [True, False])
    assert result["status"].startswith("FAIL_CLOSED")
    assert result["pointwise_optimal"] is False


def test_full_score_needs_no_unsat_certificate():
    contracts = [
        {
            "instruction_id": "keywords:existence",
            "slots": {"keywords": ["river"]},
        },
        {
            "instruction_id": "detectable_format:title",
            "slots": {},
        },
    ]
    result = certify(contracts, [True, True])
    assert result["pointwise_optimal"] is True
    assert result["required_next_cardinality_subset_count"] == 0


def test_sentence_end_unsat_makes_one_of_two_pointwise_optimal():
    contracts = [
        {
            "instruction_id": "length_constraints:number_sentences",
            "slots": {"num_sentences": 1, "relation": "less than"},
        },
        {
            "instruction_id": "startend:end_checker",
            "slots": {"end_phrase": "Any other questions?"},
        },
    ]
    result = certify(contracts, [False, True])
    assert result["pointwise_optimal"] is True
    assert result["required_next_cardinality_subset_count"] == 1
    assert "SENTENCE_LT_ONE_WITH_MANDATORY_END_PHRASE" in result["semantic_unsat_evidence"][0]["hard_unsat_reasons"]
