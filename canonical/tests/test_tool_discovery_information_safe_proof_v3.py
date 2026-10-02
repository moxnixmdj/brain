import unittest

from canonical.runtime.tool_discovery_information_safe_candidate import next_action
from canonical.runtime import tool_discovery_information_safe_proof_v3 as v3


class ToolDiscoveryV3Tests(unittest.TestCase):
    def test_full_v3_batch(self):
        out = v3.run_batch(20261002, 90, next_action)
        self.assertTrue(out["all_pass"], out["failures"][:5])
        for cls in v3.CLASSES:
            self.assertGreater(out["by_class"][cls]["total"], 0)
            self.assertEqual(out["by_class"][cls]["pass"], out["by_class"][cls]["total"])

    def test_dynamic_discovery_requires_new_tool(self):
        ordinal = v3.CLASSES.index("DYNAMIC_DISCOVERY")
        case = v3.generate_case(7, ordinal)
        out = v3.score_episode(case, next_action)
        self.assertTrue(out["pass"], out)
        discovered = {e["tool"]["tool_id"] for e in case["stage1"]["catalog_events"]}
        self.assertIn(out["selected"], discovered)

    def test_active_constraint_schema(self):
        ordinal = v3.CLASSES.index("ACTIVE_CONSTRAINT_SCHEMA")
        case = v3.generate_case(11, ordinal)
        out = v3.score_episode(case, next_action)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected"], v3._oracle_best(case))

    def test_strict_baseline_advantage(self):
        ordinal = v3.CLASSES.index("BASELINE_ADVANTAGE")
        case = v3.generate_case(13, ordinal)
        out = v3.score_episode(case, next_action)
        self.assertTrue(out["pass"], out)
        self.assertLess((out["selected_cost"], out["probe_count"]), (out["baseline"]["selected_cost"], out["baseline"]["probe_count"]))


if __name__ == "__main__":
    unittest.main()
