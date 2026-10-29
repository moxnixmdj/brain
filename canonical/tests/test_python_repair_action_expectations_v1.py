"""Planner action expectations must reflect semantic results, not file writes."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import astra_runtime
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as patch

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


class RepairActionExpectationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capabilities = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]

    def assert_rejected(self, capability: str, result: dict) -> None:
        action = self.capabilities[capability]["action_template"]
        with self.assertRaisesRegex(astra_runtime.Blocker, "ACTION_EXPECTATION_FAILED"):
            astra_runtime._verify_action_expectation(action, result)

    def test_no_candidate_does_not_satisfy_repair_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "m.py").write_text("def f(x):\n    return x\n", encoding="utf-8")
            (root / "test_m.py").write_text("from m import f\ndef test_value():\n    assert f(2) == 99\n", encoding="utf-8")
            result = patch.run({"source_path": "m.py", "test_paths": ["test_m.py"],
                                "output_path": "out.json", "max_candidates": 10}, root)
            self.assertFalse(result["pass"])
            self.assertTrue(result["output_verified"])
            self.assert_rejected("python.patch.search.test_guided.ast.v1", result)

    def test_empty_rankings_and_noop_application_do_not_satisfy_effects(self):
        cases = {
            "python.fault.localize.dynamic.dataflow.v1": {"pass": False, "output_verified": True},
            "python.fault.provenance.interprocedural.value.v1": {"pass": False, "output_verified": True},
            "python.software.repair.apply.verified.v1": {"pass": True, "applied": False, "output_verified": True},
            "python.software.repair.loop.coupled.ast.v1": {"pass": True, "crossed_nonmonotonic_valley": False, "output_verified": True},
            "python.software.repair.guided.provenance.coupled.v1": {"pass": True, "provenance_guided_verified": False, "output_verified": True},
            "python.software.repair.measured_acceptance.v1": {"pass": False, "output_verified": True},
            "python.software.repair.semantic_acceptance.v1": {"pass": False, "output_verified": True},
        }
        for capability, result in cases.items():
            with self.subTest(capability=capability):
                self.assert_rejected(capability, result)

    def test_positive_effect_fields_are_accepted(self):
        expected = {"python.patch.search.test_guided.ast.v1": "pass",
                    "python.fault.localize.dynamic.dataflow.v1": "pass",
                    "python.software.repair.apply.verified.v1": "applied",
                    "python.software.repair.loop.coupled.ast.v1": "crossed_nonmonotonic_valley",
                    "python.software.repair.guided.provenance.coupled.v1": "provenance_guided_verified"}
        for capability, field in expected.items():
            with self.subTest(capability=capability):
                action = self.capabilities[capability]["action_template"]
                self.assertEqual(action["expect"]["field"], field)
                astra_runtime._verify_action_expectation(action, {field: True})


if __name__ == "__main__":
    unittest.main()
