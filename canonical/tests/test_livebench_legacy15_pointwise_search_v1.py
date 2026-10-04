import re

from canonical.runtime import livebench_legacy15_pointwise_search_v1 as search


def c(iid, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def test_postvalidated_partial_candidate_gets_semantic_optimality_certificate():
    contracts = [
        c(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=2,
            nth_paragraph=1,
            first_word="alpha",
        ),
        c("keywords:forbidden_words", forbidden_words=["alpha"]),
    ]
    out = search.select_best_postvalidated(
        contracts,
        [
            {"response": "alpha x", "checker_results": [True, False]},
            {"response": "q0", "checker_results": [False, True]},
        ],
    )
    assert out["status"] == "PASS__POINTWISE_OPTIMAL_CANDIDATE_CERTIFIED"
    assert out["pointwise_optimal"] is True
    assert out["best_candidate"]["true_checker_count"] == 1
    assert out["best_candidate"]["score_numerator"] == 1
    assert out["best_candidate"]["score_denominator"] == 4
    assert out["certificate"]["semantically_verified_unsat_subset_count"] == 1


def test_relaxed_search_plus_checker_executes_unsat_pair_end_to_end():
    contracts = [
        c(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=2,
            nth_paragraph=1,
            first_word="alpha",
        ),
        c("keywords:forbidden_words", forbidden_words=["alpha"]),
    ]

    def checker(response, _contracts):
        paragraphs = response.split("\n\n")
        first = paragraphs[0].strip().split()[0].strip("'\".,?!").lower() if paragraphs and paragraphs[0].strip() else ""
        nth_ok = first == "alpha" and len(paragraphs) == 2
        forbidden_ok = re.search(r"\balpha\b", response, re.I) is None
        return [nth_ok, forbidden_ok]

    out = search.solve_with_checker(contracts, checker, max_per_subset=4, max_total=64)
    assert out["status"] == "PASS__POINTWISE_OPTIMAL_CANDIDATE_CERTIFIED"
    assert out["pointwise_optimal"] is True
    assert out["candidate_pool_count"] > 0
    assert out["best_candidate"]["true_checker_count"] == 1


def test_full_score_candidate_needs_no_unsat_certificates():
    contracts = [
        c("keywords:forbidden_words", forbidden_words=["omega"]),
    ]

    def checker(response, _contracts):
        return [re.search(r"\bomega\b", response, re.I) is None]

    out = search.solve_with_checker(contracts, checker, max_per_subset=2, max_total=32)
    assert out["status"] == "PASS__POINTWISE_OPTIMAL_CANDIDATE_CERTIFIED"
    assert out["best_candidate"]["checker_results"] == [True]
    assert out["certificate"]["required_next_cardinality_subset_count"] == 0


def test_selector_fails_closed_when_unsat_coverage_is_missing():
    contracts = [
        c("keywords:existence", keywords=["alpha"]),
        c("detectable_format:title"),
    ]
    out = search.select_best_postvalidated(
        contracts,
        [{"response": "alpha", "checker_results": [True, False]}],
    )
    assert out["status"] == "FAIL_CLOSED__BEST_CANDIDATE_OPTIMALITY_NOT_CERTIFIED"
    assert out["pointwise_optimal"] is False
    assert out["certificate"]["unresolved_subset_indices"] == [[0, 1]]


def test_sentence_lt_one_plus_forbidden_partial_candidate_is_pointwise_optimal():
    contracts = [
        c("length_constraints:number_sentences", num_sentences=1, relation="less than"),
        c("keywords:forbidden_words", forbidden_words=["omega"]),
    ]
    # Under strict evaluation, blank scores [False, False]. A safe nonblank
    # response scores [False, True]. The full pair is UNSAT because sentence<1
    # cannot ever receive strict credit.
    out = search.select_best_postvalidated(
        contracts,
        [
            {"response": "", "checker_results": [False, False]},
            {"response": "alpha", "checker_results": [False, True]},
        ],
    )
    assert out["status"] == "PASS__POINTWISE_OPTIMAL_CANDIDATE_CERTIFIED"
    assert out["pointwise_optimal"] is True
    assert out["best_candidate"]["checker_results"] == [False, True]
    assert out["best_candidate"]["score_numerator"] == 1
    assert out["best_candidate"]["score_denominator"] == 4
    reasons = out["certificate"]["semantic_unsat_evidence"][0]["hard_unsat_reasons"]
    assert "STRICT_EVALUATOR_SENTENCE_LT_ONE_UNSAT" in reasons
