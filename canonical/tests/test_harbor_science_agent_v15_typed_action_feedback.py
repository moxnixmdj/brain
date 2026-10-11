from __future__ import annotations

import unittest

from canonical.runtime import harbor_science_agent_v15 as agent
from canonical.runtime import harbor_science_planner_v8 as planner


def candidate(command: str, *, schema=None):
    return {
        "action_id": "a",
        "covers": ["R1"],
        "executor": "python",
        "command": command,
        "verify_executor": "shell",
        "verify_command": "true",
        "schema_requirements": list(schema or []),
    }


class TypedActionFeedbackV15Tests(unittest.TestCase):
    def test_python_syntax_failure_exposes_finite_feedback_code(self):
        rows, rejected = agent._candidate_rows([candidate("for")], {"R1"})
        self.assertEqual(rows, [])
        self.assertEqual(len(rejected), 1)
        self.assertEqual(
            rejected[0].get("validation_error_code"),
            "PYTHON_SOURCE_SYNTAX_INVALID",
        )
        self.assertNotIn("error", rejected[0].get("validation_error_code", "").lower())

    def test_undeclared_literal_key_exposes_prefix_not_dynamic_key_material(self):
        rows, rejected = agent._candidate_rows(
            [candidate("print(spec['box'])")],
            {"R1"},
        )
        self.assertEqual(rows, [])
        self.assertEqual(
            rejected[0].get("validation_error_code"),
            "PYTHON_LITERAL_SCHEMA_KEYS_UNDECLARED",
        )
        self.assertNotIn("box", rejected[0].get("validation_error_code", ""))

    def test_valid_typed_python_still_passes_unchanged_gate(self):
        rows, rejected = agent._candidate_rows(
            [candidate(
                "print(spec['box'])",
                schema=[{"path": "/app/spec.json", "format": "json", "keys": ["box"]}],
            )],
            {"R1"},
        )
        self.assertEqual(rejected, [])
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["command"].startswith("python -c "))

    def test_planner_system_contract_requires_raw_parseable_python(self):
        payload = planner._seedless_request_payload("synthetic")
        system = payload["messages"][0]["content"]
        self.assertIn("raw Python source", system)
        self.assertIn("ast.parse", system)
        self.assertIn("no Markdown fences", system)
        self.assertIn("validation_error_code", system)

    def test_agent_prompt_carries_validation_feedback_to_next_cycle(self):
        prompt = agent.build_science_planner_prompt(
            goal="synthetic",
            requirements=["R1"],
            unresolved=["R1"],
            raw_task_prompt_summary={"ordered_manifest_sha256": "0" * 64},
            declared_inputs=[],
            brain_deliverables={},
            observations=[{
                "kind": "PLANNER_CANDIDATE_REJECTED",
                "cycle": 0,
                "action_id": "a",
                "validation_error_code": "PYTHON_SOURCE_SYNTAX_INVALID",
            }],
        )
        self.assertIn("PYTHON_SOURCE_SYNTAX_INVALID", prompt)
        self.assertIn("repair that exact validation class", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
