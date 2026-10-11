from __future__ import annotations

import unittest

from canonical.runtime import python_software_request_acceptance_cells_v1 as cells
from canonical.runtime.bound_capabilities.python_repository_acceptance_measurement_v1 import (
    MEASUREMENT_SCHEMA,
)


def fields(**overrides):
    out = {
        "tests_pass": True,
        "test_returncode": 0,
        "test_count": 4,
        "python_parse_ok": True,
        "python_file_count": 3,
        "repository_source_unchanged": True,
    }
    out.update(overrides)
    return out


class SoftwareRequestAcceptanceCellsV1Tests(unittest.TestCase):
    def test_make_all_tests_pass_compiles(self):
        out = cells.compile_cell("Make all tests pass.")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["field"], "tests_pass")

    def test_tests_must_pass_paraphrase_compiles(self):
        out = cells.compile_cell("The tests must pass!")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["cell_id"], "EXPLICIT_TESTS_PASS_TRUE")

    def test_python_parse_postcondition_compiles(self):
        out = cells.compile_cell("Ensure the Python code parses.")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["field"], "python_parse_ok")

    def test_source_unchanged_postcondition_compiles(self):
        out = cells.compile_cell("Keep the repository source unchanged during verification.")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["field"], "repository_source_unchanged")

    def test_vague_fix_request_remains_unresolved(self):
        out = cells.compile_cell("Fix the parser bug.")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "UNRESOLVED__NO_SOUND_SOFTWARE_ACCEPTANCE_CELL")

    def test_better_tests_request_remains_unresolved(self):
        out = cells.compile_cell("Make the tests better.")
        self.assertFalse(out["pass"])

    def test_multisegment_supported_task_is_accounted_and_passes(self):
        out = cells.evaluate_task(
            "Make all tests pass. Ensure the Python code parses.",
            fields(),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["required_obligation_count"], 2)
        self.assertEqual(out["evaluated_obligation_count"], 2)
        self.assertTrue(out["all_raw_obligations_accounted_for"])
        self.assertFalse(out["acceptance_stop_authorized"])

    def test_false_measured_postcondition_falsifies(self):
        out = cells.evaluate_task("Make all tests pass.", fields(tests_pass=False))
        self.assertFalse(out["pass"], out)
        self.assertTrue(out["semantic_residual_obligation_ids"])

    def test_supported_plus_vague_segment_stays_open(self):
        out = cells.evaluate_task(
            "Make all tests pass. Fix the parser bug.",
            fields(),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(len(out["semantic_residual_obligation_ids"]), 1)

    def test_existing_controlled_field_grammar_still_works(self):
        out = cells.evaluate_task(
            "tests_pass must be true.",
            fields(),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["obligation_results"][0]["route"], "EXISTING_OBJECTIVE_ACCEPTANCE")

    def test_wrong_measurement_field_set_fails_closed(self):
        out = cells.evaluate_task("Make all tests pass.", {"tests_pass": True})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "MEASUREMENT_FIELD_SET_MISMATCH")

    def test_measurement_schema_stays_exact(self):
        self.assertEqual(
            set(MEASUREMENT_SCHEMA),
            {
                "tests_pass",
                "test_returncode",
                "test_count",
                "python_parse_ok",
                "python_file_count",
                "repository_source_unchanged",
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
