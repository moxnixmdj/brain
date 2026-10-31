"""A CERTIFICATE MAY ONLY CLAIM WORK THAT WAS DONE.

Every case here was measured on 2026-10-31 (report V4) as a `pass: true` over an artifact that
said, in its own bytes, that the work had not happened:

    "Run the tests in canonical/tests/test_swe_typed_plan_v1.py"
        -> python.repository.acceptance.measure.v1
        -> artifact: test_count 0, test_returncode 1, tests_pass false,
           terminal_authority false,
           hard_nonclaims[0] == "MEASUREMENT_SUCCESS_IS_NOT_TASK_ACCEPTANCE"
        -> door: PASS__...EXACT_SEMANTIC_ACCEPTANCE_VERIFIED

    "Find the fault in <f> that makes the test fail"
        -> code.impact.tree_sitter.testselect.v1 (a list of tests to run, nothing localized)
        -> PASS

    "Which tests does <f> break"
        -> delivered `records.0.tests` == 0, the test count of the FIRST record

    "Find every caller of build_plan in <f>"
        -> an index whose source_root was <f> itself: 1 of 7 call sites, "truncated": false

    "Check for security vulnerabilities in <f>"
        -> gate "PASS", complete true, from a substitute scanner (bandit absent)

The law is the same in all five: **what a row PRODUCES decides whether it may answer, and a
claim of completeness needs a scope that can contain the answer.** These tests pin the law at the
seam that admitted each one, so a future change cannot quietly restore the certificate.
"""
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime import answer_shape_v1 as shape  # noqa: E402

TYPED_FILE = "canonical/runtime/swe_typed_plan_v1.py"

# The registry row as it is declared today, copied from BOUND_CAPABILITY_REGISTRY_V1.json so the
# test states the same facts the door reads.
MEASUREMENT_ROW = {
    "capability_id": "python.repository.acceptance.measure.v1",
    "provides": ["python.repository.acceptance.measurement.content_addressed",
                 "python.test.measurement.objective"],
    "keywords": ["python", "repository", "measurement", "acceptance", "test",
                 "content-addressed", "run the tests", "run tests", "test suite"],
    "result_fields": ["status", "pass", "subject", "measurements", "test_evidence",
                      "python_parse_errors", "model_dependency_count", "output_verified"],
}

EXECUTION_ROW = {
    "capability_id": "python.tests.run.unittest.v1",
    "provides": ["python.tests.run", "python.tests.execution"],
    "keywords": ["run", "tests", "suite"],
    "result_fields": ["records", "exit_code", "tests", "passed", "failed"],
}


class MeasurementIsNotTheWork(unittest.TestCase):
    def test_a_measurement_row_cannot_answer_a_run(self):
        errors = door.stated_answer_errors(
            "Run the tests in canonical/tests/test_swe_typed_plan_v1.py",
            MEASUREMENT_ROW, MEASUREMENT_ROW["capability_id"])
        self.assertTrue(any(e.startswith("STATED_EXECUTION_ANSWERED_BY_A_MEASUREMENT")
                            for e in errors), errors)

    def test_a_run_row_still_answers_a_run(self):
        errors = door.stated_answer_errors(
            "Run the tests in canonical/tests/test_swe_typed_plan_v1.py",
            EXECUTION_ROW, EXECUTION_ROW["capability_id"])
        self.assertFalse(any(e.startswith("STATED_EXECUTION_ANSWERED_BY_A_MEASUREMENT")
                             for e in errors), errors)

    def test_keywords_and_an_id_never_excuse_a_measurement(self):
        """The defect was that a NAME satisfied the rule: the id says `acceptance`, the
        keywords say `run the tests`, and the row measures. Only the declaration counts."""
        loud = dict(MEASUREMENT_ROW,
                    capability_id="python.tests.execute.runner.v1",
                    keywords=["run", "execute", "records", "suite", "pytest", "exit code",
                              "run the tests"])
        errors = door.stated_answer_errors(
            "Run the script canonical/runtime/goal_compilation_benchmark_v1.py",
            loud, loud["capability_id"])
        self.assertTrue(any(e.startswith("STATED_EXECUTION_ANSWERED_BY_A_MEASUREMENT")
                            for e in errors), errors)


class DiagnosisIsNotATestSelection(unittest.TestCase):
    SELECTOR = {
        "capability_id": "code.impact.tree_sitter.testselect.v1",
        "provides": ["python.code.change_impact.test_selection"],
        "keywords": ["impact", "test", "selection", "callers"],
        "result_fields": ["selected_test_count", "candidate_test_count"],
    }

    def test_a_selector_cannot_answer_find_the_fault(self):
        errors = door.stated_answer_errors(
            "Find the fault in %s that makes the test fail" % TYPED_FILE,
            self.SELECTOR, self.SELECTOR["capability_id"])
        self.assertTrue(any(e.startswith("STATED_DIAGNOSIS_NOT_PROVIDED_BY_CAPABILITY")
                            for e in errors), errors)

    def test_a_localizer_still_answers_find_the_fault(self):
        localizer = dict(self.SELECTOR, capability_id="python.dynamic.fault_localizer.v1",
                         provides=["python.debug.fault_localization.ochiai"])
        errors = door.stated_answer_errors(
            "Find the fault in %s that makes the test fail" % TYPED_FILE,
            localizer, localizer["capability_id"])
        self.assertFalse(any(e.startswith("STATED_DIAGNOSIS_NOT_PROVIDED_BY_CAPABILITY")
                             for e in errors), errors)


class AnElementOfAListIsNotTheCollection(unittest.TestCase):
    def test_a_scalar_inside_a_list_item_is_never_the_enumeration(self):
        payload = {"records": [{"path": "a.py", "tests": 0}, {"path": "b.py", "tests": 5}]}
        asked = shape.asked("Which tests does %s break" % TYPED_FILE)
        self.assertIsNotNone(asked, "the sentence must classify as an enumeration")
        self.assertIsNone(shape._project(payload, asked),
                          "records.0.tests is one element, not the enumeration")

    def test_the_collection_itself_is_still_delivered(self):
        payload = {"tests": [{"path": "a.py", "tests": 0}, {"path": "b.py", "tests": 5}]}
        asked = shape.asked("Which tests does %s break" % TYPED_FILE)
        self.assertEqual(shape._project(payload, asked)[0], "tests")


class CompletenessNeedsScope(unittest.TestCase):
    def test_every_caller_from_inside_the_defining_file_is_refused(self):
        result = door.solve({"task_id": "law", "goal": (
            "Find every caller of build_plan in %s" % TYPED_FILE)})
        self.assertIs(result.get("pass"), False, result.get("status"))
        self.assertEqual(result.get("failure_class"), "ANSWER_SCOPE_UNPROVEN")
        self.assertTrue(any("SEARCH_SCOPE_IS_THE_STATED_FILE" in str(x)
                            for x in result.get("unproven_scope") or []))


class ASubstituteCheckerIsNotAGate(unittest.TestCase):
    def test_the_security_gate_does_not_certify_a_substitute(self):
        try:
            import bandit  # noqa: F401
            self.skipTest("bandit is installed: the gate ran its declared checker")
        except Exception:  # noqa: BLE001 - absence is the condition under test
            pass
        adapter = ROOT / "canonical/runtime/bound_capabilities/python_review_diff_security_gate.py"
        spec = __import__("importlib.util", fromlist=["spec"]).spec_from_file_location(
            "law_security_gate", adapter)
        module = __import__("importlib.util", fromlist=["module"]).module_from_spec(spec)
        spec.loader.exec_module(module)
        work = ROOT / "canonical/astra_runtime/tmp"
        work.mkdir(parents=True, exist_ok=True)
        diff = work / "law_certificate_diff.diff"
        out = work / "law_certificate_security.json"
        diff.write_text(
            "--- /dev/null\n+++ b/canonical/runtime/swe_typed_plan_v1.py\n"
            "@@ -0,0 +1,2 @@\n+def f(x):\n+    return x\n", encoding="utf-8")
        try:
            result = module.run({"diff_path": str(diff.relative_to(ROOT)),
                                 "worktree_path": ".",
                                 "output_path": str(out.relative_to(ROOT))}, ROOT)
        finally:
            for path in (diff, out):
                try:
                    path.unlink()
                except OSError:
                    pass
        # The substitute scanner's verdict stands -- it is a real check -- but the artifact
        # may not call itself complete, and it must name the checker that did not run.
        self.assertEqual(result.get("complete"), False, result)
        self.assertEqual(result.get("unavailable_checkers"), ["bandit"], result)
        if result.get("gate") == "PASS":
            self.assertFalse(str(result.get("bandit") or "").startswith("bandit"),
                             "a PASS is only a clean bill when the declared checker ran")


if __name__ == "__main__":
    unittest.main()
