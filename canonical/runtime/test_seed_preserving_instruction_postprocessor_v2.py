#!/usr/bin/env python3
from canonical.runtime.seed_preserving_instruction_postprocessor_v2 import (
    PUBLIC_IFBENCH_INSTRUCTIONS_BLOB,
    _check_nested_parentheses,
    _check_nested_quotes,
    _check_newline_words,
    _check_punctuation_cover,
    transform,
)


def test_public_source_is_content_addressed():
    assert PUBLIC_IFBENCH_INSTRUCTIONS_BLOB == "7f167018e0c5472b04e13cbf847e5988c04ecb11"


def test_nested_parentheses_public_contract():
    instruction = "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep."
    seed = "The semantic answer remains intact."
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert seed in out["response"]
    assert _check_nested_parentheses(out["response"])
    assert "IFBENCH_NESTED_PARENTHESES_5" in out["applied_transforms"]


def test_nested_quotes_public_contract():
    instruction = (
        "Include quotes within quotes within quotes, at least 3 levels deep, "
        "alternating between double quotes and single quotes."
    )
    seed = "The semantic answer remains intact."
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert seed in out["response"]
    assert _check_nested_quotes(out["response"])
    assert "IFBENCH_NESTED_QUOTES_3_ALTERNATING" in out["applied_transforms"]


def test_punctuation_cover_public_contract():
    instruction = (
        "Use every standard punctuation mark at least once, including semicolons, "
        "colons, and the interrobang (?!)."
    )
    seed = "The semantic answer remains intact"
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert out["response"].startswith(seed)
    assert _check_punctuation_cover(out["response"])
    assert "IFBENCH_PUNCTUATION_COVER" in out["applied_transforms"]


def test_newline_words_public_contract_preserves_token_order():
    instruction = "Write each word on a new line."
    seed = "alpha beta gamma delta"
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert out["response"] == "alpha\nbeta\ngamma\ndelta"
    assert out["response"].split() == seed.split()
    assert _check_newline_words(out["response"])
    assert "IFBENCH_WORD_PER_LINE" in out["applied_transforms"]


def test_composed_public_structural_constraints():
    instruction = (
        "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep. "
        "Use every standard punctuation mark at least once, including semicolons, "
        "colons, and the interrobang (?!). "
        "Write each word on a new line."
    )
    seed = "alpha beta gamma"
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert _check_nested_parentheses(out["response"])
    assert _check_punctuation_cover(out["response"])
    assert _check_newline_words(out["response"])
    assert all(word in out["response"] for word in seed.split())


def test_v1_case_constraint_still_works():
    out = transform("Mixed Case Answer", "Write the entire response in lowercase only.")
    assert out["status"] == "PASS"
    assert out["response"] == "mixed case answer"


def test_v1_word_floor_that_requires_semantic_invention_still_fails_closed():
    out = transform("one two", "Answer with at least 5 words.")
    assert out["status"] == "FAIL_CLOSED"
    assert "MIN_WORDS" in out["validation_errors"]


def test_exact_response_conflicting_with_structural_wrapper_fails_closed():
    out = transform(
        "semantic seed",
        'Reply with exactly "OK". Nest parentheses (and [brackets {and braces}]) at least 5 levels deep.',
    )
    assert out["status"] == "FAIL_CLOSED"
    assert "EXACT_RESPONSE" in out["validation_errors"]


def test_no_terminal_authority_or_credit_claim():
    out = transform("alpha beta", "Write each word on a new line.")
    assert out["status"] == "PASS"
    assert out["terminal_authority"] is False
    assert out["terminal_cases_used"] == 0
    assert out["incremental_spend_usd"] == 0
