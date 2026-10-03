from __future__ import annotations
import json,unittest
from pathlib import Path
from canonical.runtime.current_terminal_information_dominance_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    def result(self):
        return evaluate(
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
            load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
            load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
            load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
        )

    def test_exact_live_world(self):
        x=self.result()
        self.assertTrue(x["pass"],x)
        s=x["live_world_summary"]
        self.assertEqual((s["frozen_predicates"],s["proved_predicates"],s["unresolved_predicates"]),(38,8,30))
        self.assertEqual(s["live_action_coverage_count"],30)

    def test_dominance_is_exact_and_current(self):
        x=self.result()
        d=x["dominance"]
        self.assertEqual(d["status"],"EXACT_INFORMATION_DOMINANCE_COMPUTED")
        self.assertEqual(d["unresolved_predicate_count"],30)
        self.assertEqual(d["certificate_count"],x["live_world_summary"]["live_certificate_count"])
        self.assertLessEqual(d["certificate_count"],20)
        self.assertIsNotNone(d["best_full_frontier_bundle"])
        self.assertEqual(d["best_full_frontier_bundle"]["covered_predicate_count"],30)

    def test_closed_delegation_certificate_is_absent(self):
        x=self.result()
        ids=set(x["dominance"]["nondominated_certificate_ids"])|set(x["dominance"]["dominated_certificate_ids"])
        self.assertNotIn("DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE",ids)
        covered={p for row in x["dominance"]["single_certificate_structural_front"] for p in row["covered_predicates"]}
        self.assertNotIn("DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",covered)
        self.assertIn("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",covered)

    def test_zero_credit_zero_reality(self):
        x=self.result()
        self.assertEqual(x["new_reality_units_consumed"],0)
        self.assertEqual(x["incremental_spend_usd"],0)
        self.assertFalse(x["execution_authority"])
        self.assertFalse(x["promotion_authority"])
        self.assertFalse(x["fresh_reality_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
