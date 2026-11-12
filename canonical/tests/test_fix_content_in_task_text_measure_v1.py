#!/usr/bin/env python3
"""What an issue text mentions, what a patch brings in, whether that is at hand, where the changed
line stands, and the counts and the rule."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import fix_shape_v1 as fix_shape  # noqa: E402
from canonical.tools import fix_content_in_task_text_measure_v1 as measure  # noqa: E402
from canonical.tools import small_passing_patch_place_measure_v1 as place  # noqa: E402

BEFORE = '''def rename(self, apps, db, old, new):
    """Rename the model."""
    with transaction.atomic(using=db):
        content_type.save(update_fields={'model'})
    return content_type
'''
AFTER = BEFORE.replace("save(update_fields", "save(using=db, update_fields")
ISSUE = ("RenameContentType._rename() doesn't save the content type on the correct database\n"
         "The lines in question:\nwith transaction.atomic(using=db):\n\tcontent_type.save(update_fields={'model'})\n"
         "I believe it should be content_type.save(using=db, update_fields={'model'}) because of the 3 routers.")
ELSEWHERE = "The table of contents is wrong when a heading has a link in it; see the 12 examples."


def patch(before: str = BEFORE, after: str = AFTER, shape: str = fix_shape.PUT_IN, needs: str = fix_shape.HELD) -> dict:
    return {"before": before, "wanted": place.normal(after), "shape": shape, "needs": needs}


def held(text: str = BEFORE) -> set:
    return fix_shape.atoms(measure._parsed(text))


# --------------------------------------------------------------------------- #
# the issue texts
# --------------------------------------------------------------------------- #
def test_a_statement_in_double_quotes_on_one_line_is_read():
    assert measure.statement_of('a: 1\nproblem_statement: "x\\ny \\"z\\" \\\\ t\\tu"\nb: 2') == 'x\ny "z" \\ t\tu'


def test_a_statement_in_single_quotes_over_several_lines_keeps_every_word():
    text = measure.statement_of("a: 1\nproblem_statement: 'it''s here\n\n  on two lines'\nb: 2\n")
    assert text.split() == ["it's", "here", "on", "two", "lines"]


def test_a_file_without_a_statement_gives_none():
    assert measure.statement_of("a: 1\nb: 2") is None


def test_statements_are_read_for_the_tasks_that_have_a_file(tmp_path):
    (tmp_path / "a__b-1.yaml").write_text('instance_id: a__b-1\nproblem_statement: "one"\n', encoding="utf-8")
    assert measure.statements(tmp_path, ["a__b-1", "a__b-2"]) == {"a__b-1": "one"}


def test_two_copies_agree_when_the_words_are_the_same_in_the_same_order(tmp_path):
    (tmp_path / "a__b-1.json").write_text(json.dumps({"problem_statement": "one  two\nthree"}), encoding="utf-8")
    (tmp_path / "a__b-2.json").write_text(json.dumps({"problem_statement": "one three two"}), encoding="utf-8")
    found = measure.copies_agree({"a__b-1": "one two three", "a__b-2": "one two three", "a__b-3": "x"}, tmp_path)
    assert found == {"in_both_copies": 2, "the_same_words_in_the_same_order": 1}
    assert measure.copies_agree({"a__b-1": "one"}, None) == {"in_both_copies": 0, "the_same_words_in_the_same_order": 0}


# --------------------------------------------------------------------------- #
# what a text mentions
# --------------------------------------------------------------------------- #
def test_a_name_is_mentioned_as_a_whole_word_letter_for_letter():
    text = measure.Text("the database and db, also DB and dbs")
    assert text.mentions(("name", "db")) == (1, text.text.index("db,"))
    assert text.mentions(("name", "data")) == (0, -1)
    assert text.mentions(("name", "Db")) == (0, -1)


def test_a_dotted_name_mentions_each_of_its_parts():
    text = measure.Text("call content_type.save(using=db)")
    assert all(text.mentions(("name", name))[0] == 1 for name in ("content_type", "save", "using", "db"))


def test_a_number_is_mentioned_only_standing_alone():
    text = measure.Text("version 3.12 has 12 of them, and x12 too")
    assert text.mentions(("constant", "int", "12"))[0] == 1
    assert text.mentions(("constant", "int", "3"))[0] == 0
    assert text.mentions(("constant", "float", "3.12"))[0] == 1


def test_a_string_is_mentioned_as_written_and_a_very_short_one_is_not_looked_for():
    text = measure.Text("the 'model' field, the model, a , b")
    assert text.mentions(("constant", "str", "'model'"))[0] == 2
    assert text.mentions(("constant", "str", "', '"))[0] == 0
    assert text.mentions(("constant", "str", "'missing'")) == (0, -1)


def test_other_constants_are_never_mentioned():
    text = measure.Text("None True b'abc' ...")
    assert text.mentions(("constant", "bytes", "b'abc'")) == (0, -1)
    assert text.mentions(("constant", "NoneType", "None")) == (0, -1)


def test_the_pool_holds_what_is_mentioned_and_could_be_supplied_the_most_mentioned_first():
    text = measure.Text("db then using, then db again; len is a builtin; unknown is not held")
    pool = measure.pool_of(text, {("name", "db"), ("name", "using"), ("name", "apps")} | measure._BUILTIN_NAMES)
    assert pool[:2] == [("name", "db"), ("name", "using")]
    assert ("name", "len") in pool and ("name", "unknown") not in pool and ("name", "apps") not in pool


def test_small_constants_are_not_in_the_pool():
    text = measure.Text("0 1 2 and 7")
    pool = measure.pool_of(text, {("constant", "int", "0"), ("constant", "int", "1"), ("constant", "int", "7")})
    assert pool == [("constant", "int", "7")]


def test_ties_in_the_pool_go_to_the_first_mentioned():
    text = measure.Text("beta alpha")
    assert measure.pool_of(text, {("name", "alpha"), ("name", "beta")}) == [("name", "beta"), ("name", "alpha")]


# --------------------------------------------------------------------------- #
# what a patch brings in, and whether it is at hand
# --------------------------------------------------------------------------- #
def test_wanted_is_what_the_changed_statement_holds_afterwards_and_did_not_before():
    assert measure.wanted_leaves(BEFORE, AFTER) == {("name", "using"), ("name", "db")}


def test_a_piece_taken_out_wants_nothing():
    assert measure.wanted_leaves(AFTER, BEFORE) == set()


def test_a_statement_put_in_wants_everything_it_is_written_with():
    after = BEFORE.replace("    return content_type", "    apps.clear_cache()\n    return content_type")
    assert measure.wanted_leaves(BEFORE, after) == {("name", "apps"), ("name", "clear_cache")}


def test_two_texts_that_are_the_same_program_want_nothing():
    assert measure.wanted_leaves(BEFORE, BEFORE + "\n") == set()


def test_nothing_wanted_is_at_hand():
    assert measure.at_hand(set(), []) == (measure.NOTHING, None)


def test_only_small_constants_wanted_is_at_hand_without_the_text():
    assert measure.at_hand({("constant", "NoneType", "None"), ("constant", "int", "0")}, []) == (measure.SMALL, None)


def test_the_constant_next_to_the_one_replaced_is_at_hand_without_the_text():
    assert measure.at_hand({("constant", "int", "7")}, [], next_to_it=True) == (measure.SMALL, None)


def test_wanted_leaves_in_the_pool_are_pointed_to_at_the_place_of_the_furthest():
    pool = [("name", "save"), ("name", "using"), ("name", "db")]
    assert measure.at_hand({("name", "using"), ("name", "db"), ("constant", "NoneType", "None")}, pool) == (measure.POINTED, 3)


def test_a_wanted_leaf_far_down_the_pool_does_not_count_as_among_the_first():
    pool = [("name", f"n{at}") for at in range(measure.FIRST_OF_THE_POOL + 1)]
    assert measure.at_hand({pool[measure.FIRST_OF_THE_POOL - 1]}, pool) == (measure.POINTED, measure.FIRST_OF_THE_POOL)
    assert measure.at_hand({pool[measure.FIRST_OF_THE_POOL]}, pool) == (measure.FURTHER, measure.FIRST_OF_THE_POOL + 1)


def test_one_wanted_leaf_outside_the_pool_makes_the_patch_not_pointed_to():
    assert measure.at_hand({("name", "using"), ("name", "db")}, [("name", "db")]) == (measure.NOT_POINTED, None)


# --------------------------------------------------------------------------- #
# the line
# --------------------------------------------------------------------------- #
def test_a_name_weighs_one_over_the_number_of_lines_that_hold_it():
    lines = ["a = db", "b = db + using", "return b"]
    assert measure.weights(lines, measure.Text("db using")) == [0.5, 1.5, 0.0]


def test_keywords_and_documentation_weigh_nothing():
    lines = ['"""return the db"""', "return db"]
    assert measure.weights(lines, measure.Text("return db")) == [0.0, 1.0]


def test_a_changed_line_is_found_and_given_as_it_was_and_as_it_is():
    before, after = ["a = 1", "b = 2", "c = 3"], ["a = 1", "b = 5", "c = 3"]
    assert measure.changed_lines(before, after) == ([1], ["b = 2"], ["b = 5"])


def test_a_line_only_put_in_counts_as_the_lines_on_both_sides_of_the_gap():
    before, after = ["a = 1", "c = 3"], ["a = 1", "b = 2", "c = 3"]
    assert measure.changed_lines(before, after) == ([0, 1], [], ["b = 2"])
    assert measure.changed_lines(["a = 1"], ["a = 1", "b = 2"]) == ([0], [], ["b = 2"])
    assert measure.changed_lines(["b = 2"], ["a = 1", "b = 2"]) == ([0], [], ["a = 1"])


def test_a_line_taken_out_is_the_changed_line():
    assert measure.changed_lines(["a = 1", "b = 2"], ["a = 1"]) == ([1], ["b = 2"], [])


def test_the_place_of_a_line_counts_the_heavier_ones_and_ties_from_the_top():
    assert measure.place_of_line([0.0, 2.0, 1.0, 2.0], [3]) == 2
    assert measure.place_of_line([0.0, 2.0, 1.0, 2.0], [1]) == 1
    assert measure.place_of_line([0.0, 2.0, 1.0, 2.0], [0]) == 4
    assert measure.place_of_line([0.0, 2.0, 1.0, 2.0], [0, 2]) == 3
    assert measure.place_of_line([1.0], []) is None


def test_with_a_text_that_mentions_nothing_the_place_is_the_place_from_the_top():
    assert measure.place_of_line(measure.weights(["a = 1", "b = 2", "c = 3"], measure.Text("nothing here")), [2]) == 3


def test_a_line_is_quoted_whatever_the_blanks_and_the_kind_of_quote():
    text = measure.Text('see content_type.save( update_fields = {"model"} ) there')
    assert measure.is_quoted(["        content_type.save(update_fields={'model'})"], text)
    assert not measure.is_quoted(["content_type.save(using=db)"], text)


def test_a_very_short_line_is_never_quoted():
    assert not measure.is_quoted(["pass"], measure.Text("pass pass pass"))
    assert not measure.is_quoted([], measure.Text("anything"))


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #
def test_what_the_changed_files_hold_leaves_out_tests_and_what_is_not_python():
    record = {"files": [{"is_test": False, "is_python": True, "before": "x = y"}, {"is_test": True, "is_python": True, "before": "t = u"},
                        {"is_test": False, "is_python": False, "before": "v = w"}, {"is_test": False, "is_python": True, "before": None},
                        {"is_test": False, "is_python": True, "before": "def (:"}]}
    assert measure.held_by(record) == {("name", "x"), ("name", "y")}


def test_a_task_whose_issue_quotes_the_fix_has_it_at_hand():
    found = measure.of_task([patch()], held(), ISSUE)
    best = found["best"]
    assert best["class"] == measure.POINTED and best["place_in_the_pool"] <= 3
    assert best["wanted"] == 2 and best["wanted_and_mentioned"] == 2
    assert best["line_as_it_was_quoted"] and best["line_as_patched_quoted"]
    # the line above it, which the issue quotes too, weighs the same and stands higher: ties go from the top
    assert best["place_of_the_line"] == 2 and best["place_of_the_line_from_the_top"] == 4 and best["lines"] == 5
    assert found["pool"] >= 5


def test_the_same_task_with_another_text_has_it_not():
    best = measure.of_task([patch()], held(), ELSEWHERE)["best"]
    assert best["class"] == measure.NOT_POINTED and best["wanted_and_mentioned"] == 0
    assert not best["line_as_it_was_quoted"] and best["place_of_the_line"] == best["place_of_the_line_from_the_top"]


def test_the_best_patch_of_a_task_is_the_one_that_needs_the_least_from_the_text():
    taken_out = patch(AFTER, BEFORE, fix_shape.TAKEN_OUT, fix_shape.NOTHING)
    found = measure.of_task([patch(), taken_out], held(), ELSEWHERE)
    assert [row["class"] for row in found["patches"]] == [measure.NOT_POINTED, measure.NOTHING]
    assert found["best"]["class"] == measure.NOTHING and found["best"]["shape"] == fix_shape.TAKEN_OUT


def test_a_constant_next_to_the_one_replaced_needs_nothing_from_the_text():
    before, after = "def f(x):\n    return x[7]\n", "def f(x):\n    return x[8]\n"
    best = measure.of_task([patch(before, after, fix_shape.LEAF, fix_shape.NEXT_TO_IT)], held(before), ELSEWHERE)["best"]
    assert best["class"] == measure.SMALL


# --------------------------------------------------------------------------- #
# all of them
# --------------------------------------------------------------------------- #
def row(level: str, shape: str = fix_shape.PUT_IN, in_pool: int | None = None, line: int | None = 1, top: int | None = 4, quoted: bool = False) -> dict:
    return {"shape": shape, "class": level, "place_in_the_pool": in_pool, "wanted": 2, "wanted_and_mentioned": 1, "wanted_not_small": 2, "lines": 20,
            "place_of_the_line": line, "place_of_the_line_from_the_top": top, "line_as_it_was_quoted": quoted, "line_as_patched_quoted": False,
            "names_of_the_definition": 10, "names_of_the_definition_mentioned": 3}


def task(*rows: dict, pool: int = 12) -> dict:
    best = min(rows, key=lambda found: measure.CLASSES.index(found["class"]))
    return {"patches": list(rows), "best": best, "pool": pool, "words_of_the_text": 100, "names_held": 300}


def per_task() -> dict:
    return {
        "t1": task(row(measure.POINTED, in_pool=2, quoted=True)),
        "t2": task(row(measure.NOT_POINTED, line=7), row(measure.FURTHER, shape=fix_shape.LEAF, in_pool=15, line=6)),
        "t3": task(row(measure.NOTHING, shape=fix_shape.TAKEN_OUT, line=12, top=2), row(measure.POINTED, in_pool=1, line=3)),
        "t4": task(row(measure.SMALL, shape=fix_shape.LEAF, line=None, top=None)),
        "t5": task(row(measure.NOT_POINTED, line=11, top=11)),
    }


def test_the_summary_counts_the_tasks_by_what_is_at_hand_and_those_the_rule_asks_about():
    reached = {"t1": False, "t2": False, "t3": False, "t4": True, "t5": False}
    found = measure.summarise(per_task(), reached, ["t1", "t2", "t4", "t5"])
    assert found["tasks"] == 5
    assert found["tasks_by_what_is_at_hand_for_the_best_patch"] == {measure.NOTHING: 1, measure.SMALL: 1, measure.POINTED: 1, measure.FURTHER: 1, measure.NOT_POINTED: 1}
    assert found["tasks_that_only_put_in_or_exchange_and_were_not_reached"] == 3            # t4 was reached, t3 takes a piece out
    assert found["of_those_with_the_content_at_hand"] == 1
    assert found["of_those_by_class"][measure.FURTHER] == 1 and found["of_those_by_class"][measure.NOT_POINTED] == 1


def test_the_summary_by_shape_takes_the_best_patch_of_that_shape():
    found = measure.summarise(per_task(), {}, [])["by_shape_of_the_passing_patch"]
    assert found[fix_shape.PUT_IN]["tasks_with_such_a_passing_patch"] == 4
    assert found[fix_shape.PUT_IN][measure.POINTED] == 2 and found[fix_shape.PUT_IN][measure.NOT_POINTED] == 2
    assert found[fix_shape.LEAF] == {"tasks_with_such_a_passing_patch": 2, measure.NOTHING: 0, measure.SMALL: 1, measure.POINTED: 0, measure.FURTHER: 1, measure.NOT_POINTED: 0}
    assert found[fix_shape.TAKEN_OUT][measure.NOTHING] == 1


def test_the_summary_takes_the_best_line_of_any_patch_of_a_task():
    found = measure.summarise(per_task(), {}, [])
    assert found["tasks_whose_changed_line_is_among_the_first"] == {"1": 1, "3": 2, "5": 2, "10": 3}
    assert found["the_same_counted_from_the_top_of_the_definition"] == {"1": 0, "3": 1, "5": 3, "10": 3}
    assert found["tasks_with_the_line_as_it_was_quoted"] == 1 and found["tasks_with_the_line_as_patched_quoted"] == 0
    assert found["median_size_of_the_pool"] == 12 and found["median_share_of_the_names_of_the_definition_mentioned"] == 0.3
    assert found["wanted_leaves_that_are_not_small_constants"] == 14 and found["of_them_mentioned_in_the_issue_text"] == 7


@pytest.mark.parametrize("count, verdict", [(24, "build"), (40, "build"), (23, "undecided"), (12, "undecided"), (11, "does not hold"), (0, "does not hold")])
def test_the_rule_is_the_one_written_beforehand(count, verdict):
    assert verdict in measure.rule(count, 3)["verdict"]
    assert "at least 24" in measure.EXPECTED["rule"] and "fewer than 12" in measure.EXPECTED["rule"]


def test_the_rule_says_whether_the_text_says_something_about_its_task():
    assert measure.rule(30, 8)["the_text_says_something_about_its_task"]
    assert not measure.rule(10, 10)["the_text_says_something_about_its_task"]


def test_every_expectation_is_a_range_and_the_rule_is_written_out():
    ranges = [value for key, value in measure.EXPECTED.items() if key not in ("written", "rule")]
    assert len(ranges) == 7 and all(len(pair) == 2 and pair[0] < pair[1] for pair in ranges)
    assert "before anything was counted" in measure.EXPECTED["written"]


def test_the_code_that_is_hashed_exists():
    assert all(len(value) == 64 for value in measure.code_sha256().values())
