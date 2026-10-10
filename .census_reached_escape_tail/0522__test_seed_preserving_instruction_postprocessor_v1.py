#!/usr/bin/env python3
from canonical.runtime.seed_preserving_instruction_postprocessor_v1 import transform


def test_exact_response_conflicting_seed_fails_closed():
    out = transform("irrelevant semantic draft", 'Reply with exactly "OK"')
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "EXACT_RESPONSE_CONFLICTS_WITH_SEED_PRESERVATION"
    assert out["response"] is None


def test_exact_response_already_equal_seed_passes():
    out = transform("OK", 'Reply with exactly "OK"')
    assert out["status"] == "PASS"
    assert out["response"] == "OK"
    assert out["seed_verbatim_preserved"] is True


def test_lossy_case_conversion_fails_closed():
    out = transform("Mixed Case Answer", "Write the entire response in lowercase only.")
    assert out["status"] == "FAIL_CLOSED"
    assert "LOWERCASE_ONLY" in out["validation_errors"]


def test_already_lowercase_seed_passes_without_rewrite():
    out = transform("mixed case answer", "Write the entire response in lowercase only.")
    assert out["status"] == "PASS"
    assert out["response"] == "mixed case answer"
    assert out["applied_transforms"] == []


def test_prefix_suffix_preserve_seed_verbatim():
    seed = "core answer"
    out = transform(
        seed,
        'Response must start with "BEGIN" and response must end with "END"',
    )
    assert out["status"] == "PASS"
    assert out["response"].startswith("BEGIN")
    assert out["response"].endswith("END")
    assert seed in out["response"]
    assert out["seed_verbatim_preserved"] is True


def test_already_satisfies_word_floor():
    seed = "one two three four five"
    out = transform(seed, "Answer with at least 5 words.")
    assert out["status"] == "PASS"
    assert out["response"] == seed
    assert out["seed_verbatim_preserved"] is True


def test_word_floor_needing_invention_fails_closed():
    out = transform("one two", "Answer with at least 5 words.")
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "SEED_MUTATION_OR_UNSUPPORTED_TRANSFORMATION_REQUIRED"
    assert "MIN_WORDS" in out["validation_errors"]


def test_forbidden_literal_needing_deletion_fails_closed():
    out = transform(
        "the semantic answer contains banana",
        'Do not include the word "banana"',
    )
    assert out["status"] == "FAIL_CLOSED"
    assert "FORBIDDEN_LITERAL:banana" in out["validation_errors"]


def test_required_literal_already_present_passes():
    seed = "the answer contains cedar"
    out = transform(seed, 'Include the word "cedar"')
    assert out["status"] == "PASS"
    assert out["response"] == seed


def test_empty_seed_fails_closed():
    out = transform("", 'Reply with exactly "OK"')
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "SEMANTIC_SEED_REQUIRED"
