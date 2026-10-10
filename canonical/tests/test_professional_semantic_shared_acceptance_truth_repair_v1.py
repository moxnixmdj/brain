from copy import deepcopy
import unittest
from canonical.runtime import professional_semantic_shared_acceptance_truth_repair_v1 as v
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as p

class SemanticAcceptanceTruthRepairTests(unittest.TestCase):
    def test_current_shared_template_has_formal_overconstraint_countermodel(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_claim_count"],12)
        self.assertTrue(out["old_shared_acceptance_overstrong_proved"])
        self.assertTrue(out["countermodel"]["mission_compliant"])
        self.assertFalse(out["countermodel"]["old_acceptance_holds"])
        self.assertFalse(out["semantic_property_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_safe_unknown_is_required_and_accepted(self):
        out=v.evaluate_case(
            resolved=False,decision_null=False,status="UNKNOWN",
            positive_property_credit=False,positive_progress_credit=False,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["classification"],"SAFE_FAIL_CLOSED_UNKNOWN")

    def test_unresolved_positive_certification_is_rejected(self):
        out=v.evaluate_case(
            resolved=False,decision_null=False,status="PROVED",
            positive_property_credit=True,positive_progress_credit=True,
        )
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["reason"],"POSITIVE_CERTIFICATION_WITH_UNRESOLVED_MATERIAL_UNCERTAINTY")

    def test_resolved_positive_keeps_original_strength(self):
        out=v.evaluate_case(
            resolved=True,decision_null=False,status="PROVED",
            positive_property_credit=True,positive_progress_credit=True,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["classification"],"RESOLVED_POSITIVE")

    def test_nonpositive_status_cannot_mint_positive_credit(self):
        out=v.evaluate_case(
            resolved=False,decision_null=False,status="OPEN",
            positive_property_credit=True,positive_progress_credit=False,
        )
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["reason"],"UNRESOLVED_INPUT_GRANTED_POSITIVE_CREDIT")

    def test_shared_template_drift_fails_closed(self):
        pack=p.verify()
        self.assertTrue(pack["pass"],pack)
        pack=deepcopy(pack)
        pack["claims"][0]["target_predicate"]["acceptance"]="WEAKER"
        import json
        from pathlib import Path
        root=Path(v.__file__).resolve().parents[2]
        mission=json.loads((root/v.MISSION_PATH).read_text())
        theorem=json.loads((root/v.ROOT_THEOREM_PATH).read_text())
        scope=json.loads((root/v.SCOPE_VERIFY_PATH).read_text())
        out=v.analyze(pack,mission,theorem,scope)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["reason"],"SHARED_ACCEPTANCE_NOT_UNIFORM")

    def test_missing_unknown_never_proved_law_fails_closed(self):
        pack=p.verify()
        self.assertTrue(pack["pass"],pack)
        import json
        from pathlib import Path
        root=Path(v.__file__).resolve().parents[2]
        mission=json.loads((root/v.MISSION_PATH).read_text())
        theorem=json.loads((root/v.ROOT_THEOREM_PATH).read_text())
        theorem["hard_rules"]=[x for x in theorem["hard_rules"] if x!=v.UNKNOWN_RULE]
        scope=json.loads((root/v.SCOPE_VERIFY_PATH).read_text())
        out=v.analyze(pack,mission,theorem,scope)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["reason"],"ROOT_THEOREM_UNKNOWN_RULE_MISSING")

    def test_repair_does_not_grant_authority(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        for field in ("semantic_property_truth_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
            self.assertFalse(out[field],field)
        self.assertEqual(out["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
