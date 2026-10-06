from __future__ import annotations
import json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ORDER=ROOT/"canonical/governance/TERMINAL_DISTRIBUTION_AWARE_OUTCOME_ORDER_V1.json"
PARENT=ROOT/"canonical/governance/TERMINAL_UTILITY_QUOTIENT_CONTROL_REPAIR_V1.json"

class DistributionOutcomeOrderGovernanceTests(unittest.TestCase):
    def test_exact_parent_and_lemma_binding(self):
        order=json.loads(ORDER.read_text())
        parent=json.loads(PARENT.read_text())
        p=order["parent_claim"]
        self.assertEqual(p["source_git_blob_sha"],"a7db520274f2a969056ea2e251401d64a4b0ff7d")
        self.assertEqual(p["lemma"],"UTILITY_AND_EQUAL_OR_BETTER_ORDERING_WELL_FORMED")
        self.assertIn(p["lemma"],parent["successor_claim"]["required_lemmas"])
        self.assertEqual(parent["successor_claim"]["first_unresolved_lemma"],p["lemma"])

    def test_order_is_distribution_aware_and_noncompensable(self):
        d=json.loads(ORDER.read_text())
        definition=d["definition"]
        self.assertIn("EXPECTATION_PB_u_GE_EXPECTATION_PO_u",definition["weak_dominance"])
        self.assertIn("RISK_PB_h_LE_RISK_PO_h",definition["weak_dominance"])
        sem=d["distribution_semantics"]
        self.assertIn("DOES_NOT_ESTABLISH_EQUALITY",sem["support_only_forbidden"])
        self.assertIn("CANNOT_OFFSET",sem["hard_constraint_noncompensation"])

    def test_next_lemma_is_completeness_not_hidden_credit(self):
        d=json.loads(ORDER.read_text())
        sep=d["separation_of_lemmas"]
        self.assertEqual(sep["next_lemma_if_independently_verified"],"TARGET_UTILITY_QUOTIENT_COMPLETENESS")
        self.assertIn("THE_DECLARED_EVALUATOR_SET_IS_COMPLETE_FOR_ALL_USEFUL_OPUS55_CAPABILITIES",sep["not_proved_here"])
        for k,v in d["accounting"].items():
            if k.endswith("_credit_delta"):
                self.assertEqual(v,0)

if __name__=="__main__":
    unittest.main(verbosity=2)
