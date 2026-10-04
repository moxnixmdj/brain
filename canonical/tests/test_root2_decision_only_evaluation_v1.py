from __future__ import annotations
import unittest

from canonical.runtime.root2_decision_only_evaluation_v1 import (
    INPUT_SCHEMA,
    compile_decision_only_evaluation,
)
from canonical.runtime.blind_threshold_receipt_v1 import INPUT_SCHEMA as BLIND_SCHEMA
from canonical.runtime.threshold_proof_dag_v1 import INPUT_SCHEMA as DAG_SCHEMA

SHA_A="a"*40
SHA_B="b"*40
SHA_C="c"*40
SHA_D="d"*40

def ref(path, sha=SHA_A):
    return {"path":path,"git_blob_sha":sha}

def ident():
    return {"commit_sha":SHA_B,"tree_sha":SHA_C}

def blind_doc(verdict="PASS"):
    target={
        "predicate_id":"CODING_CURSORBENCH_GE_57_8",
        "benchmark_id":"CURSORBENCH_4_0_FROZEN",
        "metric_kind":"ADDITIVE_THRESHOLD",
        "operator":"GE",
        "threshold":"57.8",
        "unit":"PERCENT",
        "candidate_identity":ident(),
        "harness_receipt":ref("harness.json",SHA_D),
    }
    receipt={
        "receipt_class":"OWNER_BLIND_SCORE_THRESHOLD_RECEIPT",
        "predicate_id":target["predicate_id"],
        "benchmark_id":target["benchmark_id"],
        "operator":"GE",
        "threshold":"57.8",
        "unit":"PERCENT",
        "candidate_identity":ident(),
        "harness_receipt":ref("harness.json",SHA_D),
        "source_artifact":ref("owner.json",SHA_A),
        "source_verification_receipt":ref("verify.json",SHA_B),
        "issuer":"owner",
        "evaluation_run_id":"run-1",
        "source_authenticity_verified":True,
        "exact_frozen_protocol_verified":True,
        "candidate_identity_verified":True,
        "harness_identity_verified":True,
        "threshold_identity_verified":True,
        "independent_or_objective":True,
        "metric_semantics":"OFFICIAL_FIXED_BAR_THRESHOLD_VERDICT",
        "verdict":verdict,
        "exact_score_disclosed":False,
    }
    return {"schema":BLIND_SCHEMA,"frozen_target":target,"blind_receipt":receipt}

def dag_doc(lower=50, upper=100, actions=None):
    return {
        "schema":DAG_SCHEMA,
        "target":{
            "id":"CODING_TB4_GE_66_4",
            "metric_kind":"ADDITIVE_THRESHOLD",
            "receipt":ref("tb4-target.json"),
            "total_mass":100,
            "threshold_mass":66.4,
            "current_lower_mass":lower,
            "current_upper_mass":upper,
        },
        "allow_fresh_reality":False,
        "actions":actions or [],
    }

def action(aid, sec, gain=0, loss=0, zr=True):
    return {
        "action_id":aid,
        "critical_path_seconds":sec,
        "zero_reality":zr,
        "coverage_ids":[aid],
        "depends_on":[],
        "lower_gain_if_pass":gain,
        "upper_loss_if_fail":loss,
        "margin_gain_if_pass":0,
    }

class DecisionOnlyEvaluationTests(unittest.TestCase):
    def test_blind_one_bit_receipt_preempts_full_score(self):
        d={
            "schema":INPUT_SCHEMA,
            "predicate_id":"CODING_CURSORBENCH_GE_57_8",
            "blind_threshold_doc":blind_doc("PASS"),
            "threshold_dag_doc":dag_doc(),
        }
        o=compile_decision_only_evaluation(d)
        self.assertEqual(o["status"],"DECIDED__AUTHENTICATED_ONE_BIT_THRESHOLD_CERTIFICATE")
        self.assertEqual(o["verdict"],"PASS")
        self.assertFalse(o["exact_score_required"])
        self.assertFalse(o["dataset_disclosure_required"])
        self.assertEqual(o["decision_route"],"BLIND_THRESHOLD_RECEIPT")

    def test_blind_fail_is_still_a_terminal_decision(self):
        d={"schema":INPUT_SCHEMA,"predicate_id":"CODING_CURSORBENCH_GE_57_8","blind_threshold_doc":blind_doc("FAIL")}
        o=compile_decision_only_evaluation(d)
        self.assertEqual(o["verdict"],"FAIL")
        self.assertEqual(o["decision_route"],"BLIND_THRESHOLD_RECEIPT")

    def test_existing_lower_bound_closes_without_full_benchmark(self):
        d={"schema":INPUT_SCHEMA,"predicate_id":"CODING_TB4_GE_66_4","threshold_dag_doc":dag_doc(lower=70,upper=90)}
        o=compile_decision_only_evaluation(d)
        self.assertEqual(o["status"],"DECIDED__THRESHOLD_CERTIFICATE")
        self.assertEqual(o["verdict"],"PASS")
        self.assertFalse(o["full_benchmark_required"])

    def test_open_case_returns_minimum_zero_reality_cut(self):
        actions=[action("fast-a",2,gain=10),action("fast-b",3,gain=7)]
        d={"schema":INPUT_SCHEMA,"predicate_id":"CODING_TB4_GE_66_4","threshold_dag_doc":dag_doc(lower=50,upper=100,actions=actions)}
        o=compile_decision_only_evaluation(d)
        self.assertEqual(o["status"],"OPEN__MINIMUM_CERTIFICATE_CUT_COMPILED")
        self.assertEqual(o["verdict"],"OPEN")
        self.assertEqual(o["minimum_pass_cut"]["actions"],["fast-a","fast-b"])
        self.assertFalse(o["full_benchmark_required"])

    def test_fresh_reality_action_is_not_scheduled_without_authority(self):
        actions=[action("fresh",1,gain=20,zr=False)]
        d={"schema":INPUT_SCHEMA,"predicate_id":"CODING_TB4_GE_66_4","threshold_dag_doc":dag_doc(lower=50,upper=100,actions=actions)}
        o=compile_decision_only_evaluation(d)
        self.assertEqual(o["status"],"OPEN__MINIMUM_CERTIFICATE_CUT_COMPILED")
        self.assertIn("fresh",o["blocked_fresh_reality_actions"])
        self.assertIsNone(o["minimum_pass_cut"])

    def test_predicate_drift_in_blind_receipt_fails_that_route_and_does_not_create_credit(self):
        b=blind_doc()
        b["frozen_target"]["predicate_id"]="OTHER"
        b["blind_receipt"]["predicate_id"]="OTHER"
        d={"schema":INPUT_SCHEMA,"predicate_id":"CODING_CURSORBENCH_GE_57_8","blind_threshold_doc":b}
        o=compile_decision_only_evaluation(d)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertEqual(o["acceptance_credit_delta"],0)
        self.assertFalse(o["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
