#!/usr/bin/env python3
"""Census of ADVANCED software-engineering requests against the front door.

The 54-case capability matrix (``swe_capability_matrix_v1.py``) measures ordinary team
work: repair, rename, a few analyses. It says nothing about the work an advanced software
engineer is actually asked to do -- systems languages, build systems, CI, performance,
concurrency, test authoring, git surgery, design -- because a matrix only measures the
sentences somebody wrote cases for.

This instrument writes those sentences and records what happens.

* it prints the finding and exits 0 -- unless a floor was asked for and not met, because a
  census nothing can regress is a number nobody fixes (see ``--floor``);
* it has no per-request oracle, so ``SERVED`` means exactly "came back ``pass: true`` and
  edited nothing the sentence did not name". A wrong answer in the right shape is visible
  only in the ``selected`` column -- that is why the column is printed. The 2026-10-31
  census caught one: "Review <f> for API design problems" was answered by
  ``python.source.secret_scan.v1``;
* it builds its own scratch project, so it cannot damage the tree it runs in.

Usage::

    python3 execution_guard/swe_advanced_probe_v1.py            # the full census
    python3 execution_guard/swe_advanced_probe_v1.py --axis perf
    python3 execution_guard/swe_advanced_probe_v1.py --json /tmp/census.json
    python3 execution_guard/swe_advanced_probe_v1.py --floor 3 --summary "$GITHUB_STEP_SUMMARY"

Authority: NONE. This is a single-machine measurement of one tree at one commit.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import re
import shutil
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# The fixture's git tree has one owner (execution_guard/swe_git_fixture_v1.py) because the
# capability matrix already built it: a git question asked of a plain directory measures the
# absence of a repository, not the machine.
_HERE = str(pathlib.Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from swe_git_fixture_v1 import seed_repository  # noqa: E402

# A sentence that talks about history is asked of a tree that has some.  The predicate is about
# the sentence (HEAD~, commit, branch, bisect, git, changelog), never a curated case list, so a
# new history sentence is measured correctly the day it is written.

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/swe_advanced_probe"

FILES = {
    "pkg/calc.py": "def add(a, b):\n    total = a + b\n    return total\n\n\ndef mul(a, b):\n    return a * b\n",
    "pkg/util.py": "def total(xs):\n    out = 0\n    for x in xs:\n        out += x\n    return out\n",
    "pkg/service.py": "import calc\n\n\ndef area(w, h):\n    return calc.mul(w, h)\n",
    "pkg/mod.py": "def add(a, b):\n    return a + b\n\n\ndef twice(x):\n    return add(x, x)\n",
    "tests/test_calc.py": ("import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
                           "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n"),
    "pyproject.toml": "[project]\nname = \"probe\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11\"\n",
    "Makefile": "test:\n\tpython -m unittest discover -s tests\n",
    ".github/workflows/ci.yml": ("name: ci\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
                                 "    steps:\n      - uses: actions/checkout@v4\n"
                                 "      - run: python -m unittest discover -s tests\n"),
    "src/main.cpp": ("#include <vector>\n\nint sum(const std::vector<int>& xs) {\n  int t = 0;\n"
                     "  for (int x : xs) t += x;\n  return t;\n}\n"),
    "src/lib.rs": "pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n",
    "src/main.go": "package main\n\nfunc Add(a, b int) int {\n\treturn a + b\n}\n",
    "src/Main.java": "public class Main {\n    static int add(int a, int b) { return a + b; }\n}\n",
    "src/app.ts": "export function add(a: number, b: number): number {\n  return a + b;\n}\n",
    "src/schema.sql": "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL);\n",
}

# (axis, request template, files the request itself authorises to change)
PROBES: list[tuple[str, str, tuple[str, ...]]] = [
    ("polyglot", "Fix the off-by-one bug in {src}/main.cpp so that sum returns the right total.", ("src/main.cpp",)),
    ("polyglot", "Add a function sub to {src}/lib.rs that subtracts two integers.", ("src/lib.rs",)),
    ("polyglot", "Add a method Mul to {src}/main.go that multiplies two integers.", ("src/main.go",)),
    ("polyglot", "Add a second method to {src}/Main.java and make sure it compiles.", ("src/Main.java",)),
    ("polyglot", "Rename the exported function add to plus in {src}/app.ts and update its callers.", ("src/app.ts",)),
    ("polyglot", "Add a NOT NULL constraint on users.email in {src}/schema.sql.", ("src/schema.sql",)),
    ("polyglot", "Repair the C++ source file {src}/main.cpp so that it compiles cleanly.", ("src/main.cpp",)),
    ("build", "Add pytest as a development dependency in {root}/pyproject.toml.", ("pyproject.toml",)),
    ("build", "Create a pyproject.toml for the project in {pkg} with a console script entry point.", ("pyproject.toml",)),
    ("build", "Add a target `lint` to {root}/Makefile that runs ruff over the package.", ("Makefile",)),
    ("build", "Pin the dependency versions in {root}/pyproject.toml.", ("pyproject.toml",)),
    ("build", "Vendor the single dependency of the project in {pkg}.", ()),
    ("ci", "Fix the failing CI job in {root}/.github/workflows/ci.yml.", (".github/workflows/ci.yml",)),
    ("ci", "Make the CI workflow in {root}/.github/workflows/ci.yml run the tests on Python 3.11 and 3.12.",
     (".github/workflows/ci.yml",)),
    ("ci", "Add caching of pip downloads to {root}/.github/workflows/ci.yml.", (".github/workflows/ci.yml",)),
    ("ci", "Quarantine the flaky test in {tests}/test_calc.py so CI is green.", ("tests/test_calc.py",)),
    ("perf", "Profile {pkg}/util.py and tell me which function is the hot spot.", ()),
    ("perf", "Optimise the function total in {pkg}/util.py; it is too slow on large inputs.", ("pkg/util.py",)),
    ("perf", "Benchmark {pkg}/calc.py against the version in git HEAD~1.", ()),
    ("perf", "Add memoisation to the function twice in {pkg}/mod.py.", ("pkg/mod.py",)),
    ("systems", "Find the race condition in {pkg}/service.py.", ()),
    ("systems", "Add a thread pool to {pkg}/util.py that totals the list in parallel.", ("pkg/util.py",)),
    ("systems", "Make the function total in {pkg}/util.py release the GIL while summing.", ("pkg/util.py",)),
    ("tests", "Write a unit test for the function mul in {pkg}/calc.py.", ("tests/test_calc.py",)),
    ("tests", "Write a property-based test for the function add in {pkg}/calc.py.", ("tests/test_calc.py",)),
    ("tests", "Add a regression test that reproduces the bug in {pkg}/mod.py.", ("tests/test_calc.py",)),
    ("tests", "Increase the mutation score of {pkg}/calc.py above 0.8 by adding tests.", ("tests/test_calc.py",)),
    ("tests", "Fuzz the function add in {pkg}/calc.py for integer overflow.", ()),
    ("tests", "Run the test suite in {tests} and tell me which tests fail and why.", ()),
    ("debug", "The test in {tests}/test_calc.py fails; find the root cause.", ()),
    ("debug", "Explain why the function total in {pkg}/util.py returns None for empty input.", ()),
    ("debug", "Find the commit that broke the test in {tests}/test_calc.py.", ()),
    ("refactor", "Move the function add from {pkg}/mod.py into {pkg}/calc.py and update every caller.",
     ("pkg/mod.py", "pkg/calc.py")),
    ("refactor", "Split {pkg}/calc.py into one module per function.", ("pkg",)),
    ("refactor", "Rename the public function total in {pkg}/util.py to sum_all across the repository.", ("pkg",)),
    ("refactor", "Replace every use of the deprecated function mul in {pkg} with mul_v2.", ("pkg",)),
    ("refactor", "Add type hints to every function in {pkg}/calc.py.", ("pkg/calc.py",)),
    ("refactor", "Extract the loop in the function total in {pkg}/util.py into a helper.", ("pkg/util.py",)),
    ("review", "Review {pkg}/service.py for API design problems.", ()),
    ("review", "Review {pkg}/calc.py for security issues.", ()),
    ("review", "Audit the dependency list in {root}/pyproject.toml for known vulnerabilities.", ()),
    ("git", "Commit the changes in {pkg} with a clear message.", ()),
    ("git", "Create a branch named feature/x and commit {pkg}/calc.py there.", ()),
    ("git", "Show me the diff of {pkg}/calc.py against HEAD~1.", ()),
    ("git", "Cherry-pick the last commit onto a new branch.", ()),
    ("git", "Write the changelog entry for the last three commits.", ()),
    ("design", "Design the API for a rate limiter and write an ADR.", ()),
    ("design", "Plan the migration of the package in {pkg} from Python 3.9 to 3.12.", ()),
    ("design", "Write a design document for splitting {pkg} into two packages.", ()),
]


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    for rel, text in FILES.items():
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return base


def _asks_about_history(goal: str) -> bool:
    return bool(re.search(r"\bgit\b|HEAD[~^]|\bcommit(s|ted)?\b|\bbranch\b|\bbisect\b|\bchangelog\b",
                          str(goal or ""), re.I))


def _paths(base: pathlib.Path) -> dict[str, str]:
    out = {rel: base.joinpath(rel).relative_to(ROOT).as_posix() for rel in FILES}
    out["pkg"] = (base / "pkg").relative_to(ROOT).as_posix()
    out["tests"] = (base / "tests").relative_to(ROOT).as_posix()
    out["src"] = (base / "src").relative_to(ROOT).as_posix()
    out["root"] = base.relative_to(ROOT).as_posix()
    return out


def census(axis_filter: str | None = None) -> list[dict]:
    rows: list[dict] = []
    for i, (axis, template, allow) in enumerate(PROBES, 1):
        if axis_filter and axis != axis_filter:
            continue
        base = _build("%02d_%s" % (i, axis))
        goal = template.format(**_paths(base))
        if _asks_about_history(goal):
            seed_repository(base)
        before = {p.relative_to(ROOT).as_posix(): _digest(p) for p in base.rglob("*") if p.is_file()}
        started = time.perf_counter()
        try:
            result = door.solve({"task_id": "ADVANCED_PROBE_%02d" % i, "goal": goal}) or {}
            status, passed = str(result.get("status")), bool(result.get("pass"))
            selected = str(result.get("compiled_capability_id") or "")
            refusal = str(result.get("failure_class") or "")
            # THE DOOR ALREADY NAMES THE CAUSE.  Measured 2026-10-31: the controller returns
            # ``reason`` ("RuntimeError:HELPER_NAME_SURVIVED_IN:...", "BINDING_REFUSED:message:...")
            # and this census kept only the class, so ten different failures read as one string and
            # the inventory called them opaque.  They were not opaque; they were unread.
            reason = str(result.get("reason") or result.get("failure_reason") or "")
            if not reason:
                # A route admission refusal carries its rule, not a reason: R3_WEAK_EVIDENCE,
                # R11_STATED_PAYLOAD_SLOT_MISSING, INPUT_FORMAT_MISMATCH...  That rule IS the
                # cause, and it is the difference between "the sentence is thin evidence" and
                # "there is no slot for what you asked to be produced".
                admission = result.get("route_admission") or {}
                reason = str(admission.get("rule") or admission.get("typed_binding_reason") or "")
        except BaseException as exc:  # noqa: BLE001 - a census must never stop itself
            status, passed, selected, refusal = "RAISED:" + type(exc).__name__, False, "", str(exc)[:120]
            reason = "RAISED:" + type(exc).__name__
        elapsed = round((time.perf_counter() - started) * 1000)
        after = {p.relative_to(ROOT).as_posix(): _digest(p) for p in base.rglob("*") if p.is_file()}
        changed = sorted(p for p, d in before.items() if p in after and after[p] != d)
        allowed = tuple("/" + a for a in allow)
        # A git operation writes its own metadata by definition; .git/ is the tree the sentence
        # asked for, not a source edit the sentence did not name.
        unauthorised = [p for p in changed
                        if "/.git/" not in p and not any(p.endswith(a) for a in allowed)]
        rows.append(dict(n=i, axis=axis, goal=goal, status=status, served=passed,
                         selected=selected, ms=elapsed, changed=changed,
                         unauthorised=unauthorised, refusal=refusal, reason=reason))
    return rows


def _cause(row: dict) -> str:
    """The named cause of a refusal, from the field the door already fills.

    ``failure_class`` is the family ("LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE"); the
    cause is in ``reason`` ("RuntimeError:INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS",
    "BINDING_REFUSED:message:value_not_parseable").  A census that keeps only the family cannot
    be acted on, and a harness that cannot separate causes certifies nothing.
    """
    reason = str(row.get("reason") or "").strip()
    if reason:
        reason = reason.splitlines()[0].strip()
        parts = reason.split(":")
        if parts[0] in ("RuntimeError", "ValueError", "KeyError", "TypeError", "OSError",
                        "FileNotFoundError", "SyntaxError", "Exception"):
            reason = ":".join(parts[1:])
            parts = reason.split(":")
        if parts[0] in ("BINDING_REFUSED", "RAISED") and len(parts) > 1:
            # Keeps the slot: "BINDING_REFUSED:message" says which input the sentence did not
            # state, which is the whole actionable content of that refusal.
            return (parts[0] + ":" + parts[1]).strip()[:80]
        return reason.strip()[:80] or "-"
    return str(row.get("status") or "-")


def summary(path: str, rows: list[dict], served: int, floor: int | None,
            floor_met: bool) -> None:
    """Append the census to a markdown file (``$GITHUB_STEP_SUMMARY`` takes this as-is)."""
    out: list[str] = []
    out.append("### Advanced SWE census")
    out.append("")
    total = len(rows)
    head = "**SERVED %d / %d**" % (served, total)
    if floor is not None:
        head += " -- floor %d %s" % (floor, "met" if floor_met else "**NOT MET**")
    out.append(head)
    out.append("")
    out.append("| axis | served | total |")
    out.append("| --- | ---: | ---: |")
    by_axis: dict[str, list[int]] = collections.OrderedDict()
    for row in rows:
        by_axis.setdefault(row["axis"], [0, 0])
        by_axis[row["axis"]][1] += 1
        by_axis[row["axis"]][0] += 1 if row["served"] else 0
    for axis, (ok, n) in by_axis.items():
        out.append("| %s | %d | %d |" % (axis, ok, n))
    out.append("")
    refused = [r for r in rows if not r["served"]]
    counts = collections.Counter(_cause(r) for r in refused)
    out.append("Refused, by cause (%d):" % len(refused))
    out.append("")
    out.append("| count | cause |")
    out.append("| ---: | --- |")
    for cause, count in counts.most_common():
        out.append("| %d | `%s` |" % (count, cause.replace("|", "/")[:160]))
    out.append("")
    if refused:
        out.append("<details><summary>every refused sentence</summary>")
        out.append("")
        out.append("| # | axis | sentence | chosen row | status | cause |")
        out.append("| ---: | --- | --- | --- | --- | --- |")
        for r in refused:
            cell = r["goal"].replace("|", "/")
            out.append("| %d | %s | %s | `%s` | `%s` | `%s` |"
                       % (r["n"], r["axis"], cell[:150],
                          str(r.get("selected") or "-").replace("|", "/")[:60],
                          str(r.get("status") or "-").replace("|", "/")[:60],
                          _cause(r).replace("|", "/")[:90]))
        out.append("")
        out.append("</details>")
        out.append("")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(out) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--axis", default=None)
    ap.add_argument("--json", default=None)
    # A FLOOR, SO THE NUMBER CANNOT SILENTLY STAY WHERE IT IS.
    #
    # This instrument was written to always exit 0 and it does: it is a census, not a gate.
    # Measured 2026-10-31 on 34f867a: it reported SERVED 2 of 49 across three inventories
    # and two weeks while every check in the repository stayed green, because no workflow ran
    # it and nothing could fail.  The surface census next door already has this argument and
    # the difference is visible in its numbers (23 -> 25 -> 28 once it became a gate).
    # The floor is the count that exists today, not a target; when a change raises it, raise
    # the floor in the same pull request.
    ap.add_argument("--floor", type=int, default=None)
    # The census already knows the refusal taxonomy, so the histogram belongs here rather
    # than in a YAML heredoc that can only guess at the field names.
    ap.add_argument("--summary", default=None, help="append a markdown census to this file")
    ns = ap.parse_args(argv)

    rows = census(ns.axis)
    for row in rows:
        print("%2d %-9s %-8s %6dms %-44s %-44s %-40s %s"
              % (row["n"], row["axis"], "SERVED" if row["served"] else "refused", row["ms"],
                 (row["selected"] or "-")[:44], (row["status"] or "-")[:44],
                 _cause(row)[:40],
                 ",".join(p.split("/")[-1] for p in row["unauthorised"])[:30]))
    served = sum(1 for r in rows if r["served"])
    print("\nREQUESTS %d  SERVED %d  REFUSED %d" % (len(rows), served, len(rows) - served))
    by_axis: dict[str, list[int]] = collections.OrderedDict()
    for row in rows:
        by_axis.setdefault(row["axis"], [0, 0])
        by_axis[row["axis"]][1] += 1
        by_axis[row["axis"]][0] += 1 if row["served"] else 0
    for axis, (ok, total) in by_axis.items():
        print("  %-9s served %d/%d" % (axis, ok, total))
    if ns.json:
        pathlib.Path(ns.json).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
        print("WROTE", ns.json)
    floor_met = ns.floor is None or served >= ns.floor
    if ns.summary:
        summary(ns.summary, rows, served, ns.floor, floor_met)
        print("WROTE", ns.summary)
    print("AUTHORITY NONE -- single-machine census, not independent verification")
    if not floor_met:
        print("SERVED FLOOR NOT MET: %d < %d" % (served, ns.floor))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
