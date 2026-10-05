import json, unittest
from canonical.runtime import h100_typed_capability_planner_v1 as p

EXPECTED=["OP_COMPOSITIONAL_LANGUAGE","OP_TOOL_TRACE_NORMALIZER","OP_PARAMETRIC_REGISTRY_RESOLVER"]

class H100TypedCapabilityPlannerTests(unittest.TestCase):
    def test_planner_derives_shortest_chain_without_task_values(self):
        d=json.loads(p.PRE.read_text())
        out=p.derive_plan(d["initial_resources"],d["goal_resource"])
        self.assertEqual(out["status"],"PLAN_FOUND")
        self.assertEqual(out["plan"],EXPECTED)
        self.assertEqual(out["plan_length"],3)

    def test_irrelevant_lexical_operators_are_not_selected(self):
        out=p.derive_plan(["SCHEMA_TEXT","RAW_TOOL_TRACE"],"PREDICTOR_RESOLUTION")
        self.assertTrue(all("LEXICAL" not in x for x in out["plan"]))

    def test_missing_schema_text_has_no_plan(self):
        out=p.derive_plan(["RAW_TOOL_TRACE"],"PREDICTOR_RESOLUTION")
        self.assertEqual(out["status"],"NO_PLAN")

    def test_derived_plan_executes_three_positive_tasks_and_one_fail_closed_control(self):
        out=p.run()
        self.assertEqual(out["positive_tasks_passed"],3)
        self.assertTrue(out["negative_control_fail_closed"])
        self.assertEqual(out["derived_plan"]["plan"],EXPECTED)
        self.assertEqual(out["persistent_learned_bytes"],0)
        for row in out["task_results"]:
            self.assertEqual(row["executed_plan"],EXPECTED)
            self.assertEqual(row.get("raw_synthesis_attempts_executed"),0)

if __name__=="__main__":
    unittest.main(verbosity=2)
