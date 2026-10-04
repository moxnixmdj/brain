from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.general_literal_response_v1 import (
    parse_literal_response_instruction,
    run_literal_response_instruction,
)
from canonical.runtime import astra_runtime

PRE=Path(__file__).resolve().parents[1]/"governance"/"GENERAL_LITERAL_RESPONSE_PREEXPOSURE_V1.json"


class GeneralLiteralResponseTests(unittest.TestCase):
    def test_frozen_positive_population_exact(self):
        doc=json.loads(PRE.read_text())
        self.assertEqual(len(doc["positive_tasks"]),8)
        for task in doc["positive_tasks"]:
            parsed=parse_literal_response_instruction(task["instruction"])
            self.assertIsNotNone(parsed,task["id"])
            self.assertEqual(parsed["payload"],task["expected"],task["id"])
            self.assertEqual(parsed["persistent_learned_bytes"],0)
            self.assertEqual(parsed["external_frontier_model_calls"],0)
            self.assertEqual(parsed["network_calls"],0)
            self.assertEqual(parsed["tool_calls"],0)

    def test_frozen_negative_population_abstains(self):
        doc=json.loads(PRE.read_text())
        self.assertEqual(len(doc["negative_tasks"]),8)
        for task in doc["negative_tasks"]:
            self.assertIsNone(
                parse_literal_response_instruction(task["instruction"]),
                task["id"],
            )

    def test_model_independent_result_contract(self):
        out=run_literal_response_instruction("Output exactly \"safe literal\"")
        self.assertEqual(out["stdout"],"safe literal")
        self.assertEqual(out["final_summary"],"safe literal")
        self.assertEqual(out["controller_mode"],"MODEL_INDEPENDENT_ACTION_PLAN")
        self.assertIsNone(out["planner_source"])
        self.assertEqual(out["literal_response_contract"]["tool_calls"],0)

    def test_non_string_abstains(self):
        for value in (None,1,{},[]):
            self.assertIsNone(parse_literal_response_instruction(value))

    def test_astra_runtime_routes_frozen_positive_without_acquisition(self):
        doc=json.loads(PRE.read_text())
        instruction=doc["positive_tasks"][0]["instruction"]
        expected=doc["positive_tasks"][0]["expected"]
        out=astra_runtime.run_goal(
            {
                "goal_ref":"goal",
                "allow_optional_model_planner":False,
                "max_controller_actions":4,
                "max_cycles":2,
            },
            {"mission_id":"GENERAL-LITERAL-RESPONSE-PREEXPOSURE","goal":instruction},
        )
        self.assertEqual(out["stdout"],expected)
        self.assertEqual(out["cognition_dependency_class"],"MODEL_INDEPENDENT")
        self.assertEqual(out["model_dependency_count"],0)
        self.assertEqual(out["literal_response_contract"]["tool_calls"],0)
        self.assertEqual(out["literal_response_contract"]["network_calls"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
