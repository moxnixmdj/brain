from __future__ import annotations

import copy
import unittest

from canonical.runtime.capability_execution_trace_capsule_v1 import (
    verify_and_compile,
)


def fixture():
    problem = {
        "initial_facts": ["seed.available"],
        "target_effects": ["report.verified"],
        "capabilities": [
            {
                "id": "produce",
                "requires": ["seed.available"],
                "provides": ["report.available"],
                "action": {
                    "type": "invoke_capability",
                    "args": {"capability_id": "produce"},
                    "expect": {
                        "field": "verified",
                        "type": "field_equals",
                        "value": True,
                    },
                },
                "result_fields": ["output_path"],
            },
            {
                "id": "verify",
                "requires": ["report.available"],
                "provides": ["report.verified"],
                "action": {
                    "type": "invoke_capability",
                    "args": {
                        "capability_id": "verify",
                        "path": {"$result": {"cycle": 0, "field": "output_path"}},
                    },
                    "expect": {
                        "field": "verified",
                        "type": "field_equals",
                        "value": True,
                    },
                },
                "result_fields": [],
            },
        ],
    }
    planned = {
        "planning": {
            "plan": ["produce", "verify"],
            "target_effects": ["report.verified"],
        },
        "actions": [
            {
                "type": "invoke_capability",
                "args": {"capability_id": "produce"},
                "expect": {
                    "field": "verified",
                    "type": "field_equals",
                    "value": True,
                },
                "capability_id": "produce",
            },
            {
                "type": "invoke_capability",
                "args": {
                    "capability_id": "verify",
                    "path": {"$result": {"cycle": 0, "field": "output_path"}},
                },
                "expect": {
                    "field": "verified",
                    "type": "field_equals",
                    "value": True,
                },
                "capability_id": "verify",
            },
            {
                "type": "finish",
                "args": {"summary": "done"},
                "why": "complete",
            },
        ],
    }
    execution = {
        "trace": [
            {
                "cycle": 0,
                "plan": copy.deepcopy(planned["actions"][0]),
                "result": {
                    "verified": True,
                    "output_path": "canonical/tmp/report.json",
                },
            },
            {
                "cycle": 1,
                "plan": {
                    "type": "invoke_capability",
                    "args": {
                        "capability_id": "verify",
                        "path": "canonical/tmp/report.json",
                    },
                    "expect": {
                        "field": "verified",
                        "type": "field_equals",
                        "value": True,
                    },
                    "capability_id": "verify",
                },
                "result": {"verified": True},
            },
            {
                "cycle": 2,
                "plan": copy.deepcopy(planned["actions"][2]),
                "result": {"type": "finish", "summary": "done"},
            },
        ]
    }
    return problem, planned, execution


class Tests(unittest.TestCase):
    def test_valid_trace_compiles_to_content_addressed_capsule(self):
        problem, planned, execution = fixture()
        verdict = verify_and_compile(problem, planned, execution)
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertEqual(verdict["capsule_record_count"], 2)
        self.assertEqual(verdict["explicit_result_edge_count"], 1)
        self.assertTrue(verdict["all_target_effects_have_witnesses"])

    def test_missing_runtime_expectation_fails_closed(self):
        problem, planned, execution = fixture()
        planned["actions"][1].pop("expect")
        execution["trace"][1]["plan"].pop("expect")
        verdict = verify_and_compile(problem, planned, execution)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ACTION_EFFECT_EXPECTATION_NOT_WITNESSED", verdict["reason"])

    def test_false_runtime_expectation_fails_closed(self):
        problem, planned, execution = fixture()
        execution["trace"][1]["result"]["verified"] = False
        verdict = verify_and_compile(problem, planned, execution)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ACTION_EFFECT_EXPECTATION_NOT_WITNESSED", verdict["reason"])

    def test_resolved_action_tamper_fails_closed(self):
        problem, planned, execution = fixture()
        execution["trace"][1]["plan"]["args"]["path"] = "canonical/tmp/other.json"
        verdict = verify_and_compile(problem, planned, execution)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("RESOLVED_ACTION_MISMATCH", verdict["reason"])

    def test_undeclared_result_field_fails_closed(self):
        problem, planned, execution = fixture()
        problem["capabilities"][0]["result_fields"] = []
        verdict = verify_and_compile(problem, planned, execution)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("RESULT_REFERENCE_FIELD_UNDECLARED", verdict["reason"])

    def test_result_edge_without_declared_effect_dependency_fails_closed(self):
        problem, planned, execution = fixture()
        problem["capabilities"][1]["requires"] = ["unrelated.effect"]
        problem["initial_facts"].append("unrelated.effect")
        verdict = verify_and_compile(problem, planned, execution)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("RESULT_REFERENCE_WITHOUT_DECLARED_EFFECT_EDGE", verdict["reason"])

    def test_missing_runtime_precondition_witness_fails_closed(self):
        problem, planned, execution = fixture()
        problem["capabilities"][1]["requires"].append("never.produced")
        verdict = verify_and_compile(problem, planned, execution)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("RUNTIME_PRECONDITION_WITNESS_MISSING", verdict["reason"])

    def test_result_error_fails_closed(self):
        problem, planned, execution = fixture()
        execution["trace"][0]["result"]["error"] = "boom"
        verdict = verify_and_compile(problem, planned, execution)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ACTION_RESULT_ERROR", verdict["reason"])

    def test_trace_count_mismatch_fails_closed(self):
        problem, planned, execution = fixture()
        execution["trace"].pop()
        verdict = verify_and_compile(problem, planned, execution)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("EXECUTION_TRACE_COUNT_MISMATCH", verdict["reason"])

    def test_finish_must_be_terminal_and_nonempty(self):
        problem, planned, execution = fixture()
        execution["trace"][2]["result"]["summary"] = ""
        verdict = verify_and_compile(problem, planned, execution)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("FINISH_SUMMARY_EMPTY", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
