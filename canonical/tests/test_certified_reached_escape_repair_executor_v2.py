from __future__ import annotations

import unittest

from canonical.runtime import certified_reached_escape_repair_executor_v1 as v1
from canonical.runtime import certified_reached_escape_repair_executor_v2 as e
from canonical.runtime import reached_escape_state_kernel_v1 as k


def state3():
    return {
        "schema": k.STATE_SCHEMA,
        "state_id": "S3",
        "regions": [{"region_id": x} for x in ("a", "b", "c")],
        "policies": [
            policy("pa", ("a",)),
            policy("pb", ("b",)),
            policy("pc", ("c",)),
        ],
        "discriminators": [],
    }


def state2():
    return {
        "schema": k.STATE_SCHEMA,
        "state_id": "S2",
        "regions": [{"region_id": "r1"}, {"region_id": "r2"}],
        "policies": [policy("p1", ("r1",)), policy("p2", ("r2",))],
        "discriminators": [],
    }


def policy(pid, covers):
    return {
        "policy_id": pid,
        "authenticated": True,
        "safe": True,
        "adequate_region_ids": list(covers),
    }


def candidate(alt, marker):
    return {
        "schema": v1.CANDIDATE_SCHEMA,
        "alternative_id": alt["alternative_id"],
        "proposal": {"marker": marker},
    }


def receipt(req, marker):
    cand = candidate(req["alternative"], marker)
    return {
        "pass": True,
        "receipt_sha256": (marker * 64)[:64],
        "frontier_changed": True,
        "verification_authority_mutated": False,
        "candidate_delta": cand,
        "candidate_delta_sha256": v1._sha(cand),
    }


def verifier_receipt(req, delta, marker):
    return {
        "schema": v1.VERIFICATION_SCHEMA,
        "pass": True,
        "receipt_sha256": (marker * 64)[:64],
        "candidate_delta_sha256": req["candidate_delta_sha256"],
        "alternative_id": req["alternative"]["alternative_id"],
        "verified_delta": delta,
        "verified_delta_sha256": v1._sha(delta),
        "verification_authority_mutated": False,
    }


class StrictProgressRepairLoopTests(unittest.TestCase):
    def test_two_step_discriminator_repair_reaches_certification(self):
        provider_calls = []
        verifier_calls = []
        deltas = [
            {
                "kind": "ADD_DISCRIMINATOR",
                "row": {
                    "discriminator_id": "d1",
                    "authenticated": True,
                    "safe": True,
                    "truthful": True,
                    "complete": True,
                    "outcomes": {"a": 0, "b": 1, "c": 1},
                },
            },
            {
                "kind": "ADD_DISCRIMINATOR",
                "row": {
                    "discriminator_id": "d2",
                    "authenticated": True,
                    "safe": True,
                    "truthful": True,
                    "complete": True,
                    "outcomes": {"a": 0, "b": 0, "c": 1},
                },
            },
        ]

        def provider(req):
            provider_calls.append(req)
            return receipt(req, "a")

        def verifier(req):
            i = len(verifier_calls)
            verifier_calls.append(req)
            return verifier_receipt(req, deltas[i], "b")

        out = e.execute(
            state3(),
            evidence_acquisition_provider=provider,
            candidate_verifier=verifier,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__ITERATIVE_REPAIR_VERIFIED_BY_CONSTRUCTOR_RECERTIFICATION",
        )
        self.assertTrue(out["repair_verified"])
        self.assertTrue(out["strict_progress_verified"])
        self.assertEqual(out["initial_repair_potential"], 2)
        self.assertEqual(out["final_repair_potential"], 0)
        self.assertEqual(out["accepted_strict_progress_steps"], 1)
        self.assertEqual(
            [(x["before_repair_potential"], x["after_repair_potential"]) for x in out["strict_progress_history"]],
            [(2, 1)],
        )
        self.assertEqual(len(provider_calls), 2)
        self.assertEqual(len(verifier_calls), 2)
        self.assertFalse(out["global_repair_acquirability_proved"])
        self.assertFalse(out["global_escape_progress_totality_proved"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_partial_progress_is_preserved_when_later_provider_exhausts(self):
        calls = 0
        d1 = {
            "kind": "ADD_DISCRIMINATOR",
            "row": {
                "discriminator_id": "d1",
                "authenticated": True,
                "safe": True,
                "truthful": True,
                "complete": True,
                "outcomes": {"a": 0, "b": 1, "c": 1},
            },
        }

        def provider(req):
            nonlocal calls
            calls += 1
            if calls == 1:
                return receipt(req, "a")
            return None

        def verifier(req):
            return verifier_receipt(req, d1, "b")

        out = e.execute(
            state3(),
            evidence_acquisition_provider=provider,
            candidate_verifier=verifier,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__NO_VERIFIED_ALTERNATIVE_RESTORED_CERTIFICATION_OR_STRICT_PROGRESS",
        )
        self.assertTrue(out["strict_progress_verified"])
        self.assertEqual(len(out["strict_progress_history"]), 1)
        self.assertEqual(out["strict_progress_history"][0]["before_repair_potential"], 2)
        self.assertEqual(out["strict_progress_history"][0]["after_repair_potential"], 1)
        self.assertEqual(out["current_repair_potential"], 1)
        self.assertEqual(
            len(out["candidate_state"]["discriminators"]),
            1,
        )

    def test_zero_progress_budget_blocks_provider_calls(self):
        calls = []
        def provider(req):
            calls.append(req)
            raise AssertionError("provider must not be called")
        def verifier(req):
            raise AssertionError("verifier must not be called")
        out = e.execute(
            state3(),
            evidence_acquisition_provider=provider,
            candidate_verifier=verifier,
            max_strict_progress_steps=0,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__STRICT_PROGRESS_BUDGET_EXHAUSTED")
        self.assertEqual(calls, [])
        self.assertEqual(out["current_repair_potential"], 2)

    def test_nondecreasing_verified_delta_is_not_retained(self):
        delta = {
            "kind": "ADD_POLICY",
            "row": policy("p_extra", ("r1",)),
        }
        def provider(req):
            return receipt(req, "a")
        def verifier(req):
            return verifier_receipt(req, delta, "b")
        out = e.execute(
            state2(),
            capability_synthesis_provider=provider,
            candidate_verifier=verifier,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__NO_VERIFIED_ALTERNATIVE_RESTORED_CERTIFICATION_OR_STRICT_PROGRESS",
        )
        self.assertFalse(out["strict_progress_verified"])
        self.assertEqual(out["strict_progress_history"], [])
        self.assertEqual(len(out["candidate_state"]["policies"]), 2)

    def test_one_step_common_policy_fast_path_is_preserved(self):
        delta = {
            "kind": "ADD_POLICY",
            "row": policy("p_common", ("r1", "r2")),
        }
        def provider(req):
            return receipt(req, "a")
        def verifier(req):
            return verifier_receipt(req, delta, "b")
        out = e.execute(
            state2(),
            capability_synthesis_provider=provider,
            candidate_verifier=verifier,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__REPAIR_VERIFIED_BY_CONSTRUCTOR_RECERTIFICATION",
        )
        self.assertTrue(out["repair_verified"])
        self.assertFalse(out["strict_progress_verified"])
        self.assertEqual(out["strict_progress_history"], [])

    def test_missing_verifier_still_blocks_before_provider(self):
        calls = []
        def provider(req):
            calls.append(req)
            raise AssertionError
        out = e.execute(
            state2(),
            capability_synthesis_provider=provider,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__INDEPENDENT_CANDIDATE_VERIFIER_REQUIRED")
        self.assertEqual(calls, [])

    def test_invalid_progress_budget_fails_closed(self):
        out = e.execute(
            state2(),
            candidate_verifier=lambda req: None,
            max_strict_progress_steps=-1,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__STRICT_PROGRESS_BUDGET_INVALID")

    def test_already_certified_state_skips_everything(self):
        s = state2()
        s["policies"].append(policy("common", ("r1", "r2")))
        calls = []
        def never(req):
            calls.append(req)
            raise AssertionError
        out = e.execute(
            s,
            capability_synthesis_provider=never,
            evidence_acquisition_provider=never,
            candidate_verifier=never,
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["status"], "PASS__STATE_ALREADY_CERTIFIED")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
