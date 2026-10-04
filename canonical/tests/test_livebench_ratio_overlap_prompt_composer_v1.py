import math
import re

from canonical.runtime.livebench_ratio_overlap_prompt_composer_v1 import compose
from canonical.runtime.livebench_ratio_overlap_visible_token_constructor_v1 import exact_checker_overlap


def _in_band(value: float, target: float, tolerance: float = 2.0) -> bool:
    return target - tolerance <= value <= target + tolerance


def test_ratio_only_is_exact_despite_raw_reference_whitespace():
    reference = (
        "Use induction to prove the following claims.\n"
        "Consider a simple undirected graph with m edges, n vertices,\n"
        "and p connected components."
    )
    prompt = (
        "Use induction to prove the following claims. "
        "Consider a simple undirected graph with m edges, n vertices, "
        "and p connected components. "
        "Maintain a trigram overlap of 72% (±2%) with the provided reference text."
    )
    out = compose(prompt)
    assert out["status"] == "PASS_UNDER_PROMPT_SEGMENTER_CONTRACT"
    exact = exact_checker_overlap(out["response"], reference)
    assert _in_band(exact, 72)
    assert math.isclose(exact, out["predicted_exact_overlap_percent"], abs_tol=1e-12)


def test_sentence_keyword_thirtieth_sentence_stays_ratio_exact():
    reference = (
        "Write a believable sci fi history about a parasite that could loosely "
        "retain the form, memories and personality of its hosts, eventually being destroyed."
    )
    prompt = (
        "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
        "The response must include keyword horary in the 30-th sentence. "
        + reference
    )
    out = compose(prompt)
    assert out["composition_mode"] == "RATIO_PLUS_SENTENCE_KEYWORD"
    exact = exact_checker_overlap(out["response"], reference)
    assert _in_band(exact, 23)
    assert math.isclose(exact, out["predicted_exact_overlap_percent"], abs_tol=1e-12)

    # The constructor's grammar uses only periods as terminators and excludes
    # periods from both the selected token and required keyword.
    sentences = [part for part in out["response"].split(".") if part]
    assert len(sentences) == 30
    assert "horary" in sentences[29].lower()


def test_consonant_cluster_composition_uses_one_checker_visible_word():
    reference = (
        'What are the pros and cons of defining "model" in machine learning '
        "to be just weights and biases?"
    )
    prompt = (
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together). "
        "Maintain a trigram overlap of 11% (±2%) with the provided reference text. "
        + reference
    )
    out = compose(prompt)
    assert out["composition_mode"] == "RATIO_PLUS_CONSONANT_CLUSTER"
    exact = exact_checker_overlap(out["response"], reference)
    assert _in_band(exact, 11)
    assert len(out["response"].split()) == 1
    assert re.search(r"[bcdfghjklmnpqrstvwxyz]{2}", out["response"], re.IGNORECASE)


def test_private_use_collision_is_removed_from_fresh_pool():
    reference = "Alpha \ue000 boundary with transformable reference token"
    prompt = (
        "Alpha \ue000 boundary with transformable reference token "
        "Maintain a trigram overlap of 50% (±2%) with the provided reference text."
    )
    out = compose(prompt)
    assert out["status"] == "PASS_UNDER_PROMPT_SEGMENTER_CONTRACT"
    assert "\ue000" not in out["response"]
    exact = exact_checker_overlap(out["response"], reference)
    assert _in_band(exact, 50)


def test_unproven_sentence_plus_consonant_combination_fails_closed():
    prompt = (
        "Base transformable request. "
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together). "
        "Maintain a trigram overlap of 30% (±2%) with the provided reference text. "
        "The response must include keyword horary in the 3-rd sentence."
    )
    out = compose(prompt)
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "UNPROVEN_MULTI_CO_CONSTRAINT_COMPOSITION"
