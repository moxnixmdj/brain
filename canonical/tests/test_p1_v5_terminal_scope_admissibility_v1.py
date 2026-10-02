from __future__ import annotations
import copy
import unittest
from canonical.runtime import p1_v5_terminal_scope_admissibility_v1 as gate

class P1V5TerminalScopeAdmissibilityTests(unittest.TestCase):
    def test_live_state_has_three_open_relations_and_no_clearance(self):
        out=gate.evaluate()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertEqual(out["open_surface_count"],3)
        self.assertFalse(out["scope_transport_admissible"])
        self.assertFalse(out["p1_scope_quarantine_clearable"])
        self.assertEqual(out["new_reality_units_consumed"],0)

    def test_synthetic_v5_pass_does_not_imply_surface_relation(self):
        r=copy.deepcopy(gate._load(gate.RELATIONS))
        r["status"]="ACTIVE_V5_IS_VERY_BROAD"
        out=gate.evaluate(relations=r)
        self.assertFalse(out["scope_transport_admissible"])
        self.assertEqual(out["open_surface_count"],3)

    def test_relation_without_claim_bound_witness_or_independent_verification_is_not_admissible(self):
        r=copy.deepcopy(gate._load(gate.RELATIONS))
        r["relations"][0]["relation"]="SUPERSET"
        out=gate.evaluate(relations=r)
        self.assertFalse(out["surface_relations"][0]["relation_admissible"])
        self.assertIn("CLAIM_BOUND_SCOPE_WITNESS",out["surface_relations"][0]["missing"])
        self.assertIn("INDEPENDENT_RELATION_VERIFICATION",out["surface_relations"][0]["missing"])

    def test_three_independently_verified_exact_relations_only_open_composite_restoration(self):
        r=copy.deepcopy(gate._load(gate.RELATIONS))
        for i,row in enumerate(r["relations"]):
            row["relation"]="EXACT"
            row["claim_bound_scope_witness"]={"path":f"receipt-{i}.json","claim_id":f"P1-SURFACE-{i}"}
            row["independent_verification"]={"path":f"verify-{i}.json","status":"INDEPENDENT_PASS__EXACT_RELATION"}
        out=gate.evaluate(relations=r)
        self.assertTrue(out["scope_transport_admissible"],out)
        self.assertEqual(out["open_surface_count"],0)
        self.assertFalse(out["p1_scope_quarantine_clearable"])
        self.assertEqual(out["remaining_after_scope_transport"],["P1_COMPOSITE_RESTORATION_INDEPENDENT_RECONCILIATION"])

    def test_removing_synthetic_firewall_fails_closed(self):
        b=copy.deepcopy(gate._load(gate.BINDING))
        b["terminal_acceptance"]["standalone_synthetic_whole_domain_score_forbidden"]=False
        out=gate.evaluate(binding=b)
        self.assertEqual(out["status"],"FAIL_CLOSED__SOURCE_OR_RELATION_DRIFT")
        self.assertIn("SYNTHETIC_SCORE_FIREWALL_MISSING",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
