# PROJECT_BRAIN
"""In-process candidate judging: the whole batch in one confined interpreter.

Measured floor before this (2-cpu host): 0.19 s per candidate, of which the
test itself was ~0.01 s -- the rest was a pytest start (~0.09 s) and an
unshare+chroot (~0.09 s) paid once PER CANDIDATE.  The two-edit case tested
118 candidates in 22 s.

What this does instead, when it may: one confined process per worker copy of
the tree, the candidates streamed through it; for each candidate the target
file is rewritten, every module under the tree is dropped from sys.modules,
the named test modules are imported fresh and their zero-parameter ``test_*``
functions called directly.  Failures are counted from exceptions, imports
that fail count as failures, a per-candidate alarm bounds runaway candidates,
results are written incrementally so a deadline still yields what ran.  Each
failing test also yields an ASSERTION DISTANCE: for `assert <expr> == <lit>`
the expression is evaluated in the imported module and |actual - expected| is
scaled into [0, 1) -- a gradient for composition (GenProg/Arja-style fitness),
never a verdict.

When it may: only for PLAIN tests -- every ``test_*`` function in the named
files takes no parameters (no fixtures, no parametrize), no test classes, no
``autouse`` fixture anywhere in the tree's conftests, no pytest ini options
that change collection.  Anything else falls back to the pytest path,
unchanged.  The applicability check is static and says why it refused.

Fidelity: this judge decides which candidates are GREEN CANDIDATES.  The one
that is chosen is still replayed twice under real pytest and gated against
the whole suite, so an in-process false positive cannot ship; an in-process
false negative costs one missed candidate.  State leaking between candidates
is bounded by the module purge and by the final pytest replay.
"""
from __future__ import annotations

import ast
import copy
import json
import pathlib
from typing import Any

PLAIN_MAX_TESTS = 500


def plain_tests(tree: pathlib.Path, tests_rel: list[str]) -> tuple[bool, str, list[dict[str, Any]]]:
    """(ok, why, modules).  modules: [{"path": rel, "import": dotted, "sys_path": rel_dir|None}]."""
    for ini in ("pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml"):
        p = tree / ini
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return False, "INI_UNREADABLE:" + ini, []
            if "python_files" in text or "python_functions" in text or "usefixtures" in text or "addopts" in text:
                return False, "INI_CHANGES_COLLECTION:" + ini, []
    for conf in tree.rglob("conftest.py"):
        try:
            text = conf.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False, "CONFTEST_UNREADABLE", []
        if "autouse" in text or "pytest_runtest" in text or "pytest_collection" in text:
            return False, "CONFTEST_HOOKS_OR_AUTOUSE:" + conf.relative_to(tree).as_posix(), []
    mods: list[dict[str, Any]] = []
    total = 0
    for rel in tests_rel:
        p = tree / rel
        try:
            src = p.read_text(encoding="utf-8")
            t = ast.parse(src)
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            return False, "TEST_UNPARSEABLE:" + rel + ":" + type(exc).__name__, []
        n = 0
        cases: dict[str, list[dict[str, Any]]] = {}
        for node in t.body:
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                return False, "TEST_CLASS:" + rel + ":" + node.name, []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                if isinstance(node, ast.AsyncFunctionDef):
                    return False, "ASYNC_TEST:" + rel + ":" + node.name, []
                a = node.args
                if a.kwonlyargs or a.vararg or a.kwarg:
                    return False, "TEST_TAKES_PARAMETERS:" + rel + ":" + node.name, []
                params = [x.arg for x in [*a.posonlyargs, *a.args]]
                groups: list[dict[str, Any]] = []
                for d in node.decorator_list:
                    g = _literal_parametrize(d)
                    if g is None:
                        return False, "DECORATED_TEST:" + rel + ":" + node.name, []
                    groups.append(g)
                bound = [nm for g in groups for nm in g["names"]]
                if sorted(bound) != sorted(params) or len(set(bound)) != len(bound):
                    return False, "TEST_TAKES_PARAMETERS:" + rel + ":" + node.name, []
                if groups:
                    rows = 1
                    for g in groups:
                        rows *= len(g["rows"])
                    cases[node.name] = groups
                    n += rows
                else:
                    n += 1
        if n == 0:
            return False, "NO_PLAIN_TEST_FUNCTIONS:" + rel, []
        total += n
        # import the way pytest's rootdir/prepend mode does: walk up through
        # packages (__init__.py) to the first non-package directory
        parts = list(pathlib.PurePosixPath(rel).parts)
        d = p.parent
        pkg: list[str] = []
        while (d / "__init__.py").is_file() and d != tree.parent:
            pkg.insert(0, d.name)
            d = d.parent
        dotted = ".".join(pkg + [p.stem])
        sys_path = d.relative_to(tree).as_posix() if d != tree else "."
        mods.append({"path": rel, "import": dotted, "sys_path": sys_path, "tests": n,
                     "asserts": assert_specs(t, cases), "cases": cases})
        if total > PLAIN_MAX_TESTS:
            return False, "TOO_MANY_TESTS:" + str(total), []
    return True, "PLAIN", mods


def _literal_parametrize(dec: ast.expr) -> dict[str, Any] | None:
    """`@pytest.mark.parametrize("a,b", [(1, 2), ...])` with literal rows -> {names, rows};
    anything else (ids=, pytest.param, indirect, computed values) -> None."""
    if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "parametrize"
            and isinstance(dec.func.value, ast.Attribute) and dec.func.value.attr == "mark"
            and isinstance(dec.func.value.value, ast.Name) and dec.func.value.value.id == "pytest"
            and len(dec.args) == 2 and not dec.keywords):
        return None
    try:
        names_v = ast.literal_eval(dec.args[0])
        rows_v = ast.literal_eval(dec.args[1])
    except (ValueError, TypeError, SyntaxError):
        return None
    if isinstance(names_v, str):
        names = [x.strip() for x in names_v.split(",") if x.strip()]
    elif isinstance(names_v, (list, tuple)) and all(isinstance(x, str) for x in names_v):
        names = list(names_v)
    else:
        return None
    if not names or not isinstance(rows_v, (list, tuple)) or not rows_v:
        return None
    rows: list[list[Any]] = []
    for r in rows_v:
        if len(names) == 1:
            rows.append([r])
        elif isinstance(r, (list, tuple)) and len(r) == len(names):
            rows.append(list(r))
        else:
            return None
    return {"names": names, "rows": rows}


def expand_cases(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stacked parametrize decorators -> the cartesian product of bindings (pytest's order)."""
    out: list[dict[str, Any]] = [{}]
    for g in reversed(groups):          # the decorator nearest the def varies fastest
        out = [{**b, **dict(zip(g["names"], row))} for b in out for row in g["rows"]]
    return out


class _Subst(ast.NodeTransformer):
    def __init__(self, bindings: dict[str, Any]) -> None:
        self.b = bindings

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id in self.b:
            return ast.copy_location(ast.Constant(self.b[node.id]), node)
        return node


def assert_specs(test_tree: ast.AST, cases: dict[str, list[dict[str, Any]]] | None = None) -> list[dict[str, Any]]:
    """`assert <expr> == <literal>` (either side literal) inside plain test functions:
    the pairs an assertion-distance fitness can measure.  For a parametrized test the
    row's bindings are substituted first, so `assert area(w, h) == e` over
    `[(3, 4, 12)]` yields the concrete `area(3, 4) == 12`.  The expression is kept as
    source; the judge evaluates it in the imported test module."""
    out: list[dict[str, Any]] = []
    for fn in test_tree.body:
        if not (isinstance(fn, ast.FunctionDef) and fn.name.startswith("test")):
            continue
        bindings_list = expand_cases((cases or {}).get(fn.name) or []) or [{}]
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare)
                    and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq)):
                continue
            for bindings in bindings_list:
                test = _Subst(bindings).visit(copy.deepcopy(node.test)) if bindings else node.test
                left, right = test.left, test.comparators[0]
                for expr, lit in ((left, right), (right, left)):
                    try:
                        expected = ast.literal_eval(lit)
                    except (ValueError, TypeError, SyntaxError):
                        continue
                    if isinstance(expected, (bool, int, float, str, type(None), tuple, list)):
                        out.append({"test": fn.name, "expr": ast.unparse(expr), "expected": expected})
                        break
    return out[:200]


def judge_program(target_rel: str, modules: list[dict[str, Any]], batch_dir_rel: str, count: int,
                  out_rel: str, per_candidate_s: int = 5) -> str:
    """Source of the batch judge; runs with cwd = the tree copy (confined: /project)."""
    spec = json.dumps({"target": target_rel, "modules": modules, "batch": batch_dir_rel, "count": count,
                       "out": out_rel, "per": per_candidate_s})
    return r'''
import importlib, json, os, shutil, signal, sys
sys.dont_write_bytecode = True
SPEC = json.loads(%s)
ROOT = os.getcwd()
for m in SPEC["modules"]:
    sp = os.path.join(ROOT, m["sys_path"]) if m["sys_path"] != "." else ROOT
    if sp not in sys.path:
        sys.path.insert(0, sp)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
target = os.path.join(ROOT, SPEC["target"])
originals = {}


def _write(rel, data):
    path = os.path.join(ROOT, rel)
    if rel not in originals:
        originals[rel] = open(path, "rb").read()
    with open(path, "wb") as fh:
        fh.write(data)


class _Timeout(BaseException):
    pass


def _alarm(signum, frame):
    raise _Timeout()


signal.signal(signal.SIGALRM, _alarm)


def _purge():
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None) or ""
        if f and os.path.abspath(f).startswith(ROOT + os.sep):
            del sys.modules[name]
    importlib.invalidate_caches()


def _rows(groups):
    out = [{}]
    for g in reversed(groups or []):
        out = [dict(b, **dict(zip(g["names"], row))) for b in out for row in g["rows"]]
    return out


def _distance(actual, expected):
    # 0 when equal; numeric gap scaled to [0, 1); otherwise 1 -- a gradient for the
    # search, never a verdict (the verdict is the assertion itself)
    try:
        if actual == expected and type(actual) is type(expected):
            return 0.0
    except Exception:
        return 1.0
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)) and not isinstance(actual, bool) and not isinstance(expected, bool):
        try:
            d = abs(float(actual) - float(expected))
            return d / (1.0 + d)
        except Exception:
            return 1.0
    if isinstance(actual, str) and isinstance(expected, str):
        n = max(len(actual), len(expected)) or 1
        same = sum(1 for a, b in zip(actual, expected) if a == b)
        return 1.0 - same / n if same else 1.0
    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        n = max(len(actual), len(expected)) or 1
        return 1.0 - sum(1 for a, b in zip(actual, expected) if a == b) / n
    return 1.0


def _run():
    failed = passed = 0
    distance = 0.0
    for m in SPEC["modules"]:
        try:
            mod = importlib.import_module(m["import"])
        except _Timeout:
            raise
        except BaseException:
            failed += int(m.get("tests") or 1)
            distance += float(m.get("tests") or 1)
            continue
        failing = set()
        for name in sorted(dir(mod)):
            fn = getattr(mod, name)
            if name.startswith("test") and callable(fn) and getattr(fn, "__module__", None) == mod.__name__:
                for kw in _rows((m.get("cases") or {}).get(name)):
                    try:
                        fn(**kw)
                        passed += 1
                    except _Timeout:
                        raise
                    except BaseException:
                        failed += 1
                        failing.add(name)
        for spec in m.get("asserts") or []:
            if spec["test"] not in failing:
                continue
            try:
                actual = eval(spec["expr"], vars(mod))
                distance += _distance(actual, spec["expected"])
            except _Timeout:
                raise
            except BaseException:
                distance += 1.0
    return failed, passed, distance


results = {}
for i in range(SPEC["count"]):
    cand = os.path.join(ROOT, SPEC["batch"], str(i))
    for rel, raw in list(originals.items()):           # back to the original before the next candidate
        with open(os.path.join(ROOT, rel), "wb") as fh:
            fh.write(raw)
    if os.path.exists(cand + ".json"):                  # a patch set: {rel: text}
        with open(cand + ".json", "r", encoding="utf-8") as fh:
            for rel, text in json.load(fh).items():
                _write(rel, text.encode("utf-8"))
    else:
        with open(cand + ".py", "rb") as fh:
            _write(SPEC["target"], fh.read())
    _purge()
    signal.alarm(SPEC["per"])
    try:
        failed, passed, distance = _run()
        results[i] = [failed if failed else (0 if passed else 998), round(distance, 6)]
    except _Timeout:
        results[i] = [999, 999.0]
    except BaseException:
        results[i] = [997, 997.0]
    finally:
        signal.alarm(0)
    with open(os.path.join(ROOT, SPEC["out"]), "w", encoding="utf-8") as fh:
        json.dump(results, fh)
for rel, raw in originals.items():
    with open(os.path.join(ROOT, rel), "wb") as fh:
        fh.write(raw)
_purge()
print("BRAIN_JUDGE_DONE=" + str(len(results)))
''' % repr(spec)


def spectrum_program(modules: list[dict[str, Any]], out_rel: str, per_test_s: int = 5) -> str:
    """Source of the in-process spectrum localizer (Abreu, Zoeteweij & van Gemund 2007,
    Ochiai): every plain test (each parametrized row is one test) runs once under
    ``sys.settrace``; the lines it executes in tree files that are not test files are
    its spectrum.  Output: ranked (path, line, ochiai, ef, ep) and the per-test verdicts.
    This is the fast path for suites the judge can run; it proposes lines, nothing else."""
    spec = json.dumps({"modules": modules, "out": out_rel, "per": per_test_s})
    return r'''
import importlib, json, math, os, signal, sys
sys.dont_write_bytecode = True
SPEC = json.loads(%s)
ROOT = os.getcwd()
for m in SPEC["modules"]:
    sp = os.path.join(ROOT, m["sys_path"]) if m["sys_path"] != "." else ROOT
    if sp not in sys.path:
        sys.path.insert(0, sp)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
TEST_FILES = {os.path.realpath(os.path.join(ROOT, m["path"])) for m in SPEC["modules"]}
PREFIX = os.path.realpath(ROOT) + os.sep


class _Timeout(BaseException):
    pass


def _alarm(signum, frame):
    raise _Timeout()


signal.signal(signal.SIGALRM, _alarm)


def _rows(groups):
    out = [{}]
    for g in reversed(groups or []):
        out = [dict(b, **dict(zip(g["names"], row))) for b in out for row in g["rows"]]
    return out


hits = {}          # (path, line) -> [ef, ep, depth]
tests = []
current = {}       # (path, line) -> deepest call depth seen in this test
depth = 0


def _tracer(frame, event, arg):
    global depth
    f = frame.f_code.co_filename
    if not f.startswith(PREFIX) or f in TEST_FILES or os.sep + "conftest.py" in f:
        return None
    if event == "call":
        depth += 1
    elif event == "return":
        depth -= 1
    elif event == "line":
        key = (f[len(PREFIX):], frame.f_lineno)
        if current.get(key, -1) < depth:
            current[key] = depth
    return _tracer


for m in SPEC["modules"]:
    try:
        mod = importlib.import_module(m["import"])
    except BaseException as exc:
        tests.append({"id": m["import"], "ok": False, "error": type(exc).__name__})
        continue
    for name in sorted(dir(mod)):
        fn = getattr(mod, name)
        if not (name.startswith("test") and callable(fn) and getattr(fn, "__module__", None) == mod.__name__):
            continue
        for k, kw in enumerate(_rows((m.get("cases") or {}).get(name))):
            current = {}
            depth = 0
            ok = True
            signal.alarm(SPEC["per"])
            sys.settrace(_tracer)
            try:
                fn(**kw)
            except BaseException:
                ok = False
            finally:
                sys.settrace(None)
                signal.alarm(0)
            tests.append({"id": name + ("[" + str(k) + "]" if kw else ""), "ok": ok})
            for key, d in current.items():
                h = hits.setdefault(key, [0, 0, 0])
                h[0 if not ok else 1] += 1
                h[2] = max(h[2], d)

nf = sum(1 for t in tests if not t["ok"])
ranked = []
for (path, line), (ef, ep, d) in hits.items():
    score = ef / math.sqrt(nf * (ef + ep)) if nf and (ef + ep) else 0.0
    ranked.append([path, line, round(score, 6), ef, ep, d])
# ties: the deeper call first -- nearer the computation the failing tests disagree with
ranked.sort(key=lambda r: (-r[2], -r[3], r[4], -r[5], r[0], r[1]))
with open(os.path.join(ROOT, SPEC["out"]), "w", encoding="utf-8") as fh:
    json.dump({"tests": tests, "failing": nf, "ranked": ranked[:500]}, fh)
print("BRAIN_SPECTRUM_DONE=" + str(len(ranked)))
''' % repr(spec)
