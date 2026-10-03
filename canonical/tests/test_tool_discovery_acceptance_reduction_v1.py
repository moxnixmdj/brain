from __future__ import annotations
import copy
import unittest

from canonical.runtime.tool_discovery_acceptance_reduction_v1 import (
    TARGET,FAMILY,load,reduce,verify
)

class ToolDiscoveryAcceptanceReductionV1Tests(unittest.TestCase):
    def inputs(self):
        return dict(
          scope_receipt=load("canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
          bindings=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
          protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
          firewall=load("canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"),
          registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        )

    def test_live_inputs_produce_zero_credit_closure_candidate(self):
        out=verify()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["family_candidate_state"],"PASS_3_OF_3")
        self.assertEqual(out["candidate_claim"]["predicate_id"],TARGET)
        self.assertEqual(out["candidate_claim"]["state"],"PROVED")
        self.assertTrue(out["candidate_claim"]["scope_complete"])
        self.assertTrue(out["candidate_claim"]["objective_ceiling"])
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertFalse(out["source_180_of_180_load_bearing"])
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

    def test_failed_independent_receipt_fails_closed(self):
        x=self.inputs()
        x["scope_receipt"]=copy.deepcopy(x["scope_receipt"])
        x["scope_receipt"]["independent_runner"]["conclusion"]="failure"
        self.assertFalse(reduce(**x)["pass"])

    def test_empirical_generalization_reintroduced_fails_closed(self):
        x=self.inputs()
        x["scope_receipt"]=copy.deepcopy(x["scope_receipt"])
        x["scope_receipt"]["verified"]["uses_empirical_generalization"]=True
        self.assertFalse(reduce(**x)["pass"])

    def test_wrong_target_fails_closed(self):
        x=self.inputs()
        x["scope_receipt"]=copy.deepcopy(x["scope_receipt"])
        x["scope_receipt"]["verified"]["target_predicate"]="OTHER"
        self.assertFalse(reduce(**x)["pass"])

    def test_missing_existing_learning_atom_fails_closed(self):
        for pid in (
          "TOOL_LEARNING_SECOND_TASK_TRANSFER",
          "TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION",
        ):
            x=self.inputs()
            x["bindings"]=copy.deepcopy(x["bindings"])
            row=next(r for r in x["bindings"]["claims"] if r["predicate_id"]==pid)
            row["state"]="OPEN"
            self.assertFalse(reduce(**x)["pass"],pid)

    def test_scope_firewall_must_explicitly_allow_universal_formal_proof(self):
        x=self.inputs()
        x["firewall"]=copy.deepcopy(x["firewall"])
        x["firewall"]["admissible_absolute_dominance_bases"].remove(
          "UNIVERSAL_FORMAL_SCOPE_PROOF"
        )
        self.assertFalse(reduce(**x)["pass"])

    def test_current_target_must_be_exact_scope_blocker(self):
        x=self.inputs()
        x["bindings"]=copy.deepcopy(x["bindings"])
        row=next(r for r in x["bindings"]["claims"] if r["predicate_id"]==TARGET)
        row["blocker"]="SOMETHING_ELSE"
        self.assertFalse(reduce(**x)["pass"])


if __name__=="__main__":
    unittest.main(verbosity=2)
