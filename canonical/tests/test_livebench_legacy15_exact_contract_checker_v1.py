import types

import pytest

from canonical.runtime import livebench_legacy15_exact_contract_checker_v1 as c


class Forbidden:
    def __init__(self, iid):
        self.iid = iid

    def build_description(self, *, forbidden_words):
        self.words = list(forbidden_words)
        return "x"

    def check_following(self, value):
        return all(w.lower() not in value.lower().split() for w in self.words)


class End:
    def __init__(self, iid):
        self.iid = iid

    def build_description(self, *, end_phrase):
        self.end_phrase = end_phrase
        return "x"

    def check_following(self, value):
        return value.strip().strip('"').lower().endswith(
            self.end_phrase.strip().lower()
        )


REGISTRY = types.SimpleNamespace(
    INSTRUCTION_DICT={
        "keywords:forbidden_words": Forbidden,
        "startend:end_checker": End,
    }
)


def test_git_blob_helper_matches_git_empty_blob():
    assert c.git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def test_exact_visible_slots_feed_registry_without_defaults():
    contracts = [
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": ["omega"]},
        },
        {
            "instruction_id": "startend:end_checker",
            "slots": {"end_phrase": "Any other questions?"},
        },
    ]
    assert c.evaluate_with_registry(
        "alpha Any other questions?", contracts, REGISTRY
    ) == (True, True)
    assert c.evaluate_with_registry(
        "omega Any other questions?", contracts, REGISTRY
    ) == (False, True)


def test_exact_checker_matches_strict_nonempty_outer_gate():
    contract = [{
        "instruction_id": "keywords:forbidden_words",
        "slots": {"forbidden_words": ["omega"]},
    }]
    # The checker alone accepts empty text, but frozen LiveBench strict
    # evaluation rejects it before checker execution.
    assert c.evaluate_with_registry("", contract, REGISTRY) == (False,)
    assert c.evaluate_with_registry("   \n\t", contract, REGISTRY) == (False,)
    assert c.evaluate_with_registry("alpha", contract, REGISTRY) == (True,)


def test_missing_slot_fails_closed_instead_of_randomizing():
    with pytest.raises(c.ExactContractCheckerError, match="VISIBLE_SLOT_SHAPE_MISMATCH"):
        c.evaluate_with_registry(
            "x",
            [{"instruction_id": "startend:end_checker", "slots": {}}],
            REGISTRY,
        )


def test_extra_slot_fails_closed():
    with pytest.raises(c.ExactContractCheckerError, match="VISIBLE_SLOT_SHAPE_MISMATCH"):
        c.validate_contract(
            {
                "instruction_id": "detectable_format:title",
                "slots": {"invented": 1},
            }
        )


def test_duplicate_id_fails_closed():
    row = {
        "instruction_id": "keywords:forbidden_words",
        "slots": {"forbidden_words": ["omega"]},
    }
    with pytest.raises(c.ExactContractCheckerError, match="DUPLICATE_INSTRUCTION_ID"):
        c.evaluate_with_registry("x", [row, row], REGISTRY)


def test_outside_active15_fails_closed():
    with pytest.raises(c.ExactContractCheckerError, match="OUTSIDE_FROZEN_ACTIVE15"):
        c.validate_contract({"instruction_id": "punctuation:no_comma", "slots": {}})
