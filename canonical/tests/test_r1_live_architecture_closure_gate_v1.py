from __future__ import annotations

import unittest

from canonical.runtime import live_brain_runtime_v1 as live_runtime
from canonical.runtime import live_capability_invoker_v1 as live_invoker
from canonical.runtime import live_capability_ownership_v1 as live_ownership
from canonical.runtime import r1_live_architecture_closure_gate_v1 as gate
from canonical.runtime.unified_cognitive_fabric_v1 import (
    CANONICAL_PUBLIC_ENTRYPOINT,
    ENGINE_DESCRIPTORS,
    SUBORDINATE_RUNTIME_ENTRYPOINT,
)


class R1LiveArchitectureClosureGateV1Tests(unittest.TestCase):
    def _current(self):
        ownership = live_ownership.evaluate(ENGINE_DESCRIPTORS)
        invocation = live_invoker.coverage(ownership["live_owned_capability_ids"])
        return ownership, invocation

    def test_current_live_architecture_is_closed_and_drift_locked(self):
        ownership, invocation = self._current()
        out = gate.evaluate(
            ENGINE_DESCRIPTORS,
            ownership=ownership,
            invocation=invocation,
            subruntime_surfaces=live_runtime.SURFACES,
            canonical_public_entrypoint=CANONICAL_PUBLIC_ENTRYPOINT,
            subordinate_runtime_entrypoint=SUBORDINATE_RUNTIME_ENTRYPOINT,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["errors"], [])
        self.assertEqual(
            out["live_owned_capability_count"],
            out["universally_invocable_capability_count"],
        )

    def test_receipt_exact_blob_drift_reopens_r1(self):
        receipt = gate._json(gate.CURRENT_RECEIPT_PATH)
        tampered = dict(receipt)
        tampered["exact_blobs"] = {
            key: dict(value)
            for key, value in receipt["exact_blobs"].items()
        }
        tampered["exact_blobs"]["unified_fabric"]["git_blob_sha"] = "0" * 40
        errors, checked = gate._receipt_exact_blob_errors(tampered)
        self.assertGreater(checked, 0)
        self.assertIn("RECEIPT_EXACT_BLOB_DRIFT:unified_fabric", errors)

    def test_stale_authority_receipt_binding_reopens_r1(self):
        authority = gate._json(gate.AUTHORITY_PATH)
        authority = dict(authority)
        authority["live_capability_ownership_20261008_v1"] = dict(
            authority["live_capability_ownership_20261008_v1"]
        )
        authority["live_capability_ownership_20261008_v1"]["verification"] = dict(
            authority["live_capability_ownership_20261008_v1"]["verification"]
        )
        authority["live_capability_ownership_20261008_v1"]["verification"]["git_blob_sha"] = "0" * 40
        errors, _checked = gate._current_receipt_errors(authority)
        self.assertIn("AUTHORITY_VERIFICATION_RECEIPT_BLOB_DRIFT", errors)

    def test_engine_route_drift_reopens_r1(self):
        ownership, invocation = self._current()
        drifted = dict(ENGINE_DESCRIPTORS)
        drifted["ADAPTIVE_SOLVER"] = "parallel_runtime.run"
        out = gate.evaluate(
            drifted,
            ownership=ownership,
            invocation=invocation,
            subruntime_surfaces=live_runtime.SURFACES,
            canonical_public_entrypoint=CANONICAL_PUBLIC_ENTRYPOINT,
            subordinate_runtime_entrypoint=SUBORDINATE_RUNTIME_ENTRYPOINT,
        )
        self.assertFalse(out["pass"])
        self.assertIn("ENGINE_BINDING_DRIFT:ADAPTIVE_SOLVER", out["errors"])

    def test_missing_reuse_learning_surface_reopens_r1(self):
        ownership, invocation = self._current()
        surfaces = tuple(
            x for x in live_runtime.SURFACES
            if x != "AUTONOMOUS_VERIFIED_SELF_IMPROVEMENT_V1"
        )
        out = gate.evaluate(
            ENGINE_DESCRIPTORS,
            ownership=ownership,
            invocation=invocation,
            subruntime_surfaces=surfaces,
            canonical_public_entrypoint=CANONICAL_PUBLIC_ENTRYPOINT,
            subordinate_runtime_entrypoint=SUBORDINATE_RUNTIME_ENTRYPOINT,
        )
        self.assertFalse(out["pass"])
        self.assertIn(
            "SUBRUNTIME_SURFACE_MISSING:AUTONOMOUS_VERIFIED_SELF_IMPROVEMENT_V1",
            out["errors"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
