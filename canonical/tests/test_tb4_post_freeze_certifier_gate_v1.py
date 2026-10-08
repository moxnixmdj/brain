from __future__ import annotations
import copy
import unittest
from canonical.runtime.tb4_post_freeze_certifier_gate_v1 import evaluate, REQUIRED_TRUE, REQUIRED_FALSE

H="a"*64

def good():
    return {
        "schema":"PROJECT_BRAIN_TB4_POST_FREEZE_CERTIFIER_SPEC_V1",
        "task":"synthetic-tb4-task",
        "actor_config_sha256":H,
        "output_sha256":"b"*64,
        "certifier_identity":"independent-certifier-v1",
        "gate":{
            **{k:True for k in REQUIRED_TRUE},
            **{k:False for k in REQUIRED_FALSE},
        },
        "temporal_order":[
            "ACTOR_EXECUTION",
            "OUTPUT_HASH_COMMIT",
            "ACTOR_WRITE_CLOSE",
            "CERTIFIER_EVALUATOR_EXPOSURE",
            "PROOF_OBJECT_EMISSION",
        ],
        "channels":{
            "evaluator_to_actor":False,
            "certifier_to_actor_same_task":False,
            "certifier_to_frozen_output":False,
            "proof_to_actor_same_task":False,
        },
    }

class Tests(unittest.TestCase):
    def test_good_passes(self):
        v=evaluate(good())
        self.assertTrue(v.admissible)
        self.assertEqual(v.acceptance_credit_delta,0)
        self.assertFalse(v.execution_authority)
        self.assertFalse(v.promotion_authority)

    def test_each_true_gate_has_teeth(self):
        for k in REQUIRED_TRUE:
            with self.subTest(k=k):
                x=good(); x["gate"][k]=False
                self.assertFalse(evaluate(x).admissible)

    def test_each_false_gate_has_teeth(self):
        for k in REQUIRED_FALSE:
            with self.subTest(k=k):
                x=good(); x["gate"][k]=True
                self.assertFalse(evaluate(x).admissible)

    def test_evaluator_to_actor_leak_fails(self):
        x=good(); x["channels"]["evaluator_to_actor"]=True
        self.assertFalse(evaluate(x).admissible)

    def test_certifier_feedback_fails(self):
        x=good(); x["channels"]["certifier_to_actor_same_task"]=True
        self.assertFalse(evaluate(x).admissible)

    def test_certifier_mutation_fails(self):
        x=good(); x["channels"]["certifier_to_frozen_output"]=True
        self.assertFalse(evaluate(x).admissible)

    def test_proof_feedback_fails(self):
        x=good(); x["channels"]["proof_to_actor_same_task"]=True
        self.assertFalse(evaluate(x).admissible)

    def test_temporal_reordering_fails(self):
        x=good(); x["temporal_order"][2],x["temporal_order"][3]=x["temporal_order"][3],x["temporal_order"][2]
        self.assertFalse(evaluate(x).admissible)

    def test_invalid_hash_fails(self):
        x=good(); x["output_sha256"]="not-a-hash"
        self.assertFalse(evaluate(x).admissible)

if __name__=="__main__":
    unittest.main(verbosity=2)
