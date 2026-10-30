#!/usr/bin/env python3
"""Advanced-software-engineering request probes: what the machine actually does.

This is a MEASUREMENT, not a capability.  Authority: NONE.  Credit: 0.

Two suites, one instrument.  Every case is one ``live_brain_route_admission_v1.solve({...})``
call over a small but real tree -- nothing mocked, nothing stubbed -- and each case records the
four things that decide whether the machine is any good at hard software work:

    pass     did the machine certify the request?
    touched  did the file the sentence named actually change?  (md5, before/after)
    dirty    did a refusal leave edits behind?  (git status, per case)
    status   what did it say -- and was that sentence true?
    ms       how long a human waits

``--suite sentence`` (28 cases, one shared tree) asks whether ordinary advanced requests land.
``--suite hardcore`` (44 cases, a FRESH tree per case, so no case can be credited with another's
damage) asks the harder question: git, build, packaging, dependencies, debugging, refactoring
beyond rename, test authoring, review, performance and polyglot work.

A ``pass=True`` with ``touched=False`` is not automatically a false pass: "run the test suite"
and "find every caller" state effects that change no source.  It is the cases whose stated effect
is a SOURCE CHANGE (repair, refactor, feature) where ``touched=False`` must be read as a claim the
world does not support.

Usage::

    python3 execution_guard/swe_request_probe_v1.py                    # 28 sentences
    python3 execution_guard/swe_request_probe_v1.py --suite hardcore    # 44 hardcore requests
    python3 execution_guard/swe_request_probe_v1.py --suite hardcore --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TREE = "canonical/astra_runtime/tmp/swe_request_probe"
HARD_TREE = "canonical/astra_runtime/tmp/swe_hardcore_probe"

CALC = ("def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n\n\n"
        "def unused(x):\n    return x\n")
UTIL = "from calc import add\n\n\ndef total(xs):\n    return sum(add(x, 1) for x in xs)\n"
TEST_CALC = ("import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
             "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n\n"
             "    def test_mul(self):\n        self.assertEqual(calc.mul(2, 3), 6)\n")
APP_JS = "function add(a, b) {\n  return a + b;\n}\n\nmodule.exports = { add };\n"
PACKAGE_JSON = '{"name": "web", "version": "1.0.0", "scripts": {"test": "node --test"}}\n'
JS_TEST = ("const test = require('node:test');\nconst assert = require('node:assert');\n"
           "const { add } = require('./app.js');\n\n"
           "test('add', () => { assert.equal(add(2, 3), 5); });\n")
PYPROJECT = ('[build-system]\nrequires = ["setuptools>=61"]\nbuild-backend = "setuptools.build_meta"\n\n'
             '[project]\nname = "probepkg"\nversion = "0.1.0"\nrequires-python = ">=3.9"\n')
MAKEFILE = "test:\n\tpython3 -m pytest -q pkg\n\nbuild:\n\tpython3 -m compileall -q pkg\n"
README = "# probepkg\n\nAdds numbers.\n"


def build() -> str:
    base = ROOT / TREE
    shutil.rmtree(base, ignore_errors=True)
    (base / "pkg").mkdir(parents=True)
    (base / "web").mkdir()
    (base / "pkg" / "calc.py").write_text(CALC, encoding="utf-8")
    (base / "pkg" / "util.py").write_text(UTIL, encoding="utf-8")
    (base / "pkg" / "test_calc.py").write_text(TEST_CALC, encoding="utf-8")
    (base / "web" / "app.js").write_text(APP_JS, encoding="utf-8")
    (base / "web" / "package.json").write_text(PACKAGE_JSON, encoding="utf-8")
    return TREE


def _git(base: pathlib.Path, *args: str) -> None:
    env = dict(os.environ, GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="p@x",
               GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="p@x")
    subprocess.run(("git", "-C", str(base)) + args, check=False, capture_output=True,
                   env=env, text=True)


def build_hardcore() -> str:
    """A small repository a working engineer would recognise: a package, a red test, a build
    file, a README, a JavaScript package, no CI, and one commit of history."""
    base = ROOT / HARD_TREE
    shutil.rmtree(base, ignore_errors=True)
    (base / "pkg").mkdir(parents=True)
    (base / "web").mkdir()
    (base / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (base / "pkg" / "calc.py").write_text(CALC, encoding="utf-8")
    (base / "pkg" / "util.py").write_text(UTIL, encoding="utf-8")
    (base / "pkg" / "test_calc.py").write_text(TEST_CALC, encoding="utf-8")
    (base / "web" / "app.js").write_text(APP_JS, encoding="utf-8")
    (base / "web" / "app.test.js").write_text(JS_TEST, encoding="utf-8")
    (base / "web" / "package.json").write_text(PACKAGE_JSON, encoding="utf-8")
    (base / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (base / "Makefile").write_text(MAKEFILE, encoding="utf-8")
    (base / "README.md").write_text(README, encoding="utf-8")
    _git(base, "init", "-q", "-b", "main")
    _git(base, "add", "-A")
    _git(base, "commit", "-qm", "initial import")
    return HARD_TREE


def cases(base: str) -> list[tuple[str, str]]:
    c, t = base + "/pkg/calc.py", base + "/pkg/test_calc.py"
    js, util = base + "/web/app.js", base + "/pkg/util.py"
    return [
        # the change lane: repair and refactor
        ("repair/bug_report", "Bug: %s add() returns the wrong value. Failing test: %s." % (c, t)),
        ("repair/two_files", "Repair %s and %s so that the tests pass." % (c, util)),
        ("refactor/extract_fn", "Extract the function mul from %s into %s/pkg/mathops.py." % (c, base)),
        ("refactor/rename_sym", "Rename the symbol `mul` to `multiply` in %s." % c),
        ("refactor/split_fn", "Split the function add in %s into smaller functions." % c),
        ("refactor/dedupe", "Remove the duplicated logic between %s and %s." % (c, util)),
        ("refactor/type_hints", "Add type hints to every function in %s." % c),
        ("refactor/drop_dead", "Remove the dead code from %s." % c),
        # tests
        ("test/write_unit", "Write a unit test for the function mul in %s." % c),
        ("test/run_suite", "Run the test suite in %s/pkg." % base),
        ("test/which_tests", "Which tests do I need to run after changing %s?" % c),
        ("test/flaky", "Find the flaky test in %s." % t),
        # debugging
        ("debug/failing_test", "Why does %s fail?" % t),
        ("debug/debugger", "Attach a debugger to %s and show me the frame where it breaks." % t),
        # measurement
        ("measure/coverage", "Measure the test coverage of %s." % c),
        ("measure/mutation", "Measure the mutation score of %s." % c),
        ("measure/security", "Review %s for security issues." % c),
        # analysis
        ("analyze/explain", "Explain what %s does." % c),
        ("analyze/callers", "Find every caller of the function add in %s/pkg." % base),
        ("analyze/dead_code", "Find the dead code in %s." % c),
        # repository work
        ("git/commit", "Commit the changes to %s with a descriptive message." % c),
        ("git/branch", "Create the branch feature/x and switch to it."),
        ("git/bisect", "Find the commit that broke %s with git bisect." % c),
        # feature work
        ("feature/cli_flag", "Add a command-line flag --verbose to %s." % c),
        ("feature/logging", "Add logging to the function add in %s." % c),
        # polyglot
        ("js/lint", "Lint the javascript file %s." % js),
        ("js/test", "Run the javascript test suite in %s/web." % base),
        # a request that is not software engineering at all
        ("honesty/not_swe", "Calibrate the neutrino interferometer phase drift."),
    ]


def hardcore_cases(base: str) -> list[tuple[str, str]]:
    """44 requests an advanced engineer is asked for, in the order a week actually goes."""
    c = base + "/pkg/calc.py"
    u = base + "/pkg/util.py"
    t = base + "/pkg/test_calc.py"
    repo = base
    js = base + "/web/app.js"
    return [
        # --- understand before changing -------------------------------------------------
        ("understand/explain_module", "Explain what the module %s does and how it is used." % c),
        ("understand/trace_flow", "Trace how data flows from %s into %s." % (u, c)),
        ("understand/why_red", "The suite in %s is red. Find out why." % base),
        ("understand/root_cause", "Find the root cause of the failure in %s." % t),
        # --- repair ----------------------------------------------------------------------
        ("repair/from_issue", "Fix the bug: add(2, 3) returns -1 and the test expects 5. Code: %s" % c),
        ("repair/named_test", "Make the failing test in %s pass without changing the test." % t),
        ("repair/two_files", "Repair %s and %s so that the whole suite passes." % (c, u)),
        ("repair/regression", "The behaviour of mul() regressed; find and fix the cause in %s." % c),
        # --- refactor (beyond rename) ------------------------------------------------------
        ("refactor/inline", "Inline the function mul in %s into its only caller." % c),
        ("refactor/move", "Move the function mul from %s into %s/pkg/mathops.py." % (c, base)),
        ("refactor/extract_const", "Extract the magic numbers in %s into named constants." % c),
        ("refactor/dedupe", "Remove the duplicated logic between %s and %s." % (c, u)),
        ("refactor/drop_dead", "Remove the dead code from %s." % c),
        ("refactor/rename_repo", "Rename the symbol `mul` to `multiply` everywhere in %s." % repo),
        ("refactor/type_hints", "Add type hints to every function in %s and make mypy pass." % c),
        ("refactor/split_module", "Split %s into two modules without changing behaviour." % c),
        # --- tests ----------------------------------------------------------------------
        ("test/write_unit", "Write a unit test for the function mul in %s." % c),
        ("test/write_regression", "Write a regression test for the bug in %s." % c),
        ("test/raise_coverage", "Raise the test coverage of %s to at least 90%%." % c),
        ("test/affected_only", "Which tests do I need to run after changing %s?" % c),
        ("test/mutation_score", "Measure the mutation score of %s." % c),
        ("test/js_suite", "Run the javascript test suite in %s/web." % base),
        # --- quality gates the repo already has tools for ---------------------------------
        ("quality/lint", "Lint %s and fix what it reports." % c),
        ("quality/format", "Format %s with ruff format." % c),
        ("quality/typecheck", "Typecheck %s with mypy." % c),
        ("quality/security_fix", "Find and fix the security issues in %s." % c),
        ("quality/review_diff", "Review the diff of %s and tell me what is wrong with it." % c),
        # --- build, packaging, dependencies ----------------------------------------------
        ("build/build_package", "Build the package in %s into a wheel." % base),
        ("build/run_make", "Run `make test` in %s." % base),
        ("build/add_dep", "Add the dependency `requests` to %s/pyproject.toml." % base),
        ("build/upgrade_dep", "Upgrade the dependency setuptools in %s and fix what breaks." % base),
        ("build/setup_ci", "Set up CI for %s with GitHub Actions." % base),
        # --- git -------------------------------------------------------------------------
        ("git/commit", "Commit the changes in %s with a descriptive message." % base),
        ("git/branch", "Create the branch feature/x in %s and switch to it." % base),
        # The three questions the acceptance layer could always verify (`_READ_ONLY_SUBCOMMANDS`)
        # and no sentence could state until 2026-10-30.
        ("git/status", "What changed in %s since the last commit?" % base),
        ("git/log", "Show me the recent commits in %s." % base),
        ("git/diff", "What is the diff of the working tree in %s?" % base),
        ("git/bisect", "Find the commit that broke %s using git bisect." % base),
        ("git/revert", "Revert the last commit in %s." % base),
        ("git/changelog", "Write a changelog entry for the change in %s." % c),
        # --- feature work ------------------------------------------------------------------
        ("feature/cli_flag", "Add a command-line flag --verbose to %s." % c),
        ("feature/logging", "Add logging to the function add in %s." % c),
        ("feature/error_handling", "Add error handling to %s for bad input." % c),
        ("feature/issue_to_pr", "Implement this issue end to end in %s: add a subtract function with tests." % c),
        # --- performance ---------------------------------------------------------------------
        ("perf/profile", "Profile the function total in %s and tell me where the time goes." % u),
        ("perf/optimise", "Make the function total in %s faster without changing behaviour." % u),
        # --- polyglot ------------------------------------------------------------------------
        ("polyglot/js_lint", "Lint the javascript file %s." % js),
        ("polyglot/port", "Port the function add from %s to %s." % (c, js)),
    ]


def _md5(path: pathlib.Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()[:8]
    except OSError:
        return "GONE"


def _dirty(base: str) -> int:
    out = subprocess.run(("git", "-C", str(ROOT / base), "status", "--porcelain"),
                         capture_output=True, text=True).stdout
    return len([line for line in out.splitlines() if line.strip()])


def run(suite: str = "sentence", as_json: bool = False) -> int:
    from canonical.runtime import live_brain_route_admission_v1 as door

    rows = []
    if suite == "sentence":
        base = build()
        watched = ROOT / base / "pkg" / "calc.py"
        plan = [(name, goal, None) for name, goal in cases(base)]
    else:
        plan = [(name, goal, True) for name, goal in hardcore_cases(HARD_TREE)]
        base = None

    for name, goal, rebuild in plan:
        if rebuild:
            base = build_hardcore()
        watched = ROOT / base / "pkg" / "calc.py"
        before = _md5(watched)
        started = time.time()
        try:
            result = door.solve({"task_id": name.replace("/", "_"), "goal": goal})
            row = {"case": name, "pass": result.get("pass") is True,
                   "status": str(result.get("status") or ""),
                   "capability": str(result.get("compiled_capability_id") or "")}
        except BaseException as exc:  # noqa: BLE001 - a probe records every outcome
            row = {"case": name, "pass": False, "status": "RAISED:" + type(exc).__name__,
                   "capability": ""}
        row["ms"] = int((time.time() - started) * 1000)
        row["touched"] = _md5(watched) != before
        row["dirty"] = _dirty(base) if rebuild else 0
        rows.append(row)

    if as_json:
        print(json.dumps(rows, indent=1))
    else:
        for row in rows:
            print("%-26s %6dms pass=%-5s touched=%-5s dirty=%-2d %-44s %s"
                  % (row["case"], row["ms"], row["pass"], row["touched"], row["dirty"],
                     row["status"][:44], row["capability"]))

    answered = [r for r in rows if r["pass"]]
    changed = [r for r in rows if r["touched"]]
    dirtied = [r for r in rows if not r["pass"] and r["dirty"]]
    ms = sorted(r["ms"] for r in rows)
    print("\nANSWERED %d of %d (%.1f%%) · files changed %d · refused-but-tree-dirty %d"
          % (len(answered), len(rows), 100.0 * len(answered) / len(rows), len(changed), len(dirtied)))
    print("LATENCY p50 %d ms · p90 %d ms · max %d ms"
          % (ms[len(ms) // 2], ms[int(0.9 * (len(ms) - 1))], ms[-1]))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", choices=("sentence", "hardcore"), default="sentence")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    sys.exit(run(args.suite, args.json))
