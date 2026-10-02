from __future__ import annotations
import copy, unittest
from canonical.runtime.differential_dominance_compiler_v1 import evaluate

def base():
    return {
        "predicate_id":"MATCHED_TEST",
        "scope":{
            "scope_id":"FROZEN_SCOPE",
            "frozen":True,
            "complete":True,
            "finite":True,
            "independently_verified":True,
            "shared_success_criterion":True,
            "shared_authority_boundary":True,
            "contamination_clean":True,
            "scope_receipt":"receipt://scope",
            "criterion_receipt":"receipt://criterion",
            "case_ids":["A","B"],
        },
        "cases":[
            {"case_id":"A","brain":{"status":"SUCCESS","verified":True,"receipt":"receipt://brain-a"}},
            {"case_id":"B","brain":{"status":"SUCCESS","verified":True,"receipt":"receipt://brain-b"}},
        ],
    }

class Tests(unittest.TestCase):
    def test_all_verified_brain_successes_yield_candidate(self):
        out=evaluate(base())
        self.assertEqual(out["status"],"CANDIDATE_DIFFERENTIAL_DOMINANCE_READY__INDEPENDENT_VERIFICATION_REQUIRED")
        self.assertTrue(out["differential_dominance_proved"])
        self.assertFalse(out["promotion_authority"])

    def test_verified_impossibility_can_close_brain_failure_case(self):
        d=base()
        d["cases"][1]={
            "case_id":"B",
            "brain":{"status":"FAILURE","verified":True,"receipt":"receipt://brain-b-fail"},
            "comparator_success_exclusion":{
                "comparator_success_impossible":True,
                "verified":True,
                "scope_complete_for_case":True,
                "proof_kind":"FORMAL_PROOF",
                "receipt":"receipt://impossible-b",
            },
        }
        out=evaluate(d)
        self.assertTrue(out["differential_dominance_proved"])

    def test_verified_comparator_failure_can_close_unknown_brain_case(self):
        d=base()
        d["cases"][1]={
            "case_id":"B",
            "brain":{"status":"UNKNOWN","verified":False},
            "comparator":{"status":"FAILURE","verified":True,"receipt":"receipt://comp-b-fail"},
        }
        out=evaluate(d)
        self.assertTrue(out["differential_dominance_proved"])

    def test_unresolved_case_remains_residual(self):
        d=base()
        d["cases"][1]={"case_id":"B","brain":{"status":"FAILURE","verified":True,"receipt":"receipt://brain-b-fail"}}
        out=evaluate(d)
        self.assertEqual(out["status"],"DIFFERENTIAL_RESIDUAL_OPEN")
        self.assertEqual(out["residual_case_ids"],["B"])

    def test_verified_comparator_win_brain_loss_is_counterexample(self):
        d=base()
        d["cases"][1]={
            "case_id":"B",
            "brain":{"status":"FAILURE","verified":True,"receipt":"receipt://brain-b-fail"},
            "comparator":{"status":"SUCCESS","verified":True,"receipt":"receipt://comp-b-pass"},
        }
        out=evaluate(d)
        self.assertEqual(out["status"],"VERIFIED_DIFFERENTIAL_COUNTEREXAMPLE")
        self.assertFalse(out["differential_dominance_proved"])

    def test_incomplete_scope_fails_closed(self):
        d=base(); d["scope"]["complete"]=False
        self.assertEqual(evaluate(d)["status"],"FAIL_CLOSED")

    def test_case_universe_mismatch_fails_closed(self):
        d=base(); d["scope"]["case_ids"].append("C")
        out=evaluate(d)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertTrue(any(x.startswith("MISSING_CASE_ROWS") for x in out["errors"]))

    def test_unverified_exclusion_never_becomes_proof(self):
        d=base()
        d["cases"][1]={
            "case_id":"B",
            "brain":{"status":"FAILURE","verified":True,"receipt":"receipt://brain-b-fail"},
            "comparator_success_exclusion":{
                "comparator_success_impossible":True,
                "verified":False,
                "scope_complete_for_case":True,
                "proof_kind":"FORMAL_PROOF",
                "receipt":"receipt://not-verified",
            },
        }
        self.assertEqual(evaluate(d)["status"],"DIFFERENTIAL_RESIDUAL_OPEN")

    def test_shared_success_criterion_is_mandatory(self):
        d=base(); d["scope"]["shared_success_criterion"]=False
        self.assertEqual(evaluate(d)["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main(verbosity=2)
