#!/usr/bin/env python3
"""An advanced-software-engineering request probe: 28 sentences, one ordinary tree.

This is a MEASUREMENT, not a capability.  Authority: NONE.  Credit: 0.

Every case is one ``live_brain_route_admission_v1.solve({...})`` call over a small tree
(a Python package with a RED suite, a dead function, a second module and a JavaScript
package).  Nothing is mocked, nothing is stubbed, and each case records the four things
that decide whether the machine is any good at hard software work:

    pass     did the machine certify the request?
    touched  did the file the sentence named actually change?  (md5, before/after)
    status   what did it say -- and was that sentence true?
    ms       how long a human waits

Usage::

    python3 execution_guard/swe_request_probe_v1.py            # table
    python3 execution_guard/swe_request_probe_v1.py --json      # machine readable

A ``pass=True`` with ``touched=False`` is not automatically a false pass: "run the test
suite" and "find every caller" state effects that change no source.  It is the cases
whose stated effect is a SOURCE CHANGE (repair, refactor, feature) where a ``touched``
of False must be read as a claim the world does not support.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TREE = "canonical/astra_runtime/tmp/swe_request_probe"

CALC = ("def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n\n\n"
        "def unused(x):\n    return x\n")
UTIL = "from calc import add\n\n\ndef total(xs):\n    return sum(add(x, 1) for x in xs)\n"
TEST_CALC = ("import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
             "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n\n"
             "    def test_mul(self)\n:\n        self.assertEqual(calc.mul(2, 3), 6)\n")
TEST_CALC = TEST_CALC.replace("def test_mul(self)\n:", "def test_mul(self):")
APP_JS = "function add(a, b) {\n  return a + b;\n}\n\nmodule.exports = { add };\n"
PACKAGE_JSON = '{"name": "web", "version": "1.0.0", "scripts": {"test": "node --test"}}\n'


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


def _md5(path: pathlib.Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()[:8]
    except OSError:
        return "GONE"


def run(as_json: bool = False) -> int:
    from canonical.runtime import live_brain_route_admission_v1 as door

    base = build()
    watched = ROOT / base / "pkg" / "calc.py"
    rows = []
    for name, goal in cases(base):
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
        rows.append(row)
    if as_json:
        print(json.dumps(rows, indent=1))
    else:
        for row in rows:
            print("%-22s %6dms pass=%-5s touched=%-5s %-46s %s"
                  % (row["case"], row["ms"], row["pass"], row["touched"],
                     row["status"][:46], row["capability"]))
    answered = sum(1 for row in rows if row["pass"])
    print("\nANSWERED %d of %d (%.1f%%)" % (answered, len(rows), 100.0 * answered / len(rows)))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    sys.exit(run(ap.parse_args().json))
