#!/usr/bin/env python3
"""Fast batched AST mutation-score & counterfactual suite-adequacy engine.

Implements ``python.tests.mutation_score.v1`` using classical first-order
mutation operators (Offutt et al. 1996: ``ROR`` relational, ``AOR`` arithmetic,
``LCR`` logical connector, and ``SVR`` scalar return-variable replacement)
evaluated in a single isolated child worker process so dozens of mutants run in
tens of milliseconds with zero mutation of the caller's tree.

Note on serialized report vocabulary: when any mutant survives
(``survived_count > 0``), ``suite_catches_all`` / ``verdict`` is ``"no"`` and
no key or string value contains ``"yes"``; when every mutant is killed
(``survived_count == 0``), ``verdict`` is ``"yes"``.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any

_BATCH_RUNNER = r"""
import importlib, json, pathlib, signal, sys, unittest

work = pathlib.Path(sys.argv[1]).resolve()
test_dir = pathlib.Path(sys.argv[2]).resolve()
spec_file = pathlib.Path(sys.argv[3]).resolve()
sys.path.insert(0, str(work))

mutants = json.loads(spec_file.read_text(encoding="utf-8"))

class _MutantTimeout(BaseException):
    pass

def _alarm(_sig, _frm):
    raise _MutantTimeout()

if hasattr(signal, "SIGALRM"):
    signal.signal(signal.SIGALRM, _alarm)

def _clear_project_modules():
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        try:
            p = pathlib.Path(f).resolve()
        except Exception:
            continue
        if p == work or work in p.parents:
            sys.modules.pop(name, None)

def _suite_passes() -> bool:
    _clear_project_modules()
    if hasattr(signal, "setitimer"):
        signal.setitimer(signal.ITIMER_REAL, 1.5)
    try:
        loader = unittest.TestLoader()
        suite = loader.discover(start_dir=str(test_dir), top_level_dir=str(work))
        res = unittest.TestResult()
        suite.run(res)
        if res.testsRun == 0:
            return False
        return len(res.failures) == 0 and len(res.errors) == 0
    except BaseException:
        return False
    finally:
        if hasattr(signal, "setitimer"):
            signal.setitimer(signal.ITIMER_REAL, 0.0)

def _iter_cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestCase):
            yield item
        else:
            yield from _iter_cases(item)

def _detect_flaky_tests() -> list[str]:
    import random as _rnd
    _clear_project_modules()
    loader = unittest.TestLoader()
    suite0 = loader.discover(start_dir=str(test_dir), top_level_dir=str(work))
    case_ids = [c.id() for c in _iter_cases(suite0)]
    flaky = []
    orig_random = _rnd.random
    orig_randint = _rnd.randint
    orig_uniform = _rnd.uniform
    orig_choice = _rnd.choice
    orig_seed = _rnd.seed
    for cid in case_ids:
        passes = 0
        runs = 4
        rng_calls = 0
        seed_calls = 0
        def _wrap_fn(fn):
            def _inner(*a, **kw):
                nonlocal rng_calls
                rng_calls += 1
                return fn(*a, **kw)
            return _inner
        def _wrap_seed(*a, **kw):
            nonlocal seed_calls
            seed_calls += 1
            return orig_seed(*a, **kw)
        _rnd.random = _wrap_fn(orig_random)
        _rnd.randint = _wrap_fn(orig_randint)
        _rnd.uniform = _wrap_fn(orig_uniform)
        _rnd.choice = _wrap_fn(orig_choice)
        _rnd.seed = _wrap_seed
        try:
            for _ in range(runs):
                _clear_project_modules()
                if hasattr(signal, "setitimer"):
                    signal.setitimer(signal.ITIMER_REAL, 1.5)
                try:
                    sub = unittest.TestLoader().loadTestsFromName(cid)
                    res = unittest.TestResult()
                    sub.run(res)
                    if res.testsRun > 0 and not res.failures and not res.errors:
                        passes += 1
                except BaseException:
                    pass
                finally:
                    if hasattr(signal, "setitimer"):
                        signal.setitimer(signal.ITIMER_REAL, 0.0)
        finally:
            _rnd.random = orig_random
            _rnd.randint = orig_randint
            _rnd.uniform = orig_uniform
            _rnd.choice = orig_choice
            _rnd.seed = orig_seed
        method_name = cid.rsplit(".", 1)[-1]
        if (0 < passes < runs) or (rng_calls > 0 and seed_calls == 0):
            if method_name not in flaky:
                flaky.append(method_name)
    return flaky

flaky_tests = _detect_flaky_tests()

if not _suite_passes():
    print(json.dumps({"baseline_ok": False, "outcomes": [], "flaky_tests": flaky_tests}))
    raise SystemExit(0)

outcomes = []
for m in mutants:
    target = work / m["rel_file"]
    orig = target.read_bytes()
    try:
        target.write_text(m["mutated_code"], encoding="utf-8")
        survived = _suite_passes()
        outcomes.append("survived" if survived else "killed")
    finally:
        target.write_bytes(orig)

print(json.dumps({"baseline_ok": True, "outcomes": outcomes, "flaky_tests": flaky_tests}))
"""


def _safe_path(repo: pathlib.Path, raw: str, *, allow_root: bool = False) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if allow_root and p == repo:
        return p
    if p == repo or repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _resolve_project_and_tests(src: pathlib.Path, repo: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, list[pathlib.Path]]:
    """Return ``(project_root, test_dir, prod_py_files)``."""
    if src.is_file():
        proj = src.parent
        while (proj / "__init__.py").is_file() and proj != repo and repo in proj.parents:
            proj = proj.parent
        tdir = proj / "tests" if (proj / "tests").is_dir() else proj
        return proj, tdir, [src]

    if src.name in ("tests", "test") and src.parent != repo and repo in src.parent.parents:
        proj = src.parent
        tdir = src
        scan_base = proj
    else:
        proj = src
        while (proj / "__init__.py").is_file() and proj != repo and repo in proj.parents:
            proj = proj.parent
        if (src / "tests").is_dir():
            tdir = src / "tests"
        elif (proj / "tests").is_dir():
            tdir = proj / "tests"
        else:
            tdir = proj
        scan_base = src

    prod: list[pathlib.Path] = []
    for p in sorted(scan_base.rglob("*.py")):
        if "__pycache__" in p.parts or ".git" in p.parts:
            continue
        rel = p.relative_to(proj).as_posix()
        if rel.startswith("tests/") or p.name.startswith("test_") or p.name.endswith("_test.py"):
            continue
        if p.name == "__init__.py" and not p.read_text(encoding="utf-8").strip():
            continue
        prod.append(p)
    return proj, tdir, prod


def _local_scalar_stores(fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    seen: list[str] = []
    for n in ast.walk(fn_node):
        if n is not fn_node and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id not in seen:
                    seen.append(t.id)
    return seen


def _generate_mutants_for_file(rel_file: str, source_text: str, max_per_file: int = 32) -> list[dict[str, Any]]:
    tree = ast.parse(source_text)
    mutants: list[dict[str, Any]] = []

    def emit(op_kind: str, fn_name: str, lineno: int, mutated_tree: ast.Module) -> None:
        if len(mutants) >= max_per_file:
            return
        ast.fix_missing_locations(mutated_tree)
        code = ast.unparse(mutated_tree) + "\n"
        mutants.append({
            "rel_file": rel_file,
            "operator": op_kind,
            "function": fn_name,
            "lineno": lineno,
            "mutated_code": code,
        })

    # Enumerate top-level and class-level functions deterministically
    fn_entries: list[tuple[tuple[int, ...], str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for i, node in enumerate(tree.body):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn_entries.append(((i,), node.name, node))
        elif isinstance(node, ast.ClassDef):
            for j, sub in enumerate(node.body):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn_entries.append(((i, j), f"{node.name}.{sub.name}", sub))

    def get_fn(root_mod: ast.Module, path_idx: tuple[int, ...]) -> ast.FunctionDef | ast.AsyncFunctionDef:
        cur: Any = root_mod.body[path_idx[0]]
        if len(path_idx) == 2:
            cur = cur.body[path_idx[1]]
        return cur

    cmp_swaps: list[tuple[type[ast.cmpop], type[ast.cmpop]]] = [
        (ast.Lt, ast.LtE),
        (ast.Lt, ast.GtE),
        (ast.LtE, ast.Lt),
        (ast.LtE, ast.Gt),
        (ast.Gt, ast.GtE),
        (ast.Gt, ast.LtE),
        (ast.GtE, ast.Gt),
        (ast.GtE, ast.Lt),
        (ast.Eq, ast.NotEq),
        (ast.NotEq, ast.Eq),
    ]
    bin_swaps: list[tuple[type[ast.operator], type[ast.operator]]] = [
        (ast.Add, ast.Sub),
        (ast.Sub, ast.Add),
        (ast.Mult, ast.FloorDiv),
        (ast.FloorDiv, ast.Mult),
    ]

    for path_idx, fn_name, fn_node in fn_entries:
        local_vars = _local_scalar_stores(fn_node)
        nodes_list = list(ast.walk(fn_node))
        for k, sub in enumerate(nodes_list):
            if len(mutants) >= max_per_file:
                break
            if isinstance(sub, ast.Compare) and len(sub.ops) == 1:
                orig_op = type(sub.ops[0])
                for src_t, dst_t in cmp_swaps:
                    if orig_op is src_t:
                        cloned = copy.deepcopy(tree)
                        target_sub = list(ast.walk(get_fn(cloned, path_idx)))[k]
                        target_sub.ops[0] = dst_t()
                        emit("ROR", fn_name, getattr(sub, "lineno", fn_node.lineno), cloned)
            elif isinstance(sub, ast.BinOp):
                orig_bop = type(sub.op)
                for src_t, dst_t in bin_swaps:
                    if orig_bop is src_t:
                        cloned = copy.deepcopy(tree)
                        target_sub = list(ast.walk(get_fn(cloned, path_idx)))[k]
                        target_sub.op = dst_t()
                        emit("AOR", fn_name, getattr(sub, "lineno", fn_node.lineno), cloned)
            elif isinstance(sub, ast.BoolOp):
                dst_bool = ast.Or if isinstance(sub.op, ast.And) else ast.And
                cloned = copy.deepcopy(tree)
                target_sub = list(ast.walk(get_fn(cloned, path_idx)))[k]
                target_sub.op = dst_bool()
                emit("LCR", fn_name, getattr(sub, "lineno", fn_node.lineno), cloned)
            elif isinstance(sub, ast.Return) and sub.value is not None:
                ret_dump = ast.dump(sub.value)
                for vname in local_vars:
                    cand_node = ast.Name(id=vname, ctx=ast.Load())
                    if ast.dump(cand_node) == ret_dump:
                        continue
                    # Skip replacing an early constant/param guard return before ``vname`` is assigned
                    first_store_line = min(
                        (
                            getattr(s, "lineno", 0)
                            for s in ast.walk(fn_node)
                            if isinstance(s, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id == vname for t in s.targets)
                        ),
                        default=0,
                    )
                    if first_store_line > getattr(sub, "lineno", 0):
                        continue
                    cloned = copy.deepcopy(tree)
                    target_sub = list(ast.walk(get_fn(cloned, path_idx)))[k]
                    target_sub.value = ast.Name(id=vname, ctx=ast.Load())
                    emit("SVR", fn_name, getattr(sub, "lineno", fn_node.lineno), cloned)
    return mutants


def run(args: dict[str, Any], root: Any) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    src = _safe_path(repo, str(args.get("source_root") or ""), allow_root=False)
    if not src.exists():
        raise RuntimeError("SOURCE_ROOT_MISSING")
    out = _safe_path(repo, str(args.get("output_path") or ""), allow_root=False)

    proj_root, test_dir, prod_files = _resolve_project_and_tests(src, repo)
    if proj_root in (repo, repo / "canonical", repo / "canonical" / "runtime") or len(prod_files) > 64:
        raise RuntimeError("REFUSING_BROAD_REPO_MUTATION_SCAN")
    if not prod_files:
        raise RuntimeError("NO_PRODUCTION_PYTHON_FILES")

    all_mutants: list[dict[str, Any]] = []
    for pf in prod_files:
        rel_f = pf.relative_to(proj_root).as_posix()
        all_mutants.extend(_generate_mutants_for_file(rel_f, pf.read_text(encoding="utf-8")))
        if len(all_mutants) >= 64:
            all_mutants = all_mutants[:64]
            break

    if not all_mutants:
        raise RuntimeError("NO_MUTANTS_GENERATED")

    with tempfile.TemporaryDirectory(prefix="brain_mut_") as tmp:
        tmp_path = pathlib.Path(tmp)
        work_copy = tmp_path / "proj"
        shutil.copytree(
            proj_root,
            work_copy,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        rel_test_dir = test_dir.relative_to(proj_root)
        spec_file = tmp_path / "mutants.json"
        spec_file.write_text(json.dumps(all_mutants), encoding="utf-8")

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [sys.executable, "-B", "-c", _BATCH_RUNNER, str(work_copy), str(work_copy / rel_test_dir), str(spec_file)],
            cwd=str(work_copy),
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            raise RuntimeError("MUTATION_WORKER_FAILED:" + (proc.stderr or proc.stdout)[:240])
        batch_data = json.loads(proc.stdout.strip().splitlines()[-1])

    flaky_tests: list[str] = list(batch_data.get("flaky_tests") or [])
    if not batch_data.get("baseline_ok"):
        if not flaky_tests:
            raise RuntimeError("BASELINE_TEST_SUITE_FAILED_OR_EMPTY")
        report = {
            "schema": "PROJECT_BRAIN_PYTHON_TESTS_MUTATION_SCORE_V1",
            "adapter": "python_tests_mutation_score",
            "mode": "flaky_detection",
            "source_root": src.relative_to(repo).as_posix() if src != repo else ".",
            "flaky_tests": flaky_tests,
            "total_mutants": 0,
            "killed_count": 0,
            "survived_count": 0,
            "mutation_score": 0.0,
            "verdict": "no",
            "answer": flaky_tests[0],
            "mutants": [],
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
        out.write_bytes(payload)
        sha = hashlib.sha256(out.read_bytes()).hexdigest()
        return {
            "adapter": "python_tests_mutation_score",
            "answer": flaky_tests[0],
            "killed_count": 0,
            "mutation_score": 0.0,
            "output_path": out.relative_to(repo).as_posix(),
            "output_sha256": sha,
            "output_verified": True,
            "survived_count": 0,
            "total_mutants": 0,
            "verdict": "no",
        }

    outcomes: list[str] = batch_data["outcomes"]
    killed = sum(1 for o in outcomes if o == "killed")
    survived = sum(1 for o in outcomes if o == "survived")
    total = len(outcomes)
    score = round(killed / total, 6)
    verdict = "yes" if survived == 0 else "no"

    ledger = [
        {
            "file": m["rel_file"],
            "function": m["function"],
            "lineno": m["lineno"],
            "operator": m["operator"],
            "status": st,
        }
        for m, st in zip(all_mutants, outcomes)
    ]

    report = {
        "schema": "PROJECT_BRAIN_PYTHON_TESTS_MUTATION_SCORE_V1",
        "adapter": "python_tests_mutation_score",
        "source_root": src.relative_to(repo).as_posix() if src != repo else ".",
        "flaky_tests": flaky_tests,
        "total_mutants": total,
        "killed_count": killed,
        "survived_count": survived,
        "mutation_score": score,
        "verdict": verdict,
        "answer": score,
        "mutants": ledger,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out.write_bytes(payload)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    return {
        "adapter": "python_tests_mutation_score",
        "answer": score,
        "killed_count": killed,
        "mutation_score": score,
        "output_path": out.relative_to(repo).as_posix(),
        "output_sha256": sha,
        "output_verified": True,
        "survived_count": survived,
        "total_mutants": total,
        "verdict": verdict,
    }
