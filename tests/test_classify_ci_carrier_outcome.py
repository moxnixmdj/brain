from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "classify_ci_carrier_outcome.py"
SPEC = importlib.util.spec_from_file_location("ci_carrier_classifier", SCRIPT)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class CICarrierClassifierTests(unittest.TestCase):
    def test_preassignment_failure_is_not_semantic_failure(self):
        out = mod.classify_jobs(
            [{
                "status": "completed",
                "conclusion": "failure",
                "runner_id": 0,
                "runner_name": "",
                "steps": [],
            }]
        )
        self.assertEqual(out["classification"], mod.PREASSIGNMENT)
        self.assertFalse(out["semantic_failure_observed"])
        self.assertTrue(out["alternate_verification_carrier_required"])
        self.assertFalse(out["branch_repair_authorized_from_this_signal"])

    def test_executed_failure_requires_logs_not_automatic_repair(self):
        out = mod.classify_jobs(
            [{
                "status": "completed",
                "conclusion": "failure",
                "runner_id": 42,
                "runner_name": "runner",
                "steps": [{"name": "test", "conclusion": "failure"}],
            }]
        )
        self.assertEqual(out["classification"], mod.EXECUTED_FAILURE)
        self.assertTrue(out["semantic_failure_observed"])
        self.assertFalse(out["branch_repair_authorized_from_this_signal"])

    def test_success(self):
        out = mod.classify_jobs(
            [{
                "status": "completed",
                "conclusion": "success",
                "runner_id": 42,
                "runner_name": "runner",
                "steps": [{"name": "test", "conclusion": "success"}],
            }]
        )
        self.assertEqual(out["classification"], mod.EXECUTED_SUCCESS)

    def test_pending_precedes_preassignment_signature(self):
        out = mod.classify_jobs(
            [{
                "status": "queued",
                "conclusion": None,
                "runner_id": 0,
                "runner_name": "",
                "steps": [],
            }]
        )
        self.assertEqual(out["classification"], mod.PENDING)
        self.assertFalse(out["alternate_verification_carrier_required"])

    def test_mixed_preassignment_and_success_is_mixed(self):
        out = mod.classify_jobs(
            [
                {
                    "status": "completed",
                    "conclusion": "failure",
                    "runner_id": 0,
                    "runner_name": "",
                    "steps": [],
                },
                {
                    "status": "completed",
                    "conclusion": "success",
                    "runner_id": 7,
                    "runner_name": "runner",
                    "steps": [{"name": "x"}],
                },
            ]
        )
        self.assertEqual(out["classification"], mod.MIXED)
        self.assertTrue(out["alternate_verification_carrier_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
