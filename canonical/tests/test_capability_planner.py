#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
PLANNER_PATH = CANONICAL_ROOT / "runtime" / "capability_planner.py"
spec = importlib.util.spec_from_file_location("capability_planner_test_target", PLANNER_PATH)
planner = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = planner
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


    def test_plan_actions_wires_prior_effect_result_into_consumer(self):
        problem = {
            "initial_facts": [],
            "target_effects": ["record.written"],
            "capabilities": [
                {
                    "id": "learn-value",
                    "requires": [],
                    "provides": ["knowledge.value.available"],
                    "result_fields": ["value"],
                    "cost": 1,
                    "action": {"type": "fetch_json_knowledge", "args": {"url": "https://example.test/value"}}
                },
                {
                    "id": "write-value",
                    "requires": ["knowledge.value.available"],
                    "provides": ["record.written"],
                    "cost": 1,
                    "action": {
                        "type": "write_json_records",
                        "args": {
                            "value": {
                                "$effect_result": {
                                    "effect": "knowledge.value.available",
                                    "field": "value"
                                }
                            }
                        }
                    }
                }
            ]
        }
        out = planner.plan_actions(problem)
        self.assertEqual(out["planning"]["plan"], ["learn-value", "write-value"])
        self.assertEqual(
            out["actions"][1]["args"]["value"],
            {"$result": {"cycle": 0, "field": "value"}},
        )

    def test_effect_result_binding_rejects_undeclared_provider_field(self):
        problem = {
            "initial_facts": [],
            "target_effects": ["record.written"],
            "capabilities": [
                {
                    "id": "learn-value",
                    "requires": [],
                    "provides": ["knowledge.value.available"],
                    "result_fields": [],
                    "cost": 1,
                    "action": {"type": "fetch_json_knowledge", "args": {}}
                },
                {
                    "id": "write-value",
                    "requires": ["knowledge.value.available"],
                    "provides": ["record.written"],
                    "cost": 1,
                    "action": {
                        "type": "write_json_records",
                        "args": {
                            "value": {
                                "$effect_result": {
                                    "effect": "knowledge.value.available",
                                    "field": "value"
                                }
                            }
                        }
                    }
                }
            ]
        }
        with self.assertRaisesRegex(
            planner.PlanningFailure,
            "BINDING_RESULT_FIELD_UNDECLARED:learn-value:value",
        ):
            planner.plan_actions(problem)

    def test_plan_actions_wires_multiple_required_effect_results(self):
        problem = {
            "initial_facts": [],
            "target_effects": ["assessment.available"],
            "capabilities": [
                {
                    "id": "observe-a",
                    "requires": [],
                    "provides": ["observation.a"],
                    "result_fields": ["output_path"],
                    "cost": 1,
                    "action": {"type": "fetch_json_knowledge", "args": {"output_path": "a.json"}}
                },
                {
                    "id": "observe-b",
                    "requires": [],
                    "provides": ["observation.b"],
                    "result_fields": ["output_path"],
                    "cost": 1,
                    "action": {"type": "fetch_json_knowledge", "args": {"output_path": "b.json"}}
                },
                {
                    "id": "assess",
                    "requires": ["observation.a", "observation.b"],
                    "provides": ["assessment.available"],
                    "result_fields": ["output_path"],
                    "cost": 1,
                    "action": {
                        "type": "assess_knowledge_consistency",
                        "args": {
                            "evidence_paths": [
                                {"$effect_result": {"effect": "observation.a", "field": "output_path"}},
                                {"$effect_result": {"effect": "observation.b", "field": "output_path"}}
                            ],
                            "output_path": "assessment.json"
                        }
                    }
                }
            ]
        }
        out = planner.plan_actions(problem)
        self.assertEqual(out["planning"]["plan"], ["observe-a", "observe-b", "assess"])
        self.assertEqual(
            out["actions"][2]["args"]["evidence_paths"],
            [
                {"$result": {"cycle": 0, "field": "output_path"}},
                {"$result": {"cycle": 1, "field": "output_path"}}
            ],
        )

    def test_effect_result_binding_must_correspond_to_required_effect(self):
        problem = {
            "initial_facts": [],
            "target_effects": ["record.written"],
            "capabilities": [
                {
                    "id": "learn-value",
                    "requires": [],
                    "provides": ["knowledge.value.available"],
                    "result_fields": ["value"],
                    "cost": 1,
                    "action": {"type": "fetch_json_knowledge", "args": {}}
                },
                {
                    "id": "write-value",
                    "requires": ["knowledge.value.available"],
                    "provides": ["record.written"],
                    "cost": 1,
                    "action": {
                        "type": "write_json_records",
                        "args": {
                            "value": {
                                "$effect_result": {
                                    "effect": "unrelated.effect",
                                    "field": "value"
                                }
                            }
                        }
                    }
                }
            ]
        }
        with self.assertRaisesRegex(
            planner.PlanningFailure,
            "BINDING_EFFECT_NOT_REQUIRED:write-value:unrelated.effect",
        ):
            planner.plan_actions(problem)


if __name__ == "__main__":
    unittest.main(verbosity=2)
