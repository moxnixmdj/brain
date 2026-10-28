# PROJECT_BRAIN
"""Differential witness for candidate patches: how much behaviour did each
green patch change, beyond what the failing tests demanded?

Measured problem (2026-10-28): ``return w * h if w <= 0 else 0`` with a test
``area(3, 4) == 12`` was "repaired" to ``w != 0`` -- green, full suite green,
wrong.  ``w > 0`` is also green.  The suite cannot tell them apart, so a loop
that ships the first green patch ships whichever the generator emitted first.

What the literature does (Xiong et al. 2018 PATCH-SIM; DiffTGen; Opad): a
correct patch changes the program's behaviour on the failing inputs and as
little as possible elsewhere.  That is measurable without an oracle: run the
original and each candidate on the same inputs and count the inputs where they
disagree.  Fewer disagreements = less collateral change = preferred.  This is a
RANKING witness, never proof -- ``proves_correctness`` is False.

Inputs are the tests' own calls to the function (literal arguments found in the
test files) plus a deterministic grid over the literal types seen there (ints:
-7..100, floats, strings, bools), capped and seeded.  Each program runs in a
per-candidate copy of the tree under the caller's runner (confined when the
host can), imports the module by its real dotted name, and prints one JSON
line; the comparison happens here.

Only free functions are witnessed (methods and nested functions report
WITNESS_UNAVAILABLE:<why>); the loop then falls back to search order, and the
ledger says so.
"""
from __future__ import annotations

import ast
import itertools
import json
import pathlib
import random
from typing import Any, Callable, Iterable

INT_GRID = [-7, -2, -1, 0, 1, 2, 3, 7, 10, 100]
FLOAT_GRID = [-1.5, -0.5, 0.0, 0.5, 1.5, 2.0]
STR_GRID = ["", "a", "ab", "hello", " x "]
BOOL_GRID = [True, False]
NONE_GRID = [None]
MAX_INPUTS = 120


def owning_function(source_text: str, lineno: int) -> tuple[str | None, int, str | None]:
    """(name, arity, why_not) of the free function that owns ``lineno``."""
    tree = ast.parse(source_text)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= lineno <= (node.end_lineno or node.lineno):
                if isinstance(node, ast.AsyncFunctionDef):
                    return None, 0, "ASYNC_FUNCTION"
                a = node.args
                if a.vararg or a.kwarg or a.kwonlyargs:
                    return None, 0, "VARIADIC_SIGNATURE"
                for inner in ast.walk(node):
                    if inner is not node and isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                        if inner.lineno <= lineno <= (inner.end_lineno or inner.lineno):
                            return None, 0, "NESTED_FUNCTION"
                return node.name, len(a.posonlyargs) + len(a.args), None
        elif isinstance(node, ast.ClassDef) and node.lineno <= lineno <= (node.end_lineno or node.lineno):
            return None, 0, "METHOD"
    return None, 0, "NO_OWNING_FUNCTION"


def _literal(node: ast.AST) -> tuple[bool, Any]:
    try:
        v = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return False, None
    if isinstance(v, (bool, int, float, str, type(None))):
        return True, v
    return False, None


def test_call_inputs(test_paths: Iterable[pathlib.Path], name: str, arity: int) -> list[list[Any]]:
    """Argument tuples the tests pass to ``name`` -- the inputs the suite actually specifies."""
    out: list[list[Any]] = []
    for p in test_paths:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call) or n.keywords:
                continue
            f = n.func
            fname = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if fname != name or len(n.args) != arity:
                continue
            vals = [_literal(a) for a in n.args]
            if all(ok for ok, _ in vals):
                row = [v for _, v in vals]
                if row not in out:
                    out.append(row)
    return out


def grid_inputs(test_inputs: list[list[Any]], arity: int, cap: int = MAX_INPUTS) -> list[list[Any]]:
    """Deterministic grid over the literal types the tests used per position."""
    if arity == 0:
        return [[]]
    per_pos: list[list[Any]] = []
    for i in range(arity):
        seen = [row[i] for row in test_inputs] if test_inputs else []
        types = {type(v) for v in seen} or {int}
        pool: list[Any] = []
        if bool in types:
            pool += BOOL_GRID
        if int in types:
            pool += INT_GRID
        if float in types:
            pool += FLOAT_GRID
        if str in types:
            pool += STR_GRID
        if type(None) in types:
            pool += NONE_GRID
        for v in seen:
            if not any(type(v) is type(x) and v == x for x in pool):
                pool.append(v)
        per_pos.append(pool)
    total = 1
    for pool in per_pos:
        total *= len(pool)
    if total <= cap:
        return [list(t) for t in itertools.product(*per_pos)]
    rng = random.Random(1729)
    out: list[list[Any]] = []
    seen_keys: set[str] = set()
    while len(out) < cap:
        row = [rng.choice(pool) for pool in per_pos]
        k = json.dumps(row, sort_keys=True, default=repr)
        if k not in seen_keys:
            seen_keys.add(k)
            out.append(row)
    return out


def probe_program(module_name: str, func: str, inputs: list[list[Any]], out_rel: str) -> str:
    """Python source that imports ``module_name`` and writes one outcome per input to ``out_rel``."""
    return (
        "import importlib, json, os, sys\n"
        "sys.path.insert(0, os.getcwd())\n"
        "rows = []\n"
        "try:\n"
        "    f = getattr(importlib.import_module(" + repr(module_name) + "), " + repr(func) + ")\n"
        "except BaseException as exc:\n"
        "    f = None; rows.append(['IMPORT', type(exc).__name__])\n"
        "if f is not None:\n"
        "    for args in json.loads(" + repr(json.dumps(inputs)) + "):\n"
        "        try:\n"
        "            r = f(*args); rows.append(['R', repr(r)[:200]])\n"
        "        except BaseException as exc:\n"
        "            rows.append(['E', type(exc).__name__])\n"
        "open(" + repr(out_rel) + ", 'w', encoding='utf-8').write(json.dumps(rows))\n"
    )


def rank(original: list[Any] | None, per_candidate: list[tuple[int, list[Any] | None]],
         n_test_inputs: int) -> list[dict[str, Any]]:
    """Order candidates by behavioural delta vs the original outside the tests' own inputs.

    ``original``/candidate outcome lists align with the inputs: the first
    ``n_test_inputs`` are the suite's calls, the rest the grid.  A candidate that
    does not differ from the original on at least one test input did not change
    what the failing test saw (its green came from elsewhere) and ranks last.
    """
    rows = []
    for index, outcomes in per_candidate:
        if original is None or outcomes is None or len(outcomes) != len(original):
            rows.append({"index": index, "delta_outside_tests": None, "delta_on_tests": None,
                         "witness": "UNAVAILABLE"})
            continue
        on_tests = sum(1 for a, b in zip(original[:n_test_inputs], outcomes[:n_test_inputs]) if a != b)
        outside = sum(1 for a, b in zip(original[n_test_inputs:], outcomes[n_test_inputs:]) if a != b)
        rows.append({"index": index, "delta_outside_tests": outside, "delta_on_tests": on_tests,
                     "grid_inputs": len(original) - n_test_inputs, "witness": "MEASURED"})
    def key(r: dict[str, Any]) -> tuple:
        if r["witness"] != "MEASURED":
            return (2, 0, r["index"])
        return (0 if r["delta_on_tests"] > 0 or n_test_inputs == 0 else 1, r["delta_outside_tests"], r["index"])
    rows.sort(key=key)
    return rows


def witness(*, tree: pathlib.Path, target_rel: str, original_text: str, lineno: int,
            greens: list[tuple[int, str]], test_paths: list[pathlib.Path],
            run_program: Callable[[pathlib.Path, str, str], list[Any] | None],
            scratch: pathlib.Path) -> dict[str, Any]:
    """Rank ``greens`` [(index, candidate_text)] by behavioural delta.

    ``run_program(copy_root, program_source, out_rel)`` executes the probe in a
    copy whose target file already holds the version under test and returns
    the parsed outcome rows (or None).  Copy management is the caller's.
    """
    name, arity, why = owning_function(original_text, lineno)
    if name is None:
        return {"status": "WITNESS_UNAVAILABLE:" + str(why), "ranking": [{"index": i, "witness": "UNAVAILABLE"} for i, _ in greens],
                "proves_correctness": False}
    module_name = target_rel[:-3].replace("/", ".") if target_rel.endswith(".py") else target_rel.replace("/", ".")
    if module_name.endswith(".__init__"):
        module_name = module_name[: -len(".__init__")]
    t_inputs = test_call_inputs(test_paths, name, arity)
    inputs = t_inputs + [g for g in grid_inputs(t_inputs, arity) if g not in t_inputs]
    out_rel = ".brain_diagnose/witness.json"
    program = probe_program(module_name, name, inputs, out_rel)
    import shutil
    base = scratch / "witness"
    shutil.rmtree(base, ignore_errors=True)
    shutil.copytree(tree, base, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    target = base / target_rel
    cache = target.parent / "__pycache__"

    def run_version(text: str) -> list[Any] | None:
        target.write_text(text, encoding="utf-8")
        shutil.rmtree(cache, ignore_errors=True)
        return run_program(base, program, out_rel)

    try:
        original = run_version(original_text)
        per = [(i, run_version(text)) for i, text in greens]
    finally:
        shutil.rmtree(base, ignore_errors=True)
    ranking = rank(original, per, len(t_inputs))
    return {"status": "MEASURED" if original is not None else "WITNESS_UNAVAILABLE:ORIGINAL_PROBE_FAILED",
            "function": name, "module": module_name, "test_inputs": len(t_inputs), "grid_inputs": len(inputs) - len(t_inputs),
            "ranking": ranking, "proves_correctness": False}
