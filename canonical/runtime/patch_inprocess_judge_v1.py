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
        for node in t.body:
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                return False, "TEST_CLASS:" + rel + ":" + node.name, []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                if isinstance(node, ast.AsyncFunctionDef):
                    return False, "ASYNC_TEST:" + rel + ":" + node.name, []
                a = node.args
                if a.args or a.posonlyargs or a.kwonlyargs or a.vararg or a.kwarg:
                    return False, "TEST_TAKES_PARAMETERS:" + rel + ":" + node.name, []
                for d in node.decorator_list:
                    return False, "DECORATED_TEST:" + rel + ":" + node.name, []
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
                     "asserts": assert_specs(t)})
        if total > PLAIN_MAX_TESTS:
            return False, "TOO_MANY_TESTS:" + str(total), []
    return True, "PLAIN", mods


def assert_specs(test_tree: ast.AST) -> list[dict[str, Any]]:
    """`assert <expr> == <literal>` (either side literal) inside zero-parameter test
    functions: the pairs an assertion-distance fitness can measure.  The expression
    is kept as source; the judge evaluates it in the imported test module."""
    out: list[dict[str, Any]] = []
    for fn in test_tree.body:
        if not (isinstance(fn, ast.FunctionDef) and fn.name.startswith("test")):
            continue
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare)
                    and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq)):
                continue
            left, right = node.test.left, node.test.comparators[0]
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
original = open(target, "rb").read()


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
                try:
                    fn()
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
    cand = os.path.join(ROOT, SPEC["batch"], str(i) + ".py")
    shutil.copyfile(cand, target)
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
open(target, "wb").write(original)
_purge()
print("BRAIN_JUDGE_DONE=" + str(len(results)))
''' % repr(spec)
