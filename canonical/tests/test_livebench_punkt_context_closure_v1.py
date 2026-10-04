from canonical.runtime import livebench_punkt_context_closure_v1 as p


def test_symbolic_punkt_reduction_is_total_over_sentence_id_sets():
    out = p.symbolic_verify()
    assert out["sentence_compatible_id_set_count"] == 285
    assert out["less_than_partition"]["tail_context_count"] == 36
    assert out["at_least_public_threshold_domain"] == [1, 20]
    assert out["acceptance_credit"] is False


def test_numeric_scaffold_is_decimal_and_consecutive():
    for n in range(1, 21):
        toks = p.numeric_sentence_tokens(n)
        assert len(toks) == n
        assert toks == tuple(f"{p.SAFE}{i}." for i in range(1, n + 1))
        assert all(x[:-1].isdigit() for x in toks)


def test_tail_quotient_is_exactly_36_unique_contexts():
    tails = p.less_than_tail_contexts()
    assert len(tails) == 36
    assert len(set(tails)) == 36
    assert all(text.strip() for text in tails)
    assert all(text.count("?") <= 1 for text in tails)


class _Params:
    abbrev_types = set()
    collocations = set()


class _Tokenizer:
    _params = _Params()


def _toy_count(text: str) -> int:
    # This is deliberately not evidence about Punkt. It only exercises the
    # verifier interface in unit tests. Independent proof-grade execution uses
    # exact NLTK 3.10.3 + the pinned Punkt data archive.
    if all(ch not in text for ch in ".?!"):
        return 1
    if "\n" in text and all(part.rstrip(".").isdigit() for part in text.split("\n")):
        return len(text.split("\n"))
    return 1


def test_injected_verifier_fails_closed_on_pinned_model_exception():
    class BadParams:
        abbrev_types = set()
        collocations = {("##number##", "##number##")}

    class BadTokenizer:
        _params = BadParams()

    try:
        p.verify_with_pinned_tokenizer(tokenizer=BadTokenizer(), count_sentences=_toy_count)
    except AssertionError as exc:
        assert "PINNED_NUMERIC_COLLOCATION_EXCEPTION" in str(exc)
    else:
        raise AssertionError("expected fail-closed numeric collocation exception")
