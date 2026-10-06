from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CONTROL=ROOT/"canonical/governance/TERMINAL_UTILITY_QUOTIENT_CONTROL_REPAIR_V2.json"
ORDER_RECEIPT=ROOT/"canonical/verification/TERMINAL_DISTRIBUTION_AWARE_OUTCOME_ORDER_SPRITE_VERIFICATION_20261006_V1.json"

class UtilityQuotientControlV2Tests(unittest.TestCase):
    def setUp(self):
        self.d=json.loads(CONTROL.read_text())
        self.r=json.loads(ORDER_RECEIPT.read_text())
    def test_ordering_schema_is_exactly_verified(self):
        o=self.d["ordering_schema"]
        self.assertEqual(o["verification_git_blob_sha"],"a50dcf132d33e2d8f306ea18608ec2852b95b65a")
        self.assertIn("PASS__9_OF_9",self.r["status"])
        self.assertIn("PROVED_AS_ORDER_SCHEMA",o["status"])
        self.assertIn("DOES_NOT_PROVE",o["boundary"])
    def test_next_unresolved_is_target_completeness(self):
        s=self.d["successor_claim"]
        self.assertEqual(s["first_unresolved_lemma"],"TARGET_UTILITY_QUOTIENT_COMPLETENESS")
        rows={x["id"]:x["status"] for x in s["required_lemmas"]}
        self.assertIn("PROVED_SCHEMA",rows["UTILITY_AND_EQUAL_OR_BETTER_ORDERING_WELL_FORMED"])
        self.assertEqual(rows["TARGET_UTILITY_QUOTIENT_COMPLETENESS"],"ACTIVE_FIRST_UNRESOLVED")
    def test_current_30_are_witnesses_not_deleted(self):
        s=self.d["scheduler_effect"]
        self.assertIn("EVIDENCE_WITNESSES",s["current_30_truth_obligations_role"])
        self.assertIn("NO_CLAIM_ANY_OF_THE_30_CURRENT_TRUTH_WITNESSES_IS_BULK_DELETED",self.d["hard_nonclaims"])
    def test_no_credit_or_external_reality(self):
        a=self.d["accounting"]
        self.assertEqual(a["incremental_spend_usd"],0)
        self.assertEqual(a["fresh_reality_units_consumed"],0)
        for k,v in a.items():
            if k.endswith("_credit_delta"): self.assertEqual(v,0)
    def test_completeness_mission_is_counterexample_driven(self):
        t=self.d["target_quotient_completeness_mission"]["tournament"]
        self.assertIn("RUN_TARGET_OMISSION_COUNTEREXAMPLE_SEARCH",t)
        self.assertIn("RUN_NONSEPARABLE_CONDITION_AND_COMPOSITION_COUNTEREXAMPLE_SEARCH",t)
        self.assertIn("ADD_OR_SPLIT_ONLY_THE_MINIMUM_DISCRIMINATOR_EXPOSED_BY_A_CONSTRUCTIVE_COUNTEREXAMPLE",t)

if __name__=="__main__": unittest.main(verbosity=2)
