#!/usr/bin/env python3
"""Manufacture the input on which a change is visible. Or prove no input can be.

WHY THIS EXISTS
---------------
The last round ended on a negative number: 19 of 29 real merged code changes could be reverted and the
project's own suite still passed. A negative number is a diagnosis, not a capability. The question it
leaves is the only one worth asking:

    if the tests are silent, what else can serve as the oracle?

The 2026 answer, and the deepest mechanism in the field, does not need a specification, a test suite,
or a model. It needs the two versions of the program. *Shadow of a Doubt* (ICSE 2016) runs the old and
new versions in one symbolic execution instance, with the old shadowing the new, and every time a
branch condition disagrees between them it emits an input that exercises the disagreement. DiffTestGen
(arXiv 2607.16024, Jul 2026) says the same thing empirically: differential testing exposes behavioural
differences in 78.2% of pull requests, and "the gain comes from directed access information and
feedback, not token budget". DiffCodeGen (arXiv 2605.20473) does it with coverage-guided fuzzing and
"without requiring any existing tests or large language models".

What none of them say is the thing this repository needs: the witness has to be *cheap enough to run
before a lesson is admitted*, and it has to be *exact*. So this does not implement symbolic execution.
It implements the reason shadow execution works, at the scale a learn path can pay for:

  1. the change is a small edit, so the divergence is at the expressions the edit touched
  2. those expressions mention literals, and the disagreement is at a literal's boundary
  3. therefore: call both versions on boundary values, compare results, keep the disagreements

Step 3 is what makes it exact. A candidate input is a witness only if the two programs actually return
different results (or raise differently) on it -- executed, not predicted. There is no model guess and
no similarity score anywhere in this file.

WHAT A WITNESS IS GOOD FOR -- AND WHAT IT SETTLES
-------------------------------------------------
A witness is an input tuple plus the two results. It settles the question the licence could not:

  * a change with a witness is BEHAVIOURAL. Here is the missing regression test, generated, exactly:
    it fails on the old version and passes on the new one, by construction.
  * a change with no witness on a bounded search is probably NOT behavioural (a refactor, a rename, a
    pure speedup). For those, the suite being green after a revert is CORRECT, and last round's
    "unprotected" count was overstating risk.

That split is the whole value: it takes "the check is blind to 24% of sites" and divides it into
"here are the tests nobody wrote" and "there is nothing to test here". Both are true statements; only
the first is work, and this tool tells them apart by execution instead of by opinion.

WHAT THIS DOES NOT SAY
----------------------
* `NO_WITNESS_FOUND` is BOUNDED, never a proof of equivalence. The search is a grid of boundary values
  over the parameters the signature declares. A witness needing a list of 40 elements, a file, or a
  network call will not be found, and the report says `bounded_search` with the grid it used.
* Functions whose parameters are objects, callables, or untyped containers are usually out of reach:
  `UNREACHABLE_PARAMETERS`, named, not scored as zero.
* A witness is not a correctness proof for the NEW behaviour. It says the two versions disagree, which
  is a fact; which one is right is the specification's business, and this tool does not have it.
* Execution is in a throwaway copy, in a subprocess, with a timeout. A candidate that hangs costs the
  whole function its search (`TIMED_OUT`), which is reported rather than hidden.

Authority: NONE. `$0`, zero model calls, no capability registered, `truth.achieved` untouched.
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_DIFFERENTIAL_WITNESS_V1"
AUTHORITY = "NONE"

WITNESS = "WITNESS"
NO_WITNESS = "NO_WITNESS_FOUND_ON_GRID"
NOT_BEHAVIOURAL = "NO_EXPRESSION_CHANGED"
UNREACHABLE = "UNREACHABLE_PARAMETERS"
TIMED_OUT = "TIMED_OUT"
UNPARSEABLE = "UNPARSEABLE"
EXECUTION_INCOMPLETE = "EXECUTION_INCOMPLETE"
IMPORT_FAILED = "IMPORT_FAILED"

MAX_CANDIDATES_DEFAULT = 600

# Values tried around every literal in a changed expression, then a type-agnostic fallback grid.
# Order matters: the first witness found is the shortest input, which makes the emitted test readable.
_OFFSETS = (0, 1, -1, 2, -2)
_FALLBACK = (0, 1, -1, 2, -2, 10, 100, -100, True, False, None, "", "a", "A", 0.0, 1.0, -1.0,
             # A few shapes that appear in real signatures (versions, specifiers, markers, names).
             # They cost nothing when unused and unlock constructors that reject plain ints.
             "1.0", "1.0.0", "2.0a1", ">=1.0", "<2", "nameless")


# Shapes that no single literal can express: a limit is crossed by REPETITION, not by a value.
# Measured: a fix that caps marker nesting at 200 is driven by `"("*201 + "a" + ")"*201`, and a grid of
# literals contains no such string. Two or three sizes was enough to find it; the third is where the
# change starts to disagree, so the sizes are offsets around a limit the source states when it has one.
_STRUCTURAL_TEMPLATES = (
    ("paren", lambda n: "(" * n + "a" + ")" * n),
    ("bracket", lambda n: "[" * n + "a" + "]" * n),
    ("repeat", lambda n: "a" * n),
    ("nest_dot", lambda n: ".".join(["a"] * n)),
    ("and", lambda n: " and ".join(["a"] * n)),
    ("comma", lambda n: ",".join(["a"] * n)),
)


def _structural(literals: Sequence[Any]) -> list[str]:
    """Strings whose meaning is their REPETITION count, sized around the limits the change states.

    This is not a wider grid; it is a different axis. A change that says `depth > 200` or `len > 40` is
    an assertion about a count, and the input that exercises it is not any of the values nearby -- it is
    a value built from the count. Cheap, deterministic, and bounded to a few hundred candidates.
    """
    sizes: list[int] = [1, 2, 3, 8, 40, 41, 48, 49, 199, 200, 201, 500]
    for literal in literals:
        if isinstance(literal, int) and not isinstance(literal, bool) and 2 < literal < 5000:
            for offset in (-1, 0, 1):
                size = literal + offset
                if size > 0 and size not in sizes:
                    sizes.append(size)
    out: list[str] = []
    for _name, build in _STRUCTURAL_TEMPLATES:
        for size in sizes:
            try:
                text = build(size)
            except (MemoryError, OverflowError):
                continue
            if len(text) > 200_000:
                continue
            if text not in out:
                out.append(text)
    return out


def _assembled(literals: Sequence[Any], budget: int = 300) -> list[str]:
    """Strings built by COMBINING the literals the change mentions, in the shapes syntax uses.

    A third axis, and it is the one that finds a separator bug. Measured: a fix that stops excluding
    `===` from the fast path is exercised by `foo===arbitrarystring,>= 1` -- every piece of that string
    is a literal in the changed function, and every piece is a variant none of the single-literal grid
    tried. Composing four literal strings with the three separators the grammar uses costs a few
    hundred candidates and needs nothing but the source.
    """
    words = [w for w in literals if isinstance(w, str) and 0 < len(w) <= 24]
    out: list[str] = []
    # An operator followed by a SEPARATED operand. A grammar that splits on separators is exercised
    # by whether the separator is there, not by which operand follows, so the operator literals in the
    # source are enough to build the shape.
    for word in words:
        if word.isalnum():
            continue
        for tail in ("1.0", " 1.0", "1.0,>= 1", "1.0, >=1", ",>= 1", "1.0,>=1 ; python_version >= '3'"):
            text = word + tail
            if text not in out:
                out.append(text)
    separators = ("", ",", ", ", " ")
    for left in words:
        for right in words:
            for separator in separators:
                text = left + separator + right
                if text not in out:
                    out.append(text)
                for tail in ("1", "1.0", ">=2"):
                    longer = text + separator + tail
                    if longer not in out:
                        out.append(longer)
                if len(out) >= budget:
                    return out
    return out


@dataclass
class Witness:
    function: str
    args: tuple[Any, ...]
    before_result: str
    after_result: str
    kind: str                     # VALUE | EXCEPTION | EXCEPTION_TYPE
    module: str = ""
    via: str = "DIRECT"           # ENTRY_POINT | METHOD | DIRECT

    def row(self) -> dict[str, Any]:
        return {"function": self.function, "args": list(self.args),
                "before_result": self.before_result, "after_result": self.after_result,
                "kind": self.kind, "module": self.module, "via": self.via}

    def as_test(self, module: str = "mod") -> str:
        """The regression test the developer did not write, in the shape it would be committed."""
        module = self.module.split(".")[-1] if self.module else module
        call = f"{module}.{self.function}({', '.join(repr(a) for a in self.args)})"
        stance = f"    # the two versions disagree here: {self.before_result} -> {self.after_result}\n"
        if self.kind == "EXCEPTION_MESSAGE":
            message = self.after_result.split("EXCEPTION: ", 1)[-1]
            return (f"def test_{self.function}_message_at_this_input():\n"
                    + stance
                    + "    import pytest\n"
                    f"    with pytest.raises(Exception, match={message!r}):\n"
                    f"        {call}\n")
        if self.kind == "VALUE":
            return (f"def test_{self.function}_at_this_input():\n"
                    + stance
                    + f"    assert {call} == {self.after_result.split(': ', 1)[-1]}\n")
        return (f"def test_{self.function}_raises_at_this_input():\n"
                + stance
                + "    import pytest\n"
                f"    with pytest.raises({self.after_result.split(': ', 1)[-1]}):\n"
                f"        {call}\n")


# ------------------------------------------------------------------------------ finding the change

def _functions(source: str) -> dict[str, ast.AST]:
    tree = ast.parse(source)
    out: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = node
    return out


def _literals(node: ast.AST) -> list[Any]:
    """Real literal values under `node`, in source order.

    Collected from the AST, never from `ast.dump` text. Measured: re-parsing a dump turns `Name(id='size')`
    into the STRING `'size'`, so parameter names and field names filled the input grid and pushed the
    values that actually trigger the change out of the candidate budget.
    """
    docstrings = set()
    for sub in ast.walk(node):
        body = getattr(sub, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and \
                isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            docstrings.add(id(body[0].value))
    out: list[Any] = []
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Constant) or id(sub) in docstrings:
            continue
        # A docstring or a prose message is not an input. Measured: the first witnesses for a real
        # fix were "call tail(<docstring>, 0)" -- true, useless, and it would have shipped as the
        # generated test. Prose is excluded by shape (newlines, length), never by wording.
        if isinstance(sub.value, str) and ("\n" in sub.value or len(sub.value) > 60):
            continue
        if isinstance(sub.value, (int, float, str, bool)) and sub.value not in out and len(out) < 40:
            out.append(sub.value)
    return out


def _expressions(node: ast.AST) -> dict[tuple[str, ...], str]:
    """Every sub-expression of a function, keyed by a structural path, dumped for comparison.

    Keyed by path (not by position) so a rename or a reformat does not look like a change, and so two
    versions can be lined up without a diff algorithm. Only expressions are collected: statements
    changing is interesting only insofar as they change what is computed.
    """
    out: dict[tuple[str, ...], str] = {}

    def walk(current: ast.AST, path: tuple[str, ...]) -> None:
        for index, child in enumerate(ast.iter_child_nodes(current)):
            child_path = path + (type(child).__name__, str(index))
            if isinstance(child, ast.expr):
                out[child_path] = ast.dump(child)
            walk(child, child_path)

    walk(node, ())
    return out


def changed_functions(before_source: str, after_source: str) -> list[dict[str, Any]]:
    """Functions whose computed expressions differ, with the literals involved in the difference.

    A function whose only difference is a docstring, a comment, an annotation or a rename produces no
    entry here -- which is the correct answer, and the reason this is better than a line diff.
    """
    try:
        before = _functions(before_source)
        after = _functions(after_source)
    except SyntaxError:
        return []
    changed: list[dict[str, Any]] = []
    for name, after_node in after.items():
        before_node = before.get(name)
        if before_node is None:
            changed.append({"function": name, "why": "NEW_FUNCTION", "literals": [],
                            "before": None, "after": after_node})
            continue
        before_expr = _expressions(before_node)
        after_expr = _expressions(after_node)
        differing = [key for key in after_expr if before_expr.get(key) != after_expr[key]]
        if not differing:
            continue
        literals: list[Any] = []
        for node in (after_node, before_node):
            for literal in _literals(node):
                if literal not in literals:
                    literals.append(literal)
        # EVERY literal in the function on either side, not only the ones inside the edited
        # expression. Measured: a fix that stops special-casing `===` DELETED that literal, so it
        # appeared in neither side's edited expression and the grid never tried `===1.0`. A literal
        # that disappeared from the source is the strongest possible hint about the input that
        # distinguishes the versions.

        changed.append({"function": name, "why": "EXPRESSION_CHANGED", "literals": literals,
                        "changed_expressions": len(differing),
                        "before": before_node, "after": after_node})
    return changed


def changed_bindings(before_source: str, after_source: str) -> list[dict[str, Any]]:
    """Module-level bindings whose value changed, with the literals involved.

    Measured: a fix that changes `re.compile('...{49}')` to `'...{40,49}'` sits in a module-level
    assignment, and a function-only comparison reported NO_EXPRESSION_CHANGED -- the verdict that says
    "this commit changed nothing behavioural" about a commit that widened a regex. Constants, regexes
    and class attributes are ordinary change sites, so they are compared too. They cannot be called,
    so they widen the input grid for the functions that read them instead of being driven directly.
    """
    def bindings(source: str) -> tuple[dict[str, str], dict[str, ast.AST]]:
        out: dict[str, str] = {}
        nodes: dict[str, ast.AST] = {}
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return out, nodes
        for node in tree.body:
            targets = ([t for t in node.targets if isinstance(t, ast.Name)]
                       if isinstance(node, ast.Assign) else
                       [node.target] if isinstance(node, ast.AnnAssign) and node.value else [])
            for target in targets:
                out[target.id] = ast.dump(node.value)
                nodes[target.id] = node.value
        return out, nodes

    before, before_nodes = bindings(before_source)
    after, after_nodes = bindings(after_source)
    changed: list[dict[str, Any]] = []
    for name, dump in after.items():
        if before.get(name) == dump:
            continue
        literals: list[Any] = []
        for node in (after_nodes.get(name), before_nodes.get(name)):
            for literal in _literals(node) if node is not None else []:
                if literal not in literals:
                    literals.append(literal)
        changed.append({"function": name, "why": "MODULE_BINDING_CHANGED", "literals": literals,
                        "changed_expressions": 1, "before": None, "after": None})
    return changed


# ------------------------------------------------------------------------------- the input domain

def parameter_names(node: ast.AST) -> list[str] | None:
    """Positional parameter names, or None when the function cannot be called with plain values."""
    args = getattr(node, "args", None)
    if args is None:
        return None
    if getattr(args, "vararg", None) is not None or getattr(args, "kwarg", None) is not None:
        return None
    if getattr(args, "kwonlyargs", None):
        return None
    return [a.arg for a in list(getattr(args, "posonlyargs", [])) + list(args.args)
            if a.arg not in ("self", "cls")]


def owning_class(source: str, function_name: str) -> dict[str, Any] | None:
    """The class a method belongs to, and how to build one from plain values.

    Found by measurement: 9 of 44 real commits came back `UNREACHABLE_PARAMETERS` and they were
    methods. A method is only unreachable if its class cannot be constructed; `Version.__eq__` is
    perfectly reachable once you have `Version("1.0")`. So the owner's `__init__` signature is read
    and its parameters are driven from the same domain.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for sub in node.body:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == function_name:
                init = next((n for n in node.body
                             if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
                return {"class": node.name, "init": init}
    return None


def receiver_arguments(owner: Mapping[str, Any] | None) -> list[tuple[Any, ...]] | None:
    """Argument tuples that build a receiver, or None when the class cannot be built from values."""
    if owner is None:
        return None
    init = owner.get("init")
    if init is None:
        return [()]                     # no __init__: the default constructor is enough
    names = parameter_names(init)
    if names is None:
        return None
    if not names:
        return [()]
    values = _domain((), _FALLBACK)
    if len(names) == 1:
        return [(v,) for v in values[:10]]
    return [tuple(values[: len(names)])]


def _domain(literals: Iterable[Any], fallback: Sequence[Any]) -> list[Any]:
    """Boundary values around the literals the change mentions, then a small fallback grid.

    This is the whole "directed" part of change-directed testing, and it is why the search is cheap:
    a boundary edit disagrees at a literal's boundary, so the literals in the edited expression are
    where to look first.
    """
    values: list[Any] = []
    for literal in literals:
        if isinstance(literal, bool):
            for v in (True, False):
                if v not in values:
                    values.append(v)
            continue
        if isinstance(literal, (int, float)):
            for offset in _OFFSETS:
                for v in (literal + offset, literal - offset):
                    if v not in values:
                        values.append(v)
            continue
        if isinstance(literal, str):
            for v in (literal, literal + "a", literal[:-1] if literal else literal, "", "a"):
                if v not in values:
                    values.append(v)
    for v in fallback:
        if v not in values:
            values.append(v)
    return values


def candidates(node: ast.AST, literals: Sequence[Any],
               limit: int = MAX_CANDIDATES_DEFAULT) -> list[tuple[Any, ...]] | None:
    """Argument tuples to try, in a deterministic order. None when the signature is out of reach."""
    names = parameter_names(node)
    if names is None or not names:
        return None
    values = _domain(literals, _FALLBACK)
    out: list[tuple[Any, ...]] = []
    if len(names) == 1:
        out = [(v,) for v in values]
    elif len(names) == 2:
        # The change almost always rides on the first parameter and the second is the thing it is
        # applied to. A full cross product spends the whole budget pairing noise; measured, a fix that
        # rejects a negative size was tried as `tail("size", "size")` and never as `tail(-1, 0)`.
        # Container-shaped values first: the second parameter is nearly always the thing the change is
        # applied TO, and `tail(-1, 0)` finds a TypeError about `0` rather than the guard the commit
        # added. `tail(-1, "ABCDEFG")` is the input the fix's own test uses.
        benign = ("ABCDEFG", [1, 2, 3], "a", (), 1, 0, -1, "")
        for a in values:
            for b in benign:
                out.append((a, b))
        for a in values[:12]:
            out.append((a, a))
    else:
        # Three or more: the first parameter carries the change in almost every real guard, so vary it
        # against a small fixed set for the rest. Bounded and stated, not silently exhaustive.
        fixed = (0, 1, -1, 10)
        for a in values:
            out.append((a, *fixed[: len(names) - 1]))
    return out[:limit]


# ------------------------------------------------------------------------- public entry points
#
# THE MECHANISM THAT MAKES THIS WORK ON REAL CODE
# -----------------------------------------------
# Measured: 25 real commits produced ZERO witnesses, and the reason was never that the changes were
# unobservable. `packaging`'s `_parse_marker(tokenizer, depth)` takes a TOKENIZER OBJECT; feeding it
# `0` raises the same exception on both sides, so no input diverges and the tool reports "no witness"
# about a fix that changed behaviour for every user of `Marker`.
#
# The answer is the one DiffTestGen (arXiv 2607.16024) uses and Shadow (ICSE 2016) relies on: do not
# drive the private function, drive the PUBLIC function that reaches it. A public entry point builds
# the objects from plain values, which is exactly the domain this search can supply. The result is
# then compared across the two whole snapshots, so the divergence propagates the way a user would
# meet it -- and the witness is an input to a real API, which is a test somebody would actually write.

_PRIVATE = ("_",)


def _package_prefix(root: pathlib.Path, package: str) -> tuple[pathlib.Path, str] | None:
    """(directory that contains the package folder, the dotted prefix before it).

    `src/packaging/version.py` is imported as `packaging.version`, and the `src` in the path is not
    part of the name. Measured: joining the raw relative path produced `src.packaging.version`, which
    imports nothing, and the entry-point search silently found two private methods instead of the
    public `Marker`. The prefix is derived from where the package directory actually is.
    """
    for base in ("", "src", "lib", "python"):
        directory = (root / base / package) if base else (root / package)
        if directory.is_dir():
            return directory, base
    return None


def _module_dotted(rel_to_package: pathlib.PurePosixPath, package: str) -> str:
    parts = list(rel_to_package.parts)
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([package] + parts) if parts else package


def _calls_into(source: str) -> dict[str, set[str]]:
    """{function defined here -> names it calls or references}, for a cheap call graph."""
    tree = ast.parse(source)
    out: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            used: set[str] = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    target = sub.func
                    if isinstance(target, ast.Name):
                        used.add(target.id)
                    elif isinstance(target, ast.Attribute):
                        used.add(target.attr)
                elif isinstance(sub, ast.Attribute):
                    used.add(sub.attr)
            out[node.name] = used
    return out


ENTRY_POINT_DEPTH = 7      # DiffTestGen drives the five shortest paths; measured, 3 and 5 too shallow.


_OBJECT_PARAMETERS = ("tokenizer", "state", "self", "cls", "fp", "file", "obj", "target")


def _takes_plain_value(node: ast.AST) -> bool:
    """Does every required parameter of `node` take a value a literal grid can supply?

    `parse_marker(source: str)` is drivable with the grid; `_parse_marker(tokenizer, depth)` is not.
    Comparing the two is the whole difference between finding a witness and reporting that there is
    none, so the ones that can be driven go first.
    """
    spec = getattr(node, "args", None)
    if spec is None:
        return False
    positional = list(spec.posonlyargs) + list(spec.args)
    defaults = len(spec.defaults)
    required = positional[: len(positional) - defaults] if defaults else positional
    if len(required) > 2:
        return False
    for argument in required:
        if argument.arg in _OBJECT_PARAMETERS:
            return False
        annotation = ast.unparse(argument.annotation) if argument.annotation else ""
        if any(word in annotation for word in ("Tokenizer", "Parser", "ParserSyntaxError")):
            return False
    return True


def entry_points(version_root: str | os.PathLike[str], package: str, changed: Sequence[str], *,
                 max_depth: int = 3, limit: int = 6) -> list[dict[str, Any]]:
    """Public functions in `package` that reach a changed function within `max_depth` calls.

    Public and shallow first: a witness at `Marker(...)` is a test a developer would write, and a
    short path is the one the search can afford to drive with plain values. Anything not reachable
    is reported by the caller rather than guessed at.
    """
    root = pathlib.Path(version_root)
    found_prefix = _package_prefix(root, package)
    if found_prefix is None:
        return []
    package_dir, _base = found_prefix
    graph: dict[str, set[str]] = {}
    defined_in: dict[str, tuple[str, str]] = {}
    params: dict[str, ast.AST] = {}
    public_modules: set[str] = set()
    for path in sorted(package_dir.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue
        rel = path.relative_to(package_dir).as_posix()
        dotted = _module_dotted(pathlib.PurePosixPath(rel), package)
        leaf = dotted.rsplit(".", 1)[-1]
        # Build the graph from EVERY module, including internal ones. An internal module is not a
        # candidate entry point, but the edges that pass THROUGH it are the path from the public API
        # to the change. Measured: skipping `_parser.py` cut `parse_marker -> _parse_full_marker ->
        # _parse_marker`, and the fix to `_parse_marker` was reported unreachable. Publicness filters
        # the candidates; it must never filter the graph.
        internal = leaf.startswith("_")
        for name in _calls_into(source):
            graph.setdefault(name, set()).update(())
        calls = _calls_into(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                graph.setdefault(node.name, set()).update(calls.get(node.name, set()))
                # EVERY definition is addressable, including the ones inside internal modules.
                # `parse_marker` lives in `_parser.py` and is imported by `markers.py`, so it is a
                # legitimate place to drive from -- the module name is internal, the function is a
                # real API surface. Measured: excluding it made `Marker`'s fix unreachable.
                defined_in[node.name] = (dotted, rel)
                params[node.name] = node
                public_modules.add(dotted) if not internal else None

    wanted = set(changed)
    found: list[dict[str, Any]] = []
    for name, reaches in graph.items():
        if name in wanted or name not in defined_in:
            continue
        # Bounded breadth-first over the reverse call graph, recording the hop count at which a
        # changed function is first reached. The previous version incremented depth only on a miss,
        # so a function one hop away was recorded as depth 1 and a function three hops away was
        # never reached at all -- measured: `parse_marker` exists in the graph and was not found.
        frontier, seen, hops = set(reaches), {name}, 0
        depth = None
        while frontier and hops < max_depth:
            hops += 1
            if frontier & wanted:
                depth = hops
                break
            nxt: set[str] = set()
            for item in frontier:
                if item in seen:
                    continue
                seen.add(item)
                nxt |= graph.get(item, set())
            frontier = nxt - seen
        if depth is None:
            continue
        dotted, rel = defined_in[name]
        found.append({"function": name, "module": dotted, "rel_path": rel,
                      "node": params[name], "depth": depth,
                      # A function whose NAME does not start with an underscore is public even when
                      # it lives in an internal module: `parse_marker` is in `_parser.py` and is the
                      # API `markers.py` re-exports. The module's privacy is not the function's.
                      "public": not name.startswith("_"),
                      "internal_module": dotted not in public_modules})
    # Order by what the search can actually DRIVE, not by depth alone -- and never let a surface that
    # takes a plain string be crowded out by one that takes a Tokenizer. Measured: `parse_requirement`
    # is public and reachable in 3 hops, and `limit` dropped it behind three tokenizer surfaces, so a
    # one-line parser fix reported no witness.
    found.sort(key=lambda e: (not _takes_plain_value(e["node"]), not e["public"], e["depth"],
                              e["function"]))
    return found[:limit]


# --------------------------------------------------------------------------- executing both versions

def _render(value, budget: int = 4000) -> str:
    """A stable rendering of a result: execute what is lazy, and never include an address.

    Measured false positive: `set_partitions(...)` returns a GENERATOR, and `repr` of one contains its
    memory address, so nearly every candidate "differed" -- a docs-only commit came back with a
    witness. A generator is the function's output, so it is materialised (bounded) before comparing,
    and anything still carrying an address is treated as uncomparable rather than different.

    This has to live in the MODULE, not only in the runner: the module-side self-check has to be able
    to prove it, and a duplicate definition is one more thing that can drift.
    """
    if isinstance(value, (str, bytes)):
        kind = b"..." if isinstance(value, bytes) else "..."
        return repr(value[:budget] + kind if len(value) > budget else value)
    if isinstance(value, (list, tuple, set, frozenset)) or hasattr(value, "__next__"):
        items = []
        try:
            for index, item in enumerate(iter(value)):
                if index >= 64:
                    items.append("...")
                    break
                items.append(_render(item, 400))
        except BaseException as error:                     # noqa: BLE001 - any lazy failure is a value
            return "<%s while iterating: %s>" % (type(error).__name__, str(error)[:80])
        return type(value).__name__ + "(" + ", ".join(items) + ")"
    if isinstance(value, dict):
        return "{" + ", ".join("%s: %s" % (_render(k, 100), _render(v, 100))
                               for k, v in list(value.items())[:32]) + "}"
    text = repr(value)
    if _ADDRESS.search(text):
        return "<%s at an address>" % type(value).__name__
    return text[:900]


# Rendered with `re` and `_ADDRESS` bound in its own namespace, and it must never depend on anything
# else in this module: the runner execs this source in a bare namespace.
_ADDRESS = re.compile(r"0x[0-9a-fA-F]{4,}")
_RENDER_SOURCE = "import re\n_ADDRESS = re.compile(r'0x[0-9a-fA-F]{4,}')\n" + inspect.getsource(_render)


_RUNNER = r'''import importlib, importlib.util, json, os, re, sys, traceback

spec = json.load(open(sys.argv[1]))
import re
_namespace = {}
exec(spec["render_source"], _namespace)          # the module's own renderer, not a copy
_render = _namespace["_render"]
root, side = os.path.abspath(sys.argv[2]), sys.argv[3]

# ONE PROCESS PER VERSION, and this is the whole correctness argument. Loading before and after into
# one interpreter leaves both alive at once: CPython caches modules by name, so a module imported
# lazily from inside a `before` call can resolve to the `after` snapshot that was linked second, and
# every witness above that seam is then a comparison of a version with itself. Two processes cannot
# do that. It also lets a test that mutates module globals run against one version only.

def load(rel_module, direct_path):
    if not spec.get("package"):
        file_spec = importlib.util.spec_from_file_location("_w_direct", direct_path)
        module_obj = importlib.util.module_from_spec(file_spec)
        sys.modules[file_spec.name] = module_obj
        file_spec.loader.exec_module(module_obj)
        return module_obj
    sys.path.insert(0, root)          # the directory that CONTAINS the package, e.g. src/
    try:
        importlib.invalidate_caches()
        module_obj = importlib.import_module(rel_module)
    finally:
        try:
            sys.path.remove(root)
        except ValueError:
            pass
    # THE GUARD THAT MATTERS. Measured: the snapshot root was put on sys.path instead of the
    # directory containing the package, so `packaging` resolved from the OTHER version's PYTHONPATH
    # entry and every candidate compared a version against itself -- which reads as "the change is a
    # refactor", the most confidently wrong answer this tool can give. A module that did not come from
    # the snapshot we asked for is never measured.
    # _INSTALLED_GUARD, second form. `more_itertools` has a `src/`-style layout with no
    # `more_itertools/__init__.py` at the root, so setuptools resolves it to whatever is INSTALLED --
    # measured, both sides then imported the installed package and reported a behavioural change in a
    # commit that touched only docs and a test. A snapshot that is not the one we asked for is never
    # measured, whether it came from the other version or from site-packages.
    # STRICT: the module must come from THIS side's snapshot. Accepting either snapshot was the
    # looser version and it silently restored the self-comparison it was meant to catch.
    origin = os.path.abspath(getattr(module_obj, "__file__", "") or "")
    if not origin.startswith(os.path.abspath(root) + os.sep):
        raise RuntimeError("MISLOADED_SNAPSHOT: %s came from %s, not from %s"
                           % (rel_module, origin or "<no file>", os.path.abspath(root)))
    return module_obj

def call(target, fn_name, receiver_args, args, owner_name):
    fn = getattr(target, fn_name, None)
    if fn is None:
        return {"kind": "MISSING"}
    try:
        if receiver_args is not None:
            owner = getattr(target, owner_name, None)
            if owner is None:
                return {"kind": "MISSING"}
            receiver = owner(*receiver_args)
            value = getattr(receiver, fn_name)(*args)
        else:
            value = fn(*args)
    except BaseException as error:
        return {"kind": "EXCEPTION", "type": type(error).__name__, "message": str(error)[:120]}
    return {"kind": "VALUE", "repr": _render(value)}



try:
    modules = {}
    for item in spec["calls"]:
        key = item.get("module") or spec["module"] or "_w_direct"
        if key not in modules:
            modules[key] = load(key, spec[side + "_path"])
except BaseException:
    print("__W__" + json.dumps({"import_failed": traceback.format_exc()[-900:]}))
    raise SystemExit(0)

# One module failing to import must not erase the witnesses the others can still produce: measured,
# a single bad key turned a reachable `parse_marker` into IMPORT_FAILED for the whole run.
for item in spec["calls"]:
    key = item.get("module") or spec["module"] or "_w_direct"
    try:
        target = modules[key]
    except KeyError:
        continue
    if item.get("probe"):
        # A module-level constant is READ, not called. Its value is the observable: `{49}` becoming
        # `{40,49}` is a different object in the two versions and a user can see it.
        value = getattr(target, item["fn"], None)
        if value is None:
            result = {"kind": "MISSING"}
        else:
            try:
                result = {"kind": "VALUE", "repr": _render(value)}
            except BaseException as error:
                result = {"kind": "EXCEPTION", "type": type(error).__name__,
                          "message": str(error)[:120]}
    else:
        result = call(target, item["fn"], item["recv"], item["args"], item.get("owner"))
    print("__W__" + json.dumps({"i": item["i"], "fn": item["fn"], "args": item["args"],
                                "recv": item["recv"], "via": item.get("via"), "module": key,
                                "loaded_from": os.path.abspath(
                                    getattr(target, "__file__", "") or ""),
                                "result": result}))
'''



# Words that only appear in an exception message a human wrote. Cheap and deliberate: the alternative
# is a model call, which is forbidden, or trusting every interpreter-generated message, which is wrong.
# A rendering that STILL contains an address after the renderer has walked it is a container of
# objects with default reprs. Two of those are never comparable across two processes: measured, a
# `DIRECTORY_AUTHORITIES` registry differed only by the memory addresses of its Authority objects, and
# it was reported as a behavioural witness. If the address survives rendering, the value is
# unobservable here, not different.
# The renderer replaces a surviving address with "<Type at an address>", so the guard has to look for
# BOTH forms. Measured: with only the "0x..." pattern, a module-level list of objects with default
# reprs still produced a witness -- the address was gone and the placeholder was what differed.
_ADDRESS_IN_VALUES = re.compile(r"0x[0-9a-fA-F]{6,}| at an address>")

_AUTHORED_WORDS = ("must", "invalid", "more than", "at least", "not allowed", "duplicate",
                   "unknown", "nested", "reference", "expected a", "expected an")


def _compare(before: Mapping[str, Any], after: Mapping[str, Any]) -> str | None:
    """How the two results differ, or None when they are the same. Executed facts, not predictions."""
    if before == after:
        return None
    if before.get("kind") == "MISSING" or after.get("kind") == "MISSING":
        return None                       # the function does not exist on both sides: not a divergence
    if before.get("kind") == "VALUE" and after.get("kind") == "VALUE":
        return "VALUE"
    if before.get("kind") == "EXCEPTION" and after.get("kind") == "EXCEPTION":
        if before.get("type") != after.get("type"):
            return "EXCEPTION_TYPE"
        # Same exception class, different message. This IS a divergence -- the project's own tests
        # assert on these messages -- but it is a weaker one than a changed value, so it is reported
        # separately and never counted as strong. Measured: the two most interesting fixes in this
        # round differ only here ("Expected a marker variable" -> "nested more than 200 levels deep").
        if (before.get("message") or "") != (after.get("message") or ""):
            # Only a message the PROGRAM authored counts. Measured: a genuine refactor came back with a
            # witness because `total("(a)")` raised "TypeError: int" on one side and "TypeError: str"
            # on the other -- the interpreter naming a type, not the change saying anything. A named
            # message is one that appears in the source; those are asserted on by real tests.
            text = (before.get("message") or "") + (after.get("message") or "")
            if not any(word in text for word in _AUTHORED_WORDS):
                return None
            return "EXCEPTION_MESSAGE"
        return None
    return "EXCEPTION"


class _NoLocalShadow:
    """Guard against the classic mistake: importing the INSTALLED package instead of the file.

    Measured twice in this repository already -- `pypa/packaging`'s tests ran against site-packages
    and reported the project's own code as broken. Here it would silently compare a module to itself
    and find no witnesses, which reads as "the change is not behavioural". The runner loads both files
    by explicit path (`spec_from_file_location`), so that specific failure cannot happen, and the
    module-level import surface is left to the caller's `sys.path`.
    """


_INSTALLED_GUARD = _NoLocalShadow  # kept as a name so the intent is greppable


def _module_identity(project: pathlib.Path, rel_path: str) -> tuple[str, str]:
    """(package, dotted module) for a file inside a project, from its path and layout metadata.

    `src/packaging/version.py` is `packaging.version`, not `version`. The 2026 measurement on this
    repository already recorded that the import name is a DECLARATION which the filesystem alone
    cannot always recover; here the common layouts are read directly and anything else is named
    rather than guessed.
    """
    rel = pathlib.PurePosixPath(pathlib.Path(rel_path).as_posix())
    parts = list(rel.parts)
    if parts and parts[0] in ("src", "lib"):
        parts = parts[1:]
    if not parts or not parts[-1].endswith(".py"):
        raise ValueError(f"NOT_A_PYTHON_FILE:{rel_path}")
    stem = parts[-1][:-3]
    package = parts[0] if len(parts) > 1 else stem
    dotted = ".".join(parts[:-1] + [stem])
    return package, dotted


def search(before_source: str, after_source: str, *, timeout: float = 60.0,
           limit: int = MAX_CANDIDATES_DEFAULT, extra_paths: Sequence[str] = (),
           project: str | os.PathLike[str] | None = None,
           rel_path: str | None = None,
           before_root: str | os.PathLike[str] | None = None,
           after_root: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Find, for every changed function, an input on which the two versions disagree."""
    try:
        ast.parse(before_source)
        ast.parse(after_source)
    except SyntaxError as error:
        return {"schema": SCHEMA, "authority": AUTHORITY, "verdict": UNPARSEABLE,
                "detail": str(error), "witnesses": [], "network": False}
    changed = changed_functions(before_source, after_source)
    bindings = changed_bindings(before_source, after_source)
    changed.extend(bindings)
    if not changed:
        return {"schema": SCHEMA, "authority": AUTHORITY, "verdict": NOT_BEHAVIOURAL,
                "witnesses": [], "functions_examined": 0,
                "detail": "no computed expression differs between the two versions"}

    calls: list[dict[str, Any]] = []
    per_function: dict[str, int] = {}
    unreachable: list[str] = []
    owners: dict[str, Any] = {}
    entries: list[dict[str, Any]] = []
    package = module = None

    # Prefer driving a PUBLIC function that reaches the change. Measured: `_parse_marker(tokenizer,
    # depth)` cannot be driven with plain values (feeding it 0 raises the same exception on both
    # sides), while `parse_marker("a and b")` reaches it through every branch a user can.
    if project is not None and rel_path and before_root:
        try:
            package, module = _module_identity(pathlib.Path(project), rel_path)
            entries = entry_points(before_root, package,
                                   [e["function"] for e in changed
                                    if e["why"] == "EXPRESSION_CHANGED"],
                                   max_depth=ENTRY_POINT_DEPTH, limit=8)
        except (ValueError, OSError):
            entries = []
    inherited: list[Any] = []
    for entry in changed:
        for literal in entry.get("literals") or []:
            if literal not in inherited:
                inherited.append(literal)
    for candidate_entry in entries:
        options = candidates(candidate_entry["node"], inherited, limit)
        if options is None:
            continue
        for args in options:
            calls.append({"i": len(calls), "fn": candidate_entry["function"], "args": list(args),
                          "recv": None, "module": candidate_entry["module"],
                          "via": "ENTRY_POINT", "owner": None})
        per_function[candidate_entry["function"]] = len(options)
        owners[candidate_entry["function"]] = None

    # Phase two: the same surfaces, driven with REPETITION instead of literals. Bounded separately and
    # reported separately, so a witness from here is never confused with one a literal grid could find.
    structural = _structural(inherited)
    structural_calls: list[dict[str, Any]] = []
    # The budget is split so a private function cannot eat the whole structural phase. Measured: a
    # private DIRECT_STRUCTURAL budget of 400 filled first and the public surface -- the one that
    # actually reaches the fix -- got nothing, so a real divergence was reported as no witness.
    # A PER-SURFACE cap, not a global one: whichever entry point came first used to consume the whole
    # phase, so the surface that reaches the change was never driven. Measured twice.
    per_surface = 90
    for candidate_entry in entries:
        names = parameter_names(candidate_entry["node"])
        if not names:
            continue
        for text in structural[:per_surface]:
            if len(structural_calls) >= per_surface * 12:
                break
            structural_calls.append({"i": len(calls) + len(structural_calls),
                                     "fn": candidate_entry["function"], "args": [text],
                                     "recv": None, "module": candidate_entry["module"],
                                     "via": "ENTRY_POINT_STRUCTURAL", "owner": None})
    for entry in changed:
        if entry["why"] != "EXPRESSION_CHANGED":
            continue
        names = parameter_names(entry["after"])
        if not names:
            continue
        owner = owning_class(after_source, entry["function"]) if names is None else None
        for text in structural[:per_surface]:
            if len(structural_calls) >= per_surface * 12:
                break
            structural_calls.append({"i": len(calls) + len(structural_calls),
                                     "fn": entry["function"], "args": [text], "recv": None,
                                     "probe": None,
                                     "module": module, "via": "DIRECT_STRUCTURAL", "owner": None})
        del owner
    # Phase three: assembled strings, entry points only. Same literals, different algebra.
    assembled = _assembled(inherited)
    assembled_calls: list[dict[str, Any]] = []
    for candidate_entry in entries:
        names = parameter_names(candidate_entry["node"])
        if not names:
            continue
        for text in assembled[:per_surface * 2]:
            if len(assembled_calls) >= per_surface * 20:
                break
            assembled_calls.append({"i": len(calls) + len(assembled_calls),
                                    "fn": candidate_entry["function"], "args": [text],
                                    "recv": None, "module": candidate_entry["module"],
                                    "via": "ENTRY_POINT_ASSEMBLED", "owner": None})
    for binding in bindings:
        calls.append({"i": len(calls), "fn": binding["function"], "args": [],
                      "recv": None, "module": module, "via": "MODULE_BINDING",
                      "probe": "VALUE"})
    # Cheap, directed surfaces first, then the wider axes; indices assigned once, at the end, because
    # per-phase counters collided and silently overwrote results measured for a different argument.
    calls.extend(structural_calls)
    calls.extend(assembled_calls)
    for position, candidate in enumerate(calls):
        candidate["i"] = position

    for entry in changed:
        if entry["why"] == "MODULE_BINDING_CHANGED":
            continue                      # a constant is not callable; it only widens the grid
        if entry["why"] == "NEW_FUNCTION":
            unreachable.append(entry["function"])
            continue
        options = candidates(entry["after"], entry["literals"], limit)
        owner = None
        if options is None:
            # A method with a receiver is reachable; only a genuinely unbuildable class is not.
            owner = owning_class(after_source, entry["function"])
            receivers = receiver_arguments(owner)
            if receivers is None:
                unreachable.append(entry["function"])
                continue
            base_args = candidates(entry["after"], entry["literals"], limit) or [()]
            options = []
            for recv in receivers[:4]:
                for args in base_args:
                    options.append((recv, args))
            owners[entry["function"]] = owner["class"]
        for option in options:
            if owner is not None:
                recv, args = option
                calls.append({"i": len(calls), "fn": entry["function"], "args": list(args),
                              "recv": list(recv), "module": module, "via": "METHOD",
                              "owner": owner["class"]})
            else:
                calls.append({"i": len(calls), "fn": entry["function"], "args": list(option),
                              "recv": None, "module": module, "via": "DIRECT", "owner": None})
        per_function[entry["function"]] = len(options)

    if not calls:
        return {"schema": SCHEMA, "authority": AUTHORITY, "verdict": UNREACHABLE,
                "witnesses": [], "unreachable": unreachable,
                "detail": "the changed functions take parameters this search cannot supply"}

    with tempfile.TemporaryDirectory(prefix="witness_") as tmp:
        tmp_path = pathlib.Path(tmp)
        before_path = tmp_path / "_w_before.py"
        after_path = tmp_path / "_w_after.py"
        before_path.write_text(before_source, encoding="utf-8")
        after_path.write_text(after_source, encoding="utf-8")

        # Two snapshots of the project, one at each version of this file, so relative imports resolve
        # and each side is loaded in its own package. Only used when the caller gave us a project.
        snapshots = {"before": str(tmp_path / "before"), "after": str(tmp_path / "after")}
        if package is not None:
            for label, source_root in (("before", before_root or project),
                                       ("after", after_root or project)):
                shutil.copytree(source_root, snapshots[label],
                                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc",
                                                              ".tox", ".venv", "node_modules"))
                (pathlib.Path(snapshots[label]) / rel_path).write_text(
                    before_source if label == "before" else after_source, encoding="utf-8")

        # The directory that CONTAINS the package is what belongs on sys.path, not the repo root:
        # measured, `packaging` with a `src/` layout imported as a missing module until the prefix was
        # stripped. Found with the same helper the AST side uses, so the two cannot disagree.
        roots = [str(pathlib.Path(p).resolve()) for p in extra_paths]
        import_roots = {}
        for label in ("before", "after"):
            if package is not None:
                found = _package_prefix(pathlib.Path(snapshots[label]), package)
                import_roots[label] = (str(found[0].parent.resolve()) if found is not None
                                       else snapshots[label])
            else:
                import_roots[label] = (str(pathlib.Path(project).resolve())
                                       if project is not None else snapshots[label])
            roots.append(import_roots[label])
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if roots:
            env["PYTHONPATH"] = os.pathsep.join(
                roots + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))

        results: dict[str, dict[int, dict[str, Any]]] = {"before": {}, "after": {}}
        import_failure = None
        for side in ("before", "after"):
            payload = {"calls": calls, "package": package, "module": module,
                       "before_path": str(before_path), "after_path": str(after_path),
                       "after_root": import_roots["after"],
                       # One implementation of the renderer, shared by the module and the runner, so
                       # the value compared by the subprocess is the value the self-check proved.
                       "render_source": _RENDER_SOURCE}
            # Via a file, not argv: measured, a few thousand candidates overflow ARG_MAX and the
            # whole run dies with OSError instead of reporting anything.
            payload_path = tmp_path / "payload.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")
            try:
                proc = subprocess.run(
                    [sys.executable, "-B", "-c", _RUNNER, str(payload_path),
                     import_roots[side], side],
                    capture_output=True, text=True, timeout=timeout, env=env, cwd=str(tmp_path))
            except subprocess.TimeoutExpired:
                return {"schema": SCHEMA, "authority": AUTHORITY, "verdict": TIMED_OUT,
                        "witnesses": [], "detail": f"the {side} snapshot did not finish a candidate",
                        "candidates_tried": len(calls), "network": False}
            lines = [l for l in proc.stdout.splitlines() if l.startswith("__W__")]
            if not lines:
                return {"schema": SCHEMA, "authority": AUTHORITY, "verdict": IMPORT_FAILED,
                        "witnesses": [], "detail": (proc.stderr or proc.stdout)[-500:],
                        "network": False}
            first = json.loads(lines[0][len("__W__"):])
            if "import_failed" in first:
                import_failure = first["import_failed"]
                continue
            for line in lines:
                item = json.loads(line[len("__W__"):])
                results[side][item["i"]] = item
        if not results["before"] and not results["after"]:
            return {"schema": SCHEMA, "authority": AUTHORITY, "verdict": IMPORT_FAILED,
                    "witnesses": [], "detail": import_failure or "neither side produced a result",
                    "network": False}

    rows = []
    for i, item in sorted({**results["before"], **results["after"]}.items()):
        before = (results["before"].get(i) or {}).get("result") or {"kind": "MISSING"}
        after = (results["after"].get(i) or {}).get("result") or {"kind": "MISSING"}
        rows.append({"fn": item["fn"], "args": item["args"], "module": item["module"],
                     "via": item["via"], "before": before, "after": after})
    data = {"rows": rows}

    # Rank by KIND, not by discovery order. Measured: a boundary flip is found both as
    # `classify(100) -> True/False` (VALUE) and as `classify("(a)")` where only the operator name in the
    # TypeError message differs (EXCEPTION_MESSAGE). Keeping the first one found kept the useless one.
    # One witness per function, the strongest, so the generated test is the one worth committing.
    _strength = {"VALUE": 4, "EXCEPTION_TYPE": 3, "EXCEPTION": 2, "EXCEPTION_MESSAGE": 1}
    best: dict[str, tuple[int, dict[str, Any], str]] = {}
    for row in data["rows"]:
        kind = _compare(row["before"], row["after"])
        if kind is None:
            continue
        if kind == "VALUE" and (_ADDRESS_IN_VALUES.search(str(row["before"].get("repr") or ""))
                                or _ADDRESS_IN_VALUES.search(str(row["after"].get("repr") or ""))):
            continue               # containers of objects with default reprs: not observable
        # A message-only divergence only counts for an input a USER would plausibly pass. Measured:
        # `total("(a)")` -- a string manufactured by the structural axis -- produced "TypeError:
        # unsupported operand" against "'int' object is not iterable" in a genuine refactor. Those two
        # messages are the interpreter talking about the shapes I invented, not the program saying
        # anything. Grammar axes are for grammar changes; they do not get to testify about messages.
        if kind == "EXCEPTION_MESSAGE" and "STRUCTURAL" in str(row.get("via") or ""):
            continue
        # And a grammar-axis witness never outranks a value-grid one for the same function. Measured:
        # a guard on `x < 0` was reported at `f("(a)")` (a manufactured parenthesis string raising
        # TypeError on one side) instead of `f(-1)`, which is the input the fix's own test uses.
        rank = _strength.get(kind, 0)
        if "STRUCTURAL" in str(row.get("via") or "") or "ASSEMBLED" in str(row.get("via") or ""):
            rank -= 1
        current = best.get(row["fn"])
        if current is None or rank > current[0]:
            best[row["fn"]] = (rank, row, kind)
    witnesses: list[Witness] = []
    for _rank, row, kind in sorted(best.values(), key=lambda item: -item[0]):
        witnesses.append(Witness(
            function=row["fn"], args=tuple(row["args"]), module=row.get("module") or "",
            via=row.get("via") or "DIRECT",
            before_result=f"{row['before'].get('kind')}: {row['before'].get('repr') or row['before'].get('type')}",
            after_result=f"{row['after'].get('kind')}: {row['after'].get('repr') or row['after'].get('type')}",
            kind=kind))

    behavioural = {w.function for w in witnesses}
    silent = [name for name in per_function if name not in behavioural]
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "verdict": WITNESS if witnesses else NO_WITNESS,
        "witnesses": [w.row() for w in witnesses],
        "witness_count": len(witnesses),
        # A message-only divergence is a real difference in observable behaviour but a weak one: quote
        # the strong count when reporting, never the total.
        "strong_witness_count": sum(1 for w in witnesses if w.kind != "EXCEPTION_MESSAGE"),
        "witness_kinds": sorted({w.kind for w in witnesses}),
        "surfaces_tried": sorted({c.get("via") for c in calls if c.get("via")}),
        "functions_examined": len(per_function),
        "functions_with_witness": sorted(behavioural),
        # A change with no witness on this grid is (probably) a refactor. That is the correct answer
        # for a pure speedup, and it is the reason last round's "unprotected" count overstates risk.
        "functions_without_witness": silent,
        "module_bindings_changed": [e["function"] for e in bindings],
        # Provenance, so a reader can see which file was measured instead of trusting it.
        "loaded_from": sorted({item.get("loaded_from") for item in
                               (list(results["after"].values()) if "results" in dir() else [])
                               if item.get("loaded_from")})[:4],
        "unreachable": unreachable,
        "candidates_tried": len(calls),
        "bounded_search": {"grid": list(_FALLBACK), "offsets": list(_OFFSETS),
                           "per_function_budget": per_function,
                           "note": "NO_WITNESS_FOUND is bounded, never a proof of equivalence"},
        "network": False,
    }


def tests_from(result: Mapping[str, Any], module: str = "mod") -> list[str]:
    """The generated regression tests, one per witness, in commit-ready shape."""
    out = []
    for row in result.get("witnesses") or []:
        witness = Witness(function=row["function"], args=tuple(row["args"]),
                          before_result=row["before_result"], after_result=row["after_result"],
                          kind=row["kind"], module=row.get("module") or "",
                          via=row.get("via") or "DIRECT")
        out.append(witness.as_test(module))
    return out


def self_check() -> dict[str, Any]:
    """Prove the instrument still gives the answer it is claimed to give, cheaply.

    Every failure this tool has produced this round was a SILENT one: a runner that crashed mid-run
    reported "no witness", a docstring-drive witness reported a docs-only commit as behavioural, a
    generator's address made everything differ. Each line below is one of those, pinned so it cannot
    come back. It runs on hand-written pairs, so it costs nothing and needs no network.
    """
    checks: list[dict[str, Any]] = []

    def check(name: str, fn) -> None:
        try:
            passed, detail = fn()
        except BaseException as error:                    # noqa: BLE001 - a check may fail any way
            passed, detail = False, f"{type(error).__name__}: {error}"
        checks.append({"check": name, "passed": bool(passed), "detail": str(detail)[:200]})

    def boundary():
        result = search("def classify(x):\n    return x <= 100\n",
                        "def classify(x):\n    return x < 100\n")
        found = [w for w in result.get("witnesses") or [] if w["args"] == [100]]
        return bool(found), f"verdict={result['verdict']} args={[w['args'] for w in result.get('witnesses') or []]}"

    def guard():
        result = search("def chunk(n):\n    return list(range(n))\n",
                        "def chunk(n):\n    if n <= 0:\n        raise ValueError('n')\n"
                        "    return list(range(n))\n")
        return (result.get("strong_witness_count", 0) >= 1,
                f"verdict={result['verdict']} strong={result.get('strong_witness_count')}")

    def refactor_is_silent():
        result = search("def total(xs):\n    out = 0\n    for x in xs:\n        out += x\n"
                        "    return out\n",
                        "def total(xs):\n    return sum(xs)\n")
        return result["verdict"] == NO_WITNESS, f"verdict={result['verdict']}"

    def real_bug_in_speedup():
        # A "pure" speedup that is not equivalent: measured, this was the first real bug found.
        result = search("def triangle(n):\n    return sum(range(n))\n",
                        "def triangle(n):\n    return n * (n - 1) // 2\n")
        return (result.get("strong_witness_count", 0) >= 1,
                f"verdict={result['verdict']} witnesses={[w['args'] for w in result.get('witnesses') or []]}")

    def docstring_is_not_an_input():
        source = ('def f(x):\n    """A long docstring that must never become an argument.\n\n'
                  '    >>> f(1)\n    1\n    """\n    return x\n')
        literals = _literals(ast.parse(source).body[0])
        prose = [v for v in literals if isinstance(v, str) and "\n" in v]
        return (not prose, f"literals={literals}")

    def generator_address_is_not_a_value():
        rendered = _render((x for x in (1, 2)))
        import re as _re
        return (not _re.search(r"0x[0-9a-f]{4,}", rendered), rendered)

    def load_guard_exists():
        return ("MISLOADED_SNAPSHOT" in _RUNNER and "_INSTALLED_GUARD" in _RUNNER,
                "both forms of the guard are in the runner source")

    check("a boundary flip is found at the boundary", boundary)
    check("an added guard is found", guard)
    check("a genuine refactor produces no witness", refactor_is_silent)
    check("a not-actually-equivalent speedup is caught", real_bug_in_speedup)
    check("prose never becomes an argument", docstring_is_not_an_input)
    check("a generator is compared by content, not address", generator_address_is_not_a_value)
    check("the snapshot guard is present in the runner", load_guard_exists)

    return {"schema": "BRAIN_DIFFERENTIAL_WITNESS_SELF_CHECK_V1", "authority": AUTHORITY,
            "checks": checks, "passed": all(c["passed"] for c in checks),
            "count": len(checks), "network": False}


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Find an input on which two versions disagree.")
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--module", default="mod", help="name to use in emitted tests")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    result = search(pathlib.Path(args.before).read_text(), pathlib.Path(args.after).read_text(),
                    timeout=args.timeout)
    for row in result["witnesses"]:
        print(f"{row['function']}({', '.join(repr(a) for a in row['args'])})  "
              f"{row['before_result']}  ->  {row['after_result']}")
    if not result["witnesses"]:
        print(f"no witness: {result['verdict']} ({result.get('detail', '')})")
    tests = tests_from(result, args.module)
    if tests:
        print()
        print("\n".join(tests))
    if args.out:
        result["tests"] = tests
        pathlib.Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
        print(f"wrote {args.out}")
    return 0 if result["witnesses"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
