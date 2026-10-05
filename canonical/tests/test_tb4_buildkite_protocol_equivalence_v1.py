import copy, json, unittest
from pathlib import Path
from canonical.runtime.tb4_buildkite_protocol_equivalence_v1 import REQUIRED,evaluate,current_runtime_receipt_projection

ROOT=Path(__file__).resolve().parents[2]
SPEC=json.loads((ROOT/"canonical/governance/TB4_BUILDKITE_PROTOCOL_EQUIVALENCE_FALSIFICATION_20261006_V1.json").read_text())
BK=json.loads((ROOT/"canonical/verification/BUILDKITE_ZERO_CASE_RUNTIME_RECEIPT_20261006_V1.json").read_text())

class Tests(unittest.TestCase):
    def test_current_runtime_receipt_fails_closed_on_all_protocol_obligations(self):
        out=evaluate(SPEC,current_runtime_receipt_projection(BK))
        self.assertFalse(out["pass"])
        self.assertEqual(out["missing_protocol_obligations"],list(REQUIRED))
        self.assertFalse(out["anthropic_release_target_harness_relation_bound"])
        self.assertEqual(out["terminal_credit_delta"],0)

    def test_complete_zero_case_protocol_receipt_passes_only_public_harbor_carrier_gate(self):
        r={"target_predicate":"CODING_TB4_GE_66_4","provider":"Buildkite","frozen_dataset_commit":"452bf305c6daa62fc59061d22133a7cbc7c1572e","protocol_probe":{k:True for k in REQUIRED},"terminal_cases_consumed":0,"incremental_spend_usd":0}
        out=evaluate(SPEC,r)
        self.assertTrue(out["pass"])
        self.assertTrue(out["public_harbor_carrier_protocol_equivalence_bound"])
        self.assertFalse(out["anthropic_release_target_harness_relation_bound"])
        self.assertEqual(out["terminal_credit_delta"],0)

    def test_one_missing_obligation_fails_closed(self):
        r={"target_predicate":"CODING_TB4_GE_66_4","provider":"Buildkite","frozen_dataset_commit":"452bf305c6daa62fc59061d22133a7cbc7c1572e","protocol_probe":{k:True for k in REQUIRED},"terminal_cases_consumed":0,"incremental_spend_usd":0}
        r["protocol_probe"]["P4_VERIFIER_NO_NETWORK_BASELINE"]=False
        out=evaluate(SPEC,r)
        self.assertFalse(out["pass"])
        self.assertIn("P4_VERIFIER_NO_NETWORK_BASELINE",out["missing_protocol_obligations"])

    def test_stale_dataset_binding_fails(self):
        r={"target_predicate":"CODING_TB4_GE_66_4","provider":"Buildkite","frozen_dataset_commit":"wrong","protocol_probe":{k:True for k in REQUIRED},"terminal_cases_consumed":0,"incremental_spend_usd":0}
        self.assertIn("FROZEN_DATASET_NOT_EXACTLY_BOUND",evaluate(SPEC,r)["errors"])

    def test_terminal_case_or_spend_invalidates_probe(self):
        r={"target_predicate":"CODING_TB4_GE_66_4","provider":"Buildkite","frozen_dataset_commit":"452bf305c6daa62fc59061d22133a7cbc7c1572e","protocol_probe":{k:True for k in REQUIRED},"terminal_cases_consumed":1,"incremental_spend_usd":0}
        self.assertIn("TERMINAL_CASE_CONSUMPTION_NONZERO",evaluate(SPEC,r)["errors"])
        r["terminal_cases_consumed"]=0;r["incremental_spend_usd"]=0.01
        self.assertIn("INCREMENTAL_SPEND_NONZERO",evaluate(SPEC,r)["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
