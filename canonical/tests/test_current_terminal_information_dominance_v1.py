from __future__ import annotations
import json,unittest
from pathlib import Path
from canonical.runtime.current_terminal_information_dominance_v1 import evaluate
from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as tool_retrieval_gate

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
            tool_retrieval_gate.evaluate_repository(ROOT),
        )

    def test_exact_live_world(self):
        x=self.result()
        self.assertTrue(x["pass"],x)
        s=x["live_world_summary"]
        self.assertEqual((s["frozen_predicates"],s["proved_predicates"],s["unresolved_predicates"]),(38,11,27))
        self.assertEqual(s["live_action_coverage_count"],27)

    def test_dominance_is_exact_and_current(self):
        x=self.result()
        d=x["dominance"]
        self.assertEqual(d["status"],"EXACT_INFORMATION_DOMINANCE_COMPUTED")
        self.assertEqual(d["unresolved_predicate_count"],27)
        self.assertEqual(d["certificate_count"],x["live_world_summary"]["live_certificate_count"])
        self.assertLessEqual(d["certificate_count"],20)
        self.assertIsNotNone(d["best_full_frontier_bundle"])
        self.assertEqual(d["best_full_frontier_bundle"]["covered_predicate_count"],27)

    def test_closed_recovery_and_delegation_certificates_are_absent(self):
        x=self.result()
        ids=set(x["dominance"]["nondominated_certificate_ids"])|set(x["dominance"]["dominated_certificate_ids"])
        self.assertNotIn("DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE",ids)
        covered={p for row in x["dominance"]["single_certificate_structural_front"] for p in row["covered_predicates"]}
        self.assertNotIn("DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",covered)
        self.assertNotIn("RECOVERY_TERMINAL_NONINFERIOR",covered)
        self.assertNotIn("RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",covered)
        self.assertNotIn("RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",covered)
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
