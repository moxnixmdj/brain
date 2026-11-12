#!/usr/bin/env python3
"""The shape of a fix: what each shape is, what a new piece needs, and that "one piece taken out"
decided from the part that differs is the same as looking through the full list of take_out_v1."""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import fix_shape_v1 as fix_shape  # noqa: E402
from canonical.runtime import take_out_v1 as take_out  # noqa: E402

PROGRAM = '''import os


def f(xs, n):
    """What f does."""
    total = 0
    for x in xs:
        if x > n and x != 0:
            total += x + 1
        else:
            total -= 1
    try:
        g(total, n)
    except ValueError:
        pass
    finally:
        h()
    while n:
        n -= 1
    else:
        total = [n, 1, total]
    return sorted(xs)[1:]


class C:
    def m(self, a, b=None):
        if not a:
            return {a: 1, b: 2}
        with open(a) as fh:
            return [y for y in fh if y if b]
        return a < b < 3
'''

OTHER_PROGRAMS = (
    "x = 1\n",
    "def f(a):\n    return a\n",
    "def f(a):\n    if a:\n        return a\n",
    "def f(a):\n    if a:\n        return a\n    else:\n        return 0\n",
    "def f(a):\n    for i in a:\n        if i:\n            continue\n    return a[1:2:3]\n",
    "def f(a, b):\n    a += b\n    return max(a, b, key=len)\n",
    "def f(a):\n    try:\n        return a()\n    finally:\n        a = None\n",
    "def f(a):\n    a\n    a\n    return a\n",
    "def f(a):\n    if a:\n        if a:\n            return a\n    return a\n",
    "def f(a):\n    while a:\n        while a:\n            a -= 1\n",
)


def shape_of(old: str, new: str, program: str = PROGRAM) -> dict:
    assert old in program, old
    return fix_shape.shape(program, program.replace(old, new, 1))


# --------------------------------------------------------------------------- #
# the two shapes that are decided with take_out_v1 agree with its full list
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("program", (PROGRAM,) + OTHER_PROGRAMS)
def test_every_candidate_of_take_out_is_one_piece_taken_out_and_the_way_back_is_one_piece_put_in(program):
    listed = take_out.candidates(program)
    for text, fewer, kind in listed:
        there = fix_shape.shape(program, text)
        assert (there["shape"], there["kind"], there["nodes"]) == (fix_shape.TAKEN_OUT, kind, fewer), text
        assert there["needs"] == fix_shape.NOTHING
        back = fix_shape.shape(text, program)
        assert (back["shape"], back["kind"], back["nodes"]) == (fix_shape.PUT_IN, kind, fewer), text


def test_the_programs_have_candidates_of_every_kind_and_many():
    assert {kind for _, _, kind in take_out.candidates(PROGRAM)} == set(take_out.KINDS)
    assert sum(len(take_out.candidates(program)) for program in (PROGRAM,) + OTHER_PROGRAMS) > 90


@pytest.mark.parametrize("old,new", [
    ("total = 0", "total = 1"), ("x > n", "x >= n"), ("x > n", "x > total"), ("g(total, n)", "g(n, total)"),
    ("total += x + 1", "total += x * n"), ("return sorted(xs)[1:]", "return xs[0]"), ("n -= 1", "n -= 1\n        n -= 1\n        n -= 1"),
    ("total = 0", "total = 0\n    del n"), ("h()", "h(); k(); k()"),
])
def test_what_take_out_does_not_list_is_neither_taken_out_nor_put_in(old, new):
    changed = PROGRAM.replace(old, new, 1)
    wanted = {text for text, _, _ in take_out.candidates(PROGRAM)}
    back = {text for text, _, _ in take_out.candidates(changed)}
    import ast
    there = ast.unparse(ast.parse(changed)) in wanted
    here = ast.unparse(ast.parse(PROGRAM)) in back
    found = fix_shape.shape(PROGRAM, changed)["shape"]
    assert (found == fix_shape.TAKEN_OUT) == there
    assert (found == fix_shape.PUT_IN) == (here and not there)


def test_a_statement_alone_in_its_block_is_not_taken_out_as_a_statement():
    """take_out_v1 deletes a statement only where its block keeps one; with one neighbour handed
    over the same is decided here."""
    alone = "def f(a):\n    if a:\n        g(a)\n    return a\n"
    gone = "def f(a):\n    return a\n"
    assert fix_shape.shape(alone, gone)["kind"] == take_out.STATEMENT            # the if goes, its block keeps `return a`
    two = "def f(a):\n    g(a)\n    return a\n"
    assert fix_shape.shape(two, "def f(a):\n    return a\n") == {"shape": fix_shape.TAKEN_OUT, "kind": take_out.STATEMENT, "needs": fix_shape.NOTHING, "nodes": 4}
    assert fix_shape.shape(two, "def f(a):\n    g(a)\n")["shape"] == fix_shape.TAKEN_OUT


def test_a_piece_taken_out_that_leaves_no_program_is_not_taken_out():
    """`return` inside a function that is unwrapped to the module is not a program: take_out_v1
    never lists it, so it is not that shape here either."""
    wrapped = "if a:\n    def f():\n        return 1\n"
    assert fix_shape.shape("for i in a:\n    break\n", "break\n")["shape"] != fix_shape.TAKEN_OUT
    assert fix_shape.shape("break\n", "for i in a:\n    break\n")["shape"] != fix_shape.PUT_IN
    assert fix_shape.shape(wrapped, "def f():\n    return 1\n")["shape"] == fix_shape.TAKEN_OUT


def test_definitions_are_never_taken_out_or_put_in():
    more = PROGRAM + "\n\ndef k():\n    return 1\n"
    added = fix_shape.shape(PROGRAM, more)
    assert (added["shape"], added["kind"]) == (fix_shape.ONE_PLACE, "definitions put in")
    removed = fix_shape.shape(more, PROGRAM)
    assert (removed["shape"], removed["kind"], removed["needs"]) == (fix_shape.ONE_PLACE, "statements taken out", fix_shape.NOTHING)


def test_an_else_put_in_or_dropped():
    with_else = "def f(a):\n    if a:\n        return 1\n    else:\n        return 2\n"
    without = "def f(a):\n    if a:\n        return 1\n"
    assert fix_shape.shape(with_else, without) == {"shape": fix_shape.TAKEN_OUT, "kind": take_out.NO_ELSE, "needs": fix_shape.NOTHING, "nodes": 2}
    back = fix_shape.shape(without, with_else)
    assert (back["shape"], back["kind"], back["nodes"], back["needs"]) == (fix_shape.PUT_IN, take_out.NO_ELSE, 2, fix_shape.BUILT_IN)
    assert fix_shape.shape("def f():\n    '''d'''\n    return 1\n", "def f():\n    return 1\n")["shape"] != fix_shape.TAKEN_OUT


# --------------------------------------------------------------------------- #
# the other shapes
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("old,new,kind,level", [
    ("x > n", "x >= n", "an operator", fix_shape.NOTHING),
    ("x > n and", "x > n or", "an operator", fix_shape.NOTHING),
    ("total += x + 1", "total -= x + 1", "an operator", fix_shape.NOTHING),
    ("x > n", "x > total", "a name", fix_shape.NOTHING),          # the if holds `total` under it
    ("x > n", "x > xs", "a name", fix_shape.HELD),
    ("x > n", "x > x", "a name", fix_shape.NOTHING),
    ("x > n", "x > len", "a name", fix_shape.BUILT_IN),
    ("x > n", "x > zz", "a name", fix_shape.NEW),
    ("x + 1", "x + True", "a constant", fix_shape.BUILT_IN),
    ("x + 1", "x + 3", "a constant", fix_shape.HELD),
    ("x + 1", "x + 2", "a constant", fix_shape.HELD),
    ("x + 1", "x + 40", "a constant", fix_shape.NEW),
    ("total -= 1", "total -= 4", "a constant", fix_shape.NEW),
    ("b < 3", "b < 4", "a constant", fix_shape.NEXT_TO_IT),
    ("x + 1", "x + n", "a name for a constant", fix_shape.HELD),
    ("x > n", "x > 0", "a constant for a name", fix_shape.NOTHING),
    ("x > n", "x > 9", "a constant for a name", fix_shape.NEW),
    ("fh if y", "fh.zz if y", None, None),
    ("def f(xs, n)", "def f(xs, k)", "a name", fix_shape.NEW),
    ("def m(self", "def mm(self", "a name", fix_shape.NEW),
    ("key", "key", None, None),
])
def test_one_leaf_exchanged(old, new, kind, level):
    if kind is None:
        return
    found = shape_of(old, new)
    assert (found["shape"], found["kind"], found["needs"], found["nodes"]) == (fix_shape.LEAF, kind, level, 1)


def test_an_attribute_name_exchanged():
    program = "def f(a):\n    return a.first + a.second\n"
    held = fix_shape.shape(program, program.replace("a.first", "a.second"))
    assert (held["shape"], held["kind"], held["needs"]) == (fix_shape.LEAF, "an attribute name", fix_shape.NOTHING)
    new = fix_shape.shape(program, program.replace("a.first", "a.third"))
    assert (new["shape"], new["kind"], new["needs"]) == (fix_shape.LEAF, "an attribute name", fix_shape.NEW)
    both = fix_shape.shape(program, program.replace("a.first", "b.third"))
    assert both["shape"] == fix_shape.EXPRESSION


def test_one_expression_exchanged():
    found = shape_of("total += x + 1", "total += n * x - 3")
    assert (found["shape"], found["needs"], found["nodes"]) == (fix_shape.EXPRESSION, fix_shape.HELD, 7)
    assert shape_of("g(total, n)", "g(n, total)")["needs"] == fix_shape.NOTHING
    assert shape_of("g(total, n)", "k.g(total, n)")["shape"] == fix_shape.EXPRESSION
    assert shape_of("g(total, n)", "k.g(total, n)")["needs"] == fix_shape.NEW
    assert shape_of("sorted(xs)[1:]", "list(xs)[1:]")["shape"] == fix_shape.LEAF
    assert shape_of("[y for y in fh if y if b]", "[y for z in fh if y if b]")["shape"] == fix_shape.LEAF


def test_one_statement_rewritten():
    found = shape_of("total = 0", "n = 1")
    assert (found["shape"], found["kind"], found["needs"]) == (fix_shape.STATEMENT, None, fix_shape.HELD)
    other = shape_of("return sorted(xs)[1:]", "yield_ = sorted(xs)[1:]")
    assert (other["shape"], other["kind"]) == (fix_shape.STATEMENT, "another kind of statement")
    head = shape_of("for x in xs:", "for y in xs[1:]:")
    assert (head["shape"], head["kind"], head["nodes"]) == (fix_shape.STATEMENT, "the head of a compound statement", 5)
    assert shape_of("def m(self, a, b=None):", "def m(self, a, b=None, c=0):")["kind"] == "the head of a compound statement"
    assert shape_of("import os", "import os, sys")["shape"] == fix_shape.STATEMENT
    handler = shape_of("except ValueError:\n        pass", "except KeyError:\n        raise")
    assert (handler["shape"], handler["kind"]) == (fix_shape.SEVERAL_PLACES, "more than one part of a compound statement")


def test_a_run_in_which_a_compound_statement_was_changed_inside_is_several_places():
    two_definitions = fix_shape.shape(PROGRAM, PROGRAM.replace("total = 0", "total = 1").replace("return a < b < 3", "return a"))
    assert (two_definitions["shape"], two_definitions["kind"]) == (fix_shape.SEVERAL_PLACES, "a compound statement changed inside, and more")
    and_a_new_one = fix_shape.shape(PROGRAM, PROGRAM.replace("return a < b < 3", "return a") + "\n\ndef k():\n    return 1\n")
    assert and_a_new_one["shape"] == fix_shape.SEVERAL_PLACES
    plain = fix_shape.shape("a = 1\nb = 2\nc = 3\n", "a = 1\nx = 2\ny = 3\nc = 3\n")
    assert (plain["shape"], plain["kind"]) == (fix_shape.ONE_PLACE, "statements rewritten")
    kept = fix_shape.shape("a = 1\nif b:\n    c = 3\nd = 4\n", "a = 1\nif b:\n    c = 4\ne = 4\n")
    assert kept["shape"] == fix_shape.SEVERAL_PLACES


def test_several_statements_at_one_place():
    put = shape_of("total = 0", "total = 0\n    a = 1\n    b = 2")
    assert (put["shape"], put["kind"], put["nodes"]) == (fix_shape.ONE_PLACE, "statements put in", 6)
    rewritten = shape_of("total = 0", "a = 1\n    b = 2")
    assert (rewritten["shape"], rewritten["kind"]) == (fix_shape.ONE_PLACE, "statements rewritten")
    clause = shape_of("    finally:", "    except KeyError:\n        raise\n    finally:")
    assert (clause["shape"], clause["kind"]) == (fix_shape.ONE_PLACE, "a clause")
    kind = shape_of("while n:", "for n in xs:")
    assert (kind["shape"], kind["kind"]) == (fix_shape.ONE_PLACE, "a compound statement of another kind")
    out = fix_shape.shape("def f(a):\n    a = 1\n    b = 2\n    c = 3\n    return a\n", "def f(a):\n    a = 1\n    return a\n")
    assert (out["shape"], out["kind"], out["needs"], out["nodes"]) == (fix_shape.ONE_PLACE, "statements taken out", fix_shape.NOTHING, 6)


def test_several_places():
    assert fix_shape.shape(PROGRAM, PROGRAM.replace("total = 0", "total = 1").replace("h()", "h(1)"))["shape"] == fix_shape.SEVERAL_PLACES
    both = shape_of("if x > n and x != 0:\n            total += x + 1", "if x > total:\n            total += x + 2")
    assert (both["shape"], both["kind"]) == (fix_shape.SEVERAL_PLACES, "more than one part of a compound statement")
    two_blocks = shape_of("            total += x + 1\n        else:\n            total -= 1", "            total += x + 2\n        else:\n            total -= 2")
    assert (two_blocks["shape"], two_blocks["kind"]) == (fix_shape.SEVERAL_PLACES, "more than one part of a compound statement")
    two_handlers = "try:\n    a()\nexcept A:\n    b()\nexcept B:\n    c()\n"
    assert fix_shape.shape(two_handlers, two_handlers.replace("b()", "bb()").replace("c()", "cc()"))["shape"] == fix_shape.SEVERAL_PLACES
    assert fix_shape.shape(two_handlers, two_handlers.replace("b()", "bb()"))["shape"] == fix_shape.LEAF


def test_what_changes_nothing_that_runs_and_what_cannot_be_read():
    assert fix_shape.shape(PROGRAM, PROGRAM.replace("total = 0", "total = 0  # said"))["shape"] == fix_shape.SAME
    assert fix_shape.shape(PROGRAM, PROGRAM)["shape"] == fix_shape.SAME
    assert fix_shape.shape("def (", PROGRAM)["shape"] == fix_shape.UNREADABLE
    assert fix_shape.shape(PROGRAM, "def (") == {"shape": fix_shape.UNREADABLE, "kind": "SyntaxError", "needs": None, "nodes": None}
    assert set(fix_shape.shape(PROGRAM, PROGRAM.replace("total = 0", "total = 1"))) >= {"shape", "kind", "needs", "nodes"}


# --------------------------------------------------------------------------- #
# what the new piece needs
# --------------------------------------------------------------------------- #
def test_needs_is_the_first_level_that_holds_everything_new():
    program = {("name", "a"), ("name", "b"), ("constant", "int", "7")}
    old = {("name", "a")}
    assert fix_shape.needs({("name", "a")}, old, program) == fix_shape.NOTHING
    assert fix_shape.needs(set(), old, program) == fix_shape.NOTHING
    assert fix_shape.needs({("name", "a"), ("name", "b")}, old, program) == fix_shape.HELD
    assert fix_shape.needs({("constant", "int", "7")}, old, program) == fix_shape.HELD
    assert fix_shape.needs({("name", "b"), ("name", "len")}, old, program) == fix_shape.BUILT_IN
    assert fix_shape.needs({("constant", "int", "0")}, old, program) == fix_shape.BUILT_IN
    assert fix_shape.needs({("constant", "bool", "True")}, old, program) == fix_shape.BUILT_IN
    assert fix_shape.needs({("constant", "int", "8")}, old, program) == fix_shape.NEW
    assert fix_shape.needs({("name", "b"), ("name", "zz")}, old, program) == fix_shape.NEW


def test_a_constant_is_told_from_another_of_the_same_look():
    """1 and True and 1.0 are three constants; a program that holds 1 does not hold 1.0."""
    program = "def f(a):\n    return a + 5\n"
    assert fix_shape.shape(program, program.replace("a + 5", "a + 5.0"))["needs"] == fix_shape.NEW
    assert fix_shape.same(1, 1) and not fix_shape.same(1, True) and not fix_shape.same(1, 1.0)
    assert fix_shape.shape("x = 1\n", "x = True\n")["shape"] == fix_shape.LEAF
    assert fix_shape.shape("x = 1\n", "x = 1.0\n")["shape"] == fix_shape.LEAF


def test_atoms_are_the_names_and_constants_written():
    import ast
    tree = ast.parse("import os.path as p\nfrom a import b\ndef f(x, *, k=1):\n    return g(x.y, key=k, z='s')\n")
    got = fix_shape.atoms(tree)
    for name in ("p", "b", "f", "x", "k", "g", "y", "key", "z"):
        assert ("name", name) in got, name
    assert ("constant", "int", "1") in got and ("constant", "str", "'s'") in got
    assert ("name", "os") not in got and ("name", "a") not in got


def test_put_in_says_what_the_piece_needs_and_how_large_it_is():
    program = "def f(a, b):\n    c = a\n    return c\n"
    assert fix_shape.shape(program, program.replace("c = a", "c = abs(a)")) == {"shape": fix_shape.PUT_IN, "kind": take_out.ONE_INSIDE, "needs": fix_shape.BUILT_IN, "nodes": 2}
    assert fix_shape.shape(program, program.replace("c = a", "c = a + b")) == {"shape": fix_shape.PUT_IN, "kind": take_out.ONE_INSIDE, "needs": fix_shape.HELD, "nodes": 3}
    assert fix_shape.shape(program, program.replace("c = a", "c = a + a"))["needs"] == fix_shape.NOTHING
    assert fix_shape.shape(program, program.replace("c = a", "c = a + 17"))["needs"] == fix_shape.NEW
    statement = fix_shape.shape(program, program.replace("    return c", "    if c < 0:\n        return 0\n    return c"))
    assert (statement["shape"], statement["kind"], statement["needs"], statement["nodes"]) == (fix_shape.PUT_IN, take_out.STATEMENT, fix_shape.BUILT_IN, 7)
    plain = fix_shape.shape("def f(a, b):\n    a = b\n    return a\n", "def f(a, b):\n    a += b\n    return a\n")
    assert (plain["shape"], plain["kind"], plain["nodes"]) == (fix_shape.PUT_IN, take_out.PLAIN_ASSIGNMENT, 1)


# --------------------------------------------------------------------------- #
# what can be listed
# --------------------------------------------------------------------------- #
def test_can_be_listed():
    program = "def f(a, b):\n    c = a\n    return c\n"
    def listed(new: str, old: str = "c = a") -> bool:
        return fix_shape.can_be_listed(fix_shape.shape(program, program.replace(old, new)))
    assert listed("c = abs(a)") and listed("c = a + b") and listed("c = b") and listed("c = len")
    assert listed("pass", "c = a") is False                                     # a statement rewritten
    assert not listed("c = a + 17")                                             # needs something new
    assert not listed("c = a + b + 1")                                          # a piece of more than three nodes
    assert not listed("c = zz")
    assert not listed("c = b * (a - b)")
    assert fix_shape.can_be_listed(fix_shape.shape("def f(a):\n    g(a)\n    return a\n", "def f(a):\n    return a\n"))
    assert fix_shape.can_be_listed({"shape": fix_shape.LEAF, "needs": fix_shape.NEXT_TO_IT, "nodes": 1})
    assert not fix_shape.can_be_listed({"shape": fix_shape.LEAF, "needs": fix_shape.NEW, "nodes": 1})
    assert not fix_shape.can_be_listed({"shape": fix_shape.PUT_IN, "needs": fix_shape.HELD, "nodes": fix_shape.SMALL_PIECE + 1})
    assert fix_shape.can_be_listed({"shape": fix_shape.PUT_IN, "needs": fix_shape.HELD, "nodes": fix_shape.SMALL_PIECE})
    assert not fix_shape.can_be_listed({"shape": fix_shape.PUT_IN, "needs": fix_shape.NEXT_TO_IT, "nodes": 1})
    for name in (fix_shape.EXPRESSION, fix_shape.STATEMENT, fix_shape.ONE_PLACE, fix_shape.SEVERAL_PLACES):
        assert not fix_shape.can_be_listed({"shape": name, "needs": fix_shape.NOTHING, "nodes": 1})


# --------------------------------------------------------------------------- #
# the parts
# --------------------------------------------------------------------------- #
def test_descend_finds_the_innermost_block_and_the_lowest_pair():
    import ast
    before = ast.parse(PROGRAM)
    after = ast.parse(PROGRAM.replace("total -= 1", "total -= x"))
    found = fix_shape.descend(before, after)
    assert [type(node).__name__ for node in found["pair"]] == ["Constant", "Name"] and found["fields"] is None and found["places"] == 1
    assert found["owner"][2] == "orelse" and type(found["owner"][0]).__name__ == "If"
    assert [type(node).__name__ for node in found["expression"]] == ["Constant", "Name"]
    two = fix_shape.descend(before, ast.parse(PROGRAM.replace("total = 0", "total = 1").replace("h()", "h(1)")))
    assert type(two["pair"][0]).__name__ == "FunctionDef" and two["fields"] == {"body"} and two["places"] == 2
    assert two["owner"][2] == "body" and two["expression"] is None


def test_window_sets_aside_what_two_blocks_begin_and_end_with():
    import ast
    a = ast.parse("a\nb\nc\nd\n").body
    assert [len(part) if isinstance(part, list) else part for part in fix_shape.window(a, ast.parse("a\nx\nd\n").body)] == [1, 2, 1]
    assert [len(part) if isinstance(part, list) else part for part in fix_shape.window(a, ast.parse("a\nb\nc\nd\ne\n").body)] == [4, 0, 1]
    assert [len(part) if isinstance(part, list) else part for part in fix_shape.window(a, ast.parse("b\nc\nd\n").body)] == [0, 1, 0]
    same = ast.parse("a\na\n").body
    assert [len(part) if isinstance(part, list) else part for part in fix_shape.window(same, ast.parse("a\n").body)] == [1, 1, 0]


def test_a_statement_too_large_is_said_not_to_have_been_listed(monkeypatch):
    program = "def f(a, b):\n    c = a + b + 1\n    return c\n"
    assert fix_shape.shape(program, program.replace("a + b + 1", "a + b"))["shape"] == fix_shape.TAKEN_OUT
    monkeypatch.setattr(fix_shape, "TOO_LARGE_TO_LIST", 3)
    found = fix_shape.shape(program, program.replace("a + b + 1", "a + b"))
    assert found["shape"] != fix_shape.TAKEN_OUT and found["not_listed"] is True
    assert fix_shape.shape(program, program.replace("a + b + 1", "a + b + 2")).get("not_listed") is False


def test_nothing_is_run():
    """Two texts are read. A program that would do harm if it ran is given a shape like any other."""
    harm = "import os\nos.remove('/nonexistent/never')\nraise SystemExit(3)\n"
    assert fix_shape.shape(harm, harm.replace("3", "4"))["shape"] == fix_shape.LEAF
