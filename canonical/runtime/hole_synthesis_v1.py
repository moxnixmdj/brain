# PROJECT_BRAIN
"""One-hole sketch synthesis inside a function (SKETCH, Solar-Lezama 2008; the
staged condition synthesis of SPR/Prophet, Long & Rinard 2015 -- nothing new).

The returned-expression synthesis in expression_synthesis_v1 needs no execution:
it maps parameters to the expected value.  Most faults are not on the return line.
Here the HOLE is any expression on the suspicious line inside the owning free
function -- an assignment's right-hand side, an augmented assignment, a condition
(`if`/`elif`/`while`), a return value -- and the fix is the function, run on the
tests' own inputs, agreeing with the tests' expected outputs.

Mechanism (runs CONFINED: it executes the user's module):
  1. run the function once per example under a line tracer and snapshot its
     locals the first time control reaches the hole line (what is in scope there);
  2. enumerate expressions over those names and the function's own constants,
     smallest first, one representative per output vector on the snapshots
     (observational equivalence); conditions enumerate comparisons too;
  3. for each distinct expression, splice it into the hole, recompile the
     function in the module's namespace and run every example (short itimer);
     keep the ones that agree with all expected outputs.

Bounds: size <= 3 operators, enumeration/wall-clock caps, per-call itimer, one
hole at a time.  >= 2 examples required; the result is a CANDIDATE list for the
judge, the witness and the full-suite gate, never a verdict.  This module is
import-free so its own source can be shipped into the confined interpreter.
"""
from __future__ import annotations

import ast
import itertools
import json
import time
from typing import Any

BINOPS: list[tuple[str, Any]] = [
    ("+", lambda a, b: a + b), ("-", lambda a, b: a - b), ("*", lambda a, b: a * b),
    ("//", lambda a, b: a // b), ("%", lambda a, b: a % b), ("/", lambda a, b: a / b),
]
CMPOPS: list[tuple[str, Any]] = [
    ("<", lambda a, b: a < b), ("<=", lambda a, b: a <= b), ("==", lambda a, b: a == b),
    ("!=", lambda a, b: a != b), (">", lambda a, b: a > b), (">=", lambda a, b: a >= b),
]
MAX_ABS = 10 ** 9
SIMPLE = (bool, int, float, str, tuple, list, type(None))


def _ok(v: Any) -> bool:
    if isinstance(v, bool):
        return True
    if isinstance(v, int):
        return abs(v) <= MAX_ABS
    if isinstance(v, float):
        return v == v and abs(v) <= MAX_ABS
    return isinstance(v, (str, tuple, list, type(None))) and (not hasattr(v, "__len__") or len(v) <= 1000)


def _key(outs: tuple) -> tuple:
    return tuple((type(v).__name__, repr(v)) for v in outs)


def enumerate_distinct(names: list[str], envs: list[dict[str, Any]], constants: list[Any], *,
                       max_size: int = 3, budget_s: float = 1.5, max_enum: int = 60000,
                       booleans: bool = False, original: tuple | None = None) -> tuple[list[tuple[str, int, int]], int, str]:
    """One expression per output vector on ``envs``, in (size, consts) order.
    Returns ([(src, size, consts)], enumerated, stop) -- pure, executes no user code."""
    t0 = time.monotonic()
    by_size: dict[int, list[tuple[str, int, int, frozenset, tuple]]] = {0: []}
    seen: set[tuple] = set()
    order: list[tuple[str, int, int]] = []

    def add(src: str, size: int, consts: int, params: frozenset, outs: tuple) -> None:
        k = _key(outs)
        if k in seen:
            return
        seen.add(k)
        by_size.setdefault(size, []).append((src, size, consts, params, outs))
        order.append((src, size, consts))

    for name in names:
        add(name, 0, 0, frozenset([name]), tuple(env[name] for env in envs))
    consts: list[Any] = []
    for c in [0, 1, 2, *constants]:
        if isinstance(c, (int, float)) and not isinstance(c, bool) and c not in consts:
            consts.append(c)
    for c in consts:
        add(repr(c), 0, 1, frozenset(), tuple(c for _ in envs))
    for src, size, cn, params, outs in list(by_size[0]):
        for fname, fn in (("len", len), ("abs", abs)):
            try:
                o = tuple(fn(v) for v in outs)
            except Exception:
                continue
            if all(_ok(v) for v in o):
                add(fname + "(" + src + ")", 1, cn, params, o)
    enum = 0
    stop = "EXHAUSTED"
    for size in range(1, max_size + 1):
        for ls in range(0, size):
            rs = size - 1 - ls
            for a, b in itertools.product(list(by_size.get(ls, [])), list(by_size.get(rs, []))):
                if a[2] and b[2] and not (a[3] or b[3]):
                    continue                       # constant folding is not synthesis
                for sym, fn in BINOPS:
                    enum += 1
                    if enum > max_enum or time.monotonic() - t0 > budget_s:
                        return _finish(order, by_size, envs, booleans, enum, "BUDGET", original)
                    try:
                        o = tuple(fn(x, y) for x, y in zip(a[4], b[4]))
                    except Exception:
                        continue
                    if not all(_ok(v) for v in o):
                        continue
                    add("(" + a[0] + " " + sym + " " + b[0] + ")", size, a[2] + b[2], a[3] | b[3], o)
    return _finish(order, by_size, envs, booleans, enum, stop, original)


def _finish(order, by_size, envs, booleans, enum, stop, original=None, per_vector=3):
    if not booleans:
        return order, enum, stop
    # conditions, in SPR/Prophet's staged order: the ORIGINAL condition loosened or
    # tightened by one comparison first (`orig or C`, `orig and C`), then a comparison
    # alone, then two comparisons joined.  Truth vectors on a few examples collapse to
    # 2^n classes, so several representatives per vector are kept (bounded) and the
    # judge, the differential witness and the gate decide between them.
    terminals = list(by_size.get(0, []))
    lefts = [e for e in terminals if e[3]] + [e for e in by_size.get(1, []) if e[3]][:60]
    per: dict[tuple, int] = {}
    cmps: list[tuple[str, int, int, tuple]] = []
    for a, b in itertools.product(lefts, terminals):
        if a[0] == b[0]:
            continue
        for sym, fn in CMPOPS:
            enum += 1
            try:
                o = tuple(bool(fn(x, y)) for x, y in zip(a[4], b[4]))
            except Exception:
                continue
            if len(set(o)) < 2 and len(envs) > 1:
                continue                        # a constant truth value is not a condition
            cmps.append((a[0] + " " + sym + " " + b[0], a[1] + b[1] + 1, a[2] + b[2], o))
    cmps.sort(key=lambda e: (e[1], e[2], len(e[0])))
    out: list[tuple[str, int, int]] = []

    def emit(src, size, consts, vec):
        n = per.get(vec, 0)
        if n >= per_vector:
            return
        per[vec] = n + 1
        out.append((src, size, consts))

    if original is not None:
        ovec = tuple(bool(v) for v in original)
        for c in cmps:
            for sym, fn in (("or", lambda x, y: x or y), ("and", lambda x, y: x and y)):
                emit("(" + "__ORIG__" + ") " + sym + " " + c[0], c[1] + 1, c[2], tuple(bool(fn(x, y)) for x, y in zip(ovec, c[3])))
    for c in cmps:
        emit(c[0], c[1], c[2], c[3])
    simple = [c for c in cmps if c[1] == 1][:80]          # name-vs-name / name-vs-constant only
    for a, b in itertools.combinations(simple, 2):
        for sym, fn in (("and", lambda x, y: x and y), ("or", lambda x, y: x or y)):
            emit(a[0] + " " + sym + " " + b[0], a[1] + b[1] + 1, a[2] + b[2], tuple(bool(fn(x, y)) for x, y in zip(a[3], b[3])))
    return out, enum, stop


def find_def(tree: ast.AST, function: str, cls: str | None = None) -> Any:
    """The FunctionDef named ``function`` -- at module level, or inside class ``cls``."""
    if cls is None:
        return next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function), None)
    c = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls), None)
    if c is None:
        return None
    return next((n for n in c.body if isinstance(n, ast.FunctionDef) and n.name == function), None)


def hole_sites(source_text: str, function: str, line: int, cls: str | None = None) -> list[dict[str, Any]]:
    """Single-line expression holes on ``line`` inside ``function``: return value,
    assignment / augmented assignment RHS, if/elif/while condition."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []
    fn = find_def(tree, function, cls)
    if fn is None or not (fn.lineno <= line <= (fn.end_lineno or fn.lineno)):
        return []
    out: list[dict[str, Any]] = []
    for node in ast.walk(fn):
        if getattr(node, "lineno", None) != line:
            continue
        kind, expr = None, None
        if isinstance(node, ast.Return) and node.value is not None:
            kind, expr = "return", node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            kind, expr = "assign", node.value
        elif isinstance(node, ast.AugAssign):
            kind, expr = "augassign", node.value
        elif isinstance(node, (ast.If, ast.While)):
            kind, expr = "condition", node.test
        if expr is None or expr.lineno != expr.end_lineno:
            continue
        site = {"kind": kind, "lineno": expr.lineno, "col_offset": expr.col_offset,
                "end_col_offset": expr.end_col_offset, "original": ast.get_source_segment(source_text, expr)}
        if kind == "assign" and isinstance(node.targets[0], ast.Name) and node.lineno == node.end_lineno:
            site["target"] = node.targets[0].id          # `x = x` is a deletion, not an assignment
        out.append(site)
    return out


def splice(source_text: str, site: dict[str, Any], expr: str) -> str:
    lines = source_text.splitlines(keepends=True)
    i = site["lineno"] - 1
    ln = lines[i]
    lines[i] = ln[:site["col_offset"]] + expr + ln[site["end_col_offset"]:]
    return "".join(lines)


def function_text(source_text: str, function: str, cls: str | None = None) -> tuple[str, int] | None:
    """(dedented source of the def with its decorators, first line number)."""
    tree = ast.parse(source_text)
    fn = find_def(tree, function, cls)
    if fn is None:
        return None
    first = min([fn.lineno, *[d.lineno for d in fn.decorator_list]])
    lines = source_text.splitlines(keepends=True)[first - 1:fn.end_lineno]
    indent = len(lines[0]) - len(lines[0].lstrip())
    return "".join(ln[indent:] if ln[:indent].strip() == "" else ln for ln in lines), first


def program(spec: dict[str, Any], own_source: str) -> str:
    """Source of the confined solver.  ``spec``: module, sys_path, target (rel path),
    function, line, examples [[args, expected]], constants, out (rel path), budget_s,
    max_found.  ``own_source`` is this file's text (so the enumerator travels along)."""
    return own_source + r'''

# ---- driver (confined) -------------------------------------------------------
import importlib, os, signal, sys, traceback
sys.dont_write_bytecode = True
SPEC = json.loads(%s)
ROOT = os.getcwd()
sp = os.path.join(ROOT, SPEC["sys_path"]) if SPEC["sys_path"] != "." else ROOT
for p in (sp, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)
T0 = time.monotonic()
OUT = {"status": "", "sites": [], "seconds": 0.0}


class _Captured(BaseException):
    pass


class _Tick(BaseException):
    pass


def _tick(signum, frame):
    raise _Tick()


signal.signal(signal.SIGALRM, _tick)


def _done(status):
    OUT["status"] = status
    OUT["seconds"] = round(time.monotonic() - T0, 3)
    with open(os.path.join(ROOT, SPEC["out"]), "w", encoding="utf-8") as fh:
        json.dump(OUT, fh)
    sys.exit(0)


target_abs = os.path.realpath(os.path.join(ROOT, SPEC["target"]))
try:
    mod = importlib.import_module(SPEC["module"])
except BaseException as exc:
    _done("MODULE_IMPORT_FAILED:" + type(exc).__name__)
CLS = SPEC.get("class")
N_CTOR = int(SPEC.get("n_ctor") or 0)
if CLS:
    klass = getattr(mod, CLS, None)
    fn = vars(klass).get(SPEC["function"]) if isinstance(klass, type) else None
else:
    klass = None
    fn = getattr(mod, SPEC["function"], None)
if not callable(fn):
    _done("FUNCTION_NOT_FOUND")


def _call(f, args):
    # a method runs on a fresh instance built from the example's constructor literals
    if klass is None:
        return f(*args)
    return f(klass(*args[:N_CTOR]), *args[N_CTOR:])


source_text = open(target_abs, encoding="utf-8").read()
sites = hole_sites(source_text, SPEC["function"], SPEC["line"], CLS)
if not sites:
    _done("NO_HOLE_ON_LINE")
ft = function_text(source_text, SPEC["function"], CLS)
if ft is None:
    _done("FUNCTION_NOT_FOUND")

# 1. what is in scope at the hole line, per example
arrivals = []      # every arrival at the hole line, across iterations and examples (bounded)
MAX_ARRIVALS = 40


def _tracer(frame, event, arg):
    if frame.f_code.co_name != SPEC["function"] or os.path.realpath(frame.f_code.co_filename) != target_abs:
        return None
    if event == "line" and frame.f_lineno == SPEC["line"]:
        env = {k: v for k, v in frame.f_locals.items() if isinstance(v, SIMPLE) and _ok(v)}
        me = frame.f_locals.get("self")
        if me is not None and hasattr(me, "__dict__"):
            # the instance's simple attributes are names too: `self.w`
            env.update({"self." + k: v for k, v in vars(me).items() if isinstance(v, SIMPLE) and _ok(v)})
        arrivals.append(env)
        if len(arrivals) >= MAX_ARRIVALS:
            raise _Captured()
    return _tracer


# an example that never reaches the line (an empty list skipping the loop body)
# contributes no snapshot but still judges every candidate in _agrees below
reached = 0
for args, expected in SPEC["examples"]:
    before = len(arrivals)
    signal.setitimer(signal.ITIMER_REAL, 0.5)
    sys.settrace(_tracer)
    try:
        _call(fn, args)
    except BaseException:
        pass
    finally:
        sys.settrace(None)
        signal.setitimer(signal.ITIMER_REAL, 0)
    if len(arrivals) != before:
        reached += 1
OUT["reached_examples"] = reached
if not arrivals:
    _done("HOLE_LINE_NOT_REACHED_BY_EXAMPLE")
# a hole inside a loop is executed many times: observational equivalence is taken
# over EVERY arrival, so `acc + x` and `x` stay distinct after the first iteration
envs = arrivals[:MAX_ARRIVALS]
names = sorted(set.intersection(*[set(e) for e in envs]))
OUT["arrivals"] = len(envs)
if not names:
    _done("NO_NAMES_IN_SCOPE")
OUT["names"] = names

class _Attrs:
    def __init__(self, d):
        self.__dict__.update(d)


def _ns(env):
    # `self.w` entries become a stand-in object so the original condition can be evaluated
    plain = {k: v for k, v in env.items() if "." not in k}
    attrs = {k[5:]: v for k, v in env.items() if k.startswith("self.")}
    if attrs:
        plain["self"] = _Attrs(attrs)
    return plain


# 2./3. enumerate distinct expressions, splice, recompile, run the examples
def _agrees(g):
    for args, expected in SPEC["examples"]:
        signal.setitimer(signal.ITIMER_REAL, 0.05)
        try:
            got = _call(g, args)
        except BaseException:
            return False
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            if not (got == expected and type(got) is type(expected)):
                return False
        except Exception:
            return False
    return True


budget = float(SPEC.get("budget_s") or 2.0)
total_found = 0
for site in sites:
    row = {"site": site, "expressions": [], "tried": 0}
    OUT["sites"].append(row)
    remaining = budget - (time.monotonic() - T0)
    if remaining <= 0.05:
        row["stop"] = "BUDGET"
        continue
    original = site["original"].strip()
    ovec = None
    if site["kind"] == "condition":
        try:
            ovec = tuple(bool(eval(original, dict(vars(mod)), _ns(env))) for env in envs)
        except Exception:
            ovec = None
    exprs, enum, stop = enumerate_distinct(names, envs, SPEC.get("constants") or [], budget_s=remaining * 0.5,
                                           booleans=(site["kind"] == "condition"), original=ovec)
    row["distinct"] = len(exprs)
    row["enumerated"] = enum
    for src, size, consts in exprs:
        if time.monotonic() - T0 > budget:
            stop = "BUDGET"
            break
        try:
            text = ast.unparse(ast.parse(src.replace("__ORIG__", original), mode="eval"))
        except SyntaxError:
            continue
        if text == original:
            continue
        patched = splice(source_text, site, text)
        try:
            fsrc, first = function_text(patched, SPEC["function"], CLS)
            code = compile(fsrc, target_abs, "exec")
        except (SyntaxError, ValueError, TypeError):
            continue
        ns = dict(vars(mod))
        row["tried"] += 1
        signal.setitimer(signal.ITIMER_REAL, 0.1)
        try:
            exec(code, ns)
        except BaseException:
            continue
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        g = ns.get(SPEC["function"])
        if callable(g) and _agrees(g):
            row["expressions"].append(text)
            total_found += 1
            if len(row["expressions"]) >= int(SPEC.get("max_found") or 4):
                break
    row["stop"] = stop
_done("FOUND:" + str(total_found) if total_found else "NONE")
''' % repr(json.dumps(spec))
