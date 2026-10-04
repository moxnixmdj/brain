from __future__ import annotations
import unittest
from canonical.runtime.blind_threshold_receipt_v1 import (
    INPUT_SCHEMA,
    compile_blind_threshold_receipt,
)

SHA_A="a"*40
SHA_B="b"*40
SHA_C="c"*40
SHA_D="d"*40

def ref(path, sha=SHA_A):
    return {"path":path,"git_blob_sha":sha}

def identity(commit=SHA_B, tree=SHA_C):
    return {"commit_sha":commit,"tree_sha":tree}

def doc(kind="ADDITIVE_THRESHOLD", threshold="57.8", semantics="OFFICIAL_FIXED_BAR_THRESHOLD_VERDICT", verdict="PASS"):
    target={
        "predicate_id":"CODING_CURSORBENCH_GE_57_8",
        "benchmark_id":"CURSORBENCH_4_0_FROZEN",
        "metric_kind":kind,
        "operator":"GE",
        "threshold":threshold,
        "unit":"PERCENT",
        "candidate_identity":identity(),
        "harness_receipt":ref("harness.json",SHA_D),
    }
    receipt={
        "receipt_class":"OWNER_BLIND_SCORE_THRESHOLD_RECEIPT",
        "predicate_id":target["predicate_id"],
        "benchmark_id":target["benchmark_id"],
        "operator":"GE",
        "threshold":threshold,
        "unit":"PERCENT",
        "candidate_identity":identity(),
        "harness_receipt":ref("harness.json",SHA_D),
        "source_artifact":ref("owner/result.json",SHA_A),
        "source_verification_receipt":ref("verification/result.json",SHA_B),
        "issuer":"benchmark-owner",
        "evaluation_run_id":"run-123",
        "source_authenticity_verified":True,
        "exact_frozen_protocol_verified":True,
        "candidate_identity_verified":True,
        "harness_identity_verified":True,
        "threshold_identity_verified":True,
        "independent_or_objective":True,
        "metric_semantics":semantics,
        "verdict":verdict,
        "exact_score_disclosed":False,
    }
    return {"schema":INPUT_SCHEMA,"frozen_target":target,"blind_receipt":receipt}

class BlindThresholdReceiptTests(unittest.TestCase):
    def test_blind_fixed_bar_pass_needs_no_score(self):
        o=compile_blind_threshold_receipt(doc())
        self.assertEqual(o["status"],"PASS__BLIND_THRESHOLD_CERTIFICATE_STRUCTURALLY_ELIGIBLE__ZERO_CREDIT")
        self.assertEqual(o["verdict"],"PASS")
        self.assertFalse(o["exact_score_required"])
        self.assertEqual(o["acceptance_credit_delta"],0)

    def test_fail_verdict_is_eligible_but_zero_credit(self):
        o=compile_blind_threshold_receipt(doc(verdict="FAIL"))
        self.assertEqual(o["verdict"],"FAIL")
        self.assertEqual(o["acceptance_credit_delta"],0)
        self.assertFalse(o["promotion_authority"])

    def test_relative_rating_requires_direct_relative_semantics(self):
        d=doc(kind="RELATIVE_RATING_THRESHOLD",threshold="1846",semantics="OFFICIAL_RELATIVE_RATING_THRESHOLD_VERDICT")
        d["frozen_target"]["unit"]="ELO"
        d["blind_receipt"]["unit"]="ELO"
        d["frozen_target"]["predicate_id"]="PROWORK_GDPVAL_GE_1846"
        d["blind_receipt"]["predicate_id"]="PROWORK_GDPVAL_GE_1846"
        o=compile_blind_threshold_receipt(d)
        self.assertEqual(o["verdict"],"PASS")

    def test_relative_rating_rejects_absolute_behavioral_semantics(self):
        d=doc(kind="RELATIVE_RATING_THRESHOLD",threshold="1846",semantics="OFFICIAL_FIXED_BAR_THRESHOLD_VERDICT")
        d["frozen_target"]["unit"]="ELO"; d["blind_receipt"]["unit"]="ELO"
        o=compile_blind_threshold_receipt(d)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertIn("RELATIVE_RATING",o["errors"][0])

    def test_threshold_drift_fails_closed(self):
        d=doc(); d["blind_receipt"]["threshold"]="57.7"
        self.assertEqual(compile_blind_threshold_receipt(d)["status"],"FAIL_CLOSED")

    def test_candidate_drift_fails_closed(self):
        d=doc(); d["blind_receipt"]["candidate_identity"]["commit_sha"]="e"*40
        self.assertEqual(compile_blind_threshold_receipt(d)["status"],"FAIL_CLOSED")

    def test_harness_drift_fails_closed(self):
        d=doc(); d["blind_receipt"]["harness_receipt"]["git_blob_sha"]="e"*40
        self.assertEqual(compile_blind_threshold_receipt(d)["status"],"FAIL_CLOSED")

    def test_missing_independent_source_verification_fails_closed(self):
        d=doc(); d["blind_receipt"].pop("source_verification_receipt")
        self.assertEqual(compile_blind_threshold_receipt(d)["status"],"FAIL_CLOSED")

    def test_missing_authenticity_verification_fails_closed(self):
        d=doc(); d["blind_receipt"]["source_authenticity_verified"]=False
        self.assertEqual(compile_blind_threshold_receipt(d)["status"],"FAIL_CLOSED")

    def test_disclosed_score_must_match_verdict(self):
        d=doc(verdict="PASS")
        d["blind_receipt"]["exact_score_disclosed"]=True
        d["blind_receipt"]["exact_score"]="50"
        o=compile_blind_threshold_receipt(d)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertIn("INCONSISTENT",o["errors"][0])

    def test_undisclosed_score_cannot_leak_into_receipt(self):
        d=doc(); d["blind_receipt"]["exact_score"]="60"
        self.assertEqual(compile_blind_threshold_receipt(d)["status"],"FAIL_CLOSED")

    def test_matched_noninferiority_not_collapsed_into_fixed_bar_receipt(self):
        d=doc(kind="MATCHED_NONINFERIORITY")
        self.assertEqual(compile_blind_threshold_receipt(d)["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main(verbosity=2)
