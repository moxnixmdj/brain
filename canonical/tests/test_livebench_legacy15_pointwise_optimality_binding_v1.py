from fractions import Fraction

from canonical.runtime import livebench_legacy15_pointwise_optimality_binding_v1 as b


def c(iid, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def score(out):
    return Fraction(
        out["candidate_exact_score_numerator"],
        out["candidate_exact_score_denominator"],
    )


def test_full_score_is_immediately_pointwise_optimal():
    contracts = [
        c("keywords:existence", keywords=["alpha"]),
        c("keywords:forbidden_words", forbidden_words=["omega"]),
        c("detectable_format:title"),
    ]
    out = b.certify_pointwise_optimality(contracts, [True, True, True])
    assert out["status"] == "PASS__POINTWISE_OPTIMALITY_CERTIFIED_BY_SLOT_SEMANTICS"
    assert out["required_next_cardinality_unsat_subset_count"] == 0
    assert out["pointwise_optimal"] is True
    assert score(out) == 1


def test_known_nth_forbidden_collision_certifies_best_one_of_two():
    contracts = [
        c(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=2,
            nth_paragraph=1,
            first_word="alpha",
        ),
        c("keywords:forbidden_words", forbidden_words=["alpha"]),
    ]
    out = b.certify_pointwise_optimality(contracts, [True, False])
    assert out["status"] == "PASS__POINTWISE_OPTIMALITY_CERTIFIED_BY_SLOT_SEMANTICS"
    assert out["pointwise_optimal"] is True
    assert out["semantically_verified_unsat_subset_count"] == 1
    assert out["semantic_unsat_receipts"][0]["subset_indices"] == [0, 1]
    assert "NTH_FIRST_WORD_IS_FORBIDDEN_WORD" in out[
        "semantic_unsat_receipts"
    ][0]["hard_unsat_reasons"]
    assert score(out) == Fraction(1, 4)


def test_known_collision_plus_independent_title_certifies_two_of_three_optimum():
    contracts = [
        c(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=2,
            nth_paragraph=1,
            first_word="alpha",
        ),
        c("keywords:forbidden_words", forbidden_words=["alpha"]),
        c("detectable_format:title"),
    ]
    out = b.certify_pointwise_optimality(contracts, [True, False, True])
    assert out["status"] == "PASS__POINTWISE_OPTIMALITY_CERTIFIED_BY_SLOT_SEMANTICS"
    assert out["pointwise_optimal"] is True
    assert out["required_next_cardinality_unsat_subset_count"] == 1
    assert score(out) == Fraction(1, 3)


def test_insufficient_unsat_coverage_fails_closed():
    contracts = [
        c(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=2,
            nth_paragraph=1,
            first_word="alpha",
        ),
        c("keywords:forbidden_words", forbidden_words=["alpha"]),
    ]
    out = b.certify_pointwise_optimality(contracts, [False, False])
    assert out["status"] == "FAIL_CLOSED__SEMANTIC_UNSAT_COVERAGE_INCOMPLETE"
    assert out["pointwise_optimal"] is False
    assert len(out["missing_unsat_subsets"]) == 2


def test_mismatch_fails_closed():
    out = b.certify_pointwise_optimality(
        [c("detectable_format:title")],
        [],
    )
    assert out["status"] == "FAIL_CLOSED__CHECKER_RESULT_ARITY_MISMATCH"
