from canonical.runtime.livebench_ngram_overlap_whitespace_invariant_constructor_v1 import (
    construct_overlap_witness,
    normalize_ws,
    overlap_percent,
    verify_against_raw_reference,
)


def test_whitespace_normalization_is_exact_for_whitespace_free_candidate():
    raw = "alpha\n\t beta   gamma\n delta"
    normalized = normalize_ws(raw)
    candidate = "alphabetagamma"
    out = verify_against_raw_reference(candidate, raw, normalized)
    assert out["status"] == "PASS"
    assert out["exact_equal"] is True


def test_constructor_hits_livebench_threshold_neighborhood_without_raw_reference():
    # 65.7 is the terminal family threshold, not a hidden case parameter.
    ref = "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda."
    out = construct_overlap_witness(ref, 65.7)
    assert out["status"] == "PASS"
    assert out["candidate_whitespace_free"] is True
    assert abs(out["predicted_percent"] - 65.7) <= 2.0


def test_constructor_handles_low_overlap_target():
    ref = "ordinary reference material with enough visible characters"
    out = construct_overlap_witness(ref, 6)
    assert out["status"] == "PASS"
    assert abs(out["predicted_percent"] - 6) <= 2.0


def test_verifier_rejects_wrong_normalized_reference():
    raw = "alpha   beta"
    out = verify_against_raw_reference("alph", raw, "alpha gamma")
    assert out["status"] == "FAIL"
    assert out["reason"] == "NORMALIZED_REFERENCE_MISMATCH"


def test_candidate_overlap_matches_raw_after_mixed_whitespace_changes():
    raw = "one\n\ttwo   three\r\nfour"
    normalized = normalize_ws(raw)
    out = construct_overlap_witness(normalized, 50)
    assert out["status"] == "PASS"
    candidate = out["candidate"]
    assert overlap_percent(candidate, raw) == overlap_percent(candidate, normalized)
