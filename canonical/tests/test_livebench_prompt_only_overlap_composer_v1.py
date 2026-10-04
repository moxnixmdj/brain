from canonical.runtime.livebench_prompt_only_overlap_composer_v1 import (
    construct_from_prompt,
    parse_supported_prompt,
    robust_overlap_percent,
)


def test_prompt_only_overlap_standalone():
    prompt = (
        "alpha extraordinarytoken beta "
        "Maintain a trigram overlap of 72% (±2%) with the provided reference text."
    )
    out = construct_from_prompt(prompt)
    assert out["status"] == "PASS"
    assert out["raw_reference_text_required"] is False
    assert out["hidden_kwargs_required"] is False
    assert abs(out["score_percent"] - 72) <= 2


def test_zero_width_adjacent_to_constraint_is_deleted():
    prompt = (
        "axisymmetric flow proof\u200b"
        "Maintain a trigram overlap of 74% (±2%) with the provided reference text."
    )
    parsed = parse_supported_prompt(prompt)
    assert parsed["normalized_reference_surface"] == "axisymmetric flow proof"


def test_keyword_sentence_composition_is_whitespace_free_and_hits_band():
    prompt = (
        "Write a believable history about a parasite and personality. "
        "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
        "The response must include keyword horary in the 30-th sentence."
    )
    out = construct_from_prompt(prompt)
    assert out["status"] == "PASS"
    assert not any(ch.isspace() for ch in out["response"])
    sentences = [x for x in out["response"].split(".") if x]
    assert len(sentences) >= 30
    assert "horary" in sentences[29].lower()
    assert abs(out["score_percent"] - 23) <= 2


def test_consonant_cluster_composition():
    prompt = (
        "pre-recorded graphics rendering. "
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together). "
        "Maintain a trigram overlap of 54% (±2%) with the provided reference text."
    )
    out = construct_from_prompt(prompt)
    assert out["status"] == "PASS"
    assert out["consonant_cluster_required"] is True
    assert abs(out["score_percent"] - 54) <= 2
    assert robust_overlap_percent(
        out["response"], out["normalized_reference_surface"]
    ) == out["score_percent"]
