"""A candidate that fails the suite is refused, and only real evidence opens the gate.

WHY THIS TEST EXISTS
  Two plans on this branch depend on `required_verification_kind == 'TEST_SUITE'`
  being a real gate rather than a label:

    - broadening a learned rule's match surface is only safe if a weak caller
      cannot reach the broadened path. Probe E measured that a bool callback
      asking for TEST_SUITE gets 0/9, because evaluate() auto-demotes a bool to
      CALLER_PREDICATE and then rejects the kind mismatch.
    - admitting any generator of candidate source -- model-driven or not -- is
      only safe if a candidate that compiles and is WRONG is refused.

  Both are asserted here against the repository's own ProjectTestOracle, which
  copies the tree, runs the real acceptance measurement, and re-manifests the
  original tree to prove it was untouched. Nothing is stubbed and no evidence
  field is fabricated: the hashes, test_count and returncode come from a real
  subprocess suite run.

  This is the gate test that must exist BEFORE a generator does. Writing it
  afterwards would mean trusting the gate that the generator depends on.

WHAT WOULD MAKE THESE TESTS MEANINGLESS
  If a bool callback could satisfy required_kind='TEST_SUITE', or if a candidate
  that merely compiles were accepted, every test below would still pass while the
  gate was decoration. So the refusals are asserted as refusals, not as "did not
  crash", and the accepted path is asserted to carry real evidence fields.
"""

import pathlib
import tempfile
import unittest

from canonical.swe_kernel import verified_skill_crystallizer_v1 as K
from canonical.swe_kernel.skill_verification_contract_v1 import (
    ProjectTestOracle,
    VerificationResult,
    evaluate,
    source_sha256,
)

SCOPE = "SCOPE_BOUNDS_V1"

BUGGY = "def within(x, hi):\n    return x <= hi\n"
FIXED = "def within(x, hi):\n    return x < hi\n"
# Compiles cleanly, satisfies nothing. The whole point of it is that it is not a
# syntax error -- a gate that only rejected broken code would let this through.
WRONG = "def within(x, hi):\n    return True\n"

TEST_SRC = '''import unittest
from bounds import within


class TestUpperBoundIsExclusive(unittest.TestCase):
    def test_exclusive_at_the_upper_bound(self):
        self.assertFalse(within(10, 10))
        self.assertTrue(within(9, 10))

    def test_well_below_and_above(self):
        self.assertTrue(within(0, 10))
        self.assertFalse(within(11, 10))


if __name__ == "__main__":
    unittest.main()
'''

CONTRACT = {
    "schema_version": 1,
    "scope_id": SCOPE,
    "verification_kind": "TEST_SUITE",
    "dependencies": {},
    "preconditions": {},
}
CONTEXT = {"dependencies": {}, "preconditions": {}}

# evaluate() requires these for TEST_SUITE; their presence is what makes the
# evidence real rather than a boolean in a dict.
REQUIRED_EVIDENCE = (
    "test_count",
    "returncode",
    "measurement_program_sha256",
    "measurement_spec_sha256",
    "snapshot_sha256",
)


class GenuineSuiteGateTest(unittest.TestCase):
    """One real project per test, built in a temp dir and thrown away."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = pathlib.Path(self._tmp.name) / "proj"
        root.mkdir()
        (root / "bounds.py").write_text(BUGGY, encoding="utf-8")
        (root / "test_bounds.py").write_text(TEST_SRC, encoding="utf-8")
        self.root = root
        self.oracle = ProjectTestOracle(root, "bounds.py", ["test_bounds.py"], SCOPE)

    def test_a_failing_baseline_is_real_evidence_not_a_false_flag(self):
        """The buggy module must genuinely run tests and genuinely lose."""
        result = self.oracle(BUGGY)
        evidence = dict(result.evidence or {})

        self.assertIs(result.passed, False)
        self.assertEqual(result.kind, "TEST_SUITE")
        self.assertEqual(result.scope_id, SCOPE)
        # test_count > 0 and returncode != 0 together mean the suite executed and
        # failed. Without both, "failed" could mean "no tests were found".
        self.assertGreater(evidence.get("test_count", 0), 0)
        self.assertNotEqual(evidence.get("returncode"), 0)
        self.assertEqual(result.candidate_sha256, source_sha256(BUGGY))
        for field in REQUIRED_EVIDENCE:
            self.assertIn(field, evidence, f"missing real evidence field {field}")

    def test_the_fix_passes_the_same_real_suite(self):
        """Guard against an oracle that refuses everything, which would also pass
        the refusal assertions below while proving nothing."""
        result = self.oracle(FIXED)
        self.assertIs(result.passed, True)
        self.assertEqual(result.kind, "TEST_SUITE")
        self.assertGreater(dict(result.evidence or {}).get("test_count", 0), 0)
        self.assertEqual(dict(result.evidence or {}).get("returncode"), 0)

    def test_the_gate_admits_real_evidence_at_test_suite(self):
        self.assertIsNotNone(evaluate(self.oracle, FIXED, "TEST_SUITE", SCOPE))

    def test_a_bool_callback_cannot_claim_to_be_a_test_suite(self):
        """The load-bearing refusal. A callback that says True to everything is
        the weakest possible verifier; if it could satisfy TEST_SUITE, then every
        gate keyed on that kind would be decoration.

        The empty scope_id is the point, not an oversight. A bool is demoted to a
        CALLER_PREDICATE result whose scope_id is '', so passing a non-empty scope
        here would let the scope check do the refusing and this test would still
        pass with the kind gate deleted. Verified: neutering
        `if required_kind != 'CALLER_PREDICATE' and result.kind != required_kind`
        leaves the scoped assertion green and turns the unscoped one red. Only the
        unscoped call isolates the kind gate.
        """
        # unscoped: ONLY the kind-mismatch check can refuse this
        self.assertIsNone(evaluate(lambda candidate: True, FIXED, "TEST_SUITE", ""))
        # scoped as well, for defence in depth -- but see the docstring: on its own
        # this assertion does not pin the kind gate
        self.assertIsNone(evaluate(lambda candidate: True, FIXED, "TEST_SUITE", SCOPE))

    def test_a_candidate_that_compiles_and_is_wrong_is_refused(self):
        """The negative control that must exist before any generator does."""
        result = self.oracle(WRONG)
        self.assertIs(result.passed, False)
        self.assertNotEqual(dict(result.evidence or {}).get("returncode"), 0)
        self.assertIsNone(evaluate(self.oracle, WRONG, "TEST_SUITE", SCOPE))

    def test_a_scoped_lesson_is_taught_and_recalled_again_under_the_suite(self):
        """End to end through the public API: teach with the real oracle as the
        training verifier, then recall and confirm the applied patch is the fix
        and that its verification is genuine TEST_SUITE evidence."""
        store = K.VerifiedSkillStore(pathlib.Path(self._tmp.name) / "scoped.db", seed=False)

        taught = store.crystallize_code_fix(
            before_snippet=BUGGY,
            after_snippet=FIXED,
            language="python",
            error_class="BOUNDARY_EXCLUSIVE",
            contract=CONTRACT,
            training_verifier=self.oracle,
        )
        self.assertTrue(taught.get("crystallized"), taught.get("reason"))

        recalled = store.recall_and_apply_verified(
            source_text=BUGGY,
            language="python",
            verifier=self.oracle,
            error_class="BOUNDARY_EXCLUSIVE",
            required_verification_kind="TEST_SUITE",
            scope_id=SCOPE,
            context=CONTEXT,
        )
        self.assertIsNotNone(recalled)
        self.assertEqual(recalled.get("patched_source"), FIXED)
        verification = recalled.get("verification") or {}
        self.assertEqual(verification.get("kind"), "TEST_SUITE")
        self.assertGreater(dict(verification.get("evidence") or {}).get("test_count", 0), 0)
        # A passed suite for one file is not proof about the whole request. The
        # store says so itself, and this keeps it honest.
        self.assertIs(recalled.get("whole_task_correctness_proved"), False)

    def test_a_wrong_candidate_is_not_recalled_as_a_fix(self):
        """Recall must not hand back a rewrite just because a rule matched and the
        caller asked for TEST_SUITE. The verifier is the precision mechanism, so
        this asserts it is load-bearing on the recall path and not only inside
        evaluate().

        The weak verifier here returns a VerificationResult with the CORRECT scope
        but predicate grade. That is deliberate. A plain bool would be refused by
        the scope check instead -- evaluate() demotes a bool to scope_id='', and
        this recall is scoped -- so a bool would leave this test green with the
        kind gate deleted. Right scope, wrong kind, means only
        `result.kind != required_kind` can refuse it.

        UPDATED 2026-11-03: `allow_simulated_oracle=True` is now required here,
        because a TEST_SUITE *declaration* backed by a non-contract callable is
        refused outright by the provenance gate (pinned by
        `test_a_declared_test_suite_needs_a_contract_oracle_v1.py`). Without the
        flag this call raises and the kind check never runs, so the assertion
        would go green while pinning nothing. The assertion itself is unchanged.
        """
        store = K.VerifiedSkillStore(pathlib.Path(self._tmp.name) / "wrong.db", seed=False)
        store.crystallize_code_fix(
            before_snippet=BUGGY,
            after_snippet=FIXED,
            language="python",
            error_class="BOUNDARY_EXCLUSIVE",
            contract=CONTRACT,
            training_verifier=self.oracle,
        )

        def predicate_grade_only(candidate):
            return VerificationResult(
                True, "CALLER_PREDICATE", source_sha256(candidate), SCOPE, {})

        weak = store.recall_and_apply_verified(
            source_text=BUGGY,
            language="python",
            verifier=predicate_grade_only,
            error_class="BOUNDARY_EXCLUSIVE",
            required_verification_kind="TEST_SUITE",
            scope_id=SCOPE,
            context=CONTEXT,
            allow_simulated_oracle=True,
        )
        self.assertIsNone(weak)


if __name__ == "__main__":
    unittest.main()
