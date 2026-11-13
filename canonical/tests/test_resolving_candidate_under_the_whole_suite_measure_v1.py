#!/usr/bin/env python3
"""A candidate the task's own tests accept, under the project's whole suite: which tests count as
broken by it, which do not (this machine's, and the ones that fail one time in two), when nothing is
said, how the counts add up, the rule, and that the record in the tree adds up from its rows.

The project here is a small one made on the spot, with a stand-in for Django's `tests/runtests.py`
that takes the same arguments and, with no label, runs every test module: every run in these tests
is a real run of real tests."""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import tests_as_the_judge_v1 as judge  # noqa: E402
from canonical.tools import candidate_under_the_tasks_tests_measure_v1 as count  # noqa: E402
from canonical.tools import resolving_candidate_under_the_whole_suite_measure_v1 as whole  # noqa: E402

RECORD = ROOT / "canonical" / "verification" / "RESOLVING_CANDIDATE_UNDER_THE_WHOLE_SUITE_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json"
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not here")

STORE = '''HELPER = 'shop'


def label(name):
    return HELPER + ':' + name


class Store:
    def __init__(self):
        self.rows = {}

    def save(self, name, db):
        self.rows.setdefault('default', []).append(name)
        return db

    def load(self, db):
        return list(self.rows.get(db, []))
'''
FIXED = STORE.replace("self.rows.setdefault('default', []).append(name)", "self.rows.setdefault(db, []).append(name)")
BREAKS_THE_LABEL = FIXED.replace("return HELPER + ':' + name", "return HELPER + name")
TAKES_A_NAME_AWAY = FIXED.replace("HELPER = 'shop'", "PREFIX = 'shop'").replace("return HELPER + ':' + name", "return PREFIX + ':' + name")
RUNNER = '''import os
import sys
import unittest

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
given = sys.argv[1:]
assert given[:4] == ["--verbosity", "2", "--settings=test_sqlite", "--parallel"] and given[4].isdigit(), given
loader = unittest.defaultTestLoader
if given[5:]:
    suite = unittest.TestSuite(loader.discover(os.path.join(here, name.split(".")[0]), pattern="tests.py", top_level_dir=here) for name in given[5:])
else:
    suite = unittest.TestSuite(loader.discover(os.path.join(here, name), pattern="tests.py", top_level_dir=here)
                               for name in sorted(os.listdir(here)) if os.path.isdir(os.path.join(here, name)) and not name.startswith("_"))
outcome = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
sys.exit(0 if outcome.wasSuccessful() else 1)
'''
STORE_TESTS = '''import unittest

from shop.store import Store


class StoreTests(unittest.TestCase):
    def test_load_of_nothing(self):
        self.assertEqual(Store().load('default'), [])
'''
MORE_STORE_TESTS = STORE_TESTS + '''
    def test_save_writes_to_the_database_given(self):
        store = Store()
        store.save('a', 'other')
        self.assertEqual(store.load('other'), ['a'])
'''
LABEL_TESTS = '''import unittest

from shop.store import HELPER, label


class LabelTests(unittest.TestCase):
    def test_label(self):
        """
        A label holds the shop and the name.
        """
        self.assertEqual(label('a'), HELPER + ':a')

    def test_nothing_much(self):
        self.assertTrue(HELPER)
'''
MACHINE_TESTS = '''import unittest


class MachineTests(unittest.TestCase):
    def test_fails_on_this_machine(self):
        self.assertEqual(1, 2)
'''
ONCE_TESTS = '''import pathlib
import unittest


class OnceTests(unittest.TestCase):
    def test_fails_the_first_time(self):
        seen = pathlib.Path(__file__).parent / 'seen'
        first = not seen.exists()
        seen.write_text('')
        self.assertFalse(first)
'''
TREE = {
    "shop/__init__.py": "",
    "shop/store.py": STORE,
    "tests/runtests.py": RUNNER,
    "tests/store_tests/__init__.py": "",
    "tests/store_tests/tests.py": STORE_TESTS,
    "tests/label_tests/__init__.py": "",
    "tests/label_tests/tests.py": LABEL_TESTS,
    "tests/machine_tests/__init__.py": "",
    "tests/machine_tests/tests.py": MACHINE_TESTS,
}
FIRST = ["test_save_writes_to_the_database_given (store_tests.tests.StoreTests)"]
LABEL = "test_label (label_tests.tests.LabelTests)"
MUCH = "test_nothing_much (label_tests.tests.LabelTests)"
MACHINE = "test_fails_on_this_machine (machine_tests.tests.MachineTests)"
ONCE = "test_fails_the_first_time (once_tests.tests.OnceTests)"


def _git(directory, *args):
    done = subprocess.run(["git", "-C", str(directory), "-c", "user.name=t", "-c", "user.email=t@example.org", *args], capture_output=True, text=True, check=True)
    return done.stdout


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    """A project at the commit a task starts from, with the task's test patch and the expert's fix as diffs."""
    directory = tmp_path_factory.mktemp("trees") / "django__django.git"
    directory.mkdir()
    _git(directory, "init", "-q")
    for path, source in TREE.items():
        (directory / path).parent.mkdir(parents=True, exist_ok=True)
        (directory / path).write_text(source)
    _git(directory, "add", "-A")
    _git(directory, "commit", "-q", "-m", "as the task starts")
    commit = _git(directory, "rev-parse", "HEAD").strip()
    (directory / "tests" / "store_tests" / "tests.py").write_text(MORE_STORE_TESTS)
    test_patch = _git(directory, "diff")
    _git(directory, "commit", "-q", "-a", "-m", "the task's tests")
    (directory / "shop" / "store.py").write_text(FIXED)
    fix = _git(directory, "diff")
    _git(directory, "checkout", "-q", "--", ".")
    return {"clone": directory, "commit": commit, "test_patch": test_patch, "fix": fix}


@pytest.fixture()
def tree(project, tmp_path):
    place = tmp_path / "tree"
    count.at_commit(project["clone"], place, project["commit"])
    return place


def under(project, tree, text, **more):
    return whole.of_candidate(tree, project["test_patch"], project["fix"], "shop/store.py", text, FIRST, **more)


# --------------------------------------------------------------------------- #
# reading two runs against each other
# --------------------------------------------------------------------------- #
FOUND = {"test_a (m.T)": judge.PASSED, "test_b (m.T)": judge.FAILED, "test_c (pkg.n.U)": judge.ERROR, "test_d (m.T)": judge.SKIPPED,
         "What b does": judge.FAILED, "test_views (unittest.loader._FailedTest)": judge.ERROR}


def test_the_tests_that_did_not_pass_are_the_failed_and_the_errors_by_name():
    assert whole.not_passing(FOUND) == ["test_b (m.T)", "test_c (pkg.n.U)", "test_views (unittest.loader._FailedTest)"]


def test_the_modules_to_run_again_are_those_of_the_tests_that_did_not_pass_and_those_that_did_not_load():
    printed = "ERROR: test_views (unittest.loader._FailedTest)\nImportError: Failed to import test module: admin_docs.test_views\nTraceback ...\n"
    assert whole.modules_again(FOUND, printed) == ["admin_docs.test_views", "m", "pkg.n"]
    assert whole.modules_again(FOUND, "") == ["m", "pkg.n"]                               # unittest's own name for a module that did not load is no module to run
    assert whole.modules_again({"test_a (m.T)": judge.PASSED, "test_d (m.T)": judge.SKIPPED}, "") == []


def test_broken_is_passing_with_the_fix_and_not_passing_with_the_candidate():
    fixed = {"test_a (m.T)": judge.PASSED, "test_b (m.T)": judge.PASSED, "test_c (m.T)": judge.PASSED, "test_d (m.T)": judge.FAILED, "test_e (m.T)": judge.SKIPPED,
             "test_f (m.T)": judge.PASSED, "What b does": judge.PASSED}
    candidate = {"test_a (m.T)": judge.PASSED, "test_b (m.T)": judge.FAILED, "test_d (m.T)": judge.FAILED, "test_e (m.T)": judge.FAILED,
                 "test_f (m.T)": judge.SKIPPED, "What b does": judge.FAILED}
    assert whole.broken(fixed, candidate) == ["test_b (m.T)", "test_c (m.T)", "test_f (m.T)"]       # failed; did not run; skipped where it passed
    assert whole.broken(fixed, fixed) == [] and whole.broken({}, candidate) == []


# --------------------------------------------------------------------------- #
# one candidate
# --------------------------------------------------------------------------- #
@needs_git
def test_the_stand_in_runs_every_module_when_no_label_is_given_and_the_labels_when_they_are(project, tree):
    assert count.as_the_task_starts(tree, project["test_patch"])
    everything = whole.run_whole(tree, [], 60)
    assert judge.ran(everything["output"]) == 5 and judge.finished(everything["output"]) and not everything["stopped"]
    found = judge.statuses(everything["output"])
    assert found[FIRST[0]] == judge.FAILED and found[LABEL] == judge.PASSED and found[MACHINE] == judge.FAILED
    some = whole.run_whole(tree, ["label_tests.tests"], 60, processes=1)
    assert judge.ran(some["output"]) == 2 and set(judge.statuses(some["output"])) == {LABEL, MUCH, "A label holds the shop and the name."}


@needs_git
def test_a_run_that_takes_too_long_is_stopped(project, tree):
    (tree / "tests" / "store_tests" / "tests.py").write_text("import time\ntime.sleep(30)\n")
    got = whole.run_whole(tree, [], 1.0)
    assert got["stopped"] and got["seconds"] < 10 and not judge.finished(got["output"])


@needs_git
def test_a_candidate_that_breaks_nothing_keeps_the_whole_suite_though_a_test_fails_on_this_machine(project, tree):
    row = under(project, tree, FIXED)
    assert row["whole_run"] == {**row["whole_run"], "ran": 5, "finished": True, "stopped": False, "passing": 4, "not_passing": 1, "start_passing": 1, "start_passing_wanted": 1}
    assert row["modules_again"] == ["machine_tests.tests"]
    assert row["run_again"]["with_the_candidate"]["ran"] == 1 and row["run_again"]["with_the_fix"]["not_passing"] == 1
    assert row["broken_by_the_candidate"] == [] and row["keeps_the_whole_suite"] is True and row["why_nothing_is_said"] is None


@needs_git
def test_a_candidate_that_breaks_a_test_elsewhere_does_not_keep_the_whole_suite(project, tree):
    row = under(project, tree, BREAKS_THE_LABEL)
    assert row["whole_run"]["start_passing"] == 1 and row["whole_run"]["not_passing"] == 2          # the task's own test passes: the count called this resolving
    assert row["modules_again"] == ["label_tests.tests", "machine_tests.tests"]
    assert row["broken_by_the_candidate"] == [LABEL] and row["keeps_the_whole_suite"] is False
    assert (tree / "shop" / "store.py").read_text() == FIXED                                        # the second run with the expert's fix was the last one


@needs_git
def test_a_module_that_does_not_load_with_the_candidate_has_all_its_tests_broken(project, tree):
    row = under(project, tree, TAKES_A_NAME_AWAY)
    assert row["modules_again"] == ["label_tests.tests", "machine_tests.tests"]
    assert row["broken_by_the_candidate"] == [LABEL, MUCH] and row["keeps_the_whole_suite"] is False


@needs_git
def test_a_test_that_fails_once_and_passes_the_second_time_is_not_held_against_the_candidate(project, tree):
    """The whole run and the second run with the candidate share a tree; the tree is cleaned before the run with the expert's fix."""
    patch = project["test_patch"] + ("diff --git a/tests/once_tests/__init__.py b/tests/once_tests/__init__.py\nnew file mode 100644\n"
                                     "diff --git a/tests/once_tests/tests.py b/tests/once_tests/tests.py\nnew file mode 100644\n--- /dev/null\n+++ b/tests/once_tests/tests.py\n"
                                     f"@@ -0,0 +1,{len(ONCE_TESTS.splitlines())} @@\n" + "".join(f"+{line}\n" for line in ONCE_TESTS.splitlines()))
    row = whole.of_candidate(tree, patch, project["fix"], "shop/store.py", FIXED, FIRST)
    assert row["whole_run"]["ran"] == 6 and row["whole_run"]["not_passing"] == 2 and row["modules_again"] == ["machine_tests.tests", "once_tests.tests"]
    assert row["run_again"]["with_the_candidate"]["not_passing"] == 1 and row["run_again"]["with_the_fix"]["not_passing"] == 2
    assert row["broken_by_the_candidate"] == [] and row["keeps_the_whole_suite"] is True


def canned(*outputs, stopped=()):
    """A runner that hands out what was printed, one run after the other."""
    left = list(outputs)
    calls = []

    def run(tree, labels, seconds):
        calls.append(list(labels))
        return {"output": left.pop(0), "seconds": 1.0, "stopped": len(calls) in stopped, "exit": 0}
    run.calls = calls
    return run


ALL_PASS = "test_a (m.T) ... ok\n\n----\nRan 1 test in 0.1s\n\nOK\n"
ONE_FAILS = "test_a (m.T) ... FAIL\n\n----\nRan 1 test in 0.1s\n\nFAILED (failures=1)\n"


@needs_git
def test_with_nothing_failing_in_the_whole_run_no_second_run_is_made(project, tree):
    run = canned(ALL_PASS)
    row = under(project, tree, FIXED, run=run)
    assert run.calls == [[]] and row["modules_again"] == [] and row["run_again"] is None and row["broken_by_the_candidate"] == [] and row["keeps_the_whole_suite"] is True


@needs_git
def test_the_second_runs_are_of_the_modules_alone_first_with_the_candidate_then_with_the_fix(project, tree):
    run = canned(ONE_FAILS, ONE_FAILS, ALL_PASS)
    row = under(project, tree, BREAKS_THE_LABEL, run=run)
    assert run.calls == [[], ["m"], ["m"]] and row["broken_by_the_candidate"] == ["test_a (m.T)"] and row["keeps_the_whole_suite"] is False
    row = under(project, tree, BREAKS_THE_LABEL, run=canned(ONE_FAILS, ALL_PASS, ONE_FAILS))            # the other way round: the fix fails, the candidate passes
    assert row["broken_by_the_candidate"] == [] and row["keeps_the_whole_suite"] is True


@needs_git
@pytest.mark.parametrize("outputs, stopped, why", [
    (("test_a (m.T) ... ok\n",), (), "the whole run ended before its summary"),
    (("test_a (m.T) ... ok\n",), (1,), "the whole run was stopped for time"),
    ((ONE_FAILS, "test_a (m.T) ... FAIL\n", ALL_PASS), (), "a second run did not get to its summary"),
    ((ONE_FAILS, ONE_FAILS, "test_a (m.T) ... ok\n"), (), "a second run did not get to its summary"),
])
def test_where_a_run_does_not_get_to_its_summary_nothing_is_said_of_the_candidate(project, tree, outputs, stopped, why):
    row = under(project, tree, FIXED, run=canned(*outputs, stopped=stopped))
    assert row["keeps_the_whole_suite"] is None and row["broken_by_the_candidate"] is None and row["why_nothing_is_said"] == why


@needs_git
def test_too_many_modules_are_not_run_again_and_nothing_is_said(project, tree, monkeypatch):
    monkeypatch.setattr(whole, "MOST_MODULES_AGAIN", 1)
    run = canned("test_a (m.T) ... FAIL\ntest_b (n.T) ... ERROR\n\n----\nRan 2 tests in 0.1s\n\nFAILED (failures=1, errors=1)\n")
    row = under(project, tree, FIXED, run=run)
    assert run.calls == [[]] and row["keeps_the_whole_suite"] is None and row["why_nothing_is_said"] == "2 modules hold a test that did not pass: too many to run again"
    monkeypatch.setattr(whole, "MOST_MODULES_AGAIN", 2)
    assert under(project, tree, FIXED, run=canned(run_two := ONE_FAILS.replace("test_a (m.T) ... FAIL", "test_a (m.T) ... FAIL\ntest_b (n.T) ... ERROR"), run_two, run_two))["keeps_the_whole_suite"] is True


@needs_git
def test_the_whole_run_is_kept_as_it_was_printed(project, tree, tmp_path):
    under(project, tree, FIXED, run=canned(ALL_PASS), keep_output=tmp_path / "printed.txt")
    assert (tmp_path / "printed.txt").read_text() == ALL_PASS


@needs_git
def test_a_test_patch_or_a_fix_that_does_not_go_in_is_an_error_not_a_verdict(project, tree):
    with pytest.raises(RuntimeError, match="the test patch did not go in"):
        whole.of_candidate(tree, "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n", project["fix"], "shop/store.py", FIXED, FIRST, run=canned(ALL_PASS))
    with pytest.raises(RuntimeError, match="the expert's fix did not go in"):
        whole.of_candidate(tree, project["test_patch"], "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n", "shop/store.py", FIXED, FIRST,
                           run=canned(ONE_FAILS, ONE_FAILS, ALL_PASS))


# --------------------------------------------------------------------------- #
# all of them
# --------------------------------------------------------------------------- #
PER_TASK = {
    "django__django-900": {"candidates": [{"place": 1, "resolves": False}, {"place": 2, "resolves": True}, {"place": 3, "resolves": True}]},
    "django__django-1000": {"candidates": [{"place": 1, "resolves": True}, {"place": 2, "resolves": True}]},
    "django__django-800": {"candidates": [{"place": 1, "resolves": True}]},
    "django__django-700": {"candidates": [{"place": 1, "resolves": False}]},
    "django__django-600": {"candidates": []},
    "django__django-500": {"judged": False},
}


def test_the_resolving_candidates_in_the_order_they_are_run():
    assert whole.resolving(PER_TASK, "one") == [("django__django-800", 1), ("django__django-1000", 1)]
    assert whole.resolving(PER_TASK, "first") == [("django__django-800", 1), ("django__django-1000", 1), ("django__django-900", 2)]
    assert whole.resolving(PER_TASK, "all") == whole.resolving(PER_TASK, "first") + [("django__django-900", 3), ("django__django-1000", 2)]
    assert whole.resolving(PER_TASK) == whole.resolving(PER_TASK, "first")


def a_row(task, at, keeps, first=True, broken=(), finished=True, why=None, seconds=10.0):
    return {"task": task, "place": at, "first_resolving": first, "whole_run": {"finished": finished}, "keeps_the_whole_suite": keeps,
            "broken_by_the_candidate": None if keeps is None else list(broken), "why_nothing_is_said": why, "seconds": seconds}


ROWS = [a_row("django__django-1", 1, True), a_row("django__django-2", 1, False, broken=("a", "b")), a_row("django__django-3", 1, None, finished=False, why="the whole run ended before its summary"),
        a_row("django__django-4", 2, True), a_row("django__django-5", 6, False, broken=("c",)), a_row("django__django-2", 4, True, first=False), a_row("django__django-1", 3, False, first=False, broken=("d",))]


def test_the_counts():
    summary = whole.summarise(ROWS)
    assert summary["candidates_run"] == 7 and summary["seconds_of_test_runs"] == 70.0
    assert (summary["one_submission__candidates_run"], summary["one_submission__whole_runs_that_got_to_their_summary"]) == (3, 2)
    assert (summary["one_submission__keeping_the_whole_suite"], summary["one_submission__breaking_a_test_elsewhere"]) == (1, 1)
    assert summary["one_submission__keeping_the_whole_suite__tasks"] == ["django__django-1"]
    assert summary["one_submission__breaking_a_test_elsewhere__tests_broken"] == {"django__django-2 place 1": 2}
    assert summary["one_submission__nothing_said"] == {"django__django-3 place 1": "the whole run ended before its summary"}
    assert (summary["first_resolving__candidates_run"], summary["first_resolving__keeping_the_whole_suite"], summary["first_resolving__breaking_a_test_elsewhere"]) == (5, 2, 2)
    assert summary["first_resolving__breaking_a_test_elsewhere__tests_broken"] == {"django__django-2 place 1": 2, "django__django-5 place 6": 1}
    assert (summary["every_resolving_candidate_run__candidates_run"], summary["every_resolving_candidate_run__keeping_the_whole_suite"],
            summary["every_resolving_candidate_run__breaking_a_test_elsewhere"]) == (7, 3, 3)
    assert summary["tasks_with_a_candidate_run_that_keeps_the_whole_suite"] == ["django__django-1", "django__django-2", "django__django-4"]
    assert whole.summarise([])["one_submission__candidates_run"] == 0


def test_each_expectation_is_judged_with_both_ends_counted_in():
    names = list(whole.EXPECTED)
    assert names == ["one_submission__whole_runs_that_got_to_their_summary", "one_submission__breaking_a_test_elsewhere", "one_submission__keeping_the_whole_suite"]
    low = {name: whole.EXPECTED[name][0] for name in names}
    high = {name: whole.EXPECTED[name][1] for name in names}
    assert all(row["held"] for row in whole.held(low).values()) and all(row["held"] for row in whole.held(high).values())
    assert not any(row["held"] for row in whole.held({name: value - 1 for name, value in low.items()}).values())
    assert not any(row["held"] for row in whole.held({name: value + 1 for name, value in high.items()}).values())
    assert whole.held({})[names[0]] == {"expected": list(whole.EXPECTED[names[0]]), "found": None, "held": False}


def counts(run=5, breaking=2, keeping=3):
    return {"one_submission__candidates_run": run, "one_submission__breaking_a_test_elsewhere": breaking, "one_submission__keeping_the_whole_suite": keeping}


def test_the_rule_when_a_first_candidate_breaks_a_test_elsewhere():
    said = whole.rule(counts())
    assert len(said["verdict"]) == 1 and said["verdict"][0].startswith("2 of the 5 first candidates the tasks' own tests accept break a test elsewhere in the project")
    assert said["verdict"][0].endswith("one submission that also keeps the whole suite: 3") and "BEFORE it is handed in" in said["next"]


def test_the_rule_when_none_does_and_when_nothing_can_be_said_of_some():
    said = whole.rule(counts(breaking=0, keeping=5))
    assert len(said["verdict"]) == 1 and said["verdict"][0].startswith("none of the 5 first candidates") and said["verdict"][0].endswith("agree on 5") and "WRITING" in said["next"]
    said = whole.rule(counts(breaking=1, keeping=2))
    assert len(said["verdict"]) == 2 and said["verdict"][0].startswith("of 2 of the 5 first candidates nothing can be said on this machine")
    assert said["verdict"][1].startswith("1 of the 5 first candidates")


def test_the_code_that_is_hashed_is_this_tool_the_count_and_the_organ():
    assert sorted(whole.code_sha256()) == ["canonical/runtime/tests_as_the_judge_v1.py", "canonical/tools/candidate_under_the_tasks_tests_measure_v1.py",
                                           "canonical/tools/resolving_candidate_under_the_whole_suite_measure_v1.py"]


# --------------------------------------------------------------------------- #
# the record in the tree
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def written():
    if not RECORD.exists():
        pytest.skip("the record is not in the tree yet")
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_the_record_adds_up_from_its_rows(written):
    assert written["schema"] == whole.SCHEMA and written["model_calls"] == 0
    assert written["summary"] == whole.summarise(written["candidates"])
    assert written["expectations"] == whole.held(written["summary"]) and written["rule"] == whole.rule(written["summary"])
    assert written["expected"] == {name: list(pair) for name, pair in whole.EXPECTED.items()}


def test_the_record_was_made_by_the_code_in_the_tree(written):
    assert written["code_sha256"] == whole.code_sha256()


def test_the_records_candidates_are_the_ones_the_count_called_resolving(written):
    counted = json.loads(whole.COUNT_RECORD.read_text(encoding="utf-8"))["per_task"]
    assert [(row["task"], row["place"]) for row in written["candidates"]] == whole.resolving(counted, written["which"])
    for row in written["candidates"]:
        there = counted[row["task"]]["candidates"][row["place"] - 1]
        assert there["resolves"] and there["sha256"] == row["sha256"] and there["place"] == row["place"]
        assert row["whole_run"]["start_passing"] == row["whole_run"]["start_passing_wanted"] or row["keeps_the_whole_suite"] is not True
