from canonical.runtime.livebench_if_single_checker_solver_v1 import detect, solve


def test_public_pronoun_wording_is_detected_and_solved():
    prompt = "Explain the topic. The response should include at least 5 pronouns."
    assert detect(prompt) == ["count:pronouns"]
    out = solve(prompt)
    assert out["status"] == "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS"
    assert out["checker_id"] == "count:pronouns"
    assert out["response"].split() == ["I"] * 5


def test_personal_pronoun_source_variant_is_also_supported():
    prompt = "The response should include at least 4 personal pronouns."
    assert detect(prompt) == ["count:pronouns"]
    out = solve(prompt)
    assert out["status"] == "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS"
    assert len(out["response"].split()) == 4


def test_unrelated_semantic_mention_of_pronouns_does_not_false_positive():
    prompt = "Explain why pronouns matter in grammar."
    assert "count:pronouns" not in detect(prompt)
    out = solve(prompt)
    assert out["status"] == "FAIL_CLOSED"


def test_multi_checker_prompt_remains_fail_closed():
    prompt = (
        "Include exactly 7 numbers in the response. "
        "Use at least 4 different coordinating conjunctions in the response."
    )
    ids = detect(prompt)
    assert set(ids) == {"count:numbers", "count:conjunctions"}
    out = solve(prompt)
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "CHECKER_FAMILY_CARDINALITY_NOT_ONE"
