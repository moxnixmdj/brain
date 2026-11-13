#!/usr/bin/env python3
"""What a verbose run of a project's tests says: how each test ended, under which names a test is
known, whether the tests tell the broken program from the fixed one, and whether a candidate does
what the fix does."""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import tests_as_the_judge_v1 as judge  # noqa: E402

# What Django's runner printed here (Python 3.11) for django__django-10880 with the expert's fix, cut short.
NEW = """Testing against Django installed in '/tmp/dj/w1/django'
Importing application aggregation
Operations to perform:
  Synchronize unmigrated apps: aggregation, auth, contenttypes, messages, sessions, staticfiles
  Apply all migrations: admin, sites
Running migrations:
  Applying admin.0001_initial... OK
  Applying sites.0002_alter_domain_unique... OK
System check identified no issues (0 silenced).
test_count_distinct_expression (aggregation.tests.AggregateTestCase.test_count_distinct_expression) ... ok
test_count_star (aggregation.tests.AggregateTestCase.test_count_star) ... ok
test_dates_with_aggregation (aggregation.tests.AggregateTestCase.test_dates_with_aggregation)
.dates() returns a distinct set of dates when applied to a ... ok
test_ticket11881 (aggregation.tests.AggregateTestCase.test_ticket11881)
Subquery annotations are excluded from the GROUP BY if they are ... FAIL
test_backend_only (aggregation.tests.AggregateTestCase.test_backend_only) ... skipped 'Database has feature(s) x'
test_broken (aggregation.tests.AggregateTestCase.test_broken) ... ERROR

----------------------------------------------------------------------
Ran 6 tests in 0.126s

FAILED (failures=1, errors=1, skipped=1)
"""

# The same tests as Python before 3.11 names them, and before 3.9 for a docstring that opens with an empty line.
OLD = """test_count_distinct_expression (aggregation.tests.AggregateTestCase) ... ok
test_count_star (aggregation.tests.AggregateTestCase) ... ok
test_dates_with_aggregation (aggregation.tests.AggregateTestCase) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.1s

OK
"""


# --------------------------------------------------------------------------- #
# names
# --------------------------------------------------------------------------- #
def test_the_name_python_3_11_prints_becomes_the_older_one():
    assert judge.normal("test_x (pkg.mod.Class.test_x)") == "test_x (pkg.mod.Class)"
    assert judge.normal("  test_x (pkg.mod.Class.test_x)  ") == "test_x (pkg.mod.Class)"


def test_the_older_name_and_a_docstring_line_stay_as_they_are():
    assert judge.normal("test_x (pkg.mod.Class)") == "test_x (pkg.mod.Class)"
    assert judge.normal(".dates() returns a distinct set of dates when applied to a") == ".dates() returns a distinct set of dates when applied to a"
    assert judge.normal("A docstring that ends (like.a.name)") == "A docstring that ends (like.a.name)"


def test_a_class_whose_last_part_is_not_the_method_is_left_alone():
    assert judge.normal("test_x (pkg.mod.test_y)") == "test_x (pkg.mod.test_y)"


# --------------------------------------------------------------------------- #
# how each test ended
# --------------------------------------------------------------------------- #
def test_each_test_is_read_with_how_it_ended():
    found = judge.statuses(NEW)
    assert found["test_count_star (aggregation.tests.AggregateTestCase)"] == judge.PASSED
    assert found["test_backend_only (aggregation.tests.AggregateTestCase)"] == judge.SKIPPED
    assert found["test_broken (aggregation.tests.AggregateTestCase)"] == judge.ERROR
    assert found["test_ticket11881 (aggregation.tests.AggregateTestCase)"] == judge.FAILED


def test_the_lines_of_the_migrations_are_not_tests():
    assert len(judge.statuses(NEW)) == 8                           # six tests, two of them known by a docstring line as well
    assert not any("Applying" in name for name in judge.statuses(NEW))


def test_a_test_with_a_docstring_is_known_by_its_name_and_by_the_docstrings_line():
    found = judge.statuses(NEW)
    assert found["test_dates_with_aggregation (aggregation.tests.AggregateTestCase)"] == judge.PASSED
    assert found[".dates() returns a distinct set of dates when applied to a"] == judge.PASSED
    assert found["Subquery annotations are excluded from the GROUP BY if they are"] == judge.FAILED


def test_the_older_run_and_the_newer_one_give_the_same_names():
    old, new = judge.statuses(OLD), judge.statuses(NEW)
    assert set(old) <= set(new)
    assert all(new[name] == judge.PASSED for name in old)


def test_two_tests_that_share_a_docstring_line_pass_under_it_only_when_both_pass():
    printed = ("test_a (m.T.test_a)\nThe same words ... ok\n"
               "test_b (m.T.test_b)\nThe same words ... FAIL\n"
               "test_c (m.T.test_c)\nThe same words ... ok\n")
    found = judge.statuses(printed)
    assert found["The same words"] == judge.FAILED
    assert (found["test_a (m.T)"], found["test_b (m.T)"], found["test_c (m.T)"]) == (judge.PASSED, judge.FAILED, judge.PASSED)


def test_a_skipped_test_that_shares_a_docstring_line_keeps_the_line_from_passing():
    printed = "test_a (m.T.test_a)\nThe same words ... ok\ntest_b (m.T.test_b)\nThe same words ... skipped 'no'\n"
    assert judge.statuses(printed)["The same words"] == judge.SKIPPED
    printed = "test_b (m.T.test_b)\nThe same words ... skipped 'no'\ntest_a (m.T.test_a)\nThe same words ... ok\n"
    assert judge.statuses(printed)["The same words"] == judge.SKIPPED


def test_a_docstring_line_never_takes_the_place_of_a_tests_own_name():
    printed = "test_a (m.T.test_a) ... FAIL\ntest_b (m.T.test_b)\ntest_a (m.T) ... ok\n"
    found = judge.statuses(printed)
    assert found["test_a (m.T)"] == judge.PASSED                   # the second line pair is a test named by a name-like line: read as a name
    printed = "test_b (m.T.test_b)\nwords of b ... ok\ntest_a (m.T.test_a) ... FAIL\n"
    found = judge.statuses(printed)
    assert found == {"test_b (m.T)": judge.PASSED, "words of b": judge.PASSED, "test_a (m.T)": judge.FAILED}


def test_a_name_line_belongs_only_to_the_line_right_under_it():
    printed = "test_b (m.T.test_b)\nsomething the program printed\nwords ... ok\n"
    found = judge.statuses(printed)
    assert found == {"words": judge.PASSED}
    printed = "test_b (m.T.test_b)\nwords of b ... ok\nother words ... FAIL\n"
    assert judge.statuses(printed) == {"test_b (m.T)": judge.PASSED, "words of b": judge.PASSED, "other words": judge.FAILED}
    assert judge.identifiers(printed) == {"test_b (m.T)": ["m.T.test_b"], "words of b": ["m.T.test_b"]}


def test_a_line_that_is_a_test_of_its_own_keeps_its_ending_when_another_test_carries_it_as_its_docstring():
    printed = "words ... FAIL\ntest_b (m.T.test_b)\nwords ... ok\n"
    assert judge.statuses(printed) == {"words": judge.FAILED, "test_b (m.T)": judge.PASSED}


def test_a_test_that_prints_something_of_its_own_is_read_from_the_line_that_ends_it():
    printed = "test_loud (m.T.test_loud) ... some output of the test\nmore of it\nok\ntest_next (m.T.test_next) ... ok\n"
    found = judge.statuses(printed)
    assert found == {"test_loud (m.T)": judge.PASSED, "test_next (m.T)": judge.PASSED}
    printed = "test_loud (m.T.test_loud) ... some output\nFAIL\n"
    assert judge.statuses(printed) == {"test_loud (m.T)": judge.FAILED}
    printed = "test_loud (m.T.test_loud) ... some output\nERROR\n"
    assert judge.statuses(printed) == {"test_loud (m.T)": judge.ERROR}


def test_a_loud_test_with_a_docstring_is_known_by_both():
    printed = "test_loud (m.T.test_loud)\nWhat it does ... noise\nok\n"
    assert judge.statuses(printed) == {"test_loud (m.T)": judge.PASSED, "What it does": judge.PASSED}


def test_a_bare_ok_with_no_test_waiting_is_nothing():
    assert judge.statuses("ok\nFAIL\ntest_a (m.T.test_a) ... ok\nok\n") == {"test_a (m.T)": judge.PASSED}


def test_an_expected_failure_does_not_pass_and_an_unexpected_success_fails():
    printed = "test_a (m.T.test_a) ... expected failure\ntest_b (m.T.test_b) ... unexpected success\n"
    assert judge.statuses(printed) == {"test_a (m.T)": judge.SKIPPED, "test_b (m.T)": judge.FAILED}


def test_the_three_ways_a_pass_is_printed():
    printed = "test_a (m.T.test_a) ... ok\ntest_b (m.T.test_b) ... OK\ntest_c (m.T.test_c) ...  OK\n"
    assert set(judge.statuses(printed).values()) == {judge.PASSED} and len(judge.statuses(printed)) == 3


def test_a_name_with_dots_of_its_own_keeps_them():
    printed = "test_a (m.T.test_a) [<object object at 0x1>] (value=' ... ') ... ok\n"
    assert judge.statuses(printed) == {"test_a (m.T.test_a) [<object object at 0x1>] (value=' ... ')": judge.PASSED}


def test_a_test_that_printed_no_line_is_not_there():
    found = judge.statuses("ERROR: setUpClass (m.T)\n")
    assert found == {} and judge.passing(found, ["test_a (m.T)"]) == []


# --------------------------------------------------------------------------- #
# the run
# --------------------------------------------------------------------------- #
def test_how_many_tests_ran_and_whether_the_run_got_to_its_end():
    assert judge.ran(NEW) == 6 and judge.finished(NEW)
    assert judge.ran(OLD) == 3 and judge.finished(OLD)
    assert judge.ran("Ran 1 test in 0.001s\n\nOK\n") == 1


def test_a_run_that_crashed_before_its_summary_did_not_finish():
    crashed = "Traceback (most recent call last):\n  File \"tests/runtests.py\", line 1\nImportError: cannot import name 'x'\n"
    assert judge.ran(crashed) is None and not judge.finished(crashed)
    assert not judge.finished("Ran 3 tests in 0.1s\n")             # stopped between the count and the verdict
    assert not judge.finished("OK\nRan 3 tests in 0.1s\n")         # a verdict before the count is not this run's


def test_the_last_count_is_the_runs():
    assert judge.ran("Ran 2 tests in 0.1s\n\nOK\nRan 5 tests in 0.2s\n\nFAILED (failures=1)\n") == 5


# --------------------------------------------------------------------------- #
# the three questions
# --------------------------------------------------------------------------- #
FIRST = ["test_count_distinct_expression (aggregation.tests.AggregateTestCase)"]
KEEP = ["test_count_star (aggregation.tests.AggregateTestCase)", "test_dates_with_aggregation (aggregation.tests.AggregateTestCase)"]


def _found(**how: str) -> dict[str, str]:
    names = {"first": FIRST[0], "star": KEEP[0], "dates": KEEP[1]}
    return {names[key]: value for key, value in how.items()}


def test_the_names_that_pass_are_given_back_as_they_were_given():
    found = judge.statuses(NEW)
    asked = ["test_count_star (aggregation.tests.AggregateTestCase.test_count_star)", "test_broken (aggregation.tests.AggregateTestCase)", "not there"]
    assert judge.passing(found, asked) == [asked[0]]


def test_the_tests_tell_the_broken_program_from_the_fixed_one():
    assert judge.tells_apart(_found(first=judge.FAILED), _found(first=judge.PASSED), FIRST)
    assert judge.tells_apart(_found(first=judge.ERROR), _found(first=judge.PASSED), FIRST)
    assert judge.tells_apart({}, _found(first=judge.PASSED), FIRST)


def test_they_do_not_when_the_broken_program_passes_or_the_fixed_one_fails_or_nothing_is_named():
    assert not judge.tells_apart(_found(first=judge.PASSED), _found(first=judge.PASSED), FIRST)
    assert not judge.tells_apart(_found(first=judge.FAILED), _found(first=judge.FAILED), FIRST)
    assert not judge.tells_apart(_found(first=judge.FAILED), _found(first=judge.SKIPPED), FIRST)
    assert not judge.tells_apart(_found(first=judge.FAILED), _found(first=judge.PASSED), [])


def test_with_two_tests_one_failing_without_the_fix_is_enough_and_both_must_pass_with_it():
    two = FIRST + [KEEP[0]]
    assert judge.tells_apart(_found(first=judge.FAILED, star=judge.PASSED), _found(first=judge.PASSED, star=judge.PASSED), two)
    assert not judge.tells_apart(_found(first=judge.FAILED, star=judge.PASSED), _found(first=judge.PASSED, star=judge.FAILED), two)


def test_the_tests_that_fail_here_even_with_the_fix_are_named():
    fixed = _found(first=judge.PASSED, star=judge.PASSED, dates=judge.FAILED)
    assert judge.left_out(fixed, KEEP) == [KEEP[1]]
    assert judge.left_out(_found(star=judge.PASSED, dates=judge.PASSED), KEEP) == []
    assert judge.left_out({}, KEEP) == KEEP


def test_a_candidate_resolves_when_everything_the_fix_passes_passes():
    fixed = _found(first=judge.PASSED, star=judge.PASSED, dates=judge.PASSED)
    assert judge.resolves(_found(first=judge.PASSED, star=judge.PASSED, dates=judge.PASSED), fixed, FIRST, KEEP)


def test_a_candidate_that_leaves_the_test_failing_does_not_resolve():
    fixed = _found(first=judge.PASSED, star=judge.PASSED, dates=judge.PASSED)
    assert not judge.resolves(_found(first=judge.FAILED, star=judge.PASSED, dates=judge.PASSED), fixed, FIRST, KEEP)
    assert not judge.resolves(_found(star=judge.PASSED, dates=judge.PASSED), fixed, FIRST, KEEP)


def test_a_candidate_that_breaks_a_test_that_should_keep_passing_does_not_resolve():
    fixed = _found(first=judge.PASSED, star=judge.PASSED, dates=judge.PASSED)
    assert not judge.resolves(_found(first=judge.PASSED, star=judge.PASSED, dates=judge.FAILED), fixed, FIRST, KEEP)
    assert not judge.resolves(_found(first=judge.PASSED, star=judge.ERROR, dates=judge.PASSED), fixed, FIRST, KEEP)
    assert not judge.resolves(_found(first=judge.PASSED, dates=judge.PASSED), fixed, FIRST, KEEP)


def test_a_test_that_fails_here_even_with_the_fix_is_not_held_against_the_candidate():
    fixed = _found(first=judge.PASSED, star=judge.PASSED, dates=judge.FAILED)
    assert judge.resolves(_found(first=judge.PASSED, star=judge.PASSED, dates=judge.FAILED), fixed, FIRST, KEEP)
    assert judge.resolves(_found(first=judge.PASSED, star=judge.PASSED), fixed, FIRST, KEEP)


def test_nothing_resolves_a_task_the_fix_itself_does_not_pass_here_or_that_names_no_test():
    everything = _found(first=judge.PASSED, star=judge.PASSED, dates=judge.PASSED)
    assert not judge.resolves(everything, _found(first=judge.FAILED, star=judge.PASSED, dates=judge.PASSED), FIRST, KEEP)
    assert not judge.resolves(everything, everything, [], KEEP)


def test_a_candidate_is_judged_by_names_in_either_form():
    older, newer = judge.statuses(OLD), judge.statuses(NEW)
    first = ["test_count_distinct_expression (aggregation.tests.AggregateTestCase.test_count_distinct_expression)"]
    assert judge.resolves(newer, older, first, [KEEP[1]])
    assert judge.resolves(older, newer, first, [KEEP[1]])
    assert judge.resolves(newer, newer, first, [".dates() returns a distinct set of dates when applied to a", KEEP[0]])


def test_a_docstring_line_the_run_with_the_fix_does_not_print_is_left_out():
    older, newer = judge.statuses(OLD), judge.statuses(NEW)
    line = ".dates() returns a distinct set of dates when applied to a"
    assert judge.left_out(older, [line]) == [line] and judge.left_out(newer, [line]) == []
    assert judge.resolves(newer, older, FIRST, [line])             # not held against the candidate: the fix does not show it passing
    assert not judge.resolves(older, newer, FIRST, [line])         # held against it: with the fix it passes, with the candidate it is not there


# --------------------------------------------------------------------------- #
# the labels that run just some tests
# --------------------------------------------------------------------------- #
def test_the_label_of_a_test_is_its_dotted_name():
    known = judge.identifiers(NEW)
    assert known["test_count_star (aggregation.tests.AggregateTestCase)"] == ["aggregation.tests.AggregateTestCase.test_count_star"]
    assert judge.identifiers(OLD)["test_count_star (aggregation.tests.AggregateTestCase)"] == ["aggregation.tests.AggregateTestCase.test_count_star"]


def test_a_docstring_line_gives_the_label_of_the_test_above_it():
    known = judge.identifiers(NEW)
    assert known[".dates() returns a distinct set of dates when applied to a"] == ["aggregation.tests.AggregateTestCase.test_dates_with_aggregation"]
    assert known["test_dates_with_aggregation (aggregation.tests.AggregateTestCase)"] == ["aggregation.tests.AggregateTestCase.test_dates_with_aggregation"]


def test_a_docstring_line_two_tests_share_gives_both_labels_once_each():
    printed = "test_a (m.T.test_a)\nThe same words ... ok\ntest_b (m.T.test_b)\nThe same words ... ok\ntest_a (m.T.test_a)\nThe same words ... ok\n"
    assert judge.identifiers(printed)["The same words"] == ["m.T.test_a", "m.T.test_b"]


def test_a_failed_or_skipped_test_has_a_label_too_and_a_line_that_is_no_test_has_none():
    known = judge.identifiers(NEW + "something ... ok\n")
    assert known["test_broken (aggregation.tests.AggregateTestCase)"] == ["aggregation.tests.AggregateTestCase.test_broken"]
    assert known["test_backend_only (aggregation.tests.AggregateTestCase)"] == ["aggregation.tests.AggregateTestCase.test_backend_only"]
    assert "something" not in known


@pytest.mark.parametrize("printed", ["", "\n\n", "no tests here\n"])
def test_nothing_printed_is_nothing_found(printed):
    assert judge.statuses(printed) == {} and judge.identifiers(printed) == {} and judge.ran(printed) is None and not judge.finished(printed)
