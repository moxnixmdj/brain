#!/usr/bin/env python3
"""Whether the task text finds the file in the project's tree: how a tree is listed and read, what
is counted for a task, how the counts are added up, the rule, and that the record in the tree adds
up from its rows."""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import file_the_task_text_points_at_v1 as finder  # noqa: E402
from canonical.tools import file_found_from_task_text_measure_v1 as measure  # noqa: E402
from canonical.tools import passing_patch_shape_measure_v1 as passing  # noqa: E402

RECORD = ROOT / "canonical" / "verification" / "FILE_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json"
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not here")

STORE = '''import os

LIMIT = 3


def unrelated(a, b):
    c = a
    return c


class Store:
    def save(self, content_type, db):
        content_type.save(update_fields={'model'})
        return db

    def load(self, a):
        return a


def third(z):
    return z
'''
NOISE = "def noise(database, wrong, writes):\n    return database, wrong, writes, database, wrong, writes\n"
A_TEST = "def test_store_save_writes_to_the_wrong_database(store, content_type, db):\n    assert store.save(content_type, db) is db\n"
TREE = {
    "pkg/store.py": STORE,
    "pkg/noise.py": NOISE,
    "pkg/util/helpers.py": "def helper(x):\n    return x + 1\n",
    "pkg/__init__.py": "VERSION = 1\n",
    "setup.py": "from setuptools import setup\nsetup()\n",
    "tests/test_store.py": A_TEST,
    "docs/store.txt": "Store.save writes to the database\n",
}
TEXT = "Store.save() writes to the wrong database.\n```\ncontent_type.save(using=db, update_fields={'model'})\n```\n"
OTHER = "helper(x) should add 2, see helpers."
NAMES_ANOTHER = TEXT + "\nIt started in pkg/noise.py.\n"


def diff(path: str, hunks: str) -> str:
    return f"diff --git a/{path} b/{path}\nindex 83a4f00..5f3a362 100644\n--- a/{path}\n+++ b/{path}\n{hunks}\n"


IN_SAVE = diff("pkg/store.py", "@@ -11,4 +11,4 @@\n class Store:\n     def save(self, content_type, db):\n-        content_type.save(update_fields={'model'})\n"
                               "+        content_type.save(using=db, update_fields={'model'})\n         return db")
IN_SAVE_OTHERWISE = diff("pkg/store.py", "@@ -11,4 +11,5 @@\n class Store:\n     def save(self, content_type, db):\n-        content_type.save(update_fields={'model'})\n"
                                         "+        with atomic(db):\n+            content_type.save(update_fields={'model'})\n         return db")
IN_UNRELATED = diff("pkg/store.py", "@@ -6,3 +6,3 @@\n def unrelated(a, b):\n-    c = a\n+    c = abs(a)\n     return c")
AT_THE_TOP = diff("pkg/store.py", "@@ -2,3 +2,3 @@\n \n-LIMIT = 3\n+LIMIT = 4\n ")


def record(task: str = "a__b-1") -> dict:
    return {"instance_id": task, "repo": "a/b",
            "files": [{"path": "pkg/store.py", "status": "modified", "before": STORE, "is_test": False, "is_python": True, "patch": ""}]}


def documents(tree=TREE, tests_too=False):
    return {path: finder.document(path, source) for path, source in tree.items() if path.endswith(".py") and (tests_too or not path.startswith("tests/"))}


def one(diffs, text=TEXT, other=OTHER, tree=TREE):
    return measure.of_task(documents(tree), tree.__getitem__, record(), diffs, text, other)


def _git(directory, *args):
    done = subprocess.run(["git", "-C", str(directory), "-c", "user.name=t", "-c", "user.email=t@example.org", *args], capture_output=True, text=True, check=True)
    return done.stdout.strip()


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    """A project with two commits: the tree above, then the same with one more file and the test changed."""
    directory = tmp_path_factory.mktemp("project")
    _git(directory, "init", "-q")
    for path, source in TREE.items():
        (directory / path).parent.mkdir(parents=True, exist_ok=True)
        (directory / path).write_text(source)
    _git(directory, "add", "-A")
    _git(directory, "commit", "-q", "-m", "first")
    first = _git(directory, "rev-parse", "HEAD")
    (directory / "pkg" / "later.py").write_text("def later():\n    return 1\n")
    (directory / "tests" / "test_store.py").write_text(A_TEST + "\n\ndef test_more():\n    pass\n")
    _git(directory, "add", "-A")
    _git(directory, "commit", "-q", "-m", "second")
    return directory, first, _git(directory, "rev-parse", "HEAD")


# --------------------------------------------------------------------------- #
# a task's name and its base commit
# --------------------------------------------------------------------------- #
def test_the_project_and_the_repository_of_a_task():
    assert measure.project_of("scikit-learn__scikit-learn-11578") == "scikit-learn__scikit-learn"
    assert measure.repository_of("scikit-learn__scikit-learn-11578") == "scikit-learn/scikit-learn"
    assert measure.project_of("django__django-11066") == "django__django" and measure.repository_of("django__django-11066") == "django/django"


def test_the_base_commit_is_read_from_the_statement(tmp_path):
    (tmp_path / "a__b-1.yaml").write_text("instance_id: a__b-1\nbase_commit: " + "0a" * 20 + "\nproblem_statement: |\n  base_commit: nothing\n")
    (tmp_path / "a__b-2.yaml").write_text("base_commit: '" + "1b" * 20 + "'\n")
    (tmp_path / "a__b-3.yaml").write_text("instance_id: a__b-3\n")
    assert measure.base_commits(tmp_path, ["a__b-1", "a__b-2", "a__b-3", "a__b-4"]) == {"a__b-1": "0a" * 20, "a__b-2": "1b" * 20}


# --------------------------------------------------------------------------- #
# a tree, listed and read
# --------------------------------------------------------------------------- #
@needs_git
def test_the_listing_is_the_python_files_outside_the_tests_of_that_commit(project):
    directory, first, second = project
    assert [path for path, _ in measure.listing(directory, "a/b", first)] == ["pkg/__init__.py", "pkg/noise.py", "pkg/store.py", "pkg/util/helpers.py", "setup.py"]
    assert [path for path, _ in measure.listing(directory, "a/b", second)] == ["pkg/__init__.py", "pkg/later.py", "pkg/noise.py", "pkg/store.py", "pkg/util/helpers.py", "setup.py"]


@needs_git
def test_with_the_tests_too_the_listing_is_every_python_file(project):
    directory, first, _ = project
    found = [path for path, _ in measure.listing(directory, "a/b", first, tests_too=True)]
    assert "tests/test_store.py" in found and "docs/store.txt" not in found and len(found) == 6


@needs_git
def test_in_pytest_the_tests_are_the_files_under_testing(project):
    directory, first, _ = project
    assert "tests/test_store.py" in [path for path, _ in measure.listing(directory, "pytest-dev/pytest", first)]


@needs_git
def test_a_file_that_did_not_change_keeps_its_name_and_a_changed_one_does_not(project):
    directory, first, second = project
    before, after = dict(measure.listing(directory, "a/b", first, tests_too=True)), dict(measure.listing(directory, "a/b", second, tests_too=True))
    assert before["pkg/store.py"] == after["pkg/store.py"] and before["tests/test_store.py"] != after["tests/test_store.py"]


@needs_git
def test_the_contents_are_read_by_name_and_an_unknown_name_reads_as_nothing(project):
    directory, first, _ = project
    names = dict(measure.listing(directory, "a/b", first))
    contents = measure.Contents(directory)
    try:
        assert contents.read(names["pkg/store.py"]) == STORE
        assert contents.read("0" * 40) == ""
        assert contents.read(names["pkg/noise.py"]) == NOISE and contents.read(names["pkg/store.py"]) == STORE
    finally:
        contents.close()


@needs_git
def test_a_stretch_of_tasks_is_counted_from_the_trees_of_their_commits(project):
    directory, first, second = project
    jobs = [("a__b-1", first, record("a__b-1"), [IN_SAVE], TEXT, OTHER), ("a__b-2", second, record("a__b-2"), [IN_SAVE], NAMES_ANOTHER, OTHER)]
    found = measure.of_chunk((str(directory), "a/b", jobs, False))
    assert found["a__b-1"] == one([IN_SAVE]) and found["a__b-1"]["files"] == 5 and found["a__b-1"]["place"] == 1
    assert found["a__b-2"]["files"] == 6 and found["a__b-2"]["expert"] == 2 and found["a__b-2"]["place"] is None and found["a__b-2"]["place_three"] == 1
    assert found["a__b-1"]["same_text"] and found["a__b-2"]["same_text"]


@needs_git
def test_with_the_tests_too_a_test_can_stand_before_the_file(project):
    directory, first, _ = project
    text = "test_store_save_writes_to_the_wrong_database fails: store.save(content_type, db) is not db"
    without = measure.of_chunk((str(directory), "a/b", [("a__b-1", first, record(), [IN_SAVE], text, OTHER)], False))["a__b-1"]
    with_tests = measure.of_chunk((str(directory), "a/b", [("a__b-1", first, record(), [IN_SAVE], text, OTHER)], True))["a__b-1"]
    assert without["files"] == 5 and with_tests["files"] == 6
    assert without["expert"] == 1 and with_tests["expert"] == 2


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #
def test_the_functions_that_hold_a_passing_patch_and_their_texts_after_it():
    found = measure.targets_of(record(), [IN_SAVE, IN_SAVE_OTHERWISE, IN_UNRELATED, AT_THE_TOP, "not a patch"])
    assert set(found) == {("pkg/store.py", (12, 14)), ("pkg/store.py", (6, 8))}
    assert len(found[("pkg/store.py", (12, 14))]) == 2 and len(found[("pkg/store.py", (6, 8))]) == 1


def test_a_patch_outside_every_function_gives_no_target():
    assert measure.targets_of(record(), [AT_THE_TOP]) == {}
    assert measure.targets_of(record(), []) == {}


def test_the_rank_of_the_first_wanted_file():
    assert measure.rank_of(["a.py", "b.py", "c.py"], {"c.py", "b.py"}) == 2
    assert measure.rank_of(["a.py", "b.py"], {"a.py"}) == 1
    assert measure.rank_of(["a.py", "b.py"], {"z.py"}) is None and measure.rank_of([], {"a.py"}) is None and measure.rank_of(["a.py"], set()) is None


def test_the_place_of_the_first_candidate_that_is_a_passing_text():
    from canonical.runtime import function_the_task_text_points_at_v1 as pointer
    save, other = pointer.Function(12, 14, "Store.save"), pointer.Function(6, 8, "unrelated")
    targets = {("pkg/store.py", (12, 14)): {"good"}}
    assert measure.place_of([("pkg/store.py", save, "bad"), ("pkg/store.py", save, "good")], targets) == 2
    assert measure.place_of([("pkg/store.py", other, "good"), ("pkg/noise.py", save, "good")], targets) is None      # the right text in the wrong place is not it
    assert measure.place_of([], targets) is None and measure.place_of([("pkg/store.py", save, "good")], {}) is None


def test_a_task_whose_text_points_at_the_file_and_quotes_the_line():
    row = one([IN_SAVE])
    assert row["files"] == 5 and (row["expert"], row["expert_by_score"], row["passing"]) == (1, 1, 1)
    assert (row["function"], row["place"], row["place_three"]) == (1, 1, 1)
    assert row["expert_named"] == finder.NOT_NAMED and row["same_text"] is True


def test_another_tasks_text_finds_neither_the_file_nor_the_patch():
    row = one([IN_SAVE])
    assert row["expert_other_text"] > 1 and row["place_other_text"] is None


def test_a_text_that_names_another_file_loses_the_patch_with_one_file_and_keeps_it_with_three():
    row = one([IN_SAVE], text=NAMES_ANOTHER)
    assert (row["expert"], row["expert_by_score"]) == (2, 1)
    assert row["function"] is None and row["place"] is None and row["place_three"] == 1


def test_a_text_that_names_the_file_says_how():
    assert one([IN_SAVE], text=TEXT + "\nsee pkg/store.py\n")["expert_named"] == finder.WRITTEN_OUT
    assert one([IN_SAVE], text=TEXT + "\nsee store.py\n")["expert_named"] == finder.FILE_NAME_ONLY


def test_a_passing_patch_the_list_does_not_write_is_found_but_not_reached():
    row = one([IN_SAVE_OTHERWISE])
    assert (row["passing"], row["function"]) == (1, 1) and row["place"] is None and row["place_three"] is None


def test_the_place_of_the_function_is_its_rank_among_the_functions_of_the_first_file():
    row = one([IN_UNRELATED])
    assert row["passing"] == 1 and row["function"] > 1 and row["place"] is None


def test_a_task_without_a_passing_patch_inside_a_function_still_has_the_rank_of_its_file():
    for diffs in ([], [AT_THE_TOP]):
        row = one(diffs)
        assert row["expert"] == 1 and row["passing"] is None and row["function"] is None and row["place"] is None


def test_an_expert_file_that_is_not_in_the_tree_has_no_rank():
    tree = {path: source for path, source in TREE.items() if path != "pkg/store.py"}
    row = measure.of_task(documents(tree), tree.__getitem__, record(), [IN_SAVE], TEXT, OTHER)
    assert row["expert"] is None and row["passing"] is None and row["expert_named"] is None and row["place"] is None


def test_a_tree_whose_file_is_not_the_text_the_collector_read_is_said():
    tree = dict(TREE)
    tree["pkg/store.py"] = STORE + "\n# changed since\n"
    assert measure.of_task(documents(tree), tree.__getitem__, record(), [IN_SAVE], TEXT, OTHER)["same_text"] is False


# --------------------------------------------------------------------------- #
# added up
# --------------------------------------------------------------------------- #
def row(expert=1, by_score=1, other=None, named=0, passing=None, function=None, place=None, three=None, place_other=None, files=10, same=True):
    return {"files": files, "expert": expert, "expert_by_score": by_score, "expert_other_text": other, "expert_named": named, "passing": passing,
            "function": function, "place": place, "place_three": three, "place_other_text": place_other, "same_text": same}


PER_TASK = {
    "a__b-1": row(expert=1, by_score=2, other=7, named=2, passing=1, function=1, place=3, three=3, files=10),
    "a__b-2": row(expert=3, by_score=1, other=1, named=0, passing=3, three=5, files=20),
    "a__b-3": row(expert=11, by_score=10, other=None, named=1, passing=None, files=30),
    "c__d-1": row(expert=None, by_score=None, other=None, named=None, passing=None, files=40, same=False),
    "c__d-2": row(expert=1, by_score=1, other=2, named=0, passing=1, function=5, files=50),
}


def test_the_counts_of_the_file():
    found = measure.summarise(PER_TASK, [], [])
    assert found["tasks"] == 5 and found["tasks_with_an_expert_file_in_the_tree"] == 4 and found["median_python_files_outside_the_tests"] == 30
    assert found["expert_file_among_the_first__organ"] == {"1": 2, "3": 3, "10": 3}
    assert found["expert_file_among_the_first__score_alone"] == {"1": 2, "3": 3, "10": 4}
    assert found["expert_file_among_the_first__another_tasks_text"] == {"1": 1, "3": 2, "10": 3}
    assert found["expert_file_among_the_first__organ__share"] == {"1": 0.4, "3": 0.6, "10": 0.6}
    assert found["tasks_whose_text_names_an_expert_file"] == 2 and found["tasks_whose_text_names_an_expert_file__share"] == 0.4
    assert found["expert_files_whose_text_in_the_tree_is_not_what_the_collector_read__tasks"] == 1


def test_the_counts_by_how_the_text_names_the_file_and_by_project():
    found = measure.summarise(PER_TASK, [], [])
    naming = found["by_how_the_text_names_the_file"]
    assert naming["written out with a directory or a module path"] == {"tasks": 1, "first_in_the_order_of_the_organ": 1, "first_by_score_alone": 0}
    assert naming["the file name alone"] == {"tasks": 1, "first_in_the_order_of_the_organ": 0, "first_by_score_alone": 0}
    assert naming["not named"] == {"tasks": 2, "first_in_the_order_of_the_organ": 1, "first_by_score_alone": 2}
    assert found["by_project"] == {"a__b": {"tasks": 3, "first": 1, "among_the_first_3": 2, "among_the_first_10": 2},
                                   "c__d": {"tasks": 2, "first": 1, "among_the_first_3": 1, "among_the_first_10": 1}}


def test_the_counts_of_the_chain():
    found = measure.summarise(PER_TASK, ["a__b-1", "a__b-2", "z__z-9"], ["c__d-2", "a__b-2", "z__z-9"])
    assert found["tasks_with_a_passing_patch_inside_one_function"] == 3
    assert found["file_holding_such_a_patch_among_the_first__organ"] == {"1": 2, "3": 3, "10": 3}
    assert found["function_holding_such_a_patch_among_the_first_of_the_first_file"] == {"1": 1, "4": 1, "10": 2}
    assert found["chain__tasks_reached_from_the_tree__all_20_in_the_first_file"] == 1 and found["chain__which"] == ["a__b-1"]
    assert found["chain__tasks_reached__functions_of_the_first_3_files_together"] == 2 and found["chain__which_three"] == ["a__b-1", "a__b-2"]
    assert found["chain__tasks_reached_with_another_tasks_text"] == 0
    assert (found["reached_with_the_file_given"], found["of_them_reached_from_the_tree"], found["of_them_reached_from_the_tree__three_files"]) == (2, 1, 2)
    assert found["reached_from_the_tree_only"] == 0
    assert found["earlier_lists__tasks_kept_with_the_file_given"] == 2 and found["earlier_lists__which"] == ["c__d-2"]
    assert found["of_the_500_from_the_tree_and_the_text_alone"] == 2


def test_a_task_reached_only_from_the_tree_is_counted_as_such():
    assert measure.summarise(PER_TASK, [], [])["reached_from_the_tree_only"] == 1
    reached_by_another_text = dict(PER_TASK, **{"a__b-3": row(place_other=4)})
    assert measure.summarise(reached_by_another_text, [], [])["chain__tasks_reached_with_another_tasks_text"] == 1


def test_no_task_adds_up_to_nothing():
    found = measure.summarise({}, [], [])
    assert found["tasks"] == 0 and found["expert_file_among_the_first__organ__share"] == {"1": None, "3": None, "10": None}
    assert found["median_python_files_outside_the_tests"] is None


# --------------------------------------------------------------------------- #
# the rule and the earlier lists
# --------------------------------------------------------------------------- #
def summary(kept, of=10, three=0, share=0.3):
    return {"of_them_reached_from_the_tree": kept, "reached_with_the_file_given": of, "of_them_reached_from_the_tree__three_files": three,
            "expert_file_among_the_first__score_alone__share": {"1": share}}


@pytest.mark.parametrize("kept, verdict", [(10, "stands"), (7, "stands"), (6, "undecided"), (4, "undecided"), (3, "limiting"), (0, "limiting")])
def test_the_rule_reads_how_many_of_the_tasks_reached_with_the_file_given_are_still_reached(kept, verdict):
    assert verdict in measure.rule(summary(kept))["verdict"]
    assert measure.rule(summary(kept))["of_them_reached_from_the_tree"] == kept


@pytest.mark.parametrize("share, agrees", [(0.22, True), (0.394, True), (0.50, True), (0.21, False), (0.51, False), (None, False)])
def test_the_rule_says_whether_score_alone_agrees_with_what_others_measured(share, agrees):
    assert measure.rule(summary(8, share=share))["score_alone_agrees_with_what_others_measured"] is agrees


def test_the_thresholds_of_the_rule_are_the_ones_written_before_counting():
    text = measure.EXPECTED["rule"]
    assert "at least 7 of the 10" in text and "3 or fewer" in text and "undecided" in text


def test_the_earlier_lists_keep_a_task_whose_small_functions_all_stand_first():
    place_record = {"per_task": {"t-1": [0, 0, 5], "t-2": [0, 0, 181], "t-3": [0, 0, None], "t-4": [0, 0, 9], "t-5": [0, 0, 180], "t-6": [0, 0, 1], "t-7": [0, 0, 2]}}
    function_record = {"per_task": {
        "t-1": {"functions": [{"rank": 1, "small": True}, {"rank": 7, "small": False}]},
        "t-2": {"functions": [{"rank": 1, "small": True}]},
        "t-3": {"functions": [{"rank": 1, "small": True}]},
        "t-4": {"functions": [{"rank": 2, "small": True}]},
        "t-5": {"functions": [{"rank": 1, "small": True}, {"rank": 1, "small": True}]},
        "t-6": {"functions": [{"rank": 1, "small": False}]},
    }}
    assert measure.earlier_kept(function_record, place_record) == ["t-1", "t-5"]


def test_the_code_that_is_hashed_is_there():
    found = measure.code_sha256()
    assert len(found) == 8 and all(len(value) == 64 for value in found.values())
    assert "canonical/runtime/file_the_task_text_points_at_v1.py" in found and "canonical/tools/file_found_from_task_text_measure_v1.py" in found


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


def test_the_record_holds_the_500_tasks_and_every_one_has_its_expert_file_in_the_tree(written):
    tasks = sorted(json.loads(measure.place.PASSING_RECORD.read_text())["per_task"])
    assert sorted(written["per_task"]) == tasks and len(tasks) == 500
    assert written["summary"]["tasks"] == 500 and written["summary"]["tasks_with_an_expert_file_in_the_tree"] == 500
    assert written["summary"]["expert_files_whose_text_in_the_tree_is_not_what_the_collector_read__tasks"] == 0


def test_the_summary_of_the_record_adds_up_from_its_rows(written):
    function_record = json.loads(measure.FUNCTION_RECORD.read_text())
    reached = sorted(task for task, found in function_record["per_task"].items() if found["file_given"] is not None)
    again = measure.summarise(written["per_task"], reached, measure.earlier_kept(function_record, json.loads(measure.PLACE_RECORD.read_text())))
    assert again == written["summary"]
    assert measure.rule(again) == written["rule"]


def test_the_expectations_in_the_record_are_the_ones_in_the_tool(written):
    assert written["expected_before"] == measure.EXPECTED


def test_the_record_ran_no_model_and_none_of_the_tasks_programs_or_tests(written):
    assert (written["model_calls"], written["task_programs_run"], written["task_tests_run"]) == (0, 0, 0)
    assert written["files_ranked"] == "the Python files of the tree outside the tests"


def found_for(written):
    """Each range written before counting, with the number the record's summary holds for it."""
    summary = written["summary"]
    return {
        "share of the 500 tasks with a file the expert changed first, by score alone": summary["expert_file_among_the_first__score_alone__share"]["1"],
        "the same in the order of the organ, which puts the files the text names first": summary["expert_file_among_the_first__organ__share"]["1"],
        "share with such a file among the first 3, organ": summary["expert_file_among_the_first__organ__share"]["3"],
        "share with such a file among the first 10, organ": summary["expert_file_among_the_first__organ__share"]["10"],
        "share with such a file first, another task's text, organ": summary["expert_file_among_the_first__another_tasks_text__share"]["1"],
        "share of the tasks whose text names a file the expert changed": summary["tasks_whose_text_names_an_expert_file__share"],
        "median number of Python files outside the tests": summary["median_python_files_outside_the_tests"],
        "of the 10 tasks reached with the file given, those reached from the tree, all 20 candidates in the first file": summary["of_them_reached_from_the_tree"],
        "the same with the functions of the first 3 files ranked together": summary["of_them_reached_from_the_tree__three_files"],
        "tasks reached from the tree with another task's text": summary["chain__tasks_reached_with_another_tasks_text"],
    }


def test_every_expectation_is_judged_in_the_record_as_the_numbers_say(written):
    found = found_for(written)
    ranges = {key: value for key, value in measure.EXPECTED.items() if isinstance(value, list)}
    assert set(found) == set(ranges)
    judged = {one["what"]: one for one in written["judged"]}
    assert set(judged) == set(ranges)
    for what, (low, high) in ranges.items():
        assert judged[what]["found"] == found[what] and judged[what]["expected"] == [low, high]
        assert judged[what]["held"] is (low <= found[what] <= high)
    assert written["read_this_first"]["expectations_held"] == f"{sum(one['held'] for one in written['judged'])} of {len(ranges)}"


def test_the_two_earlier_counts_are_kept_with_what_was_wrong_with_their_input(written):
    earlier = written["earlier_counts"]
    first, second = earlier["the_first"], earlier["the_second"]
    assert first["tasks_with_an_expert_file_in_the_tree"] == 496 and len(first["tasks_whose_records_were_not_fetched_whole"]) == 4
    assert set(first["tasks_whose_records_were_not_fetched_whole"]) <= set(first["rows_that_differ_from_this_count"])
    assert (first["submissions_with_patches"], second["submissions_with_patches"], written["submissions_with_patches"]) == (51, 51, 73)
    assert second["tasks_with_an_expert_file_in_the_tree"] == 500
    assert second["expert_file_among_the_first__organ"] == written["summary"]["expert_file_among_the_first__organ"]
    assert second["expert_file_among_the_first__score_alone"] == written["summary"]["expert_file_among_the_first__score_alone"]
    for one in (first, second):
        assert one["of_them_reached_from_the_tree"] == written["summary"]["of_them_reached_from_the_tree"]
        assert one["of_the_500_from_the_tree_and_the_text_alone"] == written["summary"]["of_the_500_from_the_tree_and_the_text_alone"]


def test_the_record_was_counted_from_as_many_submissions_as_the_record_it_is_compared_with(written):
    assert written["submissions_with_patches"] == json.loads(measure.FUNCTION_RECORD.read_text())["submissions_with_patches"] == 73
    assert written["summary"]["tasks_with_a_passing_patch_inside_one_function"] == 339


def test_what_was_counted_afterwards_adds_up_from_the_rows(written):
    rows, after = written["per_task"], written["afterwards"]
    with_patch = [row for row in rows.values() if row["passing"] is not None]
    funnel = after["the_funnel"]
    assert funnel["with_a_passing_patch_inside_one_function"] == len(with_patch)
    assert funnel["of_them_the_file_holding_it_first_of_the_tree"] == sum(1 for row in with_patch if row["passing"] == 1)
    assert funnel["of_them_the_function_holding_it_first_of_that_file"] == sum(1 for row in with_patch if row["function"] == 1)
    assert funnel["of_them_a_passing_patch_among_the_20_candidates"] == sum(1 for row in with_patch if row["place"] is not None)
    assert funnel["of_the_tasks_reached_the_function_first"] == sum(1 for row in with_patch if row["place"] is not None and row["function"] == 1)
    names = after["what_putting_the_named_files_first_does"]
    assert names["tasks_where_it_puts_an_expert_file_first_and_score_alone_does_not"] == sum(1 for row in rows.values() if row["expert"] == 1 and row["expert_by_score"] != 1)
    assert names["tasks_where_score_alone_has_one_first_and_it_does_not"] == sum(1 for row in rows.values() if row["expert"] != 1 and row["expert_by_score"] == 1)
    reached = after["the_10_tasks_reached"]
    assert reached["how_their_text_names_the_file"] == {task: rows[task]["expert_named"] for task in written["summary"]["chain__which"]}
    assert reached["with_the_file_first_by_score_alone"] == sum(1 for task in written["summary"]["chain__which"] if rows[task]["expert_by_score"] == 1)
    split = after["the_tasks_the_quoted_line_list_was_shaped_on_and_the_others"]
    shaped = set(json.loads(measure.FUNCTION_RECORD.read_text())["shaped_on"])
    for name, mine in (("the_80", [row for task, row in rows.items() if task in shaped]), ("outside", [row for task, row in rows.items() if task not in shaped])):
        assert split[name]["tasks"] == len(mine)
        assert split[name]["expert_file_among_the_first_1_3_10"] == [sum(1 for row in mine if row["expert"] is not None and row["expert"] <= n) for n in (1, 3, 10)]
        assert split[name]["reached"] == sum(1 for row in mine if row["place"] is not None)


# --------------------------------------------------------------------------- #
# the input that is refused
# --------------------------------------------------------------------------- #
def test_whole_input_is_not_refused():
    assert measure.refused({"a__b-1": record()}, 73, 73) is None and measure.refused({}, 0, 0) is None


def test_a_pull_request_record_without_the_text_of_a_file_is_refused():
    broken = record()
    broken["files"][0].update(before=None, fetch_error="limited")
    assert "a__b-1" in measure.refused({"a__b-1": broken, "a__b-2": record("a__b-2")}, 73, 73)
    assert "not fetched whole" in measure.refused({"a__b-1": {"instance_id": "a__b-1", "error": "limited"}}, 73, 73)


@pytest.mark.parametrize("here", [51, 0, 74])
def test_another_number_of_submissions_than_the_function_record_had_is_refused(here):
    assert "73" in measure.refused({"a__b-1": record()}, here, 73)


# --------------------------------------------------------------------------- #
# the round of seeded faults (canonical/tools/seeded_faults_file_found_v1.py)
# --------------------------------------------------------------------------- #
def test_the_seeded_faults_are_each_one_piece_of_text_that_stands_once():
    from canonical.tools import seeded_faults_file_found_v1 as seeded
    assert len(seeded.FAULTS) == len({what for what, _, _, _ in seeded.FAULTS}) >= 60
    for what, name, old, new in seeded.FAULTS:
        assert name in (seeded.ORGAN, seeded.MEASURE) and old != new, what
        assert (ROOT / name).read_text(encoding="utf-8").count(old) == 1, what


def test_the_round_leaves_the_other_rounds_lists_as_they_were():
    from canonical.tools import seeded_faults_file_found_v1 as seeded
    from canonical.tools import seeded_faults_function_found_v1 as base
    before = (base.TESTS, base.LEFT_OUT, base.RECORDS, base.FAULTS)
    seen = []
    kept, base.main = base.main, lambda argv=None: seen.append((base.TESTS, base.LEFT_OUT, base.RECORDS, base.FAULTS)) or 0
    try:
        assert seeded.main([]) == 0
    finally:
        base.main = kept
    assert seen == [(seeded.TESTS, seeded.LEFT_OUT, seeded.RECORDS, seeded.FAULTS)]
    assert (base.TESTS, base.LEFT_OUT, base.RECORDS, base.FAULTS) == before and len(base.FAULTS) == 34


def test_the_record_says_how_many_seeded_faults_the_tests_caught(written):
    from canonical.tools import seeded_faults_file_found_v1 as seeded
    found = written["seeded_faults"]
    last = found["rounds"][-1]
    assert last["seeded"] == len(seeded.FAULTS) and last["not_seeded"] == []
    assert last["caught"] + len(last["survived"]) == last["seeded"]
    assert [row["fault"] for row in last["rows"]] == [what for what, _, _, _ in seeded.FAULTS]
    assert sorted(row["fault"] for row in last["rows"] if not row["caught"]) == sorted(last["survived"])
    assert last["left_out_of_the_run"] == list(seeded.LEFT_OUT)
    assert found["tests_added_after_the_first_round"] == [name for name in found["tests_added_after_the_first_round"] if (ROOT / name.split("::")[0]).exists()]


# --------------------------------------------------------------------------- #
# added after the round of seeded faults: four faults of the measure got past the tests above
# (the other text's candidates made from the task's own text; a task reached twice counted
# twice; one small function standing first being enough for the earlier lists; a base commit
# read from the middle of a line)
# --------------------------------------------------------------------------- #
def test_another_text_that_finds_the_file_and_quotes_nothing_reaches_nothing():
    names_the_file = "Store.load returns a, see pkg/store.py"
    found = one([IN_SAVE], other=names_the_file)
    assert found["expert_other_text"] == 1 and found["place"] == 1 and found["place_other_text"] is None


def test_another_text_that_quotes_the_line_is_counted_as_reaching_it():
    assert one([IN_SAVE], other=TEXT)["place_other_text"] == 1


def test_a_task_the_chain_and_the_earlier_lists_both_reach_is_one_task():
    found = measure.summarise(PER_TASK, ["a__b-1"], ["a__b-1", "c__d-2"])
    assert found["chain__which"] == ["a__b-1"] and found["earlier_lists__which"] == ["a__b-1", "c__d-2"]
    assert found["of_the_500_from_the_tree_and_the_text_alone"] == 2


def test_the_earlier_lists_do_not_keep_a_task_with_a_small_function_that_does_not_stand_first():
    place_record = {"per_task": {"t-1": [0, 0, 5], "t-2": [0, 0, 5]}}
    function_record = {"per_task": {"t-1": {"functions": [{"rank": 1, "small": True}, {"rank": 3, "small": True}]},
                                    "t-2": {"functions": [{"rank": 1, "small": True}, {"rank": 3, "small": False}]}}}
    assert measure.earlier_kept(function_record, place_record) == ["t-2"]


def test_a_base_commit_quoted_inside_the_statement_is_not_the_base_commit(tmp_path):
    (tmp_path / "a__b-1.yaml").write_text("problem_statement: |\n  base_commit: " + "9f" * 20 + "\nbase_commit: " + "0a" * 20 + "\n")
    (tmp_path / "a__b-2.yaml").write_text("problem_statement: |\n  base_commit: " + "9f" * 20 + "\n")
    assert measure.base_commits(tmp_path, ["a__b-1", "a__b-2"]) == {"a__b-1": "0a" * 20}
