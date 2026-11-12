"""Inline one local variable that is set once and used once, straight away.

    markup = price * rate            ->     return round(price * rate, 2)
    return round(markup, 2)

The action is deliberately narrow.  It accepts a variable only when removing it cannot change what
the function does, for any values and whatever the expression calls:

* the variable is set by one plain ``name = expression`` and never set again;
* it is read exactly once, in the statement that directly follows, in the same block;
* that read is the first thing the following statement computes -- before it the statement only
  reads names and constants -- and it is computed exactly once (not in a loop test, not in one arm
  of ``and`` / ``or`` / ``if ... else``, not inside a lambda or a comprehension).

Then the same operations run in the same order as before; only "store the name, read the name" is
gone.  One assumption remains and is checked as far as a file can show it: a name the following
statement reads before the variable (``helper`` in ``helper(markup)``) must not be replaced while
the expression runs.  A local name is refused if a nested function declares it ``nonlocal``; a
module-level name is refused if this file assigns it more than once or declares it ``global``.
Code elsewhere that reaches into this module and replaces such a name is not visible from here.

Also refused: a parameter, a name bound in a nested scope or by ``def`` / ``import`` / ``except`` /
``match`` / ``global`` / ``nonlocal``, an expression with ``yield``, ``await`` or ``:=``, an assignment
that shares its lines with other code or a comment, and a function that calls ``locals``, ``vars``,
``eval``, ``exec`` or ``dir``.

Before anything is written the edited text is parsed again and compared with the original tree in
which the assignment was removed and the read replaced by the expression; if the two differ the
file is left alone.
"""
REQUEST = ("lessons_q7/pricing_q7.py", "quote_q7", "markup_q7")  # file, function, variable

import ast
import collections
import io
import pathlib
import re
import sys
import tokenize

SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef,
               ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
MATCH_NAMES = tuple(getattr(ast, n) for n in ("MatchAs", "MatchStar") if hasattr(ast, n))
SEES_VARIABLE_NAMES = {"locals", "vars", "eval", "exec", "dir"}
RUNS_NO_CODE = (ast.Name, ast.Constant, ast.Tuple, ast.List, ast.expr_context)   # a set or dict display hashes its keys
NEEDS_NO_PARENTHESES = (ast.Name, ast.Call, ast.Attribute, ast.Subscript, ast.List, ast.Dict, ast.Set,
                        ast.ListComp, ast.SetComp, ast.DictComp, ast.JoinedStr)
BARE_IN_A_SLOT = NEEDS_NO_PARENTHESES + (ast.Constant, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp)
FOUND, ONLY_READ, COMPUTED = "found", "only read", "computed"


class Refused(Exception):
    """The request is outside what this action can do without risking a change of behaviour."""


def read_python(path):
    target = pathlib.Path(path)
    if target.is_absolute() or ".." in target.parts:
        raise Refused("%s is not a path inside the project" % path)
    if not target.is_file():
        raise Refused("there is no file %s" % path)
    data = target.read_bytes()
    if data.startswith(b"\xef\xbb\xbf") or re.search(rb"\r(?!\n)", data):
        raise Refused("%s has a byte-order mark or bare carriage returns" % path)
    try:
        source = data.decode("utf-8")
        ast.parse(source)
    except (UnicodeDecodeError, SyntaxError, ValueError):
        raise Refused("%s is not valid UTF-8 Python" % path)
    return target, source


def find_function(tree, dotted):
    """The function and whether it sits inside another function."""
    node, nested = tree, False
    for part in dotted.split("."):
        found = [n for n in getattr(node, "body", [])
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == part]
        if len(found) != 1:
            raise Refused("there %s %s" % ("are %d definitions of" % len(found) if found else "is no function", dotted))
        nested = nested or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        node = found[0]
    if isinstance(node, ast.ClassDef):
        raise Refused("%s is a class, not a function" % dotted)
    return node, nested


def parameters(func):
    args = func.args
    names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
    return names + [a.arg for a in (args.vararg, args.kwarg) if a is not None]


def body_nodes(func):
    return [node for statement in func.body for node in ast.walk(statement)]


def scope_of(node, parent, func):
    node = parent.get(node)
    while node is not None and node is not func and not isinstance(node, SCOPE_NODES):
        node = parent.get(node)
    return func if node is None else node


def bound_some_other_way(nodes):
    found = {}
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found[node.name] = "a nested def or class"
        elif isinstance(node, ast.ExceptHandler) and node.name:
            found[node.name] = "an except clause"
        elif isinstance(node, ast.alias):
            found[(node.asname or node.name).split(".")[0]] = "an import"
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            found.update((name, "a global or nonlocal statement") for name in node.names)
        elif MATCH_NAMES and isinstance(node, MATCH_NAMES) and node.name:
            found[node.name] = "a match pattern"
        elif hasattr(ast, "MatchMapping") and isinstance(node, ast.MatchMapping) and node.rest:
            found[node.rest] = "a match pattern"
    return found


def computed_first(statement):
    """The expression a statement evaluates first, exactly once, or None when there is no such thing."""
    if isinstance(statement, (ast.Return, ast.Expr, ast.Assign)):
        return statement.value
    if isinstance(statement, (ast.AnnAssign, ast.AugAssign)):
        return statement.value if isinstance(statement.target, ast.Name) else None
    if isinstance(statement, (ast.If, ast.Assert)):
        return statement.test
    if isinstance(statement, ast.For):
        return statement.iter
    if isinstance(statement, ast.With):
        return statement.items[0].context_expr
    if isinstance(statement, ast.Raise):
        return statement.exc
    if hasattr(ast, "Match") and isinstance(statement, ast.Match):
        return statement.subject
    return None


def reach(node, use, read_before):
    """Walk an expression in the order Python evaluates it, up to ``use``.

    FOUND      ``use`` was reached and nothing before it did more than read a name or a constant.
    ONLY_READ  ``node`` is a name or a constant and is not ``use``.
    COMPUTED   something was computed, or could be skipped or repeated, before ``use`` was reached.
    """
    if node is use:
        return FOUND
    if isinstance(node, ast.Constant):
        return ONLY_READ
    if isinstance(node, ast.Name):
        read_before.append(node.id)
        return ONLY_READ
    if isinstance(node, ast.BinOp):
        parts = [node.left, node.right]
    elif isinstance(node, ast.UnaryOp):
        parts = [node.operand]
    elif isinstance(node, ast.BoolOp):
        parts = node.values[:1]                      # the others may never run
    elif isinstance(node, ast.Compare):
        parts = [node.left, node.comparators[0]]     # a chained comparison may stop early
    elif isinstance(node, ast.Call):
        parts = [node.func]
        for argument in node.args:
            if isinstance(argument, ast.Starred):
                break
            parts.append(argument)
        else:
            for keyword_argument in node.keywords:
                if keyword_argument.arg is None:
                    break
                parts.append(keyword_argument.value)
    elif isinstance(node, ast.Attribute):
        parts = [node.value]
    elif isinstance(node, ast.Subscript):
        parts = [node.value, node.slice]
    elif isinstance(node, ast.Slice):
        parts = [p for p in (node.lower, node.upper, node.step) if p is not None]
    elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        parts = []
        for element in node.elts:
            if isinstance(element, ast.Starred):
                break
            parts.append(element)
    elif isinstance(node, ast.Dict):
        parts = []
        for key, value in zip(node.keys, node.values):
            if key is None:
                break
            parts += [key, value]
    elif isinstance(node, ast.IfExp):
        parts = [node.test]                          # only the test always runs
    elif isinstance(node, ast.JoinedStr):
        parts = []
        for piece in node.values:
            if isinstance(piece, ast.FormattedValue):
                parts.append(piece.value)            # formatting it is a computation: stop here
                break
            parts.append(piece)
    else:
        return COMPUTED
    for part in parts:
        outcome = reach(part, use, read_before)
        if outcome != ONLY_READ:
            return outcome
    return COMPUTED


def module_level_bindings(tree):
    """How many times each name is bound at module level, and the names any function declares global."""
    counts = collections.Counter()

    def visit(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                counts[child.name] += 1
                continue
            if isinstance(child, SCOPE_NODES):
                continue
            if isinstance(child, ast.Name) and not isinstance(child.ctx, ast.Load):
                counts[child.id] += 1
            elif isinstance(child, ast.alias):
                counts[(child.asname or child.name).split(".")[0]] += 1
            elif isinstance(child, ast.ExceptHandler) and child.name:
                counts[child.name] += 1
            visit(child)

    visit(tree)
    declared = {name for node in ast.walk(tree) if isinstance(node, ast.Global) for name in node.names}
    return counts, declared


def whole_slot(holder, use):
    """True when ``use`` is a whole operand position that needs no parentheses around what replaces it."""
    if isinstance(holder, (ast.Return, ast.Expr, ast.Assign, ast.AnnAssign, ast.AugAssign, ast.keyword)):
        return getattr(holder, "value", None) is use
    if isinstance(holder, (ast.If, ast.Assert)):
        return holder.test is use
    if isinstance(holder, ast.For):
        return holder.iter is use
    if isinstance(holder, ast.withitem):
        return holder.context_expr is use
    if isinstance(holder, ast.Raise):
        return holder.exc is use
    if isinstance(holder, ast.Call):
        return any(argument is use for argument in holder.args)
    if isinstance(holder, ast.Subscript):
        return holder.slice is use
    if isinstance(holder, (ast.List, ast.Set)):
        return any(element is use for element in holder.elts)
    if isinstance(holder, ast.Dict):
        return any(v is use for v in holder.values) or any(k is use for k in holder.keys)
    return False


def inline_variable(source, function, name):
    """Return the new text of the file; raise ``Refused`` when the variable cannot be removed safely."""
    if not name.isidentifier():
        raise Refused("%r is not a name a variable can have" % name)
    tree = ast.parse(source)
    func, nested_function = find_function(tree, function)
    if name in parameters(func):
        raise Refused("%s is a parameter of %s, not a variable" % (name, function))
    parent = {child: node for node in ast.walk(func) for child in ast.iter_child_nodes(node)}
    nodes = body_nodes(func)
    other = bound_some_other_way(nodes)
    if name in other:
        raise Refused("%s is bound by %s in %s" % (name, other[name], function))
    if any(isinstance(n, ast.arg) and n.arg == name for n in nodes):
        raise Refused("%s is also a parameter of a nested function or lambda" % name)
    names = {n.id for n in nodes if isinstance(n, ast.Name)}
    seen = sorted(SEES_VARIABLE_NAMES & names)
    if seen:
        raise Refused("%s uses %s(), which can see variable names" % (function, seen[0]))

    written = [n for n in nodes if isinstance(n, ast.Name) and n.id == name and not isinstance(n.ctx, ast.Load)]
    read = [n for n in nodes if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load)]
    if not written:
        raise Refused("%s is not a variable assigned in %s" % (name, function))
    if len(written) != 1:
        raise Refused("%s is set %d times in %s; only a variable set once can be inlined" % (name, len(written), function))
    if scope_of(written[0], parent, func) is not func:
        raise Refused("%s is bound in a nested scope at line %d" % (name, written[0].lineno))
    assignment = parent[written[0]]
    if not (isinstance(assignment, ast.Assign) and assignment.targets == [written[0]]):
        raise Refused("%s is not set by a plain '%s = ...' statement" % (name, name))
    if not read:
        raise Refused("%s is never read; removing it would also remove what it computes" % name)
    if len(read) != 1:
        raise Refused("%s is read %d times; this action inlines a variable that is read once" % (name, len(read)))
    use = read[0]
    value = assignment.value
    if any(isinstance(n, (ast.Yield, ast.YieldFrom, ast.Await, ast.NamedExpr)) for n in ast.walk(value)):
        raise Refused("the expression contains yield, await or ':='")

    block = next(body for body in (getattr(parent[assignment], field, None) for field in ("body", "orelse", "finalbody"))
                 if isinstance(body, list) and assignment in body)
    following = block[block.index(assignment) + 1:block.index(assignment) + 2]
    first = computed_first(following[0]) if following else None
    read_before = []
    if isinstance(following[0] if following else None, ast.AugAssign):
        read_before.append(following[0].target.id)
    if first is None or reach(first, use, read_before) != FOUND:
        raise Refused("%s is not the first thing the next statement computes, exactly once" % name)

    if not all(isinstance(n, RUNS_NO_CODE) for n in ast.walk(value)):
        counts, declared_global = module_level_bindings(tree)
        local = set(parameters(func)) | set(other) | {n.id for n in nodes if isinstance(n, ast.Name)
                                                        and not isinstance(n.ctx, ast.Load)
                                                        and scope_of(n, parent, func) is func}
        handed_out = {n for node in nodes if isinstance(node, (ast.Global, ast.Nonlocal)) for n in node.names}
        for before in read_before:
            if before in handed_out:
                raise Refused("%s is read before %s and is declared global or nonlocal" % (before, name))
            if before in local:
                continue
            if nested_function:
                raise Refused("%s is read before %s and may belong to an enclosing function" % (before, name))
            if counts[before] > 1 or before in declared_global:
                raise Refused("%s is read before %s and this file assigns it more than once" % (before, name))

    lines = source.encode("utf-8").split(b"\n")
    first_line, last_line = lines[assignment.lineno - 1], lines[assignment.end_lineno - 1]
    if first_line[:assignment.col_offset].strip() or last_line[assignment.end_col_offset:].strip():
        raise Refused("the assignment shares its lines with other code or a comment")
    for token in tokenize.tokenize(io.BytesIO(source.encode("utf-8")).readline):
        if token.type == tokenize.COMMENT and assignment.lineno <= token.start[0] <= assignment.end_lineno:
            raise Refused("the assignment carries a comment, which would be lost")

    segment = ast.get_source_segment(source, value)
    if segment is None:
        raise Refused("the expression's text could not be read")
    bare = ("\n" not in segment and (isinstance(value, NEEDS_NO_PARENTHESES)
                                     or (isinstance(value, BARE_IN_A_SLOT) and whole_slot(parent[use], use))))
    replacement = (segment if bare else "(%s)" % segment).encode("utf-8")
    line, was = lines[use.lineno - 1], name.encode("utf-8")
    if line[use.col_offset:use.col_offset + len(was)] != was:
        raise Refused("the text at line %d is not where the parser says it is" % use.lineno)
    lines[use.lineno - 1] = line[:use.col_offset] + replacement + line[use.col_offset + len(was):]
    del lines[assignment.lineno - 1:assignment.end_lineno]
    result = b"\n".join(lines).decode("utf-8")

    expected = ast.parse(source)
    spot, use_spot = (assignment.lineno, assignment.col_offset), (use.lineno, use.col_offset)
    moved = next(n for n in ast.walk(expected) if isinstance(n, ast.Assign) and (n.lineno, n.col_offset) == spot)

    class Inline(ast.NodeTransformer):
        def visit_Assign(self, node):
            return None if node is moved else self.generic_visit(node)

        def visit_Name(self, node):
            return moved.value if (node.lineno, node.col_offset) == use_spot and node.id == name else node

    try:
        same = ast.dump(ast.parse(result)) == ast.dump(Inline().visit(expected))
    except SyntaxError:
        same = False
    if not same:
        raise Refused("the edit could not be verified, so nothing was written")
    return result


def main(request):
    path, function, name = request
    try:
        target, source = read_python(path)
        result = inline_variable(source, function, name)
    except Refused as why:
        print("REFUSED: %s" % why)
        return 3
    target.write_bytes(result.encode("utf-8"))
    print("inlined the variable '%s' in the function '%s' in %s" % (name, function, path))
    return 0


if __name__ == "__main__":
    sys.exit(main(REQUEST))
