"""Wiring tests: Perfect Algorithm operators inside the live learning loop.

These tests exist because an import that nobody calls is not wiring. Each test
asserts that a specific operator is actually consulted on the real code path,
and that it did not widen any authority.

The authority boundary stays exactly where it was:
- the K1 prior only reorders candidates that have ALREADY passed independent
  re-authentication and exact-skeleton matching;
- semantic IR is a diagnostic field on a candidate that still cannot self-verify;
- the tomography gate can only add evidence of an effect, never remove it.
"""
from __future__ import annotations

import unittest

from canonical.runtime import autonomous_verified_self_improvement_v1 as loop
from canonical.runtime import perfect_algorithm_v1 as pa
from canonical.runtime.executable_skill_program_v7 import induce_candidate
from canonical.tests.test_universal_learning_proof_program_v7 import episode


class K1PriorIsConsultedTests(unittest.TestCase):
    def test_selection_consults_the_prior_and_still_admits_skills(self):
        """The prior runs on the real `_select_active_skill` path."""
        calls = {"n": 0, "ranked": 0, "bf": []}
        original = loop._k1_prior_for_skill_selection
        self.assertIsNotNone(original, "K1 prior must be importable by the loop")

        def spy(problem, state):
            prior = original(problem, state)
            calls["n"] += 1
            calls["ranked"] += len(prior.get("ranked") or ())
            calls["bf"].append(prior.get("effective_branching_factor"))
            return prior

        loop._k1_prior_for_skill_selection = spy
        try:
            suite = unittest.defaultTestLoader.loadTestsFromName(
                "canonical.tests.test_autonomous_verified_self_improvement_v1"
            )
            result = unittest.TextTestRunner(verbosity=0).run(suite)
        finally:
            loop._k1_prior_for_skill_selection = original

        self.assertTrue(result.wasSuccessful(), "wiring must not change selection outcomes")
        self.assertEqual([], result.failures)
        self.assertEqual([], result.errors)
        self.assertGreater(calls["n"], 0, "the prior was never consulted")
        self.assertGreater(calls["ranked"], 0, "the prior ranked nothing")

    def test_missing_prior_degrades_to_existing_behaviour(self):
        """Fail-safe: absent module must not break selection."""
        original = loop._k1_prior_for_skill_selection
        loop._k1_prior_for_skill_selection = None
        try:
            suite = unittest.defaultTestLoader.loadTestsFromName(
                "canonical.tests.test_autonomous_verified_self_improvement_v1"
            )
            result = unittest.TextTestRunner(verbosity=0).run(suite)
        finally:
            loop._k1_prior_for_skill_selection = original
        self.assertTrue(result.wasSuccessful(), "fallback path must still pass")

    def test_prior_is_a_ranking_hint_not_authority(self):
        """The prior never grants verified_skill or reuse_authorized."""
        prior = pa.k1_prior_for_skill_selection(
            {"initial_facts": ["goal"], "target_effects": ["done"]},
            {"skills": {
                "s1": {
                    "active": True,
                    "skill": {
                        "verified_skill": True,
                        "reuse_authorized": True,
                        "preconditions": ["goal"],
                        "postconditions": ["done"],
                        "steps": [{"op": "solve", "inputs": [], "outputs": ["done"]}],
                    },
                }
            }},
        )
        for row in prior.get("ranked") or ():
            self.assertNotIn("verified_skill", row)
            self.assertNotIn("reuse_authorized", row)
            self.assertNotIn("execution_authority", row)


class TomographyGateIsAdditiveTests(unittest.TestCase):
    def test_state_diff_can_only_add_evidence(self):
        clean = {}
        with_evidence = {"output_sha256": "abc"}
        self.assertFalse(loop._effect_may_have_occurred(clean))
        self.assertTrue(
            loop._effect_may_have_occurred(clean, state_diff={"state_changed": True})
        )
        self.assertTrue(loop._effect_may_have_occurred(with_evidence))
        self.assertTrue(
            loop._effect_may_have_occurred(
                with_evidence, state_diff={"state_changed": False}
            ),
            "a quiet diff must never clear an existing effect signal",
        )
        self.assertFalse(
            loop._effect_may_have_occurred(clean, state_diff={"state_changed": False})
        )


class SemanticIRIsDiagnosticOnlyTests(unittest.TestCase):
    def test_candidate_carries_meaning_digest_but_stays_unverified(self):
        candidate = induce_candidate([episode("e1", "a"), episode("e2", "b")])
        ir = candidate.get("semantic_ir")
        self.assertIsInstance(ir, dict)
        self.assertTrue(str(ir["semantic_ir_sha256"]).startswith("sha256:"))
        self.assertGreater(ir["semantic_ir_node_count"], 0)
        # The meaning digest must not promote anything.
        self.assertFalse(candidate["verified_skill"])
        self.assertFalse(candidate["reuse_authorized"])
        self.assertFalse(candidate["promotion_authority"])
        self.assertEqual(0, candidate["acceptance_credit_delta"])

    def test_semantic_ir_is_deterministic(self):
        first = induce_candidate([episode("e1", "a"), episode("e2", "b")])
        second = induce_candidate([episode("e1", "a"), episode("e2", "b")])
        self.assertEqual(first["semantic_ir"], second["semantic_ir"])
        self.assertEqual(first["candidate_sha256"], second["candidate_sha256"])

    def test_same_meaning_across_syntax_is_recognized(self):
        """UMG equivalence is what the skeleton check cannot see."""
        left = "def f(x):\n    return x * 2 + 1\n"
        right = "def g(y):\n    return (y * 2) + 1\n"
        self.assertTrue(pa.semantic_equivalent(pa.to_umg(left), pa.to_umg(right)))


class SchemaOwnershipTests(unittest.TestCase):
    def test_runtime_and_swe_kernel_modules_are_distinguishable(self):
        """Same name, different job: the identity must be unambiguous."""
        self.assertEqual("PROJECT_BRAIN_PERFECT_ALGORITHM_RUNTIME_V1", pa.RUNTIME_SCHEMA)
        try:
            from canonical.swe_kernel import perfect_algorithm_v1 as swe
        except Exception:  # pragma: no cover - optional dependency
            self.skipTest("swe_kernel module unavailable")
        self.assertNotEqual(pa.RUNTIME_SCHEMA, swe.SCHEMA)
        self.assertEqual("PROJECT_BRAIN_PA_MEMORY_V1", swe.MEMORY_SCHEMA)


if __name__ == "__main__":
    unittest.main(verbosity=2)
