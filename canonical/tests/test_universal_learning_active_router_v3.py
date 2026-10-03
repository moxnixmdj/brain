from __future__ import annotations
import unittest
from canonical.runtime import universal_learning_active_router_v3 as r

R={"receipt_id":"r","independent_verified":True,"exact_byte_bound":True,"conclusion":"success"}
M={"receipt_id":"m","independent_verified":True,"exact_byte_bound":True,"conclusion":"success"}

class Tests(unittest.TestCase):
    def test_v1_v2_verified_route_remains_authoritative(self):
        out=r.route(goal="known",verified_coverage=True,target_requirements={"x"},verified_facts={"x"},structural_mappings=[],hypotheses=[],probes=[],actions=[])
        self.assertEqual(out["route"],"USE_VERIFIED_CAPABILITY")
        self.assertTrue(out["trusted_execution_authorized"])

    def test_verified_structural_transfer_never_becomes_trusted_target_knowledge(self):
        out=r.route(goal="transfer",verified_coverage=False,target_requirements={"x"},verified_facts=set(),structural_mappings=[{"source_primitive_id":"a","target_requirement_id":"x","mapping_basis":"CAUSAL_INVARIANT","label_only":False,"source_verification_receipt":R,"mapping_verification_receipt":M}],hypotheses=[],probes=[],actions=[])
        self.assertEqual(out["route"],"LEARN_WITH_STRUCTURAL_TRANSFER")
        self.assertEqual(out["structural_transfer"]["covered"],["x"])
        self.assertFalse(out["trusted_execution_authorized"])
        self.assertEqual(out["next_requirement"],"VERIFY_TRANSFERRED_SOLUTION_IN_TARGET_DOMAIN")

    def test_action_disagreement_uses_exact_minimum_discriminator_before_generic_action(self):
        out=r.route(goal="learn",verified_coverage=False,target_requirements={"x"},verified_facts=set(),structural_mappings=[],hypotheses=[{"id":"h1","plausible":True,"best_action":"A"},{"id":"h2","plausible":True,"best_action":"B"}],probes=[{"id":"p","safe":True,"time":1,"cost":0,"risk":0,"outcomes":{"h1":"a","h2":"b"}}],actions=[{"id":"generic","decision_gain":99,"transfer_gain":99,"proof_gain":99,"time":1,"cost":0,"risk":0}])
        self.assertEqual(out["route"],"LEARN_WITH_MINIMUM_DISCRIMINATOR")
        self.assertEqual(out["probe_ids"],["p"])

    def test_if_no_model_discriminator_generic_learning_can_still_gather_new_information(self):
        out=r.route(goal="learn",verified_coverage=False,target_requirements={"x"},verified_facts=set(),structural_mappings=[],hypotheses=[{"id":"h1","plausible":True,"best_action":"A"},{"id":"h2","plausible":True,"best_action":"B"}],probes=[],actions=[{"id":"search","decision_gain":1,"transfer_gain":0,"proof_gain":0,"time":1,"cost":0,"risk":0}])
        self.assertEqual(out["route"],"LEARN_GENERAL_INFORMATION")
        self.assertIsNotNone(out["next_action"])

    def test_nonidentifiable_without_information_route_abstains(self):
        out=r.route(goal="learn",verified_coverage=False,target_requirements={"x"},verified_facts=set(),structural_mappings=[],hypotheses=[{"id":"h1","plausible":True,"best_action":"A"},{"id":"h2","plausible":True,"best_action":"B"}],probes=[],actions=[])
        self.assertEqual(out["route"],"ABSTAIN_OR_REQUEST_DISCRIMINATOR")
        self.assertFalse(out["trusted_execution_authorized"])

    def test_model_consensus_remains_unverified(self):
        out=r.route(goal="learn",verified_coverage=False,target_requirements={"x"},verified_facts=set(),structural_mappings=[],hypotheses=[{"id":"h1","plausible":True,"best_action":"A"},{"id":"h2","plausible":True,"best_action":"A"}],probes=[],actions=[])
        self.assertEqual(out["route"],"DECISION_SUFFICIENT_UNVERIFIED_MODEL")
        self.assertEqual(out["recommended_action"],"A")
        self.assertFalse(out["trusted_execution_authorized"])

    def test_zero_credit_all_paths(self):
        out=r.route(goal="known",verified_coverage=True,target_requirements={"x"},verified_facts={"x"},structural_mappings=[],hypotheses=[],probes=[],actions=[])
        for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
            self.assertEqual(out[k],0)
        self.assertFalse(out["promotion_authorized"])

if __name__=='__main__': unittest.main(verbosity=2)
