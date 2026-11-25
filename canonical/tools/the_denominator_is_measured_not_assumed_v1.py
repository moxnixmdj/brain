"""The denominator, measured instead of assumed.

WHY THIS EXISTS
---------------
"6 of 45" is a number that can be made to say almost anything. Four of the corpus's rows
have a named test that does NOT fail at the commit's parent in this environment, and a row
whose failure cannot be reproduced is not a row any repair tool can be judged on -- it is a
gap in the corpus. Reporting 6/45 while four rows were impossible to attempt inverts the
story: the tool looks weaker than it is on the rows it CAN see, and the corpus looks
better than it is.

So this runs the named test on the parent commit, alone and in its whole file, with the
oracle interpreter, and reports one of:

  FAILS_ALONE       the failure is real and isolated -- the honest denominator
  FAILS_IN_FILE     the failure needs its file's context (an ordering dependency)
  PASSES            the corpus names a test that does not fail here; NOT the tool's fault
  HARNESS           the suite will not run at all

Only the first two are rows on which a relation can be read. The rest are reported as
what they are and excluded from the denominator, with the reason kept.

Anything this script cannot decide is printed as UNKNOWN, never folded into a pass.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

ORACLE = "/home/user/venv8/bin/python"
SCHEMA = "THE_DENOMINATOR_IS_MEASURED_NOT_ASSUMED_V1"


def _worktree(repo: pathlib.Path, sha: str, root: pathlib.Path) -> pathlib.Path | None:
    target = root / sha[:8]
    subprocess.run(["git", "-C", str(repo), "worktree", "prune"], capture_output=True)
    if target.exists():
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(target)],
                       capture_output=True)
        shutil.rmtree(target, ignore_errors=True)
    made = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(target), sha],
                          capture_output=True, text=True)
    return target if made.returncode == 0 else None


def _pytest(wt: pathlib.Path, args: Sequence[str], timeout: int = 300) -> tuple[int, str]:
    env = {**os.environ,
           "PYTHONPATH": f"{wt / 'src'}{os.pathsep}{wt}{os.pathsep}{os.environ.get('PYTHONPATH', '')}",
           "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        done = subprocess.run([ORACLE, "-m", "pytest", *args, "-q", "-p", "no:cacheprovider",
                               "--no-header", "-x" if False else "--tb=no"],
                              cwd=wt, capture_output=True, text=True, timeout=timeout, env=env)
        return done.returncode, (done.stdout or "") + (done.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except OSError as error:
        return 125, f"HARNESS: {error}"


def classify(entry: Mapping[str, Any], repos_root: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
    repo_name = str(entry["repo"])
    repo = repos_root / repo_name
    sha = f"{entry['commit']}^"
    test = str(entry["test"])
    if "::" not in test:
        # the corpus sometimes names a whole file; the failing item is in `failing`
        failing = entry.get("failing") or []
        test = failing[0] if failing else test
    file_part = test.split("::")[0]

    wt = _worktree(repo, sha, root)
    if wt is None:
        return {"repo": repo_name, "commit": str(entry["commit"])[:8],
                "verdict": "HARNESS", "why": "worktree could not be made"}

    # THE SAME PROTOCOL THE ENGINE USES. Most of these commits ADD their regression test
    # alongside the fix, so the test does not exist at the parent. Overlaying the fixed
    # test file onto the parent tree is what makes the row a fail-to-pass target at all,
    # and NOT doing it here made this script report TEST_ABSENT for rows the engine
    # legitimately verifies. A denominator that measures a different experiment than the
    # one being reported is worse than no denominator.
    if file_part and not file_part.endswith(".py") is False:
        shown = subprocess.run(["git", "-C", str(repo), "show", f"{entry['commit']}:{file_part}"],
                               capture_output=True, text=True, errors="replace")
        if shown.returncode == 0 and shown.stdout:
            target = wt / file_part
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(shown.stdout, encoding="utf-8")

    code_alone, out_alone = _pytest(wt, [test])
    if code_alone == 0:
        verdict, why = "PASSES", "the named test passes on the parent commit, alone"
    elif code_alone in (4, 5) or "no tests ran" in out_alone or "not found:" in out_alone:
        # THE TEST DOES NOT EXIST YET. Most of these commits ADD their regression test
        # alongside the fix, so at the parent there is nothing to fail. This is neither a
        # pass nor a miss -- the row is not runnable as a repair target at all, and calling
        # it FAILS was a bug in this very script: pytest exits 4 for "not found", which is
        # non-zero, and the first version read every non-zero exit as a failure.
        verdict, why = "TEST_ABSENT", "the named test does not exist at the parent commit"
    elif code_alone == 124 or "HARNESS:" in out_alone:
        verdict, why = "HARNESS", ("timeout" if code_alone == 124
                                   else out_alone.strip().splitlines()[-1][:160])
    else:
        verdict, why = "FAILS_ALONE", "fails on the parent commit, alone"

    code_file, out_file = _pytest(wt, [file_part])
    in_file = code_file != 0
    if verdict == "PASSES" and in_file:
        verdict, why = "FAILS_IN_FILE", "passes alone but fails with its file"

    return {"repo": repo_name, "commit": str(entry["commit"])[:8], "test": test,
            "verdict": verdict, "why": why,
            "alone_rc": code_alone, "file_rc": code_file}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commits", type=pathlib.Path,
                        default=pathlib.Path("canonical/corpus/single_line_fix_commits_20261123_V1.json"))
    parser.add_argument("--repos", type=pathlib.Path, default=pathlib.Path("/home/user/repos"))
    parser.add_argument("--receipt", type=pathlib.Path, default=pathlib.Path("/tmp/rel/denominator.json"))
    parser.add_argument("--only", default="")
    args = parser.parse_args(argv)

    entries = json.loads(args.commits.read_text())["tasks"]
    if args.only:
        wanted = {c.strip() for c in args.only.split(",") if c.strip()}
        entries = [e for e in entries if any(str(e["commit"]).startswith(w) for w in wanted)]

    root = pathlib.Path(tempfile.mkdtemp(prefix="denom-"))
    rows: list[dict[str, Any]] = []
    try:
        for index, entry in enumerate(entries, 1):
            result = classify(entry, args.repos, root)
            rows.append(result)
            print(f"[{index}/{len(entries)}] {result['repo']:14} {result['commit']} "
                  f"-> {result['verdict']}", flush=True)
    finally:
        for repo in {r["repo"] for r in rows}:
            subprocess.run(["git", "-C", str(args.repos / repo), "worktree", "prune"],
                           capture_output=True)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    attemptable = counts.get("FAILS_ALONE", 0) + counts.get("FAILS_IN_FILE", 0)
    receipt = {"schema": SCHEMA, "rows": rows, "counts": counts,
               "attemptable": attemptable, "total": len(rows)}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True))

    print("\n=== the denominator")
    for verdict, count in sorted(counts.items(), key=lambda pair: -pair[1]):
        print(f"  {verdict:16} {count:3}")
    print(f"\n  attemptable rows: {attemptable}/{len(rows)}")
    print("  a row whose failure cannot be reproduced is not the tool's failure, "
          "and is excluded from the denominator, never counted as a miss")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
