from canonical.runtime.livebench_ratio_conjunction_solver_v1 import (
    ConjunctionSolverError,
    consonant_cluster_ok,
    overlap_percent,
    solve_visible_prompt,
)


def test_ratio_only_whitespace_invariant():
    prompt = (
        "alpha beta gamma delta "
        "Maintain a trigram overlap of 50% (±2%) with the provided reference text."
    )
    out = solve_visible_prompt(prompt)
    raw = "alpha\n\nbeta\tgamma delta"
    assert abs(overlap_percent(out["response"], raw) - 50) <= 2
    assert out["hidden_kwargs_read"] is False


def test_sentence_keyword_conjunction_high_sentence_count():
    base = (
        "Write a believable sci fi history about a parasite that could loosely retain "
        "the form, memories and personality of its' hosts, eventually being destroyed."
    )
    prompt = (
        "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
        "The response must include keyword horary in the 30-th sentence. " + base
    )
    out = solve_visible_prompt(prompt)
    assert out["mode"] == "RATIO_PLUS_SENTENCE_KEYWORD"
    assert out["response"].count(".") == 29
    assert "horary" in out["response"].split(".")[29].lower()
    assert abs(overlap_percent(out["response"], base) - 23) <= 2


def test_consonant_cluster_conjunction():
    base = "Strong cryptic systems preserve structural constraints"
    prompt = (
        base
        + " Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together). "
        "Maintain a trigram overlap of 54% (±2%) with the provided reference text."
    )
    out = solve_visible_prompt(prompt)
    assert out["mode"] == "RATIO_PLUS_CONSONANTS"
    assert consonant_cluster_ok(out["response"])
    assert abs(overlap_percent(out["response"], base) - 54) <= 2


def test_scope_binding_is_fail_closed():
    try:
        solve_visible_prompt(
            "abc Maintain a trigram overlap of 50% (±2%) with the provided reference text.",
            scope_binding="UNPROVED",
        )
    except ConjunctionSolverError as exc:
        assert "SCOPE_BINDING_REQUIRED" in str(exc)
    else:
        raise AssertionError("expected fail closed")
