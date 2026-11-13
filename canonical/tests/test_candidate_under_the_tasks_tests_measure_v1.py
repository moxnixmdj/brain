#!/usr/bin/env python3
"""Candidates under a task's own tests: how the published task is read, how a tree is set up and
its tests are run, what is said of one task and of each candidate, how the counts are added up, the
rule, and that the record in the tree adds up from its rows.

The project here is a small one made on the spot, with a stand-in for Django's `tests/runtests.py`
that takes the same arguments: every run in these tests is a real run of real tests."""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import tests_as_the_judge_v1 as judge  # noqa: E402
from canonical.tools import candidate_under_the_tasks_tests_measure_v1 as measure  # noqa: E402

RECORD = ROOT / "canonical" / "verification" / "CANDIDATE_UNDER_THE_TASKS_TESTS_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json"
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not here")

STORE = '''"""A shop."""


def unrelated(a, b):
    c = a
    return c


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
ONLY_OTHER = STORE.replace("self.rows.setdefault('default', []).append(name)", "self.rows.setdefault('other', []).append(name)")
RUNNER = '''import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
given = sys.argv[1:]
assert given[:5] == ["--verbosity", "2", "--settings=test_sqlite", "--parallel", "1"], given
outcome = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(unittest.defaultTestLoader.loadTestsFromNames(given[5:]))
sys.exit(0 if outcome.wasSuccessful() else 1)
'''
TESTS = '''import pathlib
import unittest

from shop.store import Store


class StoreTests(unittest.TestCase):
    def test_load_of_nothing(self):
        self.assertEqual(Store().load('default'), [])

    def test_the_default_database(self):
        """
        The default database keeps what was saved to it.
        """
        store = Store()
        store.save('a', 'default')
        self.assertEqual(store.load('default'), ['a'])

    def test_known_to_fail_here(self):
        self.assertEqual(1, 2)

    def test_saved_where_the_file_says(self):
        where = (pathlib.Path(__file__).parent / 'expected.txt').read_text().strip()
        store = Store()
        store.save('a', where)
        self.assertEqual(store.load(where), ['a'])
'''
MORE_TESTS = TESTS + '''
    def test_save_writes_to_the_database_given(self):
        store = Store()
        store.save('a', 'other')
        self.assertEqual(store.load('other'), ['a'])
'''
TREE = {
    "shop/__init__.py": "",
    "shop/store.py": STORE,
    "shop/noise.py": "def noise(database, wrong, writes):\n    return database, wrong, writes\n",
    "tests/runtests.py": RUNNER,
    "tests/store_tests/__init__.py": "",
    "tests/store_tests/tests.py": TESTS,
    "tests/store_tests/expected.txt": "default\n",
    "docs/store.txt": "Store.save writes to the database\n",
}
TEXT = "Store.save() writes to the wrong database.\n```\nself.rows.setdefault(db, []).append(name)\n```\n"
OTHER_TEXT = "noise(database, wrong, writes) should not return writes.\n```\nreturn database, wrong\n```\n"
FIRST = ["test_save_writes_to_the_database_given (store_tests.tests.StoreTests)"]
KEEP = ["test_load_of_nothing (store_tests.tests.StoreTests)", "The default database keeps what was saved to it.",
        "test_known_to_fail_here (store_tests.tests.StoreTests)"]
TASK_TESTS = {"fail_to_pass": FIRST, "pass_to_pass": KEEP, "version": "4.2"}
# A second task on the same tree: its test patch changes a file that is no test module, and a test that is there already starts failing.
DATA_TESTS = {"fail_to_pass": ["test_saved_where_the_file_says (store_tests.tests.StoreTests)"], "pass_to_pass": KEEP[:2], "version": "4.2"}


def _git(directory, *args):
    done = subprocess.run(["git", "-C", str(directory), "-c", "user.name=t", "-c", "user.email=t@example.org", *args], capture_output=True, text=True, check=True)
    return done.stdout


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    """A project at the commit a task starts from, the task's test patch and the expert's fix as diffs, and the commit after both."""
    directory = tmp_path_factory.mktemp("trees") / "django__django.git"
    directory.mkdir()
    _git(directory, "init", "-q")
    for path, source in TREE.items():
        (directory / path).parent.mkdir(parents=True, exist_ok=True)
        (directory / path).write_text(source)
    _git(directory, "add", "-A")
    _git(directory, "commit", "-q", "-m", "as the task starts")
    commit = _git(directory, "rev-parse", "HEAD").strip()
    (directory / "tests" / "store_tests" / "expected.txt").write_text("other\n")
    data_patch = _git(directory, "diff")
    _git(directory, "checkout", "-q", "--", ".")
    (directory / "tests" / "store_tests" / "tests.py").write_text(MORE_TESTS)
    test_patch = _git(directory, "diff")
    _git(directory, "commit", "-q", "-a", "-m", "the task's tests")
    (directory / "shop" / "store.py").write_text(FIXED)
    fix = _git(directory, "diff")
    _git(directory, "commit", "-q", "-a", "-m", "the expert's fix")
    return {"clone": directory, "commit": commit, "test_patch": test_patch, "fix": fix, "data_patch": data_patch, "after": _git(directory, "rev-parse", "HEAD").strip()}


@pytest.fixture()
def tree(project, tmp_path):
    return tmp_path / "tree"


def candidate(text: str, function: str = "Store.save", path: str = "shop/store.py") -> dict:
    return {"path": path, "function": function, "text": text}


def counting(runs: list):
    def run(tree, labels, seconds):
        runs.append(list(labels))
        return measure.run_tests(tree, labels, seconds)
    return run


# --------------------------------------------------------------------------- #
# the task as it is published
# --------------------------------------------------------------------------- #
A_PATCH = ("diff --git a/tests/admin_views/tests.py b/tests/admin_views/tests.py\n--- a/tests/admin_views/tests.py\n+++ b/tests/admin_views/tests.py\n@@ -1 +1 @@\n-a\n+b\n"
           "diff --git a/tests/admin_views/templates/x.html b/tests/admin_views/templates/x.html\n@@ -1 +1 @@\n-a\n+b\n"
           "diff --git a/tests/migrations/test_loader.py b/tests/migrations/test_loader.py\n@@ -1 +1 @@\n-a\n+b\n"
           "diff --git a/django/test/utils.py b/django/test/utils.py\n@@ -1 +1 @@\n-a\n+b\n"
           "diff --git a/tests/admin_views/tests.py b/tests/admin_views/tests.py\n@@ -9 +9 @@\n-a\n+b\n")


def test_the_paths_a_diff_touches_once_each_in_its_order():
    assert measure.touched(A_PATCH) == ["tests/admin_views/tests.py", "tests/admin_views/templates/x.html", "tests/migrations/test_loader.py", "django/test/utils.py"]
    assert measure.touched("") == []
    assert measure.touched("+diff --git a/x.py b/x.py\n") == []       # a line of a diff that quotes a diff is not a file


def test_the_labels_are_the_python_test_modules_the_test_patch_touches():
    assert measure.labels_of(A_PATCH) == ["admin_views.tests", "migrations.test_loader"]
    assert measure.labels_of("diff --git a/tests/validators/invalid_urls.txt b/tests/validators/invalid_urls.txt\n") == []


def test_the_modules_the_tests_names_give():
    names = ["test_a (validators.tests.TestValidators)", "test_b (validators.tests.TestValidators.test_b)", "A docstring line", "test_c (other.tests.T)",
             "test_d (NoModule)"]
    assert measure.modules_named(names) == ["validators.tests", "other.tests"]
    assert measure.modules_named([]) == []


def test_the_lists_of_tests_are_read_from_the_file_the_dataset_is_kept_in(tmp_path):
    pytest.importorskip("yaml")
    held = tmp_path / "django__django-1.yaml"
    held.write_text("base_commit: 0123456789abcdef0123456789abcdef01234567\nversion: '4.2'\nfail_to_pass:\n- test_a (m.T)\n- 'Quoted: line'\n"
                    "pass_to_pass:\n- test_b (m.T)\nproblem_statement: |\n  words\n")
    assert measure.tests_of(held) == {"fail_to_pass": ["test_a (m.T)", "Quoted: line"], "pass_to_pass": ["test_b (m.T)"], "version": "4.2",
                                      "base_commit": "0123456789abcdef0123456789abcdef01234567"}
    held.write_text("base_commit: abc\nversion: 5.0\n")
    assert measure.tests_of(held)["fail_to_pass"] == [] and measure.tests_of(held)["pass_to_pass"] == [] and measure.tests_of(held)["version"] == "5.0"


def pull(*files: dict) -> dict:
    return {"files": [{"status": "modified", "previous": None, "is_test": False, **file} for file in files]}


def test_the_experts_fix_is_every_file_of_the_pull_request_the_test_patch_does_not_touch():
    record = pull({"path": "django/a.py", "patch": "@@ -1 +1 @@\n-a\n+b"}, {"path": "tests/admin_views/tests.py", "patch": "@@ -1 +1 @@\n-a\n+b", "is_test": True},
                  {"path": "docs/releases/4.2.txt", "patch": "@@ -1 +1 @@\n-a\n+b\n"}, {"path": "django/logo.png", "patch": None},
                  {"path": "tests/helpers_not_in_the_patch.py", "patch": "@@ -1 +1 @@\n-a\n+b", "is_test": True})
    diff = measure.expert_diff(record, A_PATCH)
    assert measure.touched(diff) == ["django/a.py", "docs/releases/4.2.txt", "tests/helpers_not_in_the_patch.py"]
    assert diff.startswith("diff --git a/django/a.py b/django/a.py\n--- a/django/a.py\n+++ b/django/a.py\n@@ -1 +1 @@\n-a\n+b\ndiff --git a/docs/releases/4.2.txt ")
    assert diff.endswith("+b\n") and "\n\n" not in diff


def test_a_new_file_a_removed_one_and_a_renamed_one_are_written_as_git_writes_them():
    diff = measure.expert_diff(pull({"path": "django/new.py", "status": "added", "patch": "@@ -0,0 +1 @@\n+a"}), "")
    assert diff == "diff --git a/django/new.py b/django/new.py\nnew file mode 100644\n--- /dev/null\n+++ b/django/new.py\n@@ -0,0 +1 @@\n+a\n"
    diff = measure.expert_diff(pull({"path": "django/old.py", "status": "removed", "patch": "@@ -1 +0,0 @@\n-a"}), "")
    assert diff == "diff --git a/django/old.py b/django/old.py\ndeleted file mode 100644\n--- a/django/old.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-a\n"
    diff = measure.expert_diff(pull({"path": "django/to.py", "status": "renamed", "previous": "django/from.py", "patch": "@@ -1 +1 @@\n-a\n+b"}), "")
    assert diff == ("diff --git a/django/from.py b/django/to.py\nrename from django/from.py\nrename to django/to.py\n--- a/django/from.py\n+++ b/django/to.py\n"
                    "@@ -1 +1 @@\n-a\n+b\n")
    assert measure.expert_diff({"files": []}, "") == "" and measure.expert_diff({}, "") == ""


@needs_git
def test_the_new_the_removed_and_the_changed_file_go_into_a_tree_together(project, tree):
    measure.at_commit(project["clone"], tree, project["commit"])
    record = pull({"path": "shop/new.py", "status": "added", "patch": "@@ -0,0 +1 @@\n+A = 1"},
                  {"path": "docs/store.txt", "status": "removed", "patch": "@@ -1 +0,0 @@\n-Store.save writes to the database"},
                  {"path": "shop/noise.py", "patch": "@@ -1,2 +1,2 @@\n def noise(database, wrong, writes):\n-    return database, wrong, writes\n+    return database, wrong"})
    assert measure.applied(tree, measure.expert_diff(record, ""))
    assert (tree / "shop" / "new.py").read_text() == "A = 1\n" and not (tree / "docs" / "store.txt").exists()
    assert (tree / "shop" / "noise.py").read_text().endswith("return database, wrong\n")


PRINTED = ("test_a (m.T.test_a) ... ok\ntest_b (m.T.test_b)\nWhat b does ... ok\ntest_c (m.U.test_c)\nWhat b does ... ok\n")


def test_the_labels_that_run_just_the_named_tests():
    assert measure.few_of(PRINTED, ["test_a (m.T)"]) == ["m.T.test_a"]
    assert measure.few_of(PRINTED, ["What b does", "test_a (m.T.test_a)", "test_b (m.T)"]) == ["m.T.test_b", "m.U.test_c", "m.T.test_a"]


def test_no_labels_when_one_of_the_tests_cannot_be_named_or_none_is_asked_for():
    assert measure.few_of(PRINTED, ["test_a (m.T)", "not printed"]) is None
    assert measure.few_of(PRINTED, []) is None


def test_whether_a_file_is_python():
    assert measure.parses(STORE) and measure.parses("")
    assert not measure.parses("def broken(:\n") and not measure.parses("x = 1\n\0")


# --------------------------------------------------------------------------- #
# the tree and the runs
# --------------------------------------------------------------------------- #
@needs_git
def test_the_tree_is_the_commits_and_nothing_else(project, tree):
    measure.at_commit(project["clone"], tree, project["commit"])
    assert (tree / "shop" / "store.py").read_text() == STORE and (tree / "tests" / "store_tests" / "tests.py").read_text() == TESTS
    (tree / "left_behind.py").write_text("x = 1\n")
    (tree / "shop" / "store.py").write_text("changed\n")
    measure.at_commit(project["clone"], tree, project["after"])
    assert (tree / "shop" / "store.py").read_text() == FIXED and not (tree / "left_behind.py").exists()
    measure.at_commit(project["clone"], tree, project["commit"])
    assert (tree / "shop" / "store.py").read_text() == STORE


@needs_git
def test_a_diff_goes_in_whole_or_not_at_all(project, tree):
    measure.at_commit(project["clone"], tree, project["commit"])
    assert measure.applied(tree, project["fix"]) and (tree / "shop" / "store.py").read_text() == FIXED
    assert not measure.applied(tree, project["fix"])                # it is in already
    assert not measure.applied(tree, "") and not measure.applied(tree, "\n")
    assert (tree / "shop" / "store.py").read_text() == FIXED


@needs_git
def test_back_to_the_start_of_the_task_takes_a_candidate_out_and_puts_the_tests_in(project, tree):
    measure.at_commit(project["clone"], tree, project["commit"])
    (tree / "shop" / "store.py").write_text(ONLY_OTHER)
    (tree / "shop" / "extra.py").write_text("x = 1\n")
    assert measure.as_the_task_starts(tree, project["test_patch"])
    assert (tree / "shop" / "store.py").read_text() == STORE and not (tree / "shop" / "extra.py").exists()
    assert (tree / "tests" / "store_tests" / "tests.py").read_text() == MORE_TESTS
    assert measure.as_the_task_starts(tree, project["test_patch"])   # and again, from a tree that has them
    assert not measure.as_the_task_starts(tree, project["test_patch"].replace("        self.assertEqual(store.load(where), ['a'])", "        self.assertEqual(store.load(where), ['b'])"))


@needs_git
def test_a_run_gives_what_the_runner_printed(project, tree):
    measure.at_commit(project["clone"], tree, project["commit"])
    got = measure.run_tests(tree, ["store_tests.tests"], 60)
    assert not got["stopped"] and got["exit"] == 1 and got["seconds"] < 60
    assert judge.ran(got["output"]) == 4 and judge.finished(got["output"])
    found = judge.statuses(got["output"])
    assert found["test_load_of_nothing (store_tests.tests.StoreTests)"] == judge.PASSED
    assert found["test_known_to_fail_here (store_tests.tests.StoreTests)"] == judge.FAILED
    got = measure.run_tests(tree, ["store_tests.tests.StoreTests.test_load_of_nothing"], 60)
    assert got["exit"] == 0 and judge.ran(got["output"]) == 1


@needs_git
def test_a_run_that_takes_too_long_is_stopped_with_everything_it_started(project, tree):
    measure.at_commit(project["clone"], tree, project["commit"])
    (tree / "tests" / "runtests.py").write_text("import subprocess, sys, time\nprint('started', flush=True)\n"
                                                "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\ntime.sleep(60)\n")
    started = time.time()
    got = measure.run_tests(tree, ["store_tests.tests"], 4)
    assert got["stopped"] and "started" in got["output"] and time.time() - started < 30
    assert not judge.finished(got["output"])


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #
@needs_git
def test_a_task_this_machine_can_judge(project, tree):
    row = measure.of_task(tree, project["clone"], project["commit"], project["test_patch"], project["fix"], TASK_TESTS, [], None)
    assert row["judged"] and row["why_not"] is None and row["labels"] == ["store_tests.tests"]
    assert (row["start_passing"], row["keep_passing"], row["candidates_made"], row["candidates"], row["another_tasks_text"]) == (1, 3, 0, [], None)
    assert row["as_it_stands"]["start_passing"] == 0 and row["as_it_stands"]["keep_passing"] == 2 and row["as_it_stands"]["ran"] == 5
    assert row["with_the_fix"]["start_passing"] == 1 and row["with_the_fix"]["keep_passing"] == 2 and row["with_the_fix"]["finished"]
    assert row["left_out"] == 1 and row["version"] == "4.2" and row["seconds"] >= 0
    assert "few" not in row                                          # nothing to run just some tests for


@needs_git
def test_each_candidate_is_judged_alone_in_its_place(project, tree):
    runs: list = []
    made = [candidate(STORE, "as it stands"), candidate("def broken(:\n", "does not parse"), candidate(ONLY_OTHER, "passes the new test, breaks an old one"),
            candidate(FIXED, "the fix"), candidate(FIXED, "the fix again")]
    row = measure.of_task(tree, project["clone"], project["commit"], project["test_patch"], project["fix"], TASK_TESTS, made, candidate(STORE, "another"),
                          run=counting(runs))
    assert row["judged"] and row["few"]["labels"] == 1 and row["few"]["stands"]
    stands, broken, breaks, fix, again = row["candidates"]
    assert [one["place"] for one in row["candidates"]] == [1, 2, 3, 4, 5]
    assert (stands["resolves"], stands["whole_run"], stands["start_passing"]) == (False, False, 0)
    assert broken["does_not_parse"] and not broken["resolves"] and not broken["whole_run"] and broken["start_passing"] is None
    assert (breaks["resolves"], breaks["whole_run"], breaks["start_passing"], breaks["keep_passing"], breaks["keep_wanted"]) == (False, True, 1, 1, 2)
    assert (fix["resolves"], fix["whole_run"], fix["start_passing"], fix["keep_passing"], fix["keep_wanted"]) == (True, True, 1, 2, 2)
    assert {key: value for key, value in again.items() if key not in ("place", "function")} == {key: value for key, value in fix.items() if key not in ("place", "function")}
    assert row["another_tasks_text"]["resolves"] is False and "place" not in row["another_tasks_text"] and row["another_tasks_text"]["function"] == "another"
    assert measure.first_resolving(row) == 4
    whole, few = ["store_tests.tests"], ["store_tests.tests.StoreTests.test_save_writes_to_the_database_given"]
    assert runs == [whole, whole, few,                               # as it stands, with the fix, just the new test with the fix
                    few,                                             # the file as it stands: the new test fails, no whole run
                    few, whole,                                      # passes the new test, so the whole module is run
                    few, whole]                                      # the fix; its second copy and the unchanged file are not run again
    assert (tree / "shop" / "store.py").read_text() == FIXED          # the last candidate that was run is what is left in the tree


@needs_git
def test_a_candidate_is_not_helped_by_the_one_before_it(project, tree):
    made = [candidate(FIXED), candidate(STORE.replace("return list(self.rows.get(db, []))", "return list(self.rows.get(db, [])) + []"), "Store.load")]
    row = measure.of_task(tree, project["clone"], project["commit"], project["test_patch"], project["fix"], TASK_TESTS, made, None)
    assert [one["resolves"] for one in row["candidates"]] == [True, False]


@needs_git
def test_a_candidate_in_another_file_is_written_into_that_file(project, tree):
    made = [candidate("def noise(database, wrong, writes):\n    return database\n", "noise", "shop/noise.py")]
    row = measure.of_task(tree, project["clone"], project["commit"], project["test_patch"], project["fix"], TASK_TESTS, made, None)
    assert row["candidates"][0]["resolves"] is False and row["candidates"][0]["path"] == "shop/noise.py"
    assert (tree / "shop" / "noise.py").read_text().endswith("return database\n") and (tree / "shop" / "store.py").read_text() == STORE


@needs_git
def test_without_labels_for_just_the_new_tests_every_candidate_gets_the_whole_run(project, tree):
    runs: list = []
    tests = {**TASK_TESTS, "fail_to_pass": FIRST}
    measure.at_commit(project["clone"], tree, project["commit"])
    assert measure.applied(tree, project["test_patch"]) and measure.applied(tree, project["fix"])
    fixed = judge.statuses(measure.run_tests(tree, ["store_tests.tests"], 60)["output"])
    row = measure.of_candidate(tree, project["test_patch"], "shop/store.py", STORE, ["store_tests.tests"], None, fixed, tests["fail_to_pass"], KEEP, counting(runs))
    assert runs == [["store_tests.tests"]] and row["whole_run"] and not row["resolves"] and row["start_passing"] == 0 and row["keep_passing"] == 2
    row = measure.of_candidate(tree, project["test_patch"], "shop/store.py", FIXED, ["store_tests.tests"], None, fixed, tests["fail_to_pass"], KEEP, counting(runs))
    assert row["resolves"] and len(runs) == 2


@needs_git
def test_a_new_test_that_fails_when_run_alone_even_with_the_fix_is_not_run_alone(project, tree):
    runs: list = []

    def run(tree, labels, seconds):
        runs.append(list(labels))
        got = measure.run_tests(tree, labels, seconds)
        return {**got, "output": got["output"].replace(" ... ok", " ... FAIL")} if len(labels[0].split(".")) > 2 else got

    row = measure.of_task(tree, project["clone"], project["commit"], project["test_patch"], project["fix"], TASK_TESTS, [candidate(FIXED)], None, run=run)
    assert row["few"]["stands"] is False and row["candidates"][0]["resolves"] and row["candidates"][0]["whole_run"]
    assert runs[3:] == [["store_tests.tests"]]


@needs_git
@pytest.mark.parametrize("change, why", [
    (lambda given: {**given, "tests": {**TASK_TESTS, "fail_to_pass": []}}, "the task names no test that should start passing"),
    (lambda given: {**given, "test_patch": "diff --git a/docs/store.txt b/docs/store.txt\n", "tests": {**TASK_TESTS, "fail_to_pass": ["Only a docstring line"], "pass_to_pass": []}},
     "neither the test patch nor the tests' names give a test module"),
    (lambda given: {**given, "test_patch": given["test_patch"].replace("        self.assertEqual(store.load(where), ['a'])", "        self.assertEqual(store.load(where), ['b'])")},
     "the test patch did not go in"),
    (lambda given: {**given, "fix": given["fix"].replace("-        self.rows.setdefault('default'", "-        self.rows.setdefault('elsewhere'")}, "the expert's fix did not go in"),
    (lambda given: {**given, "fix": ""}, "the expert's fix did not go in"),
    (lambda given: {**given, "tests": {**TASK_TESTS, "fail_to_pass": ["test_known_to_fail_here (store_tests.tests.StoreTests)"]}},
     "with the expert's fix a test that should start passing does not pass here"),
    (lambda given: {**given, "tests": {**TASK_TESTS, "fail_to_pass": ["test_load_of_nothing (store_tests.tests.StoreTests)"]}},
     "without the fix every test that should start passing passes here"),
    (lambda given: {**given, "fix": given["fix"].replace("+        self.rows.setdefault(db, []).append(name)", "+        self.rows.setdefault(db, []).append(name")},
     "the tests do not run here: with the expert's fix the run ended before its summary"),
])
def test_a_task_this_machine_cannot_judge_says_why_and_runs_no_candidate(project, tree, change, why):
    runs: list = []
    given = change({"test_patch": project["test_patch"], "fix": project["fix"], "tests": TASK_TESTS})
    row = measure.of_task(tree, project["clone"], project["commit"], given["test_patch"], given["fix"], given["tests"], [candidate(FIXED)], candidate(FIXED),
                          run=counting(runs))
    assert not row["judged"] and row["why_not"] == why
    assert row["candidates"] == [] and row["another_tasks_text"] is None and row["candidates_made"] == 1 and len(runs) <= 2


@needs_git
def test_a_run_with_the_fix_that_is_stopped_for_time_is_said(project, tree):
    def run(tree, labels, seconds):
        got = measure.run_tests(tree, labels, seconds)
        return {**got, "output": got["output"].split("Ran ")[0], "stopped": True}

    row = measure.of_task(tree, project["clone"], project["commit"], project["test_patch"], project["fix"], TASK_TESTS, [candidate(FIXED)], None, run=run)
    assert not row["judged"] and row["why_not"] == "the tests do not run here: with the expert's fix the run was stopped for time"
    assert row["with_the_fix"]["stopped"] and not row["with_the_fix"]["finished"]


@needs_git
def test_a_task_whose_test_patch_touches_no_test_module_is_run_on_the_modules_its_tests_name(project, tree):
    assert measure.touched(project["data_patch"]) == ["tests/store_tests/expected.txt"] and measure.labels_of(project["data_patch"]) == []
    row = measure.of_task(tree, project["clone"], project["commit"], project["data_patch"], project["fix"], DATA_TESTS, [candidate(STORE), candidate(FIXED)], None)
    assert row["judged"] and row["labels"] == ["store_tests.tests"] and row["as_it_stands"]["start_passing"] == 0
    assert [one["resolves"] for one in row["candidates"]] == [False, True]


ONE_MORE_MODULE = ("diff --git a/tests/store_tests/test_more.py b/tests/store_tests/test_more.py\nnew file mode 100644\n--- /dev/null\n+++ b/tests/store_tests/test_more.py\n"
                   "@@ -0,0 +1,6 @@\n+import unittest\n+\n+\n+class MoreTests(unittest.TestCase):\n+    def test_more(self):\n+        self.assertTrue(True)\n")


@needs_git
def test_every_module_the_test_patch_touches_is_run_whether_or_not_the_tasks_lists_name_a_test_of_it(project, tree):
    """Added after the round of seeded faults: with the labels always taken from the tests' names nothing failed."""
    patch = project["test_patch"] + ONE_MORE_MODULE
    row = measure.of_task(tree, project["clone"], project["commit"], patch, project["fix"], TASK_TESTS, [candidate(FIXED)], None)
    assert row["labels"] == ["store_tests.tests", "store_tests.test_more"] and measure.modules_named(FIRST + KEEP) == ["store_tests.tests"]
    assert row["judged"] and row["as_it_stands"]["ran"] == 6 and row["with_the_fix"]["ran"] == 6 and row["candidates"][0]["resolves"]


@needs_git
def test_a_test_that_fails_here_even_with_the_fix_is_not_held_against_a_candidate(project, tree):
    row = measure.of_task(tree, project["clone"], project["commit"], project["test_patch"], project["fix"], TASK_TESTS, [candidate(FIXED)], None)
    assert row["left_out"] == 1 and row["candidates"][0]["resolves"] and row["candidates"][0]["keep_wanted"] == 2


@needs_git
def test_a_candidate_that_hangs_is_stopped_and_does_not_resolve(project, tree, monkeypatch):
    monkeypatch.setattr(measure, "FEW_SECONDS", 6)
    hangs = STORE.replace("self.rows.setdefault('default', []).append(name)", "import time; time.sleep(60)")
    row = measure.of_task(tree, project["clone"], project["commit"], project["test_patch"], project["fix"], TASK_TESTS, [candidate(hangs), candidate(FIXED)], None)
    assert row["candidates"][0]["stopped"] and not row["candidates"][0]["resolves"] and not row["candidates"][0]["whole_run"]
    assert row["candidates"][1]["resolves"] and not row["candidates"][1]["stopped"]


# --------------------------------------------------------------------------- #
# the candidates the chain makes, and the whole way from text to verdict
# --------------------------------------------------------------------------- #
@needs_git
def test_the_candidates_of_a_task_are_whole_files_made_from_the_tree_and_the_text(project):
    made = measure.candidates_of(project["clone"], "a/b", [("a__b-1", project["commit"], TEXT, OTHER_TEXT)])["a__b-1"]
    assert made["candidates"] and all(one["path"] == "shop/store.py" for one in made["candidates"])
    assert made["candidates"][0] == {"path": "shop/store.py", "function": "Store.save", "text": FIXED}
    assert all(set(one) == {"path", "function", "text"} for one in made["candidates"])
    assert made["another_tasks_text"]["path"] == "shop/noise.py" and made["another_tasks_text"]["function"] == "noise"
    assert made["another_tasks_text"]["text"] == "def noise(database, wrong, writes):\n    return (database, wrong)\n"   # as the list writes a statement


@needs_git
def test_a_text_that_quotes_no_code_gives_no_candidate(project):
    made = measure.candidates_of(project["clone"], "a/b", [("a__b-1", project["commit"], "Store.save writes to the wrong database.", "nothing")])["a__b-1"]
    assert made == {"candidates": [], "another_tasks_text": None}


@needs_git
def test_from_the_tree_and_the_text_to_the_verdict_of_the_tests(project, tree):
    made = measure.candidates_of(project["clone"], "a/b", [("a__b-1", project["commit"], TEXT, OTHER_TEXT)])["a__b-1"]
    row = measure.of_task(tree, project["clone"], project["commit"], project["test_patch"], project["fix"], TASK_TESTS, made["candidates"], made["another_tasks_text"])
    assert row["judged"] and measure.first_resolving(row) == 1 and row["candidates_made"] == len(made["candidates"]) == len(row["candidates"])
    assert row["another_tasks_text"]["resolves"] is False
    summary = measure.summarise({"django__django-1": row}, {"django__django-1": 1})
    assert summary["one_submission__tasks"] == ["django__django-1"] and summary["recorded_places__standing"] == ["django__django-1"]
    assert summary["another_tasks_text__tasks_run"] == 1 and summary["another_tasks_text__tasks_resolved"] == 0


@needs_git
def test_every_file_of_the_listed_trees_is_there_after_the_fetch(project):
    report = measure.fetch_everything(project["clone"], [project["commit"], project["after"]])
    assert report["commits"] == 2 and report["files"] == 9 and report["fetched"] == 0 and report["still_missing"] == 0   # the two empty files are one


@needs_git
def test_a_clone_made_without_file_contents_has_them_after_the_fetch(project, tmp_path):
    _git(project["clone"], "config", "uploadpack.allowFilter", "true")
    _git(project["clone"], "config", "uploadpack.allowAnySHA1InWant", "true")
    clone = tmp_path / "without.git"
    subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none", f"file://{project['clone']}", str(clone)], check=True, capture_output=True)
    report = measure.fetch_everything(clone, [project["commit"]])
    assert report == {"commits": 1, "files": 7, "fetched": 7, "still_missing": 0, "seconds": report["seconds"]}
    report = measure.fetch_everything(clone, [project["commit"], project["after"]])
    assert (report["files"], report["fetched"], report["still_missing"]) == (9, 2, 0)
    assert measure.fetch_everything(clone, [project["commit"], project["after"]])["fetched"] == 0
    measure.at_commit(clone, tmp_path / "tree", project["after"])
    assert (tmp_path / "tree" / "shop" / "store.py").read_text() == FIXED


@needs_git
def test_what_a_fetch_does_not_bring_is_counted_as_still_missing(project, tmp_path, monkeypatch):
    """Added after the round of seeded faults: with the count of what is still missing set to nothing, nothing failed."""
    _git(project["clone"], "config", "uploadpack.allowFilter", "true")
    clone = tmp_path / "without.git"
    subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none", f"file://{project['clone']}", str(clone)], check=True, capture_output=True)
    real = measure._git
    monkeypatch.setattr(measure, "_git", lambda directory, *args, **more: None if "fetch" in args else real(directory, *args, **more))
    report = measure.fetch_everything(clone, [project["commit"]])
    assert (report["files"], report["fetched"], report["still_missing"]) == (7, 7, 7)


# --------------------------------------------------------------------------- #
# all of them
# --------------------------------------------------------------------------- #
def a_row(judged=True, version="4.2", resolving=(), made=3, other=None, why=None, left_out=0, keep=10, whole=(), stopped=(), broken=()) -> dict:
    """A task's row: `resolving` are the places whose candidate resolves, `whole` those that got the whole run."""
    candidates = [{"place": at, "path": "a.py", "function": "f", "resolves": at in resolving, "whole_run": at in resolving or at in whole,
                   **({"stopped": True} if at in stopped else {}), **({"does_not_parse": True} if at in broken else {})} for at in range(1, made + 1)] if judged else []
    return {"version": version, "judged": judged, "why_not": why, "candidates_made": made, "candidates": candidates, "left_out": left_out, "keep_passing": keep,
            "another_tasks_text": None if other is None or not judged else {"resolves": other}, "seconds": 2.0}


ROWS = {
    "django__django-1": a_row(resolving=(1, 3), other=False, left_out=2),
    "django__django-2": a_row(resolving=(2,), other=False, whole=(1,), version="3.0"),
    "django__django-3": a_row(made=2, other=True, stopped=(1,), broken=(2,)),
    "django__django-4": a_row(made=0, version="3.0"),
    "django__django-5": a_row(judged=False, why="the tests do not run here: with the expert's fix the run ended before its summary", version="1.11", left_out=59),
    "django__django-6": a_row(judged=False, why="the expert's fix did not go in", made=0),
    "django__django-7": a_row(judged=False, why="the expert's fix did not go in", made=0),
    "django__django-8": a_row(resolving=(1,), made=20),
}
RECORDED = {"django__django-1": 1, "django__django-2": 1, "django__django-5": 4, "django__django-8": 1, "django__django-99": 1}


def test_the_place_of_the_first_candidate_the_tests_accept():
    assert measure.first_resolving(ROWS["django__django-1"]) == 1 and measure.first_resolving(ROWS["django__django-2"]) == 2
    assert measure.first_resolving(ROWS["django__django-3"]) is None and measure.first_resolving({"candidates": []}) is None and measure.first_resolving({}) is None


def test_the_counts_of_what_this_machine_can_judge():
    summary = measure.summarise(ROWS, RECORDED)
    assert (summary["tasks"], summary["judged"], summary["judged__share_of_the_django_tasks"]) == (8, 5, 0.625)
    assert summary["not_judged__why"] == {"the expert's fix did not go in": 2, "the tests do not run here: with the expert's fix the run ended before its summary": 1}
    assert list(summary["not_judged__why"]) == ["the expert's fix did not go in", "the tests do not run here: with the expert's fix the run ended before its summary"]
    assert summary["tests_left_out__that_fail_here_even_with_the_fix"] == 2 and summary["tasks_with_a_test_left_out"] == 1   # the 59 of a task that is not judged are not among them
    assert summary["tests_that_should_keep_passing__in_the_judged_tasks"] == 50
    assert (summary["with_a_candidate"], summary["with_a_candidate_and_judged"]) == (5, 4)


def test_one_submission_is_the_first_candidate_and_within_twenty_is_the_first_that_resolves():
    summary = measure.summarise(ROWS, RECORDED)
    assert summary["one_submission__tasks"] == ["django__django-1", "django__django-8"] and summary["one_submission__tasks_resolved"] == 2
    assert summary["one_submission__share_of_the_judged_with_a_candidate"] == 0.5 and summary["one_submission__share_of_the_django_tasks"] == 0.25
    assert summary["within_twenty__tasks"] == {"django__django-1": 1, "django__django-2": 2, "django__django-8": 1} and summary["within_twenty__tasks_resolved"] == 3
    assert summary["within__tasks_resolved"] == {"1": 2, "5": 3, "10": 3, "20": 3}


def test_the_counts_of_the_candidates_that_were_run():
    summary = measure.summarise(ROWS, RECORDED)
    assert summary["candidates_run"] == 3 + 3 + 2 + 20 and summary["candidates_resolving"] == 2 + 1 + 0 + 1
    assert summary["candidates_passing_what_should_start_passing_and_breaking_what_should_keep_passing"] == 1
    assert summary["candidates_stopped_for_time"] == 1 and summary["candidates_that_do_not_parse"] == 1


def test_the_earlier_records_places_are_checked_one_by_one():
    summary = measure.summarise(ROWS, RECORDED)
    assert summary["recorded_places"] == {"django__django-1": 1, "django__django-2": 1, "django__django-5": 4, "django__django-8": 1}
    assert summary["recorded_places__standing"] == ["django__django-1", "django__django-8"]
    assert summary["recorded_places__not_resolving"] == ["django__django-2"] and summary["recorded_places__judged_and_not_resolving_at_the_recorded_place"] == 1
    assert summary["recorded_places__not_judged"] == ["django__django-5"] and summary["recorded_places__tasks_judged_of_the_seven"] == 3
    assert summary["within_twenty__tasks_not_in_the_earlier_record"] == [] and summary["within_twenty__resolved_and_not_in_the_earlier_record"] == 0
    fewer = measure.summarise(ROWS, {"django__django-1": 1})
    assert fewer["within_twenty__tasks_not_in_the_earlier_record"] == ["django__django-2", "django__django-8"]
    assert fewer["within_twenty__resolved_and_not_in_the_earlier_record"] == 2


def test_a_recorded_place_beyond_the_candidates_that_were_run_does_not_stand():
    summary = measure.summarise(ROWS, {"django__django-1": 9})
    assert summary["recorded_places__not_resolving"] == ["django__django-1"] and summary["recorded_places__standing"] == []
    summary = measure.summarise(ROWS, {"django__django-1": 3})
    assert summary["recorded_places__standing"] == ["django__django-1"]
    summary = measure.summarise(ROWS, {"django__django-1": 2})
    assert summary["recorded_places__not_resolving"] == ["django__django-1"]


def test_another_tasks_text_is_counted_where_it_was_run():
    summary = measure.summarise(ROWS, RECORDED)
    assert (summary["another_tasks_text__tasks_run"], summary["another_tasks_text__tasks_resolved"]) == (3, 1)


def test_the_counts_by_version_and_the_seconds():
    summary = measure.summarise(ROWS, RECORDED)
    assert list(summary["by_version"]) == ["1.11", "3.0", "4.2"]
    assert summary["by_version"]["3.0"] == {"tasks": 2, "judged": 2, "with_a_candidate_and_judged": 1, "one_submission": 0, "within_twenty": 1}
    assert summary["by_version"]["4.2"] == {"tasks": 5, "judged": 3, "with_a_candidate_and_judged": 3, "one_submission": 2, "within_twenty": 2}
    assert summary["by_version"]["1.11"] == {"tasks": 1, "judged": 0, "with_a_candidate_and_judged": 0, "one_submission": 0, "within_twenty": 0}
    assert summary["seconds_of_test_runs"] == 16.0


def test_no_task_adds_up_to_nothing():
    summary = measure.summarise({}, {})
    assert summary["tasks"] == 0 and summary["judged__share_of_the_django_tasks"] is None and summary["one_submission__share_of_the_judged_with_a_candidate"] is None
    assert summary["within__tasks_resolved"] == {"1": 0, "5": 0, "10": 0, "20": 0} and summary["one_submission__tasks"] == []


def test_the_expectations_are_the_ones_written_before_any_candidate_was_run():
    assert measure.EXPECTED == {
        "judged__share_of_the_django_tasks": [0.70, 0.98],
        "recorded_places__tasks_judged_of_the_seven": [6, 7],
        "recorded_places__judged_and_not_resolving_at_the_recorded_place": [0, 0],
        "one_submission__tasks_resolved": [4, 10],
        "within_twenty__tasks_resolved": [7, 20],
        "within_twenty__resolved_and_not_in_the_earlier_record": [0, 10],
        "another_tasks_text__tasks_resolved": [0, 0],
    }
    assert (measure.WHOLE_SECONDS, measure.FEW_SECONDS, measure.RANKS, measure.PROJECT) == (900, 300, (1, 5, 10, 20), "django__django")


def test_each_expectation_is_judged_with_both_ends_counted_in():
    summary = {"judged__share_of_the_django_tasks": 0.70, "recorded_places__tasks_judged_of_the_seven": 7, "recorded_places__judged_and_not_resolving_at_the_recorded_place": 1,
               "one_submission__tasks_resolved": 3, "within_twenty__tasks_resolved": 21, "within_twenty__resolved_and_not_in_the_earlier_record": 10}
    said = measure.held(summary)
    assert set(said) == set(measure.EXPECTED)
    assert {key: one["held"] for key, one in said.items()} == {
        "judged__share_of_the_django_tasks": True, "recorded_places__tasks_judged_of_the_seven": True, "recorded_places__judged_and_not_resolving_at_the_recorded_place": False,
        "one_submission__tasks_resolved": False, "within_twenty__tasks_resolved": False, "within_twenty__resolved_and_not_in_the_earlier_record": True,
        "another_tasks_text__tasks_resolved": False}
    assert said["another_tasks_text__tasks_resolved"] == {"expected": [0, 0], "found": None, "held": False}
    assert said["one_submission__tasks_resolved"] == {"expected": [4, 10], "found": 3, "held": False}


def counts(judged=0.9, failing=0, one=4, within=7, other=0) -> dict:
    return {"judged__share_of_the_django_tasks": judged, "recorded_places__judged_and_not_resolving_at_the_recorded_place": failing,
            "one_submission__tasks_resolved": one, "within_twenty__tasks_resolved": within, "another_tasks_text__tasks_resolved": other}


def test_the_rule_when_the_places_stand_and_a_chooser_could_gain():
    said = measure.rule(counts())
    assert len(said["verdict"]) == 2
    assert said["verdict"][0] == "the earlier record's places stand under the tasks' own tests, as far as this machine judges them"
    assert said["verdict"][1].startswith("one submission resolves 4 and the first twenty hold a resolving candidate for 7: choosing among candidates WITHOUT the hidden tests "
                                         "is worth at most 3 task(s) here")
    assert "WRITING" in said["next"]


def test_the_rule_when_the_first_twenty_resolve_no_more_than_the_first():
    said = measure.rule(counts(one=5, within=5))
    assert said["verdict"][1] == "one submission resolves 5 and the first twenty resolve no more: choosing is not what limits this chain; writing the change is"


def test_the_rule_says_when_the_earlier_record_counted_too_many():
    said = measure.rule(counts(failing=2))
    assert said["verdict"][0].startswith("the earlier record counted 2 task(s) too many")
    assert not any("stand under" in line for line in said["verdict"])


def test_the_rule_says_when_the_machine_judges_too_few_or_the_tests_accept_another_tasks_text():
    said = measure.rule(counts(judged=0.49, other=1))
    assert said["verdict"][0].startswith("this machine judges fewer than half of the tasks") and said["verdict"][1].startswith("a candidate made from another task's text passes")
    assert len(said["verdict"]) == 4
    assert len(measure.rule(counts(judged=0.5))["verdict"]) == 2
    assert measure.rule({})["verdict"][0].startswith("this machine judges fewer than half")


def test_the_recorded_places_are_the_django_tasks_with_a_place():
    record = {"per_task": {"django__django-1": {"place": 2}, "django__django-2": {"place": None}, "sympy__sympy-3": {"place": 1}, "django__django-4": {}}}
    assert measure.recorded_places(record) == {"django__django-1": 2}


def test_the_seven_places_of_the_earlier_record_are_the_ones_this_count_checks():
    assert measure.recorded_places(json.loads(measure.FILE_RECORD.read_text())) == {
        "django__django-11066": 1, "django__django-11163": 6, "django__django-12155": 1, "django__django-15368": 1, "django__django-15467": 2,
        "django__django-15814": 4, "django__django-16569": 1}


def test_the_code_that_is_hashed_is_there():
    hashed = measure.code_sha256()
    assert sorted(hashed) == ["canonical/runtime/file_the_task_text_points_at_v1.py", "canonical/runtime/function_the_task_text_points_at_v1.py",
                              "canonical/runtime/tests_as_the_judge_v1.py", "canonical/tools/candidate_under_the_tasks_tests_measure_v1.py"]
    for path, digest in hashed.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


# --------------------------------------------------------------------------- #
# the whole count, with the small project standing where Django's clone stands
# --------------------------------------------------------------------------- #
ONE, TWO = "django__django-16569", "django__django-16527"          # two of the 231, by name only: ONE is the task above, TWO names no test
PLAIN = "noise(database, wrong, writes) should not return writes."


def _statement(commit: str, text: str, tests: dict) -> str:
    def listed(names):
        return "".join(f"\n- {json.dumps(name)}" for name in names) or " []"
    return (f"base_commit: {commit}\nversion: '{tests['version']}'\nproblem_statement: {json.dumps(text)}\n"
            f"fail_to_pass:{listed(tests['fail_to_pass'])}\npass_to_pass:{listed(tests['pass_to_pass'])}\n")


@pytest.fixture()
def dataset(project, tmp_path):
    pytest.importorskip("yaml")
    root, pulls = tmp_path / "dataset", tmp_path / "pulls"
    (root / "problems" / "swe" / "swebench-verified").mkdir(parents=True)
    (root / "patches").mkdir()
    pulls.mkdir()
    hunk = project["fix"][project["fix"].index("@@"):]
    given = {ONE: (TEXT, TASK_TESTS, project["test_patch"]), TWO: (OTHER_TEXT, {**DATA_TESTS, "fail_to_pass": []}, project["data_patch"])}
    for task, (text, tests, patch) in given.items():
        (root / "problems" / "swe" / "swebench-verified" / f"{task}.yaml").write_text(_statement(project["commit"], text, tests))
        (root / "patches" / f"{task}_tests.patch").write_text(patch)
        (pulls / f"{task}.json").write_text(json.dumps({"files": [{"path": "shop/store.py", "status": "modified", "previous": None, "patch": hunk, "is_test": False}]}))
    return {"root": root, "pulls": pulls, "trees": project["clone"].parent, "work": tmp_path / "work", "out": tmp_path / "record.json", "commit": project["commit"]}


def count(dataset, *more: str) -> int:
    return measure.main(["--dataset-dir", str(dataset["root"]), "--pull-requests-dir", str(dataset["pulls"]), "--trees-dir", str(dataset["trees"]),
                         "--work-dir", str(dataset["work"]), "--out", str(dataset["out"]), *more])


def rows_of(dataset) -> list[dict]:
    return [json.loads(line) for line in (dataset["work"] / "rows.jsonl").read_text().splitlines()]


@needs_git
def test_the_whole_count_on_two_tasks(dataset):
    assert count(dataset) == 0
    record = json.loads(dataset["out"].read_text())
    assert record["schema"] == measure.SCHEMA and list(record["per_task"]) == [TWO, ONE] and record["python"] == sys.version.split()[0]
    one, two = record["per_task"][ONE], record["per_task"][TWO]
    assert one["judged"] and measure.first_resolving(one) == 1 and one["candidates_made"] == len(one["candidates"]) >= 1
    assert one["another_tasks_text"]["resolves"] is False and one["another_tasks_text"]["path"] == "shop/noise.py"
    assert not two["judged"] and two["why_not"] == "the task names no test that should start passing" and two["candidates"] == [] and two["candidates_made"] >= 1
    assert record["summary"] == measure.summarise(record["per_task"], measure.recorded_places(json.loads(measure.FILE_RECORD.read_text())))
    assert record["summary"]["one_submission__tasks"] == [ONE] and record["summary"]["judged"] == 1 and record["summary"]["recorded_places__standing"] == [ONE]
    assert record["expectations"] == measure.held(record["summary"]) and record["rule"] == measure.rule(record["summary"])
    assert record["expected"] == measure.EXPECTED and record["code_sha256"] == measure.code_sha256() and record["fetched"]["still_missing"] == 0
    assert sorted(row["task"] for row in rows_of(dataset)) == [TWO, ONE] and {row["task"]: row["row"] for row in rows_of(dataset)} == record["per_task"]


@needs_git
def test_the_tasks_that_have_candidates_are_judged_first(dataset):
    path = dataset["root"] / "problems" / "swe" / "swebench-verified" / f"{TWO}.yaml"
    path.write_text(_statement(dataset["commit"], PLAIN, DATA_TESTS))
    assert count(dataset, "--workers", "1") == 0
    assert [row["task"] for row in rows_of(dataset)] == [ONE, TWO]            # though TWO's number is the smaller
    record = json.loads(dataset["out"].read_text())
    assert record["per_task"][TWO]["judged"] and record["per_task"][TWO]["candidates_made"] == 0 and "few" not in record["per_task"][TWO]
    assert record["per_task"][ONE]["another_tasks_text"] is None              # the other task's text quotes no code: nothing to run
    assert record["summary"]["another_tasks_text__tasks_run"] == 0 and record["summary"]["judged"] == 2


@needs_git
def test_a_count_that_was_stopped_goes_on_from_the_tasks_it_had(dataset, capsys):
    assert count(dataset, "--only", ONE) == 0
    first = json.loads(dataset["out"].read_text())
    assert list(first["per_task"]) == [ONE] and [row["task"] for row in rows_of(dataset)] == [ONE]
    assert count(dataset) == 0
    assert "1 tasks already judged" in capsys.readouterr().out
    assert [row["task"] for row in rows_of(dataset)] == [ONE, TWO]
    assert json.loads(dataset["out"].read_text())["per_task"][ONE] == first["per_task"][ONE]


@needs_git
def test_with_no_candidates_only_the_judging_is_done(dataset):
    assert count(dataset, "--no-candidates", "--only", ONE, TWO) == 0
    record = json.loads(dataset["out"].read_text())
    assert record["per_task"][ONE]["judged"] and record["per_task"][ONE]["candidates_made"] == 0 and record["per_task"][ONE]["candidates"] == []
    assert record["summary"]["with_a_candidate"] == 0 and record["summary"]["candidates_run"] == 0


@needs_git
@pytest.mark.parametrize("broken", [{"error": "not found", "files": []},
                                    {"files": [{"path": "shop/store.py", "status": "modified", "patch": "@@ -1 +1 @@", "fetch_error": "HTTP 502"}]}])
def test_a_pull_request_record_that_is_not_whole_is_refused(dataset, broken):
    (dataset["pulls"] / f"{ONE}.json").write_text(json.dumps(broken))
    assert count(dataset) == 2
    assert not dataset["out"].exists() and not (dataset["work"] / "rows.jsonl").exists()


@needs_git
def test_the_tasks_of_the_record_stand_in_the_order_of_their_numbers(project, dataset):
    """Added after the round of seeded faults: with the tasks in the order of their names, 10097 before 7530, nothing failed."""
    early = "django__django-7530"
    hunk = project["fix"][project["fix"].index("@@"):]
    (dataset["root"] / "problems" / "swe" / "swebench-verified" / f"{early}.yaml").write_text(_statement(project["commit"], TEXT, TASK_TESTS))
    (dataset["root"] / "patches" / f"{early}_tests.patch").write_text(project["test_patch"])
    (dataset["pulls"] / f"{early}.json").write_text(json.dumps({"files": [{"path": "shop/store.py", "status": "modified", "previous": None, "patch": hunk, "is_test": False}]}))
    assert count(dataset, "--no-candidates") == 0
    assert list(json.loads(dataset["out"].read_text())["per_task"]) == [early, TWO, ONE] and sorted([early, TWO, ONE]) == [TWO, ONE, early]


@needs_git
def test_trees_that_did_not_come_whole_are_refused(dataset, monkeypatch):
    real = measure.fetch_everything
    monkeypatch.setattr(measure, "fetch_everything", lambda clone, commits: {**real(clone, commits), "still_missing": 3})
    assert count(dataset) == 2
    assert not dataset["out"].exists() and not (dataset["work"] / "rows.jsonl").exists()


@needs_git
def test_a_task_that_cannot_be_set_up_is_said_and_the_count_goes_on(dataset, monkeypatch):
    real = measure.of_task

    def failing(tree, clone, commit, test_patch, fix, tests, candidates, other, run=measure.run_tests):
        if not tests["fail_to_pass"]:
            raise RuntimeError("no room on the disk")
        return real(tree, clone, commit, test_patch, fix, tests, candidates, other, run)

    monkeypatch.setattr(measure, "of_task", failing)
    assert count(dataset) == 0
    record = json.loads(dataset["out"].read_text())
    assert record["per_task"][TWO]["why_not"] == "could not be set up: RuntimeError: no room on the disk" and not record["per_task"][TWO]["judged"]
    assert record["per_task"][TWO]["candidates"] == [] and record["per_task"][TWO]["version"] == "4.2"
    assert record["per_task"][ONE]["judged"] and record["summary"]["not_judged__why"] == {"could not be set up: RuntimeError: no room on the disk": 1}


# --------------------------------------------------------------------------- #
# the record in the tree
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def written():
    if not RECORD.exists():
        pytest.skip("the record is not in this tree")
    return json.loads(RECORD.read_text())


def test_the_record_was_made_by_the_code_in_the_tree(written):
    assert written["code_sha256"] == measure.code_sha256()


def test_the_record_holds_the_231_django_tasks_and_no_model_call(written):
    assert len(written["per_task"]) == 231 and all(task.startswith("django__django-") for task in written["per_task"])
    assert written["summary"]["tasks"] == 231 and written["model_calls"] == 0 and written["schema"] == measure.SCHEMA


def test_the_summary_of_the_record_adds_up_from_its_rows(written):
    assert written["summary"] == measure.summarise(written["per_task"], measure.recorded_places(json.loads(measure.FILE_RECORD.read_text())))


def test_the_expectations_and_the_rule_in_the_record_are_the_tools(written):
    assert written["expected"] == measure.EXPECTED
    assert written["expectations"] == measure.held(written["summary"]) and written["rule"] == measure.rule(written["summary"])


def test_every_judged_task_of_the_record_passes_with_the_fix_and_not_without(written):
    for task, row in written["per_task"].items():
        if row["judged"]:
            assert row["why_not"] is None and row["with_the_fix"]["finished"], task
            assert row["with_the_fix"]["start_passing"] == row["start_passing"] > row["as_it_stands"]["start_passing"], task
        else:
            assert row["why_not"] and row["candidates"] == [] and row["another_tasks_text"] is None, task


def test_every_candidate_of_the_record_stands_in_its_place_and_a_resolving_one_passed_the_whole_run(written):
    for task, row in written["per_task"].items():
        assert [one["place"] for one in row["candidates"]] == list(range(1, len(row["candidates"]) + 1)), task
        assert len(row["candidates"]) in (0, row["candidates_made"]) and len(row["candidates"]) <= 20, task
        for one in row["candidates"]:
            if one["resolves"]:
                assert one["whole_run"] and one["start_passing"] == row["start_passing"] and one["keep_passing"] == one["keep_wanted"], task
            elif one["whole_run"]:
                assert one["start_passing"] < row["start_passing"] or one["keep_passing"] < one["keep_wanted"], task


def test_the_record_names_the_commit_that_held_the_expectations_before_any_candidate_was_run(written):
    pushed = written["pushed_before_any_candidate_was_run"]
    assert len(pushed["commit"]) == 40 and set(pushed["commit"]) <= set("0123456789abcdef")
    assert pushed["code_sha256"] == written["code_sha256"]             # the code that ran is the code that was pushed, and is the code in the tree


# --------------------------------------------------------------------------- #
# the round of seeded faults (canonical/tools/seeded_faults_tests_as_the_judge_v1.py)
# --------------------------------------------------------------------------- #
def test_the_seeded_faults_are_each_one_piece_of_text_that_stands_once():
    from canonical.tools import seeded_faults_tests_as_the_judge_v1 as seeded
    assert len(seeded.FAULTS) == len({what for what, _, _, _ in seeded.FAULTS}) >= 80
    for what, name, old, new in seeded.FAULTS:
        assert name in (seeded.ORGAN, seeded.MEASURE) and old != new, what
        assert (ROOT / name).read_text(encoding="utf-8").count(old) == 1, what


def test_the_round_leaves_the_other_rounds_lists_as_they_were():
    from canonical.tools import seeded_faults_function_found_v1 as base
    from canonical.tools import seeded_faults_tests_as_the_judge_v1 as seeded
    before = (base.TESTS, base.LEFT_OUT, base.RECORDS, base.FAULTS)
    seen = []
    kept, base.main = base.main, lambda argv=None: seen.append((base.TESTS, base.LEFT_OUT, base.RECORDS, base.FAULTS)) or 0
    try:
        assert seeded.main([]) == 0
    finally:
        base.main = kept
    assert seen == [(seeded.TESTS, seeded.LEFT_OUT, seeded.RECORDS, seeded.FAULTS)]
    assert (base.TESTS, base.LEFT_OUT, base.RECORDS, base.FAULTS) == before and len(base.FAULTS) == 34


def test_the_tests_left_out_of_the_round_are_tests_of_these_files():
    from canonical.tools import seeded_faults_tests_as_the_judge_v1 as seeded
    for name in seeded.LEFT_OUT:
        path, _, test = name.partition("::")
        assert path in seeded.TESTS and f"def {test}(" in (ROOT / path).read_text(encoding="utf-8"), name


def test_the_record_says_how_many_seeded_faults_the_tests_caught(written):
    from canonical.tools import seeded_faults_tests_as_the_judge_v1 as seeded
    found = written["seeded_faults"]
    last = found["rounds"][-1]
    assert last["seeded"] == len(seeded.FAULTS) and last["not_seeded"] == []
    assert last["caught"] + len(last["survived"]) == last["seeded"]
    assert [row["fault"] for row in last["rows"]] == [what for what, _, _, _ in seeded.FAULTS]
    assert sorted(row["fault"] for row in last["rows"] if not row["caught"]) == sorted(last["survived"])
    assert last["left_out_of_the_run"] == list(seeded.LEFT_OUT)
