from canonical.runtime import livebench_if_single_checker_solver_v1 as solver


def _stub_ratio_backend(monkeypatch):
    seen = {}

    monkeypatch.setattr(
        solver.ngram_free,
        "extract_pinned_public_ifbench_base",
        lambda prompt: "visible base",
    )

    def fake_construct(base, pct):
        seen["base"] = base
        seen["pct"] = pct
        return {"status": "PASS_UNDER_CONTRACT", "response": "candidate"}

    monkeypatch.setattr(solver.ngram_free, "construct", fake_construct)
    return seen


def test_decimal_ratio_target_parses_without_integer_cast_crash(monkeypatch):
    seen = _stub_ratio_backend(monkeypatch)
    out = solver.solve(
        "Visible source text. Maintain a trigram overlap of 65.7% with the provided reference text."
    )

    assert out["status"] == "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS"
    assert out["checker_id"] == "ratio:overlap"
    assert out["response"] == "candidate"
    assert seen == {"base": "visible base", "pct": 65.7}


def test_integer_ratio_target_still_parses_as_float(monkeypatch):
    seen = _stub_ratio_backend(monkeypatch)
    out = solver.solve(
        "Visible source text. Maintain a trigram overlap of 65% with the provided reference text."
    )

    assert out["status"] == "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS"
    assert seen["pct"] == 65.0
