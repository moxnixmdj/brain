# PROJECT_BRAIN
"""Pins for python.dynamic.fuzz.v1.

What is pinned is not "it found a bug" — it is the four things that make a fuzz finding worth
anything:

* every case runs in its OWN interpreter, so a hang or a hard crash is an outcome and not a lost
  run (a fuzzer that dies with its target measured nothing);
* generation is deterministic: the same seed produces the same cases, twice;
* a failure is shrunk to a minimal case, and the shrink may not change the failure mode — the
  greedy reduction accepted the case it started from and looped forever until `== 0` was removed
  from the candidate filter;
* an exception the contract declares expected is not a finding, and a clean function reports
  zero findings with `cases_run > 0`, so "nothing found" can never be confused with "nothing ran".

Run: python -m pytest canonical/tests/test_python_dynamic_fuzz_v1.py -q
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import dynamic_probe_v1 as D
from canonical.runtime.bound_capabilities.quality_v1 import verify_artifact

CALC = '''def safe_div(a: int, b: int) -> int:
    if b == 0:
        return 0
    return a // b


def buggy(a: int, b: int) -> int:
    return a // b


def strictly_positive(n: int) -> int:
    if n <= 0:
        raise ValueError("n must be positive")
    return n


def hangs(n: int) -> int:
    while n > 0:
        n = n + 1
    return n
'''


class _Project(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="fuzz_pin_"))
        (self.root / "pkg").mkdir(parents=True)
        (self.root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (self.root / "pkg" / "calc.py").write_text(CALC, encoding="utf-8")

    def fuzz(self, qualname: str = "buggy", **extra):
        args = {"source_root": str(self.root), "module": "pkg/calc.py", "qualname": qualname,
                "output_path": str(self.root / ".out" / (qualname + ".json")),
                "max_cases": 12, "case_timeout_s": 5}
        args.update(extra)
        return D.run(args, self.root)

    def refuse(self, **extra) -> str:
        with self.assertRaises(Exception) as ctx:
            self.fuzz(**extra)
        return str(ctx.exception)


class FuzzFindingTests(_Project):

    def test_a_crashing_input_is_found_and_shrunk_to_the_minimal_case(self):
        result = self.fuzz()
        self.assertEqual(result["gate"], "PASS")
        self.assertGreater(result["cases_that_failed"], 0)
        self.assertEqual(result["minimal_case"], [0, 0])
        self.assertEqual(result["failure_mode"], "raised")

    def test_the_finding_is_written_as_a_runnable_reproducer(self):
        result = self.fuzz()
        text = Path(result["reproducer_path"]).read_text(encoding="utf-8")
        self.assertIn("from pkg.calc import buggy", text)
        self.assertIn("CASE = [0, 0]", text)
        payload = json.loads((self.root / ".out" / "buggy.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["minimal_case"], [0, 0])
        self.assertTrue(verify_artifact(self.root / ".out" / "buggy.json"))

    def test_a_clean_function_reports_zero_findings_and_still_ran(self):
        result = self.fuzz("safe_div")
        self.assertEqual(result["cases_that_failed"], 0)
        self.assertIsNone(result["minimal_case"])
        self.assertGreater(result["cases_run"], 0)

    def test_a_declared_expected_exception_is_not_a_finding(self):
        blind = self.fuzz("strictly_positive")
        self.assertGreater(blind["cases_that_failed"], 0)
        declared = self.fuzz("strictly_positive", expected_exceptions=["ValueError"])
        self.assertEqual(declared["cases_that_failed"], 0)

    def test_a_hang_is_an_outcome_not_a_lost_run(self):
        result = self.fuzz("hangs", max_cases=3, case_timeout_s=1)
        self.assertEqual(result["failure_mode"], "timeout")
        self.assertEqual(result["minimal_case"], [1])


class FuzzDeterminismTests(_Project):

    def test_the_same_seed_produces_the_same_cases(self):
        first = self.fuzz(seed=7)
        second = self.fuzz(seed=7)
        self.assertEqual(first["cases_run"], second["cases_run"])
        self.assertEqual(first["cases_that_failed"], second["cases_that_failed"])
        self.assertEqual(first["minimal_case"], second["minimal_case"])

    def test_a_different_seed_is_a_different_draw(self):
        self.fuzz(seed=7)
        first = json.loads((self.root / ".out" / "buggy.json").read_text(encoding="utf-8"))
        self.fuzz(seed=99)
        second = json.loads((self.root / ".out" / "buggy.json").read_text(encoding="utf-8"))
        self.assertEqual(first["minimal_case"], second["minimal_case"])  # the bug is the bug
        self.assertNotEqual(first["artifact_sha256"], second["artifact_sha256"])


class FuzzRefusalTests(_Project):

    def test_an_unknown_function_is_named(self):
        self.assertIn("SYMBOL_NOT_FOUND:missing", self.refuse(qualname="missing"))

    def test_a_missing_module_is_named(self):
        self.assertIn("MODULE_NOT_FOUND:nothere.py",
                      self.refuse(module="nothere.py"))

    def test_a_missing_qualname_is_refused(self):
        self.assertIn("QUALNAME_NOT_STATED", self.refuse(qualname=""))

    def test_a_path_that_names_nothing_is_refused(self):
        self.assertIn("PATH_NOT_IN_THE_REPOSITORY", self.refuse(source_root="/not_a_project"))


if __name__ == "__main__":
    unittest.main()
