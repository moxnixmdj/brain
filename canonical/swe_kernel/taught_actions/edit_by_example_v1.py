"""Edit one file the way an example was edited.

The example is two files: a Python file as it was, and the same file after somebody changed it.
Nobody writes the change down as a program.  This action works the change out from the two files, as
rewrite rules, and then makes the same change in a third file.

How a rule is worked out.  Every place where the two example files differ is found, down to the
smallest expression, keyword argument or one-line statement that holds the difference.  Places that
were changed the same way are put together, and a part of the code becomes a blank (``?1``, ``?2``)
only where two of those places differ from each other.  A rule therefore never says more than the
example shows: one changed place gives a rule for exactly that code; two places that differ in their
arguments give a rule for any arguments; two places in different kinds of statement give a rule that
no longer cares about the statement.  A blank keeps whatever expression stood there.

What the example must also show.  Code the example left alone is evidence too: a rule that would
change something the example did not change is not accepted.  Before the third file is touched, the
rules are run on the example's first file and must produce its second file.

Refused, and nothing is written:

* the example adds, removes or reshapes whole statements or blocks (an added ``import``, a new line,
  a renamed function): only a change inside one expression or one simple statement is learned;
* the same code was changed in one place of the example and left alone in another;
* nothing in the file to edit has the form the example changed;
* two places to change overlap, or a comment inside a changed place would be lost;
* the edited text does not parse to exactly the tree intended.

A change of a bare name or a bare number is never a rule by itself; it is kept together with the
expression or statement around it.  Renaming is a different action, which looks at scopes.

The edit replaces only the bytes of the places that fit a rule.  Everything else in the file,
including comments and layout, stays as it was.
"""
REQUEST = ("lessons_q7/suite_q7.py", "lessons_q7/shown_q7/earlier.py", "lessons_q7/shown_q7/later.py")  # file to edit, example before, example after

import ast
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


def too_small(node):
    """A bare name or number: changing it everywhere it occurs would be a guess about what it means."""
    if isinstance(node, (ast.UnaryOp, ast.Starred)):
        return too_small(node.operand if isinstance(node, ast.UnaryOp) else node.value)
    return isinstance(node, (ast.Name, ast.Constant))


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

    def span(self, node):
        return (self.starts[node.lineno - 1] + node.col_offset, self.starts[node.end_lineno - 1] + node.end_col_offset)

    def of(self, node):
        start, end = self.span(node)
        return self.raw[start:end].decode("utf-8")

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
    """The text of `node` as a list of written text and blank numbers, in order."""
    spots = []

    def find(part, value):
        if part[0] == "?":
            spots.append((text.span(value), part[1]))
        elif part[0] == "N" and isinstance(value, ast.AST):
            for name, inner in part[2]:
                find(inner, getattr(value, name, None))
        elif part[0] == "L" and isinstance(value, list):
            for inner, item in zip(part[1], value):
                find(inner, item)

    find(pattern, node)
    start, end = text.span(node)
    pieces, at = [], start
    for (first, last), blank in sorted(spots):
        pieces += [text.raw[at:first].decode("utf-8"), blank]
        at = last
    return pieces + [text.raw[at:end].decode("utf-8")]


class Rule:
    """Code of one form, and what it becomes."""

    def __init__(self, kind, pattern, template, shown, pieces, lines):
        self.kind, self.pattern, self.template = kind, pattern, template
        self.shown, self.pieces, self.lines = shown, pieces, lines

    def __str__(self):
        number = {}
        for piece in self.shown:
            if not isinstance(piece, str):
                number.setdefault(piece, len(number) + 1)

        def written(pieces):
            return " ".join("".join(piece if isinstance(piece, str) else "?%d" % number[piece] for piece in pieces).split())

        return "%s -> %s" % (written(self.shown), written(self.pieces))


def rule_at(pairs, old, new, old_units):
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
    changed = {id(before) for before, _ in unique}
    if {id(node) for node in old_units if fits(pattern, node, {})} != changed:
        return None                      # it would also change code the example left alone
    before, after = unique[0]
    return Rule(kind_of(before), pattern, template, cut_at_blanks(pattern, before, old),
                cut_at_blanks(template, after, new), sorted(node.lineno for node, _ in unique))


def rule_for(group, old, new, old_units):
    """The rule with the most surrounding code that the whole group shows."""
    for level in range(min(len(levels) for levels in group) - 1, -1, -1):
        rule = rule_at([levels[level] for levels in group], old, new, old_units)
        if rule is not None:
            return rule
    return None


def learn(before_text, after_text):
    """The rules that turn the example's first file into its second."""
    old, new = Text(before_text, "the example's first file"), Text(after_text, "the example's second file")
    if shape(old.tree) == shape(new.tree):
        raise Refused("the two example files hold the same code")
    old_units = units(old.tree)
    groups = []
    for levels in places_of(old.tree, new.tree):
        for group in groups:
            if rule_for(group + [levels], old, new, old_units) is not None:
                group.append(levels)
                break
        else:
            groups.append([levels])
    rules = []
    for group in groups:
        rule = rule_for(group, old, new, old_units)
        if rule is None:
            raise Refused("line %d of the example was changed, but the same code was left alone elsewhere in the example"
                          % group[0][0][0].lineno)
        rules.append(rule)
    replayed, _ = rewrite(rules, before_text, "the example's first file")
    if shape(ast.parse(replayed)) != shape(new.tree):
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
    for wrap in (False, True):
        parts = []
        for piece in rule.pieces:
            if isinstance(piece, str):
                parts.append(piece)
            else:
                inner = text.of(bound[piece])
                parts.append("(%s)" % inner if wrap and not isinstance(bound[piece], ATOMS) else inner)
        written = "".join(parts)
        parsed = parse_like(node, rule.kind, written)
        again = {}
        if (parsed is not None and fits(rule.template, parsed, again)
                and all(shape(again[blank], ctx=False) == shape(bound[blank], ctx=False) for blank in again)):
            return written, parsed
    raise Refused("the change does not fit the code at line %d" % node.lineno)


def rewrite(rules, source_text, what="the file"):
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
    comments = text.comments()
    for (start, end), node, rule, bound in places:
        kept = [text.span(bound[piece]) for piece in rule.pieces if not isinstance(piece, str)]
        for position in comments:
            if start <= position < end and not any(first <= position < last for first, last in kept):
                raise Refused("a comment inside the code at line %d of %s would be lost" % (node.lineno, what))
    for bracketed in (False, True):
        out, at, swap = [], 0, {}
        for (start, end), node, rule, bound in places:
            written, parsed = written_for(rule, node, bound, text)
            if bracketed and rule.kind == "expression" and not isinstance(parsed, ATOMS):
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
            return result, len(places)
    raise Refused("the edited text of %s does not parse to the intended code" % what)


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
    target.write_bytes(result.encode("utf-8"))
    print("edited %s the way %s was changed into %s" % (path, before, after))
    return 0


if __name__ == "__main__":
    sys.exit(main(REQUEST))
