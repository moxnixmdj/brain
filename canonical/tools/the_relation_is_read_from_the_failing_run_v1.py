#!/usr/bin/env python3
"""Read the demanded RELATION out of the failing run, then edit the site that decides it.

WHY THIS EXISTS
---------------
The tree's own audit (`A_SITE_IS_NOT_A_PRODUCTION_20261124_V1.md`) named the ceiling:
a demand could only be said as *a value at one site*, but the corpus's real one-line
fixes are **relations** -- presence vs truth, grouping vs product, copy vs alias,
direction of a chain, union, polarity. A value-at-a-site instrument verifies 1 of 30.
Two later rounds added hand-written relations and measured their worth honestly:

    x is not None at run-selected guards   2 of 75 verified

This module asks the next question as a MEASUREMENT, not a belief:

    a relation is a fact about the execution -- which branch ran, which object was
    read, which side of a comparison the demanded value came from. So bind the
    running program to a trace of the demanded value and read the relation off what
    the run that FAILED actually produced.

Nothing is enumerated and nothing is learned into parameters. A hypothesis is only
proposed when the trace licenses it; the judge is the project's own suite; and a row
that yields nothing names the fact that was missing.

THE PIPELINE, PER ROW (child processes: the instrument must not disturb the parent)
----------------------------------------------------------------------------------
  1. worktree at the parent, the commit's own test file copied in, run the file
     -> the failing nodes (the demand) and the passes that must not regress;
  2. ONE failing node run in-process with a line tracer over the project's modules
     and a probe at every boolean / collection position, recording the LIVE value
     (type, truth, None-ness, len, hashability, elements) and, when the node fails,
     pytest's own two sides of the comparison and the exception message;
  3. the demanded value is read off the failure itself;
  4. a relation is licensed only where the trace says so: a falsey-but-not-None value
     at a test licenses PRESENCE/NEGATION; an exception naming an unhashable type
     licenses MATERIALISE at the iterable/production; a demanded collection whose
     elements appear at BOTH sides of a union licenses UNION; a demanded collection
     whose elements split across an IfExp's branches licenses EXCHANGE;
  5. the edit is compiled from the relation -- the human's line is never read here;
  6. the edit is judged by the whole test file in a fresh worktree: every failing
     node passes and every previously-passing node still passes;
  7. the receipt records the outcome, including rows where the changed line was
     never executed by the failing test (`CHANGED_LINE_NEVER_EXECUTED`) -- a fact
     about the harness, reported as such and never counted as a repair.

AUDIT MODE (falsification only, never generation): `--audit` also checks that the
human's own edit passes the same judge on the same parent. If it does not, the row
is reported `CONTROL_BROKEN` rather than counted.

Zero model calls. Zero stored parameters. Zero network calls. Deterministic.
Authority: NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "BRAIN_THE_RELATION_IS_READ_FROM_THE_FAILING_RUN_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
PROBE = "__brain_rel__"
_PATTERNS: list = [set()]
_BINDING_SPANS: list = [[]]
_LINES: list = [[]]
_UNPACKED: list = [set()]
_CHAINS: list = [{}]
MAX_VERIFICATIONS = 8

# What the STORE says to try first. Empty means the engine has no memory and searches
# its own relations in their fixed order. A store fills this with relations that were
# verified on OTHER rows, and the ablation in
# `the_store_is_the_only_thing_that_learns_v1` measures whether that changes an outcome.
# It is a module-level tuple, not a parameter threaded through ten functions, because
# the engine's search order is the only thing a store is allowed to touch.
PREFERRED_RELATIONS: tuple[str, ...] = ()


# --------------------------------------------------------------------------- #
# child: one instrumented run. Live objects in, one JSON answer out.
# --------------------------------------------------------------------------- #

CHILD = r'''
import json, os, pathlib, sys

repo = pathlib.Path(sys.argv[1]).resolve()
out_path = pathlib.Path(sys.argv[2])
node = sys.argv[3]
test_file = sys.argv[4] if len(sys.argv) > 4 else None
item_file_selector = None


class _Selector:
    def __init__(self, value):
        self.value = value


# argv: 0=script 1=repo 2=out 3=node 4=test_file 5=names 6=select 7=trace
import json as _json
_names = set(_json.loads(sys.argv[5])) if len(sys.argv) > 5 and sys.argv[5] else set()
_select = _json.loads(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] else []
_trace = (sys.argv[7] if len(sys.argv) > 7 else "1") == "1"
PROBE = "__brain_rel__"
samples = {}
executed = set()
facts = {"message": None, "assertions": [], "exception_type": None}

BUDGET = {"left": 800}

def shape(value, full=True):
    """A bounded description of a live value. O(8) in the value's size, always.

    Measured: `list(value)[:8]` MATERIALISES the whole collection before slicing --
    sampling the probe's values in a 1,755-site file took the child to 3.7 GB and
    the OOM killer ended it (rc -9), which the parent then reported as a harness
    failure. Every collection access below is capped before it is built."""
    snap = {"type": type(value).__name__, "module": getattr(type(value), "__module__", None),
            "repr": None, "is_none": value is None}
    try:
        snap["truth"] = bool(value)
    except Exception:
        snap["truth"] = None
    if not full:
        return snap
    try:
        size = len(value)
        snap["len"] = size
    except Exception:
        size = None
    try:
        snap["repr"] = repr(value)[:120]
    except Exception:
        snap["repr"] = "<unrepr>"
    try:
        hash(value)
        snap["hashable"] = True
    except Exception:
        snap["hashable"] = False
    if size is not None and size > 10_000:
        return snap
    try:
        snap["items"] = sorted(repr(item)[:80] for item in _first(value, 8))
    except Exception:
        pass
    try:
        snap["keys"] = sorted(repr(key)[:80] for key in _first(value.keys(), 8))
    except Exception:
        pass
    return snap


def _first(iterable, count):
    import itertools
    return list(itertools.islice(iter(iterable), count))


def __brain_rel__(index, thunk, label=None):
    """Evaluate the site and record what it produced. NEVER changes control flow:
    a probe that raises returns True (measured defect: it returned None, the countdown
    loop then never terminated and the child was killed -- the row read as a harness
    failure and the instrument could not tell its own bug from the project's code).

    Signature accepts a third argument because instrumentation sometimes wraps a
    `compare` site as `f(__brain_rel__(i, lambda: a), __brain_rel__(j, lambda: b))`
    from an earlier build; an arity mismatch raised `takes 2 positional arguments` in
    the PROJECT's test run and was reported as NO_RELATION for four rows. Both
    spellings are legal so an old instrumented tree can never forge a fact."""
    try:
        value = thunk()
    except BaseException:
        # RE-RAISE. A probe is an observer, and an observer that eats an exception is
        # not observing -- it is rewriting. Measured: `builder.add_init()` raises
        # `ValueError: Frozen classes can't use on_setattr.` on attrs a572c3a4; the probe
        # caught it and returned a substitute, the test PASSED under instrumentation, and
        # the row's own failure disappeared. Every earlier substitute (`return True`,
        # `return ()`) was a variant of the same lie: it made the instrument's convenience
        # into a fact about the project. There is no value a probe can invent that is
        # better than the exception the program itself decided to raise.
        raise
    bucket = samples.get(int(index))
    if bucket is None:
        # The FIRST value at every reached site is ALWAYS recorded, whatever the
        # budget: the demanded site is often the last statement before the raise, and
        # a budget spent first-come-first-served on earlier sites silently lost it
        # (measured: packaging b80e6eb0 reached 12 sites, none of them its own guard).
        # The budget only limits EXTRA samples per site.
        samples[int(index)] = [shape(value)]
        return value
    try:
        if len(bucket) < 4 and BUDGET["left"] > 0:
            bucket.append(shape(value))
            BUDGET["left"] -= 1
    except BaseException:
        pass
    return value

_CACHE = {}
_ROOT = str(repo) + os.sep

def tracer(frame, event, arg):
    if event == "line":
        code = frame.f_code
        key = id(code)
        rel = _CACHE.get(key, 0)
        if rel == 0:
            filename = code.co_filename
            rel = None
            if os.path.isabs(filename) and filename.startswith(_ROOT):
                rel = filename[len(_ROOT):].replace(os.sep, "/")
            _CACHE[key] = rel
        if rel is not None:
            executed.add((rel, frame.f_lineno))
    return tracer

# The probe is a BUILTIN, not an injected import and not a global name.
# Measured twice: an `import brain_probe_runtime` at the top of the file breaks every
# module that starts with `from __future__ ...` (SyntaxError, 0 sites reached), and a
# plain global name is shadowed by a project's own module-level loop (`countdown`)
# which then calls the probe with (index, thunk) and dies. A builtin cannot be
# shadowed by an assignment; it can only be shadowed by a local of that exact name,
# and a source-level check refuses those sites.
import builtins as _builtins
_builtins.__brain_rel__ = __brain_rel__

import pytest

class OnlyThisFile:
    """Keep only the failing file (unless explicit item ids were selected). Kept as a plugin because the terminal node id
    differs between 8.x (`tests/test_x.py::C::t`) and 9.x (`tests::test_x::C::t`);
    the argv form the tree's other instruments use is an 8.x spelling of the same
    thing."""
    def pytest_collection_modifyitems(self, items):
        if not test_file or _select:
            return
        import os
        wanted = os.path.basename(test_file)
        keep = [item for item in items
                if str(getattr(item, "fspath", "")).replace("\\", "/").endswith(test_file)
                or item.nodeid.split("::")[0].endswith(wanted)]
        # `-k` style name selection, OR the whole file. Never both: when names are
        # given, the file filter is redundant and a file whose fspath spelling differs
        # from the recorded `test` path would empty the selection entirely.
        if _names:
            chosen = [item for item in items
                      if any(item.name == name or item.name.startswith(name + "[") for name in _names)]
            if chosen:
                items[:] = chosen
            return
        if keep:
            items[:] = keep



class Capture:
    def pytest_runtest_logreport(self, report):
        try:
            if getattr(report, "when", "") == "call" and len(facts.setdefault("reports", [])) < 4000:
                facts["reports"].append([report.nodeid, report.outcome])
        except BaseException:
            pass
        if getattr(report, "when", "") == "call" and report.failed:
            longrepr = getattr(report, "longrepr", None)
            crash = getattr(longrepr, "reprcrash", None)
            if crash is not None:
                facts["message"] = str(crash.message)[:2000]
            else:
                facts["message"] = str(longrepr)[-2000:]
            try:
                facts["exception_type"] = type(longrepr.excinfo[1]).__name__ if getattr(longrepr, "excinfo", None) else None
            except Exception:
                facts["exception_type"] = None
    def pytest_assertrepr_compare(self, config, op, left, right):
        try:
            if len(facts["assertions"]) < 8:
                facts["assertions"].append({"op": op, "left": shape(left), "right": shape(right)})
        except Exception:
            pass
        return None

def run_pytest():
    """Run the failing FILE (or exactly the selected item ids) in one session.

    Measured defect: passed the JUnit-report spelling of a node (`tests::test_x::C::t`)
    to pytest's argv, which collects nothing; the session then reported zero failing
    tests and the row was scored CHANGED_LINE_NEVER_EXECUTED. A 47-case file costs
    milliseconds; a session that tests nothing costs the whole row."""
    # ONE test, not the whole file: a line tracer over a 600-case file is minutes of
    # callback overhead (measured: >300 s, and the row timed out twice before this).
    # `-k` selects the failing test by its own name so the selection does not depend
    # on the 8.x/9.x node-id spelling.
    attempts = [[], ["-p", "no:warnings"], ["-p", "no:warnings", "--override-ini=filterwarnings="]]
    # ONE session, no retry: a retried pytest.main re-registers the project's
    # plugins into a half-built config and fails on the second call with an error
    # that belongs to the retry, not to the project. A collection error is reported
    # as one by the quiet pre-check in the parent instead of being retried here.
    argv = list(_select) if _select else [test_file or node]
    try:
        # pytest 8 returns an ExitCode ENUM, not an int, when plugins are passed
        result = pytest.main(["-q", "--no-header", "-p", "no:cacheprovider", "--tb=long", *argv],
                             plugins=[OnlyThisFile(), Capture()])
        return int(getattr(result, "value", result))
    except BaseException as error:
        facts["pytest_internal_error"] = f"{type(error).__name__}: {error}"[:400]
        # A crash inside the harness is NOT a fact about the project. It is the probe
        # having changed the program, and the row must say so instead of falling through
        # to "no relation could be read". Measured: attrs 3b0378dd, where refusing one
        # tuple site shifted evaluation order and the probe read a half-built
        # `Attribute` before `.init` existed -- `AttributeError: 'Attribute' object has
        # no attribute 'init'` -- and without this the row reported NO_RELATION, i.e. it
        # blamed the project for the instrument's own edit.
        facts["the_probe_broke_the_run"] = True
        return 3

if _trace:
    sys.settrace(tracer)
try:
    code = run_pytest()
finally:
    if _trace:
        sys.settrace(None)

out_path.write_text(json.dumps({"exit": int(code), "samples": {str(k): v for k, v in samples.items()},
                                "executed": sorted(executed), "facts": facts,
                                "test_file": test_file},
                               sort_keys=True), encoding="utf-8")
'''


# --------------------------------------------------------------------------- #
# sites: where a relation can be said, read off the AST
# --------------------------------------------------------------------------- #


class Site:
    __slots__ = ("index", "line", "end_line", "col", "end_col", "text", "kind", "context", "ifexp",
                 "branches")

    def __init__(self, index: int, line: int, end_line: int, col: int, end_col: int,
                 text: str, kind: str, context: str, ifexp: Mapping[str, str] | None = None,
                 branches: Mapping[str, str] | None = None) -> None:
        self.index = index
        self.line = line
        self.end_line = end_line
        self.col = col
        self.end_col = end_col
        self.text = text
        self.kind = kind
        self.context = context
        self.ifexp = ifexp
        self.branches = branches

    def as_dict(self) -> dict[str, Any]:
        return {"index": self.index, "line": self.line, "end_line": self.end_line, "col": self.col,
                "end_col": self.end_col, "text": self.text, "kind": self.kind,
                "context": self.context, "ifexp": self.ifexp, "branches": self.branches}


def _char_col(line: str, byte_offset: int) -> int:
    return len(line.encode("utf-8")[:byte_offset].decode("utf-8", errors="ignore"))


_RAISE_LINES: list[list[int]] = [[]]


def _raise_distance(line: int) -> int:
    """How far a guard is from the nearest `raise` in the same file.

    The failing run names the exception, and a narrowed guard has to be on the path to
    the `raise` that produced it. Distance to the nearest raise is the only ranking that
    uses a fact from the file instead of the order the sites were enumerated in: ranking
    by line number let a guard at line 172 outrank attrs a572c3a4's demanded guard at
    line 2025, six lines above its own `raise ValueError(msg)`."""
    lines = _RAISE_LINES[0]
    return min((abs(line - other) for other in lines), default=10 ** 6)


def _conjuncts(text: str) -> list[str]:
    """The `and`-clauses of a condition, each ready for safe re-insertion in a guard.

    `_segment` needs the file's real lines, so a condition taken from another branch of
    the tree is rendered from its own AST node rather than from the source string; a
    clause that does not parse as an expression is dropped, never guessed at."""
    try:
        node = ast.parse(f"({text})", mode="eval").body
    except SyntaxError:
        return []
    pieces: list[str] = []

    def walk(n: ast.AST) -> None:
        if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.And):
            for value in n.values:
                walk(value)
            return
        line = getattr(n, "lineno", 0)
        # nodes parsed here carry no offsets: unparse, which is exact for a parsed AST
        try:
            segment = ast.unparse(n)
        except Exception:
            return
        if segment and not segment.startswith("lambda"):
            pieces.append(segment.strip())

    walk(node)
    return pieces


def _if_chains(tree: ast.AST) -> dict[int, list[tuple[int, str]]]:
    """For every `if`-chain, every test line in it, mapped to the chain's OTHER tests.

    A chain is one `if` and all the `elif`s hanging off its `orelse`, plus -- and this is
    the part that matters -- every `if` NESTED anywhere inside any branch of it. Measured
    on attrs a572c3a4: the guard is `if frozen is True:` nested inside
    `if a.on_setattr is not None:`, whose sibling `elif` already spells out
    `a.on_setattr is not setters.NO_OP` -- the exact conjunct the human hoisted into the
    nested guard. The predicate was in the repository the whole time; the failure is what
    says which branch needed it."""
    chains: dict[int, list[tuple[int, str]]] = {}
    lines = _LINES[0]

    def text_of(node: ast.AST) -> str:
        line = getattr(node, "lineno", 0)
        return _segment(lines, node, line, getattr(node, "end_lineno", line)) or ""

    def tests_of(root: ast.If) -> list[tuple[int, str]]:
        found: list[tuple[int, str]] = []
        current: ast.If | None = root
        while current is not None:
            found.append((current.test.lineno, text_of(current.test)))
            for nested in ast.walk(current):
                if isinstance(nested, ast.If) and nested is not current:
                    found.append((nested.test.lineno, text_of(nested.test)))
            current = (current.orelse[0] if len(current.orelse) == 1
                       and isinstance(current.orelse[0], ast.If) else None)
        return found

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        # only roots: an `elif` is visited through its root
        tests = tests_of(node)
        for lineno, _t in tests:
            others = [(l, t) for l, t in tests if l != lineno]
            if others:
                chains.setdefault(lineno, others)
    return chains


def _unpacked_ids(tree: ast.AST) -> set[int]:
    """Ids of expressions that are UNPACKED by their context.

    `for a, b in EXPR`, `a, b = EXPR`, `with EXPR as (a, b)`: a probe on EXPR must yield
    an iterable of the right shape. A probe that has to substitute a value cannot promise
    that, so these are refused as sites rather than instrumented with a guess."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        targets: list = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            # `for name, value in EXPR` -- the ITERABLE is the expression a probe must
            # not substitute, and the earlier form put it in `targets` where a Tuple
            # check could never match it (a For's iterable is not a tuple literal), so
            # it was never refused. Measured: attrs 3b0378dd line 2553, an `iterable`
            # site whose substitution broke a pickle path.
            ids.add(id(node.iter))
            targets = []
        elif isinstance(node, ast.comprehension):
            ids.add(id(node.iter))
            targets = []
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            targets = [item.context_expr for item in node.items]
        for target in targets:
            if isinstance(target, (ast.Tuple, ast.List)):
                for element in target.elts:
                    ids.add(id(element))
                # the EXPRESSION being unpacked is itself unsafe: a probe replacing it
                # must return a matching tuple, and `eq, eq_key = call(...)` is exactly
                # the shape that produced `TypeError: cannot unpack non-iterable bool
                # object` inside attrs' own import (measured: a572c3a4, line 1285)
                for container in targets:
                    if isinstance(container, (ast.Tuple, ast.List)):
                        continue
                    ids.add(id(container))
    return ids


def _segment(lines: list[str], node: ast.AST, line: int, end_line: int) -> str | None:
    """`ast.get_source_segment`, without re-splitting the file on every call.

    `get_source_segment` calls `_splitlines_no_ff` per invocation; on a 3,000-line file
    with 1,600 sites that alone was 40 s of the 79 s spent enumerating sites."""
    try:
        if line == end_line:
            return lines[line - 1][node.col_offset:node.end_col_offset]
        first = lines[line - 1][node.col_offset:]
        middle = lines[line:end_line - 1]
        last = lines[end_line - 1][:node.end_col_offset]
        return "\n".join([first, *middle, last])
    except Exception:
        return ast.get_source_segment("\n".join(lines), node)


def _probe_binding_spans(tree: ast.AST) -> list[tuple[int, int]]:
    """The line spans of the scopes that bind the probe's own name, computed ONCE.

    A site inside such a scope sees that binding, not the builtin (measured:
    more-itertools' `countdown`). The earlier form walked the whole tree for EVERY
    site and then walked each candidate scope again: 13 million `ast.walk` calls and
    38 s on one file, which is a violation of the speed law, not a detail."""
    spans: list[tuple[int, int]] = []
    for scope in ast.walk(tree):
        if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        # a scope's own args and its own name-bindings, WITHOUT re-walking nested
        # scopes: nested bindings cannot shadow anything in THIS scope
        binds = any(getattr(arg, "arg", None) == PROBE for arg in
                    list(getattr(scope, "args", None).args if getattr(scope, "args", None) else [])
                    + list(getattr(getattr(scope, "args", None), "posonlyargs", []) or [])
                    + list(getattr(getattr(scope, "args", None), "kwonlyargs", []) or []))
        if not binds:
            binds = any(isinstance(inner, ast.Name) and inner.id == PROBE
                        and isinstance(getattr(inner, "ctx", None), (ast.Store, ast.Del))
                        for inner in ast.walk(scope))
        if binds:
            spans.append((scope.lineno, getattr(scope, "end_lineno", scope.lineno)))
    return spans


def _shadows_probe(spans: list[tuple[int, int]], node: ast.AST) -> bool:
    line = getattr(node, "lineno", 0)
    return any(lo <= line <= hi for lo, hi in spans)


def _lambda_safe(node: ast.AST) -> bool:
    """Can this span stand inside `lambda:` at all? Asked of the SPAN, because the
    only authority is the parser, and answered identically here and in instrument()."""
    try:
        ast.parse("(lambda: " + ast.unparse(node) + ")")
        return True
    except SyntaxError:
        return False


def _unwrappable(tree: ast.AST) -> set[int]:
    """Ids of expressions a lambda may NOT wrap.

    Measured defect that forced this: `f(*args)` / `f(**kw)` wrapped as
    `f(*(lambda: args))` does not parse, the instrumented file died at import, and
    the row read as CHANGED_LINE_NEVER_EXECUTED -- a harness error wearing a fact's
    name. The first version of this rule also marked every ANCESTOR of such a node
    unsafe, which through a module docstring's JoinedStr marked the whole module and
    silently removed all 108 probes of the row. Exact structural checks only."""
    unsafe: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.expr) and isinstance(getattr(node, "ctx", None), (ast.Store, ast.Del)):
            unsafe.add(id(node))
        if isinstance(node, ast.Starred):
            unsafe.add(id(node))
        if isinstance(node, ast.keyword) and node.arg is None:
            unsafe.add(id(node.value))
        if isinstance(node, ast.JoinedStr):
            unsafe.add(id(node))
        if isinstance(node, (ast.Yield, ast.YieldFrom, ast.Await)):
            unsafe.add(id(node))
        if isinstance(node, ast.Call):
            for child in list(node.args) + [keyword.value for keyword in node.keywords]:
                if isinstance(child, (ast.Yield, ast.YieldFrom, ast.Await)):
                    unsafe.add(id(node))
            # A call that ALREADY contains the probe name is a tree that was left
            # instrumented (a killed run before the `finally` restore): wrapping it
            # again nests probes, and a stale two-argument spelling then dies with
            # `__brain_rel__() takes 2 positional arguments but 3 were given` inside
            # the PROJECT's test, which was reported as a fact about the project.
            for node_inside in ast.walk(node):
                if isinstance(node_inside, ast.Name) and node_inside.id == PROBE:
                    unsafe.add(id(node))
                    break
        # A walrus BINDS a name for the rest of the scope. Wrapping `value := d.get(k)`
        # in a lambda executes the assignment inside the lambda's local scope, so the
        # name is never bound in the function that reads it: the suite dies with
        # `NameError: name 'value' is not defined` before it can reach the human line
        # (measured: packaging b80e6eb0 line 106, which masked its real failing guard
        # at line 839 on every run).
        if isinstance(node, ast.NamedExpr):
            unsafe.add(id(node))
        # A site inside a TYPE ANNOTATION is not a value: `t.Dict[str, t.Any]` is a
        # subscript evaluated by typing's metaclass, and wrapping one argument in a
        # probe passes ONE argument where `Dict` requires two -- the module then dies
        # at IMPORT with `TypeError: Too few arguments for typing.Dict`, before any
        # test runs. Every row whose file annotates with `t.Dict[...]`/`Optional[...]`
        # read `NO_RELATION` while the trace showed only `TYPE_CHECKING` (measured:
        # click 3f91d215, jinja 2eb4542c/d05bd385, 5 of the first 15 rows).
        if isinstance(node, ast.arg):
            for annotated in ast.walk(node.annotation) if node.annotation else []:
                unsafe.add(id(annotated))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.AnnAssign)):
            if getattr(node, "returns", None) is not None:
                for annotated in ast.walk(node.returns):
                    unsafe.add(id(annotated))
            if isinstance(node, ast.AnnAssign) and node.annotation is not None:
                for annotated in ast.walk(node.annotation):
                    unsafe.add(id(annotated))
        if isinstance(node, ast.Subscript):
            # a subscript whose context is Load and whose value is a typing-like
            # module attribute is a type expression; the enclosing annotation walk
            # above already marks it, this catches bare `X[Y]` aliases at module level
            pass
    return unsafe


BACKSLASH = chr(92)
_REGEX_CALLS = {"compile", "match", "fullmatch", "search", "findall", "finditer", "sub", "subn", "split"}


class _NoLinkedPattern(Exception):
    """Raised inside the ANCHOR branch to abandon that branch ONLY.

    It exists because the alternative -- `return out` -- silently disabled every relation
    that came after it for an entire site kind."""


_ONE_SHOT = frozenset({"zip", "map", "filter", "enumerate", "reversed", "iter"})


def _one_shot_iterator_argument(node: ast.AST) -> bool:
    """Is this expression a one-shot iterator built here and handed straight to a call?

    `zip(a, b)` evaluated once is exhausted. A probe evaluates it in order to sample it,
    so the caller gets the empty remainder. Any such span is refused: there is no way to
    observe a one-shot value without spending it, and spending it is not observing."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _ONE_SHOT:
        return True
    # ANYWHERE inside the span: `self._setattrs(zip(...))` consumes the zip just as
    # surely as `zip(...)` alone, and refusing only the inner node left the outer call
    # doing the damage.
    for inner in ast.walk(node):
        if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                and inner.func.id in _ONE_SHOT):
            return True
    return False


def _calls_bare_super(node: ast.AST) -> bool:
    """Does this span use a zero-argument `super()` anywhere inside it?

    Zero-argument `super()` is compiled against an implicit `__class__` cell taken from
    the enclosing FUNCTION. Put the same expression inside a lambda and the cell is not
    there, so the call raises `RuntimeError: super(): no arguments` -- an error the
    probe invented and the project never had.

    Refusing only a bare `super()` site was not enough: `super().__init__(message)` is a
    `call` site, and instrumenting it produced that RuntimeError as the row's failing
    message (measured: packaging 553582d9). Any span that CALLS a bare super() must be
    refused, at any depth."""
    for inner in ast.walk(node):
        if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                and inner.func.id == "super" and not inner.args):
            return True
    return False


def _end_anchor_edit(text: str) -> str | None:
    """`re.compile(r"$")` -> `re.compile(r"\\Z")`, splicing INSIDE the literal.

    The edit must land on the pattern's own characters. Rewriting the last character of
    the whole expression removed the closing paren instead of the `$` and produced
    `re.compile(r"$"\\Z,` -- a syntax error reported as a failed hypothesis, which hides
    a working relation behind a broken splice."""
    match = re.search(r"""(r)(["'])(.*?)\2""", text)
    if not match:
        return None
    body = match.group(3)
    if not body.endswith("$") or body.endswith(chr(92) + "$"):
        return None
    replacement = text[:match.start(3)] + body[:-1] + chr(92) + "Z" + text[match.end(3):]
    return replacement


def _regex_literal_from_text(text: str) -> str | None:
    """The pattern body of a regex CALL's source text, with its escapes decoded."""
    for candidate in re.findall(r'r"([^"]*)"|r\'([^\']*)\'', text):
        body = candidate[0] or candidate[1]
        if body:
            return body.replace(chr(92) * 2, chr(92))
    return None


def _regex_literal(node: ast.AST) -> ast.Constant | None:
    """The pattern literal of a regex call, when the pattern is a literal.

    A regex is a VALUE the run evaluates and the pattern's own text is what a human
    edits (`$` -> `\\Z`). The site is the CALL, not the literal, so the sample is the
    MATCH RESULT: whether the pattern accepted the string the demand names."""
    if not isinstance(node, ast.Call) or not node.args:
        return None
    callee = node.func
    if isinstance(callee, ast.Attribute):
        name = callee.attr
    elif isinstance(callee, ast.Name):
        name = callee.id
    else:
        return None
    if name not in _REGEX_CALLS:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first
    return None


def _safe_literal(text):
    try:
        return ast.literal_eval(text)
    except Exception:
        return None


def linked_patterns(source: str) -> dict[int, set[str]]:
    """For every `re.compile` site, the set of names the compiled pattern is bound to.

    Keyed by the SITE, not by a line: a multi-line `re.compile(r"...", flag)` starts on
    line 37 while its `Assign` node reports 38, so a line-keyed map silently attaches
    the wrong name (measured: packaging 258202ed, where `_validate_regex` was recorded
    against a different pattern). The `regex_argument` site names the receiver it was
    dotted-called on, and only an agreeing name makes THIS `$` the `$` the denied string
    went through."""
    tree = ast.parse(source)
    sites = sites_in(source)
    by_call_line: dict[int, int] = {}
    for site in sites:
        if site.kind == "regex":
            by_call_line[site.line] = site.line
            by_call_line[site.end_line] = site.line
    names: dict[int, set[str]] = {site.line: set() for site in sites if site.kind == "regex"}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and _regex_literal(node.value) is not None):
            continue
        literal = _regex_literal(node.value)
        # the site spans from the assignment's first line to the literal's last line, so
        # a multi-line `re.compile(` is keyed by ITS OWN START, not the literal's line
        index = by_call_line.get(getattr(literal, "end_lineno", -1))
        if index is None:
            index = by_call_line.get(node.lineno)
        for target in node.targets:
            if isinstance(target, ast.Name):
                names[index].add(target.id)
    return names


_FLAG_NAMES = {"IGNORECASE": 2, "I": 2, "MULTILINE": 8, "M": 8, "DOTALL": 16, "S": 16,
               "VERBOSE": 64, "X": 64, "ASCII": 256, "A": 256}


def _regex_flags(text: str) -> int:
    """The pattern's OWN compile flags, read from the call's own arguments.

    Measured: reading a case-sensitive pattern against a lowercase denied string said
    "does not match" for both anchors, while the program's `re.IGNORECASE` made it
    match -- the relation was decided on a question the program never asked. Flags that
    are not a literal `re.X` name contribute nothing rather than a guess."""
    flags = 0
    tail = text.split(",", 1)
    if len(tail) == 1:
        return 0
    for name in re.findall(r"re\.([A-Za-z_]+)", tail[1]):
        flags |= _FLAG_NAMES.get(name.upper(), 0)
    return flags


def _pattern_names(tree: ast.AST) -> set[str]:
    """Names bound to a compiled pattern literal, computed ONCE per file.

    `_regex_receiver_source` walked the whole tree for every call node, which made site
    enumeration quadratic: 17 s on attrs' 3,000-line `_make.py`, and the sweep spent
    minutes per row before any test ran. One pass, then a set lookup."""
    bound: set[str] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and _regex_literal(node.value) is not None):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bound.add(target.id)
    return bound


def _structural_call(node: ast.Call, patterns: set[str]) -> bool:
    """True when this call is already owned by a structural site kind."""
    if _regex_literal(node) is not None:
        return True
    if not isinstance(node.func, ast.Attribute):
        return False
    receiver = node.func.value
    if isinstance(receiver, ast.Call) and _format_template(receiver) is not None:
        return True
    if isinstance(receiver, ast.Constant) and isinstance(receiver.value, str) and "{" in receiver.value:
        return True
    if node.func.attr in _REGEX_CALLS and len(node.args) == 1:
        if isinstance(receiver, ast.Name) and receiver.id in patterns:
            return True
        if isinstance(receiver, ast.Call) and _regex_literal(receiver) is not None:
            return True
    return False


def _regex_receiver_source(tree: ast.AST, node: ast.Call) -> bool:
    """True when the receiver of `<receiver>.<method>(...)` IS a compiled pattern.

    The receiver is usually a module-level NAME (`_wheel_name_regex = re.compile(...)`)
    rather than an inline literal, so a literal-only test finds no caller at all and
    the ANCHOR relation has no string to be decided on (measured: packaging 8af75907,
    where `_wheel_name_regex.match(name_part)` is the only use of the pattern)."""
    receiver = node.func.value
    if isinstance(receiver, ast.Call) and _regex_literal(receiver) is not None:
        return True
    if isinstance(receiver, ast.Name):
        for assigned in ast.walk(tree):
            if (isinstance(assigned, (ast.Assign, ast.AnnAssign))
                    and isinstance(getattr(assigned, "value", None), ast.Call)
                    and _regex_literal(assigned.value) is not None):
                targets = assigned.targets if isinstance(assigned, ast.Assign) else [assigned.target]
                if any(isinstance(t, ast.Name) and t.id == receiver.id for t in targets):
                    return True
    return False


def _format_template(receiver: ast.AST) -> ast.Constant | None:
    """The string literal a `.format(...)` call actually formats.

    The literal is often wrapped in the project's own gettext call -- `_("...{x}...")
    .format(x=...)` -- so a bare-Constant test finds nothing and a QUOTING row reads
    NO_RELATION while its template is right there (measured: click 3f91d215, where
    every one of 14 format calls was wrapped in `_()`). One level of a single-string
    call is unwrapped; anything else is not a template."""
    if isinstance(receiver, ast.Constant) and isinstance(receiver.value, str):
        return receiver if "{" in receiver.value else None
    if isinstance(receiver, ast.Call) and len(receiver.args) == 1 and not receiver.keywords:
        inner = receiver.args[0]
        if isinstance(inner, ast.Constant) and isinstance(inner.value, str) and "{" in inner.value:
            return inner
    return None


def sites_in(source: str) -> list[Site]:
    """Every expression whose VALUE decides which way the program goes, plus the
    collection positions where a demand can be answered by a different construction.
    Read from the AST; the human's diff is never consulted."""
    tree = ast.parse(source)
    body = source.splitlines()
    unsafe = _unwrappable(tree)
    _PATTERNS[0] = _pattern_names(tree)
    _BINDING_SPANS[0] = _probe_binding_spans(tree)
    _LINES[0] = source.splitlines()
    _UNPACKED[0] = _unpacked_ids(tree)
    _LINES[0] = source.splitlines()
    _CHAINS[0] = _if_chains(tree)
    _RAISE_LINES[0] = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Raise)]
    found: list[Site] = []
    # A `str.format` template is a value the run PRODUCES (the rendered message), and
    # its edit rewrites the template's own text (`{x}` -> `{x!r}`), which no
    # expression-level relation can express. Sampling the bare Constant would record
    # the UNRENDERED template, so the site is the enclosing `template.format(...)`
    # CALL: its sample is the produced message, and its edit is applied to the inner
    # template. Only calls whose receiver is a string literal carrying a field qualify.
    format_calls: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "format":
            template = _format_template(node.func.value)
            if template is not None:
                format_calls[id(node)] = template

    def add(node: ast.AST, kind: str, context: str, ifexp: Mapping[str, str] | None = None,
            branches: Mapping[str, str] | None = None) -> None:
        line = getattr(node, "lineno", None)
        if line is None or id(node) in unsafe or not _lambda_safe(node):
            return
        if id(node) in _UNPACKED[0]:
            return
        # `a, b` cannot stand inside `lambda:` -- `lambda: a, b` is a TUPLE whose first
        # element is the lambda, so the probe returns `a` alone and a function that
        # returned `value, key` returns a bare bool. That forged
        # `TypeError: cannot unpack non-iterable bool object` inside attrs' own import
        # (measured: a572c3a4, `return value, key`).
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return
        # Zero-argument `super()` is compiled with an implicit `__class__` cell taken from
        # the enclosing FUNCTION's frame. Inside a lambda the cell is not there, and the
        # call raises `RuntimeError: super(): no arguments` -- an error the probe created
        # and the project would never have raised (measured: click d340b0c1, whose row then
        # carried the probe's own exception as the project's failing message).
        if _calls_bare_super(node):
            return
        if _one_shot_iterator_argument(node):
            # `self._setattrs(zip(self.__slots__, state))`: the probe would sample the
            # zip, and sampling CONSUMES it, so the real call receives an exhausted
            # iterator. The failure that follows is the probe's, not the project's --
            # measured on attrs 3b0378dd, where `AttributeError: 'Attribute' object has
            # no attribute 'init'` was the end of a pickle path that read nothing.
            # An expression that BUILDS a one-shot iterator and feeds it straight into a
            # call cannot be observed without changing it, so it is not a site.
            return
        # a walrus ANYWHERE inside the expression is equally fatal (the site is the
        # Compare `(value := ...) is None`, not the NamedExpr itself)
        if any(isinstance(child, ast.NamedExpr) for child in ast.walk(node)):
            return
        if _shadows_probe(_BINDING_SPANS[0], node):
            return
        end_line = getattr(node, "end_lineno", line)
        text = _segment(_LINES[0], node, line, end_line)
        if text is None or not text.strip() or PROBE in text:
            return
        start, end = node.col_offset, getattr(node, "end_col_offset", node.col_offset)
        if end_line == line:
            start = _char_col(body[line - 1], start)
            end = _char_col(body[line - 1], end)
        found.append(Site(len(found), line, end_line, start, end, text, kind, context, ifexp, branches))

    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While)):
            spans = {}
            try:
                body_last = node.body[-1] if node.body else None
                orelse_last = node.orelse[-1] if node.orelse else None
                spans = {"body": ast.get_source_segment(source, node.body[0]) if node.body else "",
                         "orelse": ast.get_source_segment(source, node.orelse[0]) if node.orelse else "",
                         "test": ast.get_source_segment(source, node.test) or "",
                         "body_from": node.body[0].lineno if node.body else None,
                         "body_to": getattr(body_last, "end_lineno", None),
                         "orelse_from": node.orelse[0].lineno if node.orelse else None,
                         "orelse_to": getattr(orelse_last, "end_lineno", None)}
            except Exception:
                spans = {}
            add(node.test, "test", type(node).__name__, None, spans)
            for operand in ast.walk(node.test):
                if isinstance(operand, ast.BoolOp):
                    for value in operand.values:
                        add(value, "operand", type(node).__name__)
        elif isinstance(node, ast.Assert):
            add(node.test, "test", "Assert")

        elif isinstance(node, ast.IfExp):
            add(node.test, "test", "IfExp")
            try:
                ifexp = {"body": ast.get_source_segment(source, node.body) or "",
                         "test": ast.get_source_segment(source, node.test) or "",
                         "orelse": ast.get_source_segment(source, node.orelse) or ""}
            except Exception:
                ifexp = None
            if ifexp:
                add(node, "ifexp", "IfExp", ifexp)
        elif isinstance(node, ast.comprehension):
            for condition in node.ifs:
                add(condition, "test", "Comprehension.if")
            add(node.iter, "iterable", "Comprehension.iter")
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            add(node.iter, "iterable", type(node).__name__)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.BitOr)):
            add(node, "combine", "BinOp")
        elif isinstance(node, (ast.Tuple, ast.List)) and len(getattr(node, "elts", [])) > 1:
            add(node, "collection", type(node).__name__)
        elif isinstance(node, ast.Return) and getattr(node, "value", None) is not None:
            value = node.value
            add(value, "production", type(node).__name__)
            if isinstance(value, ast.Call):
                for argument in list(value.args) + [k.value for k in value.keywords]:
                    add(argument, "production_argument", type(node).__name__)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and id(node) in format_calls:
            add(node, "format_string", "Call")
        elif isinstance(node, ast.Call) and _regex_literal(node) is not None:
            add(node, "regex", "Call")
        elif isinstance(node, ast.Call) and not _structural_call(node, _PATTERNS[0]):
            # A CALL's VALUE is where most real defects live: a generator handed where a
            # tuple was needed, a function returned instead of its result. No site meant
            # no sample, so the row's own line was executed 986 times and read as
            # NO_RELATION (measured: attrs 3b0378dd, whose fix is `tuple(call(...))` on
            # the very line the trace reached).
            # EXCLUDED: the structural calls already claimed above (a regex compile or a
            # template format), and the pattern-method calls. Letting the generic kind
            # also claim them changed which relation each row proposed and cost two
            # already-VERIFIED rows their ANCHOR (measured: packaging 8af75907, 258202ed).
            add(node, "call", "Call")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr in _REGEX_CALLS and len(node.args) == 1:
            # the CALLER of a pattern method (`pattern.fullmatch(name)`): its single
            # argument is the string the pattern is tested against, and the ANCHOR
            # relation is only decidable from that value. `re.compile(...)` is excluded
            # by requiring a resolved pattern receiver.
            if _regex_receiver_source(tree, node):
                receiver = node.func.value
                name = receiver.id if isinstance(receiver, ast.Name) else "(literal)"
                add(node.args[0], "regex_argument", "Call:" + name)

    return found


def instrument(source: str, sites: Sequence[Site]) -> str:
    """Wrap each single-line site's exact span in `__brain_rel__(index, lambda: ...)`.
    The wrapper returns the value, so semantics are unchanged; a probe that raises
    returns True and is dropped by the trace, never by an exception.

    A wrap the parser rejects is REMOVED: an instrument that cannot say whether it
    broke the file is an instrument that will report its own defect as a fact about
    the project. The cheap check (can this span stand inside a lambda at all?) runs
    per site; the whole-file parse is the authority, with an incremental bail-out."""
    def acceptable(site: Site) -> bool:
        try:
            ast.parse("(lambda: " + site.text + ")")
            return True
        except SyntaxError:
            return False

    def render(chosen: Iterable[Site]) -> str:
        lines = source.splitlines(keepends=True)
        for site in sorted(chosen, key=lambda s: (s.line, s.col), reverse=True):
            line = lines[site.line - 1]
            if line[site.col:site.end_col] != site.text:
                continue
            if PROBE in line:
                # the line already carries a probe: a site that shares its line with an
                # earlier site would build `f(probe(a), probe(b))` and the probe would
                # be called with the CALLEE's arguments. Measured as
                # `__brain_rel__() takes 2 positional arguments but 4 were given`
                # inside the project's own test, which then read as a fact about the
                # project (click 42ee8a1f, d340b0c1; more-itertools 62411c16).
                continue
            lines[site.line - 1] = (line[:site.col] + f"{PROBE}({site.index}, lambda: "
                                    + line[site.col:site.end_col] + ")" + line[site.end_col:])
        return "".join(lines)

    candidates = [site for site in sites if site.end_line == site.line and acceptable(site)]
    text = render(candidates)
    try:
        ast.parse(text)
        return text
    except SyntaxError:
        pass
    kept: list[Site] = []
    for site in candidates:
        trial = render([*kept, site])
        try:
            ast.parse(trial)
            kept.append(site)
        except SyntaxError:
            continue
    return render(kept)


# --------------------------------------------------------------------------- #
# the demanded value, read off the failure
# --------------------------------------------------------------------------- #

# BOTH SIDES may be literals: `200 != 192` and `[] != [[0, 1, 2]]` are the two most
# common failures in the corpus, and the earlier pattern required a leading letter, so
# it matched neither and every numeric/empty-collection demand was read as "exception
# only" (no relation could be licensed at all).
_SCALAR_PAIR = re.compile(r"(\[\]|\{\}|\(\)|set\(\)|''|\"\"|-?\d[\w.]*|"
                          r"[A-Za-z_][\w.\[\]()'\"]{0,100})\s*(?:!=|==)\s*(.{1,160})")


def demanded_values(facts: Mapping[str, Any]) -> dict[str, Any]:
    """What the failing run says the program owed. pytest's own comparison sides are
    exact live objects; the exception message is the fallback and says so."""
    wanted: dict[str, Any] = {"source": None, "expected": None, "actual": None,
                              "exception": None, "elements": []}
    messages = [a for a in facts.get("assertions") or [] if a.get("op") in ("==", "!=")]
    if messages:
        comparison = messages[0]
        left, right = comparison.get("left") or {}, comparison.get("right") or {}
        wanted["source"] = "pytest_assertrepr_compare"
        wanted["actual"], wanted["expected"] = left, right
        wanted["elements"] = (right.get("items") or left.get("items") or [])
        return wanted
    message = str(facts.get("message") or "")
    # An exception raised where the test expected a VALUE is the same demand as
    # `DID NOT RAISE` seen from the other side: the program took a path it should not
    # have taken. The demand is then about the GUARD that took it. (Measured: attrs
    # a572c3a4, where `ValueError: Frozen classes can't use on_setattr.` is what a test
    # expecting successful construction sees, and the human fix narrows the guard with
    # `and a.on_setattr is not setters.NO_OP`.)
    if message and not message.startswith("Failed: DID NOT RAISE"):
        wanted["source"] = "exception_where_value_expected"
        wanted["exception"] = message.splitlines()[0][:300]
        wanted["over_broad_guard"] = True
        match = _SCALAR_PAIR.search(message)
        if match:
            wanted["actual"] = match.group(1).strip()
            wanted["expected"] = match.group(2).strip()
        return wanted
    match = _SCALAR_PAIR.search(message)
    if match:
        wanted.update({"source": "exception_message", "actual": match.group(1).strip(),
                       "expected": match.group(2).strip()})
        # a produced EMPTY collection where the demand is a non-empty one is the
        # single most common relational fact in this corpus (`Lists differ: [] != [...]`,
        # `[] != [[0, 1, 2], ...]`): it names the value's falsiness, which PRESENCE
        # turns into `is not None` and MATERIALISE into `tuple(...)`. Read the literal
        # sides, never the message's prose.
        left, right = match.group(1).strip(), match.group(2).strip()
        if left in ("[]", "{}", "set()", "()", "''", '""') and right not in ("[]", "{}", "set()", "()"):
            wanted["produced_empty"] = True
        if right in ("[]", "{}", "set()", "()") and left not in ("[]", "{}", "set()", "()"):
            wanted["demanded_empty"] = True
        return wanted
    # a pytest.raises that did NOT raise: the demand is a PATH property, and the
    # relation that satisfies it is a stricter predicate on the guard that let the
    # value through. `raises_demand` reads the type; nothing else is inferred here.
    # The test itself names the value it expected to be REJECTED: every failing case in
    # this corpus is either a value that must not be accepted or a string that must be
    # formatted differently, and both are literals quoted in the failure. Read them as
    # literals; never as prose.
    literals = []
    for token in re.findall(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"", message):
        body = token[0] or token[1]
        try:
            literals.append(ast.literal_eval(("'" + body + "'")))
        except Exception:
            literals.append(body)
    if literals:
        wanted["literals"] = [value[:200] for value in literals if isinstance(value, str)]
    # a pytest.raises that did NOT raise: the demand is a PATH property, and the
    # relation that satisfies it is a stricter predicate on the guard that let the
    # value through. `raises_demand` reads the type; nothing else is inferred.
    if raises_demand(message):
        wanted["source"] = "did_not_raise"
        wanted["exception"] = message.splitlines()[0][:300]
        # `DID NOT RAISE` is a demand that a PATH not be taken: the program owed an
        # exception and returned a value instead. That is exactly a guard that let the
        # value through, so it licenses GUARD_NARROWING on the guard that was TRUE.
        wanted["over_broad_guard"] = True
        return wanted
    if message:
        wanted["source"] = "exception_only"
        wanted["exception"] = message.splitlines()[0][:300]
    return wanted


def _unescape_literal(text: str) -> str:
    """The string a Python literal denotes, or the text itself if it is not one."""
    try:
        return ast.literal_eval(text)
    except Exception:
        return text


def quoting_transforms(template: str, produced_repr: str, demanded: str) -> list[dict[str, str]]:
    """Every QUOTING edit the two strings license, one per candidate field.

    `produced_repr` is the repr of the string the failing run built; `demanded` is the
    token the test says must appear in it. A candidate exists when the demanded token is
    a substring of the produced value's REPR and is NOT a substring of the produced
    value: the program printed the value raw where the demand is the value's repr, so
    exactly the field carrying that value needs `!r`. WHICH field is not guessed here --
    every field is a candidate and the run's own verifier keeps the one that turns the
    failure into a pass. Measured on click 3f91d215: the tempdir is literally one
    backslash, the demand is two, and two-backslash text is only in `repr(value)`."""
    if not template or not demanded or not produced_repr:
        return []
    body = _unescape_literal(template)
    if "!r" in body:
        return []
    fields = [f for f in re.findall(r"\{([^{}]+)\}", body) if "!" not in f and ":" not in f]
    if not fields:
        return []
    try:
        produced_value = ast.literal_eval(produced_repr)
    except Exception:
        return []
    if not isinstance(produced_value, str) or demanded in produced_value:
        return []
    if demanded not in repr(produced_value):
        return []
    out = []
    for field in fields:
        if not re.fullmatch(r"[A-Za-z_]\w*", field.strip().split(".")[0].strip()):
            continue
        out.append({"name": "demanded_token_is_the_repr_of_the_value",
                    "edit": template.replace("{" + field + "}", "{" + field + "!r}", 1)})
    return out


def raises_demand(message: str) -> str | None:
    """A failure of the form `DID NOT RAISE <Type>` is a demand about a PATH: the
    program owed an exception of that type and produced a value instead. The type is
    read from the failure; nothing about it is invented."""
    text = str(message or "")
    at = text.find("DID NOT RAISE")
    if at < 0:
        return None
    tail = text[at + len("DID NOT RAISE"):]
    match = re.search(r"[A-Za-z_][\w.]*", tail)
    if match:
        name = match.group(0).split(".")[-1]
        if name not in ("class", "of", "the"):
            return name
    angle = re.search(r"<class '([\w.]+)'", text)
    return angle.group(1).split(".")[-1] if angle else None


_CONTAINS = re.compile(r"assert\s+(?P<token>.+?)\s+(?P<neg>not\s+)?in\s+(?P<actual>.+)$")


def forbidden_token(facts: Mapping[str, Any]) -> str | None:
    """The token the failing run says must NOT appear in the output.

    Two exact readings, no invention: a failed `x not in y` comparison from pytest's
    own sides, or an `assert <token> not in <actual>` statement in the message. A
    failed `x in y` says the token must appear -- a different relation, not this one."""
    for assertion in facts.get("assertions") or []:
        if assertion.get("op") != "not in":
            continue
        left = assertion.get("left") or {}
        token = left.get("repr")
        # a string's own repr is single- or double-quoted (and may be non-ASCII), so
        # the literal is read by prefix, not by a fixed quote character
        if isinstance(token, str) and len(token) >= 2 and token[0] in "\"'" and token[-1] in "\"'":
            try:
                value = ast.literal_eval(token)
            except Exception:
                value = token[1:-1]
            if isinstance(value, str):
                return value
    message = str(facts.get("message") or "")
    match = _CONTAINS.search(message)
    if match and match.group("neg"):
        try:
            value = ast.literal_eval(match.group("token").strip())
            if isinstance(value, str):
                return value
        except Exception:
            return None
    return None


def expected_elements(wanted: Mapping[str, Any]) -> set[str]:
    out: set[str] = {str(item) for item in wanted.get("elements") or []}
    for side in ("expected", "actual"):
        value = wanted.get(side)
        if not isinstance(value, dict):
            continue
        for key in ("items", "keys"):
            out |= {str(item) for item in value.get(key) or []}
    return out


# --------------------------------------------------------------------------- #
# the relations: licensed by the trace, never enumerated
# --------------------------------------------------------------------------- #


def relations_for(site: Site, samples: Sequence[Mapping[str, Any]], wanted: Mapping[str, Any],
                  exception_type: str | None, message: str, *, forbidden: str | None = None,
                  wanted_raise: str | None = None,
                  sites_inside: Sequence[tuple["Site", Sequence[Mapping[str, Any]]]] = (),
                  patterns_linked: Mapping[int, bool] | None = None
                  ) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    patterns_linked = patterns_linked or {}
    expected = expected_elements(wanted)
    _ = exception_type
    expression = site.text.strip()
    if not samples:
        # A pattern compiled at IMPORT time (a dict of rules, a module constant) can never
        # be sampled: the trace's probes run inside functions, and import has already
        # happened. Its VALUE is not in question -- a compiled literal is a literal -- so
        # END_ANCHOR is the one relation that can be read without a sample, and only when
        # the run itself said an exception failed to arrive.
        if (site.kind == "regex" and str(wanted.get("source") or "") == "did_not_raise"):
            literal_here = _regex_literal_from_text(site.text)
            repaired_here = _end_anchor_edit(expression)
            if literal_here and repaired_here:
                out.append({"relation": "END_ANCHOR", "site": site.index, "line": site.line,
                            "expression": expression, "edit": repaired_here,
                            "witness": {"demand": "the exception that did not come",
                                        "pattern": literal_here[:120],
                                        "why": "$ also matches before a trailing newline"}})
        return out
    falsey_not_none = [s for s in samples if s.get("is_none") is False and s.get("truth") is False
                       and s.get("type") != "bool"]
    none_seen = any(s.get("is_none") is True for s in samples)

    if site.kind in ("test", "operand") and falsey_not_none:
        witness = {k: falsey_not_none[0].get(k) for k in ("type", "repr", "truth", "is_none")}
        if site.context in ("If", "While", "IfExp", "Assert", "Comprehension.if"):
            out.append({"relation": "PRESENCE", "site": site.index, "line": site.line,
                        "expression": expression, "edit": f"{expression} is not None",
                        "witness": witness})
        if site.kind == "operand":
            out.append({"relation": "PRESENCE_ON_OPERAND", "site": site.index, "line": site.line,
                        "expression": expression, "edit": f"{expression} is not None",
                        "witness": witness})
        if site.kind == "test":
            out.append({"relation": "NEGATION", "site": site.index, "line": site.line,
                        "expression": expression, "edit": f"not ({expression})",
                        "witness": witness})
    if site.kind == "test" and none_seen and any(s.get("truth") for s in samples):
        out.append({"relation": "NONE_GUARD", "site": site.index, "line": site.line,
                    "expression": expression, "edit": f"{expression} is not None",
                    "witness": {"none_and_truthy_both_seen": True}})
    if site.kind == "call":
        # A call whose VALUE is an un-exhausted iterator where a SEQUENCE is required.
        # The relation is MATERIALISE and it is read from the value itself, not from the
        # source: the sample's type is a generator/iterator, and the fix is `tuple(...)`.
        # Measured on attrs 3b0378dd: `attrs = field_transformer(cls, attrs)` ran 986
        # times in the failing run and the row had no site at all on that line.
        generators = [s for s in samples
                      if s.get("type") in ("generator", "list_iterator", "map", "filter",
                                           "zip", "enumerate", "reversed", "_grouper")
                      or (isinstance(s.get("repr"), str) and "<generator object" in s["repr"])]
        if generators:
            out.append({"relation": "MATERIALISE", "site": site.index, "line": site.line,
                        "expression": expression, "edit": f"tuple({expression})",
                        "witness": {"value_type": generators[0].get("type"),
                                    "repr": str(generators[0].get("repr"))[:120]}})
    if "unhashable" in (message or ""):
        if site.kind in ("iterable", "production_argument", "production", "combine"):
            out.append({"relation": "MATERIALISE", "site": site.index, "line": site.line,
                        "expression": expression, "edit": f"tuple({expression})",
                        "witness": {"exception": message.splitlines()[0][:160] if message else ""}})
    if wanted.get("produced_empty") and falsey_not_none:
        # The run produced an EMPTY collection where the demand is a non-empty one, and
        # this site forces a boolean reading of exactly such a value. That is the same
        # PRESENCE relation the emptiness names: the guard passed an empty container
        # through a check meant to establish that it was there. Proposed only on sites
        # whose own sample IS empty -- the witnessed value, not the site's shape.
        if any(s.get("len") == 0 and s.get("truth") is False for s in falsey_not_none):
            out.append({"relation": "PRESENCE", "site": site.index, "line": site.line,
                        "expression": expression, "edit": f"{expression} is not None",
                        "witness": {"produced_empty": True,
                                    "type": falsey_not_none[0].get("type"),
                                    "len": 0}})
    if site.kind == "regex":
        try:
            # ANCHOR relation, read from the run and the code's own call site.
            #
            # A regex site's sample is the MATCH RESULT at that call. When the demand is
            # that a named string be REJECTED, the pattern must be read against the strings
            # the CALLER passed in the SAME traced run: `_wheel_name_regex.fullmatch(name)`
            # at line 244 had `name` = the newline-bearing filename, which `$` accepts and
            # `\Z` rejects. The relation is therefore: (1) the demand is a rejection,
            # (2) this pattern's own site has a `$` anchor, (3) `$` and `\Z` DISAGREE on a
            # string this program actually passed at this call, (4) on the disagreeing
            # string the current pattern ACCEPTED. Then the edit is the anchor substitution.
            # No candidate string is invented: (3) is computed from the traced argument.
            rejected = str(wanted.get("source") or "") == "did_not_raise"
            pattern_text = _regex_literal_from_text(site.text)
            if rejected and pattern_text and pattern_text.endswith("$"):
                # ONLY the `regex_argument` samples are candidate strings. The pattern
                # site's own sample is a Pattern object (or the synthetic placeholder for an
                # import-time compile) -- including it made `here` a list whose entries cannot
                # be decoded, and the branch died quietly on its own bookkeeping.
                here = [s.get("repr") for _site, values in sites_inside
                        for s in values if _site.kind == "regex_argument" and isinstance(s.get("repr"), str)]
                # The pattern must be the one the DENIED string actually went through, and
                # "went through" is not a guess: the pattern is assigned to a NAME and some
                # `NAME.method(arg)` call site recorded `arg` in this same run. Without that
                # link, several regexes in one file accept the same denied string and the
                # first one reached wins (measured: packaging 258202ed, where the human fix
                # is `_validate_regex` on line 38 and a sibling `_normalized_regex` on line
                # 41 accepts the identical string).
                # `patterns_linked` is keyed by LINE, not by the site index: the row's
                # sites are a FILTERED subset (`only_lines`), so an index-keyed map pointed
                # at a different site's pattern and the relation silently vanished on both
                # rows it had just verified.
                if not patterns_linked.get(site.line):
                    # This pattern has no call site in this run (an import-time rule in a
                    # dict), so the ANCHOR relation cannot link it to a denied string.
                    # Abandon ANCHOR only: END_ANCHOR needs no call site at all, and
                    # `return out` here silently disabled it.
                    raise _NoLinkedPattern()
                decoded = []
                for value in here:
                    try:
                        decoded.append(ast.literal_eval(value))
                    except Exception:
                        continue
                # Which pattern receiver saw the DENIED string in THIS run. The denied
                # string is the one the demand named (the failing parametrization), never
                # "any string this pattern also met": the earlier form asked whether the
                # receiver saw ANY value in the sampled set, which every receiver satisfies,
                # and the relation then fired on an unrelated sibling pattern (measured:
                # packaging 258202ed, firing on `_normalized_regex` line 41 instead of
                # `_validate_regex` line 37).
                # A `DID NOT RAISE` failure names only the exception TYPE, never the string,
                # so the denied text is often absent from the message. The link is then
                # read from the run itself: which name-dotted pattern call received a string
                # in this session. (Requiring the literal on every row was measured to turn
                # a VERIFIED row into NO_RELATION: packaging 8af75907.)
                # the exception TYPE is a literal too, and it is never the denied STRING, so
                # only literals that are not dotted names of the demanded exception count
                # The failing test names the exception TYPE in `DID NOT RAISE`, and the
                # exception's dotted path is the only literal such a message carries. It is
                # never the denied STRING, so when the only literal is the type, the denied
                # text is unknown and the link is read from the run alone; the project's
                # suite then decides between the linked patterns.
                message = str(wanted.get("exception") or "")
                type_token = message.split("<class '")[-1].split("'")[0] if "<class '" in message else ""
                denied = [text for text in (wanted.get("literals") or [])
                          if isinstance(text, str) and text and text != type_token
                          and "." not in text]
                denied_receivers = set()
                for other, values in sites_inside:
                    if other.kind != "regex_argument":
                        continue
                    seen = {_safe_literal(v["repr"]) for v in values if isinstance(v.get("repr"), str)}
                    if not denied or any(item in seen for item in denied):
                        if seen:
                            denied_receivers.add(other.context.split("Call:", 1)[-1])
                # Several patterns can legitimately be linked (a file may validate the same
                # denied string against two regexes), so the choice between them is NOT
                # guessed here: every linked pattern that accepts-and-should-not becomes a
                # hypothesis, and the project's own suite keeps the right one. Guessing from
                # the source was measured wrong (packaging 258202ed: `_validate_regex` and
                # `_normalized_regex` both accept the denied `hi\n`).

                if not (denied_receivers & patterns_linked.get(site.line, set())):
                    # NO LINKED PATTERN: the `ANCHOR` relation has nothing to stand on here,
                    # but the ROW is not finished. Returning from the whole relation function
                    # made every later relation unreachable for every `regex` site -- which is
                    # how END_ANCHOR sat as dead code while the rows that needed it failed.
                    # Only THIS branch gives up.
                    raise _NoLinkedPattern()
                flags = _regex_flags(site.text)
                for candidate in [c for c in decoded if isinstance(c, str) and c]:
                    try:
                        loose = re.search(pattern_text, candidate, flags) is not None
                        strict = re.search(pattern_text[:-1] + BACKSLASH + "Z", candidate, flags) is not None
                    except re.error:
                        continue
                    # only a pattern that ACCEPTED this string in this run is the site
                    # `loose`/`strict` are already computed with the pattern's OWN flags; the
                    # extra unflagged re-check that used to sit here rejected exactly the
                    # rows the flags made true (measured: packaging 258202ed, a
                    # `re.IGNORECASE` pattern whose candidate was lowercase)
                    if loose and not strict:
                        out.append({"relation": "ANCHOR", "site": site.index, "line": site.line,
                                    "expression": expression,
                                    "edit": site.text.replace("$", BACKSLASH + "Z"),
                                    "witness": {"accepted_by_$": candidate[:120],
                                                "rejected_by_\\Z": True,
                                                "pattern": pattern_text[:120]}})
                        break
        except _NoLinkedPattern:
            pass
    if site.kind == "test" and wanted.get("over_broad_guard"):
        # SIBLING_DISJUNCT: the demanded path must not be taken, and the SAME if-chain
        # already contains a predicate that distinguishes the caller that must take it
        # from the caller that must not. The edit MOVES that existing predicate into this
        # guard -- nothing is invented, nothing is memorised, and the search is bounded by
        # the file itself. Measured: attrs a572c3a4, where the human's edit is
        # `if frozen is True and a.on_setattr is not setters.NO_OP:`, and the conjunct is
        # spelled out verbatim in the sibling `elif` at line 2030.
        conjuncts = _CHAINS[0].get(site.line) or []
        # prefer the clause that names the same state the demand's exception names, then
        # the ones nearest the guard
        named = re.findall(r"[A-Za-z_][\w.]*", str(wanted.get("exception") or ""))
        ranked: list[tuple[int, int, str]] = []
        for other_line, other_text in conjuncts:
            if not other_text or other_text == expression:
                continue
            for piece in _conjuncts(other_text):
                if piece == expression or piece in expression:
                    continue
                hits = sum(1 for name in named if name in piece)
                ranked.append((-hits, abs(other_line - site.line), piece))
        ranked.sort()
        for _score, _distance, piece in ranked[:2]:
            out.append({"relation": "SIBLING_DISJUNCT", "site": site.index, "line": site.line,
                        "expression": expression,
                        "edit": f"{expression} and {piece}",
                        "distance_to_the_raise": _raise_distance(site.line),
                        "witness": {"conjunct": piece,
                                    "found_in": "the same if-chain's other branch",
                                    "exception": str(wanted.get("exception") or "")[:120]}})
    if site.kind in ("test", "operand") and wanted.get("over_broad_guard"):
        # GUARD_NARROWING: the demand is that a PATH not be taken, the run shows the
        # guard's value was the one that took it, and the guard's own operands carry the
        # discriminating state. The edit is the conjunction that the failure names:
        # every operand of this guard that was TRUE here and carries state NOT yet
        # distinguished. This is the corpus's largest single family (attrs a572c3a4,
        # click 1b0e19f5, click 40830087, click d340b0c1), and no relation could express
        # it because the instrument only sampled values, never a candidate conjunct.
        # The conjunct is almost never ON the guard's own line: the guard tests one
        # boolean (`frozen is True`) and the state that distinguishes the two callers
        # lives on an object the guard could have asked about. So the candidates are
        # (a) every other site truthy in this run whose text is a simple attribute or
        # name, and (b) any attribute of an object sampled in this run. Ordered by
        # proximity to the guard, because the human's conjunct nearly always names a
        # variable already in the enclosing scope.
        operand_edits = []
        for other, values in sites_inside:
            truths = [v.get("truth") for v in values]
            if not truths or not all(t is True for t in truths):
                continue
            text = other.text.strip()
            if text == expression or not re.fullmatch(r"[A-Za-z_][\w.\[\]()'\"]*", text):
                continue
            if other.kind == "test":
                continue
            if other.line != site.line:
                continue
            operand_edits.append(text)
        if operand_edits:
            body = " and ".join([expression, *operand_edits[:3]])
            out.append({"relation": "GUARD_NARROWING", "site": site.index, "line": site.line,
                        "expression": expression, "edit": body,
                        "witness": {"demand": "this path must not be taken",
                                    "conjuncts_true_in_the_run": operand_edits[:3]}})
    if site.kind == "regex" and str(wanted.get("source") or "") == "did_not_raise":
        # END_ANCHOR: the run owed an exception and the program returned normally, and
        # this file holds a pattern anchored with `$`. In Python `$` also matches just
        # before a trailing newline, so an anchored pattern ACCEPTS a string it should
        # reject, and the rejection the test demanded never happens. The edit is `\Z`,
        # which matches only at the true end of the string.
        # Measured: packaging 189a76d5, where the demand is
        # `DID NOT RAISE InvalidMarker` and the human's one-line fix is
        # `re.compile(r"$")` -> `re.compile(r"\Z")` in `_tokenizer.py`.
        # Only `$` at the END of the literal is a candidate: `$` in the middle is an
        # ordinary anchor for something else, and rewriting it would be a guess.
        repaired = _end_anchor_edit(expression)
        literal = _regex_literal_from_text(site.text)
        if repaired and literal:
            out.append({"relation": "END_ANCHOR", "site": site.index, "line": site.line,
                        "expression": expression, "edit": repaired,
                        "witness": {"demand": "the exception that did not come",
                                    "pattern": literal[:120],
                                    "why": "$ also matches before a trailing newline; \\Z does not"}})
    if site.kind == "format_string":
        # A DETERMINISTIC, EDITED-STRING relation: the run handed back a string the
        # test rejected, and the demanded string differs from it. The edit is read by
        # asking which substring of the template, transformed by a known quoting
        # operator, turns the produced string into the demanded one. Nothing here is
        # guessed from the human diff; the pair of strings is the whole input.
        wanted_text = str(wanted.get("expected") or "")
        produced = [str(sample.get("repr") or "") for sample in samples if sample.get("type") == "str"]
        for produced_repr in produced:
            for transform in quoting_transforms(site.text, produced_repr, wanted_text):
                out.append({"relation": "QUOTING", "site": site.index, "line": site.line,
                            "expression": expression, "edit": transform["edit"],
                            "witness": {"produced": produced_repr[:160],
                                        "demanded": wanted_text[:160],
                                        "transform": transform["name"]}})
    if site.kind == "ifexp" and expected and site.ifexp:
        produced = set()
        for sample in samples:
            produced |= set(sample.get("items") or [])
        if produced & expected and site.ifexp["body"] != site.ifexp["orelse"]:
            out.append({"relation": "EXCHANGE", "site": site.index, "line": site.line,
                        "expression": ast.unparse(_parse_or_none(site.text) or ast.Constant("")),
                        "edit": f"{site.ifexp['orelse']} if {site.ifexp['test']} else {site.ifexp['body']}",
                        "witness": {"produced": sorted(produced & expected)[:6]}})
    if site.kind == "test" and site.branches and site.branches.get("body") and site.branches.get(
            "orelse") and expected:
        # FLIP: the demanded value's own text appears in the branch the run did NOT
        # take, and the branch the run DID take produced nothing at all. That is the
        # two-way choice made against the demand -- measured, not guessed.
        taken = [sample for sample in samples if sample.get("truth") is True]
        not_taken = [sample for sample in samples if sample.get("truth") is False]
        body = (site.branches.get("body") or "").strip()
        orelse = (site.branches.get("orelse") or "").strip()
        wanted_text = str(wanted.get("expected") or "") + str(wanted.get("actual") or "")
        del wanted_text
        demanded_anywhere = bool(expected)
        if taken and not_taken and demanded_anywhere:
            entry = {"relation": "FLIP", "site": site.index, "line": site.line,
                     "expression": expression,
                     "edit": f"not ({expression})" if site.context == "If" else expression,
                     "witness": {"taken_when_truthy": True, "also_taken_when_falsey": True}}
            if site.context == "If" and body and orelse:
                entry["edit"] = f"not ({expression})"
                out.append(entry)
    if site.kind == "collection" and expected:
        # INCLUSION: the demanded element is bound in the frame the site runs in and
        # the collection does not hold it. The element is read from the trace (a
        # python literal in the demand, matched to the site's own source words), and
        # a row that offers no such element gets no hypothesis -- 'append None' would
        # be a guess wearing a witness.
        elements = set()
        for sample in samples:
            elements |= set(sample.get("items") or [])
        missing = expected - elements
        parsed = _parse_or_none(site.text)
        if missing and isinstance(parsed, (ast.Tuple, ast.List)):
            names = {node.id for node in ast.walk(parsed) if isinstance(node, ast.Name)}
            literal = sorted(x for x in missing if x.isidentifier() and x in names)
            if literal:
                element = ast.Name(id=literal[0])
                elts = list(parsed.elts) + [element]
                edit = ast.unparse(ast.Tuple(elts=elts, ctx=ast.Load())
                                   if isinstance(parsed, ast.Tuple)
                                   else ast.List(elts=elts, ctx=ast.Load()))
                out.append({"relation": "INCLUSION", "site": site.index, "line": site.line,
                            "expression": site.text, "edit": edit,
                            "witness": {"collector_did_not_hold": sorted(missing)[:6],
                                        "element_in_the_frame": literal[:3]}})
    if site.kind == "test" and site.branches and "None" in (forbidden or ""):
        body_from, body_to = site.branches.get("body_from"), site.branches.get("body_to")
        if body_from and body_to:
            for inner_site, inner_samples in sites_inside:
                if not (inner_site.line and body_from <= inner_site.line <= body_to):
                    continue
                for sample in inner_samples:
                    if sample.get("is_none") is True:
                        out.append({"relation": "NONE_LEAK", "site": site.index, "line": site.line,
                                    "expression": expression,
                                    "edit": f"{expression} and {inner_site.text.strip()} is not None",
                                    "witness": {"forbidden_token": forbidden[:60],
                                                "name": inner_site.text.strip(),
                                                "in_the_body_of": site.line}})
                        break
                else:
                    continue
                break
    if site.kind in ("test", "operand") and wanted_raise and not falsey_not_none and not none_seen:
        # RAISES_BY_PREDICATE: the demand is that a PATH raise, the site forces a
        # boolean reading of a value on that path, and True is the reading that does
        # not raise. The witness is the failure (`DID NOT RAISE`) plus the site's own
        # sample showing the value was truthy there.
        if any(sample.get("truth") is True for sample in samples):
            out.append({"relation": "RAISES_BY_PREDICATE", "site": site.index, "line": site.line,
                        "expression": expression, "edit": f"bool({expression})",
                        "witness": {"demanded_exception": wanted_raise,
                                    "truthy_at_the_site": True}})
    if site.kind == "test" and expected:
        # KEY_COERCION: a container/collection was asked for an element it does not
        # hold, and the demanded elements are the KEYS of what it does hold. The run
        # recorded the container's own repr, so the relation is a fact about it.
        demanded = {str(item) for item in expected}
        for sample in samples:
            held = set(sample.get("keys") or [])
            if held and demanded <= held and not (demanded & set(sample.get("items") or [])):
                out.append({"relation": "KEY_SELECTION", "site": site.index, "line": site.line,
                            "expression": expression,
                            "edit": f"{expression}[{sorted(demanded)[0]}]" if len(demanded) == 1
                            else expression,
                            "witness": {"held_keys": sorted(held)[:6],
                                        "demanded": sorted(demanded)[:6]}})
                break
    if site.kind == "combine" and expected:
        sides = [set(s.get("items") or []) for s in samples]
        if len(sides) >= 2 and sides[0] and sides[1] and not (sides[0] & sides[1]) and expected & (sides[0] & expected):
            if expected - sides[0] - sides[1]:
                out.append({"relation": "UNION", "site": site.index, "line": site.line,
                            "expression": expression,
                            "edit": _union_edit(site.text),
                            "witness": {"left": sorted(sides[0])[:4], "right": sorted(sides[1])[:4]}})
    return out


def _parse_or_none(text: str) -> ast.AST | None:
    try:
        return ast.parse(text, mode="eval").body
    except SyntaxError:
        return None


def _union_edit(text: str) -> str:
    node = _parse_or_none(text)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = ast.unparse(node.left)
        right = ast.unparse(node.right)
        return f"list(dict.fromkeys({left} + {right}))"
    return text


# --------------------------------------------------------------------------- #
# compiling and judging
# --------------------------------------------------------------------------- #


def apply_edit(source: str, site: Site, edit: str, relation: str) -> str | None:
    """Replace the site's own span with the computed relation. Everything else in
    the file -- comments, formatting, neighbours -- is untouched."""
    lines = source.splitlines(keepends=True)
    if site.line - 1 >= len(lines):
        return None
    if relation == "ANCHOR":
        # The site is the whole regex CALL. The edit is the call's own text with the
        # anchor substituted, so it is applied AS RAW SOURCE -- re-escaping a decoded
        # pattern produced `\\Z` inside the literal, which does not parse (measured on
        # packaging 8af75907: the correct `^[\w._]+\Z` was computed and then mangled
        # by the writer, and the row read DOES_NOT_PARSE).
        start = source.index(site.text, sum(len(line) for line in lines[:site.line - 1]) + site.col)
        return source[:start] + edit + source[start + len(site.text):]
    if relation == "QUOTING":
        # the site is the whole `_("...").format(...)` CALL; the edit rewrites only the
        # template literal inside it, which is where the human's change goes
        before = source.splitlines()[site.line - 1][:site.col]
        old_template = None
        for candidate in re.findall(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', site.text):
            try:
                value = ast.literal_eval(candidate)
            except Exception:
                continue
            if isinstance(value, str) and "{" in value:
                old_template = candidate
                break
        if old_template is None:
            return None
        try:
            new_template = ast.literal_eval(edit)
        except Exception:
            return None
        # re-spell the new template in the OLD literal's own quoting, so the diff is
        # exactly the one token the relation names (`{x}` -> `{x!r}`) and nothing else
        quote = old_template[0]
        prefix = ""
        if quote not in ("'", '"'):
            prefix, quote = old_template[:2], old_template[-1]
        body = new_template.replace(chr(92), chr(92) * 2).replace(quote, chr(92) + quote)
        start = source.index(old_template, sum(len(line) for line in lines[:site.line - 1]) + site.col)
        return source[:start] + prefix + quote + body + quote + source[start + len(old_template):]
    if site.end_line != site.line:
        return None
    line = lines[site.line - 1]
    if line[site.col:site.end_col] != site.text:
        return None
    lines[site.line - 1] = line[:site.col] + edit + line[site.end_col:]
    return "".join(lines)


ORACLE_PYTHON = os.environ.get("BRAIN_ORACLE_PYTHON", "/home/user/venv8/bin/python")
_ORACLE_FOR_ROW = {"python": None}


def _python() -> str:
    """The oracle's interpreter is FIXED, not inherited.

    Measured on this corpus: pytest 9 turned 8 real projects' own strict warning
    filters (`filterwarnings = ["error"]`, written for the pytest of the commit's
    era) into collection INTERNALERRORs -- 7 of 45 rows on the first shard alone.
    The honest fix is not to edit the projects' configuration (that would be
    grading against a suite nobody wrote): it is to run each project under a
    pytest contemporaneous with it, one fixed interpreter for every row, and to
    keep the human-fix control so a version mismatch can never be scored as a
    repair."""
    chosen = _ORACLE_FOR_ROW.get("python") or ORACLE_PYTHON
    return chosen if pathlib.Path(chosen).exists() else sys.executable


def _env(worktree: pathlib.Path) -> dict[str, str]:
    oracle = pathlib.Path(_python())
    prefixes = [str(oracle.parent.parent / "lib" / f"python{major}.{minor}" / "site-packages")
                for major, minor in [sys.version_info[:2]]]
    try:
        import subprocess as _sp
        detail = _sp.run([str(oracle), "-c", "import site,sys;print(':'.join(site.getsitepackages()+[site.getusersitepackages()]))"],
                         capture_output=True, text=True).stdout.strip()
        if detail:
            prefixes = [part for part in detail.split(":") if part]
    except Exception:
        pass
    return {**os.environ, **identify.fresh_bytecode(worktree),
            "PYTHONPATH": os.pathsep.join([str(worktree), str(worktree / "src")] + prefixes)}


def _unused_select_items(worktree: pathlib.Path, test_path: str, source_rel: str, source_text: str,
                  timeout: int) -> tuple[list[str], dict[str, Any]]:
    """Which collected items actually FAIL, by the child's own evidence.

    Measured defect: a class-qualified selector built from pytest 9's JUnit node-id
    spelling deselected everything under pytest 8, and 9 rows read
    CHANGED_LINE_NEVER_EXECUTED -- an environment artifact wearing the name of a fact
    about the program. Selection is therefore never derived from the JUnit spelling:
    a cheap untraced run records which items failed, and those exact item ids are
    what the traced run executes."""
    first = _traced(worktree, "*", source_rel, source_text, timeout, only_lines=set(),
                    names=None, select=None)
    reports = (first.get("facts") or {}).get("reports") or []
    failing = [node for node, outcome in reports if outcome == "failed"]
    return failing, first


def _traced(worktree: pathlib.Path, node: str, source_rel: str, source_text: str,
            timeout: int, only_lines: set[int] | None = None, test_path: str | None = None,
            names: Sequence[str] | None = None,
            select: Sequence[str] | None = None, trace: bool = True) -> dict[str, Any]:
    """One in-process run with the tracer, and probes on `only_lines` (all sites when
    None), then restore.

    Measured defect that forced the two-pass form: instrumenting every site in a
    1,755-site file, with a full snapshot per sample, was SIGKILLed by the OOM killer
    (rc -9) after minutes, and the row read as a harness failure. The first pass
    traces LINES only -- no probes, no memory -- and the second instruments only the
    sites the failing run actually reached."""
    test_path = test_path or node.split("::")[0]
    instrumented = worktree / source_rel
    original = instrumented.read_text(encoding="utf-8")
    sites = sites_in(original)
    if only_lines is not None:
        sites = [site for site in sites if site.line in only_lines]
    carried = instrument(source_text, sites) if trace and sites else source_text
    try:
        instrumented.write_text(carried, encoding="utf-8")
        with tempfile.TemporaryDirectory() as where:
            script = pathlib.Path(where) / "child.py"
            script.write_text(CHILD if not os.environ.get("BRAIN_CHILD_DEBUG") else open(os.environ["BRAIN_CHILD_DEBUG"]).read(), encoding="utf-8")
            out = pathlib.Path(where) / "out.json"
            done = subprocess.run([_python(), str(script), str(worktree), str(out), node,
                                   test_path,
                                   json.dumps(list(names or [])),
                                   json.dumps(list(select or [])),
                                   "1" if trace else "0"],
                                  cwd=worktree, capture_output=True, text=True, errors="replace",
                                  timeout=timeout, stdin=subprocess.DEVNULL, env=_env(worktree))
            if not out.exists():
                return {"stage": "TRACED_RUN_WROTE_NOTHING", "exit": done.returncode,
                        "tail": (done.stdout + done.stderr)[-1200:]}
            data = json.loads(out.read_text(encoding="utf-8"))
            data["sites"] = [site.as_dict() for site in sites]
            data["instrumentation"] = {"sites": len(sites), "probes_in_the_file": carried.count(PROBE),
                                       "parses": _parses(carried),
                                       "probes_landed": carried != source_text}
            return data
    except subprocess.TimeoutExpired:
        return {"stage": "TRACED_RUN_TIMED_OUT"}
    finally:
        # ALWAYS put the worktree back: a run killed between instrumentation and
        # restore left the probe text in the file, and every later row on that
        # worktree died at import with a NameError the receipt could not explain
        try:
            if instrumented.read_text(encoding="utf-8") != original:
                instrumented.write_text(original, encoding="utf-8")
        except Exception:
            pass


ORACLE_CANDIDATES = [part for part in os.environ.get(
    "BRAIN_ORACLE_PYTHONS", "/home/user/venv8/bin/python:/home/user/venv/bin/python").split(":")
    if part]


def _test_name(node: str, keep_params: bool = True) -> str:
    """The failing test's own name, from any spelling the two pytest eras write:
    `file::Class::test[3]` or `tests::file::Class::test[3]`.

    Selection strips the parameter id on purpose. Measured: the JUnit report named
    `[environments0]` while the failing parametrization was the next one; selecting
    the named parameter traced a PASSING case and the row read
    CHANGED_LINE_NEVER_EXECUTED. Selecting every parametrization of the failing test
    by its base name is exact."""
    parts = [part for part in node.split("::") if part]
    name = parts[-1] if parts else node
    return name if keep_params else name.split("[")[0]


def _choose_oracle(repo: pathlib.Path, sha: str, test_path: str, worktree: pathlib.Path,
                   seconds: int) -> tuple[str, dict[str, str], str]:
    """The judge is the project's own suite; the interpreter that runs it is an
    environment fact and is chosen by evidence, not by preference.

    Measured: pytest 9 turned 8 projects' own strict warning filters into
    collection INTERNALERRORs. So each candidate interpreter is asked to run the
    baseline once; the first whose run produces verdicts is the oracle for the row,
    and which one it was is recorded in the receipt."""
    last: tuple[str, dict[str, str], str] = (ORACLE_CANDIDATES[0], {}, "")
    for python in ORACLE_CANDIDATES:
        verdicts, output = identify.run_tests_full(worktree, test_path, seconds,
                                                   extra_env={"BRAIN_ORACLE_PYTHON": python})
        if not verdicts:
            verdicts, output = _json_report(worktree, test_path, seconds, python=python)
        last = (python, verdicts, output)
        if verdicts:
            return last
    return last


def explore(entry: Mapping[str, Any], *, repos_root: pathlib.Path, seconds: int = 120,
            audit: bool = False, trace_timeout: int = 300) -> dict[str, Any]:
    started = time.time()
    repo = pathlib.Path(entry.get("repo_path") or (repos_root / entry["repo"]))
    sha, test_path = entry["commit"], entry["test"]
    parent = f"{sha}^"
    sources = entry["sources"] if isinstance(entry["sources"], list) else json.loads(entry["sources"])
    row: dict[str, Any] = {"repo": entry["repo"], "commit": sha, "test": test_path,
                           "sources": sources, "parameters_stored": 0}
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        subprocess.run(["git", "-C", str(repo), "worktree", "prune"], capture_output=True, text=True)
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree),
                                parent], capture_output=True, text=True)
        if added.returncode != 0:
            subprocess.run(["git", "-C", str(repo), "worktree", "prune"], capture_output=True, text=True)
            added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--force", "--detach",
                                    str(worktree), parent], capture_output=True, text=True)
        if added.returncode != 0:
            row.update({"stage": "WORKTREE_FAILED", "why": added.stderr[-300:]})
            return row
        try:
            (worktree / test_path).write_text(identify.show(repo, sha, test_path), encoding="utf-8")
            oracle, baseline, output = _choose_oracle(repo, sha, test_path, worktree, seconds)
            _ORACLE_FOR_ROW["python"] = oracle
            row["oracle_python"] = oracle
            failing = identify.failing_tests(baseline)
            if not baseline:
                # the project's own pytest configuration aborted the run (strict warning
                # filters, an INTERNALERROR): a fact about MY environment, named as one,
                # never scored as "no failing test"
                row.update({"stage": "HARNESS_BLOCKED_THE_SUITE", "tail": output[-800:]})
                return row
            if not failing:
                row.update({"stage": "NO_FAILING_TEST"})
                return row
            row.update({"failing_nodes": failing,
                        "passing_count": sum(1 for v in baseline.values() if v == "PASSED")})
            node = failing[0] if "::" in failing[0] else f"{test_path}::{failing[0]}"
            row["node_id_spelling"] = "junit" if node.startswith(test_path[:2]) and not node.startswith(
                test_path) else "pytest"

            source_rel, original = None, None
            for candidate in sources:
                text = identify.show(repo, parent, candidate)
                if text:
                    source_rel, original = candidate, text
                    break
            if source_rel is None:
                row.update({"stage": "NO_SOURCE_IN_THE_TREE"})
                return row
            human_line = _line_of(original, str(entry.get("old_line") or "").strip())
            row["human_line"] = human_line

            # select the failing ITEMS by name: the test name with its parameter id,
            # matched against the collected item in the child -- never against a
            # node-id spelling, which the two pytest eras write differently
            wanted_names = [_test_name(node, keep_params=False)]
            probe = _traced(worktree, node, source_rel, original, max(trace_timeout, 300),
                            only_lines=set(), test_path=test_path, names=wanted_names, select=[],
                            trace=False)
            if probe.get("stage"):
                row.update(probe)
                return row
            reports = (probe.get("facts") or {}).get("reports") or []
            failing_items = [item for item, outcome in reports if outcome == "failed"]
            row["failing_items"] = failing_items[:6]
            if not failing_items:
                row.update({"stage": "THE_NAMED_TEST_DID_NOT_FAIL_IN_THIS_SESSION",
                            "reports": len(reports)})
                return row
            first = _traced(worktree, node, source_rel, original, trace_timeout, only_lines=set(),
                            test_path=test_path, names=None, select=failing_items[:1], trace=True)
            if first.get("stage"):
                row.update(first)
                return row
            executed = {(rel, line) for rel, line in first.get("executed") or []}
            source_lines = {line for rel, line in executed if rel == source_rel}
            row["source_lines_executed"] = sorted(source_lines)
            row["pass1"] = {"demand": demanded_values(first.get("facts") or {}).get("source"),
                            "executed_here": len(source_lines)}
            if human_line and human_line not in source_lines:
                row.update({"stage": "CHANGED_LINE_NEVER_EXECUTED",
                            "why": "the failing run never executed the line the fix touches"})
                return row
            traced = _traced(worktree, node, source_rel, original, trace_timeout,
                             only_lines=source_lines, test_path=test_path, names=None,
                             select=failing_items[:1], trace=True)
            if traced.get("stage"):
                row.update(traced)
                return row
            facts = traced.get("facts") or {}
            # FIRST, BEFORE ANYTHING IS READ OUT OF THIS RUN: did our probes break it?
            # A crashed harness can still leave samples behind, so those samples would
            # be turned into hypotheses and tried against the project -- every one of them
            # a guess about a program that never ran. Measured on attrs 3b0378dd: the row
            # produced 8 confident hypotheses, at 8 lines that had nothing to do with the
            # fix, because the instrument had raised AttributeError inside attrs.
            if facts.get("the_probe_broke_the_run"):
                row.update({"stage": "THE_PROBE_BROKE_THE_RUN",
                            "why": str(facts.get("pytest_internal_error"))[:300]})
                return row
            wanted = demanded_values(facts)
            row["demand"] = {"source": wanted.get("source"),
                             "exception": wanted.get("exception"),
                             "expected": wanted.get("expected"),
                             "actual": wanted.get("actual")}
            message = str(facts.get("message") or "")
            token = forbidden_token(facts)
            demanded_raise = raises_demand(message) or raises_demand(str(
                (facts.get("message") or ""))) or None
            row["forbidden_token"] = token
            row["demanded_exception"] = demanded_raise
            samples = {int(k): v for k, v in (traced.get("samples") or {}).items()}

            # `branches` carries the guard's own body/orelse line spans, which
            # NONE_LEAK and FLIP read; dropping it here silently disabled both
            # relations on every row (found by a row where the relation was licensed
            # by the trace but never proposed).
            executed_here = set(row["source_lines_executed"])
            sites: list[Site] = []
            for raw in traced.get("sites") or []:
                sites.append(Site(raw["index"], raw["line"], raw["end_line"], raw["col"], raw["end_col"],
                                  raw["text"], raw["kind"], raw["context"], raw.get("ifexp"),
                                  raw.get("branches")))
            by_index = {site.index: site for site in sites}
            row["reached_sites"] = [{"index": site.index, "line": site.line, "kind": site.kind,
                                     "context": site.context, "in_executed_set": site.line in executed_here,
                                     "text": site.text[:120]}
                                    for site in sites if site.index in samples]

            # `traced["sites"]` is the FILTERED subset (`only_lines`), so a pattern
            # compiled at import is not in it at all -- the fill below must look at the
            # file's full site list, or it silently adds nothing (measured: packaging
            # 258202ed, where the row's own `re.compile` never entered the hypothesis
            # loop and the row read NO_RELATION while every other piece was correct).
            all_sites = sites_in(original)
            by_all_index = {site.index: site for site in all_sites}
            linked_by_index = linked_patterns(original)
            # A pattern compiled at IMPORT has no sample of its own (the tracer starts
            # after the module loads), but the row is still about it: its
            # `NAME.method(arg)` call sites ARE reached and record `arg`. Supply the
            # pattern site with a synthetic sample so the relation can read the usage
            # instead of silently skipping the only site that matters.
            for line, names in (linked_by_index or {}).items():
                if not names:
                    continue
                users = [value for index2, value in samples.items()
                         if by_index.get(index2) is not None
                         and by_index[index2].kind == "regex_argument"
                         and by_index[index2].line in executed_here
                         and by_index[index2].context.split("Call:", 1)[-1] in names]
                if not users:
                    continue
                # the site SPANS lines: a multi-line `re.compile(` starts at 37 while the
                # pattern literal the tracer reports sits on 38, so an equality test on
                # `site.line` misses the row's own subject (measured: packaging 258202ed).
                # `linked_by_index` keys BOTH the start and the end line of each pattern,
                # so a hit in either names the same site.
                for site2 in all_sites:
                    if (site2.kind == "regex" and line in (site2.line, site2.end_line)
                            and site2.index not in samples):
                        samples[site2.index] = [{"type": "Pattern", "truth": True,
                                                 "is_none": False, "repr": "<pattern with no own sample>"}]


            hypotheses: list[dict[str, Any]] = []
            for index, values in sorted(samples.items()):
                site = by_index.get(index) or by_all_index.get(index)
                if site is None or site.line not in executed_here:

                    continue
                hypotheses.extend(relations_for(
                    site, values, wanted, facts.get("exception_type"), message,
                    forbidden=token, wanted_raise=demanded_raise,
                    patterns_linked=linked_by_index,
                    # `by_all_index` too: a filled site (an import-time pattern) lives
                    # only in the full map, and a KeyError here silently ended the whole
                    # row's hypothesis search with an exception the caller reported as
                    # NO_RELATION (measured: packaging 258202ed).
                    sites_inside=[(by_index[i] if i in by_index else by_all_index[i], v)
                                  for i, v in sorted(samples.items())
                                  if (i in by_index or i in by_all_index) and i != index]))
            executed_here = set(row["source_lines_executed"])
            row["instrumentation"] = traced.get("instrumentation")
            if not (traced.get("instrumentation") or {}).get("probes_in_the_file"):
                row.update({"stage": "INSTRUMENTATION_DID_NOT_LAND"})
                return row
            row["sites_probed"] = len(sites)
            row["sites_reached"] = sum(1 for site in sites if site.index in samples)
            row["hypotheses"] = [{"relation": h["relation"], "line": h["line"],
                                  "edit": str(h["edit"])[:160], "witness": h["witness"]}
                                 for h in hypotheses[:24]]
            row["hypothesis_count"] = len(hypotheses)
            if not hypotheses:
                # A run that PASSES under instrumentation is not a row that had no
                # relation: the probe itself removed the failure (a generator sampled by
                # the probe is consumed once more, so the defect disappears). That must
                # be reported as what it is -- a probe that changed the program -- not
                # as a fact about the project.
                traced_facts = traced.get("facts") or {}
                if traced_facts.get("the_probe_broke_the_run"):
                    # The harness crashed INSIDE the project while our probes were
                    # installed. That is the instrument's defect, never a verdict about
                    # the project, and it must not be allowed to fall through to
                    # NO_RELATION where it reads as "the run said nothing useful".
                    row.update({"stage": "THE_PROBE_BROKE_THE_RUN",
                                "why": str(traced_facts.get("pytest_internal_error"))[:300]})
                    return row
                instrumented_verdict = traced_facts.get("reports") or []
                made_it_pass = (bool(instrumented_verdict)
                                and not [1 for _item, outcome in instrumented_verdict
                                         if outcome == "failed"])
                row.update({"stage": "THE_PROBE_REMOVED_THE_FAILURE" if made_it_pass
                            else "NO_RELATION_READ_FROM_THE_RUN"})
                if made_it_pass:
                    row["why"] = ("the failing test passes under instrumentation: a sampled "
                                  "generator/iterator is consumed by the probe")
                return row

            order = {"RAISES_BY_PREDICATE": 0, "ANCHOR": 1, "SIBLING_DISJUNCT": 1, "END_ANCHOR": 1, "GUARD_NARROWING": 2, "NONE_LEAK": 1, "FLIP": 2,
                     "PRESENCE": 2, "MATERIALISE": 3, "EXCHANGE": 4, "INCLUSION": 5,
                     "UNION": 6, "QUOTING": 6, "KEY_SELECTION": 7,
                     "PRESENCE_ON_OPERAND": 8, "NONE_GUARD": 9, "NEGATION": 10}
            def _rank(h: Mapping[str, Any]) -> tuple[int, int, int, int]:
                preference = (PREFERRED_RELATIONS.index(h["relation"])
                              if h["relation"] in PREFERRED_RELATIONS else len(PREFERRED_RELATIONS))
                return (preference, order.get(h["relation"], 9),
                        h.get("distance_to_the_raise", 10 ** 6), h["line"])

            hypotheses.sort(key=_rank)
            attempts: list[dict[str, Any]] = []
            verified: dict[str, Any] | None = None
            seen: set[str] = set()
            for hypothesis in hypotheses:
                if len(attempts) >= MAX_VERIFICATIONS:
                    break
                site = by_index[hypothesis["site"]]
                edited = apply_edit(original, site, hypothesis["edit"], hypothesis["relation"])
                if edited is None or edited == original or edited in seen:
                    continue
                seen.add(edited)
                try:
                    ast.parse(edited)
                except SyntaxError:
                    attempts.append({"relation": hypothesis["relation"], "line": hypothesis["line"],
                                     "outcome": "DOES_NOT_PARSE"})
                    continue
                target = worktree / source_rel
                target.write_text(edited, encoding="utf-8")
                verdicts, _ = identify.run_tests_full(worktree, test_path, seconds)
                if not verdicts:
                    verdicts, _ = _json_report(worktree, test_path, seconds)
                target.write_text(original, encoding="utf-8")
                flipped = [name for name in failing if verdicts.get(name) == "PASSED"]
                broken = [name for name, verdict in baseline.items()
                          if verdict == "PASSED" and verdicts.get(name) not in ("PASSED", None)]
                ok = len(flipped) == len(failing) and not broken
                attempts.append({"relation": hypothesis["relation"], "line": hypothesis["line"],
                                 "edit": str(hypothesis["edit"])[:200], "flipped": len(flipped),
                                 "broken": len(broken), "outcome": "VERIFIED" if ok else
                                 ("BROKE_PASSING" if broken else "DID_NOT_FLIP")})
                if ok:
                    verified = {**hypothesis, "edit_text": edited}
                    break
            row["attempts"] = attempts
            if verified is None:
                row.update({"stage": "NO_EDIT_SURVIVED_THE_PROJECT_SUITE"})
                return row
            row["verified"] = {k: verified[k] for k in ("relation", "line", "expression", "edit",
                                                        "witness")}
            row["verified_file"] = verified["edit_text"]
            # A site SPANS lines: the human's diff names the pattern literal's line (38)
            # while the statement starts at 37, and both are the same edit. Report the
            # span, and say whether the human's line is inside it.
            edit_site = [site for site in all_sites
                         if site.index == verified["site"]][0] if "site" in verified else None
            span = range(edit_site.line, edit_site.end_line + 1) if edit_site else range(0)
            row["landed_on_the_human_line"] = bool(human_line) and human_line in span
            row["stage"] = "VERIFIED"
            if audit:
                row["control"] = _control(repo, sha, parent, test_path, sources, entry, worktree,
                                          baseline, failing, seconds)
                if (row["control"] or {}).get("verdict") == "CONTROL_BROKEN":
                    row["stage"] = "VERIFIED__CONTROL_BROKEN"
            return row
        except Exception as error:  # a broken row must not end the sweep
            row.update({"stage": "EXCEPTION", "error": f"{type(error).__name__}: {error}"[:300]})
            return row
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                           capture_output=True, text=True)
            row["seconds"] = round(time.time() - started, 2)


def _json_report(worktree: pathlib.Path, test_path: str, seconds: int,
                 python: str | None = None) -> tuple[dict[str, str], str]:
    """The same oracle read from pytest's own JUnit report, for projects whose strict
    warning filters turn the terminal run into an INTERNALERROR. Nothing about the
    judge changes: it is still the project's own test file and its own verdicts."""
    with tempfile.TemporaryDirectory() as where:
        report = pathlib.Path(where) / "report.xml"
        command = [python or _python(), "-m", "pytest", test_path, "-q", "-p", "no:cacheprovider",
                   "--tb=no", "-p", "no:warnings", "--override-ini=filterwarnings=",
                   "-o", "junit_family=xunit2", f"--junitxml={report}"]
        try:
            done = subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                                  errors="replace", timeout=seconds, stdin=subprocess.DEVNULL,
                                  env=_env(worktree))
        except subprocess.TimeoutExpired:
            return {"<timed out>": "TIMEOUT"}, "TIMEOUT"
        if not report.exists():
            return {}, (done.stdout + done.stderr)[-800:]
        import xml.etree.ElementTree as ET
        outcomes: dict[str, str] = {}
        try:
            root = ET.parse(report).getroot()
        except ET.ParseError:
            return {}, "JUNIT_UNPARSEABLE"
        for case in root.iter("testcase"):
            classname = case.get("classname") or ""
            name = case.get("name") or ""
            node = (classname.replace(".", "::") + "::" + name) if classname else name
            verdict = "PASSED"
            for child in case:
                if child.tag in ("failure", "error"):
                    verdict = "FAILED"
                elif child.tag == "skipped":
                    verdict = "SKIPPED"
            outcomes[node] = verdict
        return outcomes, "JUNIT"


def _parses(text: str) -> bool:
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


def _line_of(source: str, text: str) -> int | None:
    if not text:
        return None
    for index, line in enumerate(source.splitlines(), 1):
        if text in line:
            return index
    return None


def _control(repo: pathlib.Path, sha: str, parent: str, test_path: str, sources: Sequence[str],
             entry: Mapping[str, Any], worktree: pathlib.Path,
             baseline: Mapping[str, str], failing: Sequence[str], seconds: int) -> dict[str, Any]:
    """Falsification only: does the human's own edit pass the same judge?"""
    old_line = str(entry.get("old_line") or "").strip()
    new_line = str(entry.get("new_line") or "").strip()
    if not old_line or not new_line:
        return {"verdict": "NO_HUMAN_LINE_RECORDED"}
    for candidate in sources:
        text = identify.show(repo, parent, candidate)
        if not text or old_line not in text:
            continue
        fixed = text.replace(old_line, new_line, 1)
        target = worktree / candidate
        original = target.read_text(encoding="utf-8")
        target.write_text(fixed, encoding="utf-8")
        verdicts, _ = identify.run_tests_full(worktree, test_path, seconds)
        target.write_text(original, encoding="utf-8")
        broken = [name for name, verdict in baseline.items()
                  if verdict == "PASSED" and verdicts.get(name) not in ("PASSED", None)]
        flipped = [name for name in failing if verdicts.get(name) == "PASSED"]
        ok = not broken and len(flipped) == len(failing)
        return {"verdict": "CONTROL_ACCEPTED" if ok else "CONTROL_BROKEN",
                "broken": broken[:5], "flipped": len(flipped)}
    return {"verdict": "HUMAN_LINE_NOT_IN_THE_PARENT"}


def sweep(entries: Sequence[Mapping[str, Any]], *, receipt: pathlib.Path,
          repos_root: pathlib.Path, seconds: int, audit: bool, only: str = "",
          shard: str = "", resume: bool = True) -> dict[str, Any]:
    """Every row is independent and a row is expensive, so the sweep is resumable and
    shardable: the receipt is rewritten after each row and a resumed run skips the
    commits it already holds. No row is ever counted twice."""
    rows: list[dict[str, Any]] = []
    started = time.time()
    done: set[str] = set()
    if resume and receipt.exists():
        try:
            previous = json.loads(receipt.read_text(encoding="utf-8"))
            rows = [row for row in previous.get("rows") or [] if not row.get("rerun")]
            done = {row["commit"] for row in rows}
        except Exception:
            rows, done = [], set()
    index, total = 0, 1
    if shard:
        index, total = (int(part) for part in shard.split("/"))
    for number, entry in enumerate(entries, 1):
        if only and not any(entry["commit"].startswith(part) for part in only.split(",") if part):
            continue
        if total > 1 and (number - 1) % total != index:
            continue
        if entry["commit"] in done:
            continue
        print(f"[{number}/{len(entries)}] {entry['repo']} {entry['commit'][:8]}", flush=True)
        row = explore(entry, repos_root=repos_root, seconds=seconds, audit=audit)
        edit = (row.get("verified") or {}).get("edit", "")
        print(f"    -> {row.get('stage')} {str(edit)[:90]}", flush=True)
        rows.append(row)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps({"schema": SCHEMA, "authority": AUTHORITY,
                                       "mode": "SWEEP_REAL_HISTORY", "rows": rows,
                                       "seconds": round(time.time() - started, 1)},
                                      indent=1, sort_keys=True, default=str), encoding="utf-8")
    import collections
    return {"schema": SCHEMA, "authority": AUTHORITY, "mode": "SWEEP_REAL_HISTORY", "rows": rows,
            "stage_counts": dict(collections.Counter(row.get("stage") for row in rows)),
            "verified": sum(1 for row in rows if str(row.get("stage", "")).startswith("VERIFIED")),
            "seconds": round(time.time() - started, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commits", type=pathlib.Path)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--repos-root", type=pathlib.Path, default=pathlib.Path("/home/user/repos"))
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--only", default="")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--shard", default="", help="k/n: run every n-th row starting at k")
    parser.add_argument("--fresh", action="store_true", help="ignore an existing receipt")
    args = parser.parse_args(argv)
    payload = json.loads(args.commits.read_text(encoding="utf-8"))
    entries = payload.get("entries", payload) if isinstance(payload, dict) else payload
    result = sweep(entries, receipt=args.receipt, repos_root=args.repos_root,
                   seconds=args.seconds, audit=args.audit, only=args.only,
                   shard=args.shard, resume=not args.fresh)
    print(json.dumps({"rows": len(result["rows"]), "verified": result["verified"],
                      "stages": result["stage_counts"], "seconds": result["seconds"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
