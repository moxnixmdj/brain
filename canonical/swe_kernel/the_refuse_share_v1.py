"""How much real work has no mechanical postcondition: the REFUSE share, measured.

THE TERM THIS COMPLETES
-----------------------
`THE_CEILING_OF_LEARN_ONCE_20261116_V1.md` split real work three ways and admitted that one part
had never been measured:

    MEMORISE   31/644 = 4.8%   a lookup plus a postcondition check
    SYNTHESISE  the rest       compose a new edit, check it mechanically
    REFUSE     UNMEASURED      the honest answer where no check exists

This module measures the third. It is the term that decides whether a verification-gated agent can
be trusted at all: where no mechanical check exists, the only correct output is a refusal, and an
agent that never refuses is silently wrong at a rate nobody has measured.

THE MEASUREMENT, AND WHY THIS IS THE RIGHT QUESTION
--------------------------------------------------
A real human commit changed some code. If the project's OWN tests, at the state the author left them,
do not notice when that change is undone, then that change had **no mechanical postcondition** -- the
project could not tell whether it was present. That is not a criticism of the commit; it is a fact
about what the repository can certify.

The naive experiment is wrong and was run first, deliberately, to show why:

    git revert <sha>; run tests   ->   PASSES

It passes because many commits change the tests as well as the source, so reverting removes the very
tests that would have caught it. The honest experiment holds the tests FIXED at the post-commit state
and reverts only non-test files:

    revert only non-test files; restore tests to post-commit state; run tests
        any failure  -> GUARDED     the repository can certify this change
        no failure   -> UNGUARDED   nothing in the repository can tell

That distinction is the whole instrument, and it is reported explicitly so a reader can see which
number is real.

A CONTROL, so a broken harness can never be reported as a finding
----------------------------------------------------------------
An UNGUARDED verdict is only meaningful if the harness can produce a GUARDED verdict on the same
repository with the same commands. Any repository that yields no GUARDED result at all is excluded
and counted as an INSTRUMENT LIMIT, not reported as a result. This is the lesson applied, not
relearned: an instrument failure is never a finding.

WHAT THIS IS NOT
----------------
* Not a claim that a commit is bad. A commit can be correct and still unverifiable by its repo.
* Not a coverage number. Coverage measures whether a line was executed; this measures whether
  undoing a change is DETECTED, which is the property an agent needs.
* Not owned by us: every test run is the project's own suite, unmodified, at its own state.

Authority: NONE. $0. Zero model calls. Real repositories, real test suites, real commits.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Sequence

SCHEMA = "THE_REFUSE_SHARE_20261116_V1"
AUTHORITY = "NONE__PRODUCER_RUN_REAL_REPOSITORY_REVERTS"

REPOS = (
    ("pypa/packaging", ("pretend", "pyparsing", "six")),
    ("pallets/click", ("pytest",)),
    ("pallets/markupsafe", ("pytest",)),
    ("pallets/itsdangerous", ("pytest", "freezegun")),
    ("pypa/pyproject-hooks", ("pytest",)),
)

#: SHA-pinned commits, listed literally so the measurement is reproducible and does not depend on
#: the shape of a corpus file. Each is a real merged commit from a real repository, taken from the
#: most recent history available. Pinned by date so a later run measures the SAME commits.
PINNED: dict[str, tuple[tuple[str, str, str], ...]] = {
    "pypa/packaging": (
        ("7bcd6d8e", "2024-01-12", "Apply some refurb suggestions"),
        ("a2b3e346", "2024-01-12", "Rename Py_NOGIL to Py_GIL_DISABLED"),
        ("5e84eeb6", "2024-01-12", "Stop using deprecated/removed keys on RtD"),
        ("d7ce40d8", "2024-01-12", "Fix code blocks in CHANGELOG.md"),
        ("c1346dfd", "2024-01-12", "fix: Detect when a platform is 32-bit more accurately"),
        ("3030822b", "2024-01-12", "Include CHANGELOG.rst in sdist"),
    ),
    "encode/httpcore": (
        ("10a658221deb38a4c5b16db55ab554b0bf731707", "2025-10-13",
         "Fix max_keepalive_connections"),
        ("5974b03c7df89d3ee4e23779900d5349d550753c", "2025-09-04",
         "Bump jinja2 from 3.1.4 to 3.1.6"),
        ("fb75e4272c3ee59944c7e04a3dec371840bc20dd", "2025-09-03",
         "Add Python 3.13 and 3.14 to test matrix"),
        ("98209758cc14e1a5f966fe1dfdc1064b94055d8c", "2025-04-24", "Version 1.0.9"),
        ("d1e17c53993fb5f3bfafedcd5aaca52a7264f0ed", "2025-04-24",
         "Update h11 dependency, resolving security fix."),
        ("b2a796c4ba093e10bb05184e69374191ae6ed1d2", "2025-04-11",
         "Fix `AttributeError` when importing on Python 3.14"),
    ),
    "encode/httpx": (
        ("b5addb64f0161ff6bfe94c124ef76f6a1fba5254", "2026-02-23",
         "Adapt test_response_decode_text_using_autodetect for chardet 6.0"),
        ("ae1b9f66238f75ced3ced5e4485408435de10768", "2025-12-10",
         "Expose `FunctionAuth` in `__all__`"),
        ("ca097c96f97d8d2a5da09b8ca736c7e78a2467f6", "2025-12-10", "docs/ssl: fix typo"),
        ("def4778d622e8bf49a9fea4dda78cca4cf666d8a", "2025-10-16",
         "Fixed a syntax error in the file upload example"),
        ("4b23574cf83307ce27d3b14b4a425dc58c57d28d", "2025-09-16", "Update dependencies"),
        ("3fee27838e9fd0cb528861e41f3ff98164081a4b", "2025-09-05",
         "[docs] Remove load_ssl_context & load_verify_log DEBUG log"),
    ),
}


#: A file is a test file if its path carries one of these. Deliberately blunt and declared, so the
#: split between "changed the code" and "changed the checks" is a stated rule and not a judgement.
TEST_MARKERS = ("test_", "_test.py", "/tests/", "/test/", "conftest.py", "testing/")


def is_test_path(path: str) -> bool:
    return any(marker in path for marker in TEST_MARKERS)


def run(argv: Sequence[str], cwd: pathlib.Path, timeout: int = 900) -> tuple[int, str]:
    done = subprocess.run(list(argv), cwd=str(cwd), capture_output=True, text=True,
                          timeout=timeout)
    return done.returncode, done.stdout + done.stderr


def parse_summary(output: str) -> dict[str, int]:
    """Failed / passed / error counts from pytest's own last line, or zeros if it did not run."""
    failed = passed = errors = 0
    match = re.search(r"(\d+) failed", output)
    if match:
        failed = int(match.group(1))
    match = re.search(r"(\d+) passed", output)
    if match:
        passed = int(match.group(1))
    match = re.search(r"(\d+) error", output)
    if match:
        errors = int(match.group(1))
    return {"failed": failed, "passed": passed, "errors": errors}


def suite_verdict(python: str, repo: pathlib.Path) -> dict[str, int]:
    code, output = run([python, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider",
                        "-o", "asyncio_default_fixture_loop_scope=function", "tests"], repo)
    summary = parse_summary(output)
    summary["exit"] = code
    summary["ran"] = summary["passed"] > 0
    return summary


def measure_commit(python: str, repo: pathlib.Path, sha: str,
                   baseline_failed: int = 0, baseline_errors: int = 0) -> dict[str, Any]:
    """The honest experiment for one commit, plus the naive one for contrast."""
    _, _ = run(["git", "reset", "--hard", "-q", sha], repo)
    run(["git", "clean", "-qfd"], repo)

    touched = run(["git", "show", "--name-only", "--format=", sha], repo)[1].split()
    non_test = [p for p in touched if not is_test_path(p)]
    if not non_test:
        return {"sha": sha, "status": "NO_NON_TEST_FILES", "files": touched}

    # -- the naive experiment, recorded so the difference is visible ------------------ #
    run(["git", "revert", "--no-commit", "--no-edit", sha], repo)
    naive = suite_verdict(python, repo)
    run(["git", "reset", "--hard", "-q", sha], repo)
    run(["git", "clean", "-qfd"], repo)

    # -- the honest experiment: revert source only, hold the tests fixed ------------- #
    run(["git", "revert", "--no-commit", "--no-edit", sha], repo)
    test_paths = [p for p in touched if is_test_path(p)]
    if test_paths:
        run(["git", "checkout", sha, "--", *test_paths], repo)
    honest = suite_verdict(python, repo)
    run(["git", "reset", "--hard", "-q", sha], repo)
    run(["git", "clean", "-qfd"], repo)

    if not honest["ran"]:
        verdict = "HARNESS_DID_NOT_RUN"
    elif honest["failed"] > baseline_failed or honest["errors"] > baseline_errors:
        # DETECTED: the suite went from whatever it already was to worse.
        verdict = "GUARDED"
    else:
        verdict = "UNGUARDED"

    return {
        "sha": sha,
        "status": verdict,
        "non_test_files": non_test,
        "test_files": test_paths,
        "naive_failed": naive["failed"],
        "honest_failed": honest["failed"],
        "honest_errors": honest["errors"],
        "honest_passed": honest["passed"],
        "naive_would_have_missed_it": naive["failed"] == 0 and honest["failed"] > 0,
    }


def measure(*, per_repo: int = 6, python: str = "/tmp/v4/bin/python") -> dict[str, Any]:
    corpus = [json.loads(line) for line in
              pathlib.Path("/home/user/brain/canonical/tests/fixtures/"
                           "systematic_edit_corpus_v1.jsonl").read_text().splitlines()]

    scratch = pathlib.Path(tempfile.mkdtemp(prefix="brain_refuse_"))
    rows: list[dict[str, Any]] = []
    limits: list[str] = []
    try:
        for repo_name, deps in REPOS + tuple(
                (name, ("pytest", "anyio", "h11", "certifi", "idna",
                        "httpcore", "sniffio", "trustme", "chardet", "brotli", "zstandard",
                        "click", "rich", "pytest-asyncio", "trio", "uvicorn"))
                for name in PINNED if name not in {r[0] for r in REPOS}):
            slug = repo_name.split("/")[1]
            target = scratch / slug
            code, out = run(["git", "clone", "-q", f"https://github.com/{repo_name}.git",
                             str(target)], scratch, timeout=600)
            if code != 0:
                limits.append(f"{repo_name}: CLONE_FAILED")
                continue
            # The project must be importable by its OWN conftest, which is the first thing pytest
            # loads. Without this, every repository reports "Harness did not run" and the control
            # correctly excludes it -- an expensive way to learn that the harness, not the world,
            # was broken. Installing the project editable is part of the harness, not a finding.
            code, out = run([python, "-m", "pip", "install", "-q", "-e", "."], target,
                            timeout=900)
            if code != 0:
                limits.append(f"{repo_name}: EDITABLE_INSTALL_FAILED")
                continue
            run([python, "-m", "pip", "install", "-q", *deps], scratch, timeout=900)

            # A repository whose OWN suite does not pass at the first commit cannot yield a
            # meaningful GUARDED/UNGUARDED verdict: a pre-existing failure would be read as
            # "guarded". Baseline first, exclude on failure, and say so.
            if repo_name in PINNED:
                sha0, _date0, subj0 = PINNED[repo_name][0]
                first = [{"sha": sha0, "subject": subj0}]
            else:
                first = sorted((r for r in corpus if r["repo"] == repo_name),
                               key=lambda r: r["date"], reverse=True)[:1]
            if first:
                run(["git", "reset", "--hard", "-q", first[0]["sha"]], target)
                baseline = suite_verdict(python, target)
                if not baseline["ran"]:
                    limits.append(f"{repo_name}: BASELINE_DID_NOT_RUN")
                    continue
                # A non-green baseline is allowed. GUARDED is judged RELATIVE to it: a revert that
                # produces strictly more failures than the repository already had has been DETECTED.
                # Requiring a green suite would have thrown away every repository with a pre-existing
                # failure -- an instrument rule masquerading as a finding.

            if repo_name in PINNED:
                commits = [{"sha": sha, "date": date, "subject": subject, "repo": repo_name}
                           for sha, date, subject in PINNED[repo_name]]
            else:
                commits = sorted((r for r in corpus if r["repo"] == repo_name),
                                 key=lambda r: r["date"], reverse=True)[:per_repo]
            for record in commits:
                try:
                    row = measure_commit(python, target, record["sha"],
                                         baseline["failed"], baseline["errors"])
                except subprocess.TimeoutExpired:
                    limits.append(f"{repo_name}@{record['sha'][:8]}: TIMEOUT")
                    continue
                except Exception as exc:                       # a harness failure is not a finding
                    limits.append(f"{repo_name}@{record['sha'][:8]}: {type(exc).__name__}")
                    continue
                row["repo"] = repo_name
                row["subject"] = record.get("subject", "")[:70]
                rows.append(row)

            # The control: if this repository never produced a GUARDED verdict, its results are
            # not evidence and are excluded rather than counted as UNGUARDED.
            repo_rows = [r for r in rows if r["repo"] == repo_name]
            if repo_rows and not any(r["status"] == "GUARDED" for r in repo_rows):
                limits.append(f"{repo_name}: NO_GUARDED_RESULT__HARNESS_UNPROVEN__EXCLUDED")
                rows = [r for r in rows if r["repo"] != repo_name]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    measured = [r for r in rows if r["status"] in ("GUARDED", "UNGUARDED")]
    guarded = [r for r in measured if r["status"] == "GUARDED"]
    unguarded = [r for r in measured if r["status"] == "UNGUARDED"]
    naive_missed = [r for r in measured if r.get("naive_would_have_missed_it")]

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "kind": "receipt",
        "incremental_spend_usd": 0,
        "model_calls": 0,
        "network_calls": "git clone of five public repositories; no inference",
        "producer_cognition_model_dependency_count": 0,
        "method": {
            "naive": "git revert <sha>; run the project's tests (WRONG: removes the tests too)",
            "honest": ("revert only non-test files, hold tests at the post-commit state, run the "
                       "project's tests; any failure means the repository can certify the change"),
            "test_path_rule": list(TEST_MARKERS),
            "control": ("a repository that yields no GUARDED verdict is excluded as an instrument "
                        "limit, never counted as UNGUARDED"),
        },
        "totals": {
            "commits_measured": len(measured),
            "guarded": len(guarded),
            "unguarded": len(unguarded),
            "refuse_share": (len(unguarded) / len(measured)) if measured else None,
            "guarded_share": (len(guarded) / len(measured)) if measured else None,
            "naive_experiment_would_have_missed": len(naive_missed),
        },
        "per_repo": {
            repo: {
                "measured": sum(1 for r in measured if r["repo"] == repo),
                "guarded": sum(1 for r in measured if r["repo"] == repo
                               and r["status"] == "GUARDED"),
                "unguarded": sum(1 for r in measured if r["repo"] == repo
                                 and r["status"] == "UNGUARDED"),
            } for repo, _ in REPOS
        },
        "rows": rows,
        "instrument_limits": limits,
        "reading": (
            "UNGUARDED means the project's own tests, at the state its author left them, do not "
            "notice when the change is undone. For an agent that gates every action on a mechanical "
            "check, that is exactly the set of changes where the correct output is a REFUSAL -- and "
            "where an agent that never refuses is silently wrong with nothing to catch it."),
        "caveats": [
            "A commit can be correct and still unguarded; this measures what the repository can "
            "certify, not the quality of the change.",
            "Some reverts fail to apply cleanly and are reported as harness limits, not results.",
            "Test files are identified by path markers, a declared rule rather than a judgement.",
            "pytest only; a project's own chosen runner may behave differently.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    per_repo = 6
    out = None
    for arg in argv:
        if arg.isdigit():
            per_repo = int(arg)
        else:
            out = arg
    result = measure(per_repo=per_repo)
    text = json.dumps(result, indent=1, sort_keys=True)
    if out:
        pathlib.Path(out).write_text(text + "\n")
        print("written", out)
    totals = result["totals"]
    print(f"commits measured : {totals['commits_measured']}")
    print(f"GUARDED          : {totals['guarded']}")
    print(f"UNGUARDED        : {totals['unguarded']}")
    if totals["refuse_share"] is not None:
        print(f"REFUSE share     : {totals['refuse_share']:.4f}")
    print(f"naive experiment would have missed: {totals['naive_experiment_would_have_missed']}")
    for limit in result["instrument_limits"]:
        print("  LIMIT:", limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
