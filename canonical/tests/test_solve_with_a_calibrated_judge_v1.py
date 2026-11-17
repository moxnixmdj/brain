"""The repair must come from what a solver has at solve time, and the corpus must still be the judge.

Four ways this could cheat, each pinned:

1. It could take the answer's shape from the answer key. It may only take it from the test file — the
   object the solver can read — or from the value the candidate returns.
2. It could widen the tolerance until everything passes. Every acceptance is still put to the corpus's
   own pytest on a fresh copy, and a pass there is the only thing counted.
3. It could call a budget a verdict. A task that ran out of candidates is `BUDGET_EXHAUSTED`, never a
   failure and never a pass.
4. It could be defeated by what it judges: a candidate that loops or crashes must be `HUNG`, and must
   never be believed or allowed to take the measurement with it.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

import solve_with_a_calibrated_judge_v1 as calibrated  # noqa: E402


class TestWhatTheTestFileSays:
    def test_a_test_file_that_normalises_its_data_is_read_as_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "python_testcases").mkdir()
            (root / "python_testcases" / "test_x.py").write_text(
                "testdata = load_json_testcases(x.__name__)\n"
                "testdata = [[inp, [tuple(y) for y in out]] for inp, out in testdata]\n")
            assert calibrated.test_file_normalisation(root, "x") == "nested_lists_to_tuples"

    def test_a_test_file_without_a_transform_says_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "python_testcases").mkdir()
            (root / "python_testcases" / "test_x.py").write_text("testdata = load_json_testcases('x')\n")
            assert calibrated.test_file_normalisation(root, "x") is None

    def test_the_normalisation_does_exactly_what_the_test_file_does_one_level(self) -> None:
        value = [[1, 3], [1, 2]]
        assert calibrated.apply_normalisation(value, "nested_lists_to_tuples") == [(1, 3), (1, 2)]

    def test_without_a_normalisation_the_data_is_left_exactly_as_it_is(self) -> None:
        value = [[1, 2]]
        assert calibrated.apply_normalisation(value, None) == [[1, 2]]


class TestTheJudge:
    def test_a_generator_is_judged_by_its_values_and_bounded(self) -> None:
        flags = calibrated.satisfied_cases("def f(n):\n    for i in range(n):\n        yield i\n",
                                           "f", [([3], [0, 1, 2])], 0.05, None)
        assert flags == [True]

    def test_an_endless_generator_cannot_allocate_the_judge_to_death(self) -> None:
        flags = calibrated.satisfied_cases("def f(n):\n    while True:\n        yield 1\n",
                                           "f", [([1], [1, 1])], 0.2, None)
        assert flags == [False]

    def test_a_program_that_cannot_run_returns_none_rather_than_a_verdict(self) -> None:
        assert calibrated.satisfied_cases("def f(n)\n    return n\n", "f", [([1], 1)], 0.05, None) is None

    def test_the_clock_is_sized_from_the_defective_program_not_from_a_constant(self) -> None:
        slow = "def f(n):\n    total = 0\n    for i in range(200000):\n        total += i\n    return total\n"
        fast = "def f(n):\n    return n\n"
        cases = [([1], 1)]
        assert calibrated.clock_for(slow, "f", cases) > calibrated.clock_for(fast, "f", cases)


class TestTheSummary:
    def test_a_budget_is_never_reported_as_a_failure_of_the_mechanism(self) -> None:
        rows = [
            {"task": "a", "stage": "BUDGET_EXHAUSTED", "solved": False},
            {"task": "b", "stage": "CANDIDATE_FOUND", "solved": True, "verdicts": []},
        ]
        summary = calibrated.summarise(rows)
        assert summary["solved"] == ["b"]
        assert summary["budget_exhausted"] == ["a"]
        assert "a" in summary["not_solved"]


class TestRunningOut:
    def test_judging_a_whole_small_space_is_not_a_budget_failure(self) -> None:
        assert calibrated.exhaustion_stage(8310, 8310, 12000) == "SPACE_EXHAUSTED"

    def test_stopping_before_the_space_ends_is_a_budget_failure(self) -> None:
        assert calibrated.exhaustion_stage(12000, 17395, 12000) == "BUDGET_EXHAUSTED"

    def test_stopping_early_for_the_clock_is_also_a_budget_failure(self) -> None:
        assert calibrated.exhaustion_stage(400, 17395, 12000) == "BUDGET_EXHAUSTED"


class TestOneCandidateCannotCostTheOthersTheirVerdict:
    def test_a_case_that_runs_out_of_time_is_a_rejected_case_not_an_unknown(self) -> None:
        flags = calibrated.satisfied_cases("def f(n):\n    while True:\n        pass\n",
                                          "f", [([1], 1), ([2], 2)], 0.05, None)
        assert flags == [False, False]

    def test_bisection_charges_a_killed_child_to_the_candidate_that_killed_it(self, monkeypatch) -> None:
        def fake(sources, core, budget_s):
            if any("KILLER" in source for source in sources):
                return None
            return [[True] if "GOOD" in source else [False] for source in sources]

        monkeypatch.setattr(calibrated, "evaluate_chunk", fake)
        core = {"function": "f", "cases": [([4], 2)], "clock": 0.05, "normalisation": None}
        graded = calibrated.judge(["GOOD", "GOOD", "KILLER", "BAD"], core,
                                  budget_s=1.0, per_candidate=0.01)
        assert graded == [[True], [True], None, [False]]

    def test_a_candidate_that_takes_its_judge_down_gets_no_verdict(self, monkeypatch) -> None:
        monkeypatch.setattr(calibrated, "evaluate_chunk", lambda *a, **k: None)
        core = {"function": "f", "cases": [([1], 1)], "clock": 0.05, "normalisation": None}
        assert calibrated.judge(["KILLER"], core, budget_s=1.0) == [None]

    def test_the_first_chunk_is_priced_by_the_corpus_clock(self) -> None:
        assert calibrated.chunk_budget(None, 50, 0.5) > calibrated.chunk_budget(None, 50, 0.01)

    def test_once_the_price_is_measured_the_budget_follows_the_measurement(self) -> None:
        assert calibrated.chunk_budget(0.001, 50, 2.0) == 0.35
        assert calibrated.chunk_budget(0.5, 50, 0.05) > calibrated.chunk_budget(0.005, 50, 0.05)


class TestTheInstrumentIsCertifiedBeforeItIsBelieved:
    def test_a_judge_that_cannot_see_the_corpus_own_answer_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "python_programs").mkdir()
            (root / "correct_python_programs").mkdir()
            (root / "python_programs" / "a.py").write_text("def f(n):\n    return n + 1\n")
            (root / "correct_python_programs" / "a.py").write_text("def f(n):\n    return n\n")
            calibration = calibrated.self_calibration(root, "a", "f", [([1], 1)], [0.05], None)
            assert calibration["corrected_passes"] is True
            assert calibration["defective_is_rejected"] is True

    def test_a_judge_that_accepts_the_bug_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "python_programs").mkdir()
            (root / "correct_python_programs").mkdir()
            (root / "python_programs" / "a.py").write_text("def f(n):\n    return n\n")
            (root / "correct_python_programs" / "a.py").write_text("def f(n):\n    return n\n")
            calibration = calibrated.self_calibration(root, "a", "f", [([1], 1)], [0.05], None)
            assert calibration["defective_is_rejected"] is False


class TestTheClockIsPerCase:
    def test_one_slow_case_does_not_make_every_case_expensive(self) -> None:
        source = ("def f(n):\n    total = 0\n    if n == 0:\n        return 0\n"
                  "    for i in range(200000):\n        total += i\n    return total\n")
        clocks = calibrated.clocks_for(source, "f", [([0], 0), ([1], 1)])
        assert clocks[0] < clocks[1]


class TestTheTestFileAlsoSaysWhatEqualMeans:
    def test_a_tolerance_taken_from_the_input_is_read_from_the_test_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "python_testcases").mkdir()
            (root / "python_testcases" / "test_sqrt.py").write_text(
                "def test_sqrt(input_data, expected):\n"
                "    assert sqrt(*input_data) == pytest.approx(expected, abs=input_data[-1])\n")
            assert calibrated.test_file_normalisation(root, "sqrt") == "approx_last_argument"

    def test_an_answer_inside_the_tolerance_the_test_gives_is_accepted(self) -> None:
        source = "def f(x, epsilon):\n    return 1.4166\n"
        assert calibrated.satisfied_cases(source, "f", [([2, 0.01], 1.4166666)], 0.05,
                                          "approx_last_argument") == [True]

    def test_an_answer_outside_it_is_rejected(self) -> None:
        source = "def f(x, epsilon):\n    return 1.5\n"
        assert calibrated.satisfied_cases(source, "f", [([2, 0.01], 1.4166666)], 0.05,
                                          "approx_last_argument") == [False]
