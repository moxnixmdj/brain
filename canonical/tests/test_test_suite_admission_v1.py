#!/usr/bin/env python3
"""The gate is judged by executed mutation outcomes, including the case where it must refuse.

Every count asserted here was produced by running this tree's own `python.tests.mutation_score.v1`
on the fixture in `test_suite_admission_v1`. Nothing is mocked, no file is fed from history, and
the two arms that matter are the ones where a passing suite must NOT be admitted.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.swe_kernel import test_suite_admission_v1 as admission
from canonical.tools import test_oracle_strength_measure_20261113_v1 as measure


class _Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="brain_suite_admission_test_")
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name)
        self.project = admission.build_fixture(self.root)

    def use_suite(self, text: str) -> None:
        for path in (self.project / "tests").glob("test_*.py"):
            path.unlink()
        (self.project / "tests" / "test_suite.py").write_text(text, encoding="utf-8")

    def score(self, name: str = "mutation", **kwargs) -> dict:
        return admission.evaluate(self.root, "proj/app", output_path=f"out/{name}.json", **kwargs)


class TestTheShippedGeneratorIsMeasuredNotTrusted(_Fixture):
    def test_the_generators_own_suite_passes_its_own_runner_and_kills_no_mutant(self) -> None:
        from canonical.runtime.bound_capabilities import python_tests_generate_scaffold as generator

        generated = generator.run({"source_root": "proj/app", "generated_tests_root": "gen/app",
                                   "output_path": "out/generated.json"}, self.root)
        self.assertEqual(generated["test_failed"], 0)
        self.assertGreater(generated["test_passed"], 0)
        detail = json.loads((self.root / generated["output_path"]).read_text(encoding="utf-8"))
        self.use_suite((self.root / detail["generated_test_file"]).read_text(encoding="utf-8"))
        report = self.score("scaffold")
        self.assertEqual(report["verdict"], admission.REJECT)
        self.assertEqual(report["reason"], "SUITE_PASSES_AND_DETECTS_NOTHING")
        self.assertEqual(report["counts"]["killed"], 0)
        self.assertEqual(report["counts"]["mutants"], 12)

    def test_the_only_oracle_the_generator_writes_is_an_exception_check(self) -> None:
        from canonical.runtime.bound_capabilities import python_tests_generate_scaffold as generator

        generated = generator.run({"source_root": "proj/app", "generated_tests_root": "gen/app",
                                   "output_path": "out/generated.json"}, self.root)
        detail = json.loads((self.root / generated["output_path"]).read_text(encoding="utf-8"))
        text = (self.root / detail["generated_test_file"]).read_text(encoding="utf-8")
        assertions = {line.strip() for line in text.splitlines() if line.strip().startswith("self.assert")}
        self.assertEqual(assertions, {"self.assertNotIsInstance(result, BaseException)"})


class TestTheFourVerdicts(_Fixture):
    def test_a_suite_that_asserts_nothing_is_rejected(self) -> None:
        self.use_suite(measure.NO_ASSERTIONS_SUITE)
        report = self.score("empty")
        self.assertEqual(report["verdict"], admission.REJECT)
        self.assertEqual(report["counts"]["killed"], 0)

    def test_a_partial_value_suite_is_refined_with_its_survivors_named(self) -> None:
        self.use_suite(measure.PARTIAL_SUITE)
        report = self.score("partial")
        self.assertEqual(report["verdict"], admission.REFINE)
        self.assertEqual(report["counts"]["killed"], 7)
        self.assertEqual(report["counts"]["survived"], 5)
        self.assertEqual(len(report["survivors"]), 5)
        self.assertTrue(all(s["status"] == "survived" for s in report["survivors"]))

    def test_a_value_asserting_suite_is_admitted_at_the_measured_score(self) -> None:
        self.use_suite(admission.VALUE_ASSERTING_SUITE)
        report = self.score("strong")
        self.assertEqual(report["verdict"], admission.ADMIT)
        self.assertEqual(report["counts"]["killed"], 10)
        self.assertEqual(report["counts"]["mutation_score"], 0.833333)
        self.assertFalse(report["adequacy_proved"])

    def test_the_bar_is_the_callers_policy_not_a_hidden_constant(self) -> None:
        self.use_suite(admission.VALUE_ASSERTING_SUITE)
        self.assertEqual(self.score("strict", min_score=0.99)["verdict"], admission.REFINE)
        self.assertEqual(self.score("lax", min_score=0.5)["verdict"], admission.ADMIT)

    def test_a_failing_baseline_is_refused_not_scored(self) -> None:
        self.use_suite("import unittest\nfrom app import calc\n\n"
                       "class T(unittest.TestCase):\n"
                       "    def test_wrong(self):\n"
                       "        self.assertEqual(calc.discount(200, 10), 999)\n")
        report = self.score("failing")
        self.assertEqual(report["verdict"], admission.REFUSED)
        self.assertIn("BASELINE_TEST_SUITE_FAILED_OR_EMPTY", report["reason"])
        self.assertNotIn("counts", report)

    def test_a_tree_with_no_mutable_code_is_refused(self) -> None:
        (self.project / "app" / "calc.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.use_suite("import unittest\n\nclass T(unittest.TestCase):\n"
                       "    def test_ok(self):\n        self.assertEqual(1, 1)\n")
        report = self.score("nocode")
        self.assertEqual(report["verdict"], admission.REFUSED)


class TestSurvivorsBecomeTheNextAssertion(_Fixture):
    def test_equivalent_boundary_mutants_are_reported_as_no_input_found_not_as_suite_failures(self) -> None:
        self.use_suite(admission.VALUE_ASSERTING_SUITE)
        report = self.score("strong")
        ledger = admission.next_assertions(self.root, "proj/app", report)
        self.assertEqual(len(ledger["ledger"]), 2)
        self.assertTrue(all(e["status"] == admission.NO_DISTINCTION for e in ledger["ledger"]))
        self.assertTrue(ledger["bounded_search_not_an_equivalence_proof"])

    def test_an_untested_branch_yields_a_concrete_call_and_the_value_to_assert(self) -> None:
        self.use_suite(measure.PARTIAL_SUITE)
        report = self.score("partial")
        ledger = admission.next_assertions(self.root, "proj/app", report)
        concrete = [e for e in ledger["ledger"] if e["status"] == admission.DISTINGUISHED]
        self.assertEqual(len(concrete), 3)
        calls = {e["call"] for e in concrete}
        self.assertIn("in_range(-1, -1, -1)", calls)
        for entry in concrete:
            self.assertEqual(entry["expected_value_source"], "current_implementation")
            self.assertTrue(entry["needs_spec_confirmation"])
            self.assertNotEqual(entry["current_result"], entry["mutant_result"])

    def test_a_narrower_grid_finds_fewer_distinctions_and_only_uses_its_own_values(self) -> None:
        self.use_suite(measure.PARTIAL_SUITE)
        report = self.score("partial")
        wide = admission.next_assertions(self.root, "proj/app", report)
        narrow = admission.next_assertions(self.root, "proj/app", report, grid=(5,))
        self.assertEqual(narrow["grid"], [5])
        wide_found = {e["mutant"] for e in wide["ledger"] if e["status"] == admission.DISTINGUISHED}
        narrow_found = {e["mutant"] for e in narrow["ledger"] if e["status"] == admission.DISTINGUISHED}
        self.assertLess(len(narrow_found), len(wide_found))
        self.assertTrue(narrow_found <= wide_found)
        for entry in narrow["ledger"]:
            if entry["status"] == admission.DISTINGUISHED:
                self.assertEqual(entry["call"], "in_range(5, 5, 5)")


class TestAmplificationNeedsAnIndependentOracle(_Fixture):
    def test_harvesting_from_a_defective_program_cements_the_defect(self) -> None:
        defective = admission.FIXTURE_MODULE.replace(
            "return low <= value and value <= high", measure.OFF_BY_ONE)
        (self.project / "app" / "calc.py").write_text(defective, encoding="utf-8")
        self.use_suite(measure.PARTIAL_SUITE)
        before = self.score("naive_before")
        ledger = admission.next_assertions(self.root, "proj/app", before)
        harvested = list(dict.fromkeys(
            f"        self.assertEqual(calc.{e['call']}, {e['assert_equals']})"
            for e in ledger["ledger"] if e.get("call") and e.get("assert_equals") is not None))
        suite = self.project / "tests" / "test_suite.py"
        suite.write_text(suite.read_text(encoding="utf-8") +
                         "\n    def test_harvested(self):\n" + "\n".join(harvested) + "\n",
                         encoding="utf-8")
        after = self.score("naive_after")
        self.assertEqual(before["counts"]["killed"], 7)
        self.assertEqual(after["counts"]["killed"], 10)
        self.assertEqual(after["verdict"], admission.ADMIT)
        # the admitted suite now defends the bug: the correct program cannot pass it
        (self.project / "app" / "calc.py").write_text(admission.FIXTURE_MODULE, encoding="utf-8")
        self.assertEqual(self.score("naive_fixed")["verdict"], admission.REFUSED)

    def test_the_gate_names_the_defect_instead_of_writing_an_assertion_for_it(self) -> None:
        defective = admission.FIXTURE_MODULE.replace(
            "return low <= value and value <= high", measure.OFF_BY_ONE)
        (self.project / "app" / "calc.py").write_text(defective, encoding="utf-8")
        self.use_suite(measure.PARTIAL_SUITE)
        result = admission.amplify(self.root, "proj/app", spec=measure.SPEC_TABLE,
                                   suite_relpath="proj/tests/test_suite.py")
        self.assertEqual(result["verdict"], "DEFECT_FOUND")
        self.assertEqual(result["written"], [])
        self.assertEqual({d["call"] for d in result["defects"]},
                         {"in_range(-1, -1, -1)", "in_range(-1, -1, 0)"})
        for defect in result["defects"]:
            self.assertNotEqual(defect["program_returns"], defect["spec_requires"])
        self.assertNotIn("TestSpecConfirmedSurvivors",
                         (self.project / "tests" / "test_suite.py").read_text(encoding="utf-8"))

    def test_the_same_gate_amplifies_a_correct_program_and_the_gain_is_executed(self) -> None:
        self.use_suite(measure.PARTIAL_SUITE)
        result = admission.amplify(self.root, "proj/app", spec=measure.SPEC_TABLE,
                                   suite_relpath="proj/tests/test_suite.py")
        self.assertEqual(result["verdict"], "AMPLIFIED")
        self.assertEqual(result["killed_gained"], 3)
        self.assertEqual(result["before"]["counts"]["killed"], 7)
        self.assertEqual(result["after"]["counts"]["killed"], 10)
        self.assertEqual(len(result["written"]), 2)
        self.assertEqual(result["defects"], [])
        self.assertTrue(all(c["expected_value_source"] == "independent_spec_table"
                            for c in result["candidates"] if c.get("writeable")))

    def test_a_silent_spec_writes_nothing(self) -> None:
        self.use_suite(measure.PARTIAL_SUITE)
        result = admission.amplify(self.root, "proj/app", spec={},
                                   suite_relpath="proj/tests/test_suite.py")
        self.assertEqual(result["verdict"], admission.REFUSED)
        self.assertEqual(result["reason"], "NO_CANDIDATE_CONFIRMED_BY_AN_INDEPENDENT_SPEC")
        self.assertEqual(result["written"], [])
        self.assertGreater(len(result["withheld"]), 0)

    def test_a_rejected_suite_is_not_amplified_at_all(self) -> None:
        self.use_suite(measure.NO_ASSERTIONS_SUITE)
        result = admission.amplify(self.root, "proj/app", spec=measure.SPEC_TABLE,
                                   suite_relpath="proj/tests/test_suite.py")
        self.assertEqual(result["verdict"], admission.REJECT)
        self.assertNotIn("after", result)
        self.assertEqual(result["written"], [])

    def test_the_gate_claims_no_authority(self) -> None:
        self.use_suite(admission.VALUE_ASSERTING_SUITE)
        self.assertEqual(self.score("authority")["authority"], "NONE")


class TestTheMeasurementReproduces(unittest.TestCase):
    def test_the_tool_reports_the_same_four_verdicts_and_the_defect(self) -> None:
        result = measure.measure()
        verdicts = {row["arm"]: row["verdict"] for row in result["arms"]}
        self.assertEqual(verdicts, {"scaffold_as_shipped": admission.REJECT,
                                    "no_assertions": admission.REJECT,
                                    "partial_value_assertions": admission.REFINE,
                                    "value_asserting": admission.ADMIT})
        self.assertEqual(result["model_calls"], 0)
        amp = result["amplification"]
        self.assertEqual(amp["harvest_from_current_program"]["verdict_after"], admission.ADMIT)
        self.assertEqual(amp["harvest_from_current_program"]["verdict_once_the_defect_is_fixed"],
                         admission.REFUSED)
        self.assertEqual(amp["spec_gated_on_defective_program"]["verdict"], "DEFECT_FOUND")
        self.assertEqual(amp["spec_gated_on_correct_program"]["verdict"], "AMPLIFIED")

    def test_the_shipped_amplifier_cannot_claim_amplification_without_generating_a_test(self) -> None:
        shipped = measure.measure()["shipped_amplifier"]
        self.assertEqual(shipped["capability"], "python.tests.advance.mutation_kill.v1")
        if shipped["outcome"] == "REFUSED":
            self.assertTrue(shipped["reason"])
            return
        if shipped["amplified"]:
            self.assertGreater(shipped["tests_generated"], 0)
            self.assertGreater(shipped["kill_after"], shipped["kill_before"])
        if not shipped["pynguin_importable"]:
            self.assertEqual(shipped["tests_generated"], 0)
            self.assertFalse(shipped["verified"])
            self.assertEqual(shipped["kill_after"], shipped["kill_before"])


if __name__ == "__main__":
    unittest.main()
