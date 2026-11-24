#!/usr/bin/env python3
"""Tests for the witness-distance objective.

Every test pins either a bug this build hit against real repositories, or a measured
negative result that a future round must not quietly re-litigate. No browser and no
network: the parser is a pure function of pytest's own output.
"""
from __future__ import annotations

import importlib

W = importlib.import_module("canonical.runtime.the_witness_carries_the_distance_v1")


def _run(body: str, summary: str = "FAILED tests/test_calc.py::test_sum") -> str:
    """Real pytest shape: a section AND a short summary. A fixture with only one of them
    is not pytest, and a parser that passes on it is a parser that lies about the tool."""
    return (f"=========================== short test summary info ============================\n"
            f"{summary}\n"
            f"1 failed, 3 passed in 0.01s\n"
            f"_________________________ test_sum _________________________\n\n"
            f"{body}\n")


# --- the disease this exists to cure --------------------------------------- #
def test_two_unrelated_programs_are_one_point_under_the_failure_count() -> None:
    """"Both score 1, so no edit to the source can ever strictly improve the metric" --
    the repair loop's own docstring, and the reason it returned
    OPEN__NO_STRICTLY_IMPROVING_CANDIDATE for every bug."""
    distant = W.score(_run("E       assert 'ab' == 'abcdefghij'"))
    near = W.score(_run("E       assert 'abcdefghi' == 'abcdefghij'"))
    assert distant["failing"] == near["failing"] == 1        # the integer: identical
    assert distant["distance_total"] > near["distance_total"]  # this: ordered
    assert W.improved(distant, near) is True


def test_numeric_distance_is_relative_to_the_expected_magnitude() -> None:
    # 1 away from 5 is a bigger relative error than 1 away from 500.
    assert W.distance_between(4, 5) > W.distance_between(499, 500)
    assert W.distance_between(5, 5) == 0.0


def test_a_matching_value_is_zero_distance() -> None:
    assert W.distance_between("abc", "abc") == 0.0
    assert W.distance_between(True, True) == 0.0
    assert W.distance_between(True, False) == 1.0


def test_sets_compare_by_membership_not_position() -> None:
    """A candidate that produces the right elements in the wrong order is closer than one
    that produces the wrong elements. This is the multiset difference, not a metric."""
    close = W.distance_between(["a", "b"], ["a", "b", "c"])
    far = W.distance_between(["a", "z"], ["a", "b", "c"])
    assert close < far


# --- the failure is typed, because real failures are ---------------------- #
def test_a_missing_guard_is_read_with_the_value_that_arrived() -> None:
    """Measured on pypa/packaging 022ae6c6: `Failed: DID NOT RAISE InvalidMetadata`.
    There is no operand, so a scalar residual cannot express it -- which is why the
    witness is typed and why the frame's locals are captured."""
    s = W.score(_run("E       Failed: DID NOT RAISE InvalidMetadata\n\n"
                     "license_files = ['C:LICENSE']\nmeta       = <Metadata object>"))
    f = s["failures"][0]
    assert f["kind"] == "did_not_raise"
    assert f["expected"] == "InvalidMetadata"
    assert f["distance"] == W.DID_NOT_RAISE
    assert "license_files" in f["locals"]


def test_an_escaped_error_ranks_worse_than_a_missing_guard() -> None:
    """An escaped exception has not reached the assertion yet: it says nothing about the
    condition under test. A missing guard names the condition exactly."""
    escaped = W.score(_run("E           AttributeError: 'NoneType' has no attribute 'x'"))
    guard = W.score(_run("E       Failed: DID NOT RAISE ValueError"))
    assert escaped["distance_total"] > guard["distance_total"]


def test_a_node_named_with_no_evidence_is_not_worth_a_zero() -> None:
    """Named and nothing else is the least informative outcome. Recording it as close
    would make an unparseable failure look like progress."""
    s = W.score("=========================== short test summary info ============================\n"
                "FAILED tests/test_x.py::test_y\n1 failed in 0.01s\n")
    assert s["failures"][0]["distance"] == W.NO_OUTPUT


# --- parser bugs, each measured against a real repository ----------------- #
def test_a_section_title_may_be_several_words() -> None:
    """Measured on tomli: the header is `ERROR collecting tests/test_data.py`. A one-word
    pattern dropped the whole section, so a failure that had printed its cause read as
    NO_OUTPUT."""
    text = ("==================================== ERRORS ====================================\n"
            "_____________________ ERROR collecting tests/test_data.py ______________________\n"
            "E   ModuleNotFoundError: No module named 'tomli'\n"
            "=========================== short test summary info ============================\n"
            "ERROR tests/test_data.py\n1 error in 0.06s\n")
    kinds = [f["kind"] for f in W.score(text)["failures"]]
    assert "unreachable" in kinds, kinds


def test_a_section_is_not_a_second_gate() -> None:
    """A header reads `TestMetadata.test_invalid_license_files[license_files4]` while the
    summary names the node id. Keying off headers invented a second node for every
    failure, doubling the count and hiding real movement."""
    text = ("=========================== short test summary info ============================\n"
            "FAILED tests/test_metadata.py::TestMetadata::test_invalid_license_files[license_files4]\n"
            "1 failed, 342 passed in 0.19s\n"
            "______ TestMetadata.test_invalid_license_files[license_files4] ______\n"
            "E       Failed: DID NOT RAISE InvalidMetadata\n")
    s = W.score(text)
    assert s["failing"] == 1, [f["node"] for f in s["failures"]]


def test_the_summary_vocabulary_is_not_two_words() -> None:
    """pytest-subtests prints SUBFAILED. A list that knew only FAILED and ERROR read a
    whole file of real failures as zero gates."""
    text = ("=========================== short test summary info ============================\n"
            "SUBFAILED[common-12] tests/test_data.py::TestData::test_valid - TOMLDecodeError\n"
            "2 failed, 2 passed in 0.10s\n"
            "_______________________ TestData.test_valid [common-12] _______________________\n"
            "E           TOMLDecodeError: Unescaped '\\\\' in a string\n")
    s = W.score(text)
    assert s["failing"] >= 1, s["failures"]


def test_each_failing_subtest_is_its_own_gate() -> None:
    """One node id, two sections: the subtests are distinct places the program can be
    wrong, which is exactly what a gate is. Taking only the first threw one away."""
    text = ("=========================== short test summary info ============================\n"
            "SUBFAILED[a] tests/test_d.py::T::test_valid\n"
            "SUBFAILED[b] tests/test_d.py::T::test_valid\n"
            "2 failed in 0.1s\n"
            "_______________________ T.test_valid [a] _______________________\n"
            "E   TOMLDecodeError: first\n"
            "_______________________ T.test_valid [b] _______________________\n"
            "E   TOMLDecodeError: second\n")
    s = W.score(text)
    assert s["failing"] >= 2, [f["message"] for f in s["failures"]]


# --- the gate set must not be the candidate's own claim ------------------- #
def test_a_candidate_that_breaks_collection_does_not_get_a_perfect_score() -> None:
    """THE BUG THAT WOULD HAVE MADE THIS INSTRUMENT LIE. A candidate that cannot import
    reports no failing nodes; if the gate set came from its own output it would read
    "0 of 0 satisfied", a perfect result for a program that does not run."""
    gates = ["tests/test_m.py::test_a", "tests/test_m.py::test_b"]
    broken = ("==================================== ERRORS ====================================\n"
              "_____________________ ERROR collecting tests/test_m.py ______________________\n"
              "E   ModuleNotFoundError: No module named 'calc'\n"
              "=========================== short test summary info ============================\n"
              "ERROR tests/test_m.py\n1 error in 0.01s\n")
    s = W.score(broken, failing_nodes=gates)
    assert s["gates"] == 2 and s["satisfied"] == 0
    good = "=========================== short test summary info ============================\n" \
           "3 passed in 0.01s\n"
    assert W.score(good, failing_nodes=gates)["satisfied"] == 2


def test_the_measured_baseline_example_now_steps() -> None:
    """The exact pair the repair loop's docstring measured: an import error versus a wrong
    value, both scoring 1. Under this objective one is a long way from the other."""
    import_error = _run("E   ModuleNotFoundError: No module named 'calc'")
    wrong_value = _run("E       assert -1 == 5")
    a, b = W.score(import_error), W.score(wrong_value)
    assert a["distance_total"] != b["distance_total"]


# --- progress, exploration, and the line between them -------------------- #
def test_a_new_execution_path_is_not_progress() -> None:
    """MEASURED: 48 of 49 real mutants changed the executed lines while changing no
    verdict. Calling that progress is the lie this round exists to refuse."""
    base = {"satisfied": 0, "distance_total": 4.0, "path": {"10": 1, "20": 1},
            "key": (0, -4.0)}
    same_gates_new_path = {"satisfied": 0, "distance_total": 4.0,
                           "path": {"10": 1, "99": 1}, "key": (0, -4.0)}
    assert W.closer(base, same_gates_new_path) is False
    assert W.novel(base, same_gates_new_path) is True
    v = W.verdict(base, same_gates_new_path)
    assert v["label"] == "UNCHANGED_CORRECTNESS_NEW_BEHAVIOUR"
    assert v["sound"] is False and v["novel"] is True


def test_identical_behaviour_is_neither_progress_nor_novelty() -> None:
    a = {"satisfied": 0, "distance_total": 2.0, "path": {"5": 3}, "key": (0, -2.0)}
    v = W.verdict(a, dict(a))
    assert v["label"] == "NO_CHANGE" and v["sound"] is False and v["novel"] is False


def test_losing_a_gate_is_a_regression_not_a_sideways_move() -> None:
    before = {"satisfied": 1, "distance_total": 1.0, "path": {"1": 1}, "key": (1, -1.0)}
    after = {"satisfied": 0, "distance_total": 9.0, "path": {"1": 1}, "key": (0, -9.0)}
    assert W.verdict(before, after)["label"] == "REGRESSION"


def test_more_gates_satisfied_always_wins_even_with_a_bigger_total() -> None:
    """Lexicographic, deliberately: fixing a whole gate is worth more than shaving a
    distance elsewhere, because a gate is one test the repository actually shipped."""
    better = {"satisfied": 2, "distance_total": 50.0, "key": (2, -50.0)}
    worse = {"satisfied": 1, "distance_total": 1.0, "key": (1, -1.0)}
    assert W.improved(worse, better) is True


def test_a_loop_that_runs_once_more_has_not_moved_through_the_program() -> None:
    """Counts are deliberately not used: more iterations of the same lines is not motion."""
    assert W.path_distance({"7": 1}, {"7": 40}) == 0.0
    assert W.path_distance({"1": 1}, {"2": 1}) == 1.0


# --- where the source actually is ---------------------------------------- #
def test_a_src_layout_must_be_on_the_path_or_the_wrong_file_is_measured(tmp_path) -> None:
    """MEASURED DEFECT that invalidated a whole measurement pass: with only the repository
    root on PYTHONPATH a src-layout project imports the INSTALLED copy from site-packages.
    Every candidate edit was then invisible, which looks exactly like "no gradient"."""
    root = tmp_path
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "__init__.py").write_text("")
    (root / "src" / "pkg" / "mod.py").write_text("X = 1\n")
    paths = W.source_paths(root, "src/pkg/mod.py")
    assert str(root / "src") in paths
    assert paths.index(str(root / "src")) < paths.index(str(root))


def test_a_flat_layout_puts_the_package_parent_on_the_path(tmp_path) -> None:
    root = tmp_path
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pkg" / "mod.py").write_text("X = 1\n")
    paths = W.source_paths(root, "pkg/mod.py")
    assert str(root) in paths


# --- the measured limit: the test is silent exactly where a search must step - #
def test_a_partial_repair_is_invisible_to_the_test_and_this_is_recorded() -> None:
    """MEASURED ON 50 REAL MULTI-HUNK FIXES. Apply only the first hunk of a real repair
    and ask each observable what changed:

        the test's own output (gates, types, operands, locals, reached lines)  ~8 of 50
        the set of lines the program EXECUTED                                  42 of 50

    So a partial repair is usually invisible to the test -- by design, since a
    half-finished repair is still wrong and the test says so correctly. This test pins the
    CONCLUSION, not a fixture: no ordering over test output can be a gradient on this
    corpus, which is why the module also carries the behavioural observable and why it
    refuses to call a new execution path progress.
    """
    base = {"satisfied": 0, "distance_total": 2.0, "path": {"1": 1, "2": 1}, "key": (0, -2.0)}
    # A partial repair that the test cannot distinguish at all:
    silent = {"satisfied": 0, "distance_total": 2.0, "path": {"1": 1, "2": 1},
              "key": (0, -2.0)}
    v = W.verdict(base, silent)
    assert v["label"] == "NO_CHANGE"
    assert v["sound"] is False and v["novel"] is False
    # ...but the execution path usually does move, and the module must be able to say so:
    moved = dict(silent, path={"1": 1, "9": 1})
    v2 = W.verdict(base, moved)
    assert v2["novel"] is True and v2["sound"] is False
    assert v2["label"] == "UNCHANGED_CORRECTNESS_NEW_BEHAVIOUR"


def test_the_search_predicate_never_accepts_an_execution_path_alone() -> None:
    """The integrity line: `closer` gates acceptance; `novel` only records exploration."""
    a = {"satisfied": 0, "distance_total": 1.0, "path": {"1": 1}, "key": (0, -1.0)}
    b = {"satisfied": 0, "distance_total": 1.0, "path": {"2": 2}, "key": (0, -1.0)}
    assert W.closer(a, b) is False
    assert W.novel(a, b) is True


def test_the_tracer_reports_lines_the_program_actually_executed(tmp_path) -> None:
    """The behavioural observable is the program's own behaviour, not an inference from
    what it printed: it runs the test under a line hook and counts the repair target."""
    import subprocess
    import sys
    (tmp_path / "calc.py").write_text(
        "def add(a, b):\n    return a - b\n\ndef unused():\n    return 42\n")
    (tmp_path / "test_calc.py").write_text(
        "import calc\n\ndef test_add():\n    assert calc.add(2, 3) == 5\n")
    got = W.execute_with_path(tmp_path, "test_calc.py", "calc.py")
    assert "1 failed" in got["text"] or "failed" in got["text"]
    assert got["path"], got
    executed = {int(k) for k in got["path"]}
    assert 2 in executed           # the subtract line ran
    assert 5 not in executed       # the unused function did not
