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
        self.assertTrue(out["capability_lifecycle_complete"], out)
        self.assertTrue(all(out["capability_lifecycle"].values()), out)
        self.assertEqual(
            out["live_owned_capability_count"],
            out["universally_invocable_capability_count"],
        )

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


    def test_missing_live_composition_reopens_r1(self):
        ownership, invocation = self._current()
        drifted = dict(ENGINE_DESCRIPTORS)
        drifted.pop("LIVE_COMPOSITION", None)
        out = gate.evaluate(
            drifted,
            ownership=ownership,
            invocation=invocation,
            subruntime_surfaces=live_runtime.SURFACES,
            canonical_public_entrypoint=CANONICAL_PUBLIC_ENTRYPOINT,
            subordinate_runtime_entrypoint=SUBORDINATE_RUNTIME_ENTRYPOINT,
        )
        self.assertFalse(out["pass"])
        self.assertIn("ENGINE_BINDING_DRIFT:LIVE_COMPOSITION", out["errors"])
        self.assertFalse(out["capability_lifecycle"]["composable"])
        self.assertFalse(out["capability_lifecycle_complete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
