from canonical.runtime.livebench_ngram_whitespace_invariant_compiler_v1 import (
    construct,
    construct_from_pinned_public_prompt,
    normalize_ws,
    overlap_percent,
    recover_pinned_public_ratio_reference,
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


def test_prompt_only_singleton_suffix():
    prompt = (
        "base request text "
        "Maintain a trigram overlap of 72% (±2%) with the provided reference text."
    )
    got = recover_pinned_public_ratio_reference(prompt)
    assert got["normalized_reference"] == "base request text"
    assert got["percentage"] == 72


def test_prompt_only_keyword_prefix():
    prompt = (
        "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
        "The response must include keyword horary in the 30-th sentence. "
        "base request text"
    )
    got = recover_pinned_public_ratio_reference(prompt)
    assert got["normalized_reference"] == "base request text"
    assert got["percentage"] == 23


def test_prompt_only_consonant_and_zero_width_boundary():
    prompt = (
        "base request text\u200b "
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together). "
        "Maintain a trigram overlap of 54% (±2%) with the provided reference text."
    )
    got = recover_pinned_public_ratio_reference(prompt)
    assert got["normalized_reference"] == "base request text"
    witness = construct_from_pinned_public_prompt(prompt)
    assert witness["normalized_reference_recovered_from_visible_prompt"] is True
    assert abs(witness["score_against_normalized_reference_percent"] - 54) <= 2
