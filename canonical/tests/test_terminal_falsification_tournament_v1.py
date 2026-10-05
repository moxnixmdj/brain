from __future__ import annotations

import unittest

from canonical.runtime.terminal_falsification_tournament_v1 import evaluate_tournament

SHA = "a" * 40


def proposal(pid="P", interface="UNIVERSAL_SCOPE_AND_COMPOSITION", kind="BYPASS_SEARCH",
             status="PENDING", cost=2, targets=None, fresh=False, authority=False):
    f = {"id": "F1", "kind": kind, "cost_units": cost, "decisive": True, "status": status}
    if status in {"PASS_NO_COUNTEREXAMPLE", "COUNTEREXAMPLE_FOUND"}:
        f["receipt"] = {"path": "canonical/verification/f.json", "git_blob_sha": "b" * 40}
    return {
        "id": pid,
        "interface": interface,
        "target_obligations": targets or ["A", "B"],
        "claim": {"id": pid + "_CLAIM", "statement": "candidate theorem", "quantifier": "UNIVERSAL"},
        "falsifiers": [f],
        "action_cost_units": 10,
        "expected_closure_count": 2,
        "requires_fresh_reality": fresh,
        "fresh_reality_authority": authority,
    }


def run(*ps):
    return evaluate_tournament({
        "tournament_id": "T",
        "terminal_state_git_blob_sha": SHA,
        "proposals": list(ps),
    })


class TournamentTests(unittest.TestCase):
    def test_pending_falsifier_preempts_execution(self):
        out = run(proposal())
        self.assertEqual(out["selected_next_action"]["kind"], "RUN_FALSIFIER")
        self.assertEqual(out["selected_next_action"]["falsifier_id"], "F1")

    def test_verified_counterexample_kills_claim(self):
        out = run(proposal(status="COUNTEREXAMPLE_FOUND"))
        self.assertEqual(out["proposal_results"][0]["status"], "KILLED_BY_VERIFIED_COUNTEREXAMPLE")
        self.assertIsNone(out["selected_next_action"])

    def test_survival_is_not_proof_and_zero_credit(self):
        out = run(proposal(status="PASS_NO_COUNTEREXAMPLE"))
        r = out["proposal_results"][0]
        self.assertEqual(r["status"], "SURVIVES_FALSIFICATION__ELIGIBLE_FOR_EXECUTION")
        self.assertFalse(r["survival_is_proof"])
        self.assertEqual(r["proof_credit_delta"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_off_frontier_denied_without_content_addressed_wake(self):
        p = proposal(interface="SOME_OLD_PROGRAM")
        out = run(p)
        self.assertEqual(out["proposal_results"][0]["status"], "DENY_OFF_FRONTIER_NO_WAKE_RECEIPT")

    def test_off_frontier_can_reenter_only_with_wake_receipt(self):
        p = proposal(interface="SOME_OLD_PROGRAM")
        p["wake_receipt"] = {
            "path": "canonical/verification/wake.json",
            "git_blob_sha": "c" * 40,
            "trigger": "NEW_VERIFIED_DELTA",
        }
        out = run(p)
        self.assertEqual(out["proposal_results"][0]["status"], "MUST_FALSIFY_FIRST")

    def test_external_result_must_attack_irreducibility_first(self):
        p = proposal(interface="EXTERNAL_RESULT_OR_ACCESS", kind="NEGATIVE_CANARY")
        out = run(p)
        self.assertEqual(out["proposal_results"][0]["status"], "DENY_MISSING_INTERFACE_SPECIFIC_ATTACK")
        p = proposal(interface="EXTERNAL_RESULT_OR_ACCESS", kind="STRONGER_PROOF_SUBSTITUTION")
        out = run(p)
        self.assertEqual(out["proposal_results"][0]["status"], "MUST_FALSIFY_FIRST")

    def test_behavioral_quotient_requires_unmapped_transform_attack(self):
        p = proposal(interface="BEHAVIORAL_QUOTIENT_AND_TRANSFER", kind="UNMAPPED_TRANSFORM_SEARCH")
        out = run(p)
        self.assertEqual(out["proposal_results"][0]["status"], "MUST_FALSIFY_FIRST")

    def test_fresh_reality_stays_blocked_without_authority(self):
        p = proposal(status="PASS_NO_COUNTEREXAMPLE", fresh=True, authority=False)
        out = run(p)
        self.assertEqual(
            out["proposal_results"][0]["status"],
            "SURVIVED_FALSIFICATION__BLOCKED_ON_FRESH_REALITY_AUTHORITY",
        )

    def test_global_ranking_prefers_falsifier_leverage(self):
        a = proposal(pid="A", cost=4, targets=["1", "2"])
        b = proposal(pid="B", cost=2, targets=["1", "2", "3"])
        out = run(a, b)
        self.assertEqual(out["selected_next_action"]["proposal_id"], "B")

    def test_falsifier_precedes_survivor_even_when_survivor_has_high_execution_leverage(self):
        a = proposal(pid="A", cost=10, targets=["1"])
        b = proposal(pid="B", status="PASS_NO_COUNTEREXAMPLE", targets=["1", "2", "3"])
        b["action_cost_units"] = 0.1
        b["expected_closure_count"] = 100
        out = run(a, b)
        self.assertEqual(out["selected_next_action"]["proposal_id"], "A")
        self.assertEqual(out["selected_next_action"]["kind"], "RUN_FALSIFIER")

    def test_bad_completed_receipt_fails_closed(self):
        p = proposal(status="PASS_NO_COUNTEREXAMPLE")
        p["falsifiers"][0]["receipt"]["git_blob_sha"] = "not-a-sha"
        out = run(p)
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
