from __future__ import annotations

import unittest

from canonical.runtime import root2_tb_science_inference_adapter_v1 as adapter


class _FakeEnvironment:
    async def exec(self, command: str, **kwargs):
        raise AssertionError("controller stub should prevent environment execution")


def _request():
    return {
        "benchmark_id": adapter.BENCHMARK_ID,
        "task_id": "synthetic-zero-case",
        "task_payload": {"instruction": "synthetic task", "max_cycles": 2},
        "allowed_tools": ["environment_exec", "finish"],
        "environment": _FakeEnvironment(),
        "output_contract": {"type": "text"},
        "brain_commit": "deadbeef",
        "configuration_hash": "cfg",
        "tool_policy_hash": "policy",
    }


class TestTBScienceRoot2InferenceAdapter(unittest.TestCase):
    def test_infer_bridges_verified_controller_contract(self):
        original = adapter.run_science_goal

        async def fake_controller(goal, environment, *, max_cycles):
            self.assertEqual(goal, "synthetic task")
            self.assertEqual(max_cycles, 2)
            self.assertTrue(callable(getattr(environment, "exec", None)))
            return {
                "status": "FINISHED",
                "summary": "synthetic-complete",
                "trace": [{"kind": "SYNTHETIC_ZERO_CASE"}],
                "controller_mode": "BRAIN_OWNED_RESEARCH_CONTROL__OPTIONAL_GENERAL_COGNITION_SUBSTRATE",
            }

        adapter.run_science_goal = fake_controller
        try:
            out = adapter.infer(_request())
        finally:
            adapter.run_science_goal = original

        self.assertEqual(out["status"], "FINISHED")
        self.assertEqual(out["answer"], "synthetic-complete")
        self.assertEqual(out["task_id"], "synthetic-zero-case")
        self.assertEqual(out["provenance"]["model_dependency_count"], 1)
        self.assertFalse(out["provenance"]["model_has_terminal_authority"])
        self.assertEqual(out["incremental_spend_usd"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_missing_live_environment_fails_closed(self):
        req = _request()
        req["environment"] = None
        with self.assertRaisesRegex(adapter.TBScienceAdapterBlocked, "LIVE_HARBOR_ENVIRONMENT_REQUIRED"):
            adapter.infer(req)

    def test_wrong_benchmark_fails_closed(self):
        req = _request()
        req["benchmark_id"] = "OTHER"
        with self.assertRaisesRegex(adapter.TBScienceAdapterBlocked, "BENCHMARK_ID_MISMATCH"):
            adapter.infer(req)

    def test_unsupported_tool_declaration_fails_closed(self):
        req = _request()
        req["allowed_tools"] = ["environment_exec", "network"]
        with self.assertRaisesRegex(adapter.TBScienceAdapterBlocked, "UNSUPPORTED_TOOL_DECLARATION"):
            adapter.infer(req)


if __name__ == "__main__":
    unittest.main()
