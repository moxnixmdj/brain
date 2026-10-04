from canonical.runtime.livebench_ngram_whitespace_invariant_compiler_v1 import (
    construct,
    normalize_ws,
    overlap_percent,
    whitespace_invariant_for_reference,
)


def test_whitespace_invariance_synthetic():
    raw = "alpha\n\n beta\t gamma"
    normalized = normalize_ws(raw)
    witness = construct(normalized, 50)
    response = witness["response"]
    assert whitespace_invariant_for_reference(response, raw)
    assert overlap_percent(response, raw) == overlap_percent(response, normalized)
    assert abs(overlap_percent(response, raw) - 50) <= 2


def test_high_overlap_synthetic():
    raw = "extraordinarytoken\n second"
    witness = construct(normalize_ws(raw), 93)
    assert witness["whitespace_free"] is True
    assert abs(overlap_percent(witness["response"], raw) - 93) <= 2


def test_low_overlap_synthetic():
    raw = "reference material"
    witness = construct(normalize_ws(raw), 6)
    assert abs(overlap_percent(witness["response"], raw) - 6) <= 2
