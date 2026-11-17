"""A verdict is only a measurement if the judge can pass the answer and fail the bug.

Each test pins one way the audit could be a fiction:

1. It could accept a judge that rejects the corpus's own answer -- the false-reject that made last
   session's counts wrong in both directions.
2. It could accept a judge that accepts the defective program -- the false-accept that makes a loop
   learn the bug.
3. It could mistake a timeout for a wrong answer, or a generator for a wrong value.
4. It could read a verdict from an answer key. It reads one, and only to audit the instrument: the
   classification never proposes a repair.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

import judge_the_judge_v1 as judged  # noqa: E402


class TestTheComparison:
    def test_a_generator_is_compared_by_its_values_when_materialised(self) -> None:
        source = "def f(n):\n    for i in range(n):\n        yield i\n"
        naive = judged.case_outcomes(source, "f", [([3], [0, 1, 2])], 0.05, materialise=False)
        materialised = judged.case_outcomes(source, "f", [([3], [0, 1, 2])], 0.05, materialise=True)
        assert naive[0]["outcome"] == "FAIL"
        assert materialised[0]["outcome"] == "PASS"

    def test_an_infinite_generator_cannot_allocate_the_judge_to_death(self) -> None:
        source = "def f(n):\n    while True:\n        yield 1\n"
        outcome = judged.case_outcomes(source, "f", [([1], [1, 1])], 0.5, materialise=True)[0]
        assert outcome["outcome"] in {"FAIL", "TIMEOUT"}

    def test_a_timeout_is_not_a_wrong_answer(self) -> None:
        source = "def f(n):\n    while n:\n        n += 1\n    return n\n"
        outcome = judged.case_outcomes(source, "f", [([1], 0)], 0.05, materialise=True)[0]
        assert outcome["outcome"] == "TIMEOUT"

    def test_a_rising_program_is_not_a_wrong_answer(self) -> None:
        outcome = judged.case_outcomes("def f(n):\n    return n / 0\n", "f", [([1], 1)], 0.05,
                                       materialise=True)[0]
        assert outcome["outcome"] == "RAISED"


class TestTheRule:
    def test_the_audit_names_a_comparison_that_could_not_see_the_answer(self) -> None:
        naive = [{"outcome": "FAIL"}, {"outcome": "FAIL"}]
        materialised = [{"outcome": "PASS"}, {"outcome": "PASS"}]
        slow = [{"outcome": "PASS"}, {"outcome": "PASS"}]
        assert judged.diagnose({"naive": naive, "materialised": materialised},
                               {"materialised": slow}) == "GENERATOR_NOT_MATERIALISED"

    def test_the_audit_names_a_clock_that_was_too_short(self) -> None:
        naive = [{"outcome": "TIMEOUT"}, {"outcome": "PASS"}]
        materialised = [{"outcome": "TIMEOUT"}, {"outcome": "PASS"}]
        slow = [{"outcome": "PASS"}, {"outcome": "PASS"}]
        assert judged.diagnose({"naive": naive, "materialised": materialised},
                               {"materialised": slow}) == "TIMEOUT_TOO_SHORT"

    def test_a_disagreement_that_survives_every_repair_is_named_as_one(self) -> None:
        naive = [{"outcome": "FAIL"}]
        materialised = [{"outcome": "FAIL"}]
        slow = [{"outcome": "FAIL"}]
        assert judged.diagnose({"naive": naive, "materialised": materialised},
                               {"materialised": slow}) == "VALUE_DISAGREES"


class TestTheSummary:
    def test_an_inadmissible_judge_is_never_counted_as_measuring_anything(self) -> None:
        rows = [
            {"task": "a", "stage": "AUDITED", "judge_is_admissible": True,
             "judge_passes_the_answer": True, "naive_judge_passes_the_answer": True,
             "judge_fails_the_bug": True, "real_judge": {"corpus_test_passes": True}},
            {"task": "b", "stage": "AUDITED", "judge_is_admissible": False, "cause": "VALUE_DISAGREES",
             "judge_passes_the_answer": False, "naive_judge_passes_the_answer": False,
             "judge_fails_the_bug": True, "real_judge": {"corpus_test_passes": True}},
        ]
        summary = judged.summarise(rows)
        assert summary["judge_admissible"] == 1
        assert summary["inadmissible_tasks"] == ["b"]
        assert summary["causes"] == {"VALUE_DISAGREES": 1}

    def test_a_test_file_that_transforms_its_own_data_is_detected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "python_testcases").mkdir()
            (root / "python_testcases" / "test_x.py").write_text(
                "testdata = load_json_testcases(x.__name__)\n"
                "testdata = [[inp, [tuple(y) for y in out]] for inp, out in testdata]\n")
            found = judged.test_file_normalisation(root, "x")
        assert found["normalises_the_data"] is True
        assert found["rewrites"]
