from __future__ import annotations

import copy
import json
import pathlib
import unittest

from canonical.runtime.pure_field_projection_capsule_v1 import compile_capsule
from canonical.runtime.pure_field_projection_currentness_v1 import verify_currentness
from canonical.runtime.pure_projection_consumer_guard_v1 import evaluate_pure_consumer
from canonical.runtime.pure_sealed_projection_consumer_v1 import run_pure_sealed_consumer
from canonical.runtime.sealed_field_projection_consumer_v1 import (
    PROJECTION_FILE,
    RUNNER_SCHEMA,
)
from canonical.runtime.field_scoped_zero_reality_reuse_gate_v1 import verify_reuse


A = "a" * 64
CONSUMER = """
def evaluate(projection):
    authority = projection["sources"][0]["projection"]
    return {
        "closed": authority["/terminal/closed"],
        "open_count": authority["/terminal/open_count"],
    }
"""


class ExecutingFakeLauncher:
    def __call__(self, policy):
        root = pathlib.Path(policy["input_dir"])
        projection = json.loads(
            (root / PROJECTION_FILE).read_text(encoding="utf-8")
        )
        source = (root / "consumer.py").read_text(encoding="utf-8")
        result = evaluate_pure_consumer(source=source, projection=projection)
        if not result["pass"]:
            return {
                "status": "CHILD_EXITED",
                "returncode": 1,
                "policy_sha256": "f" * 64,
                "broker_payload": b"{}",
            }
        payload = {
            "schema": RUNNER_SCHEMA,
            "projection_bundle_sha256": projection[
                "projection_bundle_sha256"
            ],
            "consumer_result": result["consumer_result"],
        }
        return {
            "status": "CHILD_EXITED",
            "returncode": 0,
            "policy_sha256": "f" * 64,
            "broker_payload": json.dumps(
                payload, separators=(",", ":")
            ).encode(),
        }


class FieldScopedZeroRealityReuseGateTests(unittest.TestCase):
    def documents(self):
        return {
            "canonical/governance/CURRENT.json": {
                "terminal": {"closed": False, "open_count": 12},
                "scheduler": {"generation": 44},
            }
        }

    def dependencies(self):
        return {
            "canonical/governance/CURRENT.json": [
                "/terminal/closed",
                "/terminal/open_count",
            ]
        }

    def capsule(self):
        return compile_capsule(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_source=CONSUMER,
        )

    def currentness(self, frozen=None, docs=None):
        return verify_currentness(
            frozen_capsule=frozen or self.capsule(),
            current_source_documents=docs or self.documents(),
            field_dependencies=self.dependencies(),
            consumer_source=CONSUMER,
        )

    def sealed(self, docs=None):
        return run_pure_sealed_consumer(
            source_documents=docs or self.documents(),
            field_dependencies=self.dependencies(),
            consumer_source=CONSUMER,
            launcher=ExecutingFakeLauncher(),
        )

    def independent(self, frozen=None):
        cap = frozen or self.capsule()
        return {
            "pass": True,
            "independently_verified": True,
            "sha256": A,
            "semantic_identity_sha256": cap["semantic_identity_sha256"],
            "consumer_result_sha256": cap["consumer_result_sha256"],
            "external_unbound_dependencies": [],
            "dynamic_or_implicit_dependencies": [],
        }

    def valid(self):
        cap = self.capsule()
        return cap, self.currentness(cap), self.sealed(), self.independent(cap)

    def test_exact_current_pure_sealed_independent_binding_allows_reuse_only(self):
        cap, current, sealed, independent = self.valid()
        out = verify_reuse(
            frozen_capsule=cap,
            currentness_receipt=current,
            pure_sealed_execution_receipt=sealed,
            independent_result_verification=independent,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["zero_reality_verification_reuse_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])

    def test_semantic_drift_fails_closed(self):
        cap = self.capsule()
        docs = self.documents()
        docs["canonical/governance/CURRENT.json"]["terminal"]["open_count"] = 11
        out = verify_reuse(
            frozen_capsule=cap,
            currentness_receipt=self.currentness(cap, docs),
            pure_sealed_execution_receipt=self.sealed(docs),
            independent_result_verification=self.independent(cap),
        )
        self.assertFalse(out["pass"])
        self.assertIn("CURRENTNESS_RECEIPT_INVALID", out["reason"])

    def test_sealed_projection_mismatch_fails_closed(self):
        cap, current, sealed, independent = self.valid()
        sealed = copy.deepcopy(sealed)
        sealed["projection_bundle_sha256"] = "b" * 64
        out = verify_reuse(
            frozen_capsule=cap,
            currentness_receipt=current,
            pure_sealed_execution_receipt=sealed,
            independent_result_verification=independent,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SEALED_PROJECTION_BINDING_MISMATCH")

    def test_sealed_result_mismatch_fails_closed(self):
        cap, current, sealed, independent = self.valid()
        sealed = copy.deepcopy(sealed)
        sealed["consumer_result"]["open_count"] = 999
        out = verify_reuse(
            frozen_capsule=cap,
            currentness_receipt=current,
            pure_sealed_execution_receipt=sealed,
            independent_result_verification=independent,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SEALED_CONSUMER_RESULT_BINDING_MISMATCH")

    def test_nonindependent_result_receipt_fails_closed(self):
        cap, current, sealed, independent = self.valid()
        independent["independently_verified"] = False
        out = verify_reuse(
            frozen_capsule=cap,
            currentness_receipt=current,
            pure_sealed_execution_receipt=sealed,
            independent_result_verification=independent,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "INDEPENDENT_RESULT_VERIFICATION_INVALID")

    def test_open_external_dependency_fails_closed(self):
        cap, current, sealed, independent = self.valid()
        independent["external_unbound_dependencies"] = ["NETWORK_FACT"]
        out = verify_reuse(
            frozen_capsule=cap,
            currentness_receipt=current,
            pure_sealed_execution_receipt=sealed,
            independent_result_verification=independent,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "INDEPENDENT_EXTERNAL_DEPENDENCIES_OPEN")

    def test_open_dynamic_dependency_fails_closed(self):
        cap, current, sealed, independent = self.valid()
        independent["dynamic_or_implicit_dependencies"] = ["AMBIENT_STATE"]
        out = verify_reuse(
            frozen_capsule=cap,
            currentness_receipt=current,
            pure_sealed_execution_receipt=sealed,
            independent_result_verification=independent,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "INDEPENDENT_DYNAMIC_DEPENDENCIES_OPEN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
