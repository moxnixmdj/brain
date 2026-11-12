#!/usr/bin/env python3
"""What KIND of change a fix was, kept from the one fix, and every place that kind of change
could be made in another program.

Why this exists
---------------
Measured 2026-11-11 on 40 bugs written by other people (QuixBugs): this tree's memory of fixes
repeats a fix it has seen (22 of 22) and repairs a different bug from it in 1 to 3 of 858
pairs; its repair search finds 5 of 40 and the fixes of all the other bugs, taught first, make
that 6. What is kept from a fix there is the fix: a token pattern tied to the statement it was
seen in (operator_generalization_v1 widens exactly one case, the swap of a single operator).

This module keeps the kind of change instead. From one fix -- the program before and after --
it finds the smallest part of the syntax tree that holds everything that changed and writes
that change down several times, from "exactly this" to "this, anywhere":

    as it was
    names and constants of the changed part left open (builtins stay what they are)
    every part the change did not touch left open
    both
    both, and the names the change brought in are taken from the program it is applied to
    the same, and the attributes it brought in as well

each one also with more or less of what stood around it (nothing; the same position, such as
"the test of a while"; the enclosing expression; the enclosing statement). Every such writing
is an OPERATOR: a shape that has to be there, a shape that is put there, and holes. A statement
that a fix added or took out becomes an operator that adds or takes out such a statement.

Given another program, each operator is tried at every place its first shape fits. Every lesson
then votes once for each candidate program: with one over the number of candidates made by the
most exact of its operators that makes this one. Candidates are ordered by the sum of the votes.
Nothing here accepts a candidate -- the caller's tests do, one candidate at a time -- and
nothing here is taught by hand: an operator exists only because some fix was shown.

It is the technique of Getafix (Bader et al., OOPSLA 2019: fix patterns by anti-unification,
general to specific) and Refazer (Rolim et al., ICSE 2017), cut down to what ONE example
supports: with a single fix there is no second one to say how far to generalise, so every
level is kept and the tests choose.
"""
from __future__ import annotations

import ast
import builtins
import copy
import itertools
import warnings
from dataclasses import dataclass, field
from typing import Any, Iterator, Sequence

SCHEMA = "BRAIN_EDIT_KIND_LEARNING_V1"

BUILTINS = frozenset(dir(builtins))
_IGNORED = ("ctx", "type_comment", "kind")
_NOT_ENTERED = ("annotation", "returns")     # type hints: a change there changes nothing that runs
_BODIES = ("body", "orelse", "finalbody")
_SIMPLE = (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Return, ast.Expr, ast.Assert, ast.Raise, ast.Delete)

# how open a writing of the change is, from the fix exactly as it was to the most general one
AS_IT_WAS, NAMES_OPEN, UNTOUCHED_OPEN, BOTH_OPEN, FROM_THE_PLACE, ATTRIBUTES_TOO, ANY_STATEMENT = (
    "as_it_was", "names_open", "untouched_open", "both_open", "from_the_place", "attributes_too", "any_statement")
OPENNESS = (AS_IT_WAS, NAMES_OPEN, UNTOUCHED_OPEN, BOTH_OPEN, FROM_THE_PLACE, ATTRIBUTES_TOO, ANY_STATEMENT)
# how much of what stood around the change is kept
ALONE, SAME_POSITION, IN_ITS_EXPRESSION, IN_ITS_STATEMENT = "alone", "same_position", "in_its_expression", "in_its_statement"
SURROUNDINGS = (IN_ITS_STATEMENT, IN_ITS_EXPRESSION, SAME_POSITION, ALONE)

MAX_FREE_HOLES = 2            # an operator that takes more than two things from the place is not written
MAX_CANDIDATES_OF_ONE = 300   # an operator that would make more candidates than this in a program says too
                              # little about that program: it is not applied to it at all


# --------------------------------------------------------------------------- #
# trees
# --------------------------------------------------------------------------- #
def key(node: Any) -> str:
    """A tree as text: equal texts, equal trees (load/store and positions do not count)."""
    if isinstance(node, ast.AST):
        parts = [name + "=" + key(getattr(node, name, None)) for name in node._fields if name not in _IGNORED]
        return type(node).__name__ + "(" + ",".join(parts) + ")"
    if isinstance(node, list):
        return "[" + ",".join(key(item) for item in node) + "]"
    return type(node).__name__ + ":" + repr(node)


def _hole(kind: str, number: int) -> str:
    return f"__{kind}{number}__"


def hole_kind(text: Any) -> str | None:
    """'E' any expression, 'N' a name, 'C' a constant, 'F' a name taken from the place, 'A' an
    attribute taken from the place, 'S' any statement; None when the text is no hole."""
    if isinstance(text, str) and len(text) > 5 and text.startswith("__") and text.endswith("__") \
            and text[2] in "ENCFAS" and text[3:-2].isdigit():
        return text[2]
    return None


def _node_hole(node: Any) -> str | None:
    """The hole a pattern node stands for, when the whole node is one."""
    if isinstance(node, ast.Name) and hole_kind(node.id) in ("E", "N", "F"):
        return node.id
    if isinstance(node, ast.Constant) and hole_kind(node.value) == "C":
        return node.value
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Name) and hole_kind(node.value.id) == "S":
        return node.value.id
    return None


def _children(node: ast.AST) -> Iterator[tuple[str, int | None, ast.AST]]:
    for name in node._fields:
        value = getattr(node, name, None)
        if isinstance(value, ast.AST):
            yield name, None, value
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, ast.AST):
                    yield name, index, item


def _step(node: ast.AST, step: tuple[str, int | None]) -> ast.AST:
    value = getattr(node, step[0])
    return value if step[1] is None else value[step[1]]


def _put(tree: ast.AST, path: Sequence[tuple[str, int | None]], new: ast.AST) -> None:
    node = tree
    for step in path[:-1]:
        node = _step(node, step)
    name, index = path[-1]
    if index is None:
        setattr(node, name, new)
    else:
        getattr(node, name)[index] = new


def walk(node: ast.AST, path: tuple = (), position: tuple[str, str] | None = None) -> Iterator[tuple[tuple, ast.AST, tuple[str, str] | None]]:
    """Every node with the path to it and its position (the sort of node it sits in, and where there)."""
    yield path, node, position
    for name, index, child in _children(node):
        if name not in _NOT_ENTERED:
            yield from walk(child, path + ((name, index),), (type(node).__name__, name))


# --------------------------------------------------------------------------- #
# where a fix changed the program
# --------------------------------------------------------------------------- #
def locate(before: ast.AST, after: ast.AST) -> tuple[list[tuple[str, int | None]], str | None] | None:
    """The path to the smallest node that holds everything that differs, and -- when what differs
    there is the LENGTH of a list of statements -- the name of that list. None when nothing differs."""
    if key(before) == key(after):
        return None
    path: list[tuple[str, int | None]] = []
    a, b = before, after
    while type(a) is type(b):
        differing: list[tuple[str, int | None]] = []
        here = False
        lengths: list[str] = []
        for name in a._fields:
            if name in _IGNORED:
                continue
            x, y = getattr(a, name, None), getattr(b, name, None)
            if isinstance(x, list) and isinstance(y, list):
                if len(x) != len(y):
                    lengths.append(name)
                    continue
                for index, (p, q) in enumerate(zip(x, y)):
                    if key(p) != key(q):
                        if isinstance(p, ast.AST) and isinstance(q, ast.AST):
                            differing.append((name, index))
                        else:
                            here = True
            elif key(x) != key(y):
                if isinstance(x, ast.AST) and isinstance(y, ast.AST):
                    differing.append((name, None))
                else:
                    here = True                      # a name or a value of this very node changed
        if lengths:
            only = len(lengths) == 1 and not differing and not here and lengths[0] in _BODIES
            return path, (lengths[0] if only else None)
        if here or len(differing) != 1:
            break
        path.append(differing[0])
        a, b = _step(a, differing[0]), _step(b, differing[0])
    return path, None


def _one_statement_more(short: list, long_: list) -> int | None:
    """Where the one statement stands that `long_` has and `short` has not; None if that is not the difference."""
    if len(long_) != len(short) + 1:
        return None
    at = 0
    while at < len(short) and key(short[at]) == key(long_[at]):
        at += 1
    return at if all(key(short[i]) == key(long_[i + 1]) for i in range(at, len(short))) else None


# --------------------------------------------------------------------------- #
# writing a change down with holes
# --------------------------------------------------------------------------- #
def _rewritten(node: Any, change) -> Any:
    """A copy of the tree in which `change(node)` may put something else in a node's place."""
    replaced = change(node)
    if replaced is not None:
        return replaced
    if isinstance(node, ast.AST):
        new = copy.copy(node)
        for name in node._fields:
            value = getattr(node, name, None)
            if isinstance(value, ast.AST):
                setattr(new, name, _rewritten(value, change))
            elif isinstance(value, list):
                setattr(new, name, [_rewritten(item, change) if isinstance(item, ast.AST) else item for item in value])
        return new
    return node


def _open_untouched(before: ast.AST, after: ast.AST) -> tuple[ast.AST, ast.AST]:
    """Every largest expression the two sides share becomes a hole for any expression -- the same
    hole on both sides, and the same hole wherever the same expression stands."""
    shared = {key(n) for n in ast.walk(after) if isinstance(n, ast.expr)} & {key(n) for n in ast.walk(before) if isinstance(n, ast.expr)}
    numbers: dict[str, int] = {}

    def on_the_before_side(node):
        if isinstance(node, ast.expr) and _node_hole(node) is None and key(node) in shared:
            return ast.Name(id=_hole("E", numbers.setdefault(key(node), len(numbers))), ctx=ast.Load())
        return None

    def on_the_after_side(node):
        if isinstance(node, ast.expr) and key(node) in numbers:
            return ast.Name(id=_hole("E", numbers[key(node)]), ctx=ast.Load())
        return None

    return _rewritten(before, on_the_before_side), _rewritten(after, on_the_after_side)


def _open_names(before: ast.AST, after: ast.AST, new_names: bool = False, new_attributes: bool = False) -> tuple[ast.AST, ast.AST]:
    """Names and constants of the before side become holes (a builtin stays what it is); the after
    side uses the same holes. What only the after side has stays as written, or -- when asked --
    its names (`new_names`) and its attributes (`new_attributes`) become holes to be filled from
    the program the operator is applied to."""
    names: dict[str, str] = {}
    constants: dict[str, str] = {}
    attributes_before = {n.attr for n in ast.walk(before) if isinstance(n, ast.Attribute)}
    free_names: dict[str, str] = {}
    free_attributes: dict[str, str] = {}

    def a_name(text: str) -> str | None:
        if hole_kind(text) or text in BUILTINS:
            return None
        return names.setdefault(text, _hole("N", len(names)))

    def on_the_before_side(node):
        if isinstance(node, ast.Name) and a_name(node.id):
            return ast.Name(id=a_name(node.id), ctx=ast.Load())
        if isinstance(node, ast.arg) and a_name(node.arg):
            return ast.arg(arg=a_name(node.arg), annotation=node.annotation)
        if isinstance(node, ast.Constant) and hole_kind(node.value) is None:
            return ast.Constant(value=constants.setdefault(key(node), _hole("C", len(constants))))
        return None

    def a_new_name(text: str) -> str | None:
        if text in names:
            return names[text]
        if new_names and not hole_kind(text) and text not in BUILTINS:
            return free_names.setdefault(text, _hole("F", len(free_names)))
        return None

    def on_the_after_side(node):
        if isinstance(node, ast.Name) and a_new_name(node.id):
            return ast.Name(id=a_new_name(node.id), ctx=ast.Load())
        if isinstance(node, ast.arg) and a_new_name(node.arg):
            return ast.arg(arg=a_new_name(node.arg), annotation=node.annotation)
        if isinstance(node, ast.Constant) and key(node) in constants:
            return ast.Constant(value=constants[key(node)])
        if isinstance(node, ast.Attribute) and new_attributes and node.attr not in attributes_before and not hole_kind(node.attr):
            hole = free_attributes.setdefault(node.attr, _hole("A", len(free_attributes)))
            return ast.Attribute(value=_rewritten(node.value, on_the_after_side), attr=hole, ctx=ast.Load())
        return None

    new_before = _rewritten(before, on_the_before_side)
    return new_before, _rewritten(after, on_the_after_side)


def _every_node(node: ast.AST) -> Iterator[ast.AST]:
    """Every node, type hints too, parents before children, in the order of the text."""
    yield node
    for _, _, child in _children(node):
        yield from _every_node(child)


def _holes_in_order(*trees: ast.AST | None) -> list[str]:
    seen: list[str] = []
    for tree in trees:
        if tree is None:
            continue
        for node in _every_node(tree):
            for text in (getattr(node, "id", None), getattr(node, "arg", None), getattr(node, "attr", None), getattr(node, "value", None)):
                if hole_kind(text) and text not in seen:
                    seen.append(text)
    return seen


def _renumbered(before: ast.AST | None, after: ast.AST | None) -> tuple[ast.AST | None, ast.AST | None]:
    """Holes numbered in the order they appear, so that the same operator read off two fixes is the same text."""
    counts: dict[str, int] = {}
    fresh: dict[str, str] = {}
    for text in _holes_in_order(before, after):
        kind = hole_kind(text)
        fresh[text] = _hole(kind, counts.get(kind, 0))
        counts[kind] = counts.get(kind, 0) + 1

    def change(node):
        new = None
        for name in ("id", "arg", "attr", "value"):
            text = getattr(node, name, None)
            if hole_kind(text):
                new = new or copy.copy(node)
                setattr(new, name, fresh[text])
        if new is not None:
            for name, _, child in _children(node):
                value = getattr(node, name)
                if isinstance(value, ast.AST):
                    setattr(new, name, _rewritten(value, change))
                else:
                    setattr(new, name, [_rewritten(item, change) if isinstance(item, ast.AST) else item for item in value])
        return new

    return (None if before is None else _rewritten(before, change)), (None if after is None else _rewritten(after, change))


@dataclass(frozen=True)
class Operator:
    """One writing of one kind of change."""
    what: str                                  # "replace" | "insert" | "delete"
    before: ast.AST | None = field(compare=False)
    after: ast.AST | None = field(compare=False)
    position: tuple[str, str] | None           # where it has to sit, when the lesson's position is kept
    surroundings: str = field(compare=False)
    openness: str = field(compare=False)
    text: str = ""                             # the operator as text: equal texts, equal operators

    @property
    def free(self) -> list[str]:
        return [h for h in _holes_in_order(self.after) if hole_kind(h) in ("F", "A")]

    def shown(self) -> str:
        def side(tree):
            return "" if tree is None else ast.unparse(tree).replace("\n", " ; ")
        where = f"  [at {self.position[0]}.{self.position[1]}]" if self.position else ""
        return f"{self.what}: {side(self.before)}  ->  {side(self.after)}{where}"


def _operator(what, before, after, position, surroundings, openness) -> Operator | None:
    before, after = _renumbered(before, after)
    if what == "replace" and key(before) == key(after):
        return None
    made = Operator(what, before, after, position, surroundings, openness,
                    text=what + "|" + key(before) + "|" + key(after) + "|" + repr(position))
    return None if len(made.free) > MAX_FREE_HOLES else made


def _writings(before: ast.AST, after: ast.AST) -> list[tuple[str, ast.AST, ast.AST]]:
    untouched = _open_untouched(before, after)
    return [(AS_IT_WAS, before, after),
            (NAMES_OPEN, *_open_names(before, after)),
            (UNTOUCHED_OPEN, *untouched),
            (BOTH_OPEN, *_open_names(*untouched)),
            (FROM_THE_PLACE, *_open_names(*untouched, new_names=True)),
            (ATTRIBUTES_TOO, *_open_names(*untouched, new_names=True, new_attributes=True))]


def operators_of(before_source: str, after_source: str) -> list[Operator]:
    """Every writing of the change that turns the first program into the second. An empty list
    when the two are the same program, or when either cannot be read."""
    try:
        before, after = ast.parse(before_source), ast.parse(after_source)
    except (SyntaxError, ValueError, RecursionError):
        return []
    found = locate(before, after)
    if found is None:
        return []
    path, in_list = found
    chain_before, chain_after = [before], [after]
    for step in path:
        chain_before.append(_step(chain_before[-1], step))
        chain_after.append(_step(chain_after[-1], step))
    made: list[Operator] = []

    if in_list is not None:                                    # one statement more, or one fewer
        owner_before, owner_after = chain_before[-1], chain_after[-1]
        x, y = getattr(owner_before, in_list), getattr(owner_after, in_list)
        position = (type(owner_before).__name__, in_list)
        added = _one_statement_more(x, y)
        removed = _one_statement_more(y, x)
        if added is not None:
            statement = y[added]
            for where in (position, None):
                around = SAME_POSITION if where else ALONE
                made.append(_operator("insert", None, statement, where, around, AS_IT_WAS))
                made.append(_operator("insert", None, _open_names(ast.Pass(), statement, new_names=True)[1], where, around, FROM_THE_PLACE))
                made.append(_operator("insert", None, _open_names(ast.Pass(), statement, new_names=True, new_attributes=True)[1],
                                      where, around, ATTRIBUTES_TOO))
        elif removed is not None:
            statement = x[removed]
            any_statement = ast.Expr(value=ast.Name(id=_hole("S", 0), ctx=ast.Load()))
            for where in (position, None):
                made.append(_operator("delete", statement, None, where, SAME_POSITION if where else ALONE, AS_IT_WAS))
                made.append(_operator("delete", _open_names(statement, ast.Pass())[0], None, where,
                                      SAME_POSITION if where else ALONE, NAMES_OPEN))
                made.append(_operator("delete", any_statement, None, where, SAME_POSITION if where else ALONE, ANY_STATEMENT))
        if added is not None or removed is not None:
            return _distinct(made)

    # the changed part: the smallest expression or statement that holds the change
    depth = len(chain_before) - 1
    while depth > 0 and not isinstance(chain_before[depth], (ast.expr, ast.stmt)):
        depth -= 1
    if not isinstance(chain_before[depth], (ast.expr, ast.stmt)) or type(chain_before[depth]).__bases__[0] is not type(chain_after[depth]).__bases__[0]:
        return []
    part_before, part_after = chain_before[depth], chain_after[depth]
    position = None
    if depth > 0:
        position = (type(chain_before[depth - 1]).__name__, path[depth - 1][0])
    for openness, b, a in _writings(part_before, part_after):
        made.append(_operator("replace", b, a, None, ALONE, openness))
        if position is not None:
            made.append(_operator("replace", b, a, position, SAME_POSITION, openness))
    if isinstance(part_before, ast.expr):
        above = depth - 1
        while above > 0 and not isinstance(chain_before[above], (ast.expr, ast.stmt)):
            above -= 1
        if above > 0 and isinstance(chain_before[above], ast.expr):
            for openness, b, a in _writings(chain_before[above], chain_after[above]):
                made.append(_operator("replace", b, a, None, IN_ITS_EXPRESSION, openness))
        statement = depth - 1
        while statement > 0 and not isinstance(chain_before[statement], ast.stmt):
            statement -= 1
        if statement > 0 and isinstance(chain_before[statement], _SIMPLE):
            for openness, b, a in _writings(chain_before[statement], chain_after[statement]):
                made.append(_operator("replace", b, a, None, IN_ITS_STATEMENT, openness))
    return _distinct(made)


def _distinct(operators: Sequence[Operator | None]) -> list[Operator]:
    seen: dict[str, Operator] = {}
    for operator in operators:
        if operator is not None and operator.text not in seen:
            seen[operator.text] = operator
    return list(seen.values())


# --------------------------------------------------------------------------- #
# fitting a shape to a place, and building what is put there
# --------------------------------------------------------------------------- #
def fits(pattern: Any, node: Any, bound: dict[str, Any]) -> bool:
    """Whether the shape fits the node; what its holes stand for is written into `bound`."""
    hole = _node_hole(pattern)
    if hole is not None:
        kind = hole_kind(hole)
        if kind == "E":
            if not isinstance(node, ast.expr):
                return False
            if hole in bound:
                return key(bound[hole]) == key(node)
            bound[hole] = node
            return True
        if kind == "S":
            if not isinstance(node, ast.stmt):
                return False
            bound[hole] = node
            return True
        if kind == "C":
            if not isinstance(node, ast.Constant):
                return False
            if hole in bound:
                return key(bound[hole]) == key(node)
            bound[hole] = node
            return True
        if not isinstance(node, ast.Name):
            return False
        return _same_text(hole, node.id, bound)
    if type(pattern) is not type(node):
        return False
    if isinstance(pattern, ast.AST):
        for name in pattern._fields:
            if name in _IGNORED:
                continue
            x, y = getattr(pattern, name, None), getattr(node, name, None)
            if isinstance(x, str) and hole_kind(x) in ("N",):
                if not isinstance(y, str) or not _same_text(x, y, bound):
                    return False
            elif isinstance(x, (ast.AST, list)):
                if not fits(x, y, bound):
                    return False
            elif key(x) != key(y):
                return False
        return True
    if isinstance(pattern, list):
        return len(pattern) == len(node) and all(fits(p, q, bound) for p, q in zip(pattern, node))
    return key(pattern) == key(node)


def _same_text(hole: str, text: str, bound: dict[str, Any]) -> bool:
    if hole in bound:
        return bound[hole] == text
    bound[hole] = text
    return True


def built(pattern: Any, bound: dict[str, Any]) -> Any:
    """The shape with its holes filled in."""
    hole = _node_hole(pattern)
    if hole is not None:
        value = bound[hole]
        return ast.Name(id=value, ctx=ast.Load()) if isinstance(value, str) else copy.deepcopy(value)
    if isinstance(pattern, ast.AST):
        new = copy.copy(pattern)
        for name in pattern._fields:
            value = getattr(pattern, name, None)
            if isinstance(value, str) and hole_kind(value) in ("N", "F", "A"):
                setattr(new, name, bound[value])
            elif isinstance(value, ast.AST):
                setattr(new, name, built(value, bound))
            elif isinstance(value, list):
                setattr(new, name, [built(item, bound) if isinstance(item, ast.AST) else item for item in value])
        return new
    return pattern


class Place:
    """A program an operator may be applied to, read once."""

    def __init__(self, source: str) -> None:
        self.tree = ast.parse(source)
        self.original = ast.unparse(self.tree)
        self.nodes = [(path, node, position) for path, node, position in walk(self.tree) if path]
        self.by_type: dict[type, list[tuple[tuple, ast.AST, tuple[str, str] | None]]] = {}
        for row in self.nodes:
            self.by_type.setdefault(type(row[1]), []).append(row)
        self.names: list[str] = []
        self.attributes: list[str] = []
        for _, node, _ in self.nodes:
            text = node.id if isinstance(node, ast.Name) else node.arg if isinstance(node, ast.arg) else None
            if text is not None and text not in BUILTINS and text not in self.names:
                self.names.append(text)
            if isinstance(node, ast.Attribute) and node.attr not in self.attributes:
                self.attributes.append(node.attr)
        self.bodies = [(path, node, name) for path, node, _ in [((), self.tree, None)] + self.nodes for name in _BODIES
                       if isinstance(getattr(node, name, None), list) and getattr(node, name)
                       and all(isinstance(s, ast.stmt) for s in getattr(node, name))]

    def where(self, pattern: ast.AST | None) -> list[tuple[tuple, ast.AST, tuple[str, str] | None]]:
        """The nodes a shape could fit at all: those of its own sort, or every node when it is a hole."""
        hole = _node_hole(pattern)
        if hole is None:
            return self.by_type.get(type(pattern), [])
        if hole_kind(hole) == "N":
            return self.by_type.get(ast.Name, [])
        if hole_kind(hole) == "C":
            return self.by_type.get(ast.Constant, [])
        wanted = ast.stmt if hole_kind(hole) == "S" else ast.expr
        return [row for row in self.nodes if isinstance(row[1], wanted)]


def _fillings(operator: "Operator", place: Place) -> list[dict[str, str]]:
    free = operator.free
    choices = [place.names if hole_kind(h) == "F" else place.attributes for h in free]
    return [dict(zip(free, chosen)) for chosen in itertools.product(*choices)]


def is_a_program(text: str) -> bool:
    """Whether the text compiles. A candidate that does not is never worth a run of the tests."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            compile(text, "<candidate>", "exec", dont_inherit=True)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return False
    return True


def candidates(operator: Operator, place: Place | str, at_most: int = MAX_CANDIDATES_OF_ONE) -> list[str]:
    """Every text the operator makes of this program, each once, never the program itself. Not
    every one need compile (`is_a_program` says). An empty list when the operator fits nowhere --
    and when it would make more than `at_most` candidates, because then it is not applied at all."""
    if isinstance(place, str):
        try:
            place = Place(place)
        except (SyntaxError, ValueError, RecursionError):
            return []
    tree = place.tree
    out: dict[str, None] = {}

    def keep() -> None:
        try:
            text = ast.unparse(tree)
        except Exception:                                    # a shape that cannot be written as a program
            return
        if text != place.original:
            out[text] = None

    if operator.what == "replace":
        fitting = []
        for path, node, position in place.where(operator.before):
            if operator.position is not None and position != operator.position:
                continue
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue                                     # a documentation string
            bound: dict[str, Any] = {}
            if fits(operator.before, node, bound):
                fitting.append((path, node, bound))
        if not fitting:
            return []
        fillings = _fillings(operator, place)
        if len(fitting) * len(fillings) > at_most:
            return []
        for path, node, bound in fitting:
            for filling in fillings:
                _put(tree, path, built(operator.after, {**bound, **filling}))
                keep()
                _put(tree, path, node)
        return list(out)

    bodies = [(owner, name) for _, owner, name in place.bodies
              if operator.position is None or (type(owner).__name__, name) == operator.position]
    if operator.what == "delete":
        fitting = [(getattr(owner, name), index) for owner, name in bodies
                   for index, statement in enumerate(getattr(owner, name)) if fits(operator.before, statement, {})]
        if len(fitting) > at_most:
            return []
        for body, index in fitting:
            as_it_is = list(body)
            body[:] = (as_it_is[:index] + as_it_is[index + 1:]) or [ast.Pass()]
            keep()
            body[:] = as_it_is
        return list(out)
    fillings = _fillings(operator, place)
    if sum(len(getattr(owner, name)) + 1 for owner, name in bodies) * len(fillings) > at_most:
        return []
    for owner, name in bodies:
        body = getattr(owner, name)
        for filling in fillings:
            statement = built(operator.after, filling)
            for index in range(len(body) + 1):
                body.insert(index, statement)
                keep()
                del body[index]
    return list(out)


# --------------------------------------------------------------------------- #
# what was learned, and what it proposes for another program
# --------------------------------------------------------------------------- #
class Lessons:
    """Fixes that were shown, each once, kept as the operators read off them."""

    def __init__(self) -> None:
        self.operators: dict[str, Operator] = {}
        self.given_by: dict[str, list[str]] = {}          # operator text -> the lessons that gave it
        self.lessons: list[str] = []
        self.taught_nothing: list[str] = []

    def learn(self, name: str, before_source: str, after_source: str) -> int:
        """One fix. Returns how many operators it gave (0: the fix could not be read as a change)."""
        if name in self.lessons or name in self.taught_nothing:
            raise ValueError(f"the lesson {name!r} was already given")
        made = operators_of(before_source, after_source)
        if not made:
            self.taught_nothing.append(name)
            return 0
        self.lessons.append(name)
        for operator in made:
            self.operators.setdefault(operator.text, operator)
            self.given_by.setdefault(operator.text, []).append(name)
        return len(made)

    def votes(self, source: str, without: Sequence[str] = (), at_most: int = MAX_CANDIDATES_OF_ONE) -> dict[str, dict[str, tuple[float, str]]]:
        """For every candidate text: the lessons that vote for it, each with its vote and the
        operator the vote came through. A lesson's vote for a candidate is one over the number of
        candidates made by the most exact of its operators that makes this one. Lessons named in
        `without` are left out -- a bug's own fix, when the question is what the OTHER fixes teach."""
        try:
            place = Place(source)
        except (SyntaxError, ValueError, RecursionError):
            return {}
        left_out = set(without)
        votes: dict[str, dict[str, tuple[float, str]]] = {}
        for text, operator in self.operators.items():
            lessons = [name for name in self.given_by[text] if name not in left_out]
            if not lessons:
                continue
            made = candidates(operator, place, at_most)
            if not made:
                continue
            vote = 1.0 / len(made)
            for candidate in made:
                row = votes.setdefault(candidate, {})
                for lesson in lessons:
                    if lesson not in row or row[lesson][0] < vote:
                        row[lesson] = (vote, text)
        return votes

    def proposals(self, source: str, without: Sequence[str] = (), limit: int | None = None) -> list[dict[str, Any]]:
        """Candidate programs for this one, best supported first. Each says which lessons voted for
        it and through which operator the strongest vote came. Nothing here says a candidate is right."""
        out: list[dict[str, Any]] = []
        for candidate, score, row in ranking(self.votes(source, without)):
            if limit is not None and len(out) >= limit:
                break
            if not is_a_program(candidate):
                continue
            strongest = max(row.values(), key=lambda v: v[0])[1]
            out.append({"source": candidate, "score": round(score, 6), "lessons": sorted(row),
                        "operator": self.operators[strongest].shown(), "openness": self.operators[strongest].openness,
                        "surroundings": self.operators[strongest].surroundings})
        return out


def ranking(votes: dict[str, dict[str, tuple[float, str]]], only: Sequence[str] | None = None) -> list[tuple[str, float, dict[str, tuple[float, str]]]]:
    """Candidates by the sum of their votes, highest first (equal sums: the shorter text, then the
    text). `only` counts the votes of those lessons alone; a candidate none of them votes for is left out."""
    allowed = None if only is None else set(only)
    rows = []
    for candidate, row in votes.items():
        counted = row if allowed is None else {lesson: vote for lesson, vote in row.items() if lesson in allowed}
        if counted:
            rows.append((candidate, sum(vote for vote, _ in counted.values()), counted))
    rows.sort(key=lambda r: (-r[1], len(r[0]), r[0]))
    return rows


def same_program(one: str, other: str) -> bool:
    """Whether two texts are the same program (layout and comments apart)."""
    try:
        return key(ast.parse(one)) == key(ast.parse(other))
    except (SyntaxError, ValueError, RecursionError):
        return False
