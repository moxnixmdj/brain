from canonical.runtime import livebench_legacy15_joint_candidate_generator_v1 as full
from canonical.runtime import livebench_legacy15_relaxed_candidate_search_v1 as relaxed


def c(iid, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def test_unsat_full_conjunction_still_gets_partial_candidates():
    contracts = [
        c(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=2,
            nth_paragraph=1,
            first_word="alpha",
        ),
        c("keywords:forbidden_words", forbidden_words=["alpha"]),
    ]

    full_out = full.generate(contracts)
    assert full_out["status"] == "FAIL_CLOSED"
    assert full_out["candidates"] == []

    out = relaxed.generate_relaxed(contracts)
    assert out["status"] == "PASS_CANDIDATE_POOL"
    assert out["theoretical_nonempty_relaxation_count"] == 3
    assert out["subset_attempt_count"] == 3
    assert out["candidate_count"] > 0

    provenances = [
        p
        for row in out["candidates"]
        for p in row["provenance"]
        if p.get("kind") == "RELAXED_SUBSET"
    ]
    assert any(p.get("subset_indices") == [0] for p in provenances)
    assert any(p.get("subset_indices") == [1] for p in provenances)


def test_five_checker_search_has_hard_31_relaxation_bound():
    contracts = [
        c("keywords:existence", keywords=["signal"]),
        c("keywords:forbidden_words", forbidden_words=["omega"]),
        c("length_constraints:number_words", num_words=100, relation="at least"),
        c("detectable_content:postscript", postscript_marker="P.S."),
        c("startend:quotation"),
    ]
    out = relaxed.generate_relaxed(contracts, max_per_subset=2, max_total=512)
    assert out["checker_count"] == 5
    assert out["theoretical_nonempty_relaxation_count"] == 31
    assert out["subset_attempt_count"] <= 31
    assert out["candidate_count"] <= 512


def test_candidate_generation_never_claims_pointwise_optimality():
    out = relaxed.generate_relaxed([
        c("keywords:forbidden_words", forbidden_words=["omega"]),
    ])
    assert out["candidates"]
    assert out["requires_exact_full_case_checker_postvalidation"] is True
    assert out["pointwise_optimality_not_claimed_by_candidate_generation"] is True
    assert out["terminal_data_used"] is False
    assert out["hidden_kwargs_used"] is False
    assert out["acceptance_credit"] is False


def test_relaxed_search_rejects_incomplete_visible_parameters():
    bad = {
        "instruction_id": "keywords:existence",
        "slots": {"keywords": ["signal"]},
        "parameter_complete": False,
    }
    try:
        relaxed.generate_relaxed([bad])
    except ValueError as exc:
        assert str(exc) == "PARAMETER_INCOMPLETE"
    else:
        raise AssertionError("expected fail-closed incomplete parameter rejection")


def test_relaxed_search_rejects_conflicting_identity_sets():
    contracts = [
        c("detectable_format:json_format"),
        c("length_constraints:number_words", num_words=100, relation="at least"),
    ]
    try:
        relaxed.generate_relaxed(contracts)
    except ValueError as exc:
        assert str(exc) == "ACTIVE15_CONFLICT_GRAPH_REJECTED"
    else:
        raise AssertionError("expected fail-closed conflict rejection")
