import pytest

from canonical.runtime.livebench_ratio_overlap_visible_segmenter_v1 import (
    VisibleReferenceSegmentationError,
    construct_overlap_witness_from_visible_prompt,
    recover_normalized_reference,
)


def test_suffix_overlap_recovers_normalized_reference():
    prompt = (
        "alpha   beta\n gamma "
        "Maintain a trigram overlap of 72% (±2%) with the provided reference text."
    )
    out = recover_normalized_reference(prompt)
    assert out["normalized_reference"] == "alpha beta gamma"
    assert out["percentage"] == 72.0
    assert out["hidden_kwargs_required"] is False


def test_prefix_overlap_and_sentence_keyword_are_removed():
    prompt = (
        "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
        "The response must include keyword horary in the 30-th sentence. "
        "Write a believable sci fi history."
    )
    out = recover_normalized_reference(prompt)
    assert out["normalized_reference"] == "Write a believable sci fi history."
    assert out["removed"]["sentence_keyword"] == 1


def test_consonant_cluster_co_constraint_is_removed():
    prompt = (
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together). "
        "Maintain a trigram overlap of 11% (±2%) with the provided reference text. "
        "What are the pros and cons?"
    )
    out = recover_normalized_reference(prompt)
    assert out["normalized_reference"] == "What are the pros and cons?"
    assert out["removed"]["consonant_cluster"] == 1


def test_visible_prompt_composes_with_whitespace_invariant_constructor():
    prompt = (
        "reference material for testing "
        "Maintain a trigram overlap of 50% (±2%) with the provided reference text."
    )
    out = construct_overlap_witness_from_visible_prompt(prompt)
    assert out["status"] == "PASS"
    assert out["overlap_witness"]["within_tolerance"] is True
    assert out["overlap_witness"]["whitespace_free"] is True


def test_missing_or_ambiguous_overlap_fails_closed():
    with pytest.raises(VisibleReferenceSegmentationError):
        recover_normalized_reference("no overlap clause")
    duplicate = (
        "base Maintain a trigram overlap of 50% (±2%) with the provided reference text. "
        "Maintain a trigram overlap of 50% (±2%) with the provided reference text."
    )
    with pytest.raises(VisibleReferenceSegmentationError):
        recover_normalized_reference(duplicate)
