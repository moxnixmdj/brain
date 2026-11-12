#!/usr/bin/env python3
"""Whether the task text finds the function: how a patch is cut to its function, what is counted for
a task, how the counts are added up, the rule, and that the record in the tree adds up from its rows."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import function_found_from_task_text_measure_v1 as measure  # noqa: E402
from canonical.tools import passing_patch_shape_measure_v1 as passing  # noqa: E402

RECORD = ROOT / "canonical" / "verification" / "FUNCTION_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json"

BEFORE = '''import os

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

TEXT = "Store.save() writes to the wrong database.\n```\ncontent_type.save(using=db, update_fields={'model'})\n```\n"
OTHER = "third() should return z squared, see unrelated."


def diff(path: str, hunks: str) -> str:
    return f"diff --git a/{path} b/{path}\nindex 83a4f00..5f3a362 100644\n--- a/{path}\n+++ b/{path}\n{hunks}\n"


IN_SAVE = diff("pkg/mod.py", "@@ -11,4 +11,4 @@\n class Store:\n     def save(self, content_type, db):\n-        content_type.save(update_fields={'model'})\n"
                             "+        content_type.save(using=db, update_fields={'model'})\n         return db")
IN_SAVE_OTHERWISE = diff("pkg/mod.py", "@@ -11,4 +11,5 @@\n class Store:\n     def save(self, content_type, db):\n-        content_type.save(update_fields={'model'})\n"
                                       "+        with atomic(db):\n+            content_type.save(update_fields={'model'})\n         return db")
IN_UNRELATED = diff("pkg/mod.py", "@@ -6,3 +6,3 @@\n def unrelated(a, b):\n-    c = a\n+    c = abs(a)\n     return c")
TWO_FUNCTIONS = diff("pkg/mod.py", "@@ -6,3 +6,3 @@\n def unrelated(a, b):\n-    c = a\n+    c = abs(a)\n     return c\n"
                                   "@@ -16,2 +16,2 @@\n     def load(self, a):\n-        return a\n+        return a + 1")
AT_THE_TOP = diff("pkg/mod.py", "@@ -2,3 +2,3 @@\n \n-LIMIT = 3\n+LIMIT = 4\n ")
A_TEST = diff("tests/test_mod.py", "@@ -1,1 +1,2 @@\n x = 1\n+y = 2")
ELSEWHERE = diff("pkg/other.py", "@@ -1,1 +1,2 @@\n x = 1\n+y = 2")
WITH_A_TEST = IN_SAVE + A_TEST


def record() -> dict:
    return {"instance_id": "a__b-1", "repo": "a/b",
            "files": [{"path": "pkg/mod.py", "status": "modified", "before": BEFORE, "is_test": False, "is_python": True, "patch": ""}]}


def files() -> passing.Files:
    return passing.Files(record())


def job(diffs, text=TEXT, other=OTHER, shaped_on=False):
    return ("a__b-1", record(), diffs, text, other, shaped_on)


# --------------------------------------------------------------------------- #
# a patch cut to its function
# --------------------------------------------------------------------------- #
def test_a_patch_inside_a_method_is_cut_to_that_method():
    path, span, before, after = measure.cut(files(), IN_SAVE)
    assert path == "pkg/mod.py" and span == (12, 14)
    assert before.startswith("def save(self, content_type, db):") and "using=db" in after and "using=db" not in before


def test_the_cut_is_the_same_as_the_one_the_shape_measure_makes():
    path, span, before, after = measure.cut(files(), IN_SAVE)
    made = passing.narrowed(BEFORE, BEFORE.replace("save(update_fields", "save(using=db, update_fields"), files().read("pkg/mod.py")[0])
    assert (before, after) == made


def test_a_patch_that_also_changes_a_test_is_still_one_function():
    assert measure.cut(files(), WITH_A_TEST)[1] == (12, 14)


@pytest.mark.parametrize("patch", [A_TEST, ELSEWHERE, "", "not a patch"])
def test_a_patch_that_changes_no_python_file_of_the_expert_is_not_cut(patch):
    assert measure.cut(files(), patch) is None


def test_a_patch_in_two_functions_of_one_class_is_cut_to_nothing_smaller_than_a_function():
    found = measure.cut(files(), TWO_FUNCTIONS)
    assert found is None or found[1] not in [(6, 8), (12, 14), (16, 17)]


def test_a_patch_that_does_not_apply_is_not_cut():
    wrong = diff("pkg/mod.py", "@@ -6,3 +6,3 @@\n def unrelated(a, b):\n-    c = something_else\n+    c = abs(a)\n     return c")
    assert measure.cut(files(), wrong) is None


def test_place_in_is_the_first_wanted_one_from_one():
    assert measure.place_in(["a", "b", "c"], {"c", "b"}) == 2
    assert measure.place_in(["a"], {"z"}) is None and measure.place_in([], {"a"}) is None


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #
def test_a_task_whose_issue_quotes_the_fix_is_reached_first_with_the_function_and_with_the_file():
    task, found = measure.of_task(job([IN_SAVE]))
    assert task == "a__b-1" and found["passing_patches"] == 1 and found["not_one_function"] == 0
    row, = found["functions"]
    assert (row["first"], row["last"], row["functions_in_the_file"]) == (12, 14, 4)
    assert row["rank"] == 1 and row["from_the_top"] == 2 and row["place"] == 1
    assert found["file_given"] == 1 and found["code_lines"] == 1


def test_another_tasks_text_reaches_nothing_and_ranks_another_function_first():
    _, found = measure.of_task(job([IN_SAVE]))
    row, = found["functions"]
    assert row["place_other_text"] is None and found["file_given_other_text"] is None
    assert row["rank_other_text"] > 1


def test_a_passing_patch_the_issue_does_not_quote_is_ranked_but_not_reached():
    _, found = measure.of_task(job([IN_SAVE_OTHERWISE]))
    row, = found["functions"]
    assert row["rank"] == 1 and row["place"] is None and found["file_given"] is None


def test_two_passing_patches_in_one_function_are_one_row_and_either_counts():
    _, found = measure.of_task(job([IN_SAVE_OTHERWISE, IN_SAVE]))
    assert len(found["functions"]) == 1 and found["functions"][0]["place"] == 1 and found["passing_patches"] == 2


def test_passing_patches_in_two_functions_are_two_rows_from_the_top():
    _, found = measure.of_task(job([IN_SAVE, IN_UNRELATED]))
    assert [(row["first"], row["from_the_top"]) for row in found["functions"]] == [(6, 1), (12, 2)]
    assert [row["rank"] for row in found["functions"]] == [found["functions"][0]["rank"], 1] and found["functions"][0]["rank"] > 1


def test_a_patch_outside_every_function_or_over_several_is_counted_as_not_one_function():
    _, found = measure.of_task(job([AT_THE_TOP, TWO_FUNCTIONS, A_TEST]))
    assert found["functions"] == [] and found["not_one_function"] == 3 and found["file_given"] is None


def test_whether_a_function_holds_a_small_patch_is_looked_at_only_for_the_tasks_shaped_on():
    assert measure.of_task(job([IN_UNRELATED]))[1]["functions"][0]["small"] is False
    assert measure.of_task(job([IN_UNRELATED], shaped_on=True))[1]["functions"][0]["small"] is True


def test_with_the_file_given_a_function_beyond_the_first_four_is_not_reached():
    many = "".join(f"def filler_{n}(q, alpha, beta, gamma, delta):\n    q.save(update_fields={{'model'}}, using=db)\n    return alpha, beta, gamma, delta\n\n\n" for n in range(6))
    source = many + "def target(q):\n    q.save(update_fields={'model'})\n    return q\n"
    first = source.split("\n").index("def target(q):") + 1
    change = diff("pkg/mod.py", f"@@ -{first},3 +{first},3 @@\n def target(q):\n-    q.save(update_fields={{'model'}})\n+    q.save(using=db, update_fields={{'model'}})\n     return q")
    rec = {"instance_id": "a__b-2", "repo": "a/b", "files": [{"path": "pkg/mod.py", "status": "modified", "before": source, "is_test": False, "is_python": True, "patch": ""}]}
    text = "alpha beta gamma delta are all wrong.\n```\nq.save(using=db, update_fields={'model'})\n```\n"
    _, found = measure.of_task(("a__b-2", rec, [change], text, OTHER, False))
    row, = found["functions"]
    assert row["place"] == 1                                          # with the function given
    assert row["rank"] == 7 and found["file_given"] is None           # every word of the target stands in the six others too, which hold more of the text


# --------------------------------------------------------------------------- #
# the other text
# --------------------------------------------------------------------------- #
def test_the_other_text_is_the_next_task_of_the_same_project():
    other = measure.other_text_of(["a__a-1", "a__a-2", "a__a-3", "b__b-9", "c__c-1", "c__c-5"])
    assert other["a__a-1"] == "a__a-2" and other["a__a-3"] == "a__a-1" and other["c__c-5"] == "c__c-1"
    assert other["b__b-9"] == "c__c-1"                                # the only task of its project: the next of any
    assert all(task != chosen for task, chosen in other.items())


# --------------------------------------------------------------------------- #
# added up
# --------------------------------------------------------------------------- #
def row(rank=1, other=5, top=3, place=None, place_other=None, functions=10, small=False):
    return {"path": "p.py", "first": 1, "last": 2, "functions_in_the_file": functions, "rank": rank, "rank_other_text": other,
            "from_the_top": top, "place": place, "place_other_text": place_other, "small": small}


def task(rows, file_given=None, file_other=None, code_lines=1):
    return {"passing_patches": 1, "not_one_function": 0, "functions": rows, "file_given": file_given, "file_given_other_text": file_other, "code_lines": code_lines}


PER_TASK = {
    "a__a-1": task([row(rank=1, place=1)], file_given=1),
    "a__a-2": task([row(rank=5, place=3), row(rank=2, place=None)], file_given=None),
    "a__a-3": task([row(rank=4, other=1)], code_lines=0),
    "a__a-4": task([]),
    "b__b-1": task([row(rank=11, functions=1, small=True)]),
    "b__b-2": task([row(rank=1, place=7, small=True)], file_given=2),
}


def test_a_part_counts_the_best_function_of_each_task():
    found = measure.part(PER_TASK, sorted(PER_TASK))
    assert found["tasks"] == 5
    assert found["function_given__tasks_with_a_passing_patch_among_the_first"] == {"1": 1, "5": 2, "20": 3}
    assert found["the_function_is_among_the_first_of_its_file"] == {"1": 2, "4": 4, "10": 4}
    assert found["the_function_is_among_the_first_of_its_file__share"] == {"1": 0.4, "4": 0.8, "10": 0.8}
    assert found["with_another_tasks_text"] == {"1": 1, "4": 1, "10": 5}
    assert found["counted_from_the_top_of_the_file"] == {"1": 0, "4": 5, "10": 5}


def test_a_part_counts_what_is_kept_when_only_the_file_is_given():
    found = measure.part(PER_TASK, sorted(PER_TASK))
    assert found["reached_with_the_function_given"] == 3 and found["of_them_still_reached_with_the_file_given"] == 2
    assert found["share_kept"] == 0.667 and found["file_given__tasks_with_a_passing_patch_among_the_20"] == 2
    assert found["reached_with_the_file_given_only"] == 0 and found["tasks_whose_file_has_one_function"] == 1
    assert found["median_functions_in_the_file"] == 10


def test_a_part_of_no_task_has_no_share():
    found = measure.part(PER_TASK, ["a__a-4"])
    assert found["tasks"] == 0 and found["share_kept"] is None and found["median_functions_in_the_file"] is None


def test_the_summary_splits_the_tasks_shaped_on_from_the_rest():
    summary = measure.summarise(PER_TASK, ["b__b-1", "b__b-2", "z__z-1"], {"b__b-1": 30, "b__b-2": 190, "z__z-1": None})
    assert summary["tasks_with_a_passing_patch"] == 6 and summary["tasks_with_a_passing_patch_within_one_function"] == 5
    assert summary[measure.THE_80]["tasks"] == 2 and summary[measure.THE_REST]["tasks"] == 3 and summary[measure.ALL]["tasks"] == 5
    assert summary["tasks_whose_issue_text_has_no_code_line"] == 1
    for key, value in summary[measure.ALL].items():
        if isinstance(value, int) and key in summary[measure.THE_80] and "median" not in key:
            assert value == summary[measure.THE_80][key] + summary[measure.THE_REST][key]


def test_the_earlier_lists_keep_a_task_only_where_its_function_is_the_first():
    found = measure.earlier_lists(PER_TASK, {"b__b-1": 30, "b__b-2": 150, "z__z-1": None, "a__a-1": 190})
    assert found["reached_by_the_earlier_lists_within_200__function_given"] == 3 and found["of_them_within_180"] == 2
    assert found["of_them_with_the_function_first_of_its_file__at_least"] == 1 and found["at_most"] == 1      # b__b-2: rank 1; b__b-1: rank 11
    assert found["tasks_of_the_80_within_200__function_given__quoted_lines_first"] == 3                       # a__a-1 and b__b-2 quoted, b__b-1 earlier
    assert found["tasks_of_the_80_within_200__file_given__at_least"] == 2 and found["file_given__at_most"] == 2


def test_a_task_with_small_patches_in_two_functions_is_a_range():
    per_task = {"a__a-1": task([row(rank=1, small=True), row(rank=3, small=True)])}
    found = measure.earlier_lists(per_task, {"a__a-1": 10})
    assert found["of_them_with_the_function_first_of_its_file__at_least"] == 0 and found["at_most"] == 1


# --------------------------------------------------------------------------- #
# the rule
# --------------------------------------------------------------------------- #
def summary_with(kept, outside):
    return {measure.ALL: {"share_kept": kept}, measure.THE_REST: {"function_given__tasks_with_a_passing_patch_among_the_first": {str(measure.FIRST): outside}}}


@pytest.mark.parametrize("kept, verdict", [(1.0, "start from the file"), (0.667, "start from the file"), (0.5, "undecided"), (0.34, "undecided"),
                                           (0.3, "finding the function is the limiting step"), (0.0, "finding the function is the limiting step"),
                                           (None, "undecided: nothing reached")])
def test_the_rule_reads_the_share_kept(kept, verdict):
    assert measure.rule(summary_with(kept, 3))["verdict"].startswith(verdict)


def test_the_rule_says_apart_whether_the_list_carries_to_tasks_it_was_not_shaped_on():
    assert measure.rule(summary_with(0.9, 0))["carries_to_tasks_it_was_not_shaped_on"] is False
    assert measure.rule(summary_with(0.9, 1))["carries_to_tasks_it_was_not_shaped_on"] is True


def test_every_expectation_is_a_range_written_before_and_there_is_a_rule():
    ranges = {key: value for key, value in measure.EXPECTED.items() if key not in ("written", "rule")}
    assert len(ranges) == 10
    for low, high in ranges.values():
        assert low <= high
    assert "before anything was counted" in measure.EXPECTED["written"] and "two thirds" in measure.EXPECTED["rule"]


def test_the_budget_and_the_share_of_the_quoted_lines_are_the_ones_counted_before():
    from canonical.runtime import function_the_task_text_points_at_v1 as pointer
    from canonical.tools import quoted_line_place_measure_v1 as earlier
    assert measure.BUDGET == 200 and measure.FIRST == earlier.FIRST == pointer.FUNCTIONS * pointer.OF_EACH


def test_the_hashed_files_are_there():
    assert all(len(value) == 64 for value in measure.code_sha256().values()) and len(measure.code_sha256()) == 8


# --------------------------------------------------------------------------- #
# the record in the tree
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def stored():
    if not RECORD.exists():
        pytest.skip("the record is not in this tree")
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_the_record_adds_up_from_its_own_rows(stored):
    earlier = {name: found[2] for name, found in json.loads(measure.PLACE_RECORD.read_text())["per_task"].items()}
    assert measure.summarise(stored["per_task"], stored["shaped_on"], earlier) == stored["summary"]
    assert measure.rule(stored["summary"]) == stored["rule"]


def test_the_record_says_what_was_expected_before_and_whether_it_held(stored):
    assert stored["expected_before"] == measure.EXPECTED
    assert stored["model_calls"] == 0 and stored["tests_run"] == 0
    held = stored["expectations_held"]
    assert len(held) == 10 and all(isinstance(value["held"], bool) for value in held.values())
    for key, value in held.items():
        low, high = measure.EXPECTED[key]
        assert value["held"] == (low <= value["found"] <= high)


def test_the_record_was_counted_with_the_files_as_they_are(stored):
    now = measure.code_sha256()
    for name in ("canonical/tools/function_found_from_task_text_measure_v1.py", "canonical/runtime/function_the_task_text_points_at_v1.py",
                 "canonical/runtime/quoted_in_the_task_text_v1.py"):
        assert stored["code_sha256"][name] == now[name]


def test_the_record_begins_with_what_to_read_first(stored):
    assert next(iter(stored)) == "read_this_first" and len(stored["read_this_first"]) >= 5


# --------------------------------------------------------------------------- #
# what was counted after the result was seen, counted again from the rows
# --------------------------------------------------------------------------- #
def _best(rows, key):
    values = [found[key] for found in rows if found[key] is not None]
    return min(values) if values else None


def _split(rows_of, tasks):
    return {"tasks": len(tasks), "first": sum(_best(rows_of[name], "rank") == 1 for name in tasks),
            "among_the_first_4": sum(_best(rows_of[name], "rank") <= 4 for name in tasks),
            "first_with_another_tasks_text": sum(_best(rows_of[name], "rank_other_text") == 1 for name in tasks)}


def test_afterwards_the_tasks_outside_the_80_that_one_statement_could_reach(stored):
    passing_rows = json.loads(measure.PASSING_RECORD.read_text())["per_task"]
    rows_of = {name: found["functions"] for name, found in stored["per_task"].items() if found["functions"]}
    outside = [name for name in rows_of if name not in set(stored["shaped_on"]) and passing_rows[name][4]]
    after = stored["afterwards"]
    assert after["tasks_outside_the_80_with_a_passing_patch_within_one_statement"] == len(outside)
    assert after["of_them_reached_within_20_with_the_function_given"] == sum(_best(rows_of[name], "place") is not None for name in outside)


def test_afterwards_the_splits_by_code_line_and_by_size_of_the_file(stored):
    per_task = stored["per_task"]
    rows_of = {name: found["functions"] for name, found in per_task.items() if found["functions"]}
    after = stored["afterwards"]
    assert after["by_whether_the_issue_has_a_code_line"]["none"] == _split(rows_of, [name for name in rows_of if per_task[name]["code_lines"] == 0])
    assert after["by_whether_the_issue_has_a_code_line"]["one_or_more"] == _split(rows_of, [name for name in rows_of if per_task[name]["code_lines"] > 0])
    size = {name: min(found["functions_in_the_file"] for found in rows) for name, rows in rows_of.items()}
    bounds = {"1 to 9": (1, 9), "10 to 39": (10, 39), "40 to 99": (40, 99), "100 and more": (100, 10 ** 9)}
    for label, (low, high) in bounds.items():
        assert after["by_functions_in_the_file"][label] == _split(rows_of, [name for name in rows_of if low <= size[name] <= high])
    assert sum(found["tasks"] for found in after["by_functions_in_the_file"].values()) == stored["summary"][measure.ALL]["tasks"]
    single = [name for name in rows_of if len(rows_of[name]) == 1]
    assert after["tasks_with_exactly_one_function_that_holds_a_passing_patch"] == {
        **_split(rows_of, single), "first_from_the_top": sum(rows_of[name][0]["from_the_top"] == 1 for name in single)}


def test_afterwards_the_tasks_reached_and_the_other_way_of_spending_the_earlier_lists(stored):
    per_task = stored["per_task"]
    after = stored["afterwards"]
    reached = {name for name, found in per_task.items() if _best(found["functions"], "place") is not None}
    assert set(after["the_tasks_reached"]) == reached
    assert after["of_the_500"]["reached_within_20_with_the_function_given"] == len(reached) == stored["summary"][measure.ALL]["reached_with_the_function_given"]
    assert after["of_the_500"]["with_the_file_given"] == sum(1 for found in per_task.values() if found["file_given"] is not None)
    for name, found in after["the_tasks_reached"].items():
        assert found["place_with_the_file_given"] == per_task[name]["file_given"] and found["shaped_on"] == (name in stored["shaped_on"])
        assert (found["place_with_the_file_given"] is not None) <= (found["rank_of_the_function"] <= 4)
    earlier = {name: found[2] for name, found in json.loads(measure.PLACE_RECORD.read_text())["per_task"].items()}
    each = (measure.BUDGET - measure.FIRST) // 4
    spread = sorted(name for name, at in earlier.items() if at is not None and at <= each
                    and any(found["small"] and found["rank"] <= 4 for found in per_task.get(name, {}).get("functions", [])))
    assert after["earlier_lists_spread_over_the_first_4_functions_45_candidates_each"] == {"tasks_kept": len(spread), "which": spread}


# --------------------------------------------------------------------------- #
# added after the round of seeded faults (canonical/tools/seeded_faults_function_found_v1.py):
# counting a task reached only with the file given as kept got past the tests above
# --------------------------------------------------------------------------- #
def test_a_task_reached_only_with_the_file_given_is_not_counted_as_kept():
    per_task = {"a__a-1": task([row(place=2)], file_given=2), "a__a-2": task([row(place=None)], file_given=4)}
    found = measure.part(per_task, sorted(per_task))
    assert found["reached_with_the_function_given"] == 1 and found["of_them_still_reached_with_the_file_given"] == 1
    assert found["share_kept"] == 1.0 and found["reached_with_the_file_given_only"] == 1
    assert found["file_given__tasks_with_a_passing_patch_among_the_20"] == 2


def test_the_seeded_faults_are_each_one_piece_of_text_that_stands_once():
    from canonical.tools import seeded_faults_function_found_v1 as seeded
    assert len(seeded.FAULTS) == 34 and len({what for what, _, _, _ in seeded.FAULTS}) == 34
    for what, name, old, new in seeded.FAULTS:
        assert (ROOT / name).read_text(encoding="utf-8").count(old) == 1, what
        assert old != new


def test_the_record_says_how_many_seeded_faults_the_tests_caught(stored):
    found = stored["seeded_faults"]
    assert found["first_round"]["seeded"] == found["second_round"]["seeded"] == 34
    assert found["first_round"]["caught"] == 34 - len(found["first_round"]["survived"])
    assert found["second_round"]["caught"] == 34 - len(found["second_round"]["survived"])
