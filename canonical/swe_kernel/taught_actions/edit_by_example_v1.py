"""Edit a file the way examples were edited, and keep what the examples teach.

An example is two files: a Python file as it was, and the same file after somebody changed it.
Nobody writes the change down as a program.  This program works the change out from examples, as
rewrite rules, and makes the same change in another file.  The first word of ``REQUEST`` says what to do:

* ``edit``      -- one example, given as its two files, is repeated on a third file at once;
* ``remember``  -- one example is added to a lesson file, which is made when it is not there yet;
* ``repeat``    -- what a lesson file holds is repeated on a file.

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
  may not work with the new code.  Nothing is changed then, and the refusal names the line.  An example
  that shows that use, changed or left alone, settles it.

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
names) is repeated like any other one-line statement.  ``import`` lines an example added or removed
are not repeated: they are read as what the new code needs, and the file to edit must provide it.

A lesson file is JSON.  It holds the examples whole, line by line, and under ``teaches`` what they give:
each change, the ways the changed code was used, the imports it leans on.  ``teaches`` is for the reader;
the rules are worked out from the examples again at every use, and a file whose ``teaches`` differs from
that is refused.  A lesson is never used unasked: the request names it.

This repeats a change.  It does not check that the change is right for the code it is repeated on.

The edit replaces only the bytes of the places that fit a rule.  Everything else in the file,
including comments and layout, stays as it was.
"""
# What to do, and with which files: ("edit", (file to edit, example before, example after)),
# ("remember", (lesson file, example before, example after)) or ("repeat", (file to edit, lesson file)).
REQUEST = ("edit", ("lessons_q7/suite_q7.py", "lessons_q7/shown_q7/earlier.py", "lessons_q7/shown_q7/later.py"))

import ast
import builtins
import io
import json
import pathlib
import re
import sys
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

    def __init__(self, before_text, after_text, label="the example"):
        self.label, self.before_text = label, before_text
        self.old, self.new = Text(before_text, label + "'s first file"), Text(after_text, label + "'s second file")
        whole_old, whole_new = list(self.old.tree.body), list(self.new.tree.body)
        imports, self.only_old, self.only_new = import_changes(self.old.tree, self.new.tree)
        if shape(self.old.tree) == shape(self.new.tree) and not imports:
            raise Refused("the two %s hold the same code%s" % (
                "example files" if label == "the example" else "files of " + label,
                ", apart from import lines that were added or removed" if self.only_old or self.only_new else ""))
        self.places = places_of(self.old.tree, self.new.tree, label) + [[pair] for pair in imports]
        self.old.tree.body, self.new.tree.body = whole_old, whole_new


class Changed:
    """What the examples changed: every unit of their first files by kind, what each changed unit became,
    and which example a changed unit is from."""

    def __init__(self, examples):
        self.candidates, self.into, self.home = {}, {}, {}
        for shown in examples:
            for node in units(shown.old.tree):
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


def learn_all(examples):
    """The rules that turn every example's first file into its second.  `examples` is a list of (before, after) texts.

    Several examples are read as one: places changed the same way are put together across them, a blank appears
    where two such places differ, and code that any one of them left alone speaks against a rule that fits it.
    """
    several = len(examples) > 1
    shown = [Shown(before, after, "example %d" % number if several else "the example")
             for number, (before, after) in enumerate(examples, 1)]
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
    for example in shown:
        replayed, _ = rewrite(rules, example.before_text, example.label + "'s first file", check_names=False)
        if without_imports(ast.parse(replayed), example.only_old) != without_imports(example.new.tree, example.only_new):
            raise Refused("the rules worked out from %s do not reproduce %s"
                          % ("the examples" if several else "the example", example.label))
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


def unshown_use(rule, text, node):
    """None when the code at `node` is used a way the examples showed; otherwise that use.

    A function replaced where it was called one way says nothing about calls of another form: the new function
    may not take those arguments.  So a call must have a number of plain arguments the examples showed and no
    keyword they did not show, and code that is not called must have been shown not called.
    """
    if rule.kind != "expression":
        return None
    use, calls = text.use_of(node), [shown for shown in rule.uses if shown is not None]
    if use is None:
        return None if None in rule.uses else use_said(rule, use)
    if use[0] in {count for count, _ in calls} and use[1] <= frozenset().union(*[named for _, named in calls]):
        return None
    return use_said(rule, use)


def use_said(rule, use):
    return "%s; the examples showed it %s" % (said(use), ", ".join(
        said(shown) for shown in sorted(rule.uses, key=lambda one: (one is not None, one and (one[0], sorted(one[1]))))))


def rewrite(rules, source_text, what="the file", check_names=True):
    """Apply the rules to every place that fits.  Returns (new text, number of places changed)."""
    text = Text(source_text, what)
    places = []
    for node in units(text.tree):
        fitting = []
        for rule in rules:
            bound = {}
            if fits(rule.pattern, node, bound) and same_names(rule, text, node, bound):
                fitting.append((rule, bound))
        if len(fitting) > 1:
            raise Refused("two changes of the example both fit the code at line %d of %s" % (node.lineno, what))
        if fitting:
            other = unshown_use(fitting[0][0], text, node)
            if other is not None:
                raise Refused("line %d of %s has %s %s. A use the examples did not show may not work with the new "
                              "code, so nothing was changed; show that use too, changed or left alone"
                              % (node.lineno, what, " ".join(text.of(node).split())[:60], other))
            places.append((text.span(node), node) + fitting[0])
    places.sort(key=lambda place: place[0])
    for earlier, later in zip(places, places[1:]):
        if later[0][0] < earlier[0][1]:
            raise Refused("two places to change overlap at line %d of %s" % (later[1].lineno, what))
    if not places:
        return source_text, 0
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
        out, at, swap = [], 0, {}
        for (start, end), node, rule, bound in places:
            written, parsed = written_for(rule, node, bound, text)
            looser = rule.kind == "expression" and tightness(parsed) < tightness(node)
            if ((rule.kind == "expression" and tightness(parsed) < text.room(node)) if attempt == 0
                    else looser if attempt == 1 else rule.kind == "expression" and not isinstance(parsed, ATOMS)):
                written = "(%s)" % written
            out += [text.raw[at:start], written.encode("utf-8")]
            at = end
            swap[id(node)] = parsed
        result = b"".join(out + [text.raw[at:]]).decode("utf-8")
        try:
            again = ast.parse(result)
        except (SyntaxError, ValueError):
            continue
        if shape(again) == shape(text.tree, swap):
            if check_names:
                names_still_hold(text, again, places, what)
            return result, len(places)
    raise Refused("the edited text of %s does not parse to the intended code" % what)


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


def repeated(rules, target_text, shown_by):
    result, count = rewrite(rules, target_text)
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
        out.append(entry)
    return out


def lesson_examples(path):
    """The examples a lesson file holds, as (before, after) texts.  Refuses a file that is not a sound lesson."""
    target = inside_project(path, "the lesson file")
    if not target.name.endswith(LESSON_SUFFIX):
        raise Refused("a lesson file's name ends in %s" % LESSON_SUFFIX)
    if not target.is_file():
        return target, None
    try:
        held = json.loads(target.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        held = None
    examples = held.get("examples") if isinstance(held, dict) and held.get("format") == LESSON_FORMAT else None
    if (not isinstance(examples, list) or not examples or not all(
            isinstance(example, dict) and all(
                isinstance(example.get(side), list) and all(isinstance(line, str) for line in example[side])
                for side in ("before", "after")) for example in examples)):
        raise Refused("%s exists and is not a lesson file" % path)
    pairs = [("".join(example["before"]), "".join(example["after"])) for example in examples]
    if held.get("teaches") != described(learn_all(pairs)):
        raise Refused("%s says it teaches something other than what its examples show; it was changed by hand, or "
                      "written by another version of this action. Remember its examples again" % path)
    return target, pairs


def lesson_text(pairs, origins):
    """The bytes of a lesson file.  Raises Refused when the examples, read as one, do not give rules."""
    rules = learn_all(pairs)
    held = {"format": LESSON_FORMAT,
            "what this is": "A change worked out from examples, kept to be repeated on other files. "
                            "'teaches' is checked against 'examples' every time the lesson is used.",
            "teaches": described(rules),
            "examples": [{"shown by": origin, "before": before.splitlines(keepends=True),
                          "after": after.splitlines(keepends=True)} for (before, after), origin in zip(pairs, origins)]}
    return (json.dumps(held, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def remember(lesson, before, after):
    """Add one example to a lesson file, making the file when it is not there.  Returns (path, bytes to write)."""
    target, pairs = lesson_examples(lesson)
    _, earlier = read_python(before, "the example's first file")
    _, later = read_python(after, "the example's second file")
    origins = []
    if pairs is None:
        pairs = []
    else:
        origins = [example.get("shown by") for example in json.loads(target.read_bytes().decode("utf-8"))["examples"]]
        if (earlier, later) in pairs:
            raise Refused("%s already holds this example" % lesson)
    return target, lesson_text(pairs + [(earlier, later)], origins + ["%s -> %s" % (before, after)])


def main(request):
    action, values = request
    try:
        if action == "edit":
            path, before, after = values
            target, text = read_python(path, "the file to edit")
            _, earlier = read_python(before, "the example's first file")
            _, later = read_python(after, "the example's second file")
            written = edit_by_example(text, earlier, later).encode("utf-8")
            done = "edited %s the way %s was changed into %s" % (path, before, after)
        elif action == "remember":
            lesson, before, after = values
            target, written = remember(lesson, before, after)
            done = "remembered in %s the way %s was changed into %s" % (lesson, before, after)
        elif action == "repeat":
            path, lesson = values
            target, text = read_python(path, "the file to edit")
            _, pairs = lesson_examples(lesson)
            if pairs is None:
                raise Refused("the lesson file does not exist")
            written = repeated(learn_all(pairs), text, "the lesson").encode("utf-8")
            done = "edited %s the way %s remembers" % (path, lesson)
        else:
            raise Refused("this program does not know the action %r" % (action,))
    except Refused as why:
        print("REFUSED: %s" % why)
        return 3
    except RecursionError:
        print("REFUSED: the code is nested too deeply to compare")
        return 3
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(written)
    print(done)
    return 0


if __name__ == "__main__":
    sys.exit(main(REQUEST))
