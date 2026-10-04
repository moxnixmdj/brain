from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.general_literal_response_v1 import (
    parse_literal_response_instruction,
    run_literal_response_instruction,
)

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


if __name__=="__main__":
    unittest.main(verbosity=2)
