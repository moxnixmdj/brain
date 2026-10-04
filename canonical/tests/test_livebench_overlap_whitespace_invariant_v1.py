from canonical.runtime.livebench_overlap_whitespace_invariant_v1 import (
    OverlapInvariantError,
    char_trigrams,
    construct_whitespace_invariant_overlap,
    normalize_visible_whitespace,
    project_public_overlap_reference,
)


def _exact_checker_score(response: str, raw_reference: str) -> float:
    r = char_trigrams(response)
    h = char_trigrams(raw_reference)
    return 100.0 * len(r & h) / len(r)


def test_constructor_score_is_invariant_to_whitespace_variants():
    visible = "alpha bravo charlie delta"
    variants = [
        "alpha bravo charlie delta",
        "alpha\n\tbravo   charlie\r\ndelta",
        "alpha    bravo charlie       delta",
    ]
    for target in (6, 11, 24, 50, 59, 72, 93, 100):
        cert = construct_whitespace_invariant_overlap(visible, target)
        assert cert.unknown_unique_trigrams == 0
        for raw in variants:
            score = _exact_checker_score(cert.response, raw)
            assert abs(score - cert.certified_percent) < 1e-12
            assert abs(score - target) <= 2.0


def test_projector_handles_prefix_and_suffix_public_shapes():
    ref = "Alpha beta gamma delta."
    suffix = ref + " Maintain a trigram overlap of 72% (±2%) with the provided reference text."
    prefix = "Maintain a trigram overlap of 72% (±2%) with the provided reference text. " + ref
    for prompt in (suffix, prefix):
        p = project_public_overlap_reference(prompt)
        assert p["visible_reference"] == ref
        assert p["target_percent"] == 72
        assert p["hidden_kwargs_used"] is False


def test_projector_handles_public_companion_shapes():
    ref = "Alpha beta gamma delta."
    keyword = "The response must include keyword giraffe in the 7-th sentence."
    consonant = (
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together)."
    )
    prompts = [
        f"{ref} Maintain a trigram overlap of 13% (±2%) with the provided reference text. {keyword}",
        f"Maintain a trigram overlap of 13% (±2%) with the provided reference text. {keyword} {ref}",
        f"{ref} {consonant} Maintain a trigram overlap of 54% (±2%) with the provided reference text.",
        f"{consonant} Maintain a trigram overlap of 54% (±2%) with the provided reference text. {ref}",
    ]
    for prompt in prompts:
        p = project_public_overlap_reference(prompt)
        assert p["visible_reference"] == ref


def test_projector_fails_closed_on_unknown_envelope():
    try:
        project_public_overlap_reference(
            "unrecognized wrapper Maintain a trigram overlap of 50% (±2%) "
            "with the provided reference text. extra unknown instruction"
        )
    except OverlapInvariantError:
        pass
    else:
        raise AssertionError("unknown envelope must fail closed")


def test_zwsp_separator_is_not_part_of_reference():
    ref = "Alpha beta gamma."
    prompt = ref + "\u200bMaintain a trigram overlap of 74% (±2%) with the provided reference text."
    p = project_public_overlap_reference(prompt)
    assert normalize_visible_whitespace(p["visible_reference"]) == ref
