#!/usr/bin/env python3
from canonical.runtime.seed_preserving_instruction_postprocessor_v2 import (
    PRESERVATION_CONTRACT,
    PUBLIC_IFBENCH_INSTRUCTIONS_BLOB,
    _check_nested_parentheses,
    _check_nested_quotes,
    _check_newline_words,
    _check_punctuation_cover,
    _seed_preserved,
    transform,
)

def test_public_source_is_content_addressed():
    assert PUBLIC_IFBENCH_INSTRUCTIONS_BLOB == "7f167018e0c5472b04e13cbf847e5988c04ecb11"

def test_preservation_contract_is_explicit_and_mechanical():
    assert PRESERVATION_CONTRACT == (
        "REMOVE_WHITESPACE_SEED_OCCURS_VERBATIM_AND_CONTIGUOUSLY_INSIDE_"
        "REMOVE_WHITESPACE_RESPONSE"
    )
    assert _seed_preserved("Alpha beta", "?! Alpha\nbeta ;:") is True
    assert _seed_preserved("Alpha beta", "?! alpha\nbeta ;:") is False

def test_nested_parentheses_public_contract():
    instruction = "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep."
    seed = "The semantic answer remains intact."
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert seed in out["response"]
    assert out["seed_nonwhitespace_content_preserved"] is True
    assert _check_nested_parentheses(out["response"])

def test_nested_quotes_public_contract():
    instruction = (
        "Include quotes within quotes within quotes, at least 3 levels deep, "
        "alternating between double quotes and single quotes."
    )
    seed = "The semantic answer remains intact."
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert seed in out["response"]
    assert out["seed_nonwhitespace_content_preserved"] is True
    assert _check_nested_quotes(out["response"])

def test_punctuation_cover_public_contract():
    instruction = (
        "Use every standard punctuation mark at least once, including semicolons, "
        "colons, and the interrobang (?!)."
    )
    seed = "The semantic answer remains intact"
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert out["response"].startswith(seed)
    assert out["seed_nonwhitespace_content_preserved"] is True
    assert _check_punctuation_cover(out["response"])

def test_newline_words_public_contract_preserves_every_nonwhitespace_seed_character():
    instruction = "Write each word on a new line."
    seed = "alpha beta gamma delta"
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert out["response"] == "alpha\nbeta\ngamma\ndelta"
    assert out["response"].split() == seed.split()
    assert out["seed_nonwhitespace_content_preserved"] is True
    assert _check_newline_words(out["response"])

def test_composed_public_structural_constraints_preserve_seed_core():
    instruction = (
        "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep. "
        "Use every standard punctuation mark at least once, including semicolons, "
        "colons, and the interrobang (?!). "
        "Write each word on a new line."
    )
    seed = "alpha beta gamma"
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert out["seed_nonwhitespace_content_preserved"] is True
    assert _seed_preserved(seed, out["response"])
    assert _check_nested_parentheses(out["response"])
    assert _check_punctuation_cover(out["response"])
    assert _check_newline_words(out["response"])

def test_case_conversion_that_would_rewrite_seed_fails_closed():
    out = transform("Mixed Case Answer", "Write the entire response in lowercase only.")
    assert out["status"] == "FAIL_CLOSED"
    assert out["response"] is None
    assert "LOWERCASE_ONLY" in out["validation_errors"]

def test_case_constraint_already_satisfied_passes_without_rewrite():
    seed = "mixed case answer"
    out = transform(seed, "Write the entire response in lowercase only.")
    assert out["status"] == "PASS"
    assert out["response"] == seed
    assert out["applied_transforms"] == []

def test_exact_response_cannot_replace_semantic_seed():
    out = transform("semantic seed", 'Reply with exactly "OK".')
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "EXACT_RESPONSE_CONFLICTS_WITH_SEED_PRESERVATION"
    assert out["response"] is None

def test_exact_response_equal_to_seed_passes():
    out = transform("OK", 'Reply with exactly "OK".')
    assert out["status"] == "PASS"
    assert out["response"] == "OK"
    assert out["seed_nonwhitespace_content_preserved"] is True

def test_word_floor_that_requires_semantic_invention_still_fails_closed():
    out = transform("one two", "Answer with at least 5 words.")
    assert out["status"] == "FAIL_CLOSED"
    assert "MIN_WORDS" in out["validation_errors"]

def test_exact_response_conflicting_with_structural_wrapper_fails_closed():
    out = transform(
        "semantic seed",
        'Reply with exactly "OK". Nest parentheses (and [brackets {and braces}]) at least 5 levels deep.',
    )
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "EXACT_RESPONSE_CONFLICTS_WITH_SEED_PRESERVATION"

def test_no_terminal_authority_or_credit_claim():
    out = transform("alpha beta", "Write each word on a new line.")
    assert out["status"] == "PASS"
    assert out["terminal_authority"] is False
    assert out["terminal_cases_used"] == 0
    assert out["incremental_spend_usd"] == 0
