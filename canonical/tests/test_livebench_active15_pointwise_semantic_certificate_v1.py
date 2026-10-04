from canonical.runtime import livebench_active15_pointwise_semantic_certificate_v1 as c
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as f


def nth_forbidden():
    return [
        {
            "instruction_id": f.NTH,
            "slots": {
                "num_paragraphs": 3,
                "nth_paragraph": 2,
                "first_word": "harbor",
            },
        },
        {
            "instruction_id": f.FORBIDDEN,
            "slots": {"forbidden_words": ["harbor"]},
        },
    ]


def test_hard_unsat_pair_turns_partial_candidate_into_pointwise_optimum():
    out = c.certify(nth_forbidden(), [True, False])
    assert out["status"] == "PASS__POINTWISE_OPTIMALITY_SEMANTICALLY_CERTIFIED"
    assert out["pointwise_optimality_proved"] is True
    assert out["required_next_cardinality_subset_count"] == 1
    assert out["semantically_proved_unsat_subset_count"] == 1
    assert out["candidate_exact_score_numerator"] == 1
    assert out["candidate_exact_score_denominator"] == 4


def test_unsat_pair_inside_larger_subset_is_enough():
    contracts = nth_forbidden() + [
        {"instruction_id": "detectable_format:title", "slots": {}},
    ]
    out = c.certify(contracts, [True, False, True])
    assert out["status"] == "PASS__POINTWISE_OPTIMALITY_SEMANTICALLY_CERTIFIED"
    assert out["required_next_cardinality_subset_count"] == 1
    assert out["semantic_unsat_proofs"][0]["checker_indices"] == [0, 1, 2]


def test_section_forbidden_collision_is_semantically_certified():
    contracts = [
        {
            "instruction_id": f.SECTIONS,
            "slots": {"section_spliter": "Section", "num_sections": 3},
        },
        {
            "instruction_id": f.FORBIDDEN,
            "slots": {"forbidden_words": ["section"]},
        },
    ]
    out = c.certify(contracts, [True, False])
    assert out["status"] == "PASS__POINTWISE_OPTIMALITY_SEMANTICALLY_CERTIFIED"
    assert any(
        "MANDATORY_SECTION_SPLITTER_IS_FORBIDDEN_WORD:section" in x
        for x in out["semantic_unsat_proofs"][0]["hard_unsat_reasons"]
    )


def test_end_phrase_forbidden_collision_is_semantically_certified():
    contracts = [
        {
            "instruction_id": f.END,
            "slots": {"end_phrase": "Any other questions?"},
        },
        {
            "instruction_id": f.FORBIDDEN,
            "slots": {"forbidden_words": ["other"]},
        },
    ]
    out = c.certify(contracts, [False, True])
    assert out["status"] == "PASS__POINTWISE_OPTIMALITY_SEMANTICALLY_CERTIFIED"


def test_satisfiable_existence_forbidden_overlap_is_not_falsely_certified_unsat():
    contracts = [
        {
            "instruction_id": f.EXISTENCE,
            "slots": {"keywords": ["rock"]},
        },
        {
            "instruction_id": f.FORBIDDEN,
            "slots": {"forbidden_words": ["rock"]},
        },
    ]
    out = c.certify(contracts, [True, False])
    assert out["status"] == "FAIL_CLOSED__SEMANTIC_UNSAT_COVER_INCOMPLETE"
    assert out["pointwise_optimality_proved"] is False
    assert out["semantically_proved_unsat_subset_count"] == 0


def test_full_score_needs_no_unsat_certificates():
    contracts = [
        {"instruction_id": f.EXISTENCE, "slots": {"keywords": ["signal"]}},
        {"instruction_id": f.FORBIDDEN, "slots": {"forbidden_words": ["rock"]}},
    ]
    out = c.certify(contracts, [True, True])
    assert out["status"] == "PASS__POINTWISE_OPTIMALITY_SEMANTICALLY_CERTIFIED"
    assert out["required_next_cardinality_subset_count"] == 0
    assert out["semantically_proved_unsat_subset_count"] == 0


def test_length_mismatch_and_non_bool_fail_closed_by_exception():
    try:
        c.certify(nth_forbidden(), [True])
    except ValueError as exc:
        assert str(exc) == "CONTRACT_RESULT_LENGTH_MISMATCH"
    else:
        raise AssertionError("expected mismatch rejection")

    try:
        c.certify(nth_forbidden(), [True, 1])
    except ValueError as exc:
        assert str(exc) == "CHECKER_RESULTS_MUST_BE_BOOL"
    else:
        raise AssertionError("expected type rejection")


def test_semantically_impossible_full_score_flags_fail_closed():
    out = c.certify(nth_forbidden(), [True, True])
    assert out["status"] == "FAIL_CLOSED__CHECKER_RESULTS_CONTRADICT_SEMANTIC_UNSAT"
    assert "NTH_FIRST_WORD_IS_FORBIDDEN_WORD" in out["hard_unsat_reasons"]
    assert out["acceptance_credit"] is False
