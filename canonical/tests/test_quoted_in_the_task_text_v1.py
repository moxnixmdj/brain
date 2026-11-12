#!/usr/bin/env python3
"""One line written as the task's text writes it: what is read as a code line, where it is put, in
which order, and how the place of a patch in that list is counted."""
from __future__ import annotations

import ast
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import quoted_in_the_task_text_v1 as quoted  # noqa: E402
from canonical.tools import quoted_line_place_measure_v1 as measure  # noqa: E402
from canonical.tools import small_passing_patch_place_measure_v1 as place  # noqa: E402

PROGRAM = '''def rename(self, apps, db, old, new):
    """Rename the model."""
    with transaction.atomic(using=db):
        content_type.save(update_fields={'model'})
    if db is None:
        return None
    elif old:
        apps.clear()
    return content_type
'''
FIXED = PROGRAM.replace("save(update_fields", "save(using=db, update_fields")
ISSUE = ("RenameContentType._rename() doesn't save the content type on the correct database\n"
         "The lines in question:\nwith transaction.atomic(using=db):\n\tcontent_type.save(update_fields={'model'})\n"
         "I believe it should be `content_type.save(using=db, update_fields={'model'})` because of the routers.\n")
NORMAL = ast.unparse(ast.parse(PROGRAM))


# --------------------------------------------------------------------------- #
# what reads as a code line
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text, found", [
    ("print(x, y)", ("print(x, y)", False)),
    ("return value", ("return value", False)),
    ("value = other", ("value = other", False)),
    ("import os.path", ("import os.path", False)),
    ("for a in b:", ("for a in b:", True)),
    ("def f(x, y):", ("def f(x, y):", True)),
    ("if x is not None:", ("if x is not None:", True)),
    ('x = "double"', ("x = 'double'", False)),
    ("  spaced( a ,b )  ", ("spaced(a, b)", False)),
])
def test_a_statement_on_one_line_is_read_as_code(text, found):
    assert quoted.read_as_code(text) == found


@pytest.mark.parametrize("text", [
    "Description", "foo.bar.baz", "pre-commit-hooks", "first, second", "a_long_name_alone", "not something", "'only a string'",
    "x = 1", "f(x)", "if x:", "else:", "except ValueError:", "this is not code at all", "", "return", "if x: return y_value",
    "class Meta:\n    pass\nx = 12345",
])
def test_words_short_lines_and_more_than_one_line_are_not_code(text):
    assert quoted.read_as_code(text) is None


def test_the_code_lines_of_a_text_are_its_lines_and_what_stands_between_backticks():
    found = quoted.code_lines(ISSUE)
    assert found == [("with transaction.atomic(using=db):", True), ("content_type.save(update_fields={'model'})", False),
                     ("content_type.save(using=db, update_fields={'model'})", False)]


def test_a_prompt_or_a_diff_sign_in_front_is_set_aside():
    found = quoted.code_lines(">>> apps.clear_cache()\n+    if db is not None:\n-    return content_type.pk\n$ python manage.py\n... value = compute(1)\n")
    assert found == [("apps.clear_cache()", False), ("if db is not None:", True), ("return content_type.pk", False), ("value = compute(1)", False)]


def test_an_elif_is_read_as_the_if_it_is():
    assert quoted.code_lines("elif old and new:\n- elif isinstance(x, str):") == [("if old and new:", True), ("if isinstance(x, str):", True)]


def test_a_code_line_is_kept_once_and_in_the_order_of_the_text():
    assert quoted.code_lines("b = second_value\na = first_value\n`b = second_value`") == [("b = second_value", False), ("a = first_value", False)]


def test_a_text_without_code_has_no_code_lines():
    assert quoted.code_lines("The table of contents is wrong when a heading has a link in it.") == []


# --------------------------------------------------------------------------- #
# the lines of a program
# --------------------------------------------------------------------------- #
def test_statement_lines_are_whole_statements_and_heads_and_not_documentation():
    assert quoted.statement_lines(NORMAL) == {1: True, 3: True, 4: False, 5: True, 6: False, 7: True, 8: False, 9: False}


def test_a_statement_over_several_lines_is_not_a_statement_line():
    program = ast.unparse(ast.parse("def f():\n    x = '''a\nb'''\n    return x\n"))
    lines = quoted.statement_lines(program)
    assert all(program.split("\n")[number - 1].strip() != "" for number in lines)
    assert sum(1 for is_head in lines.values() if not is_head) >= 1


def test_the_lines_the_text_points_at_come_first_and_ties_go_from_the_top():
    lines = ["a = db", "b = db + using", "c = other", "d = other"]
    assert quoted.pointed_at(lines, [1, 2, 3, 4], "db using") == [2, 1, 3, 4]
    assert quoted.pointed_at(lines, [1, 2, 3, 4], "nothing") == [1, 2, 3, 4]
    assert quoted.pointed_at(lines, [3, 4], "other") == [3, 4]


# --------------------------------------------------------------------------- #
# the candidates
# --------------------------------------------------------------------------- #
def test_the_quoted_fix_is_the_first_candidate():
    made = quoted.candidates(PROGRAM, ISSUE)
    assert made[0] == place.normal(FIXED)


def test_every_candidate_compiles_is_made_once_and_is_not_the_program():
    made = quoted.candidates(PROGRAM, ISSUE + ">>> apps.clear_cache()\n+    if db is not None:\n")
    assert len(made) == len(set(made)) and NORMAL not in made and len(made) > 5
    for program in made:
        ast.parse(program)
        assert ast.unparse(ast.parse(program)) == program


def test_a_line_takes_the_place_only_of_a_line_it_resembles():
    made = quoted.candidates("def f(a):\n    total = compute(a)\n    return total\n", "result_of_everything = something_else_entirely(1, 2, 3)")
    assert all("total = compute(a)" in program for program in made)            # only put next to lines, never in place of one


def test_a_head_takes_the_place_only_of_a_head_that_begins_with_the_same_word():
    made = quoted.candidates("def f(a):\n    while a is None:\n        a = g()\n    return a\n", "if a is None:")
    assert made == []
    made = quoted.candidates("def f(a):\n    if a is None:\n        a = g()\n    return a\n", "if a is not None:")
    assert made == ["def f(a):\n    if a is not None:\n        a = g()\n    return a"]


def test_an_if_from_the_text_in_place_of_an_elif_stays_an_elif():
    program = "def f(a, b):\n    if a:\n        return 1\n    elif b is None:\n        return 2\n    return 3\n"
    made = quoted.candidates(program, "elif b is not None:")
    assert made == ["def f(a, b):\n    if a:\n        return 1\n    elif b is not None:\n        return 2\n    return 3"]


def test_lines_in_place_come_before_lines_put_next_to_one_and_the_most_alike_first():
    program = "def f(a):\n    value = compute(a)\n    other = compute(a, 2)\n    return value\n"
    made = quoted.candidates(program, "value = compute(a, 1)")
    assert made[0] == "def f(a):\n    value = compute(a, 1)\n    other = compute(a, 2)\n    return value"
    assert made[1] == "def f(a):\n    value = compute(a)\n    value = compute(a, 1)\n    return value"
    assert len(made) > 2 and all(program.count("\n") == 4 for program in made[2:])   # the rest have one line more


def test_nothing_is_put_in_front_of_a_program_that_is_one_definition():
    program = "def f(a):\n    value = compute(a)\n    return value\n"
    assert all(made.startswith("def f(a):") for made in quoted.candidates(program, "log_the_value(a)"))
    two = "x = compute(1)\ny = compute(2)\n"
    assert "log_the_value(a)\nx = compute(1)\ny = compute(2)" in quoted.candidates(two, "log_the_value(a)")


def test_a_line_is_put_in_at_the_depth_of_its_neighbour_and_of_the_next_line():
    program = "def f(a):\n    if a:\n        b = 1\n    return a\n"
    made = quoted.candidates(program, "log_the_value(a)")
    assert "def f(a):\n    if a:\n        log_the_value(a)\n        b = 1\n    return a" in made
    assert "def f(a):\n    if a:\n        b = 1\n        log_the_value(a)\n    return a" in made
    assert "def f(a):\n    if a:\n        b = 1\n    log_the_value(a)\n    return a" in made
    assert "def f(a):\n    log_the_value(a)\n    if a:\n        b = 1\n    return a" in made


def test_lines_are_put_next_to_the_lines_the_text_points_at_first():
    program = "def f(a, b):\n    first = a\n    second = b\n    third = special_name\n    return first\n"
    made = quoted.candidates(program, "The special_name is wrong.\nlog_the_value(a)")
    assert made[0] == "def f(a, b):\n    first = a\n    second = b\n    log_the_value(a)\n    third = special_name\n    return first"


def test_no_more_candidates_are_made_than_asked_for():
    program = "def f(a):\n" + "".join(f"    v{at} = a + {at}\n" for at in range(30)) + "    return a\n"
    assert len(quoted.candidates(program, "log_the_value(a)\nother_call(a, 1)", at_most=7)) == 7


def test_a_program_that_cannot_be_read_or_a_text_without_code_gives_nothing():
    assert quoted.candidates("def (:", ISSUE) == []
    assert quoted.candidates(PROGRAM, "nothing here is code") == []


# --------------------------------------------------------------------------- #
# the place of a patch in the list
# --------------------------------------------------------------------------- #
def patch(before: str = PROGRAM, after: str = FIXED, shape: str = "one piece put in") -> dict:
    return {"before": before, "wanted": place.normal(after), "shape": shape}


def test_the_place_is_counted_from_one_and_is_none_when_the_patch_is_not_made():
    found = measure.of_definition(PROGRAM, [place.normal(FIXED), place.normal(PROGRAM.replace("return content_type", "return None"))], ISSUE)
    assert found["places"] == [1, None] and found["candidates"] == len(quoted.candidates(PROGRAM, ISSUE))


def test_a_task_has_the_best_place_of_its_patches_and_the_code_lines_of_its_text():
    other = "def g(x):\n    return compute_all(x)\n"
    found = measure.of_task([patch(), patch(other, other.replace("compute_all(x)", "compute_all(x, 1)"), "one piece put in")], ISSUE)
    assert found["best"] == 1 and [row["place"] for row in found["patches"]] == [1, None]
    assert found["code_lines"] == 3 and len(found["candidates"]) == 2


def test_a_definition_that_is_too_large_is_not_asked():
    found = measure.of_task([patch()], ISSUE, max_nodes=5)
    assert found["best"] is None and found["candidates"] == [None]


def test_with_another_text_the_patch_is_not_in_the_list():
    assert measure.of_task([patch()], "The table of contents is wrong.\nbuild_the_table(document)")["best"] is None


def task(best: int | None, candidates: int | None = 30, code_lines: int = 3, shape: str = "one piece put in") -> dict:
    return {"patches": [{"shape": shape, "place": best}], "best": best, "candidates": [candidates], "code_lines": code_lines}


def test_the_summary_counts_what_is_new_and_what_falls_out_with_less_budget():
    per_task = {"new": task(2), "new_late": task(21), "both": task(1), "old": task(None), "old_late": task(None), "neither": task(None, 0, 0), "big": task(None, None)}
    earlier = {"new": None, "new_late": 250, "both": 40, "old": 180, "old_late": 181, "neither": None, "big": None}
    found = measure.summarise(per_task, earlier)
    assert found["tasks"] == 7
    assert found["tasks_by_best_place_in_this_list"] == {"1": 1, "5": 2, "20": 2, "100": 3, "at any place": 3, "in no place": 4}
    assert found["tasks_within_the_first_of_this_list"] == 2 and found["of_them_not_reached_by_the_earlier_lists"] == 1
    assert found["tasks_the_earlier_lists_reached_within_the_budget"] == 3
    assert found["of_them_fallen_out_with_less_budget_and_not_reached_here"] == 1
    assert found["tasks_within_the_budget_with_this_list_first"] == 3                       # new, both, old
    assert found["definitions_asked"] == 6 and found["definitions_not_asked"] == 1 and found["definitions_for_which_the_list_is_empty"] == 1
    assert found["tasks_whose_issue_text_has_no_code_line"] == 1 and found["by_shape_of_the_patch_found"] == {"one piece put in": 3}


@pytest.mark.parametrize("new, verdict", [(5, "tried first"), (9, "tried first"), (4, "undecided"), (3, "undecided"), (2, "kept out"), (0, "kept out")])
def test_the_rule_is_the_one_written_beforehand(new, verdict):
    assert verdict in measure.rule(new)["verdict"]
    assert "at least 5" in measure.EXPECTED["rule"] and "fewer than 3" in measure.EXPECTED["rule"]


def test_every_expectation_is_a_range_and_the_budget_is_the_earlier_one():
    ranges = [value for key, value in measure.EXPECTED.items() if key not in ("written", "rule")]
    assert len(ranges) == 6 and all(len(pair) == 2 and pair[0] < pair[1] for pair in ranges)
    assert measure.BUDGET == place.BUDGET == 200 and measure.FIRST == 20
    assert all(len(value) == 64 for value in measure.code_sha256().values())
