"""Four capabilities that work were unreachable, and a fifth lied when it was reached.

Measured 2026-10-29, one door call each on a fresh tree:

    "Measure the test coverage of <calc.py>."            FAIL__RAW_GOAL_COMPILATION_GAP
    "Review <calc.py> for security issues."              FAIL__RAW_GOAL_COMPILATION_GAP
    "Measure the mutation score of <calc.py>."           FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED
    "Run a performance review of <calc.py>."             FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
      ........... routed to software.review.gate.composer.v1, whose declared keywords include
      "coverage", "bandit" and "mutation" but whose contract cannot hold a review of one file.

Each of those four rows exists, binds, executes and reports a real verdict. Nothing about them was
missing; what was missing was the WIRE from the sentence to the row, and every gate below was
measured one layer at a time:

1. ``_STATED_EFFECTS`` (the answer gate's own table) knew a security review and a coverage
   measurement were STATED effects, but the routing door never asked it, so the shortlist was
   empty and the ranker was free to choose a document converter for a code review.
2. The composer declares ``bandit``/``coverage``/``mutation`` as KEYWORDS while the security gate
   declares ``python.review.diff_security_gate`` in ``provides``. Ranking tags above production
   made the row that mentions the tool outrank the row that produces the effect.
3. ``anchor_path`` (the review gates' name for the directory the tests run from) had no derivation
   row at all, and every gate thresholds its ratio with an absence-provided default the binder
   still demanded be spoken aloud.
4. The change set derived from a stated FILE was written as a NEW-file diff, which a gate that
   APPLIES it to a copy of the tree must refuse -- the file it claims to create is already there --
   and the coverage gate then reported ``gate: PASS`` with ``diff_executable_lines: 0`` and
   ``diff_covered_ratio: 1.0``: a passing measurement that measured nothing.
5. ``BOUND_PYPI_SOURCE_INCOMPLETE`` blocked a substrate that was importable
   (``coverage`` 7.17.0), and ``BOUND_PYTHON_STDLIB_MODULE_MISSING:stdlib`` blocked a declaration
   that named the standard library itself.

Nothing here widens what may run: every gate is still the pinned binder, the same execution path
and the same observation chain, and the security review on a file with a real finding still comes
back ``pass=False`` -- it now says a review ran and returned a verdict instead of claiming it could
not compile the request.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import astra_runtime  # noqa: E402
from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as brain  # noqa: E402
from canonical.runtime.bound_capabilities import (  # noqa: E402
    python_review_diff_coverage_gate as coverage_gate,
)

WORK = ROOT / "canonical/astra_runtime/tmp/test_review_ran"
REL = WORK.relative_to(ROOT).as_posix()

CLEAN = "def add(a, b):\n    total = a + b\n    return total\n\n\ndef mul(a, b):\n    return a * b\n"
VULN = ("import subprocess\n\n\ndef run(cmd):\n"
        "    return subprocess.run(cmd, shell=True, capture_output=True)\n")
SUITE = ("import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
         "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n\n"
         "    def test_mul(self):\n        self.assertEqual(calc.mul(2, 3), 6)\n")
BENCH = ("import calc\n\n\ndef bench():\n    total = 0\n"
         "    for i in range(500):\n        total += calc.add(i, 1)\n    return total\n")


def _fresh(source: str = CLEAN, tests: bool = True) -> pathlib.Path:
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "pkg").mkdir(parents=True)
    (WORK / "pkg/calc.py").write_text(source, encoding="utf-8")
    if tests:
        (WORK / "pkg/test_calc.py").write_text(SUITE, encoding="utf-8")
        (WORK / "pkg/bench_calc.py").write_text(BENCH, encoding="utf-8")
    return WORK


def _artifacts(result: dict) -> list[dict]:
    """The JSON artifacts the run says it wrote, parsed.  Never the report blob.

    The blob echoes the goal, so a substring oracle answers its own question: with the wiring
    reverted the sentence was still "real" because the sentence was in the result.
    """
    docs = []
    for row in (result.get("execution") or []):
        produced = str(((row or {}).get("result") or {}).get("output_path") or "")
        if produced and (ROOT / produced).is_file():
            try:
                import json
                docs.append(json.loads((ROOT / produced).read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
    return docs


class AReviewThatRanIsNotACompileGap(unittest.TestCase):
    def setUp(self):
        _fresh()

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    # ---- the four measurement lanes -------------------------------------------------------

    def test_a_security_review_of_a_clean_file_is_a_review(self) -> None:
        result = door.solve({"task_id": "SEC_REVIEW", "goal": "Review %s/pkg/calc.py for security issues." % REL})
        self.assertTrue(result.get("pass"), result.get("status"))
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.review.diff_security_gate.v1")
        schemas = {(doc.get("schema"), doc.get("gate")) for doc in _artifacts(result)}
        self.assertIn(("PROJECT_BRAIN_DIFF_SECURITY_GATE_V1", "PASS"), schemas)

    def test_a_security_review_with_a_finding_says_so_instead_of_blaming_the_compiler(self) -> None:
        _fresh(VULN)
        result = door.solve({"task_id": "SEC_FINDING", "goal": "Review %s/pkg/calc.py for security issues." % REL})
        self.assertFalse(result.get("pass"))
        self.assertEqual(result.get("status"),
                         "FAIL_CLOSED__REVIEW_RAN_AND_RETURNED_A_VERDICT", result.get("status"))
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.review.diff_security_gate.v1")
        self.assertIs(result.get("reviewed"), True)

    def test_a_coverage_request_measures_executable_changed_lines(self) -> None:
        result = door.solve({"task_id": "COV_MEASURE",
                             "goal": "Measure the test coverage of %s/pkg/calc.py." % REL})
        self.assertTrue(result.get("pass"), result.get("status"))
        measured = [doc for doc in _artifacts(result)
                    if doc.get("schema") == "PROJECT_BRAIN_DIFF_COVERAGE_GATE_V1"]
        self.assertTrue(measured, "no coverage artifact")
        self.assertEqual(measured[0].get("gate"), "PASS")
        self.assertGreater(measured[0].get("diff_executable_lines") or 0, 0,
                           "a PASS over zero measured lines is not a measurement")

    def test_a_coverage_request_on_a_tree_with_no_tests_refuses_and_names_why(self) -> None:
        _fresh(CLEAN, tests=False)
        result = door.solve({"task_id": "COV_NOTESTS",
                             "goal": "Measure the test coverage of %s/pkg/calc.py." % REL})
        self.assertFalse(result.get("pass"))
        self.assertIn("NO_TESTS_DISCOVERED", str(result.get("failure_class") or ""),
                      result.get("status"))

    def test_mutation_and_perf_are_measurements_too(self) -> None:
        mutation = door.solve({"task_id": "MUT", "goal": "Measure the mutation score of %s/pkg/calc.py." % REL})
        self.assertEqual(mutation.get("compiled_capability_id"), "python.review.diff_mutation_gate.v1",
                         mutation.get("status"))
        perf = door.solve({"task_id": "PERF", "goal": "Run a performance review of %s/pkg/calc.py." % REL})
        self.assertTrue(perf.get("pass"), perf.get("status"))
        perf_docs = [doc for doc in _artifacts(perf)
                     if doc.get("schema") == "PROJECT_BRAIN_DIFF_PERF_GATE_V1"]
        self.assertTrue(perf_docs, "no perf artifact")
        self.assertIsInstance(perf_docs[0].get("anchor_median_ns"), (int, float))
        self.assertIsInstance(perf_docs[0].get("patched_median_ns"), (int, float))

    # ---- the wiring itself, one gate at a time -------------------------------------------

    def test_the_declaration_table_shortlists_what_produces_the_effect(self) -> None:
        registry = brain.load_verified_registry(include_extended=True)
        from canonical.runtime import goal_compiler
        admissible = goal_compiler._platform_admissible_registry(
            {cid: entry for cid, entry in registry.items() if brain.is_verified_entry(entry)})
        for goal, expected in (
            ("Review %s/pkg/calc.py for security issues." % REL, "python.review.diff_security_gate.v1"),
            ("Measure the test coverage of %s/pkg/calc.py." % REL, "python.review.diff_coverage_gate.v1"),
        ):
            shortlist = door.declared_effect_ids(goal, admissible)
            self.assertIn(expected, shortlist, shortlist)
            # A row that merely TAGS the tool must not outrank the row that produces the effect.
            self.assertNotIn("software.review.gate.composer.v1", shortlist,
                             "keyword-only row won the shortlist: " + str(shortlist))

    def test_anchor_and_change_set_are_rooted_at_the_same_directory(self) -> None:
        registry = brain.load_verified_registry(include_extended=True)
        entry = registry["python.review.diff_coverage_gate.v1"]
        values = {key: row["value"] for key, row in
                  derivation.derive("Measure the test coverage of %s/pkg/calc.py." % REL, entry, ROOT).items()}
        self.assertEqual(values.get("anchor_path"), REL + "/pkg")
        body = (ROOT / values["diff_path"]).read_text(encoding="utf-8")
        # Anchor-relative, and a rewrite of the file that exists -- never a claim to create it.
        self.assertIn("+++ b/calc.py", body)
        self.assertNotIn("+++ b/%s" % REL, body)
        self.assertNotIn("--- /dev/null", body)

    def test_a_coverage_verdict_over_an_unmeasured_diff_is_a_refusal(self) -> None:
        """A gate that cannot find the changed file in the report has measured nothing.

        ``bench_calc.py`` is in the tree, the diff applies, and no test imports it, so the
        coverage report never mentions it.  That is exactly the shape that used to produce
        ``gate: PASS`` with ``diff_executable_lines: 0`` and ``diff_covered_ratio: 1.0``.
        """
        change = derivation._stated_change_set([REL + "/pkg/bench_calc.py"], ROOT, REL + "/pkg")
        self.assertIsNotNone(change)
        with self.assertRaises(SystemExit) as raised:
            coverage_gate.run({"anchor_path": REL + "/pkg", "diff_path": change["value"],
                               "output_path": REL + "/spool_cov.json"}, ROOT)
        self.assertIn("DIFF_FILES_NOT_IN_COVERAGE_REPORT", str(raised.exception))

    # ---- acquisition: a fact about the machine, not a record to demand -------------------

    def test_an_importable_pypi_substrate_needs_no_acquisition_record(self) -> None:
        present = astra_runtime._pypi_module_already_present(
            {"module": "json", "type": "pypi", "version_family": ">=1.0"})
        self.assertEqual((present or {}).get("status"), "ALREADY_PRESENT_FEATURE_PROBED")
        absent = astra_runtime._pypi_module_already_present(
            {"module": "no_such_module_brain_test", "type": "pypi"})
        self.assertIsNone(absent)
        # A declared family that IS comparable and is unsatisfied is a refusal, never a pass.
        self.assertIs(astra_runtime._version_family_satisfied("1.2.3", ">=99.0"), False)
        self.assertIs(astra_runtime._version_family_satisfied("7.17.0", ">=7.0"), True)
        self.assertIsNone(astra_runtime._version_family_satisfied("", ">=7.0"))
        from unittest import mock
        with mock.patch("importlib.metadata.version", return_value="1.0"):
            with self.assertRaises(astra_runtime.Blocker) as raised:
                astra_runtime._pypi_module_already_present(
                    {"module": "json", "type": "pypi", "version_family": ">=99.0"})
        self.assertIn("VERSION_FAMILY_UNSATISFIED", str(raised.exception))

    def test_the_stdlib_declaration_is_the_interpreter(self) -> None:
        resolved = astra_runtime._ensure_local_dependency(
            {"type": "python_stdlib", "module": "stdlib"})
        self.assertEqual(resolved.get("status"), "LOCAL_VERIFIED")
        self.assertEqual(resolved.get("resolution"), "THE_INTERPRETER_ITSELF")
        with self.assertRaises(astra_runtime.Blocker):
            astra_runtime._ensure_local_dependency(
                {"type": "python_stdlib", "module": "no_such_stdlib_module"})


if __name__ == "__main__":
    unittest.main()
