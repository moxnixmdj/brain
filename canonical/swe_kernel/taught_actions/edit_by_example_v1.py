"""Edit a file the way examples were edited, and keep what the examples teach.

An example is two files: a Python file as it was, and the same file after somebody changed it.
Nobody writes the change down as a program.  This program works the change out from examples, as
rewrite rules, and makes the same change in another file.  The first word of ``REQUEST`` says what to do:

* ``edit``      -- one example, given as its two files, is repeated on a third file at once;
* ``remember``  -- one example is added to a lesson file, which is made when it is not there yet;
* ``repeat``    -- what a lesson file holds is repeated on a file, all of it or nothing;
* ``repeat_shown`` -- the same, but code used a way the lesson did not show is left as it is;
* ``repeat_tried`` -- the same, and what the lesson did not show is tried, one place at a time, against
  a check: a Python file of the project that is run (its tests, or the file as a script).

How a rule is worked out.  Every place where the two files of an example differ is found, down to the
smallest expression, keyword argument or one-line statement that holds the difference.  That piece
of code, and what it became, is the rule.  Places that were changed the same way are put together,
across all the examples, and a part of the code becomes a blank (``?1``, ``?2``) only where two of those
places differ from each other.  A blank keeps whatever expression stood there.  So one changed place
gives a rule about exactly that code, and a second, different place is what makes it general.

Code the examples left alone is evidence too.  A rule that would also change something an example
did not change, or would change it another way, is not accepted; more of the surrounding code is then
taken into the rule, up to the whole one-line statement, until the rule fits the changed places only.
Before any file is touched, the rules are run on every example's first file and must produce its second.

Where a rule is applied.  A rule says no more than the examples showed:

* a name the changed code reads that an example imported must be the same import in the file to edit;
  a variable or another module of that name is something else, and that code is left as it is;
* where a blank stands for the object an attribute is read from (``?1`` in ``?1.warn``) and the examples
  showed variables there, an imported module (``warnings.warn``) is something else, and is left as it is;
* a name only the new code reads that an example imported must be that import in the file to edit;
* code that fits a rule but is used another way than any changed place of the examples -- called with
  another number of arguments, with a keyword they did not show, or not called where they called it --
  may not work with the new code.  Nothing is changed then, and the refusal names the lines.  An example
  that shows that use, changed or left alone, settles it; or the request can say to leave the rest alone.

What a try is.  One example cannot say which parts of the changed code matter: ``self.thread.isAlive()``
shown once says nothing about ``t.isAlive()``.  ``repeat_tried`` also reads the lesson more widely -- each
part the change merely copied, when it starts from a variable, may be any other code -- and tries the
places only that reading fits, together with the uses nobody showed.  A try is kept only when two runs
agree: no test of the check that passed on the file as it is fails with the place changed, and a test
that passes with it fails when that place is made to fail.  A check that passes either way says nothing
about that place, and the place stays as it was.  What a check settled is added to the lesson as a new
example -- a kept place widens the lesson, a failing one speaks against the wider reading -- and the
places the check could not settle are written in the example as ``not settled``, so they count neither
as changed nor as left alone the next time.  The check itself decides nothing else: a file that fails
the check as it is edited only where the lesson's own examples or the kept tries reach.

Refused, and nothing is written:

* an example adds, removes or reshapes whole statements or blocks (a new line, a renamed function):
  only a change inside one expression or one simple statement is learned;
* a changed place assigns different names than before, or reads a variable that exists only inside
  the example's function: such a change works only together with other changes (a rename does), so
  repeating it one place at a time would leave half of it undone;
* after the edit, the file would read a name it does not define, import or receive as a parameter, or
  would still read a name whose import the edit took away;
* the same code was changed in one place of the examples and left alone, or changed another way, in
  another;
* nothing in the file to edit has the form the examples changed;
* two places to change overlap, or a comment inside a changed place would be lost;
* the edited text does not parse to exactly the tree intended;
* a lesson file that is not one: a name that does not end in ``.lesson``, other content, or a file whose
  ``teaches`` is not what its own examples give.

A change of a bare name or a bare number is never a rule by itself; it is kept together with the
expression or statement around it.  Renaming is a different action, which looks at scopes.

An ``import`` line at the top of the file that an example changed in place (same module, other
names) is repeated like any other one-line statement.  An ``import`` line an example added is brought
along with the change when the new code needs its name, the file to edit does not provide that name
anywhere, and the import can be found where the edit is made -- the standard library or the project
itself; nothing is imported or run to decide that.  Where it cannot be found, the refusal names the
import.  ``import`` lines an example removed are not repeated.

A lesson file is JSON.  It holds the examples whole, line by line, and under ``teaches`` what they give:
each change, the ways the changed code was used, the imports it leans on.  ``teaches`` is for the reader;
the rules are worked out from the examples again at every use, and a file whose ``teaches`` differs from
that is refused.  A lesson is never used unasked: the request names it.

This repeats a change.  It does not check that the change is right for the code it is repeated on.

The edit replaces only the bytes of the places that fit a rule.  Everything else in the file,
including comments and layout, stays as it was.
"""
# What to do, and with which files: ("edit", (file to edit, example before, example after)),
# ("remember", (lesson file, example before, example after)), ("repeat", (file to edit, lesson file))
# or ("repeat_shown", (file to edit, lesson file)).
REQUEST = ("edit", ("lessons_q7/suite_q7.py", "lessons_q7/shown_q7/earlier.py", "lessons_q7/shown_q7/later.py"))

import ast
import builtins
import importlib.machinery
import io
import json
import pathlib
import re
import subprocess
import sys
import time
import tokenize

SIMPLE_STATEMENTS = (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Return, ast.Expr, ast.Raise, ast.Assert,
                     ast.Delete, ast.Pass, ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.Break,
                     ast.Continue)
ATOMS = (ast.Name, ast.Constant, ast.Attribute, ast.Subscript, ast.Call, ast.List, ast.Dict, ast.Set,
         ast.ListComp, ast.SetComp, ast.DictComp, ast.JoinedStr)
NAMING_FIELDS = ("id", "attr", "arg", "name", "module", "asname")


class Refused(Exception):
    """The request is outside what this action can do without guessing."""


# ----------------------------------------------------------------------------- code as comparable values


def shape(value, swap=None, ctx=True):
    """A nested tuple that is equal for two pieces of code exactly when they are the same code."""
    if isinstance(value, ast.AST):
        if swap:
            value = swap.get(id(value), value)
        return ("N", type(value).__name__, tuple(
            (name, shape(getattr(value, name, None), swap, ctx)) for name in value._fields
            if ctx or name != "ctx"))
    if isinstance(value, list):
        return ("L", tuple(shape(item, swap, ctx) for item in value))
    return ("V", repr(value))


def children(node):
    """Direct child nodes.  The inside of an f-string is not entered: its positions cannot be trusted."""
    if isinstance(node, ast.JoinedStr):
        return
    for name in node._fields:
        value = getattr(node, name, None)
        if isinstance(value, ast.AST):
            yield value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    yield item


def is_unit(node):
    """Code that can be replaced as one piece of text: an expression, a one-line statement, a keyword argument."""
    return (isinstance(node, (ast.expr,) + SIMPLE_STATEMENTS)
            or (isinstance(node, ast.keyword) and node.arg is not None))


def kind_of(node):
    return "statement" if isinstance(node, ast.stmt) else "keyword" if isinstance(node, ast.keyword) else "expression"


def units(tree):
    """Every unit of a tree, outermost first, in source order."""
    found, stack = [], [tree]
    while stack:
        node = stack.pop()
        if is_unit(node):
            found.append(node)
        stack.extend(reversed(list(children(node))))
    return found


def tightness(node):
    """How tightly an expression holds together.  A looser one needs brackets where a tighter one stood."""
    if isinstance(node, ast.BoolOp):
        return 2 if isinstance(node.op, ast.Or) else 3
    if isinstance(node, ast.UnaryOp):
        return 4 if isinstance(node.op, ast.Not) else 12
    if isinstance(node, ast.Compare):
        return 5
    if isinstance(node, ast.BinOp):
        return {ast.BitOr: 6, ast.BitXor: 7, ast.BitAnd: 8, ast.LShift: 9, ast.RShift: 9, ast.Add: 10, ast.Sub: 10,
                ast.Pow: 13}.get(type(node.op), 11)
    if isinstance(node, ast.Await):
        return 14
    if isinstance(node, ATOMS):
        return 15
    return 1 if isinstance(node, (ast.IfExp, ast.Lambda)) else 0


def too_small(node):
    """A bare name or number: changing it everywhere it occurs would be a guess about what it means."""
    if isinstance(node, (ast.UnaryOp, ast.Starred)):
        return too_small(node.operand if isinstance(node, ast.UnaryOp) else node.value)
    return isinstance(node, (ast.Name, ast.Constant))


def names_of(node):
    """(names the code assigns in its surroundings, names it reads from its surroundings)."""
    assigned, read = set(), set()

    def walk(part, local):
        if isinstance(part, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            local = local | {name.id for loop in part.generators for name in ast.walk(loop.target)
                             if isinstance(name, ast.Name)}
        elif isinstance(part, ast.Lambda):
            given = part.args
            local = local | {one.arg for one in given.posonlyargs + given.args + given.kwonlyargs
                             + [extra for extra in (given.vararg, given.kwarg) if extra]}
        elif isinstance(part, ast.Name):
            if part.id not in local:
                (read if isinstance(part.ctx, ast.Load) else assigned).add(part.id)
            return
        elif isinstance(part, (ast.Import, ast.ImportFrom)):
            assigned.update((alias.asname or alias.name).split(".")[0] for alias in part.names)
            return
        elif isinstance(part, (ast.Global, ast.Nonlocal)):
            assigned.update(part.names)
            return
        for child in ast.iter_child_nodes(part):
            walk(child, local)

    walk(node, frozenset())
    return assigned, read


def module_names(tree):
    """(names defined at the top level of a module, whether a ``*`` import makes that unknowable)."""
    defined, anything, stack = set(), False, list(tree.body)
    while stack:
        statement = stack.pop()
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(statement.name)
            continue
        if isinstance(statement, ast.ImportFrom) and any(alias.name == "*" for alias in statement.names):
            anything = True
        if isinstance(statement, SIMPLE_STATEMENTS):
            defined |= names_of(statement)[0]
            continue
        for name in ("target", "optional_vars"):
            if isinstance(getattr(statement, name, None), ast.AST):
                defined |= names_of(getattr(statement, name))[0]
        for item in getattr(statement, "items", []):
            if item.optional_vars is not None:
                defined |= names_of(item.optional_vars)[0]
        for name in ("body", "orelse", "finalbody"):
            stack.extend(getattr(statement, name, []))
        for handler in getattr(statement, "handlers", []):
            stack.extend(handler.body)
    return defined, anything


def made_at_top(tree):
    """Names of the functions and classes a module defines at its top level."""
    made, stack = set(), list(tree.body)
    while stack:
        statement = stack.pop()
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            made.add(statement.name)
            continue
        for name in ("body", "orelse", "finalbody"):
            stack.extend(getattr(statement, name, []))
        for handler in getattr(statement, "handlers", []):
            stack.extend(handler.body)
    return made


def is_import(statement):
    return isinstance(statement, (ast.Import, ast.ImportFrom))


def imports_of(tree):
    """Names a module binds by import at its top, each with where it comes from: (module, name in it or None).

    A name imported from two different places is kept as coming from nowhere, so it never counts as the same.
    """
    found, stack = {}, list(tree.body)
    while stack:
        statement = stack.pop()
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for alias in statement.names if is_import(statement) else ():
            if isinstance(statement, ast.Import):
                name = alias.asname or alias.name.split(".")[0]
                origin = (alias.name if alias.asname else name, None)
            else:
                name, origin = alias.asname or alias.name, ("." * statement.level + (statement.module or ""), alias.name)
            if name != "*":
                found[name] = origin if found.get(name, origin) == origin else None
        for name in ("body", "orelse", "finalbody"):
            stack.extend(getattr(statement, name, []))
        for handler in getattr(statement, "handlers", []):
            stack.extend(handler.body)
    return found


def bound_by(function):
    """Names a function binds for itself: its parameters and what its body assigns, imports or defines."""
    given = function.args
    names = {one.arg for one in given.posonlyargs + given.args + given.kwonlyargs
             + [extra for extra in (given.vararg, given.kwarg) if extra]}
    outside, stack = set(), list(function.body) if isinstance(function.body, list) else [function.body]
    while stack:
        part = stack.pop()
        if isinstance(part, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(part.name)
            continue
        if isinstance(part, ast.Lambda):
            continue
        if isinstance(part, (ast.Global, ast.Nonlocal)):
            outside.update(part.names)
        elif isinstance(part, ast.Name) and not isinstance(part.ctx, ast.Load):
            names.add(part.id)
        elif is_import(part):
            names.update((alias.asname or alias.name).split(".")[0] for alias in part.names)
        elif isinstance(part, ast.ExceptHandler) and part.name:
            names.add(part.name)
        stack.extend(ast.iter_child_nodes(part))
    return names - outside


class Text:
    """A source file: its bytes, its tree, and where each node sits in the bytes."""

    def __init__(self, text, what):
        if text.startswith("\ufeff"):
            raise Refused("%s starts with a byte-order mark" % what)
        self.raw = text.encode("utf-8")
        try:
            self.tree = ast.parse(text)
        except (SyntaxError, ValueError) as problem:
            raise Refused("%s is not Python this interpreter can read (%s)" % (what, problem))
        self.starts = [0] + [found.end() for found in re.finditer(rb"\r\n|\r|\n", self.raw)]
        self.above = {id(child): node for node in ast.walk(self.tree) for child in ast.iter_child_nodes(node)}
        self.defined, self.anything = module_names(self.tree)
        self.imports, self.bound = imports_of(self.tree), {}
        self.made = made_at_top(self.tree)

    def local_at(self, node, name):
        """Is `name`, read at `node`, a parameter or variable of a function around it?"""
        while id(node) in self.above:
            node = self.above[id(node)]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                if id(node) not in self.bound:
                    self.bound[id(node)] = bound_by(node)
                if name in self.bound[id(node)]:
                    return True
        return False

    def use_of(self, node):
        """How an expression is used where it stands: None when it is not called, else the form of the call as
        (number of plain arguments, the names of its keyword arguments with '*' and '**' for unpacked ones)."""
        parent = self.above.get(id(node))
        if isinstance(parent, ast.Call) and parent.func is node:
            return (sum(not isinstance(one, ast.Starred) for one in parent.args),
                    frozenset(one.arg or "**" for one in parent.keywords)
                    | ({"*"} if any(isinstance(one, ast.Starred) for one in parent.args) else frozenset()))
        return None

    def span(self, node):
        return (self.starts[node.lineno - 1] + node.col_offset, self.starts[node.end_lineno - 1] + node.end_col_offset)

    def of(self, node):
        start, end = self.span(node)
        return self.raw[start:end].decode("utf-8")

    def provides(self, name, node):
        """Can code at `node` read `name`?  Built in, defined at the top of the file, or a parameter around it."""
        if self.anything or name in self.defined or hasattr(builtins, name):
            return True
        while id(node) in self.above:
            node = self.above[id(node)]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                given = node.args
                if name in {one.arg for one in given.posonlyargs + given.args + given.kwonlyargs
                            + [extra for extra in (given.vararg, given.kwarg) if extra]}:
                    return True
        return False

    def room(self, node):
        """The least tightness an expression needs to stand where `node` stands without brackets."""
        parent = self.above.get(id(node))
        if isinstance(parent, ast.BinOp):
            first = parent.right if isinstance(parent.op, ast.Pow) else parent.left
            return tightness(parent) + (0 if first is node else 1)
        if isinstance(parent, ast.UnaryOp):
            return tightness(parent)
        if isinstance(parent, ast.BoolOp):
            return tightness(parent) + 1
        if isinstance(parent, (ast.Compare, ast.Starred)):
            return 6
        if isinstance(parent, ast.IfExp):
            return 1 if parent.orelse is node else 2
        if (isinstance(parent, ast.Await) or (isinstance(parent, (ast.Attribute, ast.Subscript)) and parent.value is node)
                or (isinstance(parent, ast.Call) and parent.func is node)):
            return 15
        return 0

    def bracketed(self, node):
        """Is `node` written directly inside its own pair of brackets?"""
        start, end = self.span(node)
        return self.raw[:start].rstrip()[-1:] == b"(" and self.raw[end:].lstrip()[:1] == b")"

    def comments(self):
        """Byte positions of every comment."""
        found = []
        for token in tokenize.tokenize(io.BytesIO(self.raw).readline):
            if token.type == tokenize.COMMENT:
                row, column = token.start
                found.append(self.starts[row - 1] + len(token.line[:column].encode("utf-8")))
        return found


# ----------------------------------------------------------------------------- what the example changed


def changed_places(old, new, trail=()):
    """The smallest differing parts, as (old node, new node, the pairs of nodes above them)."""
    if shape(old) == shape(new):
        return []
    here = [(old, new, trail)]
    if type(old) is not type(new) or isinstance(old, ast.JoinedStr):
        return here
    inner, below = [], trail + ((old, new),)
    for name in old._fields:
        first, second = getattr(old, name, None), getattr(new, name, None)
        if isinstance(first, ast.AST) and isinstance(second, ast.AST):
            inner += changed_places(first, second, below)
        elif isinstance(first, list) and isinstance(second, list):
            if len(first) != len(second):
                return here
            for one, other in zip(first, second):
                if isinstance(one, ast.AST) and isinstance(other, ast.AST):
                    inner += changed_places(one, other, below)
                elif repr(one) != repr(other):
                    return here
        elif repr(first) != repr(second):
            return here
    return inner or here


def levels_of(old, new, trail, label="the example"):
    """The units a difference sits in, innermost first: the place itself, then more and more code around it."""
    levels = []
    for before, after in ((old, new),) + tuple(reversed(trail)):
        if isinstance(before, ast.mod) or (isinstance(before, ast.stmt) and not isinstance(before, SIMPLE_STATEMENTS)):
            break
        if is_unit(before) and is_unit(after) and kind_of(before) == kind_of(after) and (levels or not too_small(before)):
            levels.append((before, after))
    if not levels:
        raise Refused("line %d of %s adds, removes or reshapes whole statements; only a change inside "
                      "one expression or one simple statement can be learned" % (getattr(old, "lineno", 1), label))
    return levels


def places_of(old_tree, new_tree, label="the example"):
    """One entry per changed place: its levels.  A place inside another changed place is part of it."""
    places, seen = [], set()
    for old, new, trail in changed_places(old_tree, new_tree):
        levels = levels_of(old, new, trail, label)
        if id(levels[0][0]) not in seen:
            seen.add(id(levels[0][0]))
            places.append(levels)
    return [levels for levels in places if not any(id(before) in seen for before, _ in levels[1:])]


# ----------------------------------------------------------------------------- from places to a rule


def generalize(values, blanks):
    """The most specific pattern every value fits, or None.  A blank appears only where the values differ."""
    shapes = [shape(value) for value in values]
    if all(item == shapes[0] for item in shapes):
        return shapes[0]
    first = values[0]
    if all(isinstance(value, ast.AST) for value in values):
        if len({type(value) for value in values}) == 1 and not isinstance(first, ast.JoinedStr):
            fields = []
            for name in first._fields:
                inner = generalize([getattr(value, name, None) for value in values], blanks)
                if inner is None:
                    break
                fields.append((name, inner))
            else:
                return ("N", type(first).__name__, tuple(fields))
        if all(isinstance(value, ast.expr) for value in values):
            key = tuple(shape(value, ctx=False) for value in values)
            return ("?", blanks.setdefault(key, len(blanks)))
        return None
    if all(isinstance(value, list) for value in values) and len({len(value) for value in values}) == 1:
        items = [generalize([value[index] for value in values], blanks) for index in range(len(first))]
        return None if any(item is None for item in items) else ("L", tuple(items))
    return None


def blanks_in(pattern):
    if pattern[0] == "?":
        return {pattern[1]}
    if pattern[0] == "N":
        return set().union(*[blanks_in(inner) for _, inner in pattern[2]]) if pattern[2] else set()
    if pattern[0] == "L":
        return set().union(*[blanks_in(inner) for inner in pattern[1]]) if pattern[1] else set()
    return set()


def names_something(pattern):
    """True when the pattern holds at least one written name or constant, so it is tied to particular code."""
    if pattern[0] == "N":
        if pattern[1] == "Constant":
            return True
        return any((name in NAMING_FIELDS and inner[0] == "V" and inner[1] != "None") or names_something(inner)
                   for name, inner in pattern[2])
    if pattern[0] == "L":
        return any(names_something(inner) for inner in pattern[1])
    return False


def fits(pattern, value, bound):
    """Does `value` fit `pattern`?  Fills `bound` with the code each blank stands for."""
    tag = pattern[0]
    if tag == "?":
        if not isinstance(value, ast.expr):
            return False
        if pattern[1] in bound:
            return shape(bound[pattern[1]], ctx=False) == shape(value, ctx=False)
        bound[pattern[1]] = value
        return True
    if tag == "N":
        if not isinstance(value, ast.AST) or type(value).__name__ != pattern[1]:
            return False
        return all(fits(inner, getattr(value, name, None), bound) for name, inner in pattern[2])
    if tag == "L":
        return (isinstance(value, list) and len(value) == len(pattern[1])
                and all(fits(inner, item, bound) for inner, item in zip(pattern[1], value)))
    return not isinstance(value, (ast.AST, list)) and pattern[1] == repr(value)


def cut_at_blanks(pattern, node, text):
    """The text of `node` as a list of written text and blank numbers, in order, and how much room each blank has."""
    spots = []

    def find(part, value):
        if part[0] == "?":
            spots.append((text.span(value), part[1], 0 if text.bracketed(value) else text.room(value)))
        elif part[0] == "N" and isinstance(value, ast.AST):
            for name, inner in part[2]:
                find(inner, getattr(value, name, None))
        elif part[0] == "L" and isinstance(value, list):
            for inner, item in zip(part[1], value):
                find(inner, item)

    find(pattern, node)
    start, end = text.span(node)
    pieces, at = [], start
    for (first, last), blank, _ in sorted(spots):
        pieces += [text.raw[at:first].decode("utf-8"), blank]
        at = last
    return pieces + [text.raw[at:end].decode("utf-8")], [room for _, _, room in sorted(spots)]


def objects_in(pattern):
    """Blanks that are the object of an attribute the pattern names, as ``?1`` in ``?1.warn``."""
    found = set()
    if pattern[0] == "N":
        for name, inner in pattern[2]:
            if pattern[1] == "Attribute" and name == "value" and inner[0] == "?":
                found.add(inner[1])
            found |= objects_in(inner)
    elif pattern[0] == "L":
        for inner in pattern[1]:
            found |= objects_in(inner)
    return found


def root_of(node):
    """The name an expression starts from (``a`` in ``a.b[0].c()``), or None."""
    while isinstance(node, (ast.Attribute, ast.Subscript, ast.Call)):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node if isinstance(node, ast.Name) else None


def where(node):
    """Where a piece of code stands in its file: (first line, column, last line, column)."""
    return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)


def overlap(one, other):
    return (one[0], one[1]) < (other[2], other[3]) and (other[0], other[1]) < (one[2], one[3])


def sort_of(text, node):
    """What an expression starts from (``a`` in ``a.b[0].c()``): 'local' for a parameter or variable of a function,
    lambda or comprehension around it, 'top variable' for a name the file assigns at its top, 'made' for a function
    or class the file defines, 'imported module', 'imported name', 'built in' or 'unknown'.  None for code that
    does not start from a name."""
    root = root_of(node)
    if root is None:
        return None
    name, above = root.id, root
    if text.local_at(root, name):
        return "local"
    while id(above) in text.above:
        above = text.above[id(above)]
        if isinstance(above, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)) and any(
                isinstance(part, ast.Name) and part.id == name
                for loop in above.generators for part in ast.walk(loop.target)):
            return "local"
    if name in text.imports:
        origin = text.imports[name]
        return "imported module" if origin and origin[1] is None else "imported name"
    if name in text.made:
        return "made"
    if name in text.defined:
        return "top variable"
    return "built in" if hasattr(builtins, name) else "unknown"


def imported_here(text, node):
    """Does the expression start from a name the file imports at its top (and no function around it rebinds)?"""
    root = root_of(node)
    return root is not None and root.id in text.imports and not text.local_at(root, root.id)


def import_said(name, origin):
    """An import, as it would be written."""
    module, inner = origin
    if inner is None:
        return "import %s" % module if module == name else "import %s as %s" % (module, name)
    return "from %s import %s" % (module, inner) if inner == name else "from %s import %s as %s" % (module, inner, name)


class Rule:
    """Code of one form, and what it becomes."""

    def __init__(self, kind, pattern, template, shown, pieces, pairs):
        self.kind, self.pattern, self.template = kind, pattern, template
        (self.shown, _), (self.pieces, self.room), self.pairs = shown, pieces, pairs
        self.lines = sorted(before.lineno for before, _ in pairs)
        self.needs = set()               # names the new code reads that the old code did not
        self.own = set()                 # names the new code binds for itself
        self.uses = set()                # how the changed code was used where the examples changed it
        self.origins = {}                # imported names the old code reads, and where each was imported from
        self.brought = {}                # imported names only the new code reads, and where each was imported from
        self.objects = objects_in(pattern)   # blanks that stand for the object an attribute is read from
        self.imported_objects = set()    # those of them that stood for something imported in an example
        self.bring = {}                  # names the new code needs, and the import line an example added for each
        self.take = {}                   # names the examples' change made unused, and the import line each removed

    def __str__(self):
        number = {}
        for piece in self.shown:
            if not isinstance(piece, str):
                number.setdefault(piece, len(number) + 1)

        def written(pieces):
            return " ".join("".join(piece if isinstance(piece, str) else "?%d" % number[piece] for piece in pieces).split())

        return "%s -> %s" % (written(self.shown), written(self.pieces))


def left_alone(pattern, template, changed):
    """The first piece of the examples' first files that fits `pattern` and did not become `template`, or None."""
    for node in changed.candidates.get(pattern[1], ()):
        bound, again = {}, {}
        if not fits(pattern, node, bound):
            continue
        became = changed.into.get(id(node))
        if (became is None or not fits(template, became, again)
                or any(shape(again[blank], ctx=False) != shape(bound[blank], ctx=False) for blank in again)):
            return node
    return None


def rule_at(pairs, changed):
    """The rule these (before, after) pairs show at one level, or None when they do not show one rule."""
    unique = list({id(before): (before, after) for before, after in pairs}.values())
    blanks = {}
    pattern = generalize([before for before, _ in unique], blanks)
    template = generalize([after for _, after in unique], blanks)
    if pattern is None or template is None or pattern[0] != "N" or template[0] != "N":
        return None
    if not blanks_in(template) <= blanks_in(pattern):
        return None                      # the new code holds something that varies and was not copied from the old
    if blanks_in(pattern) and not names_something(pattern):
        return None                      # all blanks: it would fit any code of that outline
    if left_alone(pattern, template, changed) is not None:
        return None                      # it would change code an example left alone, or change it differently
    before, after = unique[0]
    shown = changed.home[id(before)]
    return Rule(kind_of(before), pattern, template, cut_at_blanks(pattern, before, shown.old),
                cut_at_blanks(template, after, shown.new), unique)


class Shown:
    """One example: a file as it was and as it became, and the places where the two differ."""

    def __init__(self, before_text, after_text, label="the example", unsettled=()):
        self.label, self.before_text, self.unsettled = label, before_text, [tuple(place) for place in unsettled]
        self.old, self.new = Text(before_text, label + "'s first file"), Text(after_text, label + "'s second file")
        whole_old, whole_new = list(self.old.tree.body), list(self.new.tree.body)
        imports, self.only_old, self.only_new = import_changes(self.old.tree, self.new.tree)
        if shape(self.old.tree) == shape(self.new.tree) and not imports:
            raise Refused("the two %s hold the same code%s" % (
                "example files" if label == "the example" else "files of " + label,
                ", apart from import lines that were added or removed" if self.only_old or self.only_new else ""))
        self.places = places_of(self.old.tree, self.new.tree, label) + [[pair] for pair in imports]
        self.old.tree.body, self.new.tree.body = whole_old, whole_new
        self.added_lines = {}            # names an added import line binds, and that line as the example wrote it
        for statement in self.new.tree.body:
            if (is_import(statement) and shape(statement) in self.only_new
                    and not (isinstance(statement, ast.ImportFrom) and statement.level)):
                for alias in statement.names:
                    if alias.name != "*":
                        name = alias.asname or (alias.name.split(".")[0] if isinstance(statement, ast.Import) else alias.name)
                        self.added_lines.setdefault(name, set()).add(self.new.of(statement))
        self.removed_lines = {}          # names a removed import line bound, and that line as the example had it
        for statement in self.old.tree.body:
            if (is_import(statement) and shape(statement) in self.only_old and len(statement.names) == 1
                    and not (isinstance(statement, ast.ImportFrom) and statement.level)):
                alias = statement.names[0]
                if alias.name != "*":
                    name = alias.asname or (alias.name.split(".")[0] if isinstance(statement, ast.Import) else alias.name)
                    self.removed_lines.setdefault(name, set()).add(self.old.of(statement))

    def says_nothing_about(self, node):
        """Is this code at, in or around a place that a try left unsettled?  Then it is not evidence of anything."""
        return any(overlap(where(node), place) for place in self.unsettled)


class Changed:
    """What the examples changed: every unit of their first files by kind, what each changed unit became,
    and which example a changed unit is from."""

    def __init__(self, examples):
        self.candidates, self.into, self.home = {}, {}, {}
        for shown in examples:
            for node in units(shown.old.tree):
                if not shown.says_nothing_about(node):
                    self.candidates.setdefault(type(node).__name__, []).append(node)
            for levels in shown.places:
                for before, after in levels:
                    self.into[id(before)] = after
                    self.home[id(before)] = shown


def rule_for(group, changed):
    """The rule about the smallest pieces of code that the examples themselves do not contradict."""
    for level in range(min(len(levels) for levels in group)):
        rule = rule_at([levels[level] for levels in group], changed)
        if rule is not None:
            return rule
    return None


def stands_alone(rule, changed):
    """Refuse a rule whose places only work together with other changes.  Fills in what the rule needs."""
    for before, after in rule.pairs:
        label, new, old = changed.home[id(before)].label, changed.home[id(before)].new, changed.home[id(before)].old
        if rule.kind == "expression":
            rule.uses.add(old.use_of(before))
        kept = {}
        fits(rule.pattern, before, kept)
        inside = {id(part) for blank in kept.values() for part in ast.walk(blank)}
        for part in ast.walk(before):
            if (isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load) and id(part) not in inside
                    and part.id in old.imports and not old.local_at(part, part.id)):
                rule.origins.setdefault(part.id, set()).add(old.imports[part.id])
        rule.imported_objects |= {blank for blank in rule.objects if blank in kept and imported_here(old, kept[blank])}
        assigned_before, read_before = names_of(before)
        assigned_after, read_after = names_of(after)
        if assigned_before != assigned_after and not (is_import(before) and is_import(after)
                                                      and isinstance(new.above.get(id(after)), ast.Module)):
            raise Refused("line %d of %s changes which names are assigned (%s); that works only together "
                          "with other changes, as in a rename, and cannot be repeated one place at a time"
                          % (before.lineno, label, ", ".join(sorted(assigned_before ^ assigned_after))))
        for name in sorted(read_after - read_before):
            if not new.provides(name, after):
                raise Refused("line %d of %s makes the code read '%s', which %s's second file neither "
                              "defines or imports at the top nor receives as a parameter there; a change that leans on "
                              "a local variable cannot be repeated one place at a time" % (before.lineno, label, name, label))
            if not hasattr(builtins, name):
                rule.needs.add(name)
                if name in new.imports and not new.local_at(after, name):
                    rule.brought.setdefault(name, set()).add(new.imports[name])
    # Names the new code binds for itself (a comprehension's variable, a lambda's parameter).  Copied code
    # that already uses such a name would be captured by it.
    before, after = rule.pairs[0]
    copied = {}
    fits(rule.template, after, copied)
    inside = {id(part) for blank in copied.values() for part in ast.walk(blank)}
    for part in ast.walk(after):
        if id(part) in inside:
            continue
        if isinstance(part, ast.comprehension):
            rule.own |= {name.id for name in ast.walk(part.target) if isinstance(name, ast.Name)}
        elif isinstance(part, ast.Lambda):
            rule.own |= {one.arg for one in ast.walk(part.args) if isinstance(one, ast.arg)}


# What a part of changed code must start from to count as something that could have been any other value.
MAY_VARY = ("local", "top variable")


def may_vary(text, node):
    """Could this part of an example's code as well have been another value?  True when it starts from a variable.

    Something imported, a function or class, a built-in name or a constant is taken to be what the change is about.
    """
    return isinstance(node, (ast.Name, ast.Attribute, ast.Subscript, ast.Call)) and sort_of(text, node) in MAY_VARY


def copied_parts(text, before, after):
    """The outermost parts of `before` that stand unchanged in `after` and may vary.  The function of a call is
    never such a part as a whole: of ``box.get(key)`` only ``box`` and ``key`` are."""
    held = {shape(part, ctx=False) for part in ast.walk(after) if isinstance(part, ast.expr)}
    found = []

    def walk(node):
        if isinstance(node, ast.JoinedStr):
            return
        for name in node._fields:
            value = getattr(node, name, None)
            for child in value if isinstance(value, list) else [value]:
                if not isinstance(child, ast.AST):
                    continue
                if (isinstance(child, ast.expr) and not (isinstance(node, ast.Call) and name == "func")
                        and isinstance(getattr(child, "ctx", None), (ast.Load, type(None)))
                        and shape(child, ctx=False) in held and may_vary(text, child)):
                    found.append(child)
                else:
                    walk(child)

    walk(before)
    return found


def stand_in(value, marks):
    """A copy of code in which every expression whose shape is in `marks` is replaced by its mark."""
    if isinstance(value, ast.expr) and shape(value, ctx=False) in marks:
        return ast.copy_location(ast.Name(id=marks[shape(value, ctx=False)], ctx=ast.Load()), value)
    if isinstance(value, ast.AST):
        copy = type(value)()
        for name in value._fields:
            setattr(copy, name, stand_in(getattr(value, name, None), marks))
        return ast.copy_location(copy, value) if hasattr(value, "lineno") else copy
    if isinstance(value, list):
        return [stand_in(item, marks) for item in value]
    return value


def wider(rule, changed):
    """The rule read more widely: every part the change merely copied may be other code.  None when that is no rule.

    One changed place cannot say which of its parts matter.  This reading takes each part that stands unchanged in
    the new code and starts from a variable to be a blank, as a second place that differed there would have made
    it.  Code an example left alone still speaks against it.  Nobody showed this reading, so it is never used
    unasked: code that fits only it is changed only when a check settles that place (`repeat_tried`).
    """
    before, after = rule.pairs[0]
    parts = copied_parts(changed.home[id(before)].old, before, after)
    marks = {}
    for part in parts:
        marks.setdefault(shape(part, ctx=False), "\0%d" % len(marks))
    if not marks:
        return None
    reading = rule_at(list(rule.pairs) + [(stand_in(before, marks), stand_in(after, marks))], changed)
    if reading is None or blanks_in(reading.pattern) == blanks_in(rule.pattern):
        return None
    reading.pairs = list(rule.pairs)
    reading.lines = rule.lines
    try:
        stands_alone(reading, changed)
    except Refused:
        return None
    reading.bring = {name: line for name, line in rule.bring.items() if name in reading.needs}
    reading.take = dict(rule.take)
    return reading


def import_changes(old_tree, new_tree):
    """Take changed top-level import lines out of both trees.

    Returns (pairs changed in place, shapes only the old file has, shapes only the new file has).  A line
    counts as changed in place when both files import from the same module; any other difference is a
    line that was added or removed.
    """
    was = {shape(statement) for statement in old_tree.body if is_import(statement)}
    now = {shape(statement) for statement in new_tree.body if is_import(statement)}
    gone = [statement for statement in old_tree.body if is_import(statement) and shape(statement) not in now]
    came = [statement for statement in new_tree.body if is_import(statement) and shape(statement) not in was]
    old_tree.body = [statement for statement in old_tree.body if not any(statement is one for one in gone)]
    new_tree.body = [statement for statement in new_tree.body if not any(statement is one for one in came)]
    pairs = []
    for before in list(gone):
        for after in came:
            if (isinstance(before, ast.ImportFrom) and isinstance(after, ast.ImportFrom)
                    and (before.module, before.level) == (after.module, after.level)):
                pairs.append((before, after))
                gone.remove(before)
                came.remove(after)
                break
    return pairs, {shape(statement) for statement in gone}, {shape(statement) for statement in came}


def without_imports(tree, shapes):
    return [shape(statement) for statement in tree.body if not (is_import(statement) and shape(statement) in shapes)]


def rename_undone(before_text, after_text):
    """The example's second file with an incidental local rename undone, or the second file as it came.

    A person sometimes renames a local variable in the same commit as the edit worth teaching; the rename is
    identity-specific and poisons the lesson.  When the second file binds exactly one plainly assigned name the
    first does not, and the first binds exactly one such name the second dropped, and neither name is ever an
    import, a def, a class, a parameter, or a global/nonlocal in its file, the new name is put back to the old
    one everywhere it stands as a bare name.  The result is the same program; only the lesson becomes visible.
    """
    try:
        before_tree, after_tree = ast.parse(before_text), ast.parse(after_text)
    except SyntaxError:
        return after_text

    def all_names(tree):
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                found.add(node.id)
            elif isinstance(node, ast.arg):
                found.add(node.arg)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                found.add(node.name)
            elif isinstance(node, ast.alias):
                found.add((node.asname or node.name).split(".")[0])
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                found.update(node.names)
        return found

    olds = {name for name in all_names(before_tree) - all_names(after_tree) if not hasattr(builtins, name)}
    news = {name for name in all_names(after_tree) - all_names(before_tree) if not hasattr(builtins, name)}
    if len(olds) != 1 or len(news) != 1:
        return after_text
    old, new = olds.pop(), news.pop()

    def plainly_assigned(tree, name):
        stored = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.Global, ast.Nonlocal)) and name in node.names:
                return False
            if isinstance(node, ast.alias) and (node.asname or node.name).split(".")[0] == name:
                return False
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
                return False
            if isinstance(node, ast.arg) and node.arg == name:
                return False
            if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Store):
                stored = True
        return stored

    if not plainly_assigned(before_tree, old) or not plainly_assigned(after_tree, new):
        return after_text
    lines = after_text.splitlines(keepends=True)
    starts, total = [], 0
    for line in lines:
        starts.append(total)
        total += len(line)
    spans = sorted(((starts[node.lineno - 1] + node.col_offset, starts[node.end_lineno - 1] + node.end_col_offset)
                    for node in ast.walk(after_tree) if isinstance(node, ast.Name) and node.id == new), reverse=True)
    came_as = after_text
    for head, tail in spans:
        after_text = after_text[:head] + old + after_text[tail:]
    try:
        if ast.dump(ast.parse(after_text)) == ast.dump(before_tree):
            return came_as        # the whole example was the rename; it teaches nothing repeatable
    except SyntaxError:
        return came_as
    return after_text


def learn_all(examples, wide=False):
    """The rules that turn every example's first file into its second.  `examples` is a list of (before, after) texts.

    Several examples are read as one: places changed the same way are put together across them, a blank appears
    where two such places differ, and code that any one of them left alone speaks against a rule that fits it.
    An example may be (before, after, places): code at those places of `before` was not settled when the example
    was made, and counts neither as changed nor as left alone.

    With `wide`, returns (the rules, their wider readings); see `wider`.
    """
    several = len(examples) > 1
    shown = [Shown(example[0], rename_undone(example[0], example[1]),
                   "example %d" % number if several else "the example", example[2:] and example[2])
             for number, example in enumerate(examples, 1)]
    changed = Changed(shown)
    groups = []
    for example in shown:
        for levels in example.places:
            for group in groups:
                if rule_for(group + [levels], changed) is not None:
                    group.append(levels)
                    break
            else:
                groups.append([levels])
    rules = []
    for group in groups:
        rule = rule_for(group, changed)
        if rule is None:
            first = group[0][0][0]
            raise Refused("line %d of %s was changed, but the same code was left alone, or changed another way, "
                          "elsewhere in %s" % (first.lineno, changed.home[id(first)].label,
                                               "the examples" if several else "the example"))
        stands_alone(rule, changed)
        rules.append(rule)
    added = {}
    for example in shown:
        for name, lines in example.added_lines.items():
            added.setdefault(name, set()).update(lines)
    for rule in rules:
        rule.bring = {name: sorted(added[name])[0] for name in rule.needs
                      if name in added and len(added[name]) == 1}
    removed = {}
    for example in shown:
        for name, lines in example.removed_lines.items():
            removed.setdefault(name, set()).update(lines)
    for rule in rules:
        rule.take = {name: sorted(lines)[0] for name, lines in removed.items() if len(lines) == 1}
    for example in shown:
        replayed, _ = rewrite(rules, example.before_text, example.label + "'s first file", check_names=False,
                              skip=example.says_nothing_about)
        shapes = example.only_old | example.only_new
        if without_imports(ast.parse(replayed), shapes) != without_imports(example.new.tree, shapes):
            raise Refused("the rules worked out from %s do not reproduce %s"
                          % ("the examples" if several else "the example", example.label))
    if wide:
        return rules, [reading for reading in (wider(rule, changed) for rule in rules) if reading is not None]
    return rules


def learn(before_text, after_text):
    """The rules that turn the example's first file into its second."""
    return learn_all([(before_text, after_text)])


# ----------------------------------------------------------------------------- applying rules to a file


def parse_like(node, kind, written):
    """`written` parsed as the same kind of code as `node`, or None."""
    try:
        if kind == "statement":
            body = ast.parse(written).body
            return body[0] if len(body) == 1 else None
        if kind == "keyword":
            call = ast.parse("f(%s)" % written, mode="eval").body
            return call.keywords[0] if isinstance(call, ast.Call) and len(call.keywords) == 1 and not call.args else None
        if isinstance(getattr(node, "ctx", None), ast.Store):
            return ast.parse("%s = 0" % written).body[0].targets[0]
        if isinstance(getattr(node, "ctx", None), ast.Del):
            return ast.parse("del %s" % written).body[0].targets[0]
        return ast.parse("(%s)" % written, mode="eval").body
    except (SyntaxError, ValueError, IndexError, AttributeError):
        return None


def written_for(rule, node, bound, text):
    """The new text for one place, and that text parsed.  It must be the rule's new form with the same blanks."""
    for every in (False, True):
        parts, room = [], iter(rule.room)
        for piece in rule.pieces:
            if isinstance(piece, str):
                parts.append(piece)
            else:
                inner, needed = text.of(bound[piece]), next(room)
                loose = not isinstance(bound[piece], ATOMS) if every else tightness(bound[piece]) < needed
                if isinstance(bound[piece], (ast.Tuple, ast.GeneratorExp)) and inner[:1] == "(" and inner[-1:] == ")":
                    loose = False        # it brought its own brackets
                parts.append("(%s)" % inner if loose else inner)
        written = "".join(parts)
        parsed = parse_like(node, rule.kind, written)
        again = {}
        if (parsed is not None and fits(rule.template, parsed, again)
                and all(shape(again[blank], ctx=False) == shape(bound[blank], ctx=False) for blank in again)):
            return written, parsed
    raise Refused("the change does not fit the code at line %d" % node.lineno)


def same_names(rule, text, node, bound):
    """Is the code at `node` about the same things as the changed code of the examples?

    A name that is an imported module in an example says nothing about a variable of the same name, or about
    another module imported under it.  And where a blank stands for the object an attribute is read from
    (``?1`` in ``?1.warn``), examples that showed variables there say nothing about an imported module
    (``warnings.warn``).  Code that reads another thing is not the code the rule is about, and is left as it is.
    """
    inside = {id(part) for blank in bound.values() for part in ast.walk(blank)}
    for part in ast.walk(node):
        if (isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load) and part.id in rule.origins
                and id(part) not in inside):
            if text.imports.get(part.id) not in rule.origins[part.id] or text.local_at(part, part.id):
                return False
    return not any(blank in bound and blank not in rule.imported_objects and imported_here(text, bound[blank])
                   for blank in rule.objects)


def said(use):
    """One way of using an expression, in words."""
    if use is None:
        return "not called"
    count, named = use
    words = "called with %d argument%s" % (count, "" if count == 1 else "s")
    extra = [name for name in sorted(named) if name not in ("*", "**")]
    if extra:
        words += " and the keyword%s %s" % ("" if len(extra) == 1 else "s", ", ".join(extra))
    for mark, meaning in (("*", "unpacked arguments"), ("**", "unpacked keywords")):
        if mark in named:
            words += " and %s" % meaning
    return words


SHOWN = object()


def unshown_use(rule, text, node):
    """`SHOWN` when the code at `node` is used a way the examples showed; otherwise that use.

    A function replaced where it was called one way says nothing about calls of another form: the new function
    may not take those arguments.  So a call must have a number of plain arguments the examples showed and no
    keyword they did not show, and code that is not called must have been shown not called.
    """
    if rule.kind != "expression":
        return SHOWN
    use, calls = text.use_of(node), [shown for shown in rule.uses if shown is not None]
    if use is None:
        return SHOWN if None in rule.uses else use
    if use[0] in {count for count, _ in calls} and use[1] <= frozenset().union(*[named for _, named in calls]):
        return SHOWN
    return use


def not_shown(rule, found, text, what):
    """The refusal for uses the examples did not show.  `found` is [(use, the first node used that way)]."""
    (use, node), others = found[0], found[1:]
    also = ""
    if others:
        also = " (also %s%s)" % ("; ".join("line %d, %s" % (other.lineno, said(more)) for more, other in others[:2]),
                                 "; and %d more" % (len(others) - 2) if len(others) > 2 else "")
    return Refused("line %d of %s has %s %s%s; the examples showed it %s. A use the examples did not show may not "
                   "work with the new code, so nothing was changed; show %s too, changed or left alone"
                   % (node.lineno, what, " ".join(text.of(node).split())[:60], said(use), also,
                      ", ".join(said(shown) for shown in sorted(
                          rule.uses, key=lambda one: (one is not None, one and (one[0], sorted(one[1]))))),
                      "those uses" if others else "that use"))


def fitting(rules, text, what, skip=None, torn=True):
    """Every piece of the file a rule fits, in source order: (its bytes, the code, the rule, what each blank holds,
    `SHOWN` or the use the examples did not show).  Code that two rules fit is refused, or passed over when not `torn`."""
    found = []
    for node in units(text.tree):
        if skip is not None and skip(node):
            continue
        fit = []
        for rule in rules:
            bound = {}
            if fits(rule.pattern, node, bound) and same_names(rule, text, node, bound):
                fit.append((rule, bound))
        if len(fit) > 1 and torn:
            raise Refused("two changes of the example both fit the code at line %d of %s" % (node.lineno, what))
        if len(fit) == 1:
            found.append((text.span(node), node) + fit[0] + (unshown_use(fit[0][0], text, node),))
    return found


def rewrite(rules, source_text, what="the file", check_names=True, leave_unshown=False, skip=None):
    """Apply the rules to every place that fits.  Returns (new text, number of places changed).

    Code used a way no example showed stops the whole edit, unless `leave_unshown` asks for it to be left as it is.
    Code for which `skip` is true is not looked at.
    """
    text = Text(source_text, what)
    places, unshown = [], {}
    for span, node, rule, bound, use in fitting(rules, text, what, skip):
        if use is not SHOWN:
            if use not in [seen for seen, _ in unshown.setdefault(id(rule), (rule, []))[1]]:
                unshown[id(rule)][1].append((use, node))
            continue
        places.append((span, node, rule, bound))
    for rule, found in unshown.values():
        if not leave_unshown:
            raise not_shown(rule, found, text, what)
    if not places:
        return source_text, 0
    return written(text, places, what, check_names), len(places)


# What a changed place is replaced by to see whether a check notices that code failing.  It raises, when it is
# evaluated, an error of the kinds a wrong change raises, so whatever would swallow those swallows it as well.
FAILURE = ("type('ChangedCodeFails', (TypeError, AttributeError, ValueError, LookupError), {})"
           "('this code was made to fail, to see whether the check notices')")
FAILS = "(_ for _ in ()).throw(%s)" % FAILURE


def failing(node, kind):
    """Text that fails where `node` would have run, or None for code that is not run by itself (an assignment's target)."""
    if kind == "statement":
        return "raise " + FAILURE
    if kind == "keyword":
        return "%s=%s" % (node.arg, FAILS)
    return FAILS if isinstance(getattr(node, "ctx", ast.Load()), ast.Load) else None


def import_resolves(line):
    """Can the import this line names be found where the edit is made?  Nothing is imported or run."""
    statement = ast.parse(line).body[0]
    tops = ({alias.name.split(".")[0] for alias in statement.names} if isinstance(statement, ast.Import)
            else {(statement.module or "").split(".")[0]})
    for top in tops:
        if top not in sys.stdlib_module_names and importlib.machinery.PathFinder().find_spec(
                top, [str(pathlib.Path.cwd())] + sys.path) is None:
            return top
    return None


def imports_to_add(text, places, what, fail_at=None, must_resolve=True):
    """The import lines the examples added that this edit needs: the file does not provide the name, the
    examples added exactly one line for it, and that line's module can be found here.  Raises where it cannot.

    `must_resolve` is off only when an example is replayed on its own first file, where the import plainly was.
    """
    needed = {}
    for _, node, rule, _ in places:
        if fail_at is not None and node is fail_at[1]:
            continue
        for name in sorted(rule.needs):
            if name not in rule.bring or text.provides(name, node):
                continue
            if text.local_at(node, name):
                raise Refused("the change at line %d of %s uses '%s', and a function around that code binds that "
                              "name for itself; the import the examples added cannot reach it" % (node.lineno, what, name))
            line = rule.bring[name]
            top = import_resolves(line) if must_resolve else None
            if top is not None:
                raise Refused("the change needs `%s`, as the examples added, and nothing named '%s' can be found "
                              "in this project; nothing was changed" % (line, top))
            needed[name] = line
    return needed


def import_insert_at(text):
    """The byte where added import lines go: after the last top-level import, else after the docstring, else 0."""
    last = None
    for statement in text.tree.body:
        if is_import(statement):
            last = statement
    if last is None and text.tree.body and isinstance(text.tree.body[0], ast.Expr)             and isinstance(text.tree.body[0].value, ast.Constant) and isinstance(text.tree.body[0].value.value, str):
        last = text.tree.body[0]
    if last is None:
        return 0
    return text.starts[last.end_lineno] if last.end_lineno < len(text.starts) else len(text.raw)


class Renamed:
    """A leftover read of a name whose import the examples renamed: the read follows its definition."""

    kind = "expression"
    own = frozenset()
    needs = frozenset()
    pieces = ()
    brought = {}
    bring = {}
    take = {}

    def __init__(self, new):
        self.new = new


def renames_to_add(text, places, fail_at):
    """Places that rename a read left pointing at nothing, after the examples renamed its import.

    The examples rename an imported name where the import line itself is rewritten in place -- same module,
    same number of names, a bound name changed.  A read of the old name that no rule reaches would be a
    certain NameError once that import is gone; it follows the renamed definition.  Nothing follows where
    the map is unsure: two places that rename the name differently, a new name the file already binds, a
    read a function rebinds locally, or a read inside code a rule already rewrites.
    """
    maps = {}
    for (_, node, rule, bound) in places:
        if isinstance(rule, Renamed) or not isinstance(node, ast.ImportFrom) or node.level:
            continue
        if fail_at is not None and node is fail_at[1]:
            continue
        try:
            _, parsed = written_for(rule, node, bound, text)
        except Refused:
            continue
        if (not isinstance(parsed, ast.ImportFrom) or (node.module, node.level) != (parsed.module, parsed.level)
                or len(node.names) != len(parsed.names)):
            continue
        for a, b in zip(node.names, parsed.names):
            was, now = (a.asname or a.name), (b.asname or b.name)
            if was != now:
                maps.setdefault(was, set()).add(now)
    maps = {was: min(nows) for was, nows in maps.items() if len(nows) == 1 and min(nows) not in text.defined}
    if maps:
        renamed = {node for _, node, rule, _ in places if isinstance(node, ast.ImportFrom)}
        others = ast.Module(body=[one for one in text.tree.body if one not in renamed], type_ignores=[])
        elsewhere, anything = module_names(others)
        maps = {} if anything else {was: now for was, now in maps.items() if was not in elsewhere}
    found = []
    for part in ast.walk(text.tree):
        if not (isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load) and part.id in maps):
            continue
        at = text.span(part)
        if any(not (at[1] <= start or end <= at[0]) for (start, end), _, _, _ in places):
            continue
        if text.local_at(part, part.id):
            continue
        found.append((at, part, Renamed(maps[part.id]), {}))
    return found


def written(text, places, what="the file", check_names=True, fail_at=None):
    """`written_once`, with the leftover reads of a renamed import following their renamed definition."""
    return written_once(text, places + renames_to_add(text, places, fail_at), what, check_names, fail_at)


def written_once(text, places, what="the file", check_names=True, fail_at=None):
    """The file's text with every place rewritten by its rule; the place `fail_at` is made to fail instead.

    An import line the examples added is inserted when the new code needs its name and the file does not
    provide it -- only where that import can be found (`imports_to_add`)."""
    places = sorted(places, key=lambda place: place[0])
    brought = imports_to_add(text, places, what, fail_at, must_resolve=check_names)
    block = "".join(line + "\n" for line in sorted(set(brought.values()))).encode("utf-8")
    where_block = import_insert_at(text)
    if block and where_block == len(text.raw) and not text.raw.endswith((b"\n", b"\r")):
        block = b"\n" + block
    for earlier, later in zip(places, places[1:]):
        if later[0][0] < earlier[0][1]:
            raise Refused("two places to change overlap at line %d of %s" % (later[1].lineno, what))
    for _, node, rule, bound in places:
        used = {part.id if isinstance(part, ast.Name) else part.arg for blank in bound.values()
                for part in ast.walk(blank) if isinstance(part, (ast.Name, ast.arg))}
        if used & rule.own:
            raise Refused("the new code has its own variable '%s', and the code at line %d of %s already uses that name"
                          % (sorted(used & rule.own)[0], node.lineno, what))
    comments = text.comments()
    for (start, end), node, rule, bound in places:
        kept = [text.span(bound[piece]) for piece in rule.pieces if not isinstance(piece, str)]
        for position in comments:
            if start <= position < end and not any(first <= position < last for first, last in kept):
                raise Refused("a comment inside the code at line %d of %s would be lost" % (node.lineno, what))
    for attempt in (0, 1, 2):
        out, at, swap, shift = [], 0, {}, 0
        for (start, end), node, rule, bound in places:
            if fail_at is not None and node is fail_at[1]:
                new_text = failing(node, rule.kind)
                parsed = None if new_text is None else parse_like(node, rule.kind, new_text)
                if parsed is None:
                    raise Refused("the code at line %d of %s cannot be made to fail by itself" % (node.lineno, what))
            elif isinstance(rule, Renamed):
                new_text, parsed = rule.new, ast.parse(rule.new, mode="eval").body
            else:
                new_text, parsed = written_for(rule, node, bound, text)
                looser = rule.kind == "expression" and tightness(parsed) < tightness(node)
                if ((rule.kind == "expression" and tightness(parsed) < text.room(node)) if attempt == 0
                        else looser if attempt == 1 else rule.kind == "expression" and not isinstance(parsed, ATOMS)):
                    new_text = "(%s)" % new_text
            encoded = new_text.encode("utf-8")
            if end <= where_block:
                shift += len(encoded) - (end - start)
            out += [text.raw[at:start], encoded]
            at = end
            swap[id(node)] = parsed
        joined = b"".join(out + [text.raw[at:]])
        if block:
            there = where_block + shift
            joined = joined[:there] + block + joined[there:]
        result = joined.decode("utf-8")
        try:
            again = ast.parse(result)
        except (SyntaxError, ValueError):
            continue
        whole = list(again.body)
        for line in sorted(set(brought.values())):
            wanted = shape(ast.parse(line).body[0])
            for statement in again.body:
                if shape(statement) == wanted:
                    again.body = [other for other in again.body if other is not statement]
                    break
        same = shape(again) == shape(text.tree, swap)
        again.body = whole
        if same:
            if check_names:
                names_still_hold(text, again, [place for place in places if fail_at is None or place[1] is not fail_at[1]],
                                 what)
            return imports_taken_away(result, again, places)
    raise Refused("the edited text of %s does not parse to the intended code" % what)


def imports_taken_away(result, tree, places):
    """The finished text without the import lines the examples removed, where nothing is at risk.

    A line goes only when the examples all removed it, this file holds exactly that statement on lines
    of its own without a comment, and no code in the finished file reads or writes the name anywhere.
    Anything less certain leaves the line where it is -- leaving an import is never wrong the way
    removing a used one would be.
    """
    take = {}
    for _, _, rule, _ in places:
        take.update(getattr(rule, "take", {}))
    for name in sorted(take):
        wanted = shape(ast.parse(take[name]).body[0])
        found = [statement for statement in tree.body if is_import(statement) and shape(statement) == wanted]
        if len(found) != 1:
            continue
        statement = found[0]
        if any(isinstance(part, ast.Name) and part.id == name for part in ast.walk(tree)):
            continue
        others = [other for other in tree.body if other is not statement]
        if any(other.lineno <= statement.end_lineno and other.end_lineno >= statement.lineno for other in others):
            continue
        lines = result.splitlines(keepends=True)
        if statement.end_lineno > len(lines) or "#" in "".join(lines[statement.lineno - 1:statement.end_lineno]):
            continue
        shorter = "".join(lines[:statement.lineno - 1] + lines[statement.end_lineno:])
        try:
            again = ast.parse(shorter)
        except (SyntaxError, ValueError):
            continue
        if [shape(one) for one in again.body] != [shape(one) for one in others]:
            continue
        result, tree = shorter, again
    return result


def names_still_hold(text, edited, places, what):
    """After the edit: every name the new code reads is provided, and no name the edit took away is still read."""
    defined, anything = module_names(edited)
    if anything:
        return
    imported = imports_of(edited)
    for _, node, rule, _ in places:
        for name in sorted(rule.needs):
            if name not in defined and not text.provides(name, node):
                raise Refused("the change uses '%s', which %s does not define, import or receive as a parameter "
                              "at line %d" % (name, what, node.lineno))
            origins = rule.brought.get(name)
            if origins and None not in origins and (imported.get(name) not in origins or text.local_at(node, name)):
                raise Refused("the change uses '%s', which the examples get by `%s`; at line %d of %s that name "
                              "is something else" % (name, "` or `".join(sorted(import_said(name, origin)
                                                                               for origin in origins)), node.lineno, what))
    taken = text.defined - defined
    for part in ast.walk(edited):
        if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load) and part.id in taken:
            raise Refused("the change takes the name '%s' away from the top of %s, but line %d still uses it"
                          % (part.id, what, part.lineno))


def edit_by_example(target_text, before_text, after_text):
    """`target_text` changed the way `before_text` was changed into `after_text`."""
    return repeated(learn(before_text, after_text), target_text, "the example")


def repeated(rules, target_text, shown_by, leave_unshown=False):
    result, count = rewrite(rules, target_text, leave_unshown=leave_unshown)
    if count == 0:
        raise Refused("nothing in the file has the form %s changed (%s); a part of that form may vary "
                      "only where two changed places differ" % (shown_by, "; ".join(str(rule) for rule in rules)))
    return result


def inside_project(path, what):
    target = pathlib.Path(path)
    if target.is_absolute() or ".." in target.parts:
        raise Refused("%s must be a path inside the project" % what)
    return target


def read_python(path, what):
    target = inside_project(path, what)
    if not target.is_file():
        raise Refused("%s does not exist" % what)
    try:
        return target, target.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("%s is not UTF-8 text" % what)


# ----------------------------------------------------------------------------- a lesson kept in a file

LESSON_FORMAT = "CHANGE_LEARNED_FROM_EXAMPLES_V1"
LESSON_SUFFIX = ".lesson"
UNSETTLED = "not settled"


def described(rules):
    """What a lesson teaches, for a reader: each change, and how the changed code was used where it was shown."""
    out = []
    for rule in rules:
        entry = {"change": str(rule)}
        if rule.kind == "expression" and rule.uses != {None}:
            entry["shown"] = sorted(said(use) for use in rule.uses)
        names = {name: sorted(import_said(name, origin) if origin else "more than one import" for origin in origins)
                 for name, origins in sorted({**rule.origins, **rule.brought}.items())}
        if names:
            entry["imports"] = names
        if rule.take:
            entry["takes away"] = {name: rule.take[name] for name in sorted(rule.take)}
        out.append(entry)
    return out


def lesson_examples(path):
    """The examples a lesson file holds, each as (before, after) or (before, after, places a try left unsettled),
    and who showed each.  Returns (path, examples, shown by); the two lists are None when the file is not there.
    Refuses a file that is not a sound lesson."""
    target = inside_project(path, "the lesson file")
    if not target.name.endswith(LESSON_SUFFIX):
        raise Refused("a lesson file's name ends in %s" % LESSON_SUFFIX)
    if not target.is_file():
        return target, None, None
    try:
        held = json.loads(target.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        held = None
    kept = held.get("examples") if isinstance(held, dict) and held.get("format") == LESSON_FORMAT else None
    if (not isinstance(kept, list) or not kept or not all(
            isinstance(example, dict) and all(
                isinstance(example.get(side), list) and all(isinstance(line, str) for line in example[side])
                for side in ("before", "after")) for example in kept)):
        raise Refused("%s exists and is not a lesson file" % path)
    examples = []
    for example in kept:
        before, places = "".join(example["before"]), example.get(UNSETTLED, [])
        if (not isinstance(places, list) or (UNSETTLED in example and not places) or not all(
                isinstance(place, list) and len(place) == 4 and all(type(number) is int for number in place)
                for place in places)):
            raise Refused("%s exists and is not a lesson file" % path)
        examples.append((before, "".join(example["after"])) + ((tuple(tuple(place) for place in places),) if places else ()))
        if places:
            try:
                stand = {where(node) for node in units(ast.parse(before))}
            except (SyntaxError, ValueError):
                stand = set()
            if not set(examples[-1][2]) <= stand:
                raise Refused("%s names a place that is no piece of code in its own example; it was changed by hand. "
                              "Remember its examples again" % path)
    try:
        taught = described(learn_all(examples))
    except Refused as why:
        raise Refused("the examples in %s no longer give rules (%s); it was changed by hand, or written by another "
                      "version of this action. Remember its examples again" % (path, why))
    if held.get("teaches") != taught:
        raise Refused("%s says it teaches something other than what its examples show; it was changed by hand, or "
                      "written by another version of this action. Remember its examples again" % path)
    return target, examples, [example.get("shown by") for example in kept]


def lesson_text(examples, origins):
    """The bytes of a lesson file.  Raises Refused when the examples, read as one, do not give rules."""
    rules = learn_all(examples)
    held = {"format": LESSON_FORMAT,
            "what this is": "A change worked out from examples, kept to be repeated on other files. "
                            "'teaches' is checked against 'examples' every time the lesson is used.",
            "teaches": described(rules),
            "examples": [dict([("shown by", origin), ("before", example[0].splitlines(keepends=True)),
                               ("after", example[1].splitlines(keepends=True))]
                              + ([(UNSETTLED, [list(place) for place in example[2]])] if example[2:] and example[2] else []))
                         for example, origin in zip(examples, origins)]}
    return (json.dumps(held, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def remember(lesson, before, after):
    """Add one example to a lesson file, making the file when it is not there.  Returns (path, bytes to write)."""
    target, examples, origins = lesson_examples(lesson)
    _, earlier = read_python(before, "the example's first file")
    _, later = read_python(after, "the example's second file")
    if examples is None:
        examples, origins = [], []
    elif any(example[:2] == (earlier, later) for example in examples):
        raise Refused("%s already holds this example" % lesson)
    return target, lesson_text(examples + [(earlier, later)], origins + ["%s -> %s" % (before, after)])


# ----------------------------------------------------------------------------- what a check settles

MOST_TRIED = 8                   # places tried in one file; any further ones are left as they are
CHECK_SECONDS = 20               # the longest one run of the check may take
ALL_CHECKS_SECONDS = 90          # the longest all runs of one request may take
CHECK_SAID = "TESTS OF THE CHECK THAT FAILED: "

# Runs a check file in a fresh interpreter and prints, last, the tests of it that failed.
#
# A file that holds tests is run as a test file: every ``unittest.TestCase`` class in it and every function whose
# name starts with ``test`` and that takes no arguments.  A file without tests that has an
# ``if __name__ == "__main__":`` block is run as a script, and counts as one test.
#
# When a file to edit is named, its text is read from standard input instead of from disk wherever the project
# imports it, so a text can be tried without being written.
RUNNER = r"""
import ast, importlib.machinery, inspect, json, os, sys, traceback, types, unittest
check, edited = sys.argv[1], sys.argv[2]
text = sys.stdin.buffer.read() if edited else None
same = lambda one, other: os.path.realpath(one) == os.path.realpath(other)
if edited:
    usual = importlib.machinery.SourceFileLoader.get_code
    def get_code(self, name):
        path = self.get_filename(name)
        return self.source_to_code(text, path) if same(path, edited) else usual(self, name)
    importlib.machinery.SourceFileLoader.get_code = get_code
source = text if edited and same(check, edited) else open(check, "rb").read()
folder, parts = os.path.dirname(os.path.abspath(check)), [os.path.splitext(os.path.basename(check))[0]]
while os.path.isfile(os.path.join(folder, "__init__.py")):
    folder, parts = os.path.dirname(folder), [os.path.basename(folder)] + parts
sys.path.insert(0, folder)
sys.argv = [check]

def run(name, package):
    module = types.ModuleType(name)
    module.__file__ = check
    if package is not None:
        module.__package__ = package
    sys.modules[name] = module
    try:
        exec(compile(source, check, "exec"), module.__dict__)
    except SystemExit as stop:
        return module, stop.code not in (None, 0)
    except BaseException:
        traceback.print_exc()
        return module, True
    return module, False

def ended(failed):
    sys.stderr.flush()
    print("\n" + %r + json.dumps(None if failed is None else sorted(failed)), flush=True)
    os._exit(0)

module, broke = run(".".join(parts), ".".join(parts[:-1]))
if broke:
    ended(["reading the check itself"])
tests = unittest.TestSuite()
for label, value in list(vars(module).items()):
    if isinstance(value, type) and issubclass(value, unittest.TestCase) and value.__module__ == module.__name__:
        tests.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(value))
    elif label.startswith("test") and inspect.isfunction(value) and value.__module__ == module.__name__ and not any(
            given.default is given.empty and given.kind not in (given.VAR_POSITIONAL, given.VAR_KEYWORD)
            for given in inspect.signature(value).parameters.values()):
        tests.addTest(unittest.FunctionTestCase(value))
if tests.countTestCases():
    outcome = unittest.TextTestRunner(stream=sys.stderr, verbosity=0).run(tests)
    ended([str(test) for test, _ in outcome.failures + outcome.errors] + [str(test) for test in outcome.unexpectedSuccesses])
if any(isinstance(part, ast.If) and "__name__" in ast.dump(part.test) and "__main__" in ast.dump(part.test)
       for part in ast.parse(source).body):
    ended(["the script"] if run("__main__", None)[1] else [])
ended(None)
""" % CHECK_SAID


class Check:
    """A Python file that is run to see what of the project works."""

    def __init__(self, path, edited):
        self.path, self.edited, self.slowest, self.said = path, edited, 0.0, ""
        self.until = time.monotonic() + ALL_CHECKS_SECONDS

    def time_left(self):
        return self.until - time.monotonic() > 2 * self.slowest + 1

    def failing(self, text=None):
        """Run the check; with `text`, as if the file to edit held that text.  Returns the tests that failed.

        A run that does not come to an end counts as one failed test.  `self.said` keeps what a failing run said.
        """
        started = time.monotonic()
        try:
            ran = subprocess.run([sys.executable, "-B", "-c", RUNNER, self.path, "" if text is None else self.edited],
                                 input=b"" if text is None else text.encode("utf-8"), capture_output=True,
                                 timeout=max(1.0, min(CHECK_SECONDS, self.until - started)))
        except subprocess.TimeoutExpired:
            self.said = "it took longer than %d seconds" % CHECK_SECONDS
            return frozenset(["coming to an end"])
        self.slowest = max(self.slowest, time.monotonic() - started)
        lines = [line.strip() for line in (ran.stderr + b"\n" + ran.stdout).decode("utf-8", "replace").splitlines()
                 if line.strip()]
        failed = ["coming to an end"]
        if lines and lines[-1].startswith(CHECK_SAID):
            failed = json.loads(lines.pop()[len(CHECK_SAID):])
        if failed is None:
            raise Refused("%s holds nothing that can be run here: no unittest class, no test function without "
                          "arguments, and it is not a script; nothing was changed" % self.path)
        if failed:
            telling = [line for line in lines if re.match(r"[A-Za-z_][\w.]*(Error|Exception|Exit|Fails)\b", line)]
            self.said = (telling or lines or ["it ended with status %d" % ran.returncode])[-1][:90]
        return frozenset(failed)


def repeat_tried(path, lesson, check_path):
    """Repeat what a lesson shows on a file, and try what it does not show, keeping what a check settles.

    Tried are the places `repeat` refuses or passes over: code the lesson changed but used another way here, and
    code that fits only the wider reading of the lesson (`wider`).  A tried place is kept when no test of the
    check that passed before fails with it, and a test that passes with it fails when that code is made to fail;
    a check that does not notice the code failing says nothing about it.  A file that was tried is added to the
    lesson as an example, so that what the check settled needs no try the next time.
    """
    target, source = read_python(path, "the file to edit")
    lesson_file, examples, origins = lesson_examples(lesson)
    if examples is None:
        raise Refused("the lesson file does not exist")
    if not inside_project(check_path, "the check").is_file() or not check_path.endswith(".py"):
        raise Refused("the check must be a Python file that exists")
    rules, readings = learn_all(examples, wide=True)
    text = Text(source, "the file")
    found = fitting(rules, text, "the file")
    shown = [place[:4] for place in found if place[4] is SHOWN]
    tries = [place[:4] for place in found if place[4] is not SHOWN]
    taken = {id(place[1]) for place in found}
    tries += [place[:4] for place in fitting(readings, text, "the file", lambda node: id(node) in taken, torn=False)]
    tries.sort(key=lambda place: place[0])

    def with_places(places, fail_at=None):
        try:
            return written(text, shown + places, fail_at=fail_at)
        except Refused:
            return None

    written(text, shown)                 # what the lesson shows must be writable by itself, or the refusal says why
    trying, unsettled, against, kept = [], [], [], []
    for place in tries:
        if (len(trying) < MOST_TRIED and with_places(trying + [place]) is not None
                and with_places(trying + [place], place) is not None):
            trying.append(place)
        else:
            unsettled.append(place)
    if not shown and not trying:
        raise Refused("nothing in the file has the form the lesson changed (%s), also not when what the change "
                      "copied may be other code" % "; ".join(str(rule) for rule in rules))
    lines = lambda places: ", ".join(str(place[1].lineno) for place in sorted(places, key=lambda place: place[0]))
    check = Check(check_path, path)
    before = check.failing()
    if "coming to an end" in before:
        raise Refused("%s does not come to an end on %s as it is (%s); nothing was changed" % (check_path, path, check.said))

    def broken_by(places):
        """The tests that passed on the file as it is and fail with these places changed; None when unknown."""
        edited = with_places(places)
        return None if edited is None or not check.time_left() else check.failing(edited) - before

    broken = broken_by(trying)
    for place in list(trying) if broken else []:
        rest = [other for other in trying if other is not place]
        less = broken_by(rest)
        if less is not None and less < broken:
            trying, broken, said_against = rest, less, check.said
            against.append(place)
            if not broken:
                break
    if broken is None or broken:         # what the tries break cannot be laid at single places: none of them is kept
        unsettled, trying = unsettled + trying, []
        if shown and (broken_by([]) or check.failing(with_places([])) - before):
            raise Refused("%s fails after the change the lesson shows at line %s (%s) and not before; nothing was "
                          "changed" % (check_path, lines(shown), check.said))
    fails_now = check.failing(with_places(trying)) if trying else frozenset()
    for place in trying:
        if check.time_left() and check.failing(with_places(trying, place)) - fails_now:
            kept.append(place)
        else:
            unsettled.append(place)
    if not shown and not kept:
        raise Refused("nothing was changed: %s" % (
            "%s fails with line %s changed (%s)" % (check_path, lines(against), said_against) if against
            else "%s passes or fails the same whether or not the code at line %s fails, so it says nothing "
                 "about that code" % (check_path, lines(unsettled))))
    final = with_places(kept)
    if final is None:
        raise Refused("the places the check settled cannot be written together; nothing was changed")
    target.write_bytes(final.encode("utf-8"))
    if check.failing() - before:
        target.write_bytes(source.encode("utf-8"))
        raise Refused("%s fails on the edited file (%s) and not before; nothing was changed" % (check_path, check.said))
    if kept or against:
        told = ["a try on %s that %s settled" % (path, check_path)]
        told += ["kept line %s: a test that passes with it fails when that code fails" % lines(kept)] if kept else []
        told += ["left line %s: a test fails with it changed" % lines(against)] if against else []
        told += ["not settled, line %s" % lines(unsettled)] if unsettled else []
        try:
            lesson_file.write_bytes(lesson_text(
                examples + [(source, final, tuple(sorted(where(place[1]) for place in unsettled)))],
                origins + ["; ".join(told)]))
        except Refused:
            pass                         # the lesson cannot hold this file beside its other examples; it stays as it was


def main(request):
    action, values = request
    try:
        if action == "edit":
            path, before, after = values
            target, text = read_python(path, "the file to edit")
            _, earlier = read_python(before, "the example's first file")
            _, later = read_python(after, "the example's second file")
            written_bytes = edit_by_example(text, earlier, later).encode("utf-8")
            done = "edited %s the way %s was changed into %s" % (path, before, after)
        elif action == "remember":
            lesson, before, after = values
            target, written_bytes = remember(lesson, before, after)
            done = "remembered in %s the way %s was changed into %s" % (lesson, before, after)
        elif action in ("repeat", "repeat_shown"):
            path, lesson = values
            target, text = read_python(path, "the file to edit")
            _, examples, _ = lesson_examples(lesson)
            if examples is None:
                raise Refused("the lesson file does not exist")
            written_bytes = repeated(learn_all(examples), text, "the lesson",
                                     leave_unshown=action == "repeat_shown").encode("utf-8")
            done = "edited %s the way %s remembers%s" % (path, lesson, " and left the rest alone" if action == "repeat_shown" else "")
        elif action == "repeat_tried":
            path, lesson, check = values
            repeat_tried(path, lesson, check)
            print("edited %s the way %s remembers and tried the rest with %s" % (path, lesson, check))
            return 0
        else:
            raise Refused("this program does not know the action %r" % (action,))
    except Refused as why:
        print("REFUSED: %s" % why)
        return 3
    except RecursionError:
        print("REFUSED: the code is nested too deeply to compare")
        return 3
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(written_bytes)
    print(done)
    return 0


if __name__ == "__main__":
    sys.exit(main(REQUEST))
