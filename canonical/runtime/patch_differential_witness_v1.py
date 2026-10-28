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
    c = owning_callable(source_text, lineno)
    if c["name"] is None or c["class"] is not None:
        return None, 0, c["why"] or "METHOD"
    return c["name"], len(c["params"]), None


def _positional(node: ast.FunctionDef) -> tuple[list[str] | None, str | None]:
    a = node.args
    if a.vararg or a.kwarg or a.kwonlyargs:
        return None, "VARIADIC_SIGNATURE"
    return [x.arg for x in [*a.posonlyargs, *a.args]], None


def owning_callable(source_text: str, lineno: int) -> dict[str, Any]:
    """The free function or the plain instance method that owns ``lineno``:
    {name, class, params (without self), ctor_params (methods), why}.  Static/class
    methods, properties, async, variadic and nested callables -> name None with why."""
    none = {"name": None, "class": None, "params": [], "ctor_params": None, "why": "NO_OWNING_FUNCTION"}
    tree = ast.parse(source_text)

    def inner_owner(node: ast.AST) -> bool:
        for inner in ast.walk(node):
            if inner is not node and isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                if inner.lineno <= lineno <= (inner.end_lineno or inner.lineno):
                    return True
        return False

    for node in tree.body:
        if not (node.lineno <= lineno <= (node.end_lineno or node.lineno)):
            continue
        if isinstance(node, ast.AsyncFunctionDef):
            return {**none, "why": "ASYNC_FUNCTION"}
        if isinstance(node, ast.FunctionDef):
            params, why = _positional(node)
            if params is None:
                return {**none, "why": why}
            if inner_owner(node):
                return {**none, "why": "NESTED_FUNCTION"}
            return {"name": node.name, "class": None, "params": params, "ctor_params": None, "why": None}
        if isinstance(node, ast.ClassDef):
            for m in node.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.lineno <= lineno <= (m.end_lineno or m.lineno):
                    if isinstance(m, ast.AsyncFunctionDef):
                        return {**none, "why": "ASYNC_METHOD"}
                    if m.decorator_list:
                        return {**none, "why": "DECORATED_METHOD"}
                    params, why = _positional(m)
                    if params is None:
                        return {**none, "why": why}
                    if not params or params[0] != "self":
                        return {**none, "why": "NO_SELF"}
                    if inner_owner(m):
                        return {**none, "why": "NESTED_FUNCTION"}
                    if m.name == "__init__":
                        return {**none, "why": "CONSTRUCTOR"}
                    init = next((x for x in node.body if isinstance(x, ast.FunctionDef) and x.name == "__init__"), None)
                    if init is None:
                        ctor: list[str] | None = []
                    else:
                        ctor, why = _positional(init)
                        if ctor is None or not ctor or ctor[0] != "self":
                            return {**none, "why": "CONSTRUCTOR_" + str(why or "NO_SELF")}
                        ctor = ctor[1:]
                    if node.bases or node.keywords:
                        return {**none, "why": "CLASS_WITH_BASES"}
                    return {"name": m.name, "class": node.name, "params": params[1:], "ctor_params": ctor, "why": None}
            return {**none, "why": "CLASS_BODY"}
    return none


def _literal(node: ast.AST) -> tuple[bool, Any]:
    try:
        v = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return False, None
    if _simple(v):
        return True, v
    return False, None


def _simple(v: Any, depth: int = 0) -> bool:
    if isinstance(v, (bool, int, float, str, type(None))):
        return True
    if isinstance(v, (list, tuple)) and depth < 2 and len(v) <= 50:
        return all(_simple(x, depth + 1) for x in v)
    return False


def _sequence_pool(seen: list[Any]) -> list[Any]:
    """Lists/tuples shaped like the ones the tests passed: empty, singletons, the
    tests' own values permuted/extended/shrunk, element types from the tests plus
    zero/negative/duplicate elements -- deterministic, no randomness."""
    kinds = {type(v) for v in seen if isinstance(v, (list, tuple))} or {list}
    elems: list[Any] = []
    for v in seen:
        if isinstance(v, (list, tuple)):
            for x in v:
                if not any(type(x) is type(y) and x == y for y in elems):
                    elems.append(x)
    etypes = {type(x) for x in elems} or {int}
    base: list[Any] = []
    if int in etypes:
        base += [0, 1, 2, -1, 3, 10]
    if float in etypes:
        base += [0.0, 0.5, -1.5, 2.0]
    if str in etypes:
        base += ["", "a", "b", "ab"]
    if bool in etypes:
        base += [True, False]
    if type(None) in etypes:
        base += [None]
    for x in elems:
        if not any(type(x) is type(y) and x == y for y in base):
            base.append(x)
    shapes: list[list[Any]] = [[]]
    shapes += [[x] for x in base[:6]]
    shapes += [[base[i], base[j]] for i in range(min(4, len(base))) for j in range(min(4, len(base))) if i != j][:8]
    for v in seen:
        if isinstance(v, (list, tuple)) and v:
            lv = list(v)
            shapes += [lv[::-1], lv + lv[:1], lv[1:], lv + [base[0]], [lv[0]] * (len(lv) + 1), sorted(lv, key=repr)]
    shapes += [base[:3], base[:5], (base[:3] + base[:3])]
    out: list[Any] = []
    for kind in sorted(kinds, key=lambda k: k.__name__):
        for sh in shapes:
            v = kind(sh)
            if not any(type(v) is type(y) and v == y for y in out):
                out.append(v)
    return out


def test_call_inputs(test_paths: Iterable[pathlib.Path], name: str, arity: int,
                     cls: str | None = None, n_ctor: int = 0) -> list[list[Any]]:
    """Argument tuples the tests pass to ``name`` -- the inputs the suite actually
    specifies.  For a method (``cls`` given) the form is `Cls(<lits>).name(<lits>)` and
    the row is the constructor's literals followed by the call's (flat)."""
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
            ctor_vals: list[Any] = []
            if cls is not None:
                recv = f.value if isinstance(f, ast.Attribute) else None
                if not (isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id == cls
                        and not recv.keywords and len(recv.args) == n_ctor):
                    continue
                cv = [_literal(a) for a in recv.args]
                if not all(ok for ok, _ in cv):
                    continue
                ctor_vals = [v for _, v in cv]
            vals = [_literal(a) for a in n.args]
            if all(ok for ok, _ in vals):
                row = ctor_vals + [v for _, v in vals]
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
        if list in types or tuple in types:
            pool += _sequence_pool(seen)
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


def probe_program(module_name: str, func: str, inputs: list[list[Any]], out_rel: str,
                  cls: str | None = None, n_ctor: int = 0) -> str:
    """Python source that imports ``module_name`` and writes one outcome per input to
    ``out_rel``; for a method each input is constructor literals + call literals and
    the outcome is the result followed by the instance's simple attributes."""
    if cls is None:
        get = "    f = getattr(importlib.import_module(" + repr(module_name) + "), " + repr(func) + ")\n"
        call = "            r = f(*args); rows.append(['R', repr(r)[:200]])\n"
    else:
        get = ("    C = getattr(importlib.import_module(" + repr(module_name) + "), " + repr(cls) + ")\n"
               "    f = lambda *a: (lambda inst: (getattr(inst, " + repr(func) + ")(*a[" + str(n_ctor) + ":]), "
               "sorted((k, repr(v)[:80]) for k, v in vars(inst).items() if isinstance(v, (bool, int, float, str, tuple, list, type(None))))))"
               "(C(*a[:" + str(n_ctor) + "]))\n")
        call = "            r, st = f(*args); rows.append(['R', repr(r)[:200], st])\n"
    return (
        "import importlib, json, os, sys\n"
        "sys.path.insert(0, os.getcwd())\n"
        "rows = []\n"
        "try:\n"
        + get +
        "except BaseException as exc:\n"
        "    f = None; rows.append(['IMPORT', type(exc).__name__])\n"
        "if f is not None:\n"
        "    for args in json.loads(" + repr(json.dumps(inputs)) + "):\n"
        "        try:\n"
        + call +
        "        except BaseException as exc:\n"
        "            rows.append(['E', type(exc).__name__])\n"
        "open(" + repr(out_rel) + ", 'w', encoding='utf-8').write(json.dumps(rows))\n"
    )


def edit_size(original_text: str, candidate_text: str) -> int:
    """Characters on changed lines, both sides: the smaller edit among behavioural equals."""
    import difflib
    a, b = original_text.splitlines(), candidate_text.splitlines()
    n = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            n += sum(len(x.strip()) for x in a[i1:i2]) + sum(len(x.strip()) for x in b[j1:j2])
    return n


def rank(original: list[Any] | None, per_candidate: list[tuple[int, list[Any] | None]],
         n_test_inputs: int, expected_reprs: list[str | None] | None = None,
         sizes: dict[int, int] | None = None) -> list[dict[str, Any]]:
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
        # the tests' literal, exactly: `12` is not `12.0` even though `==` accepts it
        inexact = 0
        for o, e in zip(outcomes[:n_test_inputs], expected_reprs or []):
            if e is not None and isinstance(o, list) and len(o) >= 2 and o[0] == "R" and o[1] != e:
                inexact += 1
        rows.append({"index": index, "delta_outside_tests": outside, "delta_on_tests": on_tests,
                     "inexact_on_tests": inexact, "edit_size": (sizes or {}).get(index, 0),
                     "grid_inputs": len(original) - n_test_inputs, "witness": "MEASURED"})
    # behavioural classes among the greens themselves: two candidates with the same
    # outcomes on every input are one behaviour; different classes with the same
    # delta are a TIE the suite cannot break -- said in the ledger, never hidden
    by_index = dict(per_candidate)
    classes: list[tuple[int, list[Any] | None]] = []
    first_of_class: dict[int, int] = {}
    for r in sorted(rows, key=lambda r: r["index"]):
        o = by_index.get(r["index"])
        for cid, rep in classes:
            if rep == o:
                r["behaviour_class"] = cid
                break
        else:
            classes.append((len(classes), o))
            r["behaviour_class"] = len(classes) - 1
            first_of_class[len(classes) - 1] = r["index"]

    def key(r: dict[str, Any]) -> tuple:
        if r["witness"] != "MEASURED":
            return (2, 0, 0, 0, 0, r["index"])
        # behaviour first (least change outside the tests, exact on their literals), then
        # search order -- the generator's own specificity ranking (`is None` before `not x`,
        # measured: both are one behaviour class on an int/None grid, and the smaller edit is
        # the less specific guard); edit_size is reported, not ranked on
        return (0 if r["delta_on_tests"] > 0 or n_test_inputs == 0 else 1, r["delta_outside_tests"],
                r["inexact_on_tests"], first_of_class[r["behaviour_class"]], 0, r["index"])
    rows.sort(key=key)
    measured = [r for r in rows if r["witness"] == "MEASURED"]
    if measured:
        top = key(measured[0])[:3]
        tied = {r["behaviour_class"] for r in measured if key(r)[:3] == top}
        for r in rows:
            r["tie_at_top"] = len(tied) > 1
    return rows


def witness(*, tree: pathlib.Path, target_rel: str, original_text: str, lineno: int,
            greens: list[tuple[int, str]], test_paths: list[pathlib.Path],
            run_program: Callable[[pathlib.Path, str, str], list[Any] | None],
            scratch: pathlib.Path, expected: list[tuple[list[Any], Any]] = ()) -> dict[str, Any]:
    """Rank ``greens`` [(index, candidate_text)] by behavioural delta.

    ``run_program(copy_root, program_source, out_rel)`` executes the probe in a
    copy whose target file already holds the version under test and returns
    the parsed outcome rows (or None).  Copy management is the caller's.
    """
    c = owning_callable(original_text, lineno)
    name, cls = c["name"], c["class"]
    if name is None:
        return {"status": "WITNESS_UNAVAILABLE:" + str(c["why"]), "ranking": [{"index": i, "witness": "UNAVAILABLE"} for i, _ in greens],
                "proves_correctness": False}
    arity = len(c["params"])
    n_ctor = len(c["ctor_params"] or []) if cls else 0
    module_name = target_rel[:-3].replace("/", ".") if target_rel.endswith(".py") else target_rel.replace("/", ".")
    if module_name.endswith(".__init__"):
        module_name = module_name[: -len(".__init__")]
    t_inputs = test_call_inputs(test_paths, name, arity, cls, n_ctor)
    inputs = t_inputs + [g for g in grid_inputs(t_inputs, arity + n_ctor) if g not in t_inputs]
    out_rel = ".brain_diagnose/witness.json"
    program = probe_program(module_name, name, inputs, out_rel, cls, n_ctor)
    import shutil
    base = scratch / "witness"
    shutil.rmtree(base, ignore_errors=True)
    shutil.copytree(tree, base, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    touched: dict[str, str] = {}      # patch sets may span files: every file written is restored
    for _, text in greens:
        for rel in (text if isinstance(text, dict) else {target_rel: text}):
            touched.setdefault(rel, (tree / rel).read_text(encoding="utf-8"))
    touched.setdefault(target_rel, original_text)

    def run_version(text: Any) -> list[Any] | None:
        files = dict(text) if isinstance(text, dict) else {target_rel: text}
        for rel, t in touched.items():
            (base / rel).write_text(files.get(rel, t), encoding="utf-8")
            shutil.rmtree((base / rel).parent / "__pycache__", ignore_errors=True)
        return run_program(base, program, out_rel)

    def size(text: Any) -> int:
        files = dict(text) if isinstance(text, dict) else {target_rel: text}
        return sum(edit_size(touched[rel], t) for rel, t in files.items())

    try:
        original = run_version(original_text)
        per = [(i, run_version(text)) for i, text in greens]
    finally:
        shutil.rmtree(base, ignore_errors=True)
    exp_map = {json.dumps(list(a), default=repr): repr(e)[:200] for a, e in expected}
    expected_reprs = [exp_map.get(json.dumps(row, default=repr)) for row in t_inputs]
    ranking = rank(original, per, len(t_inputs), expected_reprs,
                   {i: size(text) for i, text in greens})
    return {"status": "MEASURED" if original is not None else "WITNESS_UNAVAILABLE:ORIGINAL_PROBE_FAILED",
            "function": name, "class": cls, "module": module_name, "test_inputs": len(t_inputs), "grid_inputs": len(inputs) - len(t_inputs),
            "behaviour_classes": len({r.get("behaviour_class") for r in ranking if "behaviour_class" in r}),
            "tie_at_top": any(r.get("tie_at_top") for r in ranking),
            "ranking": ranking, "proves_correctness": False}
