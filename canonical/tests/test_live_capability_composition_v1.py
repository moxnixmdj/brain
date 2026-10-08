from __future__ import annotations

import unittest

from canonical.runtime import live_capability_composition_v1 as composition


class LiveCapabilityCompositionV1Tests(unittest.TestCase):
    def test_cross_step_value_flow_across_provider_kinds(self):
        calls = []

        def invoke(capability_id, payload, options):
            calls.append((capability_id, payload, options))
            if capability_id == "engine:SOURCE":
                return {
                    "pass": True,
                    "status": "PASS_SOURCE",
                    "result": {"value": 7},
                }
            if capability_id == "bound:DOUBLE":
                return {
                    "pass": True,
                    "status": "PASS_DOUBLE",
                    "result": {"value": int(payload["value"]) * 2},
                }
            raise AssertionError(capability_id)

        out = composition.execute(
            {
                "composition_id": "heterogeneous-flow",
                "inputs": {},
                "composition_steps": [
                    {
                        "step_id": "source",
                        "capability_id": "engine:SOURCE",
                        "payload": {},
                    },
                    {
                        "step_id": "double",
                        "capability_id": "bound:DOUBLE",
                        "payload": {
                            "value": {"$ref": "steps.source.result.value"},
                        },
                        "expect": {
                            "path": "result.value",
                            "equals": 14,
                        },
                    },
                ],
                "outputs": {
                    "answer": {"$ref": "steps.double.result.value"},
                },
            },
            invoke_capability=invoke,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["outputs"]["answer"], 14)
        self.assertEqual(out["execution_order"], ["source", "double"])
        self.assertEqual(out["cross_step_value_flow_count"], 1)
        self.assertEqual(out["provider_kind_count"], 2)
        self.assertTrue(out["native_step_verification_preserved"])
        self.assertEqual(len(calls), 2)

    def test_dependency_cycle_fails_closed_before_execution(self):
        calls = []

        def invoke(*args):
            calls.append(args)
            return {"pass": True}

        out = composition.execute(
            {
                "composition_steps": [
                    {
                        "step_id": "a",
                        "capability_id": "engine:A",
                        "depends_on": ["b"],
                        "payload": {},
                    },
                    {
                        "step_id": "b",
                        "capability_id": "engine:B",
                        "depends_on": ["a"],
                        "payload": {},
                    },
                ],
            },
            invoke_capability=invoke,
        )
        self.assertFalse(out["pass"])
        self.assertIn("COMPOSITION_CYCLE", out["reason"])
        self.assertEqual(calls, [])

    def test_native_capability_failure_stops_graph(self):
        called = []

        def invoke(capability_id, payload, options):
            called.append(capability_id)
            if capability_id == "engine:FAIL":
                return {"pass": False, "status": "EXPECTED_FAILURE"}
            return {"pass": True, "status": "SHOULD_NOT_RUN"}

        out = composition.execute(
            {
                "composition_steps": [
                    {
                        "step_id": "first",
                        "capability_id": "engine:FAIL",
                        "payload": {},
                    },
                    {
                        "step_id": "second",
                        "capability_id": "bound:NEVER",
                        "depends_on": ["first"],
                        "payload": {},
                    },
                ],
            },
            invoke_capability=invoke,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["failed_step_id"], "first")
        self.assertEqual(called, ["engine:FAIL"])
        self.assertEqual(
            out["learning_observation"]["failure_class"],
            "LIVE_CAPABILITY_COMPOSITION_STEP_FAILURE",
        )

    def test_expectation_failure_stops_graph(self):
        out = composition.execute(
            {
                "composition_steps": [
                    {
                        "step_id": "x",
                        "capability_id": "engine:X",
                        "payload": {},
                        "expect": {"path": "result.value", "equals": 2},
                    },
                ],
            },
            invoke_capability=lambda *_: {
                "pass": True,
                "status": "PASS",
                "result": {"value": 1},
            },
        )
        self.assertFalse(out["pass"])
        self.assertIn(
            "EXPECTATION_EQUALS_FAILED:x:0:result.value",
            out["expectation_errors"],
        )

    def test_self_composition_recursion_is_forbidden(self):
        out = composition.execute(
            {
                "composition_steps": [
                    {
                        "step_id": "loop",
                        "capability_id": "engine:LIVE_COMPOSITION",
                        "payload": {},
                    }
                ],
            },
            invoke_capability=lambda *_: {"pass": True},
        )
        self.assertFalse(out["pass"])
        self.assertIn("SELF_COMPOSITION_RECURSION_FORBIDDEN", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
