from canonical.runtime import livebench_if_single_checker_solver_v1 as solver


def test_pronoun_family_accepts_public_wording_without_personal_qualifier():
    prompt = "The response should include at least 22 pronouns. Explain a topic."
    out = solver.solve(prompt)
    assert out["status"] == "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS"
    assert out["checker_id"] == "count:pronouns"
    assert len(out["response"].split()) == 22


def test_pronoun_family_preserves_personal_pronoun_wording_compatibility():
    prompt = "The response should include at least 7 personal pronouns. Explain a topic."
    out = solver.solve(prompt)
    assert out["status"] == "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS"
    assert out["checker_id"] == "count:pronouns"
    assert len(out["response"].split()) == 7
