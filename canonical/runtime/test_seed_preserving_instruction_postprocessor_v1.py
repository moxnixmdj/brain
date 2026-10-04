#!/usr/bin/env python3
from canonical.runtime.seed_preserving_instruction_postprocessor_v1 import transform


def test_exact_response():
    out = transform("irrelevant semantic draft", 'Reply with exactly "OK"')
    assert out["status"] == "PASS"
    assert out["response"] == "OK"
    assert "EXACT_RESPONSE" in out["applied_transforms"]


def test_case_conversion():
    out = transform("Mixed Case Answer", "Write the entire response in lowercase only.")
    assert out["status"] == "PASS"
    assert out["response"] == "mixed case answer"


def test_prefix_suffix():
    out = transform(
        "core answer",
        'Response must start with "BEGIN" and response must end with "END"',
    )
    assert out["status"] == "PASS"
    assert out["response"].startswith("BEGIN")
    assert out["response"].endswith("END")


def test_already_satisfies_word_floor():
    out = transform("one two three four five", "Answer with at least 5 words.")
    assert out["status"] == "PASS"
    assert out["response"] == "one two three four five"


def test_word_floor_needing_invention_fails_closed():
    out = transform("one two", "Answer with at least 5 words.")
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "UNSAFE_TRANSFORMATION_REQUIRED"
    assert "MIN_WORDS" in out["validation_errors"]


def test_forbidden_literal_needing_deletion_fails_closed():
    out = transform(
        "the semantic answer contains banana",
        'Do not include the word "banana"',
    )
    assert out["status"] == "FAIL_CLOSED"
    assert "FORBIDDEN_LITERAL:banana" in out["validation_errors"]


def test_empty_seed_fails_closed():
    out = transform("", 'Reply with exactly "OK"')
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "SEMANTIC_SEED_REQUIRED"
