from __future__ import annotations

import copy
import unittest

from canonical.runtime.work_unit_validity_guard_v2 import (
    CERT_SCHEMA,
    CERT_STATUS,
    WorkUnitValidityError,
    compute_component_digest,
    evaluate_two_clock_lease,
    validate_dependency_closure_certificate,
)


SHA_A="a"*40
SHA_B="b"*40
SHA_C="c"*40
SCHED_A="1"*64
SCHED_B="2"*64


def deps():
    return {
        "canonical/runtime/a.py":SHA_A,
        "canonical/governance/b.json":SHA_B,
    }


def product():
    return {
        "path":"canonical/verification/work_result.json",
        "git_blob_sha":SHA_C,
    }


def certificate():
    d=deps()
    return {
        "schema":CERT_SCHEMA,
        "status":CERT_STATUS,
        "independent_verified":True,
        "dependency_closure_complete":True,
        "verification_scope":"EXACT_WORK_PRODUCT_TRANSITIVE_SEMANTIC_DEPENDENCY_CONE",
        "work_product":product(),
        "semantic_dependencies":d,
        "semantic_dependency_digest_sha256":compute_component_digest(d),
        "external_unbound_dependencies":[],
        "dynamic_or_implicit_dependencies":[],
        "independent_verifier":{
            "independent_or_objective":True,
            "method":"INDEPENDENT_EXACT_BYTE_REPLAY",
        },
    }


class TwoClockWorkUnitValidityV2Tests(unittest.TestCase):
    def test_valid_certificate_binds_exact_product_and_dependencies(self):
        out=validate_dependency_closure_certificate(
            certificate(),
            expected_work_product=product(),
            expected_semantic_dependencies=deps(),
        )
        self.assertTrue(out["certificate_valid"])
        self.assertEqual(out["semantic_dependencies"],deps())

    def test_self_asserted_lease_boolean_cannot_replace_certificate(self):
        c=certificate()
        c["independent_verified"]=False
        with self.assertRaises(WorkUnitValidityError):
            validate_dependency_closure_certificate(
                c,
                expected_work_product=product(),
                expected_semantic_dependencies=deps(),
            )

    def test_dependency_omission_fails_closed(self):
        c=certificate()
        c["semantic_dependencies"]={"canonical/runtime/a.py":SHA_A}
        c["semantic_dependency_digest_sha256"]=compute_component_digest(
            c["semantic_dependencies"]
        )
        with self.assertRaises(WorkUnitValidityError):
            validate_dependency_closure_certificate(
                c,
                expected_work_product=product(),
                expected_semantic_dependencies=deps(),
            )

    def test_open_dynamic_dependency_fails_closed(self):
        c=certificate()
        c["dynamic_or_implicit_dependencies"]=["RUNTIME_ENV"]
        with self.assertRaises(WorkUnitValidityError):
            validate_dependency_closure_certificate(
                c,
                expected_work_product=product(),
                expected_semantic_dependencies=deps(),
            )

    def test_open_external_dependency_fails_closed(self):
        c=certificate()
        c["external_unbound_dependencies"]=["NETWORK_FACT"]
        with self.assertRaises(WorkUnitValidityError):
            validate_dependency_closure_certificate(
                c,
                expected_work_product=product(),
                expected_semantic_dependencies=deps(),
            )

    def test_work_product_mismatch_fails_closed(self):
        c=certificate()
        c["work_product"]["git_blob_sha"]="d"*40
        with self.assertRaises(WorkUnitValidityError):
            validate_dependency_closure_certificate(
                c,
                expected_work_product=product(),
                expected_semantic_dependencies=deps(),
            )

    def test_scheduler_only_churn_preserves_zero_reality_result(self):
        d=deps()
        out=evaluate_two_clock_lease(
            expected_work_product_sha=SHA_C,
            current_work_product_sha=SHA_C,
            expected_semantic_components=d,
            current_semantic_components_map=d,
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_B,
            dependency_closure_verified=True,
            work_class="ZERO_REALITY_DERIVATION",
        )
        self.assertTrue(out["semantic_valid"])
        self.assertTrue(out["semantic_reuse_allowed"])
        self.assertFalse(out["scheduler_current"])
        self.assertEqual(
            out["status"],
            "PASS__SEMANTIC_RESULT_REUSABLE__SCHEDULER_REPLAN_REQUIRED",
        )
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])

    def test_dependency_drift_invalidates_semantic_result(self):
        d=deps()
        changed=copy.deepcopy(d)
        changed["canonical/runtime/a.py"]="d"*40
        out=evaluate_two_clock_lease(
            expected_work_product_sha=SHA_C,
            current_work_product_sha=SHA_C,
            expected_semantic_components=d,
            current_semantic_components_map=changed,
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_A,
            dependency_closure_verified=True,
            work_class="ZERO_REALITY_DERIVATION",
        )
        self.assertFalse(out["semantic_valid"])
        self.assertFalse(out["semantic_reuse_allowed"])

    def test_work_product_drift_invalidates_semantic_result(self):
        d=deps()
        out=evaluate_two_clock_lease(
            expected_work_product_sha=SHA_C,
            current_work_product_sha="d"*40,
            expected_semantic_components=d,
            current_semantic_components_map=d,
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_A,
            dependency_closure_verified=True,
            work_class="ZERO_REALITY_DERIVATION",
        )
        self.assertFalse(out["semantic_valid"])
        self.assertFalse(out["semantic_reuse_allowed"])

    def test_fresh_reality_remains_blocked_on_scheduler_drift(self):
        d=deps()
        out=evaluate_two_clock_lease(
            expected_work_product_sha=SHA_C,
            current_work_product_sha=SHA_C,
            expected_semantic_components=d,
            current_semantic_components_map=d,
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_B,
            dependency_closure_verified=True,
            work_class="FRESH_REALITY_ACTION",
        )
        self.assertTrue(out["semantic_valid"])
        self.assertTrue(out["semantic_reuse_allowed"])
        self.assertFalse(out["fresh_reality_gate_current"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__SCHEDULER_STALE_FOR_FRESH_REALITY",
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
