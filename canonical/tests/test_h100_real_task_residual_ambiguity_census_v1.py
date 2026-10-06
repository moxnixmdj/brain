import unittest
from canonical.runtime import h100_real_task_residual_ambiguity_census_v1 as c

class H100RealTaskResidualAmbiguityCensusTests(unittest.TestCase):
    def test_chain_collapses_1554_to_one(self):
        row=c.chain_case()
        self.assertEqual(row["raw_hypothesis_count"],1554)
        self.assertEqual(row["raw_identity_bits"],11)
        self.assertEqual(row["largest_residual_equivalence_class"],1)
        self.assertEqual(row["perfect_identification_information_lower_bound_bits"],0)

    def test_planner_shortest_plan_is_unique(self):
        row=c.planner_case()
        self.assertEqual(row["shortest_plan_length"],3)
        self.assertEqual(row["shortest_valid_plan_count"],1)
        self.assertEqual(row["perfect_identification_information_lower_bound_bits"],0)
        self.assertEqual(row["shortest_valid_plans"][0],[
            "OP_COMPOSITIONAL_LANGUAGE",
            "OP_TOOL_TRACE_NORMALIZER",
            "OP_PARAMETRIC_REGISTRY_RESOLVER",
        ])

    def test_real_lexical_resolved_and_abstentions_stay_separate(self):
        row=c.lexical_case()
        self.assertEqual(row["frozen_task_count"],9)
        self.assertEqual(row["resolved_task_count"],6)
        self.assertEqual(row["abstention_task_count"],3)
        self.assertEqual(row["resolved_tasks_largest_residual_equivalence_class"],1)
        self.assertFalse(row["abstentions_receive_zero_bit_credit"])

    def test_event_history_determines_single_state(self):
        row=c.memory_case()
        self.assertEqual(row["event_count"],10000)
        self.assertEqual(row["restart_count"],3)
        self.assertEqual(row["largest_residual_equivalence_class_given_authenticated_history"],1)
        self.assertEqual(row["perfect_identification_information_lower_bound_bits"],0)

    def test_full_census(self):
        out=c.run()
        self.assertEqual(out["case_count"],4)
        self.assertEqual(out["fully_resolved_case_classes"],3)
        self.assertEqual(out["real_lexical_resolved_tasks"],6)
        self.assertEqual(out["real_lexical_abstentions"],3)
        self.assertEqual(out["h100_terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
