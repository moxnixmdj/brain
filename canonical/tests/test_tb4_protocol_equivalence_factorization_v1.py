import unittest
from canonical.runtime.tb4_protocol_equivalence_factorization_v1 import evaluate

SHA="1"*40

def receipt():
    return {"compared_to_frozen_tb4_carrier_minimum":{"runtime_resource_and_container_subpremises":"PASS"}}

def base():
    return {
        "schema":"PROJECT_BRAIN_TB4_PROTOCOL_EQUIVALENCE_FACTORIZATION_20261006_V1",
        "target_predicate":"CODING_TB4_GE_66_4",
        "carrier_invariance":{
            "status":"OPEN",
            "same_dataset_digest":False,
            "same_task_and_verifier_images":False,
            "same_harbor_execution_semantics":False,
            "same_resource_limits":False,
            "same_network_semantics":False,
            "same_retry_timeout_trial_semantics":False,
            "receipts":[]
        },
        "target_harness_identity":{
            "status":"OPEN",
            "evidence_class":"PUBLIC_LEADERBOARD_CALIBRATION",
            "same_agent_runtime_and_version":False,
            "same_model_effort":False,
            "same_fallback_policy":False,
            "same_evaluator":False,
            "same_trial_count":False,
            "fallback_policy_relation":"UNKNOWN",
            "receipts":[]
        },
    }

def prove_carrier(s):
    b=s["carrier_invariance"]
    b["status"]="PROVED_EXACT"
    b["receipts"]=[{"path":"carrier.json","git_blob_sha":SHA}]
    for k in ("same_dataset_digest","same_task_and_verifier_images","same_harbor_execution_semantics","same_resource_limits","same_network_semantics","same_retry_timeout_trial_semantics"):
        b[k]=True

def prove_target(s):
    b=s["target_harness_identity"]
    b["status"]="PROVED_EXACT"
    b["evidence_class"]="EXACT_FROZEN_TARGET_HARNESS"
    b["receipts"]=[{"path":"target.json","git_blob_sha":SHA}]
    for k in ("same_agent_runtime_and_version","same_model_effort","same_fallback_policy","same_evaluator","same_trial_count"):
        b[k]=True
    b["fallback_policy_relation"]="EXACT_MATCH"

class Tests(unittest.TestCase):
    def test_current_resource_only_fails_closed(self):
        out=evaluate(base(),receipt())
        self.assertFalse(out["pass"])
        self.assertTrue(out["carrier_runtime_subpremises_bound"])
        self.assertIn("CARRIER_INVARIANCE_CERTIFICATE",out["missing"])
        self.assertIn("EXACT_FROZEN_TARGET_HARNESS_IDENTITY",out["missing"])

    def test_carrier_only_is_not_protocol_equivalence(self):
        s=base(); prove_carrier(s)
        self.assertFalse(evaluate(s,receipt())["protocol_equivalence_bound"])

    def test_target_only_is_not_protocol_equivalence(self):
        s=base(); prove_target(s)
        self.assertFalse(evaluate(s,receipt())["protocol_equivalence_bound"])

    def test_public_calibration_never_substitutes_exact_target_identity(self):
        s=base(); prove_carrier(s); prove_target(s)
        s["target_harness_identity"]["evidence_class"]="PUBLIC_LEADERBOARD_CALIBRATION"
        self.assertFalse(evaluate(s,receipt())["protocol_equivalence_bound"])

    def test_fallback_mismatch_fails_closed(self):
        s=base(); prove_carrier(s); prove_target(s)
        s["target_harness_identity"]["fallback_policy_relation"]="MISMATCH"
        out=evaluate(s,receipt())
        self.assertFalse(out["pass"])
        self.assertIn("FALLBACK_POLICY_NOT_EXACT_MATCH",out["errors"])

    def test_full_exact_binding_passes(self):
        s=base(); prove_carrier(s); prove_target(s)
        out=evaluate(s,receipt())
        self.assertTrue(out["pass"])
        self.assertTrue(out["protocol_equivalence_bound"])
        self.assertEqual(out["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
