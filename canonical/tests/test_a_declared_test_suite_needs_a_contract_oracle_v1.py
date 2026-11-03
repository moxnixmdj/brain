"""A declared TEST_SUITE is not a TEST_SUITE capability.

WHY THIS TEST EXISTS
  `recall_and_apply_verified` only generates *broadened* candidate patterns
  (sub-expression narrowing, minimal CST subtrees, operator/semantic swaps,
  cross-language carry) when the caller declares `required_verification_kind ==
  'TEST_SUITE'`. Measured 2026-11-03 (`OPTIMAL_PLAN_20261103_V7.md` §0.1-0.2):
  broadening lifts recall from 4/7 to 6/6 under a real suite and, in the same
  probe, rewrites 3 of 4 sources where `<=` was CORRECT under a weak callback.
  So the safety of the whole broadening surface reduces to one question:

      can a caller obtain TEST_SUITE grading by *saying* TEST_SUITE?

  Before this change, yes: any callable returning a `VerificationResult` whose
  `kind` was 'TEST_SUITE' satisfied the gate, including a stub with fabricated
  evidence fields. This file pins that it is now refused.

WHAT MAKES THESE TESTS MEAN SOMETHING
  A gate test is worthless if it can stay green with the gate deleted. Each
  assertion below names the single check that must be doing the refusing:

    - a hand-written verifier that returns a *perfectly well-formed*
      TEST_SUITE result is refused. Deleting `TEST_SUITE_REQUIRES_CONTRACT_ORACLE`
      makes it profitably dispatch a broadened candidate.
    - a real `ProjectTestOracle` is admitted and DOES record the broadened
      tier, so the gate is not a "refuse everything" stub.
    - a class merely *named* `ProjectTestOracle` is refused, so provenance is
      not duck-typed by name.
    - a simulated oracle may judge, but may not widen: it receives only the
      context-anchored pattern, exactly as the weak-verifier control requires.

Authority: NONE. This is a negative-control test, not a capability claim.
"""
import pathlib
import tempfile
import textwrap
import unittest

from canonical.swe_kernel import verified_skill_crystallizer_v1 as K
from canonical.swe_kernel.skill_verification_contract_v1 import (
    CONTRACT_ORACLE_CLASSES,
    ORACLE_PROVENANCE_ATTR,
    ProjectTestOracle,
    VerificationResult,
    is_contract_oracle,
    mark_contract_oracle,
    source_sha256,
)

SCOPE = "provenance/exclusive-boundary/v1"
CONTRACT = {
    "schema_version": 1,
    "scope_id": SCOPE,
    "verification_kind": "TEST_SUITE",
    "dependencies": {"protocol": "1"},
    "preconditions": {"role": "boundary"},
}
CONTEXT = {"dependencies": {"protocol": "1"}, "preconditions": {"role": "boundary"}}

BUGGY = "def within(x, hi):\n    return x <= hi\n"
FIXED = "def within(x, hi):\n    return x < hi\n"

# Taught in a `return` statement; the FIRST case can only be reached by widening
# past the statement's leading keyword, so "did it dispatch a candidate at all?"
# is a direct observation of whether broadening was permitted.
NOVEL_IF = "def target(x, hi):\n    if x <= hi:\n        return True\n    return False\n"
NOVEL_FIXED_IF = "def target(x, hi):\n    if x < hi:\n        return True\n    return False\n"

SUITE = textwrap.dedent(
    """\
    import unittest
    from subject import {fn}
    class Checks(unittest.TestCase):
        def test_boundary(self):
            for x in range(-8, 9):
                for hi in range(-8, 9):
                    self.assertEqual({fn}(x, hi), {expr})
    """
)


def _project(root: pathlib.Path, source: str, fn: str, expr: str) -> pathlib.Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "subject.py").write_text(source, encoding="utf-8")
    (root / "test_subject.py").write_text(SUITE.format(fn=fn, expr=expr), encoding="utf-8")
    return root


class DeclaredTestSuiteNeedsAContractOracle(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = pathlib.Path(self._tmp.name)
        train = _project(self.base / "train", BUGGY, "within", "x < hi")
        self.store = K.VerifiedSkillStore(self.base / "skills.sqlite", seed=False)
        taught = self.store.crystallize_code_fix(
            before_snippet=BUGGY,
            after_snippet=FIXED,
            language="python",
            error_class="BOUNDARY",
            contract=CONTRACT,
            training_verifier=ProjectTestOracle(train, "subject.py", ["test_subject.py"], SCOPE),
        )
        self.assertTrue(taught.get("crystallized"), taught)
        self.novel = _project(self.base / "novel", NOVEL_IF, "target", "x < hi")

    def _oracle(self) -> ProjectTestOracle:
        return ProjectTestOracle(self.novel, "subject.py", ["test_subject.py"], SCOPE)

    # ---------------------------------------------------------------- refusals
    def test_a_well_formed_forged_test_suite_result_is_refused(self):
        """The forgery is *perfect*: right kind, right scope, right hash, real-looking
        evidence. Only its provenance is wrong, so only provenance can refuse it."""

        def forged(candidate):
            return VerificationResult(
                True,
                "TEST_SUITE",
                source_sha256(candidate),
                SCOPE,
                {
                    "test_count": 1,
                    "returncode": 0,
                    "measurement_program_sha256": "00" * 32,
                    "measurement_spec_sha256": "11" * 32,
                    "snapshot_sha256": "22" * 32,
                },
            )

        self.assertFalse(is_contract_oracle(forged))
        with self.assertRaisesRegex(ValueError, "TEST_SUITE_REQUIRES_CONTRACT_ORACLE"):
            self.store.recall_and_apply_verified(
                source_text=NOVEL_IF,
                language="python",
                verifier=forged,
                error_class="BOUNDARY",
                required_verification_kind="TEST_SUITE",
                scope_id=SCOPE,
                context=CONTEXT,
            )

    def test_broadening_flags_cannot_be_bought_with_a_declaration(self):
        """Even without asking for TEST_SUITE, you may not turn broadening on
        while holding a non-contract verifier."""
        with self.assertRaisesRegex(ValueError, "PATTERN_BROADENING_REQUIRES_CONTRACT_ORACLE"):
            self.store.recall_and_apply_verified(
                source_text=NOVEL_IF,
                language="python",
                verifier=lambda candidate: True,
                error_class="BOUNDARY",
                required_verification_kind="TEST_SUITE",
                scope_id=SCOPE,
                context=CONTEXT,
                allow_scope_escalation=True,
                allow_simulated_oracle=True,
            )

    def test_a_class_that_only_shares_the_name_is_refused(self):
        """Provenance must not be duck-typed. A same-named class carrying the marker
        flag is still not the contract oracle, so no laundering by naming."""

        class ProjectTestOracle:  # noqa: N801 - the name is the attack
            def __call__(self, candidate):
                return VerificationResult(True, "TEST_SUITE", source_sha256(candidate), SCOPE, {
                    "test_count": 1, "returncode": 0,
                    "measurement_program_sha256": "00" * 32,
                    "measurement_spec_sha256": "11" * 32,
                    "snapshot_sha256": "22" * 32,
                })

        impostor = ProjectTestOracle()
        with self.assertRaisesRegex(ValueError, "NOT_A_CONTRACT_ORACLE_CLASS"):
            mark_contract_oracle(impostor)
        # A hand-copied marker, of either shape, must still fail.
        setattr(impostor, ORACLE_PROVENANCE_ATTR, True)
        self.assertFalse(is_contract_oracle(impostor))
        setattr(impostor, ORACLE_PROVENANCE_ATTR, type(impostor))
        self.assertFalse(is_contract_oracle(impostor),
                         "a same-named class in another module is not this oracle")
        with self.assertRaisesRegex(ValueError, "TEST_SUITE_REQUIRES_CONTRACT_ORACLE"):
            self.store.recall_and_apply_verified(
                source_text=NOVEL_IF,
                language="python",
                verifier=impostor,
                error_class="BOUNDARY",
                required_verification_kind="TEST_SUITE",
                scope_id=SCOPE,
                context=CONTEXT,
            )

    def test_an_unmarked_contract_oracle_subclass_instance_is_refused(self):
        """The marker is set by construction. Removing it disables the gate's
        acceptance, which is what makes the acceptance below meaningful."""

        oracle = self._oracle()
        self.assertTrue(is_contract_oracle(oracle), "construction must mark the oracle")
        delattr(oracle, ORACLE_PROVENANCE_ATTR)
        self.assertFalse(is_contract_oracle(oracle), "unmarked means unprovenanced")
        mark_contract_oracle(oracle)
        self.assertTrue(is_contract_oracle(oracle))

    # -------------------------------------------------------------- acceptance
    def test_a_real_contract_oracle_is_admitted_and_reaches_the_novel_shape(self):
        """The gate is not "refuse everything": with a genuine oracle the same
        store reaches the shape that context-anchored matching cannot."""
        direct = K.apply_crystallized_code_rule(
            NOVEL_IF, self.store.lookup_rules("python", "BOUNDARY")[0]
        )
        self.assertIsNone(direct, "precondition: statement-anchored matching must miss")

        hit = self.store.recall_and_apply_verified(
            source_text=NOVEL_IF,
            language="python",
            verifier=self._oracle(),
            error_class="BOUNDARY",
            required_verification_kind="TEST_SUITE",
            scope_id=SCOPE,
            context=CONTEXT,
        )
        self.assertIsNotNone(hit)
        self.assertEqual(hit["patched_source"], NOVEL_FIXED_IF)
        self.assertEqual(hit["scope_tier"], "SCOPE_EXPRESSION")
        self.assertIn(hit["recall_strategy"], {"narrowed_pattern", "cst_minimal_subtree"})
        self.assertIs(hit["whole_task_correctness_proved"], False)

    def test_a_simulated_oracle_may_judge_but_may_not_widen(self):
        """The escape hatch is honest: it buys dispatch of the *context-anchored*
        pattern only. It must never see a broadened candidate."""
        seen: list[str] = []

        def stub(candidate):
            seen.append(candidate)
            return True

        hit = self.store.recall_and_apply_verified(
            source_text=NOVEL_IF,
            language="python",
            verifier=stub,
            error_class="BOUNDARY",
            required_verification_kind="TEST_SUITE",
            scope_id=SCOPE,
            context=CONTEXT,
            allow_simulated_oracle=True,
        )
        self.assertIsNone(hit, "the novel shape is only reachable by widening")
        self.assertEqual(seen, [], "a simulated oracle must receive no candidate at all")


if __name__ == "__main__":
    unittest.main()
