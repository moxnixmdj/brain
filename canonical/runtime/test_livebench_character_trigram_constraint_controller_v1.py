#!/usr/bin/env python3
from canonical.runtime.livebench_character_trigram_constraint_controller_v1 import (
    char_trigrams,
    parse_visible_prompt,
    solve_visible_prompt,
)


def score(response: str, reference: str) -> float:
    a=char_trigrams(response)
    b=char_trigrams(reference)
    return 100.0*len(a & b)/len(a)


def test_ratio_only_whitespace_robust():
    ref="Alpha beta\n\ngamma transformation"
    prompt="Alpha beta gamma transformation Maintain a trigram overlap of 72% (±2%) with the provided reference text."
    out=solve_visible_prompt(prompt)
    assert out["status"].startswith("PASS")
    s=score(out["response"],ref)
    assert 70 <= s <= 74


def test_zero_width_format_removed_from_reference_candidate():
    prompt="Alpha beta gamma. \u200bMaintain a trigram overlap of 50% (±2%) with the provided reference text."
    parsed=parse_visible_prompt(prompt)
    assert parsed["reference_candidate"]=="Alpha beta gamma."


def test_sentence_keyword_composition():
    ref="Is it easier to urbanize a jungle or to urbanize a desert?"
    prompt=(
        ref
        +" Maintain a trigram overlap of 13% (±2%) with the provided reference text."
        +" The response must include keyword giraffe in the 7-th sentence."
    )
    out=solve_visible_prompt(prompt)
    assert out["status"].startswith("PASS")
    response=out["response"]
    assert 11 <= score(response,ref) <= 15
    sentences=[x.strip() for x in response.split(".") if x.strip()]
    assert len(sentences)>=7
    assert "giraffe" in sentences[6].lower()


def test_consonant_cluster_composition():
    ref='What are the pros and cons of defining "model" in machine learning to be just weights and biases?'
    prompt=(
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together). "
        "Maintain a trigram overlap of 11% (±2%) with the provided reference text. "
        +ref
    )
    out=solve_visible_prompt(prompt)
    assert out["status"].startswith("PASS")
    assert 9 <= score(out["response"],ref) <= 13
    consonants=set("bcdfghjklmnpqrstvwxyz")
    for word in out["response"].lower().strip().split():
        ascii_letters=[c for c in word if "a" <= c <= "z"]
        if not ascii_letters:
            continue
        assert any(
            word[i] in consonants and word[i+1] in consonants
            for i in range(len(word)-1)
        )


def test_missing_ratio_fails_closed():
    out=solve_visible_prompt("Just answer the question.")
    assert out["status"]=="FAIL_CLOSED"
    assert out["response"] is None


def test_unverified_three_way_composition_fails_closed():
    prompt=(
        "Base request. Maintain a trigram overlap of 50% (±2%) with the provided reference text. "
        "The response must include keyword giraffe in the 2-th sentence. "
        "Ensure each word in your response has at least one consonant cluster (two or more consonants together)."
    )
    out=solve_visible_prompt(prompt)
    assert out["status"]=="FAIL_CLOSED"
