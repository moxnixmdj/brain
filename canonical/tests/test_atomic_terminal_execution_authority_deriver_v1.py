from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import atomic_terminal_execution_authority_deriver_v1 as d
from canonical.runtime import atomic_route_specific_terminal_launch_v1 as launch


class AtomicTerminalExecutionAuthorityDeriverTests(unittest.TestCase):
    @property
    def root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def test_current_exact_state_derives_authority_without_terminal_execution(self):
        with mock.patch.object(
            launch.cad, "execute_cad_route", side_effect=AssertionError("terminal CAD executed")
        ), mock.patch.object(
            launch.direct, "execute_direct_route", side_effect=AssertionError("terminal direct executed")
        ), mock.patch.object(
            launch.saccr, "execute_terminal", side_effect=AssertionError("terminal SA-CCR executed")
        ):
            out = d.evaluate(self.root)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["execution_authority"])
        self.assertEqual(out["derived_bound_executor_count"], 12)
        self.assertFalse(out["post_freeze_beacon_constructed"])
        self.assertEqual(out["terminal_results_observed"], 0)
        self.assertEqual(out["fresh_terminal_evidence_consumed"], 0)

    def test_independent_launcher_receipt_matches_current_exact_bytes(self):
        out = d.validate_launcher_receipt(self.root)
        self.assertTrue(out["pass"], out)

    def test_prequalification_failure_blocks_authority(self):
        with mock.patch.object(
            d, "evaluate_prequalification",
            return_value={"pass": False, "execution_authority": False, "failed_predicates": ["X"]},
        ), mock.patch.object(
            d, "build_prelaunch_commitment",
            return_value={
                "pass": True,
                "candidate_package_commitment": "C",
                "executor_state": {"derived_bound_executor_count": 12},
                "terminal_case_generation_performed": False,
                "errors": [],
            },
        ):
            out = d.evaluate(self.root)
        self.assertFalse(out["pass"])
        self.assertFalse(out["execution_authority"])
        self.assertIn("NONCIRCULAR_PREQUALIFICATION_NOT_PASS", out["failed_predicates"])

    def test_prelaunch_failure_blocks_authority(self):
        with mock.patch.object(
            d, "evaluate_prequalification",
            return_value={"pass": True, "execution_authority": True, "failed_predicates": []},
        ), mock.patch.object(
            d, "build_prelaunch_commitment",
            return_value={
                "pass": False,
                "candidate_package_commitment": None,
                "executor_state": {"derived_bound_executor_count": 12},
                "terminal_case_generation_performed": False,
                "errors": ["DRIFT"],
            },
        ):
            out = d.evaluate(self.root)
        self.assertFalse(out["pass"])
        self.assertIn("ATOMIC_PRELAUNCH_COMMITMENT_NOT_PASS", out["failed_predicates"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
