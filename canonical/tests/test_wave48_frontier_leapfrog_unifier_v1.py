import unittest

from canonical.runtime.wave48_frontier_leapfrog_unifier_v1 import (
    Wave48FrontierLeapfrogUnifier,
    evaluate_fixedbench_abstention,
)


class TestWave48FrontierLeapfrogUnifier(unittest.TestCase):
    def test_fixedbench_abstention_and_falsification(self) -> None:
        verifier = lambda src: "bug" not in src
        verdict = evaluate_fixedbench_abstention(
            baseline_passed=True,
            verifier_fn=verifier,
            sabotaged_source="def f(): return 'bug'",
        )
        self.assertTrue(verdict.abstain)
        self.assertTrue(verdict.verifier_falsified)
        self.assertEqual(verdict.reason, "SETTLED__NO_DEFECT_PRESENT")

    def test_dbsp_meme_cascade_and_absence(self) -> None:
        u = Wave48FrontierLeapfrogUnifier()
        u.meme_memory.assert_fact("auth_token_valid")
        u.meme_memory.assert_fact("session_active", depends_on=["auth_token_valid"])
        u.meme_memory.assert_fact("can_deploy", depends_on=["session_active"])

        cascaded = u.meme_memory.retract_fact("auth_token_valid", reason="TOKEN_EXPIRED")
        self.assertEqual(cascaded, ["auth_token_valid", "session_active", "can_deploy"])
        present, status = u.meme_memory.query("can_deploy")
        self.assertFalse(present)
        self.assertEqual(status, "UNKNOWN__UPSTREAM_SUPERSEDED:TOKEN_EXPIRED")

    def test_anytime_e_value_and_polarity_and_jitrl(self) -> None:
        u = Wave48FrontierLeapfrogUnifier()
        promoted = False
        for _ in range(10):
            promoted = u.e_gate.update(0.95, 0.70)
        self.assertTrue(promoted)

        ok, msg = u.polarity_guard.check(True, False, True)
        self.assertTrue(ok)
        self.assertEqual(msg, "ALLOWED")
        self.assertTrue(u.polarity_guard.seal_handle("#submit").startswith("hcu_"))

        u.record_skill_advantage("ast_repair_v1", 0.9)
        u.record_skill_advantage("regex_patch_v1", 0.1)
        ranked = u.rank_candidates(["regex_patch_v1", "ast_repair_v1"])
        self.assertEqual(ranked[0][0], "ast_repair_v1")


if __name__ == "__main__":
    unittest.main()
