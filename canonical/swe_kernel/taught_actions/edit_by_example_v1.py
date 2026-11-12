"""Edit one file the way an example was edited.

The example is two files: a Python file as it was, and the same file after somebody changed it.
Nobody writes the change down as a program.  This action works the change out from the two files, as
rewrite rules, and then makes the same change in a third file.

How a rule is worked out.  Every place where the two example files differ is found, down to the
smallest expression, keyword argument or one-line statement that holds the difference.  That piece
of code, and what it became, is the rule.  Places that were changed the same way are put together,
and a part of the code becomes a blank (``?1``, ``?2``) only where two of those places differ from
each other.  A blank keeps whatever expression stood there.

Code the example left alone is evidence too.  A rule that would also change something the example
did not change, or would change it another way, is not accepted; more of the surrounding code is then
taken into the rule, up to the whole one-line statement, until the rule fits the changed places only.
Before the third file is touched, the rules are run on the example's first file and must produce its
second file.

Refused, and nothing is written:

* the example adds, removes or reshapes whole statements or blocks (a new line, a renamed function):
  only a change inside one expression or one simple statement is learned;
* a changed place assigns different names than before, or reads a variable that exists only inside
  the example's function: such a change works only together with other changes (a rename does), so
  repeating it one place at a time would leave half of it undone;
* after the edit, the file would read a name it does not define, import or receive as a parameter, or
  would still read a name whose import the edit took away;
* the same code was changed in one place of the example and left alone, or changed another way, in
  another;
* nothing in the file to edit has the form the example changed;
* two places to change overlap, or a comment inside a changed place would be lost;
* the edited text does not parse to exactly the tree intended.

A change of a bare name or a bare number is never a rule by itself; it is kept together with the
expression or statement around it.  Renaming is a different action, which looks at scopes.

An ``import`` line at the top of the file that the example changed in place (same module, other
names) is repeated like any other one-line statement.  ``import`` lines the example added or removed
are not repeated: they are read as what the new code needs, and the file to edit must provide it.

This repeats a change.  It does not check that the change is right for the code it is repeated on.

The edit replaces only the bytes of the places that fit a rule.  Everything else in the file,
including comments and layout, stays as it was.
"""
REQUEST = ("lessons_q7/suite_q7.py", "lessons_q7/shown_q7/earlier.py", "lessons_q7/shown_q7/later.py")  # file to edit, example before, example after

import ast
import builtins
import io
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


def levels_of(old, new, trail):
    """The units a difference sits in, innermost first: the place itself, then more and more code around it."""
    levels = []
    for before, after in ((old, new),) + tuple(reversed(trail)):
        if isinstance(before, ast.mod) or (isinstance(before, ast.stmt) and not isinstance(before, SIMPLE_STATEMENTS)):
            break
        if is_unit(before) and is_unit(after) and kind_of(before) == kind_of(after) and (levels or not too_small(before)):
            levels.append((before, after))
    if not levels:
        raise Refused("line %d of the example adds, removes or reshapes whole statements; only a change inside "
                      "one expression or one simple statement can be learned" % getattr(old, "lineno", 1))
    return levels


def places_of(old_tree, new_tree):
    """One entry per changed place: its levels.  A place inside another changed place is part of it."""
    places, seen = [], set()
    for old, new, trail in changed_places(old_tree, new_tree):
        levels = levels_of(old, new, trail)
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


class Rule:
    """Code of one form, and what it becomes."""

    def __init__(self, kind, pattern, template, shown, pieces, pairs):
        self.kind, self.pattern, self.template = kind, pattern, template
        (self.shown, _), (self.pieces, self.room), self.pairs = shown, pieces, pairs
        self.lines = sorted(before.lineno for before, _ in pairs)
        self.needs = set()               # names the new code reads that the old code did not
        self.own = set()                 # names the new code binds for itself

    def __str__(self):
        number = {}
        for piece in self.shown:
            if not isinstance(piece, str):
                number.setdefault(piece, len(number) + 1)

        def written(pieces):
            return " ".join("".join(piece if isinstance(piece, str) else "?%d" % number[piece] for piece in pieces).split())

        return "%s -> %s" % (written(self.shown), written(self.pieces))


def rule_at(pairs, old, new, changed):
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
    for node in changed.candidates.get(pattern[1], ()):
        bound, again = {}, {}
        if not fits(pattern, node, bound):
            continue
        became = changed.into.get(id(node))
        if (became is None or not fits(template, became, again)
                or any(shape(again[blank], ctx=False) != shape(bound[blank], ctx=False) for blank in again)):
            return None                  # it would change code the example left alone, or change it differently
    before, after = unique[0]
    return Rule(kind_of(before), pattern, template, cut_at_blanks(pattern, before, old),
                cut_at_blanks(template, after, new), unique)


class Changed:
    """What the example changed: every unit of its first file by kind, and what each changed unit became."""

    def __init__(self, tree, places):
        self.candidates = {}
        for node in units(tree):
            self.candidates.setdefault(type(node).__name__, []).append(node)
        self.into = {id(before): after for levels in places for before, after in levels}


def rule_for(group, old, new, changed):
    """The rule about the smallest pieces of code that the example itself does not contradict."""
    for level in range(min(len(levels) for levels in group)):
        rule = rule_at([levels[level] for levels in group], old, new, changed)
        if rule is not None:
            return rule
    return None


def stands_alone(rule, new):
    """Refuse a rule whose places only work together with other changes.  Fills in what the rule needs."""
    for before, after in rule.pairs:
        assigned_before, read_before = names_of(before)
        assigned_after, read_after = names_of(after)
        if assigned_before != assigned_after and not (is_import(before) and is_import(after)
                                                      and isinstance(new.above.get(id(after)), ast.Module)):
            raise Refused("line %d of the example changes which names are assigned (%s); that works only together "
                          "with other changes, as in a rename, and cannot be repeated one place at a time"
                          % (before.lineno, ", ".join(sorted(assigned_before ^ assigned_after))))
        for name in sorted(read_after - read_before):
            if not new.provides(name, after):
                raise Refused("line %d of the example makes the code read '%s', which the example's second file neither "
                              "defines or imports at the top nor receives as a parameter there; a change that leans on "
                              "a local variable cannot be repeated one place at a time" % (before.lineno, name))
            if not hasattr(builtins, name):
                rule.needs.add(name)
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


def learn(before_text, after_text):
    """The rules that turn the example's first file into its second."""
    old, new = Text(before_text, "the example's first file"), Text(after_text, "the example's second file")
    whole_old, whole_new = list(old.tree.body), list(new.tree.body)
    imports, only_old, only_new = import_changes(old.tree, new.tree)
    if shape(old.tree) == shape(new.tree) and not imports:
        raise Refused("the two example files hold the same code" + (
            ", apart from import lines that were added or removed" if only_old or only_new else ""))
    places = places_of(old.tree, new.tree) + [[pair] for pair in imports]
    old.tree.body, new.tree.body = whole_old, whole_new
    changed = Changed(old.tree, places)
    groups = []
    for levels in places:
        for group in groups:
            if rule_for(group + [levels], old, new, changed) is not None:
                group.append(levels)
                break
        else:
            groups.append([levels])
    rules = []
    for group in groups:
        rule = rule_for(group, old, new, changed)
        if rule is None:
            raise Refused("line %d of the example was changed, but the same code was left alone, or changed "
                          "another way, elsewhere in the example" % group[0][0][0].lineno)
        stands_alone(rule, new)
        rules.append(rule)
    replayed, _ = rewrite(rules, before_text, "the example's first file", check_names=False)
    if without_imports(ast.parse(replayed), only_old) != without_imports(new.tree, only_new):
        raise Refused("the rules worked out from the example do not reproduce the example")
    return rules


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


def rewrite(rules, source_text, what="the file", check_names=True):
    """Apply the rules to every place that fits.  Returns (new text, number of places changed)."""
    text = Text(source_text, what)
    places = []
    for node in units(text.tree):
        fitting = []
        for rule in rules:
            bound = {}
            if fits(rule.pattern, node, bound):
                fitting.append((rule, bound))
        if len(fitting) > 1:
            raise Refused("two changes of the example both fit the code at line %d of %s" % (node.lineno, what))
        if fitting:
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
    for _, node, rule, _ in places:
        for name in sorted(rule.needs):
            if name not in defined and not text.provides(name, node):
                raise Refused("the change uses '%s', which %s does not define, import or receive as a parameter "
                              "at line %d" % (name, what, node.lineno))
    taken = text.defined - defined
    for part in ast.walk(edited):
        if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load) and part.id in taken:
            raise Refused("the change takes the name '%s' away from the top of %s, but line %d still uses it"
                          % (part.id, what, part.lineno))


def edit_by_example(target_text, before_text, after_text):
    """`target_text` changed the way `before_text` was changed into `after_text`."""
    rules = learn(before_text, after_text)
    result, count = rewrite(rules, target_text)
    if count == 0:
        raise Refused("nothing in the file has the form the example changed (%s); a part of that form may vary "
                      "only where two changed places of the example differ" % "; ".join(str(rule) for rule in rules))
    return result


def read_python(path, what):
    target = pathlib.Path(path)
    if target.is_absolute() or ".." in target.parts:
        raise Refused("%s must be a path inside the project" % what)
    if not target.is_file():
        raise Refused("%s does not exist" % what)
    try:
        return target, target.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("%s is not UTF-8 text" % what)


def main(request):
    path, before, after = request
    try:
        target, text = read_python(path, "the file to edit")
        _, earlier = read_python(before, "the example's first file")
        _, later = read_python(after, "the example's second file")
        result = edit_by_example(text, earlier, later)
    except Refused as why:
        print("REFUSED: %s" % why)
        return 3
    except RecursionError:
        print("REFUSED: the code is nested too deeply to compare")
        return 3
    target.write_bytes(result.encode("utf-8"))
    print("edited %s the way %s was changed into %s" % (path, before, after))
    return 0


if __name__ == "__main__":
    sys.exit(main(REQUEST))
