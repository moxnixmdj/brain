from __future__ import annotations
import unittest

from canonical.runtime.tb_science_brain_adapter_preflight_v1 import (
    REQUIRED_TERMINAL_ENV,
    run_preflight,
)


class TBScienceBrainAdapterPreflightTests(unittest.TestCase):
    def test_live_bound_route_passes_without_terminal_exposure(self) -> None:
        out = run_preflight()
        self.assertTrue(out["pass"], out["errors"])
        self.assertEqual(out["errors"], [])
        self.assertFalse(out["terminal_task_content_consumed"])
        self.assertFalse(out["terminal_result_observed"])
        self.assertEqual(out["incremental_spend_usd"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(
            out["candidate_closes_readiness_gap"],
            "NO_BOUND_GENERAL_BRAIN_AGENT_ADAPTER_FOR_TERMINAL_SCIENCE_TASKS",
        )

    def test_terminal_planner_is_fail_closed_to_exact_local_identity(self) -> None:
        self.assertEqual(
            REQUIRED_TERMINAL_ENV,
            {
                "PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_ONLY": "1",
                "PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_MODEL": "brain-qwen3.5-9b",
                "PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_BACKEND": "LOCAL_LLAMA_SERVER",
            },
        )

    def test_pass_does_not_claim_family_credit_or_execution_authority(self) -> None:
        out = run_preflight()
        remaining = set(out["remaining_before_terminal_execution"])
        self.assertIn("INDEPENDENT_EXACT_BYTE_VERIFICATION_OF_THIS_ADAPTER_BINDING", remaining)
        self.assertIn(
            "PROMOTION_PREFLIGHT_PROVING_A_FROZEN_TB_SCIENCE_SCORE_GE_58_7_IS_ADMISSIBLE_AND_PROMOTES_THE_FAMILY",
            remaining,
        )
        self.assertEqual(out["target_family"], "AGENTIC_SCIENTIFIC_RESEARCH")
        self.assertEqual(out["target_predicate"], "TB_SCIENCE_GE_58_7")


if __name__ == "__main__":
    unittest.main()
