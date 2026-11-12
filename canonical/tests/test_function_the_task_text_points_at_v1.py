#!/usr/bin/env python3
"""The functions of a file in the order a task's text points at them, the candidates made for the
first of them, and a function's new text written back into the file."""
from __future__ import annotations

import ast
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import function_the_task_text_points_at_v1 as pointer  # noqa: E402
from canonical.runtime import quoted_in_the_task_text_v1 as quoted  # noqa: E402

SOURCE = '''import os

LIMIT = 3


def first(a):
    return a


class RenameContentType:
    """Rename."""

    def _rename(self, apps, schema_editor, old_model, new_model):
        db = schema_editor.connection.alias
        content_type = self.get(db)
        with transaction.atomic(using=db):
            content_type.save(update_fields={'model'})

    @property
    def other(self):
        return os.getcwd()


@decorated
@twice(1)
async def helper(x):
    def inner(y):
        return y + 1

    return inner(x)
'''

TEXT = ("RenameContentType._rename() doesn't save the content type on the correct database.\n"
        "```\ncontent_type.save(using=db, update_fields={'model'})\n```\n")


def named(functions) -> list[str]:
    return [function.name for function in functions]


# --------------------------------------------------------------------------- #
# the functions of a file
# --------------------------------------------------------------------------- #
def test_every_function_is_found_from_the_top_and_a_class_is_not_one():
    assert named(pointer.functions_of(SOURCE)) == ["first", "RenameContentType._rename", "RenameContentType.other", "helper", "helper.inner"]


def test_a_function_begins_at_its_first_decorator_and_ends_at_its_last_line():
    found = {function.name: function for function in pointer.functions_of(SOURCE)}
    lines = SOURCE.split("\n")
    assert lines[found["helper"].first - 1] == "@decorated"
    assert lines[found["helper"].last - 1] == "    return inner(x)"
    assert lines[found["RenameContentType.other"].first - 1] == "    @property"
    assert lines[found["first"].first - 1] == "def first(a):" and found["first"].last == found["first"].first + 1


def test_a_function_inside_an_if_or_a_try_is_found_too():
    source = "if X:\n    def a():\n        pass\nelse:\n    def b():\n        pass\ntry:\n    def c():\n        pass\nexcept E:\n    pass\n"
    assert named(pointer.functions_of(source)) == ["a", "b", "c"]


@pytest.mark.parametrize("source", ["def broken(:\n", "", "x = 1\n", "\x00"])
def test_a_file_that_cannot_be_read_or_has_no_function_gives_none(source):
    assert pointer.functions_of(source) == []
    assert pointer.order(source, TEXT) == []
    assert pointer.candidates(source, TEXT) == []


def test_the_text_of_a_method_is_moved_to_the_margin_and_can_be_read_alone():
    function = next(f for f in pointer.functions_of(SOURCE) if f.name == "RenameContentType.other")
    text = pointer.text_of(SOURCE, function)
    assert text.split("\n")[0] == "@property" and text.split("\n")[1] == "def other(self):"
    assert isinstance(ast.parse(text).body[0], ast.FunctionDef)


# --------------------------------------------------------------------------- #
# words
# --------------------------------------------------------------------------- #
def test_an_identifier_is_a_word_whole_and_in_its_parts():
    assert pointer.words("RenameContentType") == ["RenameContentType", "rename", "content", "type"]
    assert pointer.words("update_fields") == ["update_fields", "update", "fields"]
    assert pointer.words("HTTPServer") == ["HTTPServer", "http", "server"]


def test_a_plain_small_word_is_not_given_twice_and_short_parts_are_left_out():
    assert pointer.words("save") == ["save"]
    assert pointer.words("x_y") == ["x_y"]
    assert pointer.words("to_db") == ["to_db"]                       # "to" and "db" are shorter than a part has to be
    assert pointer.words("_rename") == ["_rename", "rename"]


def test_pythons_own_words_are_left_out():
    assert pointer.words("def f(self): return None if x else y") == ["f", "self", "x", "y"]
    assert pointer.words("for_each") == ["for_each", "each"]


def test_words_of_prose_and_code_come_in_the_order_written():
    assert pointer.words("the save() call, see `using=db`") == ["the", "save", "call", "see", "using", "db"]


# --------------------------------------------------------------------------- #
# the order
# --------------------------------------------------------------------------- #
def test_the_function_the_text_names_comes_first():
    assert named(pointer.order(SOURCE, TEXT))[0] == "RenameContentType._rename"


def test_another_text_puts_another_function_first():
    assert named(pointer.order(SOURCE, "helper() returns inner(x) with the wrong y"))[0] in ("helper", "helper.inner")
    assert named(pointer.order(SOURCE, "os.getcwd is called by the other property"))[0] == "RenameContentType.other"


def test_a_text_with_nothing_in_common_leaves_the_order_of_the_file():
    assert named(pointer.order(SOURCE, "zzz qqq")) == named(pointer.functions_of(SOURCE))
    assert named(pointer.order(SOURCE, "")) == named(pointer.functions_of(SOURCE))


def test_the_name_of_the_class_counts_for_its_methods():
    source = "class Alpha:\n    def run(self):\n        return 1\n\n\nclass Beta:\n    def run(self):\n        return 1\n"
    assert named(pointer.order(source, "Beta is wrong"))[0] == "Beta.run"
    assert named(pointer.order(source, "Alpha is wrong"))[0] == "Alpha.run"


def test_ties_go_from_the_top():
    source = "def a():\n    return same\n\n\ndef b():\n    return same\n"
    assert named(pointer.order(source, "same")) == ["a", "b"]


def test_a_word_that_stands_in_every_function_does_not_decide():
    source = "def a(self):\n    return self.rare_thing\n\n\ndef b(self):\n    return self\n\n\ndef c(self):\n    return self\n"
    assert named(pointer.order(source, "self self self rare_thing"))[0] == "a"


def test_the_order_holds_every_function_once_whatever_the_text():
    for text in (TEXT, "", "helper", "os"):
        assert sorted(pointer.order(SOURCE, text)) == pointer.functions_of(SOURCE)


def test_the_order_can_be_asked_for_given_functions_only():
    some = [function for function in pointer.functions_of(SOURCE) if function.name in ("first", "helper")]
    assert named(pointer.order(SOURCE, "helper inner", some)) == ["helper", "first"]


def test_the_scorer_is_the_one_the_tree_already_has():
    from canonical.runtime.bound_capabilities import objective_relevance_bm25 as bm25
    scored = bm25._bm25_scores(["rare"], [["rare", "x"], ["x", "x"], ["y"]])
    assert len(scored) == 3 and scored[0][0] > 0 and scored[1][0] == 0 and scored[2][0] == 0


# --------------------------------------------------------------------------- #
# the candidates
# --------------------------------------------------------------------------- #
def test_candidates_come_function_by_function_in_the_order_of_the_text():
    made = pointer.candidates(SOURCE, TEXT)
    order = named(pointer.order(SOURCE, TEXT))
    seen = [function.name for function, _ in made]
    assert seen[0] == order[0]
    assert [name for at, name in enumerate(seen) if at == 0 or seen[at - 1] != name] == [name for name in order[:pointer.FUNCTIONS] if name in seen]


def test_there_are_at_most_so_many_for_each_function_and_so_many_functions():
    made = pointer.candidates(SOURCE, TEXT)
    assert 0 < len(made) <= pointer.FUNCTIONS * pointer.OF_EACH
    for name in {function.name for function, _ in made}:
        assert sum(1 for function, _ in made if function.name == name) <= pointer.OF_EACH
    assert len({function.name for function, _ in made}) <= pointer.FUNCTIONS
    assert len({function.name for function, _ in pointer.candidates(SOURCE, TEXT, functions=1)}) == 1
    assert len(pointer.candidates(SOURCE, TEXT, functions=1, of_each=2)) == 2


def test_the_first_candidate_is_the_quoted_line_in_place_of_the_line_most_like_it():
    function, made = pointer.candidates(SOURCE, TEXT)[0]
    assert function.name == "RenameContentType._rename"
    assert "content_type.save(using=db, update_fields={'model'})" in made and "content_type.save(update_fields={'model'})" not in made


def test_each_candidate_is_what_the_quoted_line_list_makes_for_that_function_alone():
    for function in pointer.order(SOURCE, TEXT)[:pointer.FUNCTIONS]:
        alone = quoted.candidates(pointer.text_of(SOURCE, function), TEXT, at_most=pointer.OF_EACH)
        assert [made for f, made in pointer.candidates(SOURCE, TEXT) if f == function] == alone


def test_a_text_without_a_code_line_gives_no_candidate():
    assert pointer.candidates(SOURCE, "RenameContentType._rename saves on the wrong database") == []


# --------------------------------------------------------------------------- #
# written back into the file
# --------------------------------------------------------------------------- #
def test_a_candidate_written_into_the_file_is_a_file_that_can_be_read():
    for function, made in pointer.candidates(SOURCE, TEXT):
        ast.parse(pointer.written_into(SOURCE, function, made))


def test_only_the_lines_of_that_function_change():
    function, made = pointer.candidates(SOURCE, TEXT)[0]
    after = pointer.written_into(SOURCE, function, made).split("\n")
    before = SOURCE.split("\n")
    assert after[:function.first - 1] == before[:function.first - 1]
    assert after[len(after) - (len(before) - function.last):] == before[function.last:]


def test_a_method_keeps_its_depth_and_an_empty_line_gets_no_spaces():
    function = next(f for f in pointer.functions_of(SOURCE) if f.name == "RenameContentType._rename")
    after = pointer.written_into(SOURCE, function, "def _rename(self):\n    a = 1\n\n    return a")
    lines = after.split("\n")
    assert lines[function.first - 1] == "    def _rename(self):" and lines[function.first] == "        a = 1"
    assert lines[function.first + 1] == "" and lines[function.first + 2] == "        return a"
    ast.parse(after)


def test_writing_a_functions_own_text_back_changes_nothing_that_python_reads():
    for function in pointer.functions_of(SOURCE):
        if "." in function.name and function.name.startswith("helper"):
            continue                                                 # a function inside a function is written back with its outer one
        after = pointer.written_into(SOURCE, function, pointer.text_of(SOURCE, function))
        assert ast.dump(ast.parse(after)) == ast.dump(ast.parse(SOURCE))


def test_what_is_written_back_is_the_patched_function_in_the_tree():
    function, made = pointer.candidates(SOURCE, TEXT)[0]
    after = ast.parse(pointer.written_into(SOURCE, function, made))
    method = next(node for node in ast.walk(after) if isinstance(node, ast.FunctionDef) and node.name == "_rename")
    assert ast.unparse(method) == made


# --------------------------------------------------------------------------- #
# added after the round of seeded faults (canonical/tools/seeded_faults_function_found_v1.py):
# a scorer that only counted the shared words got past the tests above
# --------------------------------------------------------------------------- #
def test_a_rare_word_outweighs_several_words_that_stand_in_nearly_every_function():
    common = "    return common1, common2, common3, common4\n\n\n"
    source = "".join(f"def filler_{n}():\n{common}" for n in range(5)) + "def target():\n    return common1, rare\n"
    assert named(pointer.order(source, "common1 common2 common3 common4 rare"))[0] == "target"      # it shares two words, each filler four
    assert named(pointer.order(source, "common1 common2 common3 common4"))[0] == "filler_0"
