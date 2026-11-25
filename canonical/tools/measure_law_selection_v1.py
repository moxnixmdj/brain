"""Does a law recur, and does a firing law select the repair? Reproduces the V25 numbers.

Usage:
  python3 canonical/tools/measure_law_selection_v1.py --repos-dir /tmp/repos --per-repo 4

Pipeline, per repository:
  1. enumerate recent commits that change a module and a test;
  2. KEEP ONLY CONFIRMED FIXES -- the commit's own test file must genuinely fail on its parent
     (a failure, not a collection error and not "no tests ran"). Sampling unfiltered commits mixes in
     refactors and import errors and makes every rate meaningless;
  3. run the law suite on the parent tree and on the fix, and record which laws fire, which of those go
     silent on the fix (a law catching THIS bug), and whether the witness names a class-qualified
     function the human changed (law -> repair selection);
  4. optionally record whether the witness is on the failing test's call path, which is the only
     discrimination signal available at runtime when there is no fixed tree to compare against.

Every number is computed at run time; nothing here is asserted.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.swe_kernel import metamorphic_oracle_v1 as oracle  # noqa: E402

CALLPATH_PLUGIN = '''
import json, os, sys
SEEN = set()
def _prof(frame, event, arg):
    if event == "call":
        code = frame.f_code
        SEEN.add((os.path.basename(code.co_filename), code.co_name))
def pytest_runtest_call(item):
    sys.setprofile(_prof)
def pytest_runtest_teardown(item, nextitem):
    sys.setprofile(None)
    path = os.environ.get("CALLPATH_OUT")
    if path:
        with open(path, "w") as handle:
            json.dump(sorted(SEEN), handle)
'''


def git(repo_dir: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo_dir), *args], capture_output=True, text=True).stdout


def changed_files(repo_dir: pathlib.Path, sha: str):
    files = [f for f in git(repo_dir, "show", "--name-only", "--format=", sha, "--", "*.py").split("\n")
             if f.endswith(".py")]
    modules = [f for f in files if "test" not in pathlib.Path(f).name.lower() and "/test" not in f]
    tests = [f for f in files if "test" in pathlib.Path(f).name.lower() or "/test" in f]
    return modules, tests


def qualified_changes(repo_dir: pathlib.Path, sha: str, path: str) -> set[str]:
    pre, post = git(repo_dir, "show", f"{sha}^1:{path}"), git(repo_dir, "show", f"{sha}:{path}")
    if not pre.strip() or not post.strip():
        return set()
    try:
        before_tree, after_tree = ast.parse(pre), ast.parse(post)
    except SyntaxError:
        return set()

    def index(tree: ast.AST) -> dict[str, str]:
        out: dict[str, str] = {}
        for cls in ast.walk(tree):
            if isinstance(cls, ast.ClassDef):
                for node in cls.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        out[f"{cls.name}.{node.name}"] = ast.unparse(node)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.setdefault(node.name, ast.unparse(node))
        return out

    before, after = index(before_tree), index(after_tree)
    return {n for n in set(before) | set(after) if before.get(n) != after.get(n)}


def module_name(path: str) -> str:
    parts = list(pathlib.Path(path).with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts)


def worktree(repo_dir: pathlib.Path, rev: str, tag: str) -> pathlib.Path:
    dest = pathlib.Path(tempfile.gettempdir()) / f"lawsel_{repo_dir.name}_{tag}"
    subprocess.run(["git", "-C", str(repo_dir), "worktree", "remove", "--force", str(dest)], capture_output=True)
    subprocess.run(["git", "-C", str(repo_dir), "worktree", "add", "-f", "--detach", str(dest), rev], capture_output=True)
    return dest


def drop_tests(repo_dir: pathlib.Path, dest: pathlib.Path, sha: str, tests, files) -> None:
    for path in tests:
        content = git(repo_dir, "show", f"{sha}:{path}")
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def confirm_fix(repo_dir: pathlib.Path, sha: str, tests) -> tuple[bool, str]:
    dest = worktree(repo_dir, f"{sha}^1", f"{sha[:7]}_confirm")
    drop_tests(repo_dir, dest, sha, tests, None)
    env = dict(**{"PYTHONPATH": f"{dest}:{dest / 'src'}", "PYTHONDONTWRITEBYTECODE": "1"})
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", *tests[:2]], cwd=str(dest),
                          env={**env}, capture_output=True, text=True, timeout=300)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    last = out.splitlines()[-1] if out else ""
    subprocess.run(["git", "-C", str(repo_dir), "worktree", "remove", "--force", str(dest)], capture_output=True)
    genuinely_failed = " failed" in last and "error" not in last.lower() and "no tests ran" not in last
    return genuinely_failed, last[:100]


def law_run(repo_dir: pathlib.Path, rev: str, modules, tests, tag: str) -> dict:
    root = worktree(repo_dir, rev, tag)
    try:
        result = oracle.violations_from_run(root, modules, ["-q", *tests[:2]], timeout_s=240)
        return {"laws": sorted({v.get("law", "?") for v in result.violations}),
                "witnesses": sorted({v.get("where", "?") for v in result.violations})}
    except Exception as exc:  # pragma: no cover - environment
        return {"laws": [], "witnesses": [], "error": f"{type(exc).__name__}: {exc}"[:120]}
    finally:
        subprocess.run(["git", "-C", str(repo_dir), "worktree", "remove", "--force", str(root)], capture_output=True)


def reachability(repo_dir: pathlib.Path, sha: str, row: dict) -> list[str]:
    """Which witnesses sit on the failing test's call path (runtime-available discrimination)."""
    dest = worktree(repo_dir, f"{sha}^1", f"{sha[:7]}_reach")
    drop_tests(repo_dir, dest, sha, row["tests"], None)
    plugin_dir = pathlib.Path(tempfile.mkdtemp(prefix="callpath_"))
    (plugin_dir / "callpath_plugin.py").write_text(CALLPATH_PLUGIN)
    dump = plugin_dir / "calls.json"
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin",
           "PYTHONPATH": f"{plugin_dir}:{dest}:{dest / 'src'}",
           "CALLPATH_OUT": str(dump), "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "callpath_plugin", *row["tests"][:2]],
                       cwd=str(dest), env=env, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        pass
    finally:
        subprocess.run(["git", "-C", str(repo_dir), "worktree", "remove", "--force", str(dest)], capture_output=True)
    if not dump.exists():
        return []
    called = {function for _file, function in json.loads(dump.read_text())}
    out = []
    for witness in row["witnesses"]:
        head = witness.split(" / ")[0]
        if head.split(".")[-1] in called:
            out.append(witness)
    return out


def failing_nodeids(dest: pathlib.Path, tests) -> list[str]:
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin",
           "PYTHONPATH": f"{dest}:{dest / 'src'}", "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", *tests[:2]], cwd=str(dest), env=env,
                          capture_output=True, text=True, timeout=300)
    return [line.split(" ")[1].split(" - ")[0]
            for line in ((proc.stdout or "") + (proc.stderr or "")).splitlines()
            if line.startswith("FAILED ")]


def selectors(repo_dir: pathlib.Path, sha: str, row: dict) -> dict:
    """Two runtime-available discriminators, both measured against the human fix as ground truth.

    isolation: run ONLY the failing test. Inherited debt usually needs the rest of the suite to fire.
    deselection: run the suite with the failing test REMOVED. A violation that survives does not need
    this test at all. The two are complementary on the sample that motivated them: isolation keeps
    both true detections but also keeps two violations the human fix did not address, while
    deselection keeps precision at the cost of missing a detection that other tests also trigger.
    """
    dest = worktree(repo_dir, f"{sha}^1", f"{sha[:7]}_sel")
    try:
        drop_tests(repo_dir, dest, sha, row["tests"], None)
        ids = failing_nodeids(dest, row["tests"])
        if not ids:
            return {"failing_tests": [], "isolated_laws": [], "surviving_without_failing_test": []}
        isolated = oracle.violations_from_run(dest, row["modules"], ["-q", *ids], timeout_s=240)
        deselected = oracle.violations_from_run(
            dest, row["modules"], ["-q", *row["tests"][:2], *[f"--deselect={i}" for i in ids]], timeout_s=240)
        return {"failing_tests": ids,
                "isolated_laws": sorted({v.get("law", "?") for v in isolated.violations}),
                "surviving_without_failing_test": sorted({v.get("law", "?") for v in deselected.violations})}
    finally:
        subprocess.run(["git", "-C", str(repo_dir), "worktree", "remove", "--force", str(dest)],
                       capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos-dir", default="/tmp/repos")
    parser.add_argument("--repos", default="pluggy,werkzeug,more-itertools,pyjwt,click,attrs")
    parser.add_argument("--per-repo", type=int, default=4)
    parser.add_argument("--max-attempts", type=int, default=24)
    parser.add_argument("--reachability", action="store_true")
    parser.add_argument("--selectors", action="store_true",
                        help="also run the isolation and deselection discriminators on firing commits")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    rows: list[dict] = []
    for repo in [r.strip() for r in args.repos.split(",") if r.strip()]:
        repo_dir = pathlib.Path(args.repos_dir) / repo
        if not (repo_dir / ".git").exists():
            continue
        shas = git(repo_dir, "log", "--no-merges", "-n300", "--format=%H", "--", "*.py").split()
        kept = attempts = 0
        for sha in shas:
            if kept >= args.per_repo or attempts >= args.max_attempts:
                break
            modules, tests = changed_files(repo_dir, sha)
            if not modules or not tests:
                continue
            attempts += 1
            ok, tail = confirm_fix(repo_dir, sha, tests)
            print(f"{repo}@{sha[:7]} confirm={'real fix' if ok else 'skip'} [{tail}]", flush=True)
            if not ok:
                continue
            kept += 1
            names = [module_name(m) for m in modules]
            human: set[str] = set()
            for module in modules:
                human |= qualified_changes(repo_dir, sha, module)
            buggy = law_run(repo_dir, f"{sha}^1", names, tests, f"{sha[:7]}_buggy")
            fixed = law_run(repo_dir, sha, names, tests, f"{sha[:7]}_fixed")
            fired = set(buggy["laws"])
            row = {"repo": repo, "sha": sha[:7], "modules": names, "tests": tests[:2],
                   "human_changed": sorted(human), "buggy_laws": sorted(fired),
                   "fixed_laws": fixed["laws"], "refuted": sorted(fired - set(fixed["laws"])),
                   "witnesses": buggy["witnesses"],
                   "localized": sorted({w for w in buggy["witnesses"]
                                        if any(h.split(".")[-1] in w for h in human)})}
            if args.reachability and fired:
                row["reached"] = reachability(repo_dir, sha, row)
            if args.selectors and fired:
                row.update(selectors(repo_dir, sha, row))
            rows.append(row)
            print(f"   laws={sorted(fired)} refuted={row['refuted']} localized={len(row['localized'])}"
                  f"{' reached=' + str(len(row.get('reached', []))) if args.reachability else ''}", flush=True)

    laws_fired = [law for row in rows for law in row["buggy_laws"]]
    recurring = {law for law in set(laws_fired) if sum(1 for r in rows if law in r["buggy_laws"]) >= 2}
    summary = {
        "confirmed_fixes": len(rows),
        "commits_with_a_firing_law": sum(1 for r in rows if r["buggy_laws"]),
        "distinct_laws_fired": len(set(laws_fired)),
        "laws_firing_in_2_or_more_commits": sorted(recurring),
        "commits_refuted_by_their_own_fix": sum(1 for r in rows if r["refuted"]),
        "commits_localized_to_a_changed_function": sum(1 for r in rows if r["localized"]),
    }
    if args.reachability:
        reached = sum(1 for r in rows if r.get("reached"))
        summary["firing_commits_whose_witness_is_on_the_failing_path"] = reached
    if args.selectors:
        firing = [r for r in rows if r.get("failing_tests")]
        inherited = [r for r in firing if not r["refuted"]]
        summary["selectors"] = {
            "firing_commits_with_a_failing_test_id": len(firing),
            "isolated_laws_select_a_law_the_fix_removes":
                sum(1 for r in firing if set(r.get("isolated_laws", [])) & set(r["refuted"])),
            "inherited_firings_silenced_by_isolation":
                sum(1 for r in inherited if not r.get("isolated_laws")),
            "inherited_firings_total": len(inherited),
            "violations_surviving_without_the_failing_test":
                sum(1 for r in firing if r.get("surviving_without_failing_test")),
        }
    print(json.dumps(summary, indent=1))
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps({"rows": rows, "summary": summary}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
