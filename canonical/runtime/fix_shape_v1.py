#!/usr/bin/env python3
"""What shape a fix has: one piece taken out, one piece put in, one leaf exchanged, one expression
exchanged -- or more than any list of single small changes can hold.

Why this exists
---------------
Twice a family of candidates was built here before anybody had asked how many real fixes it could
reach at all: an order counted from experience (EDIT_KIND_CHOICE_20261112_V1.json: no gain) and
one piece taken out (TAKE_OUT_20261112_V1.json: three repairs more, on bugs that had been made by
adding a piece). The question that comes first costs no test run. Given a buggy program and its
published fix: what is the smallest kind of change that turns the one into the other? Counted
over many real fixes, that is the ceiling of every family of single small changes, known before
any of them is built.

The shapes, the first that fits
-------------------------------
  one piece taken out        the fix is among the candidates of take_out_v1, exactly
  one piece put in           the BUGGY program is among the candidates of take_out_v1 for the
                             FIXED one: the fix puts one such piece back. This is the ceiling of
                             any family that puts one piece in, whatever it knows.
  one leaf exchanged         one name, constant, operator or attribute name for another
  one expression exchanged   the programs differ inside one expression and nowhere else
  one statement rewritten    they differ in one statement and not in a block under it: in more
                             than one expression of it, in the head of a compound statement,
                             or the statement is of another kind
  several statements at one place     one unbroken run of statements (or one clause of a try or
                             a match) added, removed or rewritten
  several places             more than one run, or more than one part of a compound statement

and what the new piece needs that the place it goes to does not hold
--------------------------------------------------------------------
  nothing        every name and constant of the new piece already stands at the place changed
  held           ... stands somewhere in the buggy program
  built in       ... is held, or is a Python builtin, or one of 0, 1, 2, True, False, None, ''
  next to it     (a constant for a constant) one more or one less than the constant replaced
  new            something the program does not hold

Operators need nothing: there are few and they can all be listed. A name counts as held whatever
it is the name of there (a variable, an attribute, an argument), which errs towards "held".

How "among the candidates" is decided without listing them for a whole file
---------------------------------------------------------------------------
Two programs that differ are the same outside the innermost block of statements that holds every
difference, and within that block outside one run of statements. Every change take_out_v1 makes
touches one statement of one block. So only that statement is handed to take_out_v1, with one
neighbour beside it so that "its block keeps a statement" is judged as in the whole program, and
with the check that a candidate compiles made on the whole fixed program instead of on the part.
One change is made on the owner of the block and not inside it, the else that is dropped; it is
recognised here directly. The test file holds all of this against the full list of candidates.

Nothing here runs a program or a test. It reads two texts.
"""
from __future__ import annotations

import ast
import builtins
import collections
import difflib
import warnings
from typing import Any

from canonical.runtime import edit_kind_learning_v1 as kinds
from canonical.runtime import take_out_v1 as take_out

SCHEMA = "BRAIN_FIX_SHAPE_V1"

UNREADABLE, SAME = "could not be read", "nothing that runs is changed"
TAKEN_OUT, PUT_IN = "one piece taken out", "one piece put in"
LEAF, EXPRESSION, STATEMENT = "one leaf exchanged", "one expression exchanged", "one statement rewritten"
ONE_PLACE, SEVERAL_PLACES = "several statements at one place", "several places"
SHAPES = (TAKEN_OUT, PUT_IN, LEAF, EXPRESSION, STATEMENT, ONE_PLACE, SEVERAL_PLACES)

NOTHING, HELD, BUILT_IN, NEXT_TO_IT, NEW = "nothing", "held", "built in", "next to it", "new"
NEEDS = (NOTHING, HELD, BUILT_IN, NEXT_TO_IT, NEW)

SMALL_PIECE = 3                    # nodes: `abs(x)` for `x` is two more, `x + 1` for `x` three
TOO_LARGE_TO_LIST = 6000           # nodes of one statement; beyond it the candidates are not listed

_OPERATORS = (ast.operator, ast.cmpop, ast.boolop, ast.unaryop)
_DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_ELSES = ("orelse", "finalbody")


def _value(value: Any) -> tuple[str, str]:
    return type(value).__name__, repr(value)


_FREE = {("name", name) for name in dir(builtins)} | {("constant",) + _value(value) for value in (0, 1, 2, True, False, None, "")}


# --------------------------------------------------------------------------- #
# two trees side by side
# --------------------------------------------------------------------------- #
def same(a: Any, b: Any) -> bool:
    """Whether two trees (or lists of trees, or plain values in a tree) are the same, wherever they stand in their files."""
    if isinstance(a, ast.AST):
        if type(a) is not type(b):
            return False
        return all(same(getattr(a, field, None), getattr(b, field, None)) for field in a._fields)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and repr(a) == repr(b)


def _is_block(a: Any, b: Any) -> bool:
    """Two lists of statements (one of them may be empty, not both)."""
    return (isinstance(a, list) and isinstance(b, list) and bool(a or b)
            and all(isinstance(item, ast.stmt) for item in a) and all(isinstance(item, ast.stmt) for item in b))


def _holds_blocks(value: Any) -> bool:
    """A list of statements, or of clauses that hold statements (the handlers of a try, the cases of a match)."""
    return isinstance(value, list) and any(isinstance(item, ast.stmt) or isinstance(getattr(item, "body", None), list) for item in value)


def descend(a: ast.AST, b: ast.AST) -> dict[str, Any]:
    """Follow the one place where two trees differ for as long as it stays one place.

    pair         the lowest two nodes outside which the trees are the same
    fields       the fields in which that pair differs; None when the two are not of one type
    places       in how many places of those fields (an item of a list of equal length is one place)
    block        the innermost two lists of statements that hold every difference
    owner        the two nodes those lists belong to, and the name of the field
    expression   the lowest two expressions on the way down, if the way led into an expression"""
    found: dict[str, Any] = {"block": None, "owner": None, "expression": None, "not_listed": False}
    while True:
        if isinstance(a, ast.expr) and isinstance(b, ast.expr):
            found["expression"] = (a, b)
        if type(a) is not type(b):
            found.update(pair=(a, b), fields=None, places=1)
            return found
        places: list[tuple[str, int | None, Any, Any]] = []
        for field in a._fields:
            x, y = getattr(a, field, None), getattr(b, field, None)
            if isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
                places += [(field, index, x, y) for index, (p, q) in enumerate(zip(x, y)) if not same(p, q)]
            elif not same(x, y):
                places.append((field, None, x, y))
        fields = {place[0] for place in places}
        if len(fields) == 1 and _is_block(places[0][2], places[0][3]):
            found.update(block=(places[0][2], places[0][3]), owner=(a, b, places[0][0]))
        if len(places) == 1:
            field, index, x, y = places[0]
            if index is not None and isinstance(x[index], ast.AST) and isinstance(y[index], ast.AST):
                a, b = x[index], y[index]
                continue
            if index is None and isinstance(x, ast.AST) and isinstance(y, ast.AST):
                a, b = x, y
                continue
        found.update(pair=(a, b), fields=fields, places=len(places))
        return found


def window(block_a: list, block_b: list) -> tuple[int, list, list]:
    """(how many statements the two blocks begin with in common, what is left of the first, what is
    left of the second) once the statements they begin and end with in common are set aside."""
    most = min(len(block_a), len(block_b))
    front = 0
    while front < most and same(block_a[front], block_b[front]):
        front += 1
    back = 0
    while back < most - front and same(block_a[len(block_a) - 1 - back], block_b[len(block_b) - 1 - back]):
        back += 1
    return front, block_a[front:len(block_a) - back], block_b[front:len(block_b) - back]


def _nodes(trees: Any) -> int:
    return sum(take_out.size(tree) for tree in (trees if isinstance(trees, list) else [trees]))


def atoms(trees: Any) -> set[tuple[str, ...]]:
    """The names and constants a piece of program is written with."""
    out: set[tuple[str, ...]] = set()
    for tree in (trees if isinstance(trees, list) else [trees]):
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                out.add(("name", node.id))
            elif isinstance(node, ast.Attribute):
                out.add(("name", node.attr))
            elif isinstance(node, ast.arg):
                out.add(("name", node.arg))
            elif isinstance(node, ast.keyword) and node.arg:
                out.add(("name", node.arg))
            elif isinstance(node, _DEFINITIONS):
                out.add(("name", node.name))
            elif isinstance(node, ast.alias):
                out.update(("name", part) for part in (node.asname or node.name).split("."))
            elif isinstance(node, ast.Constant):
                out.add(("constant",) + _value(node.value))
    return out


def needs(new: set, old: set, program: set) -> str:
    """What the new piece is written with that the piece it replaces is not."""
    wanted = new - old
    if not wanted:
        return NOTHING
    if wanted <= program:
        return HELD
    if wanted <= program | _FREE:
        return BUILT_IN
    return NEW


# --------------------------------------------------------------------------- #
# is one program among the candidates of take_out_v1 for the other
# --------------------------------------------------------------------------- #
def _module_text(body: list) -> str:
    return ast.unparse(ast.Module(body=body, type_ignores=[]))


def _written_with(trees: list) -> collections.Counter:
    """How often each name and constant is written. Taking a piece out never adds one."""
    count: collections.Counter = collections.Counter()
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                count["name", node.id] += 1
            elif isinstance(node, ast.Attribute):
                count["name", node.attr] += 1
            elif isinstance(node, ast.Constant):
                count[("constant",) + _value(node.value)] += 1
    return count


def taken_out(found: dict[str, Any], *, backwards: bool = False) -> tuple[str, int] | None:
    """(the kind of piece, how many nodes it has) when taking one piece out of the first program
    gives the second; with `backwards`, out of the second gives the first. None when it does not.
    `found` is what `descend` said of the two. Whether the result compiles is the caller's to ask.
    A statement of more than TOO_LARGE_TO_LIST nodes is not listed: `found["not_listed"]` says so."""
    if found["block"] is None:
        return None
    at, to = (1, 0) if backwards else (0, 1)
    block_from, block_to = found["block"][at], found["block"][to]
    owner = found["owner"][at]
    if block_from and not block_to:                                   # a whole block emptied: only an else can go like that
        if found["owner"][2] in _ELSES and isinstance(owner, ast.stmt) and not isinstance(owner, _DEFINITIONS):
            return take_out.NO_ELSE, _nodes(block_from)
        return None
    front, left_from, left_to = window(block_from, block_to)
    if len(left_from) != 1 or _nodes(left_from) <= _nodes(left_to):
        return None
    if _written_with(left_to) - _written_with(left_from):             # something is written that was not there: no piece taken out gives that
        return None
    if _nodes(left_from) > TOO_LARGE_TO_LIST:
        found["not_listed"] = True
        return None
    if front > 0:                                                     # one neighbour, so that the block keeps a statement where it does
        body_from, body_to = [block_from[front - 1]] + left_from, [block_from[front - 1]] + left_to
    elif front + 1 < len(block_from):
        body_from, body_to = left_from + [block_from[front + 1]], left_to + [block_from[front + 1]]
    else:
        body_from, body_to = left_from, left_to
    wanted = _module_text(body_to)
    for text, fewer, kind in take_out.candidates(_module_text(body_from), checked=False):
        if text == wanted:
            return kind, fewer
    return None


# --------------------------------------------------------------------------- #
# the shape
# --------------------------------------------------------------------------- #
def _count(value: Any) -> int:
    if isinstance(value, ast.AST):
        return take_out.size(value)
    if isinstance(value, list):
        return sum(_count(item) for item in value)
    return 0 if value is None else 1


def _leaf(found: dict[str, Any], old: set, program: set) -> dict[str, Any] | None:
    """One name, constant, operator or attribute name for another, if that is all the difference."""
    a, b = found["pair"]
    if isinstance(a, _OPERATORS) and isinstance(b, _OPERATORS):
        return {"kind": "an operator", "needs": NOTHING}
    if found["fields"] is None:
        if isinstance(a, (ast.Name, ast.Constant)) and isinstance(b, (ast.Name, ast.Constant)):
            return {"kind": "a name for a constant" if isinstance(b, ast.Name) else "a constant for a name", "needs": needs(atoms(b), old, program)}
        return None
    if found["places"] != 1:
        return None
    (field,) = found["fields"]
    x, y = getattr(a, field, None), getattr(b, field, None)
    if isinstance(a, ast.Constant) and field == "value":
        level = needs(atoms(b), old, program)
        if level == NEW and type(x) is int and type(y) is int and abs(x - y) == 1:
            level = NEXT_TO_IT
        return {"kind": "a constant", "needs": level}
    if isinstance(x, str) and isinstance(y, str):                     # the name of a variable, an attribute, an argument, a definition
        return {"kind": "an attribute name" if isinstance(a, ast.Attribute) else "a name", "needs": needs({("name", y)}, old, program)}
    return None


def _shape(before: ast.Module, after: ast.Module, buggy: str, fixed: str) -> dict[str, Any]:
    found = descend(before, after)
    program = atoms(before)
    block_a, block_b = found["block"]
    _, left_a, left_b = window(block_a, block_b)
    hit = taken_out(found)
    if hit is not None and kinds.is_a_program(fixed):
        return {"shape": TAKEN_OUT, "kind": hit[0], "needs": NOTHING, "nodes": hit[1]}
    hit = taken_out(found, backwards=True)
    if hit is not None and kinds.is_a_program(buggy):
        new, old = (block_b, block_a) if hit[0] == take_out.NO_ELSE else (left_b, left_a)
        return {"shape": PUT_IN, "kind": hit[0], "needs": needs(atoms(new), atoms(old), program), "nodes": hit[1]}
    out = {"needs": needs(atoms(left_b), atoms(left_a), program), "nodes": _nodes(left_b), "not_listed": found["not_listed"]}
    if len(left_a) == 1 and len(left_b) == 1:
        a, b = found["pair"]
        leaf = _leaf(found, atoms(left_a), program)
        if leaf is not None:
            return {**out, "shape": LEAF, "nodes": 1, **leaf}
        if found["expression"] is not None:
            old, new = found["expression"]
            return {**out, "shape": EXPRESSION, "kind": None, "needs": needs(atoms(new), atoms(old), program), "nodes": _nodes(new)}
        compound = any(_holds_blocks(getattr(node, field, None)) for node in (a, b) for field in node._fields)
        if found["fields"] is None:
            if compound:
                return {**out, "shape": ONE_PLACE, "kind": "a compound statement of another kind"}
            return {**out, "shape": STATEMENT, "kind": "another kind of statement"}
        if any(_holds_blocks(getattr(node, field, None)) for node in (a, b) for field in found["fields"]):
            if found["places"] > 1:
                return {**out, "shape": SEVERAL_PLACES, "kind": "more than one part of a compound statement"}
            return {**out, "shape": ONE_PLACE, "kind": "a clause"}
        return {**out, "shape": STATEMENT, "kind": "the head of a compound statement" if compound else None,
                "nodes": sum(_count(getattr(b, field, None)) for field in found["fields"])}
    told = [ast.dump(statement) for statement in left_a], [ast.dump(statement) for statement in left_b]
    runs = sum(1 for tag, *_ in difflib.SequenceMatcher(None, told[0], told[1], autojunk=False).get_opcodes() if tag != "equal")
    if runs > 1:
        return {**out, "shape": SEVERAL_PLACES, "kind": None}
    if not left_b:
        return {**out, "shape": ONE_PLACE, "kind": "statements taken out", "needs": NOTHING, "nodes": _nodes(left_a)}
    if not left_a:
        return {**out, "shape": ONE_PLACE, "kind": "definitions put in" if all(isinstance(item, _DEFINITIONS) for item in left_b) else "statements put in"}
    return {**out, "shape": ONE_PLACE, "kind": "statements rewritten"}


def shape(buggy: str, fixed: str) -> dict[str, Any]:
    """The shape of the fix that turns `buggy` into `fixed`: {"shape", "kind", "needs", "nodes"}.
    `nodes` is the size of the piece taken out or put in, else of what the place holds afterwards.
    "not_listed" is true when a statement was too large to ask take_out_v1 about it."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            before, after = ast.parse(buggy), ast.parse(fixed)
        if same(before, after):
            return {"shape": SAME, "kind": None, "needs": NOTHING, "nodes": 0}
        return _shape(before, after, buggy, fixed)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as error:
        return {"shape": UNREADABLE, "kind": type(error).__name__, "needs": None, "nodes": None}


def can_be_listed(found: dict[str, Any]) -> bool:
    """Whether a list of single small changes that knows nothing but the buggy program could hold
    this fix: one piece taken out; a piece of at most SMALL_PIECE nodes put in, written with what
    the program holds or Python has built in; one leaf exchanged for an operator, for something
    held or built in, or for the constant next to it. A ceiling: it says nothing of how long the list is."""
    if found["shape"] == TAKEN_OUT:
        return True
    if found["shape"] == PUT_IN:
        return found["nodes"] <= SMALL_PIECE and found["needs"] in (NOTHING, HELD, BUILT_IN)
    if found["shape"] == LEAF:
        return found["needs"] in (NOTHING, HELD, BUILT_IN, NEXT_TO_IT)
    return False
