"""The acceptance delimiter must remove routing prose, never user intent."""

from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import acceptance_clause_v1 as clause  # noqa: E402


GOAL = (
    "Write a measured acceptance repair report to "
    "canonical/astra_runtime/tmp/probe/report.json for the source root "
    "canonical/astra_runtime/tmp/probe using the test path "
    "canonical/astra_runtime/tmp/probe/test_all.py where "
    "`tests_pass` must be true and `python_parse_ok` must be true"
)
BINDINGS = {
    "source_root": "canonical/astra_runtime/tmp/probe",
    "test_paths": ["canonical/astra_runtime/tmp/probe/test_all.py"],
    "test_argv": [
        "/usr/bin/python3",
        "-c",
        "import pathlib,runpy,sys\nrunpy.run_path(sys.argv[1])\n",
        "canonical/astra_runtime/tmp/probe/test_all.py",
    ],
    "output_path": "canonical/astra_runtime/tmp/probe/report.json",
}


class TestAcceptanceClauseExtraction(unittest.TestCase):
    def test_a_pure_acceptance_spec_is_unchanged(self):
        pure = "tests_pass must be true.\npython_parse_ok must be true."
        out = clause.extract(pure, {})
        self.assertFalse(out["extracted"])
        self.assertEqual(out["acceptance_task_text"], pure)
        self.assertEqual(out["status"], "UNCHANGED__NO_EXPLICIT_ACCEPTANCE_CLAUSE")

    def test_the_declared_front_door_goal_extracts_both_objectives(self):
        out = clause.extract(GOAL, BINDINGS)
        self.assertTrue(out["extracted"], out)
        self.assertEqual(out["status"], "EXTRACTED__EXPLICIT_ACCEPTANCE_CLAUSE")
        self.assertEqual(
            out["acceptance_task_text"],
            "tests_pass must be true\npython_parse_ok must be true",
        )
        self.assertEqual(out["clause_count"], 2)
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertEqual(out["incremental_spend_usd"], 0)

    def test_a_hidden_requirement_before_the_delimiter_fails_closed(self):
        goal = GOAL.replace(
            "using the test path", "preserve every secret file using the test path"
        )
        out = clause.extract(goal, BINDINGS)
        self.assertFalse(out["extracted"])
        self.assertEqual(out["acceptance_task_text"], goal)
        self.assertEqual(
            out["status"], "FAIL_CLOSED__ROUTING_PREFIX_NOT_DECLARED_SYNTAX"
        )

    def test_an_unknown_path_not_present_in_the_bindings_fails_closed(self):
        goal = GOAL.replace(
            "canonical/astra_runtime/tmp/probe/test_all.py", "mystery/other_test.py"
        )
        out = clause.extract(goal, BINDINGS)
        self.assertFalse(out["extracted"])
        self.assertEqual(out["acceptance_task_text"], goal)

    def test_a_delimiter_without_an_objective_clause_fails_closed(self):
        goal = GOAL.replace(
            "where `tests_pass` must be true and `python_parse_ok` must be true",
            "where the answer looks good",
        )
        out = clause.extract(goal, BINDINGS)
        self.assertFalse(out["extracted"])
        self.assertEqual(out["acceptance_task_text"], goal)
        self.assertEqual(
            out["status"], "FAIL_CLOSED__ACCEPTANCE_CLAUSE_NOT_OBJECTIVE"
        )

    def test_a_quoted_enum_literal_is_preserved_and_field_quotes_are_removed(self):
        goal = (
            "Write a measured acceptance repair report to report.json for the "
            "source root . using the test path test_all.py where "
            "`status` must equal \"READY\""
        )
        bindings = {
            "source_root": ".",
            "test_paths": ["test_all.py"],
            "output_path": "report.json",
        }
        out = clause.extract(goal, bindings)
        self.assertTrue(out["extracted"], out)
        self.assertEqual(out["acceptance_task_text"], 'status must equal "READY"')

    def test_a_delimiter_inside_a_quoted_value_does_not_create_a_clause(self):
        goal = (
            "Write a measured acceptance repair report to report.json for the "
            "source root . using the test path test_all.py where "
            "'value where the answer lives' must be true"
        )
        bindings = {
            "source_root": ".",
            "test_paths": ["test_all.py"],
            "output_path": "report.json",
        }
        out = clause.extract(goal, bindings)
        self.assertFalse(out["extracted"])
        self.assertEqual(out["acceptance_task_text"], goal)


if __name__ == "__main__":
    unittest.main(verbosity=2)
