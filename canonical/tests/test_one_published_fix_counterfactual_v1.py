"""Controls for the bounded one-fix diagnostic; no network or external benchmark required."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from canonical.tools import one_published_fix_counterfactual_v1 as experiment  # noqa: E402
from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.swe_kernel.skill_verification_contract_v1 import VerificationResult  # noqa: E402

BEFORE = "def first(a, b):\n    return a ^ b\n"
AFTER = "def first(a, b):\n    return a & b\n"
TARGET = "def second(x, y):\n    return x ^ y\n"
FIXED = "def second(x, y):\n    return x & y\n"


def bundle():
    return {"teacher": {"name": "first", "before": BEFORE, "after": AFTER},
            "sources": {"second": TARGET, "unrelated": "def other(x):\n    return x + 1\n"}}


def test_empty_forward_reverse_keep_distinct_information():
    empty = experiment.generate(bundle(), "empty")
    forward = experiment.generate(bundle(), "forward")
    reverse = experiment.generate(bundle(), "reverse")
    assert empty["lesson_count"] == 0
    assert empty["candidates"] == {"second": [], "unrelated": []}
    assert forward["lesson_count"] == reverse["lesson_count"] == 1
    assert any(kinds.same_program(source, FIXED) for source in forward["candidates"]["second"])
    assert reverse["candidates"]["second"] == []
    assert forward["candidates"]["unrelated"] == []
    assert bundle()["sources"]["second"] == TARGET


def test_direction_control_is_an_actual_reversed_lesson():
    data = bundle()
    data["sources"] = {"repaired": FIXED}
    reverse = experiment.generate(data, "reverse")
    assert any(kinds.same_program(source, TARGET) for source in reverse["candidates"]["repaired"])


def test_fresh_process_rederivation_matches_without_python_object_state(tmp_path):
    path = tmp_path / "lesson.json"
    path.write_text(json.dumps(bundle()))
    for arm in experiment.ARMS:
        assert experiment.fresh_generation(path, arm) == experiment.generate(bundle(), arm)
        assert len(experiment.generate(bundle(), arm)["candidates"]["second"]) <= experiment.BUDGET


def test_unknown_arm_refuses():
    with pytest.raises(ValueError, match="UNKNOWN_ARM"):
        experiment.generate(bundle(), "undocumented")


class SequenceOracle:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def __call__(self, source):
        self.calls.append(source)
        passed = next(self.outcomes)
        return VerificationResult(passed, "TEST_SUITE", "0" * 64, "test", {"test_count": 1})


def test_first_test_pass_requires_confirmation_and_strict_match_is_separate():
    oracle = SequenceOracle([False, True, True])
    result = experiment.select(oracle, [TARGET, FIXED], FIXED)
    assert result["accepted"] is True
    assert result["published_fix_match"] is True
    assert result["candidate_tests"] == 2
    assert result["confirmation_tests"] == 1
    assert oracle.calls == [TARGET, FIXED, FIXED]
    other = experiment.select(SequenceOracle([True, True]), ["def f(): return 1"], FIXED)
    assert other["accepted"] is True
    assert other["published_fix_match"] is False


def test_failed_confirmation_is_not_an_accepted_repair():
    oracle = SequenceOracle([True, False])
    result = experiment.select(oracle, [FIXED], FIXED)
    assert result["accepted"] is False
    assert result["published_fix_match"] is False
    assert result["confirmation_tests"] == 1


def test_empty_memory_spends_no_candidate_tests():
    oracle = SequenceOracle([])
    result = experiment.select(oracle, [], FIXED)
    assert result["accepted"] is False
    assert result["candidate_tests"] == result["confirmation_tests"] == 0
    assert oracle.calls == []


def test_summary_does_not_count_test_only_repairs_as_reference_matches():
    row = {"arms": {
        "empty": {"accepted": False, "published_fix_match": False, "candidate_tests": 0, "confirmation_tests": 0},
        "forward": {"accepted": True, "published_fix_match": False, "candidate_tests": 3, "confirmation_tests": 1},
        "reverse": {"accepted": False, "published_fix_match": False, "candidate_tests": 2, "confirmation_tests": 0}}}
    counts = experiment.counts({"target": row})
    assert counts["forward"] == {"targets": 1, "accepted": 1, "published_fix_matches": 0,
                                  "candidates_tested": 3, "confirmations": 1}
    assert counts["empty"]["accepted"] == counts["reverse"]["accepted"] == 0
