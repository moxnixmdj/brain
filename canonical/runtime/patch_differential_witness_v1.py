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
import re
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


POST_RE = re.compile(r"^\s*(?:-\s*)?post(?:condition)?\s*:\s*(.+)$", re.I)
PROPERTY_EXAMPLES = 60


def postconditions(source_text: str, name: str, cls: str | None = None) -> list[str]:
    """``post: <expr>`` lines of the owning callable's docstring -- the same contract
    notation evidence_oracle_hypothesis_v1 checks; ``_``/``result`` is the return value,
    parameters are bound by name.  A stated contract is the third oracle beside the
    suite and the behavioural delta."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            doc = ast.get_docstring(node) or ""
            posts = [m.group(1).strip() for m in (POST_RE.match(ln) for ln in doc.splitlines()) if m]
            out = []
            for pexpr in posts:
                try:
                    ast.parse(pexpr, mode="eval")
                    out.append(pexpr)
                except SyntaxError:
                    continue
            if out:
                return out
    return []


def _strategy(seen: list[Any]):
    from hypothesis import strategies as st
    types = {type(v) for v in seen} or {int}
    parts = []
    if bool in types:
        parts.append(st.booleans())
    if int in types:
        parts.append(st.integers(min_value=-10 ** 6, max_value=10 ** 6))
    if float in types:
        parts.append(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False))
    if str in types:
        parts.append(st.text(max_size=8))
    if type(None) in types:
        parts.append(st.none())
    if list in types or tuple in types:
        elems = [x for v in seen if isinstance(v, (list, tuple)) for x in v]
        parts.append(st.lists(_strategy(elems) if elems else st.integers(-100, 100), max_size=8))
    return st.one_of(*parts) if len(parts) > 1 else parts[0]


def property_inputs(test_inputs: list[list[Any]], arity: int, n: int = PROPERTY_EXAMPLES) -> tuple[list[list[Any]], str]:
    """``n`` inputs drawn by Hypothesis from strategies shaped like the tests' literals per
    position (type-directed; negative, zero, large, empty, long, unicode -- what a hand
    grid misses), deterministic (derandomize) so a rerun ranks identically.  (rows, status)."""
    if arity == 0 or n <= 0:
        return [], "NOT_NEEDED"
    try:
        from hypothesis import HealthCheck, Phase, given, settings, strategies as st
    except Exception as exc:  # noqa: BLE001 - optional: the grid alone remains
        return [], "HYPOTHESIS_UNAVAILABLE:" + type(exc).__name__
    try:
        per_pos = [_strategy([row[i] for row in test_inputs] if test_inputs else []) for i in range(arity)]
        drawn: list[list[Any]] = []

        @settings(max_examples=n, database=None, derandomize=True, deadline=None,
                  phases=[Phase.generate], suppress_health_check=list(HealthCheck))
        @given(st.tuples(*per_pos))
        def draw(values):
            drawn.append([list(v) if isinstance(v, tuple) else v for v in values])

        draw()
    except Exception as exc:  # noqa: BLE001
        return [], "HYPOTHESIS_FAILED:" + type(exc).__name__
    out, seen = [], set()
    for row in drawn:
        k = json.dumps(row, sort_keys=True, default=repr)
        if k not in seen:
            seen.add(k)
            out.append(row)
    return out, "MEASURED"


def probe_program(module_name: str, func: str, inputs: list[list[Any]], out_rel: str,
                  cls: str | None = None, n_ctor: int = 0, params: list[str] | None = None,
                  posts: list[str] | None = None, per_input_s: float = 0.5, n_test_inputs: int = 0,
                  total_budget_s: float = 10.0) -> str:
    """Python source that imports ``module_name`` and writes one outcome per input to
    ``out_rel``; for a method each input is constructor literals + call literals and
    the outcome is the result followed by the instance's simple attributes.  With
    ``posts`` (docstring postconditions) a row whose result violates one -- or on which
    a postcondition cannot be evaluated -- is tagged 'R!' instead of 'R'.  Every call
    runs under a ``per_input_s`` alarm: an input the version loops on is the row
    ['E', 'Timeout'] (measured: find_first_in_sorted's defect loops on absent keys and
    the witness waited 60 s per version)."""
    if cls is None:
        get = ("    MOD = importlib.import_module(" + repr(module_name) + ")\n"
               "    f = getattr(MOD, " + repr(func) + ")\n")
        call = "            r = f(*args); rows.append([_tag(args, r), repr(r)[:200]])\n"
    else:
        get = ("    MOD = importlib.import_module(" + repr(module_name) + ")\n"
               "    C = getattr(MOD, " + repr(cls) + ")\n"
               "    f = lambda *a: (lambda inst: (getattr(inst, " + repr(func) + ")(*a[" + str(n_ctor) + ":]), "
               "sorted((k, repr(v)[:80]) for k, v in vars(inst).items() if isinstance(v, (bool, int, float, str, tuple, list, type(None))))))"
               "(C(*a[:" + str(n_ctor) + "]))\n")
        call = "            r, st = f(*args); rows.append([_tag(args[" + str(n_ctor) + ":], r), repr(r)[:200], st])\n"
    return (
        "import importlib, json, os, signal, sys\n"
        "sys.path.insert(0, os.getcwd())\n"
        "rows = []\n"
        "class _T(BaseException):\n"
        "    pass\n"
        "def _alarm(*a):\n"
        "    raise _T()\n"
        "signal.signal(signal.SIGALRM, _alarm)\n"
        "PER = " + repr(float(per_input_s)) + "\n"
        "POSTS = " + repr(list(posts or [])) + "\n"
        "PARAMS = " + repr(list(params or [])) + "\n"
        "SAFE = {'abs': abs, 'min': min, 'max': max, 'len': len, 'sum': sum, 'int': int, 'float': float, 'bool': bool,\n"
        "        'str': str, 'list': list, 'tuple': tuple, 'all': all, 'any': any, 'sorted': sorted, 'isinstance': isinstance,\n"
        "        'round': round, 'set': set, 'dict': dict, 'range': range, 'type': type}\n"
        "MOD = None\n"
        "def _tag(args, r):\n"
        "    if not POSTS:\n"
        "        return 'R'\n"
        "    # the module's own names are in scope, so a contract can be metamorphic:\n"
        "    # `post: _ == area(h, w)` calls the version under probe\n"
        "    g = dict(vars(MOD)) if MOD is not None else {}\n"
        "    g.update(SAFE); g['__builtins__'] = {}\n"
        "    env = dict(zip(PARAMS, args)); env.update({'_': r, 'result': r, '__return__': r})\n"
        "    for p in POSTS:\n"
        "        try:\n"
        "            if not bool(eval(p, g, env)):\n"
        "                return 'R!'\n"
        "        except BaseException:\n"
        "            return 'R!'\n"
        "    return 'R'\n"
        "try:\n"
        + get +
        "except BaseException as exc:\n"
        "    f = None; rows.append(['IMPORT', type(exc).__name__])\n"
        "import time as _time\n"
        "N_TEST = " + repr(int(n_test_inputs)) + "\n"
        "BUDGET = " + repr(float(total_budget_s)) + "\n"
        "if f is not None:\n"
        "    _start = _time.monotonic(); slowest = 0.0; per = PER\n"
        "    for k, args in enumerate(json.loads(" + repr(json.dumps(inputs)) + ")):\n"
        "        if k == N_TEST and N_TEST > 0:\n"
        "            # the budget per probe input is measured on the tests' own inputs: 20x the\n"
        "            # slowest of them (bounded) -- an input the version loops on costs that, not PER\n"
        "            per = max(0.02, min(PER, 20.0 * slowest))\n"
        "        if _time.monotonic() - _start > BUDGET:\n"
        "            rows.append(['E', 'Budget']); continue\n"
        "        t0 = _time.monotonic()\n"
        "        signal.setitimer(signal.ITIMER_REAL, per)\n"
        "        try:\n"
        + call +
        "        except _T:\n"
        "            rows.append(['E', 'Timeout'])\n"
        "        except BaseException as exc:\n"
        "            rows.append(['E', type(exc).__name__])\n"
        "        finally:\n"
        "            signal.setitimer(signal.ITIMER_REAL, 0)\n"
        "        slowest = max(slowest, _time.monotonic() - t0)\n"
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


def _unknown(row: Any) -> bool:
    """A probe row that says nothing about the version's answer: it looped or the budget ran out."""
    return isinstance(row, list) and len(row) == 2 and row[0] == "E" and row[1] in ("Timeout", "Budget")


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
        # an input the original looped on (or ran out of budget for) is not a behaviour
        # to preserve: it is excluded from the outside delta, so a candidate that
        # terminates there is not penalised against one that keeps the hang
        # (measured: find_first_in_sorted chose `hi = x % len(arr)` -- same hangs as the
        # original on absent keys -- over `lo < hi`, which terminates)
        outside = sum(1 for a, b in zip(original[n_test_inputs:], outcomes[n_test_inputs:])
                      if a != b and not _unknown(a))
        # ... and the candidate's own hangs count as behaviour it introduced
        hangs = sum(1 for a, b in zip(original, outcomes) if _unknown(b) and not _unknown(a))
        # a hang of the original that the candidate still has: the weakest tiebreak,
        # after everything the tests and the contract say
        hangs_kept = sum(1 for a, b in zip(original, outcomes) if _unknown(a) and _unknown(b))
        # the tests' literal, exactly: `12` is not `12.0` even though `==` accepts it
        inexact = 0
        for o, e in zip(outcomes[:n_test_inputs], expected_reprs or []):
            if e is not None and isinstance(o, list) and len(o) >= 2 and o[0] in ("R", "R!") and o[1] != e:
                inexact += 1
        # a stated postcondition violated (any input), and inputs the original answered
        # that the candidate turns into an exception: both before the plain delta
        posts_broken = sum(1 for o in outcomes if isinstance(o, list) and o and o[0] == "R!")
        # ... and the violations the candidate introduces: inputs on which the original
        # kept the contract and the candidate breaks it (the original's own violations
        # are the contract's quarrel with the original, not with the patch)
        posts_new = 0
        counterexample = None
        for k, (a, b) in enumerate(zip(original, outcomes)):
            if isinstance(b, list) and b and b[0] == "R!" and not (isinstance(a, list) and a and a[0] == "R!"):
                posts_new += 1
                if counterexample is None:
                    counterexample = {"input_index": k, "result": b[1:], "original": a}
        new_exc = hangs + sum(1 for a, b in zip(original, outcomes)
                              if isinstance(a, list) and isinstance(b, list) and a and b and a[0] != "E"
                              and b[0] == "E" and not _unknown(b))
        rows.append({"index": index, "delta_outside_tests": outside, "delta_on_tests": on_tests,
                     "inexact_on_tests": inexact, "postcondition_violations": posts_broken,
                     "new_postcondition_violations": posts_new, "contract_counterexample": counterexample,
                     "new_exceptions": new_exc,
                     "hangs_kept": hangs_kept,
                     "edit_size": (sizes or {}).get(index, 0),
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
            return (2, 0, 0, 0, 0, 0, 0, r["index"])
        # stated contract first, then crashes the candidate introduces, then behaviour
        # (least change outside the tests, exact on their literals), then search order --
        # the generator's own specificity ranking (`is None` before `not x`, measured: both
        # are one behaviour class on an int/None grid, and the smaller edit is the less
        # specific guard); edit_size is reported, not ranked on
        return (0 if r["delta_on_tests"] > 0 or n_test_inputs == 0 else 1, r["postcondition_violations"],
                r["new_exceptions"], r["delta_outside_tests"], r["inexact_on_tests"], r.get("hangs_kept", 0),
                first_of_class[r["behaviour_class"]], 0, r["index"])
    rows.sort(key=key)
    measured = [r for r in rows if r["witness"] == "MEASURED"]
    if measured:
        # a TIE: another behaviour class equal on the contract, the new exceptions and
        # exactness, and within noise on the delta (one or two probe inputs out of a
        # hundred decide nothing); the ranking still orders them, the flag says so
        top = measured[0]
        n_out = max(1, len(original) - n_test_inputs)
        slack = max(1, int(0.05 * n_out))
        tied = {r["behaviour_class"] for r in measured
                if key(r)[:3] == key(top)[:3] and r["inexact_on_tests"] == top["inexact_on_tests"]
                and r.get("hangs_kept", 0) == top.get("hangs_kept", 0)
                and abs(r["delta_outside_tests"] - top["delta_outside_tests"]) <= slack}
        for r in rows:
            r["tie_at_top"] = len(tied) > 1
            r["tied_with_top"] = r["witness"] == "MEASURED" and r["behaviour_class"] in tied
    return rows


def _call_text(name: str, cls: str | None, n_ctor: int, row: list[Any]) -> str:
    """`f(1, 2)` / `Cls(3).m(1)` for one probe input, as a test would spell it."""
    args = [repr(a) for a in row]
    if cls:
        return cls + "(" + ", ".join(args[:n_ctor]) + ")." + name + "(" + ", ".join(args[n_ctor:]) + ")"
    return name + "(" + ", ".join(args) + ")"


def witness(*, tree: pathlib.Path, target_rel: str, original_text: str, lineno: int,
            greens: list[tuple[int, str]], test_paths: list[pathlib.Path],
            run_program: Callable[[pathlib.Path, str, str], list[Any] | None],
            scratch: pathlib.Path, expected: list[tuple[list[Any], Any]] = (),
            property_examples: int = PROPERTY_EXAMPLES) -> dict[str, Any]:
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
    prop_rows, prop_status = property_inputs(t_inputs, arity + n_ctor, property_examples)
    n_grid = len(inputs) - len(t_inputs)
    inputs += [g for g in prop_rows if g not in inputs]
    posts = postconditions(original_text, name, cls)
    out_rel = ".brain_diagnose/witness.json"
    program = probe_program(module_name, name, inputs, out_rel, cls, n_ctor, params=list(c["params"]), posts=posts,
                            n_test_inputs=len(t_inputs))
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
    # a tie the suite cannot break is also the test that would break it: the probe
    # inputs on which the tied behaviours differ, with each behaviour's answer, so
    # the caller (or the user) can write the assertion that decides -- the one
    # thing an under-specified suite is missing
    for r in ranking:
        cx = r.get("contract_counterexample")
        if cx and cx.get("input_index") is not None and cx["input_index"] < len(inputs):
            cx["call"] = _call_text(name, cls, n_ctor, inputs[cx["input_index"]])
    distinguishing: list[dict[str, Any]] = []
    if ranking and ranking[0].get("tie_at_top"):
        by_index = dict(per)
        reps = []
        seen_classes: set[int] = set()
        for r in ranking:
            if r.get("tied_with_top") and r.get("behaviour_class") not in seen_classes:
                seen_classes.add(r["behaviour_class"])
                reps.append(r["index"])
        for k in range(len(t_inputs), len(inputs)):
            outs = {i: (by_index.get(i) or [None] * len(inputs))[k] for i in reps}
            if len({json.dumps(o, default=repr) for o in outs.values()}) > 1:
                distinguishing.append({"input": inputs[k], "call": _call_text(name, cls, n_ctor, inputs[k]),
                                       "outcomes": {str(i): o for i, o in outs.items()}})
            if len(distinguishing) >= 3:
                break
    return {"status": "MEASURED" if original is not None else "WITNESS_UNAVAILABLE:ORIGINAL_PROBE_FAILED",
            "distinguishing_inputs": distinguishing,
            "function": name, "class": cls, "module": module_name, "test_inputs": len(t_inputs), "grid_inputs": n_grid,
            "property_inputs": len(inputs) - len(t_inputs) - n_grid, "hypothesis": prop_status,
            "postconditions": posts,
            "original_postcondition_violations": sum(1 for o in (original or []) if isinstance(o, list) and o and o[0] == "R!"),
            "behaviour_classes": len({r.get("behaviour_class") for r in ranking if "behaviour_class" in r}),
            "tie_at_top": any(r.get("tie_at_top") for r in ranking),
            "ranking": ranking, "proves_correctness": False}
