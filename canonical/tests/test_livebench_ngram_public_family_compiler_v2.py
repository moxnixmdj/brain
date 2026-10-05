import pytest

from canonical.runtime.livebench_ngram_public_family_compiler_v2 import (
    PublicFamilyCompilerError,
    consonant_cluster_pass,
    construct_from_public_ratio_prompt,
    overlap_percent,
)


def test_raw_whitespace_is_not_required_for_score():
    raw_reference = "alpha\n\nbeta\tgamma"
    prompt = (
        "alpha beta gamma "
        "Maintain a trigram overlap of 50% (±2%) with the provided reference text."
    )
    witness = construct_from_public_ratio_prompt(prompt)
    raw_score = overlap_percent(witness["response"], raw_reference)
    assert 48 < raw_score < 52
    assert witness["exact_raw_reference_required"] is False
    assert witness["whitespace_free"] is True


def test_sentence_keyword_composes_with_overlap():
    prompt = (
        "Maintain a trigram overlap of 13% (±2%) with the provided reference text. "
        "The response must include keyword giraffe in the 7-th sentence. "
        "Is it easier to urbanize a jungle or to urbanize a desert?"
    )
    witness = construct_from_public_ratio_prompt(prompt)
    response = witness["response"]
    sentences = response.split(".")
    if sentences and sentences[-1] == "":
        sentences = sentences[:-1]
    assert len(sentences) >= 7
    assert "giraffe" in sentences[6].lower()
    assert 11 < witness["score_against_normalized_reference_percent"] < 15


def test_consonant_cluster_composes_with_overlap():
    prompt = (
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together). "
        "Maintain a trigram overlap of 54% (±2%) with the provided reference text. "
        "Write a detailed analysis on whether animation studios might be successful"
    )
    witness = construct_from_public_ratio_prompt(prompt)
    assert consonant_cluster_pass(witness["response"])
    assert 52 < witness["score_against_normalized_reference_percent"] < 56


def test_multiple_ratio_descriptions_fail_closed():
    prompt = (
        "alpha "
        "Maintain a trigram overlap of 50% (±2%) with the provided reference text. "
        "Maintain a trigram overlap of 60% (±2%) with the provided reference text."
    )
    with pytest.raises(PublicFamilyCompilerError, match="RATIO_DESCRIPTION_COUNT_NOT_ONE"):
        construct_from_public_ratio_prompt(prompt)


def test_unproved_keyword_plus_consonant_composition_fails_closed():
    prompt = (
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together). "
        "Maintain a trigram overlap of 30% (±2%) with the provided reference text. "
        "The response must include keyword bridge in the 2-th sentence. "
        "base reference material"
    )
    with pytest.raises(PublicFamilyCompilerError, match="UNPROVED_KEYWORD_PLUS_CONSONANT_COMPOSITION"):
        construct_from_public_ratio_prompt(prompt)
