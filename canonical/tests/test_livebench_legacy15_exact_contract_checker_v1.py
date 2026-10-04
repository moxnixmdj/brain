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


def test_verify_pinned_source_rejects_util_drift(tmp_path, monkeypatch):
    pkg = tmp_path / "livebench" / "if_runner" / "instruction_following_eval"
    pkg.mkdir(parents=True)
    registry = pkg / "instructions_registry.py"
    instructions = pkg / "instructions.py"
    util = pkg / "instructions_util.py"
    registry.write_bytes(b"registry")
    instructions.write_bytes(b"instructions")
    util.write_bytes(b"util")

    monkeypatch.setattr(c, "PINNED_REGISTRY_BLOB", c.git_blob_sha(registry.read_bytes()))
    monkeypatch.setattr(c, "PINNED_INSTRUCTIONS_BLOB", c.git_blob_sha(instructions.read_bytes()))
    monkeypatch.setattr(c, "PINNED_UTIL_BLOB", c.git_blob_sha(util.read_bytes()))
    out = c.verify_pinned_source(tmp_path)
    assert out["status"] == "PASS__EXACT_PINNED_CHECKER_SOURCE_BOUND"
    assert out["instructions_util_git_blob_sha"] == c.git_blob_sha(b"util")

    util.write_bytes(b"drift")
    with pytest.raises(c.ExactContractCheckerError, match="INSTRUCTIONS_UTIL_BLOB_DRIFT"):
        c.verify_pinned_source(tmp_path)
