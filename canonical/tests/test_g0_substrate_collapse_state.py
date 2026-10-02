import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text())

class G0SubstrateCollapseStateTests(unittest.TestCase):
    def test_g0_collapse_is_fail_closed_and_zero_credit(self):
        g0 = load("canonical/governance/G0_PROPOSAL_SUBSTRATE_COLLAPSE_V1.json")
        self.assertFalse(g0["new_state"]["independent_mechanism_residual"])
        self.assertEqual(g0["capability_credit_delta"], 0)
        self.assertEqual(g0["family_credit_delta"], 0)
        self.assertIn("NO_EXTERNAL_OR_OPAQUE_PROPOSER_OUTPUT_RECEIVES_TRUTH_AUTHORITY", g0["guards"])
        self.assertIn("NO_BYPASS_WHERE_THE_VERIFIER_HAS_FALSE_POSITIVE_GAPS_FOR_THE_CLAIMED_SCOPE", g0["guards"])
        cases = {x["case"]: x["disposition"] for x in g0["case_partition"]}
        self.assertEqual(cases["NOVEL_CANDIDATE_WITHOUT_COMPLETE_INDEPENDENT_VERIFIER"],
                         "S0_RAW_CONTEXT_TO_SOURCE_TRACEABLE_SEMANTIC_OR_EFFECT_MODEL_ACQUISITION")

    def test_only_s0_remains_as_implementation_residual(self):
        shared = load("canonical/governance/SHARED_SEMANTIC_RESIDUAL_BASIS_V2.json")
        graph = load("canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json")
        cut = load("canonical/governance/GLOBAL_TERMINAL_PROOF_CUT_V1.json")
        outer = load("canonical/governance/OUTER_GLOBAL_MINIMUM_REALITY_CUT_VERDICT_V2.json")
        self.assertEqual(shared["compression_result"]["implementation_lanes_still_open"], [])
        self.assertEqual(shared["compression_result"]["true_remaining_implementation_classes"],
                         ["S0_RAW_CONTEXT_TO_TYPED_FACT_TEMPLATE_AND_EFFECT_MODEL"])
        self.assertEqual(graph["open_mechanism_residuals"], [])
        self.assertEqual(graph["shared_cross_lane_open_mechanisms"],
                         ["S0_RAW_CONTEXT_TO_TYPED_FACT_TEMPLATE_AND_EFFECT_MODEL"])
        self.assertEqual(cut["current_mechanism_frontier"]["lane_local"], [])
        self.assertEqual(cut["current_mechanism_frontier"]["shared"], ["S0"])
        self.assertEqual(cut["current_mechanism_frontier"]["deterministic_tail"], [])
        self.assertIn("G0", cut["current_mechanism_frontier"]["proof_only"])
        self.assertIn("D0", cut["current_mechanism_frontier"]["proof_only"])
        self.assertEqual(outer["mechanism_state"]["shared_cross_lane_open"],
                         ["S0_RAW_CONTEXT_TO_TYPED_FACT_TEMPLATE_AND_EFFECT_MODEL"])

    def test_terminal_evidence_remains_blocked(self):
        universe = load("canonical/governance/GLOBAL_TERMINAL_UNIVERSE_V1.json")
        outer = load("canonical/governance/OUTER_GLOBAL_MINIMUM_REALITY_CUT_VERDICT_V2.json")
        self.assertFalse(universe["execution_authority"]["fresh_terminal_evidence_allowed"])
        self.assertFalse(universe["global_cut"]["execution_ready"])
        self.assertIn("S0_RAW_CONTEXT_TO_TYPED_FACT_TEMPLATE_AND_EFFECT_MODEL",
                      universe["global_cut"]["open_mechanism_holes"])
        self.assertNotIn("G0_NOVEL_TYPED_TEMPLATE_AND_EFFECT_MODEL_SYNTHESIS",
                         universe["global_cut"]["open_mechanism_holes"])
        self.assertIn("SHARED_S0_ROUTE_NOT_YET_FROZEN_AT_REQUIRED_SCOPE",
                      outer["execution_blockers"])

    def test_authority_mirrors_are_exactly_aligned(self):
        h = load("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json")
        p = load("canonical/CANONICAL_POINTER.json")
        s = load("canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json")
        q = load("canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json")
        c = load("canonical/capabilities/frontier/ADVANCED_AGENTIC_SOFTWARE_ENGINEERING_SUPERPOWERS_V1.json")
        blocker = h["current_parent_blocker"]
        nxt = h["next_required_action_class"]
        progress = h["next_progress_event_target"]
        self.assertEqual(p["current_frontier"]["critical_blocker"], blocker)
        self.assertEqual(p["current_frontier"]["highest_leverage_capability_gap"], blocker)
        self.assertEqual(p["current_frontier"]["next_step"], nxt)
        self.assertEqual(p["current_frontier"]["next_progress_event_target"], progress)
        self.assertEqual(s["active_frontier_accounting"]["residual_gap"], blocker)
        self.assertEqual(s["active_frontier_accounting"]["current_parent_blocker"], blocker)
        self.assertEqual(s["active_frontier_accounting"]["next_required_action"], nxt)
        self.assertEqual(s["next_required_action"], nxt)
        self.assertEqual(s["next_progress_event_target"], progress)
        self.assertEqual(q["immediate_frontier"]["exact_blocker"], blocker)
        self.assertEqual(q["immediate_frontier"]["next_action"], nxt)
        self.assertEqual(q["immediate_frontier"]["next_progress_event_target"], progress)
        self.assertEqual(c["current_atomic_blocker"], blocker)
        self.assertEqual(c["current_atomic_next_action"], nxt)
        self.assertEqual(c["current_atomic_progress_event"], progress)

if __name__ == "__main__":
    unittest.main(verbosity=2)
