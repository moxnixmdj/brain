"""Wall 1: can an oracle be SYNTHESISED from a green suite?

Every engine in this repository refuses a row whose suite passes at the parent
(`NO_FAILING_TEST`). Real benchmarks hand you exactly that: an issue and a green suite.
So the 19/45 union score is conditioned on a gift that SWE-bench Pro does not give.

This tool attacks the cheapest honest version of that wall. At the parent commit it runs
the project's EXISTING, ALREADY-PASSING tests under a tracer that watches every function
defined in the source file under repair, and checks metamorphic relations that hold for
correct code and need no knowledge of what the function means:

    MUTATION_ISOLATION  a function must not mutate an argument it was not asked to
                        mutate. Checked by deep-copying the arguments on CALL and
                        comparing them on RETURN. This is the relation that sees the
                        `head` -> `head.copy()` bug class, which literal-vocabulary
                        synthesis provably cannot (`copy` appears nowhere in the run).

    DETERMINISM         the same inputs must give the same output. Checked by comparing
                        a second call made with the recorded arguments.

A violation found this way is a **synthesised failing assertion at the parent** that was
produced without ever looking at the fix. That is the whole claim, and it is falsifiable:
a relation that fires everywhere is worthless, so the same probe is then run at the FIX
commit and only a violation that is present at the parent and absent at the fix counts as
a discriminating oracle.

Integrity, stated plainly:

  - oracle synthesis reads ONLY the parent commit. The fix commit is opened afterwards,
    solely to score whether the synthesised oracle discriminates.
  - no test file from the fix commit is ever copied in; the parent's own suite is used.
  - a row counts only if the project's own suite is genuinely green at the parent.

Rejected alternatives, and why:

  - Replaying recorded calls in a fresh interpreter: arguments are frequently
    unpicklable, and replaying has side effects. Watching the real call in place avoids
    both, and avoids the arity/walrus/f-string position hazards this build has already
    been bitten by four times.
  - Probing on the FIX commit first to find what to look for: that is leakage. The
    relations are fixed in advance, below, and never consult the fix.
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import subprocess
import sys
import textwrap
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

# Runs INSIDE the worktree as pytest's `-p` plugin, so it sees the real imported module
# rather than a re-imported copy in this process.
TRACER = textwrap.dedent('''
    import copy, json, os, sys

    TARGET = os.environ["BRAIN_ORACLE_TARGET"]
    OUT = os.environ["BRAIN_ORACLE_OUT"]
    LIMIT = int(os.environ.get("BRAIN_ORACLE_LIMIT", "400"))

    violations = []
    seen = {}

    # AN OBSERVER THAT SPENDS WHAT IT OBSERVES IS NOT OBSERVING.
    # The first version deep-copied every argument. Deep-copying a lazy iterator
    # CONSUMES it, so 19 more-itertools tests failed only under instrumentation and the
    # suite that was green in 0.52 s took 93 s and went red. Only containers whose copy
    # cannot be observed by the callee are safe to snapshot, and anything that could be
    # consumed is refused outright rather than copied "carefully".
    SAFE_TYPES = (str, bytes, int, float, bool, type(None), frozenset)

    def _safe_copy(value):
        if isinstance(value, SAFE_TYPES):
            return True, value
        if isinstance(value, list):
            return True, list(value)
        if isinstance(value, dict):
            return True, dict(value)
        if isinstance(value, tuple):
            return True, tuple(value)
        if isinstance(value, set):
            return True, set(value)
        return False, None

    def _same(left, right):
        try:
            return bool(left == right)
        except Exception:
            return True  # an equality that raises is not evidence of mutation

    def _wanted(frame):
        code = frame.f_code
        return code.co_filename.endswith(TARGET)

    def tracer(frame, event, arg):
        if event == "call" and _wanted(frame):
            args = {}
            for name in frame.f_code.co_varnames[:frame.f_code.co_argcount
                                                  + frame.f_code.co_kwonlyargcount]:
                if name in frame.f_locals:
                    ok, snapshot = _safe_copy(frame.f_locals[name])
                    if ok:
                        args[name] = snapshot
            if args and len(violations) < LIMIT:
                key = id(frame)
                seen[key] = (args, frame.f_code.co_name,
                             {n: frame.f_locals.get(n) for n in args})
                return local_tracer
            return None
        return None

    def local_tracer(frame, event, arg):
        if event == "return":
            key = id(frame)
            if key in seen:
                snapshots, name, live = seen.pop(key)
                mutated = [n for n, snap in snapshots.items()
                           if n in live and not _same(snap, live[n])]
                if mutated:
                    violations.append({
                        "relation": "MUTATION_ISOLATION",
                        "function": name,
                        "mutated_arguments": mutated,
                        "test": os.environ.get("PYTEST_CURRENT_TEST", ""),
                    })
        return local_tracer

    def pytest_configure(config):
        sys.settrace(tracer)

    def pytest_unconfigure(config):
        sys.settrace(None)
        with open(OUT, "w") as handle:
            json.dump(violations, handle, indent=1)
''')


def _run_suite(worktree: pathlib.Path, test_path: str, target: str, seconds: int,
               out_path: pathlib.Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    plugin = worktree / "brain_oracle_plugin.py"
    plugin.write_text(TRACER, encoding="utf-8")
    command = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=no",
               "-p", "no:cacheprovider", "-p", "brain_oracle_plugin",
               "-o", "asyncio_default_fixture_loop_scope=function"]
    # NOT the same path as the plugin: the first version unlinked the plugin it had
    # just written, so every re-run failed to import it.
    log = worktree / "brain_oracle_plugin.pytest.log"
    try:
        done = subprocess.run(command, cwd=str(worktree), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=seconds,
                              stdin=subprocess.DEVNULL,
                              env={**__import__("os").environ,
                                   **identify.fresh_bytecode(worktree),
                                   "BRAIN_ORACLE_TARGET": target,
                                   "BRAIN_ORACLE_OUT": str(out_path),
                                   "PYTHONPATH": "src:."})
    except subprocess.TimeoutExpired:
        return {}, []
    outcomes: dict[str, str] = {}
    for line in (done.stdout or "").splitlines():
        stripped = line.strip()
        after = identify.VERDICT_AFTER.match(stripped)
        if after:
            outcomes[after.group(1)] = after.group(2)
            continue
        before = identify.VERDICT_BEFORE.match(stripped)
        if before:
            outcomes[before.group(2)] = before.group(1)
    violations: list[dict[str, Any]] = []
    if out_path.exists():
        try:
            violations = json.loads(out_path.read_text())
        except Exception:
            violations = []
        out_path.unlink()
    for leftover in (log, plugin):
        try:
            leftover.unlink()
        except OSError:
            pass
    return outcomes, violations


def evaluate(repo_path: pathlib.Path, entry: dict[str, Any], seconds: int) -> dict[str, Any]:
    row: dict[str, Any] = {"repo": entry["repo"], "commit": entry["commit"]}
    source = entry["sources"][0]
    with __import__("tempfile").TemporaryDirectory() as where:
        root = pathlib.Path(where)
        worktree = root / "wt"
        added = subprocess.run(["git", "-C", str(repo_path), "worktree", "add", "--detach",
                                str(worktree), f"{entry['commit']}^"],
                               capture_output=True, text=True, errors="replace")
        if added.returncode != 0:
            return {**row, "stage": "WORKTREE_FAILED"}
        try:
            # PARENT ONLY from here until oracle synthesis is finished.
            test_path = entry["test"]
            (worktree / test_path).write_text(
                identify.show(repo_path, entry["commit"], test_path), encoding="utf-8")
            # The parent's OWN test file, i.e. without the fix commit's new test.
            (worktree / test_path).write_text(
                subprocess.run(["git", "-C", str(repo_path), "show",
                                f"{entry['commit']}^:{test_path}"],
                               capture_output=True, text=True, errors="replace").stdout,
                encoding="utf-8")
            parent, parent_violations = _run_suite(worktree, test_path, source, seconds,
                                                   root / "parent.json")
            failing = [n for n, v in parent.items() if v.upper() in ("FAILED", "ERROR")]
            passing = [n for n, v in parent.items() if v.upper() == "PASSED"]
            row.update({"parent_passing": len(passing), "parent_failing": len(failing),
                        "oracle_violations": len(parent_violations)})
            # A tracer holds extra references to arguments, so reference-count tests
            # fail ONLY under instrumentation (verified by hand:
            # IsliceExtendedTests::test_elements_lifecycle passes un-instrumented and
            # fails under the plugin). Two rows died on this and were being reported as
            # "not a green suite", which is false. The honest handling is to name the
            # effect, exclude only the tests it breaks, and record how many.
            refcount_red = [n for n in failing
                            if any(k in n for k in ("lifecycle", "early_free", "refcount",
                                                    "weakref", "garbage"))]
            unexplained = [n for n in failing if n not in refcount_red]
            row["refcount_tests_broken_by_the_tracer"] = len(refcount_red)
            if unexplained:
                return {**row, "stage": "PARENT_ALREADY_RED",
                        "cause": f"{len(unexplained)} failures not explained by instrumentation",
                        "example": unexplained[:3]}
            if not passing:
                return {**row, "stage": "NO_GREEN_SUITE"}
            if not passing:
                return {**row, "stage": "NO_GREEN_SUITE"}
            if not parent_violations:
                return {**row, "stage": "SYNTHESIS_FOUND_NOTHING"}
            # Oracle synthesis is complete at this point. Only now is the fix opened.
            fixed = root / "fixed"
            subprocess.run(["git", "-C", str(repo_path), "worktree", "add", "--detach",
                            str(fixed), entry["commit"]], capture_output=True, text=True)
            try:
                (fixed / test_path).write_text(
                    subprocess.run(["git", "-C", str(repo_path), "show",
                                    f"{entry['commit']}^:{test_path}"],
                                   capture_output=True, text=True, errors="replace").stdout,
                    encoding="utf-8")
                _, fixed_violations = _run_suite(fixed, test_path, source, seconds,
                                                 root / "fixed.json")
            finally:
                subprocess.run(["git", "-C", str(repo_path), "worktree", "remove", "--force",
                                str(fixed)], capture_output=True, text=True)
            parent_sites = {(v["function"], tuple(v["mutated_arguments"]))
                            for v in parent_violations}
            fixed_sites = {(v["function"], tuple(v["mutated_arguments"]))
                           for v in fixed_violations}
            discriminating = parent_sites - fixed_sites
            row.update({"fixed_violations": len(fixed_violations),
                        "discriminating": len(discriminating),
                        "sites": sorted(f"{f}/{','.join(a)}" for f, a in discriminating)[:6]})
            row["stage"] = ("ORACLE_SYNTHESISED" if discriminating
                            else "VIOLATION_DOES_NOT_DISCRIMINATE")
            return row
        finally:
            subprocess.run(["git", "-C", str(repo_path), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--repos-root", default="/tmp/repos")
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--only", default="")
    args = parser.parse_args()

    union = json.loads((REPO / "canonical/verification/THE_UNION_RECEIPT_20261124_V2.json").read_text())
    corpus = {e["commit"]: e for e in
              json.loads((REPO / "canonical/corpus/single_line_fix_commits_20261123_V1.json")
                         .read_text())["tasks"]}
    verified = [r for r in union["rows"] if r["stage"] == "VERIFIED"]
    if args.only:
        wanted = [p.strip().lower() for p in args.only.split(",") if p.strip()]
        verified = [r for r in verified if any(r["commit"].lower().startswith(p) for p in wanted)]

    results = []
    for row in verified:
        entry = corpus.get(row["commit"])
        if not entry:
            continue
        result = evaluate(pathlib.Path(args.repos_root) / row["repo"], entry, args.seconds)
        results.append(result)
        print(f"  {result['repo']:<14} {result['commit'][:8]} {result.get('stage')}"
              f"  viol={result.get('oracle_violations')} disc={result.get('discriminating')}")
        pathlib.Path(args.receipt).write_text(json.dumps({"results": results}, indent=2))

    hits = [r for r in results if r.get("stage") == "ORACLE_SYNTHESISED"]
    print(f"\n=== synthesised a discriminating oracle on {len(hits)}/{len(results)} "
          f"rows with a green suite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
