from __future__ import annotations
import unittest
from pathlib import Path

from canonical.runtime import tool_discovery_dynamic_v4_refinement_v1 as ref

ROOT=Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
    def test_live_candidate_falsifies_v3_and_proves_v4_program_side(self):
        out=ref.evaluate()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertTrue(out["v3_least_cost_claim_falsified"])
        self.assertTrue(out["v4_conditional_program_proof"])
        self.assertFalse(out["universal_target_proved"])
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)

    def test_counterexample_is_exact(self):
        out=ref.evaluate()
        self.assertEqual(out["v3_counterexample_trace"],[
            {"action":"PROBE","tool_id":"T0","capability":"CAP_A"},
            {"action":"SELECT","tool_id":"T0"},
        ])
        self.assertEqual(out["v4_counterexample_first_action"],{
            "action":"DISCOVER","source_id":"S0","query":"CAP_A",
        })

    def test_discovery_after_tool_evaluation_kills_proof(self):
        src=(ROOT/ref.V4).read_text(encoding="utf-8")
        marker_a='queried=_queried_sources(public)'
        marker_b='evidence=_evidence(public)'
        # Mutate only the certificate view of source ordering.
        mutant=src.replace(marker_a,"queried_marker_removed",1)
        out=ref.evaluate(v4_source_override=mutant)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertFalse(out["v4_conditional_program_proof"])

    def test_queried_source_exclusion_is_load_bearing(self):
        src=(ROOT/ref.V4).read_text(encoding="utf-8")
        mutant=src.replace(
            'and str(s.get("source_id") or "") not in queried',
            '',
            1,
        )
        out=ref.evaluate(v4_source_override=mutant)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("DISCOVERY_STRICTLY_EXCLUDES_QUERIED_SOURCES",out["missing"])

    def test_cost_order_is_load_bearing(self):
        src=(ROOT/ref.V4).read_text(encoding="utf-8")
        mutant=src.replace(
            'tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))',
            'tools.sort(key=lambda t:str(t.get("tool_id") or ""))',
            1,
        )
        out=ref.evaluate(v4_source_override=mutant)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("GLOBAL_TOOL_COST_ORDER",out["missing"])

    def test_external_interface_fact_remains_open(self):
        out=ref.evaluate()
        self.assertEqual(
            out["minimum_missing_fact"],
            "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
            "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1",
        )
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["new_reality_units_consumed"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
