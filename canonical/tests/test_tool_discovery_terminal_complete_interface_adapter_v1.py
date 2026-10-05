import unittest

from canonical.runtime import tool_discovery_information_safe_proof_v2 as v2
from canonical.runtime import tool_discovery_information_safe_candidate as old_policy
from canonical.runtime import tool_discovery_dynamic_candidate_v3 as dynamic_policy
from canonical.runtime import tool_discovery_terminal_complete_interface_adapter_v1 as adapter


class TerminalCompleteInterfaceAdapterTests(unittest.TestCase):
    def test_interface_hides_ids_then_returns_exact_complete_case_tool_set(self):
        case=v2.generate_case(17,0)
        before=adapter.dynamic_public(case,1,(),discovered=False)
        self.assertEqual(before["visible_tools"],[])
        self.assertNotIn("tool_ids",before["discovery_sources"][0])
        action=dynamic_policy.next_action(before)
        self.assertEqual(action["action"],"DISCOVER")
        self.assertEqual(action["source_id"],adapter.SOURCE_ID)

        source=adapter.discovery_source(case)
        receipt=adapter.discovery_receipt(case,action["query"])
        self.assertEqual(set(source["tool_ids"]),{t["tool_id"] for t in case["tools"]})
        self.assertEqual(receipt["tools"],case["tools"])

    def test_post_discovery_representative_action_matches_terminal_policy(self):
        case=v2.generate_case(23,2)
        old=v2.public_stage(case,1,())
        new=adapter.dynamic_public(case,1,(),discovered=True)
        self.assertEqual(
            adapter._norm_action(old_policy.next_action(old)),
            adapter._norm_action(dynamic_policy.next_action(new)),
        )

    def test_all_six_v2_classes_satisfy_interface_contract_shape(self):
        for ordinal,cls in enumerate(v2.CLASSES):
            case=v2.generate_case(0,ordinal)
            self.assertEqual(adapter._interface_case_errors(case),[],cls)

    def test_small_equivalence_mutation_surface(self):
        states=[
            (-1,)*8,
            (1,1,-1,-1,-1,-1,-1,-1),
            (0,1,-1,-1,-1,-1,-1,-1),
        ]
        for changed in (None,0,1):
            for mask in (0,1,3,15):
                for state in states:
                    old,new=adapter._synthetic_public(mask,state,changed_tool=changed)
                    self.assertEqual(
                        adapter._norm_action(old_policy.next_action(old)),
                        adapter._norm_action(dynamic_policy.next_action(new)),
                    )

    def test_baseline_metadata_verdict_without_expensive_exhaustion(self):
        out=adapter.evaluate(run_exhaustive=False)
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertTrue(out["complete_interface_instance_candidate"])
        self.assertEqual(out["terminal_population_binding"]["immutable_cases"],180)
        self.assertEqual(out["terminal_population_binding"]["immutable_passes"],180)
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertFalse(out["whole_protocol_scope_proved"])


if __name__=="__main__":
    unittest.main(verbosity=2)
