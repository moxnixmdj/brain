"""Rename one local variable of one function, and nothing else.

What is renamed: every use of the name that refers to that function's own variable -- in its body and
in nested functions, lambdas and comprehensions that read it.

Refused, because behaviour could change or because this action does not rewrite the form:

* the name is a parameter (the door has a separate action for parameters), or is not assigned in the
  function at all (it is a global, a closure variable or a built-in there);
* a nested scope binds the same name itself (it would be a different variable);
* the name is bound by ``def``, ``class``, ``import``, ``except ... as`` or a ``match`` pattern, or is
  declared ``global`` / ``nonlocal``;
* the new name already occurs in the function, in any role;
* the function calls ``locals``, ``vars``, ``eval``, ``exec`` or ``dir``, which can see variable names.

The edit replaces identifier bytes at the positions the parser reports.  Before anything is written,
the edited text is parsed again and compared with the original tree in which only those names were
changed; if the two differ in any way the file is left alone.
"""
REQUEST = ("lessons_q7/ledger_q7.py", "settle_q7", "subtotal_q7", "running_q7")  # file, function, old, new

import ast
import keyword
import pathlib
import re
import sys

SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef,
               ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
MATCH_NAMES = tuple(getattr(ast, n) for n in ("MatchAs", "MatchStar") if hasattr(ast, n))
SEES_VARIABLE_NAMES = {"locals", "vars", "eval", "exec", "dir"}


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
    node = tree
    for part in dotted.split("."):
        found = [n for n in getattr(node, "body", [])
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == part]
        if len(found) != 1:
            raise Refused("there %s %s" % ("are %d definitions of" % len(found) if found else "is no function", dotted))
        node = found[0]
    if isinstance(node, ast.ClassDef):
        raise Refused("%s is a class, not a function" % dotted)
    return node


def parameters(func):
    args = func.args
    names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
    return names + [a.arg for a in (args.vararg, args.kwarg) if a is not None]


def body_nodes(func):
    return [node for statement in func.body for node in ast.walk(statement)]


def scope_of(node, parent, func):
    """The innermost scope a node sits in; ``func`` for the function's own body."""
    node = parent.get(node)
    while node is not None and node is not func and not isinstance(node, SCOPE_NODES):
        node = parent.get(node)
    return func if node is None else node


def bound_some_other_way(nodes):
    """Names bound by a form this action does not rewrite, with the form's name."""
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


def replace_identifiers(source, places, old, new):
    """Replace ``old`` by ``new`` at (line, byte column) places; refuse if the bytes there are not ``old``."""
    lines = source.encode("utf-8").split(b"\n")
    was = old.encode("utf-8")
    for line_number, column in sorted(places, reverse=True):
        line = lines[line_number - 1]
        if line[column:column + len(was)] != was:
            raise Refused("the text at line %d is not where the parser says it is" % line_number)
        lines[line_number - 1] = line[:column] + new.encode("utf-8") + line[column + len(was):]
    return b"\n".join(lines).decode("utf-8")


def rename_local_variable(source, function, old, new):
    """Return the new text of the file; raise ``Refused`` when the rename cannot be shown to be safe."""
    for name in (old, new):
        if not name.isidentifier() or keyword.iskeyword(name):
            raise Refused("%r is not a name a variable can have" % name)
    if old == new:
        raise Refused("the old and the new name are the same")
    func = find_function(ast.parse(source), function)
    if old in parameters(func):
        raise Refused("%s is a parameter of %s, not a variable: ask to rename the parameter" % (old, function))
    parent = {child: node for node in ast.walk(func) for child in ast.iter_child_nodes(node)}
    nodes = body_nodes(func)
    other = bound_some_other_way(nodes)
    if old in other:
        raise Refused("%s is bound by %s in %s" % (old, other[old], function))
    written = [n for n in nodes if isinstance(n, ast.Name) and n.id == old and not isinstance(n.ctx, ast.Load)]
    if not any(scope_of(n, parent, func) is func for n in written):
        raise Refused("%s is not a variable assigned in %s" % (old, function))
    elsewhere = [n for n in written if scope_of(n, parent, func) is not func]
    elsewhere += [n for n in nodes if isinstance(n, ast.arg) and n.arg == old]
    if elsewhere:
        raise Refused("%s is also bound in a nested scope at line %d" % (old, elsewhere[0].lineno))
    names = {n.id for n in nodes if isinstance(n, ast.Name)} | {n.arg for n in nodes if isinstance(n, ast.arg)}
    if new in names or new in other or new in parameters(func):
        raise Refused("%s is already used in %s" % (new, function))
    seen = sorted(SEES_VARIABLE_NAMES & names)
    if seen:
        raise Refused("%s uses %s(), which can see variable names" % (function, seen[0]))

    places = [(n.lineno, n.col_offset) for n in nodes if isinstance(n, ast.Name) and n.id == old]
    result = replace_identifiers(source, places, old, new)

    expected = ast.parse(source)
    for node in body_nodes(find_function(expected, function)):
        if isinstance(node, ast.Name) and node.id == old:
            node.id = new
    try:
        same = ast.dump(ast.parse(result)) == ast.dump(expected)
    except SyntaxError:
        same = False
    if not same:
        raise Refused("the edit could not be verified, so nothing was written")
    return result


def main(request):
    path, function, old, new = request
    try:
        target, source = read_python(path)
        result = rename_local_variable(source, function, old, new)
    except Refused as why:
        print("REFUSED: %s" % why)
        return 3
    target.write_bytes(result.encode("utf-8"))
    print("renamed the variable '%s' to '%s' in the function '%s' in %s" % (old, new, function, path))
    return 0


if __name__ == "__main__":
    sys.exit(main(REQUEST))
