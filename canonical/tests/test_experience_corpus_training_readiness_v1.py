"""The training-readiness screen must be able to fail, and able to pass.

A census that rejects everything passes every "does it catch bad rows" test while measuring
nothing. So the screen ships a positive control that satisfies all five requirements and five
ablations that each break exactly one. These tests pin both directions, and pin the finding
about the live stores without depending on their exact row counts.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import experience_corpus_training_readiness_v1 as E


class FailurePowerTests(unittest.TestCase):
    def test_the_positive_control_satisfies_every_requirement(self):
        report = E.audit_rows("control", [E.admissible_reference_row()])
        self.assertEqual(report["fully_ready_rows"], 1)
        for name in E.REQUIREMENTS:
            self.assertEqual(report["rows_meeting_each_requirement"][name], 1, name)

    def test_each_ablation_fails_exactly_its_own_requirement(self):
        controls = E.control_report()
        self.assertTrue(controls["valid"], controls)
        for name, row in controls["ablations"].items():
            self.assertTrue(row["failed_exactly_own_requirement"], (name, row))
            self.assertEqual(row["missing"], [name])

    def test_prose_is_not_an_executed_action(self):
        self.assertFalse(E._is_executable_action("parse file with ast.parse()"))
        self.assertFalse(E._is_executable_action("read file canonical/runtime/solve_v1.py"))
        self.assertTrue(E._is_executable_action("run_gzip"))
        self.assertTrue(E._is_executable_action({"type": "click", "index": 4}))

    def test_a_step_without_an_observation_is_not_a_recorded_prefix(self):
        self.assertFalse(E._trajectory_is_executed([{"action": "inc"}]))
        self.assertTrue(E._trajectory_is_executed([{"action": "inc", "observation": 0}]))

    def test_a_carried_model_without_its_schema_has_no_comparable_world(self):
        row = E.admissible_reference_row()
        row["model"] = {"0": {"inc": 1}}
        row.pop("model_schema")
        self.assertFalse(E._has_world_identity(row))

    def test_duplicates_are_a_store_property_not_a_row_property(self):
        row = E.admissible_reference_row()
        self.assertEqual(E.audit_rows("s", [row])["duplicate_payload_rows"], 0)
        report = E.audit_rows("s", [row, dict(row), dict(row)])
        self.assertEqual(report["duplicate_payload_rows"], 2)
        self.assertEqual(report["fully_ready_rows"], 0)

    def test_a_store_of_only_successes_cannot_teach_a_boundary(self):
        report = E.audit_rows("s", [E.admissible_reference_row()])
        self.assertEqual(report["outcome_classes_present"], [True])
        self.assertFalse(report["records_both_success_and_failure"])
        failed = E.admissible_reference_row()
        failed["outcome"] = "failure"
        failed["trajectory"] = [{"action": "dec", "observation": -1}]
        report = E.audit_rows("s", [E.admissible_reference_row(), failed])
        self.assertTrue(report["records_both_success_and_failure"])

    def test_an_unrecognised_outcome_word_is_not_a_verification_bit(self):
        row = E.admissible_reference_row()
        row["outcome"] = "probably_fine"
        self.assertEqual(E.audit_rows("s", [row])["rows_meeting_each_requirement"]["verified_outcome"], 0)


class LiveCorpusTests(unittest.TestCase):
    def test_the_census_is_valid_before_its_findings_are_read(self):
        report = E.measure()
        self.assertTrue(report["census_valid"], report["controls"])
        self.assertEqual(report["authority"], E.AUTHORITY)
        self.assertEqual(report["producer_cognition_model_dependency_count"], 0)

    def test_the_frozen_expectations_match_what_was_measured(self):
        report = E.measure()
        self.assertEqual(report["observed"], report["expected"], report["observed"])
        self.assertTrue(report["expectations_met"])

    def test_no_live_store_is_ready_to_be_a_training_set(self):
        report = E.measure()
        self.assertGreater(report["totals"]["rows"], 0)
        self.assertEqual(report["totals"]["fully_ready_rows"], 0)
        self.assertEqual(report["totals"]["stores_recording_both_outcome_classes"], 0)

    def test_the_generalization_store_records_no_failures(self):
        report = E.measure()
        store = next(s for s in report["stores"] if "GENERALIZATION_EXPERIENCES" in s["store"])
        self.assertGreater(store["rows"], 0)
        self.assertEqual(store["outcome_classes_present"], [True])
        self.assertFalse(store["records_both_success_and_failure"])


if __name__ == "__main__":
    unittest.main()
