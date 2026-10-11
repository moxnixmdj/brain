from __future__ import annotations

import copy
import unittest

from canonical.runtime.field_scoped_authority_projection_gate_v1 import (
    freeze_manifest,
    check_manifest,
)
from canonical.runtime.field_scoped_work_unit_validity_guard_v1 import (
    CERT_SCHEMA,
    CERT_STATUS,
    VERIFY_SCOPE,
    FieldScopedWorkUnitValidityError,
    _component_digest,
    evaluate_currentness,
    validate_certificate,
)

SHA_A="a"*40
SHA_B="b"*40
SHA_C="c"*40
SCHED_A="1"*64
SCHED_B="2"*64


def document():
    return {
        "authority":{"proved":7,"open":12},
        "scheduler":{"generation":44},
        "telemetry":{"worker":"alpha"},
    }


def field_manifest():
    return {
        "source_path":"canonical/governance/CURRENT.json",
        "manifest":freeze_manifest(
            document(),
            ["/authority/proved","/authority/open"],
            source_path="canonical/governance/CURRENT.json",
        ),
    }


def static_deps():
    return {
        "canonical/runtime/verifier.py":SHA_A,
        "canonical/tests/test_verifier.py":SHA_B,
    }


def product():
    return {
        "path":"canonical/verification/result.json",
        "git_blob_sha":SHA_C,
    }


def certificate():
    deps=static_deps()
    return {
        "schema":CERT_SCHEMA,
        "status":CERT_STATUS,
        "independent_verified":True,
        "dependency_closure_complete":True,
        "verification_scope":VERIFY_SCOPE,
        "work_product":product(),
        "static_dependencies":deps,
        "static_dependency_digest_sha256":_component_digest(deps),
        "field_dependency_manifests":[field_manifest()],
        "external_unbound_dependencies":[],
        "dynamic_or_implicit_dependencies":[],
        "independent_verifier":{
            "independent_or_objective":True,
            "method":"INDEPENDENT_EXACT_BYTE_REPLAY_BOUND_TO_FIELD_MANIFEST",
        },
    }


class FieldScopedWorkUnitValidityGuardTests(unittest.TestCase):
    def test_valid_certificate_binds_exact_product_static_and_fields(self):
        out=validate_certificate(
            certificate(),
            expected_work_product=product(),
            expected_static_dependencies=static_deps(),
            expected_field_manifests=[field_manifest()],
        )
        self.assertTrue(out["certificate_valid"])
        self.assertEqual(out["work_product"],product())

    def test_self_asserted_independence_fails_closed(self):
        c=certificate()
        c["independent_verified"]=False
        with self.assertRaises(FieldScopedWorkUnitValidityError):
            validate_certificate(
                c,
                expected_work_product=product(),
                expected_static_dependencies=static_deps(),
                expected_field_manifests=[field_manifest()],
            )

    def test_static_dependency_omission_fails_closed(self):
        c=certificate()
        c["static_dependencies"]={"canonical/runtime/verifier.py":SHA_A}
        c["static_dependency_digest_sha256"]=_component_digest(
            c["static_dependencies"]
        )
        with self.assertRaises(FieldScopedWorkUnitValidityError):
            validate_certificate(
                c,
                expected_work_product=product(),
                expected_static_dependencies=static_deps(),
                expected_field_manifests=[field_manifest()],
            )

    def test_field_manifest_omission_fails_closed(self):
        c=certificate()
        c["field_dependency_manifests"]=[]
        with self.assertRaises(FieldScopedWorkUnitValidityError):
            validate_certificate(
                c,
                expected_work_product=product(),
                expected_static_dependencies=static_deps(),
                expected_field_manifests=[field_manifest()],
            )

    def test_open_dynamic_dependency_fails_closed(self):
        c=certificate()
        c["dynamic_or_implicit_dependencies"]=["AMBIENT_REPO_READ"]
        with self.assertRaises(FieldScopedWorkUnitValidityError):
            validate_certificate(
                c,
                expected_work_product=product(),
                expected_static_dependencies=static_deps(),
                expected_field_manifests=[field_manifest()],
            )

    def test_open_external_dependency_fails_closed(self):
        c=certificate()
        c["external_unbound_dependencies"]=["NETWORK_FACT"]
        with self.assertRaises(FieldScopedWorkUnitValidityError):
            validate_certificate(
                c,
                expected_work_product=product(),
                expected_static_dependencies=static_deps(),
                expected_field_manifests=[field_manifest()],
            )

    def test_unrelated_same_file_churn_preserves_semantics(self):
        manifest=field_manifest()["manifest"]
        live=document()
        live["scheduler"]["generation"]=999
        live["telemetry"]["worker"]="omega"
        field_check=check_manifest(live,manifest)
        out=evaluate_currentness(
            expected_work_product_sha=SHA_C,
            current_work_product_sha=SHA_C,
            expected_static_dependencies=static_deps(),
            current_static_dependencies=static_deps(),
            field_manifest_checks=[field_check],
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_B,
            certificate_verified=True,
        )
        self.assertTrue(out["semantic_valid"],out)
        self.assertTrue(out["semantic_reuse_allowed"])
        self.assertFalse(out["scheduler_current"])
        self.assertEqual(
            out["status"],
            "PASS__FIELD_SCOPED_SEMANTIC_RESULT_REUSABLE__SCHEDULER_REPLAN_REQUIRED",
        )

    def test_declared_field_change_invalidates(self):
        manifest=field_manifest()["manifest"]
        live=document()
        live["authority"]["proved"]=8
        field_check=check_manifest(live,manifest)
        out=evaluate_currentness(
            expected_work_product_sha=SHA_C,
            current_work_product_sha=SHA_C,
            expected_static_dependencies=static_deps(),
            current_static_dependencies=static_deps(),
            field_manifest_checks=[field_check],
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_A,
            certificate_verified=True,
        )
        self.assertFalse(out["semantic_valid"])
        self.assertFalse(out["semantic_reuse_allowed"])

    def test_static_blob_change_invalidates(self):
        changed=static_deps()
        changed["canonical/runtime/verifier.py"]="d"*40
        out=evaluate_currentness(
            expected_work_product_sha=SHA_C,
            current_work_product_sha=SHA_C,
            expected_static_dependencies=static_deps(),
            current_static_dependencies=changed,
            field_manifest_checks=[check_manifest(document(),field_manifest()["manifest"])],
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_A,
            certificate_verified=True,
        )
        self.assertFalse(out["semantic_valid"])

    def test_work_product_change_invalidates(self):
        out=evaluate_currentness(
            expected_work_product_sha=SHA_C,
            current_work_product_sha="d"*40,
            expected_static_dependencies=static_deps(),
            current_static_dependencies=static_deps(),
            field_manifest_checks=[check_manifest(document(),field_manifest()["manifest"])],
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_A,
            certificate_verified=True,
        )
        self.assertFalse(out["semantic_valid"])

    def test_scheduler_current_still_grants_no_consequential_authority(self):
        out=evaluate_currentness(
            expected_work_product_sha=SHA_C,
            current_work_product_sha=SHA_C,
            expected_static_dependencies=static_deps(),
            current_static_dependencies=static_deps(),
            field_manifest_checks=[check_manifest(document(),field_manifest()["manifest"])],
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_A,
            certificate_verified=True,
        )
        self.assertTrue(out["semantic_valid"])
        self.assertTrue(out["scheduler_current"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])
        self.assertFalse(out["fresh_reality_gate_current"])

    def test_unverified_certificate_never_reuses(self):
        out=evaluate_currentness(
            expected_work_product_sha=SHA_C,
            current_work_product_sha=SHA_C,
            expected_static_dependencies=static_deps(),
            current_static_dependencies=static_deps(),
            field_manifest_checks=[check_manifest(document(),field_manifest()["manifest"])],
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_A,
            certificate_verified=False,
        )
        self.assertFalse(out["semantic_reuse_allowed"])
        self.assertEqual(out["status"],"FAIL_CLOSED__DEPENDENCY_CLOSURE_UNVERIFIED")


if __name__=="__main__":
    unittest.main(verbosity=2)
