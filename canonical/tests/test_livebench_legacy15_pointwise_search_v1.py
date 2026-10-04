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
    assert out["status"] == "CONDITIONAL__POINTWISE_OPTIMAL_GIVEN_UNVERIFIED_CHECKER_VECTOR"
    assert out["pointwise_optimal_given_checker_vector"] is True
    assert out["checker_vector_authoritative"] is False
    assert out["pointwise_optimal"] is False
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
    assert out["status"] == "CONDITIONAL__POINTWISE_OPTIMAL_GIVEN_UNVERIFIED_CHECKER_VECTOR"
    assert out["pointwise_optimal_given_checker_vector"] is True
    assert out["checker_vector_authoritative"] is False
    assert out["pointwise_optimal"] is False
    assert out["candidate_pool_count"] > 0
    assert out["best_candidate"]["true_checker_count"] == 1


def test_full_score_candidate_needs_no_unsat_certificates():
    contracts = [
        c("keywords:forbidden_words", forbidden_words=["omega"]),
    ]

    def checker(response, _contracts):
        return [re.search(r"\bomega\b", response, re.I) is None]

    out = search.solve_with_checker(contracts, checker, max_per_subset=2, max_total=32)
    assert out["status"] == "CONDITIONAL__POINTWISE_OPTIMAL_GIVEN_UNVERIFIED_CHECKER_VECTOR"
    assert out["pointwise_optimal_given_checker_vector"] is True
    assert out["checker_vector_authoritative"] is False
    assert out["pointwise_optimal"] is False
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


def test_proofgrade_pinned_bridge_is_authoritative_only_with_full_binding(monkeypatch):
    class FakeForbidden:
        def __init__(self, iid):
            self.word = ""

        def build_description(self, *, forbidden_words):
            self.word = str(forbidden_words[0])

        def check_following(self, response):
            return self.word not in response

    binding = {
        "source": {
            "livebench_commit": "pinned-test",
            "evaluation_main_blob": search.PINNED_STRICT_EVALUATOR_BLOB,
            "strict_nonempty_guard": "response.strip() must be truthy before any checker can pass",
        },
        "runtime": {
            "status": "NOT_REQUIRED__NO_NLTK_DEPENDENT_ACTIVE15_CHECKER",
        },
        "proofgrade_runtime_dependencies_bound": True,
    }
    monkeypatch.setattr(
        search.exact_postvalidator,
        "load_proofgrade_registry",
        lambda root, contracts, **kwargs: (
            {"keywords:forbidden_words": FakeForbidden},
            binding,
        ),
    )

    contracts = [c("keywords:forbidden_words", forbidden_words=["omega"])]
    out = search.solve_with_pinned_livebench(
        contracts,
        "/synthetic/pinned/root",
        max_per_subset=2,
        max_total=32,
    )
    assert out["status"] == "PASS__POINTWISE_OPTIMAL_CANDIDATE_CERTIFIED"
    assert out["pointwise_optimal_given_checker_vector"] is True
    assert out["checker_vector_authoritative"] is True
    assert out["checker_vector_authority"] == "EXACT_PINNED_LIVEBENCH_PROOFGRADE_RUNTIME"
    assert out["pointwise_optimal"] is True
    assert out["exact_checker_callback_required"] is False
    assert out["exact_checker_binding"] == binding


def test_pinned_source_without_complete_proofgrade_binding_stays_conditional(monkeypatch):
    class FakeForbidden:
        def __init__(self, iid):
            self.word = ""

        def build_description(self, *, forbidden_words):
            self.word = str(forbidden_words[0])

        def check_following(self, response):
            return self.word not in response

    binding = {
        "source": {
            "livebench_commit": "pinned-test",
            # Deliberately no content-addressed strict evaluator binding.
        },
        "runtime": {"status": "SOURCE_ONLY"},
        "proofgrade_runtime_dependencies_bound": False,
    }
    monkeypatch.setattr(
        search.exact_postvalidator,
        "load_proofgrade_registry",
        lambda root, contracts, **kwargs: (
            {"keywords:forbidden_words": FakeForbidden},
            binding,
        ),
    )

    contracts = [c("keywords:forbidden_words", forbidden_words=["omega"])]
    out = search.solve_with_pinned_livebench(
        contracts,
        "/synthetic/pinned/root",
        max_per_subset=2,
        max_total=32,
    )
    assert out["status"] == "CONDITIONAL__POINTWISE_OPTIMAL_GIVEN_UNVERIFIED_CHECKER_VECTOR"
    assert out["pointwise_optimal_given_checker_vector"] is True
    assert out["checker_vector_authoritative"] is False
    assert out["checker_vector_authority"] == "PINNED_SOURCE_WITHOUT_COMPLETE_PROOFGRADE_AUTHORITY"
    assert out["pointwise_optimal"] is False


def test_fabricated_external_vector_cannot_emit_authoritative_pointwise_pass():
    contracts = [
        c(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=2,
            nth_paragraph=1,
            first_word="alpha",
        ),
        c("keywords:forbidden_words", forbidden_words=["alpha"]),
    ]
    out = search.run({
        "contracts": contracts,
        "evaluated_candidates": [
            {
                "response": "this response satisfies neither asserted fact",
                "checker_results": [True, False],
            }
        ],
    })
    assert out["status"] == "CONDITIONAL__POINTWISE_OPTIMAL_GIVEN_UNVERIFIED_CHECKER_VECTOR"
    assert out["pointwise_optimal_given_checker_vector"] is True
    assert out["checker_vector_authoritative"] is False
    assert out["pointwise_optimal"] is False
