from __future__ import annotations
import unittest

from canonical.runtime.atomic_one_use_execution_claim_v1 import (
    INPUT_SCHEMA,
    execution_lease_digest,
    expected_claim_ref,
    verify_atomic_one_use_execution_claim,
)

A="a"*40
B="b"*40

def ref(path,sha):
    return {"path":path,"git_blob_sha":sha}

def lease():
    return {
        "activation":ref("activation.json",A),
        "candidate":ref("candidate.json",B),
        "scope":{
            "benchmark_id":"LIVEBENCH_IF_2026_06_25",
            "target_predicate":"LIVEBENCH_IF_GE_65_7",
            "execution_kind":"REPLAY_EXISTING_PREFIX",
            "scope_id":"V6_REPLAY72",
            "max_case_count":72,
            "new_case_exposure":False,
        },
    }

def doc(status=201):
    l=lease()
    digest=execution_lease_digest(l)
    claim={
        "lease_digest_sha256":digest,
        "claim_ref":expected_claim_ref(digest),
        "create_http_status":status,
        "reference_created":status==201,
        "response_ref":expected_claim_ref(digest) if status==201 else None,
        "response_object_sha":A if status==201 else None,
        "expected_target_sha":A,
        "claim_uniqueness_source":"ATOMIC_CREATE_RESPONSE",
        "claim_ref_absence_precheck_performed":False,
        "case_read_before_claim":False,
        "execution_started_before_claim":False,
        "evaluation_output_exists_before_claim":False,
    }
    return {"schema":INPUT_SCHEMA,"lease":l,"claim_receipt":claim}

class AtomicOneUseExecutionClaimTests(unittest.TestCase):
    def test_first_atomic_create_201_grants_exact_lease(self):
        o=verify_atomic_one_use_execution_claim(doc(201))
        self.assertTrue(o["execution_authority"])
        self.assertTrue(o["case_read_authority"])
        self.assertEqual(o["authority_scope"],"THIS_EXACT_LEASE_ONLY")
        self.assertFalse(o["global_fresh_reality_authority"])
        self.assertFalse(o["promotion_authority"])
        self.assertFalse(o["acceptance_credit_authorized"])

    def test_duplicate_422_fails_closed(self):
        o=verify_atomic_one_use_execution_claim(doc(422))
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertFalse(o["execution_authority"])
        self.assertFalse(o["case_read_authority"])
        self.assertIn("ATOMIC_CREATE",o["errors"][0])

    def test_scope_drift_changes_claim_ref(self):
        d=doc(201)
        prior=d["claim_receipt"]["claim_ref"]
        d["lease"]["scope"]["max_case_count"]=73
        o=verify_atomic_one_use_execution_claim(d)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertNotEqual(expected_claim_ref(execution_lease_digest(d["lease"])),prior)

    def test_activation_drift_changes_lease_digest(self):
        d=doc(201)
        d["lease"]["activation"]["git_blob_sha"]="c"*40
        o=verify_atomic_one_use_execution_claim(d)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertIn("LEASE_DIGEST",o["errors"][0])

    def test_absence_precheck_is_forbidden(self):
        d=doc(201)
        d["claim_receipt"]["claim_ref_absence_precheck_performed"]=True
        o=verify_atomic_one_use_execution_claim(d)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertIn("ABSENCE_PRECHECK",o["errors"][0])

    def test_execution_started_before_claim_fails(self):
        d=doc(201)
        d["claim_receipt"]["execution_started_before_claim"]=True
        o=verify_atomic_one_use_execution_claim(d)
        self.assertEqual(o["status"],"FAIL_CLOSED")

    def test_case_read_before_claim_fails(self):
        d=doc(201)
        d["claim_receipt"]["case_read_before_claim"]=True
        o=verify_atomic_one_use_execution_claim(d)
        self.assertEqual(o["status"],"FAIL_CLOSED")

    def test_wrong_target_sha_fails(self):
        d=doc(201)
        d["claim_receipt"]["expected_target_sha"]="c"*40
        o=verify_atomic_one_use_execution_claim(d)
        self.assertEqual(o["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main(verbosity=2)
