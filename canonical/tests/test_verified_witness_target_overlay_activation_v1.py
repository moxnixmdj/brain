import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    def test_overlay_activation_and_scope_safe_v2_are_live_without_credit(self):
        activation=load("canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_ACTIVATION_V1.json")
        receipt=load("canonical/verification/VERIFIED_WITNESS_TARGET_OVERLAYS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        optimizer=load("canonical/governance/EXECUTION_FIRST_SELF_PROVING_OPTIMIZER_V1.json")
        authority=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")

        self.assertTrue(activation["status"].startswith("ACTIVE_INDEPENDENT_PASS"),activation)
        self.assertTrue(receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),receipt)
        self.assertEqual(
            optimizer["proof_compression_kernels"]["protocol_implication_scope_algebra"],
            "canonical/runtime/protocol_implication_scope_algebra_v2.py")
        self.assertNotEqual(
            optimizer["proof_compression_kernels"]["protocol_implication_scope_algebra"],
            "canonical/runtime/protocol_implication_scope_algebra_v1.py")
        self.assertEqual(
            optimizer["proof_compression_kernels"]["verified_witness_target_overlay_activation"],
            "canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_ACTIVATION_V1.json")
        self.assertEqual(
            optimizer["verified_semantic_overlay_compilation"]["runtime"],
            "canonical/runtime/protocol_implication_overlay_batch_reducer_v1.py")

        source=authority["sources"]["verified_witness_target_overlay_compilation"]
        self.assertTrue(source["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),source)
        self.assertEqual(authority["truth"]["opus55_acceptance"],"2/19_PASS__17/19_OPEN")
        self.assertFalse(authority["truth"]["achieved"])
        self.assertEqual(activation["current_projection"]["improved_target_count"],1)
        self.assertEqual(activation["current_projection"]["closed_target_count"],0)
        self.assertEqual(activation["capability_credit_delta"],0)
        self.assertEqual(activation["family_credit_delta"],0)
        self.assertFalse(activation["execution_authority"])
        self.assertFalse(activation["promotion_authority"])

if __name__=="__main__": unittest.main(verbosity=2)
