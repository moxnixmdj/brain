from __future__ import annotations
import unittest

from canonical.runtime import terminal_parent_portfolio_runner_v1 as runner


class TerminalParentPortfolioRunnerTests(unittest.TestCase):
    def test_static_preflight_binds_all_seven_multiplex_behaviors(self):
        out = runner.static_preflight()
        self.assertTrue(out["pass"], out)
        self.assertEqual(len(out["bound_behavior_ids"]), 7)
        self.assertIn(runner.CAD, out["bound_behavior_ids"])

    def test_seed_is_deterministic_and_case_specific(self):
        a = runner.derive_seed("c", "b", "case-1")
        b = runner.derive_seed("c", "b", "case-1")
        c = runner.derive_seed("c", "b", "case-2")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_all_four_parent_portfolios_pass_nonterminal_rehearsal(self):
        out = runner.rehearse_all_portfolios()
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["terminal_result"])
        self.assertEqual(out["fresh_terminal_evidence_consumed"], 0)
        self.assertEqual(set(out["portfolios"]), set(runner.PORTFOLIOS))
        for portfolio, row in out["portfolios"].items():
            self.assertTrue(row["pass"], (portfolio, row))
            self.assertFalse(row["terminal_result"])
            for receipt in row["receipts"]:
                self.assertTrue(receipt["load_bearing"])
                self.assertTrue(receipt["direct_instrumentation_pass"])
                self.assertTrue(receipt["parent_terminal_acceptance_pass"])
                self.assertFalse(receipt["case_replaced"])
                self.assertFalse(receipt["tuning_replay"])

    def test_real_entrypoint_is_fail_closed_before_launch_authority(self):
        with self.assertRaises(ValueError):
            runner.execute_parent_portfolio(
                "T0",
                commitment="not-a-real-terminal-commitment",
                beacon="not-a-real-terminal-beacon",
                direct_results={
                    runner.CAD: {
                        "pass": True,
                        "terminal_result": True,
                        "case_count": 128,
                    }
                },
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
