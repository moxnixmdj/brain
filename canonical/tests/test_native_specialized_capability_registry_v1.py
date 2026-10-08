from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import native_specialized_capability_registry_v1 as native


class NativeSpecializedCapabilityRegistryV1Tests(unittest.TestCase):
    def test_registry_is_strict_read_only_zero_spend_whitelist(self):
        snap = native.registry_snapshot()
        self.assertEqual(
            snap["status"],
            "NATIVE_SPECIALIZED_CAPABILITY_REGISTRY_READY",
        )
        self.assertEqual(snap["operation_count"], 11)
        self.assertFalse(snap["arbitrary_python_allowed"])
        self.assertFalse(snap["effectful_operations_allowed"])
        self.assertTrue(all(row["read_only"] for row in snap["operations"]))
        self.assertTrue(
            all(row["incremental_spend_usd"] == 0 for row in snap["operations"])
        )

    @patch(
        "canonical.runtime.h100_verified_capability_registry_v8.registry_snapshot"
    )
    def test_h100_snapshot_executes_through_registered_native_operation(self, snap):
        snap.return_value = {
            "status": "VERIFIED_CAPABILITY_REGISTRY_V8_READY",
            "entry_count": 7,
        }
        out = native.invoke("H100_REGISTRY_SNAPSHOT_V8", {})
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__NATIVE_SPECIALIZED_OPERATION_EXECUTED",
        )
        self.assertEqual(
            out["result"]["status"],
            "VERIFIED_CAPABILITY_REGISTRY_V8_READY",
        )
        self.assertTrue(out["read_only"])
        self.assertEqual(out["incremental_spend_usd"], 0)

    def test_compile_native_instance_into_ordinary_universal_solver_node(self):
        binding = {
            "receipt": {"path": "r.json", "git_blob_sha": "a" * 40},
            "verification": {"path": "v.json", "git_blob_sha": "b" * 40},
        }
        problem = {
            "task_id": "native",
            "initial_facts": [],
            "target_effects": ["H100_REGISTRY_READY"],
            "capabilities": [],
        }
        compiled = native.compile_into_problem(
            problem,
            [{
                "instance_id": "h100-snapshot",
                "operation_id": "H100_REGISTRY_SNAPSHOT_V8",
                "requires": [],
                "provides": ["H100_REGISTRY_READY"],
                "args": {},
                "effect_semantics_binding": binding,
            }],
        )
        cap = compiled["capabilities"][0]
        self.assertEqual(cap["id"], "h100-snapshot")
        self.assertEqual(cap["result_fields"], ["result"])
        self.assertEqual(
            cap["action"]["verifier_id"],
            "NATIVE_SPECIALIZED_OPERATION_V1",
        )
        self.assertEqual(
            cap["action"]["effect_contract"]["effects"],
            ["H100_REGISTRY_READY"],
        )
        self.assertEqual(
            cap["action"]["effect_contract"]["verifier_success_condition"],
            native.SUCCESS_CONDITION,
        )
        self.assertEqual(cap["effect_semantics_binding"], binding)

    def test_value_reference_must_be_declared_as_requirement(self):
        problem = {
            "task_id": "compose",
            "initial_facts": [],
            "target_effects": ["PREDICTED"],
            "capabilities": [],
        }
        with self.assertRaisesRegex(
            native.NativeSpecializedCapabilityError,
            "EFFECT_RESULT_REFERENCE_NOT_DECLARED_REQUIREMENT",
        ):
            native.compile_into_problem(
                problem,
                [{
                    "instance_id": "predict",
                    "operation_id": "H100_PREDICT_VERIFIED_CAPABILITY_V8",
                    "requires": [],
                    "provides": ["PREDICTED"],
                    "args": {
                        "resolution": {
                            "$effect_result": {
                                "effect": "RESOLVED",
                                "field": "result",
                            }
                        },
                        "point": {"x": 1.0},
                    },
                }],
            )

    def test_declared_value_reference_compiles_for_cross_step_composition(self):
        problem = {
            "task_id": "compose",
            "initial_facts": [],
            "target_effects": ["PREDICTED"],
            "capabilities": [],
        }
        compiled = native.compile_into_problem(
            problem,
            [{
                "instance_id": "predict",
                "operation_id": "H100_PREDICT_VERIFIED_CAPABILITY_V8",
                "requires": ["RESOLVED"],
                "provides": ["PREDICTED"],
                "args": {
                    "resolution": {
                        "$effect_result": {
                            "effect": "RESOLVED",
                            "field": "result",
                        }
                    },
                    "point": {"x": 1.0},
                },
            }],
        )
        cap = compiled["capabilities"][0]
        self.assertEqual(cap["requires"], ["RESOLVED"])
        self.assertEqual(
            cap["action"]["verifier_payload"]["args"]["resolution"][
                "$effect_result"
            ]["effect"],
            "RESOLVED",
        )

    def test_unknown_operation_and_extra_arguments_fail_closed(self):
        with self.assertRaises(native.NativeSpecializedCapabilityError):
            native.invoke("ARBITRARY_PYTHON", {})
        with self.assertRaisesRegex(
            native.NativeSpecializedCapabilityError,
            "NATIVE_SPECIALIZED_ARGS_UNSUPPORTED",
        ):
            native.compile_into_problem(
                {
                    "task_id": "bad",
                    "initial_facts": [],
                    "target_effects": ["X"],
                    "capabilities": [],
                },
                [{
                    "instance_id": "bad",
                    "operation_id": "H100_REGISTRY_SNAPSHOT_V8",
                    "requires": [],
                    "provides": ["X"],
                    "args": {"python": "print('no')"},
                }],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
