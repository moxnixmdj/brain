"""Before a row is called an engine failure: prove the harness produced an oracle.

Written because three separate sessions recorded "the engine cannot do this row" when the
truth was a missing package, a pytest config incompatibility, or a standard-library
removal:

  - werkzeug rows: `markupsafe` unpinned -> `NO_PASSING_TEST`
  - werkzeug row:  `requests` unpinned   -> `NO_ORACLE`
  - starlette row: imported at a commit that needs a dep the corpus never needed
  - pyjwt rows:    `[pytest]` in setup.cfg rejected by pytest 9, then `--cov` demanding
                   pytest-cov, then `from collections import Mapping` (removed in 3.10)

Each of those produces a stage name that reads as "the engine is not capable". None of
them is about the engine at all. This preflight answers one question per row, cheaply and
before any engine runs:

    is there a run of this project's own test file, on this machine, that produces at
    least one passing and at least one failing verdict?

and if not, WHY -- classifying the cause rather than reporting a capability limit.

The classification is deliberately blunt. Every category below is something a competent
person fixes in minutes, and none of them belongs in a failure rate.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

# Causes, in the order they must be checked: each can mask the next.
CAUSES: tuple[tuple[str, str], ...] = (
    ("PYTEST_CONFIG_SECTION",
     r"\[pytest\] section in setup\.cfg files is no longer supported"),
    ("MISSING_PLUGIN", r"unrecognized arguments: .*--cov|: error: unrecognized arguments"),
    ("MISSING_MODULE", r"ModuleNotFoundError: No module named '([\w.]+)'"),
    ("STDLIB_REMOVAL", r"ImportError: cannot import name '\w+' from 'collections'"),
    ("SYNTAX_FOR_THIS_INTERPRETER", r"SyntaxError: .*"),
    ("FIXTURE_OR_COLLECTION_ERROR", r"ERROR .*::|Interrupted: .* error during collection"),
)


def classify(output: str) -> tuple[str, str]:
    for name, pattern in CAUSES:
        found = re.search(pattern, output)
        if found:
            return name, found.group(0)[:160]
    return "UNCLASSIFIED", output.strip().splitlines()[-1][:160] if output.strip() else ""


def preflight(repo_path: pathlib.Path, entry: dict[str, Any], seconds: int) -> dict[str, Any]:
    row: dict[str, Any] = {"repo": entry["repo"], "commit": entry["commit"]}
    with __import__("tempfile").TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo_path), "worktree", "add", "--detach",
                                str(worktree), f"{entry['commit']}^"],
                               capture_output=True, text=True, errors="replace")
        if added.returncode != 0:
            return {**row, "verdict": "WORKTREE_FAILED", "cause": added.stderr[:200]}
        try:
            test_path = entry["test"]
            (worktree / test_path).write_text(
                identify.show(repo_path, entry["commit"], test_path), encoding="utf-8")
            command = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short",
                       "-p", "no:cacheprovider",
                       "-o", "asyncio_default_fixture_loop_scope=function"]
            done = subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=seconds,
                                  stdin=subprocess.DEVNULL,
                                  env={**__import__("os").environ,
                                       **identify.fresh_bytecode(worktree)})
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
            passing = sum(1 for v in outcomes.values() if v.upper() == "PASSED")
            failing = sum(1 for v in outcomes.values() if v.upper() in ("FAILED", "ERROR"))
            row.update({"passing": passing, "failing": failing})
            if passing and failing:
                return {**row, "verdict": "ORACLE_EXISTS", "cause": ""}
            if not passing and not failing:
                cause, evidence = classify((done.stdout or "") + (done.stderr or ""))
                return {**row, "verdict": "NO_ORACLE__ENVIRONMENT", "cause": cause,
                        "evidence": evidence}
            if passing and not failing:
                return {**row, "verdict": "NO_FAILING_TEST__ROW_IS_NOT_A_BUG_FIX",
                        "cause": "the commit's test file passes on the parent"}
            return {**row, "verdict": "NO_PASSING_TEST__ORACLE_UNUSABLE",
                    "cause": "every test fails before any edit"}
        finally:
            subprocess.run(["git", "-C", str(repo_path), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commits", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--repos-root", default="/tmp/repos")
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--only", default="")
    args = parser.parse_args()

    entries = json.loads(pathlib.Path(args.commits).read_text())["tasks"]
    if args.only:
        wanted = [p.strip().lower() for p in args.only.split(",") if p.strip()]
        entries = [e for e in entries if any(e["commit"].lower().startswith(p) for p in wanted)]

    results = []
    for entry in entries:
        result = preflight(pathlib.Path(args.repos_root) / entry["repo"], entry, args.seconds)
        results.append(result)
        detail = result.get("evidence") or result.get("cause") or ""
        print(f"  {result['repo']:<12} {result['commit'][:8]} {result['verdict']:<38} {detail[:60]}")
        pathlib.Path(args.receipt).write_text(json.dumps({"results": results}, indent=2))

    counts: dict[str, int] = {}
    for result in results:
        counts[result["verdict"]] = counts.get(result["verdict"], 0) + 1
    print("\n===", counts)
    environment = sum(v for k, v in counts.items() if k.startswith("NO_ORACLE__ENVIRONMENT")
                      or k.startswith("NO_PASSING_TEST"))
    print(f"=== rows where the harness, not the engine, decided the outcome: "
          f"{environment}/{len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
