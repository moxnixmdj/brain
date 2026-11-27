#!/usr/bin/env python3
"""A guide example watches one input. Measure how much of the code it actually pins.

WHY THIS ROUND EXISTS
---------------------
`THE_GUIDE_IS_A_TEST_SUITE_20261204_V1` measured that a real guide's examples run, and that
130 of 138 reproduce the output the guide printed. That answers *"can the example be
executed?"*. It does not answer the question the system depends on:

  > if the implementation is wrong, does the guide's example say so?

An example that passes on a broken implementation is an admission test, not a regression
test. A store that records "the guide confirms this receiver" on that evidence is storing a
claim it cannot support. The quantity that decides it is **detection power**: the share of
behaviour-changing implementation faults that the documented example kills.

No model, no network, no stored parameter. Real standard-library source is mutated; real
documentation is replayed; the counts are reported with their denominators.

DESIGN
------
1. RECEIVER. A real module from this interpreter's standard library, so guide and code are
   version-matched and offline. Not a fixture written for the experiment.
2. MUTANT. One behaviour-changing edit inside one function body: swap a comparison, swap an
   arithmetic or boolean operator, move a constant by one, replace a returned expression
   with `None`. Generated mechanically from the AST, so the fault set does not depend on my
   opinion about which bugs to inject.
3. EQUIVALENCE CONTROL. A mutant no observable input separates is not a fault, and counting
   it as a miss would blame the guide for the mutant's degeneracy. A mutant is counted only
   when a differential corpus (up to 40 perturbed calls, compared against the unmutated
   function's own value or exception type) separates it. The rest are reported as
   `not_separated`, never as misses.
4. ORACLES over the same counted mutants:
     GUIDE      the function's own docstring examples exactly as the author wrote them
                (the 2026-12-04 oracle);
     SAMPLE_k   k corpus calls with expected values taken from the unmutated function, i.e.
                what k real regression cases would buy (k = 1, 3, 10, 40).
5. WITNESS. For every fault the guide missed, the receipt keeps one concrete call, the
   expected result, and the mutant's result. That is the artefact the project calls missing:
   a requirement-specific, executable, failing observation. Its provenance is a mutation,
   stated as such: an injected fault, not a claim that the standard library is buggy.

WHAT THIS DOES NOT ESTABLISH
----------------------------
* Not a benchmark result. Says nothing about OSWorld, Terminal-Bench or SWE-bench.
* `not_separated` is a corpus limit, not proof of equivalence. A wider corpus can only
  enlarge the denominator, and therefore can only lower the guide's measured power.
* Corpus inputs are perturbations of the documented call's literal arguments. That is a
  convenience of the experiment: a receiver whose guide gives no literal example offers no
  corpus at all, which is itself part of the finding.
* Python only, pure functions only, one interpreter, one documentation style. Other
  languages and other guide styles will give other numbers.
* Mutation score bounds fault detection from below only for faults drawn from this operator
  set. Real bugs are not sampled from it.

Model calls 0. Parameters stored 0. Network at run time 0.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import doctest
import importlib
import inspect
import json
import pathlib
import random
import sys
import time
import types
from typing import Any, Callable, Iterator, Sequence

MAX_MUTANTS_PER_FUNCTION = 24
MAX_CORPUS_INPUTS = 40
SAMPLE_SIZES = (1, 3, 10, 40)

# --------------------------------------------------------------------------------------
# module plumbing
# --------------------------------------------------------------------------------------


@contextlib.contextmanager
def _installed(module: types.ModuleType):
    """The doctest finder only sees objects whose ``__module__`` resolves to this module."""
    name = module.__name__
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        yield module
    finally:
        if previous is not None:
            sys.modules[name] = previous
        else:
            sys.modules.pop(name, None)


def _materialize(name: str, source: str, filename: str) -> types.ModuleType:
    """Execute ``source`` as module ``name``; the module object is usable after the call."""
    module = types.ModuleType(name)
    module.__file__ = filename
    module.__package__ = name.rpartition(".")[0]
    with _installed(module):
        exec(compile(source, filename, "exec"), module.__dict__)
    return module


def _source_tree(module: types.ModuleType) -> ast.Module:
    return ast.parse(inspect.getsource(module))


# --------------------------------------------------------------------------------------
# which functions carry a guide
# --------------------------------------------------------------------------------------


def _doc_examples(node: ast.AST) -> list[doctest.Example]:
    doc = ast.get_docstring(node, clean=False) or ""
    return doctest.DocTestParser().get_examples(doc)


def documented_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    """Module-level functions whose own docstring carries at least one example."""
    counts: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            counts[node.name] = counts.get(node.name, 0) + 1
    out: list[ast.FunctionDef] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or counts[node.name] > 1:
            continue
        if node.name.startswith("_") or not node.body:
            continue
        if any(arg.arg in ("self", "cls") for arg in node.args.args):
            continue
        if not _doc_examples(node):
            continue
        out.append(node)
    return out


# --------------------------------------------------------------------------------------
# mutation, addressed by structural path so a site cannot drift
# --------------------------------------------------------------------------------------

_COMPARE = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.GtE,
    ast.GtE: ast.Lt,
    ast.Gt: ast.LtE,
    ast.LtE: ast.Gt,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
}
_BINOP = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.FloorDiv,
    ast.FloorDiv: ast.Mult,
    ast.Div: ast.Mult,
    ast.Mod: ast.Div,
    ast.Pow: ast.Mult,
    ast.BitOr: ast.BitAnd,
    ast.BitAnd: ast.BitOr,
}


def _walk_paths(node: ast.AST, path: tuple = ()) -> Iterator[tuple[tuple, ast.AST]]:
    for field, value in ast.iter_fields(node):
        if isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, ast.AST):
                    here = path + (field, index)
                    yield here, item
                    yield from _walk_paths(item, here)
        elif isinstance(value, ast.AST):
            here = path + (field,)
            yield here, value
            yield from _walk_paths(value, here)


def _resolve_path(node: ast.AST, path: tuple) -> ast.AST:
    current: Any = node
    for step in path:
        current = getattr(current, step) if isinstance(step, str) else current[step]
    return current


class Mutation:
    __slots__ = ("label", "line", "path", "apply")

    def __init__(self, label: str, line: int, path: tuple, apply: Callable[[ast.AST], None]):
        self.label = label
        self.line = line
        self.path = path
        self.apply = apply


def candidate_mutations(function: ast.FunctionDef) -> list[Mutation]:
    """Every single-site edit of one function body, in source order, capped for cost."""
    out: list[Mutation] = []
    # The docstring is the guide, not the code: mutating it edits the oracle instead of the
    # implementation, and an error message is not an observable (the corpus compares exception
    # types). Both were in the first version and both made the fault set dishonest.
    skip_prefix = ()
    if (
        function.body
        and isinstance(function.body[0], ast.Expr)
        and isinstance(function.body[0].value, ast.Constant)
        and isinstance(function.body[0].value.value, str)
    ):
        skip_prefix = (("body", 0, "value"),)
    raise_paths = []
    for path, node in _walk_paths(function):
        if isinstance(node, ast.Raise):
            raise_paths.extend(p for p, _ in _walk_paths(node) if p[: len(path)] == path)
            raise_paths.append(path)

    for path, node in _walk_paths(function):
        if any(path[: len(prefix)] == prefix for prefix in skip_prefix):
            continue
        if any(path[: len(prefix)] == prefix for prefix in raise_paths) and isinstance(node, ast.Constant) and isinstance(node.value, str):
            continue
        line = getattr(node, "lineno", function.lineno)

        if isinstance(node, ast.Compare):
            for index, op in enumerate(node.ops):
                replacement = _COMPARE.get(type(op))
                if replacement is None:
                    continue

                def apply(target: ast.Compare, index: int = index, replacement=replacement) -> None:
                    target.ops[index] = replacement()

                out.append(
                    Mutation(f"compare:{type(op).__name__}->{replacement.__name__}", line, path, apply)
                )
        elif isinstance(node, ast.BinOp):
            replacement = _BINOP.get(type(node.op))
            if replacement is None:
                continue

            def apply(target: ast.BinOp, replacement=replacement) -> None:
                target.op = replacement()

            out.append(Mutation(f"binop:{type(node.op).__name__}->{replacement.__name__}", line, path, apply))
        elif isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, bool):
                def apply(target: ast.Constant, new: bool = not value) -> None:
                    target.value = new

                out.append(Mutation(f"const:{value}->{not value}", line, path, apply))
            elif isinstance(value, int) and not isinstance(value, bool):
                num = value

                def apply(target: ast.Constant, new: int = num + 1) -> None:
                    target.value = new

                out.append(Mutation(f"const:{num}->{num + 1}", line, path, apply))
            elif isinstance(value, str) and value:
                text = value

                def apply(target: ast.Constant, new: str = text + "X") -> None:
                    target.value = new

                out.append(Mutation(f"const:{text!r}->{text + 'X'!r}", line, path, apply))
        elif isinstance(node, ast.BoolOp):
            current, replacement = type(node.op), ast.Or if isinstance(node.op, ast.And) else ast.And

            def apply(target: ast.BoolOp, replacement=replacement) -> None:
                target.op = replacement()

            out.append(Mutation(f"boolop:{current.__name__}->{replacement.__name__}", line, path, apply))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            def apply(target: ast.UnaryOp) -> None:
                target.op = ast.UAdd()

            out.append(Mutation("unary:not->identity", line, path, apply))

    returns = [(p, n) for p, n in _walk_paths(function) if isinstance(n, ast.Return) and n.value is not None]
    if returns:
        path, node = returns[0]

        def apply(target: ast.Return) -> None:
            target.value = ast.Constant(value=None)

        out.append(Mutation("return:value->None", getattr(node, "lineno", function.lineno), path, apply))
    return out[:MAX_MUTANTS_PER_FUNCTION]


def mutate_function(tree: ast.Module, name: str, mutation: Mutation) -> ast.Module:
    mutated = copy.deepcopy(tree)
    target = next(n for n in mutated.body if isinstance(n, ast.FunctionDef) and n.name == name)
    mutation.apply(_resolve_path(target, mutation.path))
    return mutated


# --------------------------------------------------------------------------------------
# oracles
# --------------------------------------------------------------------------------------


def _run_examples(module: types.ModuleType, function_name: str, examples: Sequence[doctest.Example]) -> dict[str, Any]:
    """Replay documented examples in the module's own namespace, plus its own short name.

    `textwrap.shorten`'s example is written `textwrap.shorten(...)` *inside* `shorten`, so
    the guide names the module it lives in. The 2026-12-04 round learned this the same way;
    it is stated here because a fresh reader would otherwise rebuild the bug.
    """
    short = module.__name__.split(".")[-1]
    globs = dict(module.__dict__)
    globs[short] = module
    globs[module.__name__] = module
    test = doctest.DocTest(
        list(examples), globs, f"{module.__name__}.{function_name}", module.__file__ or "<memory>", 0, ""
    )
    runner = doctest.DocTestRunner(verbose=False, optionflags=doctest.ELLIPSIS)
    output: list[str] = []
    result = runner.run(test, out=output.append)
    return {
        "attempted": result.attempted,
        "failed": result.failed,
        "killed": result.failed > 0,
        "detail": output[:4],
    }


def usable_examples(module: types.ModuleType, function_name: str, examples: Sequence[doctest.Example]) -> list[doctest.Example]:
    """Examples that already run on the unmutated module; the rest are counted as refused."""
    if not examples:
        return []
    if not _run_examples(module, function_name, examples)["failed"]:
        return list(examples)
    kept = []
    for example in examples:
        if not _run_examples(module, function_name, [example])["failed"]:
            kept.append(example)
    return kept


def traced_lines(function: Any, run: Callable[[], Any]) -> set[int]:
    """Lines of ``function``'s own code that execute during ``run`` (stdlib only, no tracer pkg)."""
    code = getattr(function, "__code__", None)
    if code is None:
        return set()
    seen: set[int] = set()

    def tracer(frame, event, arg):
        if event == "line" and frame.f_code is code:
            seen.add(frame.f_lineno)
        return tracer

    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        run()
    finally:
        sys.settrace(previous)
    return seen


def branch_spans(function: ast.FunctionDef) -> list[dict[str, Any]]:
    """Every decision branch of one function body, by source span."""
    spans: list[dict[str, Any]] = []
    for path, node in _walk_paths(function):
        if not isinstance(node, ast.If):
            continue
        for label, block in (("then", node.body), ("else", node.orelse)):
            if not block:
                continue
            first, last = block[0], block[-1]
            spans.append(
                {
                    "path": path,
                    "branch": label,
                    "test_line": node.lineno,
                    "start": first.lineno,
                    "end": getattr(last, "end_lineno", last.lineno) or last.lineno,
                }
            )
    return spans


def _spans_covering(spans: Sequence[dict[str, Any]], line: int) -> list[dict[str, Any]]:
    return [span for span in spans if span["start"] <= line <= span["end"]]


def covering_branch(function: ast.FunctionDef, mutation: Mutation, spans: Sequence[dict[str, Any]]) -> ast.If | None:
    """The innermost If whose branch contains the mutated site, if any."""
    node = _resolve_path(function, mutation.path)
    line = getattr(node, "lineno", None)
    if line is None:
        return None
    covering = _spans_covering(spans, line)
    if not covering:
        return None
    innermost = max(covering, key=lambda span: span["start"])
    return innermost


BOUNDARY_LATTICE = (
    [],
    [0],
    [1],
    [-1],
    [0, 0],
    [1, 1],
    [1, 2],
    [2, 1],
    [0, 1, 2],
    (),
    (0,),
    [0.0],
    [-1.0, 1.0],
    "",
    "a",
    " ",
    "a" * 80,
    "a b",
    {},
    {"a": 0},
    {"a": 0, "b": 1},
    0,
    1,
    -1,
    2,
    0.0,
    1.0,
    True,
    False,
)


def boundary_inputs(
    function_name: str, examples: Sequence[doctest.Example], extra: Sequence[tuple]
) -> list[tuple[tuple, dict]]:
    """Inputs built to reach a guard: the boundary lattice in every documented shape."""
    shapes: list[tuple[tuple, dict]] = []
    for example in examples:
        shapes.extend(_documented_calls(example, function_name))
    if not shapes:
        return []
    out: list[tuple[tuple, dict]] = list(extra)
    containers = (list, tuple, str, dict)
    for args, kwargs in shapes:
        if len(args) == 1 and not kwargs:
            out.extend(((value,), {}) for value in BOUNDARY_LATTICE)
            continue
        for index, value in enumerate(args):
            for candidate in BOUNDARY_LATTICE:
                if isinstance(value, containers) == isinstance(candidate, containers):
                    out.append((args[:index] + (candidate,) + args[index + 1 :], kwargs))
    return out


def reach_guards(
    function: Any,
    examples: Sequence[doctest.Example],
    spans: Sequence[dict[str, Any]],
    reached: Sequence[dict[str, Any]],
    extra: Sequence[tuple],
) -> list[dict[str, Any]]:
    """Find one input per guard the guide never entered; the expected output is NOT known."""
    untested = [span for span in spans if span not in reached]
    found: list[dict[str, Any]] = []
    if not untested:
        return found
    for args, kwargs in boundary_inputs(function.__name__, examples, extra):
        if not untested:
            break
        try:
            lines = traced_lines(function, lambda: observe(function, args, kwargs))
        except Exception:  # noqa: BLE001 - a probe that cannot run is simply not a witness
            continue
        for span in list(untested):
            if any(span["start"] <= line <= span["end"] for line in lines):
                found.append({"line": span["test_line"], "branch": span["branch"], "input": repr((args, kwargs))})
                untested.remove(span)
    return found


def _documented_calls(example: doctest.Example, name: str) -> list[tuple[tuple, dict]]:
    try:
        parsed = ast.parse(example.source.strip())
    except SyntaxError:
        return []
    calls = []
    for node in ast.walk(parsed):
        if not isinstance(node, ast.Call):
            continue
        called = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if called != name:
            continue
        try:
            args = tuple(ast.literal_eval(arg) for arg in node.args)
            kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords if kw.arg}
        except (ValueError, SyntaxError, TypeError):
            continue
        calls.append((args, kwargs))
    return calls


def _random_value(like: Any, rng: random.Random) -> Any:
    """A random value of the same kind as the documented one.

    The documented call is used only to learn the *type* of each argument. Values are drawn
    without reference to the documented value, so the fault corpus is not centred on the
    example -- that centring is what would otherwise inflate the guide's score.
    """
    if isinstance(like, bool):
        return rng.random() < 0.5
    if isinstance(like, int):
        return rng.choice([rng.randint(-20, 40), rng.randint(0, 3), -1, 0, 1, 2, 10**6])
    if isinstance(like, float):
        return rng.choice([round(rng.uniform(-50, 50), 3), 0.0, -1.5, 1e6])
    if isinstance(like, str):
        alphabet = "abcXYZ 0123456789._-"
        length = rng.choice([0, 1, 2, 3, 5, 8, 12])
        return "".join(rng.choice(alphabet) for _ in range(length))
    if isinstance(like, (list, tuple)):
        length = rng.choice([0, 1, 2, 3, 5, 8])
        if like:
            items = [_random_value(like[0], rng) for _ in range(length)]
        else:
            items = [rng.randint(-5, 20) for _ in range(length)]
        return items if isinstance(like, list) else tuple(items)
    if isinstance(like, dict):
        keys = rng.sample("abcdef", rng.choice([0, 1, 2, 3]))
        return {key: rng.randint(-5, 20) for key in keys}
    return like


def random_corpus(
    function_name: str, examples: Sequence[doctest.Example], rng: random.Random, count: int = 40
) -> list[tuple[tuple, dict]]:
    """Independent inputs of the documented shape; none of them is the documented input."""
    shapes: list[tuple[tuple, dict]] = []
    for example in examples:
        shapes.extend(_documented_calls(example, function_name))
    if not shapes:
        return []
    documented = {repr(shape) for shape in shapes}
    corpus: list[tuple[tuple, dict]] = []
    attempts = 0
    while len(corpus) < count and attempts < count * 8:
        attempts += 1
        args, kwargs = shapes[attempts % len(shapes)]
        drawn = (tuple(_random_value(value, rng) for value in args),
                 {key: _random_value(value, rng) for key, value in kwargs.items()})
        if repr(drawn) in documented or repr(drawn) in {repr(c) for c in corpus}:
            continue
        corpus.append(drawn)
    return corpus


def observe(function: Any, args: tuple, kwargs: dict) -> tuple[str, Any]:
    try:
        value = function(*args, **kwargs)
    except Exception as error:  # noqa: BLE001 - an exception type is an observable
        return ("raise", type(error).__name__)
    return ("value", value)


def _same(left: tuple[str, Any], right: tuple[str, Any]) -> bool:
    if left[0] != right[0]:
        return False
    if left[0] == "raise":
        return left[1] == right[1]
    try:
        return bool(left[1] == right[1])
    except Exception:  # noqa: BLE001
        return repr(left[1]) == repr(right[1])


# --------------------------------------------------------------------------------------
# the experiment
# --------------------------------------------------------------------------------------


def audit_module(name: str, rng: random.Random) -> dict[str, Any]:
    module = importlib.import_module(name)
    if hasattr(module, "__path__"):
        raise ValueError(f"{name} is a package; this audit mutates one source file")
    tree = _source_tree(module)
    # the control is compiled from the ORIGINAL source so its line numbers are the ones the
    # AST analysis uses; an unparsed round trip renumbers every line and silently breaks the
    # branch-reachability cross-tab (measured: 0 spans "reached" on every function).
    control = _materialize(name, inspect.getsource(module), module.__file__)
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    guards: list[dict[str, Any]] = []
    functions: set[str] = set()

    for function_node in documented_functions(tree):
        fname = function_node.name
        original = getattr(module, fname, None)
        if original is None or not callable(original):
            skipped.append({"function": fname, "why": "not a callable module attribute"})
            continue
        all_examples = _doc_examples(function_node)
        examples = usable_examples(control, fname, all_examples)
        if not examples:
            skipped.append({"function": fname, "why": "no example runs on the unmutated round-trip"})
            continue
        if len(examples) < len(all_examples):
            skipped.append(
                {
                    "function": fname,
                    "why": f"{len(all_examples) - len(examples)} of {len(all_examples)} examples refused on the control",
                }
            )
        corpus = random_corpus(fname, examples, random.Random(rng.random()))
        if len(corpus) < 12:
            skipped.append({"function": fname, "why": "fewer than twelve drawable random inputs"})
            continue
        spans = branch_spans(function_node)
        example_lines = traced_lines(
            getattr(control, fname), lambda: _run_examples(control, fname, examples)
        )
        reached = [
            span for span in spans if any(span["start"] <= line <= span["end"] for line in example_lines)
        ]
        found = reach_guards(original, examples, spans, reached, corpus[:20])
        guards.append(
            {
                "function": fname,
                "witnessed_guards": found,
                "examples": len(examples),
                "branches": len(spans),
                "reached": len(reached),
                "untested_found": len(found),
                "untested": [
                    {"line": span["test_line"], "branch": span["branch"]}
                    for span in spans
                    if span not in reached
                ],
            }
        )
        expected = [observe(original, a, k) for a, k in corpus]
        draws = {size: rng.sample(range(len(corpus)), min(size, len(corpus))) for size in SAMPLE_SIZES}
        functions.add(fname)

        for mutation in candidate_mutations(function_node):
            try:
                mutated = _materialize(
                    name, ast.unparse(mutate_function(tree, fname, mutation)), module.__file__
                )
                mutant_function = getattr(mutated, fname)
                observed = [observe(mutant_function, a, k) for a, k in corpus]
            except Exception as error:  # noqa: BLE001 - a module that will not build is not a fault
                skipped.append({"function": fname, "why": f"mutant would not build: {type(error).__name__}"})
                continue
            differences = [i for i, got in enumerate(observed) if not _same(got, expected[i])]
            covering = covering_branch(function_node, mutation, spans)
            row: dict[str, Any] = {
                "in_branch": covering is not None,
                "branch_reached_by_guide": bool(covering is not None and covering in reached),
                "module": name,
                "function": fname,
                "mutation": mutation.label,
                "line": mutation.line,
                "separated": bool(differences),
                "guide_killed": _run_examples(mutated, fname, examples)["killed"],
                "examples": len(examples),
                "sample_kills": {
                    str(size): any(i in differences for i in draws[size]) for size in SAMPLE_SIZES
                },
            }
            if differences:
                where = differences[0]
                row["witness"] = {
                    "call": f"{fname}({', '.join(repr(a) for a in corpus[where][0])}"
                    + (", " if corpus[where][0] and corpus[where][1] else "")
                    + ", ".join(f"{k}={v!r}" for k, v in corpus[where][1].items())
                    + ")",
                    "expected": repr(expected[where]),
                    "mutant": repr(observed[where]),
                }
            rows.append(row)

    separated = sum(1 for r in rows if r["separated"])

    def tab(predicate) -> dict[str, int]:
        subset = [r for r in rows if r["separated"] and predicate(r)]
        return {"separated": len(subset), "guide_kills": sum(1 for r in subset if r["guide_killed"])}

    return {
        "module": name,
        "branches": {
            "guide_reached": tab(lambda r: r["in_branch"] and r["branch_reached_by_guide"]),
            "guide_untested": tab(lambda r: r["in_branch"] and not r["branch_reached_by_guide"]),
            "outside_any_branch": tab(lambda r: not r["in_branch"]),
        },
        "functions": sorted(functions),
        "mutants": len(rows),
        "separated": separated,
        "guide_kills": sum(1 for r in rows if r["separated"] and r["guide_killed"]),
        "sample_kills": {
            str(size): sum(1 for r in rows if r["separated"] and r["sample_kills"][str(size)])
            for size in SAMPLE_SIZES
        },
        "skipped": skipped,
        "guards": guards,
        "rows": rows,
    }


EMPTY_SAMPLE = {str(size): 0 for size in SAMPLE_SIZES}


def measure(modules: Sequence[str] | None = None, seed: int = 0) -> dict[str, Any]:
    names = list(
        modules
        or (
            "statistics",
            "difflib",
            "textwrap",
            "fractions",
            "enum",
            "calendar",
            "string",
            "json",
        )
    )
    started = time.time()
    audits: list[dict[str, Any]] = []
    for name in names:
        try:
            audits.append(audit_module(name, random.Random(seed)))
        except Exception as error:  # noqa: BLE001 - a module that cannot be audited is reported
            audits.append(
                {
                    "module": name,
                    "error": f"{type(error).__name__}: {error}",
                    "functions": [],
                    "mutants": 0,
                    "separated": 0,
                    "guide_kills": 0,
                    "sample_kills": dict(EMPTY_SAMPLE),
                    "branches": {"guide_reached": {"separated": 0, "guide_kills": 0},
                                 "guide_untested": {"separated": 0, "guide_kills": 0},
                                 "outside_any_branch": {"separated": 0, "guide_kills": 0}},
                    "skipped": [],
                    "guards": [],
                    "rows": [],
                }
            )
    separated = sum(a["separated"] for a in audits)
    tally = {
        "mutants": sum(a["mutants"] for a in audits),
        "separated": separated,
        "not_separated": sum(a["mutants"] for a in audits) - separated,
        "guide_kills": sum(a["guide_kills"] for a in audits),
        "sample_kills": {
            str(size): sum(a["sample_kills"][str(size)] for a in audits) for size in SAMPLE_SIZES
        },
    }
    tally["guards"] = {
        "functions": sum(len(a["guards"]) for a in audits),
        "branches": sum(g["branches"] for a in audits for g in a["guards"]),
        "reached": sum(g["reached"] for a in audits for g in a["guards"]),
    }
    tally["guards"]["untested"] = tally["guards"]["branches"] - tally["guards"]["reached"]
    tally["guards"]["witnessed"] = sum(g["untested_found"] for a in audits for g in a["guards"])
    tally["guards"]["unreached_share"] = (
        round(1 - tally["guards"]["reached"] / tally["guards"]["branches"], 4)
        if tally["guards"]["branches"]
        else None
    )
    tally["branches"] = {
        key: {
            "separated": sum(a["branches"][key]["separated"] for a in audits),
            "guide_kills": sum(a["branches"][key]["guide_kills"] for a in audits),
        }
        for key in ("guide_reached", "guide_untested", "outside_any_branch")
    }
    for key, value in tally["branches"].items():
        value["guide_detection_power"] = (
            round(value["guide_kills"] / value["separated"], 4) if value["separated"] else None
        )
    tally["guide_detection_power"] = round(tally["guide_kills"] / separated, 4) if separated else None
    tally["sample_detection_power"] = {
        size: (round(value / separated, 4) if separated else None)
        for size, value in tally["sample_kills"].items()
    }
    return {
        "seed": seed,
        "seconds": round(time.time() - started, 3),
        "modules": audits,
        "tally": tally,
        "verdict": verdict(tally),
    }


def verdict(tally: dict[str, Any]) -> dict[str, Any]:
    power = tally["guide_detection_power"]
    return {
        "P1_the_guide_example_can_refuse_a_mutant": tally["guide_kills"] > 0,
        "P2_more_than_half_of_separated_faults_escape_the_example": bool(power is not None and power < 0.5),
        "P3_ten_cases_beat_the_single_documented_example": tally["sample_kills"]["10"] > tally["guide_kills"],
        "P4_some_faults_escape_the_whole_corpus": tally["separated"] < tally["mutants"],
        "P5_faults_inside_branches_the_guide_never_enters_escape_more_often": (
            (tally["branches"]["guide_untested"]["guide_detection_power"] or 0)
            < (tally["branches"]["guide_reached"]["guide_detection_power"] or 1)
        ),
    }


def _print_summary(report: dict[str, Any]) -> None:
    tally = report["tally"]
    print(json.dumps({k: tally["mutants"] for k in ("mutants",)} | {"separated": tally["separated"],
                     "not_separated": tally["not_separated"], "guide_kills": tally["guide_kills"]}, indent=1))
    print(json.dumps({"guide": tally["guide_detection_power"], "samples": tally["sample_detection_power"]}, indent=1))
    print(json.dumps(report["verdict"], indent=1))
    print(json.dumps({"guards": tally["guards"], "branches": tally["branches"]}, indent=1))
    for audit in report["modules"]:
        if audit.get("error"):
            print(f"  {audit['module']:12s} ERROR {audit['error']}")
            continue
        print(
            f"  {audit['module']:12s} fns={len(audit['functions']):2d} mutants={audit['mutants']:3d} "
            f"separated={audit['separated']:3d} guide_kills={audit['guide_kills']:3d}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    parser.add_argument("--modules", nargs="*", default=None)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    report = measure(args.modules, args.seed)
    _print_summary(report)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"receipt: {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
