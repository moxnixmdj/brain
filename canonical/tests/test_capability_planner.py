#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
PLANNER_PATH = CANONICAL_ROOT / "runtime" / "capability_planner.py"
spec = importlib.util.spec_from_file_location("capability_planner_test_target", PLANNER_PATH)
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


class CapabilityPlannerTests(unittest.TestCase):
    def test_selects_lowest_cost_valid_composition(self):
        problem = {
            "initial_facts": ["repo.available"],
            "target_effects": ["law.inspected"],
            "capabilities": [
                {
                    "id": "expensive-direct",
                    "requires": ["repo.available"],
                    "provides": ["law.inspected"],
                    "cost": 10,
                    "action": {"type": "read_file", "args": {"path": "canonical/laws/MODEL_NON_DEPENDENCE_LAW_V1.md"}}
                },
                {
                    "id": "locate-law",
                    "requires": ["repo.available"],
                    "provides": ["law.located"],
                    "cost": 1,
                    "action": {"type": "search_text", "args": {"query": "No step above requires an LLM."}}
                },
                {
                    "id": "read-located-law",
                    "requires": ["law.located"],
                    "provides": ["law.inspected"],
                    "cost": 1,
                    "action": {"type": "read_file", "args": {"path": "canonical/laws/MODEL_NON_DEPENDENCE_LAW_V1.md"}}
                }
            ]
        }
        result = planner.plan_capabilities(problem)
        self.assertEqual(result["plan"], ["locate-law", "read-located-law"])
        self.assertEqual(result["total_cost"], 2.0)

    def test_unreachable_effect_fails_closed(self):
        problem = {
            "initial_facts": [],
            "target_effects": ["missing.effect"],
            "capabilities": [{
                "id": "irrelevant",
                "requires": [],
                "provides": ["other.effect"],
                "cost": 1,
                "action": {"type": "list_tree", "args": {"prefix": "canonical"}}
            }]
        }
        with self.assertRaisesRegex(planner.PlanningFailure, "UNREACHABLE_TARGET_EFFECTS:missing.effect"):
            planner.plan_capabilities(problem)

    def test_plan_actions_compiles_executable_actions_and_finish(self):
        problem = {
            "initial_facts": [],
            "target_effects": ["tree.listed"],
            "finish_summary": "CAPABILITY_GRAPH_GOAL_COMPLETE",
            "capabilities": [{
                "id": "list-canonical",
                "requires": [],
                "provides": ["tree.listed"],
                "cost": 1,
                "action": {"type": "list_tree", "args": {"prefix": "canonical"}}
            }]
        }
        out = planner.plan_actions(problem)
        self.assertEqual(out["actions"][0]["capability_id"], "list-canonical")
        self.assertEqual(out["actions"][-1]["type"], "finish")
        self.assertEqual(out["actions"][-1]["args"]["summary"], "CAPABILITY_GRAPH_GOAL_COMPLETE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
