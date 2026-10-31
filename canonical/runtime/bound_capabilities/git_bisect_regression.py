#!/usr/bin/env python3
"""Git history regression bisection & revision performance attribution engine.

Implements ``git.history.bisect_regression.v1`` with zero model cognition and
zero mutation of the caller's working tree:

1. **Test-Failure Bisection (``mode = "commit_bisect"``)**:
   When the discovered ``unittest`` suite fails on ``HEAD``, clones the local
   repository into an isolated scratch directory and performs ``O(log N)``
   binary search over ``git rev-list --reverse HEAD`` to pinpoint the exact
   first commit where the suite transitioned from green to red.

2. **Revision Performance / Complexity Attribution (``mode = "perf_regression"``)**:
   When ``HEAD`` has no failing tests and ``HEAD~1`` exists, inspects every
   Python file changed between ``HEAD~1`` and ``HEAD``, computing both exact
   AST effective asymptotic loop/membership complexity deltas (e.g. ``O(n)``
   ``dict.fromkeys`` -> ``O(n^2)`` ``x not in list`` inside a loop) and isolated
   child-process micro-timings on scaled synthetic inputs to identify the
   function that regressed.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any


def _safe_path(repo: pathlib.Path, raw: str, *, allow_root: bool = False) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if allow_root and p == repo:
        return p
    if p == repo or repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _git(cwd: pathlib.Path, *args: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _find_git_root(start: pathlib.Path, repo: pathlib.Path) -> pathlib.Path:
    cur = start if start.is_dir() else start.parent
    r = _git(cur, "rev-parse", "--show-toplevel")
    if r.returncode != 0:
        raise RuntimeError("NOT_A_GIT_REPOSITORY")
    top = pathlib.Path(r.stdout.strip()).resolve()
    if top != repo and repo not in top.parents:
        raise RuntimeError("GIT_ROOT_OUTSIDE_REPOSITORY")
    return top


def _has_tests(tree_root: pathlib.Path) -> bool:
    for p in tree_root.rglob("*.py"):
        if ".git" in p.parts or "__pycache__" in p.parts:
            continue
        if p.name.startswith("test_") or p.name.endswith("_test.py"):
            return True
    return False


def _suite_root(tree_root: pathlib.Path) -> pathlib.Path:
    """Where the suite actually lives: ``<tree>/tests`` if there is one, else the tree itself."""
    return tree_root / "tests" if (tree_root / "tests").is_dir() else tree_root


def _run_suite(tree_root: pathlib.Path, timeout: int = 20) -> tuple[int, str]:
    if not _has_tests(tree_root):
        return 0, "NO_TESTS"
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(tree_root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    start_dir = str(_suite_root(tree_root))
    proc = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", start_dir, "-t", str(tree_root)],
        cwd=str(tree_root),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    return proc.returncode, (proc.stderr or proc.stdout)[-400:]


def _effective_complexity(fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Structural asymptotic exponent estimate for ``fn_node`` (1 = O(1)/O(n) baseline)."""
    # Track local variables initialized to list/tuple (linear-scan membership targets)
    linear_containers: set[str] = set()
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Assign):
            if isinstance(n.value, (ast.List, ast.Tuple, ast.ListComp)):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        linear_containers.add(t.id)

    best_depth = 0

    def walk(node: ast.AST, depth: int) -> None:
        nonlocal best_depth
        if node is not fn_node and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return
        cur = depth
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            cur = depth + 1
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            cur = depth + len(node.generators)
        if cur > best_depth:
            best_depth = cur

        if cur >= 1 and isinstance(node, ast.Compare):
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, (ast.In, ast.NotIn)):
                    if isinstance(comp, (ast.List, ast.Tuple)) or (
                        isinstance(comp, ast.Name) and comp.id in linear_containers
                    ):
                        best_depth = max(best_depth, cur + 1)
        if cur >= 1 and isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (
                node.func.attr in ("index", "count", "remove")
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in linear_containers
            ):
                best_depth = max(best_depth, cur + 1)

        for child in ast.iter_child_nodes(node):
            walk(child, cur)

    walk(fn_node, 0)
    return best_depth


def _functions_in_source(src_text: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    try:
        tree = ast.parse(src_text)
    except SyntaxError:
        return {}
    out: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = node
    return out


def _micro_slowdown_ratio(old_src: str, new_src: str, fn_name: str) -> float:
    """Isolated child-process timing ratio on a 600-element sequence when callable with 1 iterable arg."""
    probe = (
        "import json, sys, time\n"
        "old_ns, new_ns = {}, {}\n"
        "exec(sys.argv[1], old_ns)\n"
        "exec(sys.argv[2], new_ns)\n"
        "f_old, f_new = old_ns.get(sys.argv[3]), new_ns.get(sys.argv[3])\n"
        "data = [i % 250 for i in range(600)]\n"
        "f_old(list(data)); f_new(list(data))\n"
        "t0 = time.perf_counter_ns()\n"
        "for _ in range(5): f_old(list(data))\n"
        "dt_old = max(1, time.perf_counter_ns() - t0)\n"
        "t1 = time.perf_counter_ns()\n"
        "for _ in range(5): f_new(list(data))\n"
        "dt_new = max(1, time.perf_counter_ns() - t1)\n"
        "print(json.dumps({'ratio': dt_new / dt_old}))\n"
    )
    try:
        r = subprocess.run(
            [sys.executable, "-B", "-c", probe, old_src, new_src, fn_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return round(float(json.loads(r.stdout.strip().splitlines()[-1])["ratio"]), 4)
    except Exception:
        pass
    return 1.0


def _bisect_commits(git_root: pathlib.Path, commits: list[str],
                    suite_rel: str = ".") -> dict[str, Any]:
    """Binary search the history, materialising each revision in ONE shared worktree.

    This used to ``git clone --shared`` the whole repository once and then check out a
    revision per probe.  Measured 2026-10-31 on this repository (241 MB of tracked files):
    the clone alone took 35.5 s against this function's own 30 s timeout, so the row that
    answers "which commit broke the test" timed out on every other run and, when the clone
    did win the race, it ran the REPOSITORY's suite instead of the sentence's test.  A
    worktree shares the object database (8 ms to create, 2.3 s for the first full checkout)
    and a later revision costs one incremental ``reset --hard`` (0.2 s) because git only
    rewrites the files that changed between the two commits.
    """
    probed: list[dict[str, Any]] = []
    suite_rel = str(suite_rel or ".")
    with tempfile.TemporaryDirectory(prefix="brain_bisect_") as tmp:
        wt = pathlib.Path(tmp) / "work"
        added = _git(git_root, "worktree", "add", "--detach", "--no-checkout", str(wt),
                     commits[-1], timeout=120)
        if added.returncode != 0:
            raise RuntimeError("GIT_WORKTREE_FAILED:" + (added.stderr or "").strip()[-200:])
        try:
            return _bisect_in_worktree(wt, commits, suite_rel, probed)
        finally:
            _git(git_root, "worktree", "remove", "--force", str(wt), timeout=120)
            _git(git_root, "worktree", "prune")


def _bisect_in_worktree(wt: pathlib.Path, commits: list[str], suite_rel: str,
                        probed: list[dict[str, Any]]) -> dict[str, Any]:
    def check_idx(idx: int) -> bool:
        sha = commits[idx]
        co = _git(wt, "reset", "--hard", "--quiet", sha, timeout=120)
        if co.returncode != 0:
            raise RuntimeError("GIT_CHECKOUT_FAILED:" + sha)
        rc, _tail = _run_suite(wt / suite_rel if suite_rel != "." else wt)
        ok = rc == 0
        probed.append({"commit": sha, "index": idx, "pass": ok, "returncode": rc})
        return ok

    if not check_idx(0):
        return {
            "mode": "commit_bisect",
            "answer": commits[0],
            "breaking_commit": commits[0],
            "last_good_commit": None,
            "commit_count": len(commits),
            "probed_commits": probed,
        }

    lo = 0
    hi = len(commits) - 1
    probed.append({"commit": commits[hi], "index": hi, "pass": False, "returncode": 1})
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if check_idx(mid):
            lo = mid
        else:
            hi = mid

    return {
        "mode": "commit_bisect",
        "answer": commits[hi],
        "breaking_commit": commits[hi],
        "last_good_commit": commits[lo],
        "commit_count": len(commits),
        "probed_commits": probed,
    }


def _attribute_perf_regression(git_root: pathlib.Path) -> dict[str, Any]:
    diff_res = _git(git_root, "diff", "--name-only", "HEAD~1", "HEAD", "--", "*.py")
    if diff_res.returncode != 0:
        raise RuntimeError("NO_PREVIOUS_COMMIT_FOR_DIFF")
    changed_files = [line.strip() for line in diff_res.stdout.splitlines() if line.strip().endswith(".py")]
    candidates: list[dict[str, Any]] = []
    for rel in sorted(changed_files):
        old_show = _git(git_root, "show", f"HEAD~1:{rel}")
        new_show = _git(git_root, "show", f"HEAD:{rel}")
        if old_show.returncode != 0 or new_show.returncode != 0:
            continue
        old_fns = _functions_in_source(old_show.stdout)
        new_fns = _functions_in_source(new_show.stdout)
        for name in sorted(set(old_fns) & set(new_fns)):
            if ast.dump(old_fns[name]) == ast.dump(new_fns[name]):
                continue
            c_old = _effective_complexity(old_fns[name])
            c_new = _effective_complexity(new_fns[name])
            ratio = _micro_slowdown_ratio(old_show.stdout, new_show.stdout, name)
            candidates.append({
                "file": rel,
                "function": name,
                "old_complexity_rank": c_old,
                "new_complexity_rank": c_new,
                "complexity_delta": c_new - c_old,
                "slowdown_ratio": ratio,
            })
    if not candidates:
        raise RuntimeError("NO_MODIFIED_PYTHON_FUNCTIONS_BETWEEN_REVISIONS")
    candidates.sort(
        key=lambda r: (-r["complexity_delta"], -r["slowdown_ratio"], r["file"], r["function"])
    )
    winner = candidates[0]
    if winner["complexity_delta"] <= 0 and winner["slowdown_ratio"] < 1.5:
        raise RuntimeError("NO_PERFORMANCE_REGRESSION_DETECTED")
    return {
        "mode": "perf_regression",
        "answer": winner["function"],
        "regressed_function": winner["function"],
        "regressed_file": winner["file"],
        "candidates": candidates,
    }


def run(args: dict[str, Any], root: Any) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    src = _safe_path(repo, str(args.get("source_root") or "."), allow_root=True)
    if not src.exists():
        raise RuntimeError("SOURCE_ROOT_MISSING")
    out = _safe_path(repo, str(args.get("output_path") or ""), allow_root=False)
    git_root = _find_git_root(src, repo)

    revs = _git(git_root, "rev-list", "--reverse", "HEAD")
    if revs.returncode != 0 or not revs.stdout.strip():
        raise RuntimeError("EMPTY_GIT_HISTORY")
    commits = [c.strip() for c in revs.stdout.splitlines() if c.strip()]

    # THE SENTENCE NAMES A TEST; THE HISTORY MUST CONTAIN IT.
    #
    # A bisect can only attribute a change that git remembers.  Measured 2026-10-31 on this
    # repository: the named tree was an untracked scratch directory, so the row silently
    # bisected the REPOSITORY's own suite (red on main) and answered "the first commit broke
    # it" -- naming the oldest commit of an unrelated history, after a 35 s clone.  A path
    # git does not track is refused here, in milliseconds, before anything is materialised.
    suite_dir = src if src.is_dir() else src.parent
    suite_rel = suite_dir.relative_to(git_root).as_posix() if suite_dir != git_root else "."
    tracked = _git(git_root, "ls-tree", "-r", "--name-only", "HEAD", "--", suite_rel or ".")
    if tracked.returncode != 0 or not tracked.stdout.strip():
        raise RuntimeError("NAMED_TEST_NOT_IN_GIT_HISTORY:" + (suite_rel or "."))

    head_rc, _head_tail = _run_suite(suite_dir)
    if head_rc != 0 and _has_tests(suite_dir):
        details = _bisect_commits(git_root, commits, suite_rel)
    else:
        if len(commits) < 2:
            raise RuntimeError("INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS")
        details = _attribute_perf_regression(git_root)

    report = {
        "schema": "PROJECT_BRAIN_GIT_BISECT_REGRESSION_V1",
        "adapter": "git_bisect_regression",
        "git_root": git_root.relative_to(repo).as_posix() if git_root != repo else ".",
        **details,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out.write_bytes(payload)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    return {
        "adapter": "git_bisect_regression",
        "answer": report["answer"],
        "mode": report["mode"],
        "output_path": out.relative_to(repo).as_posix(),
        "output_sha256": sha,
        "output_verified": True,
    }
