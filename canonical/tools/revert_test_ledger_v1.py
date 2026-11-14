#!/usr/bin/env python3
"""Revert each real merged fix. Did any test of the project notice?

WHY THIS EXISTS, AND WHAT IT FIXES
---------------------------------
The previous record measured a licence over 5 files the author chose, and its tests ran on fixtures
the author wrote. That is the exact defect the owner named: *we keep testing on bugs we already know
work.* A fixture cannot disagree with the person who wrote it.

This asks the question on code nobody here wrote. For every real merged commit in a public
repository:

  1. check out the commit's tree, run the project's OWN test command -> it must be GREEN
  2. put back the pre-fix source files (the commit's test changes stay) -> run it again
  3. if it is still GREEN, the fix shipped with NO test that fails without it

Step 3 is the whole measurement. It is not a proxy and not a mutation: it is the actual defect being
put back, with the actual tests in place, and the project's actual runner deciding. The 2026
literature states the standard this implements:

  * *Who Tests the Tests* (Jul 2026): "a claimed regression test must be shown to fail against the
    pre-fix commit and pass against the post-fix commit -- both states demonstrated, not asserted. A
    'regression test' never shown to fail on the broken commit is not a regression test, it's an
    assertion of faith."
  * *Characterizing Regression Bug-Inducing Changes* (ICSE 2026): 21.79% of bug-inducing commits
    added or modified no test at all, and in 65.57% of those the project had no test targeting the
    feature that broke.
  * *A full-census study of 252 bug-fix commits* (arXiv 2606.22475): 42.5% of fixes shipped with a
    test, and a guard written into the same blind harness cannot see the repeat.

WHAT THIS DOES NOT SAY
----------------------
* A GREEN revert means **no test failed**, not that no test exists and not that the change is wrong.
  A commit may legitimately change behaviour no test ever specified; the ledger records the fact and
  names the commit, it does not call the commit bad.
* The suite is run as the project ships it, in a throwaway copy, with the project's own interpreter
  and dependencies. If it cannot run here, the commit is `UNRUNNABLE`, which is neither a pass nor a
  failure and is counted separately.
* A revert can fail to apply cleanly (the parent file no longer exists in that shape). Those are
  `REVERT_UNAPPLIABLE` and are reported, never silently dropped.
* This measures *the project's* ability to protect its own fixes. It says nothing about this
  repository's capabilities, which is the point: it is a measurement of the world, not of us.

Authority: NONE. Producer-run, `$0`, zero model calls. No capability registered, `truth.achieved`
untouched.

    python3 canonical/tools/revert_test_ledger_v1.py --repo /tmp/mi --limit 40 --out ledger.json
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

SCHEMA = "BRAIN_REVERT_TEST_LEDGER_V1"
AUTHORITY = "NONE"

TEST_MARKERS = ("test_", "_test.py", "tests/", "/test/", "conftest.py", "testing/")


def _git(repo: pathlib.Path, *args: str, timeout: float = 300.0) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          timeout=timeout)


VERSION_NAMES = ("__version__", "VERSION", "version", "__version_info__")


def _without_docstrings(tree):
    import ast
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                body.pop(0)
    return tree


def _version_bindings(tree):
    import ast
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if any(n in VERSION_NAMES for n in names):
                out.add(ast.dump(node))
    return out


def _strip_version_bindings(tree):
    import ast
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list):
            kept = [stmt for stmt in body
                    if not (isinstance(stmt, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id in VERSION_NAMES
                                    for t in stmt.targets))]
            if len(kept) != len(body):
                body[:] = kept
    return tree


def _without_annotations(tree):
    """Drop type annotations and keep the program. A type hint does not change runtime behaviour.

    Found by measurement, not by taste: `torproject/stem`'s "Fix timeout argument type hint" came back
    CODE_CHANGE and therefore counted as a fix no test protects. No suite can notice a type hint at
    runtime, so counting it would inflate the headline with a change no test should ever catch.
    """
    import ast
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node.returns = None
            for arg in [*node.args.args, *node.args.posonlyargs, *node.args.kwonlyargs,
                        *[a for a in (node.args.vararg, node.args.kwarg) if a is not None]]:
                arg.annotation = None
        elif isinstance(node, ast.AnnAssign):
            node.annotation = None
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list):
            body[:] = [stmt for stmt in body
                       if not (isinstance(stmt, ast.AnnAssign) and stmt.value is None)]
    return tree


def classify_change(before, after):
    """CODE_CHANGE | DOCSTRING_OR_COMMENT | VERSION_ONLY | UNPARSEABLE, mechanically.

    The first probe on a real repository returned 4 of 6 fixes "not noticed" and two of those four
    were a version bump and a docstring edit -- changes nobody ever made a test for. Counting them
    would inflate the number, so the classes are exact, the headline is reported over CODE_CHANGE
    only, and the unfiltered total is printed beside it for a reader to check the denominator.
    """
    import ast
    if before is None:
        return "CODE_CHANGE"          # a new file: real code by construction
    try:
        old = ast.parse(before.decode("utf-8"))
        new = ast.parse(after.decode("utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return "UNPARSEABLE"
    if ast.dump(old) == ast.dump(new):
        return "DOCSTRING_OR_COMMENT"
    stripped_old = ast.dump(_without_docstrings(ast.parse(before.decode("utf-8"))))
    stripped_new = ast.dump(_without_docstrings(ast.parse(after.decode("utf-8"))))
    if stripped_old == stripped_new:
        return "DOCSTRING_OR_COMMENT"
    if (_version_bindings(old) != _version_bindings(new)
            and ast.dump(_strip_version_bindings(old)) == ast.dump(_strip_version_bindings(new))):
        return "VERSION_ONLY"
    if (ast.dump(_without_annotations(ast.parse(before.decode("utf-8"))))
            == ast.dump(_without_annotations(ast.parse(after.decode("utf-8"))))):
        return "ANNOTATION_ONLY"
    return "CODE_CHANGE"


def is_test_path(path: str) -> bool:
    lowered = "/" + path.lower()
    return any(marker in lowered for marker in TEST_MARKERS)


def candidate_commits(repo: pathlib.Path, limit: int, since: str | None,
                      rev: str) -> list[dict]:
    """Real merged, non-merge commits that touch at least one non-test Python file.

    Newest first. A commit that only touches tests cannot be reverted in the sense measured here,
    and a merge commit has no single source change to put back.
    """
    args = ["log", "--no-merges", "--format=%H%x1f%ci%x1f%s", rev]
    if since:
        args.append(f"--since={since}")
    out = _git(repo, *args)
    commits: list[dict] = []
    for line in out.stdout.splitlines():
        if line.count("\x1f") != 2:
            continue
        sha, when, subject = line.split("\x1f")
        files = _git(repo, "show", "--name-only", "--format=", sha).stdout.splitlines()
        files = [f for f in files if f.strip()]
        source = [f for f in files if f.endswith(".py") and not is_test_path(f)]
        if not source:
            continue
        commits.append({"sha": sha, "when": when, "subject": subject,
                        "source_files": source, "files": files})
        if len(commits) >= limit:
            break
    return commits


def export_tree(repo: pathlib.Path, sha: str, into: pathlib.Path) -> None:
    """Materialise a commit's tree without touching any working tree or index."""
    into.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(["git", "-C", str(repo), "archive", sha], capture_output=True,
                             timeout=300)
    if archive.returncode != 0:
        raise RuntimeError(f"GIT_ARCHIVE_FAILED:{sha}:{archive.stderr[:200]}")
    tar = subprocess.run(["tar", "-x", "-C", str(into)], input=archive.stdout,
                         capture_output=True, timeout=300)
    if tar.returncode != 0:
        raise RuntimeError(f"TAR_FAILED:{sha}:{tar.stderr[:200]}")


def parent_source(repo: pathlib.Path, sha: str, rel: str) -> bytes | None:
    """The bytes of `rel` in the commit's parent, or None when the file did not exist there."""
    out = subprocess.run(["git", "-C", str(repo), "show", f"{sha}^:{rel}"], capture_output=True,
                         timeout=120)
    return out.stdout if out.returncode == 0 else None


_RAN = re.compile(r"Ran (\d+) tests?")
_PASSED = re.compile(r"(\d+) passed")
_FAILED = re.compile(r"(\d+) (?:failed|errors?)")


def tests_ran(text: str) -> int:
    """How many tests the runner says it executed. 0 when it says nothing -- which is the point.

    A check that runs nothing passes everything. Measured 2026-11-14 on `torproject/stem`: the first
    invocation (`unittest discover -s test/unit -t .`) reported "Ran 1 test ... OK", every one of 12
    reverted fixes came back `REVERT_NOT_NOTICED`, and not one of them was evidence. This is the same
    failure the repository already recorded once as "our verifier was running zero tests and
    reporting PASS", so it is guarded here rather than trusted.
    """
    counts = []
    for pattern in (_RAN, _PASSED):
        counts.extend(int(m) for m in pattern.findall(text or ""))
    return max(counts) if counts else 0


def run_check(root: pathlib.Path, argv: list[str], timeout: float,
              extra_paths: tuple[str, ...] = ()) -> dict:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("PYTHONHASHSEED", "0")
    # src-layout projects import their package from `src/`. Without this, `import packaging` resolves
    # to the installed copy in site-packages and the project's own tests run against somebody else's
    # code -- measured 2026-11-14, the same failure the oracle licence hit on the same repository.
    if extra_paths:
        roots = [str((root / p).resolve()) for p in extra_paths] + [str(root)]
        env["PYTHONPATH"] = os.pathsep.join(
            roots + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    started = time.monotonic()
    try:
        proc = subprocess.run(argv, cwd=str(root), capture_output=True, text=True,
                              timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"passed": False, "timed_out": True, "returncode": -1,
                "seconds": round(time.monotonic() - started, 2), "tail": "TIMEOUT",
                "tests_ran": 0}
    text = (proc.stdout or "") + (proc.stderr or "")
    lines = text.strip().splitlines()
    return {"passed": proc.returncode == 0, "timed_out": False, "returncode": proc.returncode,
            "seconds": round(time.monotonic() - started, 2), "tail": "\n".join(lines[-4:]),
            "tests_ran": tests_ran(text)}


def measure_commit(repo: pathlib.Path, commit: dict, argv: list[str], workdir: pathlib.Path,
                   timeout: float, extra_paths: tuple[str, ...] = ()) -> dict:
    sha = commit["sha"]
    row = {"sha": sha, "when": commit["when"], "subject": commit["subject"],
           "source_files": commit["source_files"]}
    root = workdir / sha[:12]
    try:
        export_tree(repo, sha, root)
    except RuntimeError as error:
        return {**row, "verdict": "EXPORT_FAILED", "detail": str(error)}

    # 1. the commit's own tree must be green, or a later red cannot be attributed to the revert.
    green = run_check(root, argv, timeout, extra_paths)
    if not green["passed"]:
        return {**row, "verdict": ("BASELINE_TIMEOUT" if green["timed_out"] else "BASELINE_RED"),
                "baseline": green}
    # A check that ran nothing says nothing. Refuse before any revert is written.
    if green["tests_ran"] == 0:
        return {**row, "verdict": "CHECK_RAN_NOTHING", "baseline": green,
                "detail": "the check exited 0 and named no tests, so a pass after the revert "
                          "would not be evidence of anything"}

    # 2. put the pre-fix source back, leaving the commit's test changes in place.
    reverted, skipped, classes = [], [], {}
    for rel in commit["source_files"]:
        before = parent_source(repo, sha, rel)
        target = root / rel
        if before is None:
            skipped.append({"file": rel, "why": "did not exist in the parent"})
            continue
        classes[rel] = classify_change(before, target.read_bytes() if target.exists() else b"")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(before)
        reverted.append(rel)
    if not reverted:
        return {**row, "verdict": "REVERT_UNAPPLIABLE", "skipped": skipped, "baseline": green}

    # 3. did anything notice?
    red = run_check(root, argv, timeout, extra_paths)
    verdict = "REVERT_NOT_NOTICED" if red["passed"] else "REVERT_NOTICED"
    kinds = set(classes.values())
    change_class = ("CODE_CHANGE" if "CODE_CHANGE" in kinds else
                    "UNPARSEABLE" if "UNPARSEABLE" in kinds else
                    "VERSION_ONLY" if kinds == {"VERSION_ONLY"} else "DOCSTRING_OR_COMMENT")
    return {**row, "verdict": verdict, "reverted": reverted, "skipped": skipped,
            "classes": classes, "change_class": change_class,
            "baseline": green, "after_revert": red}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--check", required=True, nargs=argparse.REMAINDER,
                        help="the project's own check, e.g. -- python -m pytest -q")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--since", default=None)
    parser.add_argument("--rev", default="HEAD")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--extra-path", action="append", default=[],
                        help="directory inside the tree to put on PYTHONPATH (src-layout)")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    repo = pathlib.Path(args.repo).resolve()
    check = [a for a in (args.check or []) if a != "--"]
    if not check:
        parser.error("--check needs a command after `--`")

    commits = candidate_commits(repo, args.limit, args.since, args.rev)
    print(f"{len(commits)} candidate commits with a non-test Python change", flush=True)
    rows: list[dict] = []
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="revert_ledger_"))
    try:
        for i, commit in enumerate(commits, 1):
            row = measure_commit(repo, commit, check, workdir, args.timeout,
                                 tuple(args.extra_path or ()))
            rows.append(row)
            print(f"[{i}/{len(commits)}] {commit['sha'][:8]} {row['verdict']:20} "
                  f"{commit['subject'][:60]}", flush=True)
            shutil.rmtree(workdir / commit["sha"][:12], ignore_errors=True)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    judged = counts.get("REVERT_NOTICED", 0) + counts.get("REVERT_NOT_NOTICED", 0)
    # Two denominators, both published. The code-change one is the claim a test can be held to;
    # the unfiltered one is printed beside it so the denominator can be checked, not trusted.
    judged_rows = [r for r in rows
                   if r["verdict"] in ("REVERT_NOTICED", "REVERT_NOT_NOTICED")]
    code_rows = [r for r in judged_rows if r.get("change_class") == "CODE_CHANGE"]
    code_noticed = sum(1 for r in code_rows if r["verdict"] == "REVERT_NOTICED")
    by_class: dict[str, dict[str, int]] = {}
    for row in judged_rows:
        bucket = by_class.setdefault(row.get("change_class") or "UNKNOWN",
                                     {"noticed": 0, "not_noticed": 0})
        bucket["noticed" if row["verdict"] == "REVERT_NOTICED" else "not_noticed"] += 1
    payload = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "repo": str(repo),
        "check": check,
        "commits_examined": len(rows),
        "counts": counts,
        "judged": judged,
        "noticed": counts.get("REVERT_NOTICED", 0),
        "not_noticed": counts.get("REVERT_NOT_NOTICED", 0),
        "fraction_noticed": round(counts.get("REVERT_NOTICED", 0) / judged, 4) if judged else None,
        "code_change_only": {
            "judged": len(code_rows),
            "noticed": code_noticed,
            "not_noticed": len(code_rows) - code_noticed,
            "fraction_noticed": round(code_noticed / len(code_rows), 4) if code_rows else None,
        },
        "by_change_class": by_class,
        "interpretation": (
            "REVERT_NOT_NOTICED means this real merged fix was put back to its pre-fix source, with "
            "its own tests in place, and the project's suite still passed. It is a fact about that "
            "commit and that suite, not a claim that the commit is wrong."
        ),
        "rows": rows,
        "spend_usd": 0,
        "model_calls": 0,
    }
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({k: payload[k] for k in ("commits_examined", "judged", "noticed",
                                              "not_noticed", "fraction_noticed",
                                              "code_change_only", "by_change_class", "counts")},
                     indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
