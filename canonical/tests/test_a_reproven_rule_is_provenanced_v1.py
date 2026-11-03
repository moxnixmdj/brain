"""A rule that is re-proven by execution is provenanced — and only by execution.

WHY THIS TEST EXISTS
  `rule_expiry_v1` refuses to promote an unstamped rule out of `UNKNOWN`: only
  `reverify()` moves a rule to `FRESH`, and it needs the rule's own training
  example. Measured 2026-11-03 on a copy of the shipped store:

      rule_expiry_v1.audit -> {FRESH: 0, STALE: 0, UNKNOWN: 5}   (all five unstamped)

  and the shipped bundle's rule records carry no training example, so those five
  can never be re-verified. Meanwhile `recall_and_apply_verified` already *skips*
  `STALE` rules (it audits on every recall), and a successful recall incremented
  `verified_hits` without stamping anything. So the one event that genuinely
  establishes "this rule still reproduces here" — a real suite passing the
  patched source in this world — left no record, and a rule could be re-proven
  forever and stay permanently unprovenanced.

WHAT THIS PINS (both directions, because one direction proves nothing)
  1. A `TEST_SUITE` hit under a contract oracle stamps the world, and the stamp
     equals the world that actually judged the candidate.
  2. The stamp makes the existing skip *bite*: with a materially different world
     recorded, the same rule is `STALE` and is NOT served — so the new stamp is
     live, not decorative.
  3. A `CALLER_PREDICATE` hit does NOT stamp. Weak evidence must not launder
     itself into a freshness claim, and an `UNKNOWN` rule must stay `UNKNOWN`.
  4. A failed stamp cannot undo a proven fix: the hit is still returned.

Authority: NONE. This records an existing event; it grants no new capability.
"""
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import rule_expiry_v1 as E
from canonical.swe_kernel import verified_skill_crystallizer_v1 as K
from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle

SCOPE = "stamp/exclusive-boundary/v1"
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
SUITE = (
    "import unittest\n"
    "from subject import {fn}\n"
    "class Checks(unittest.TestCase):\n"
    "    def test_boundary(self):\n"
    "        for x in range(-8, 9):\n"
    "            for hi in range(-8, 9):\n"
    "                self.assertEqual({fn}(x, hi), {expr})\n"
)


def _project(root: pathlib.Path, source: str, fn: str, expr: str) -> pathlib.Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "subject.py").write_text(source, encoding="utf-8")
    (root / "test_subject.py").write_text(SUITE.format(fn=fn, expr=expr), encoding="utf-8")
    return root


def _other_world() -> dict:
    """A world that differs materially from this one, with an explicit reason."""
    world = dict(E.world_fingerprint())
    world["python_major_minor"] = "2.7"
    return world


class VerifiedHitStampsTheWorld(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = pathlib.Path(self._tmp.name)
        self.db = self.base / "skills.sqlite"
        train = _project(self.base / "train", BUGGY, "within", "x < hi")
        self.store = K.VerifiedSkillStore(self.db, seed=False)
        taught = self.store.crystallize_code_fix(
            before_snippet=BUGGY,
            after_snippet=FIXED,
            language="python",
            error_class="BOUNDARY",
            contract=CONTRACT,
            training_verifier=ProjectTestOracle(train, "subject.py", ["test_subject.py"], SCOPE),
        )
        self.assertTrue(taught.get("crystallized"), taught)
        self.skill_id = taught["skill_id"]
        self.target = _project(self.base / "target", BUGGY, "within", "x < hi")

    def _oracle(self):
        return ProjectTestOracle(self.target, "subject.py", ["test_subject.py"], SCOPE)

    def _recall(self, **kwargs):
        return self.store.recall_and_apply_verified(
            source_text=BUGGY,
            language="python",
            verifier=kwargs.pop("verifier", None) or self._oracle(),
            error_class="BOUNDARY",
            required_verification_kind=kwargs.pop("kind", "TEST_SUITE"),
            scope_id=kwargs.pop("scope_id", SCOPE),
            context=CONTEXT,
            **kwargs,
        )

    # ------------------------------------------------------------ 1. the stamp
    def test_a_test_suite_hit_records_the_world_that_judged_it(self):
        before = E.audit(self.db)
        self.assertEqual(before["rules"][0]["state"], E.UNKNOWN, "precondition: unstamped at first")

        hit = self._recall()
        self.assertIsNotNone(hit)
        stamp = hit["world_stamp"]
        self.assertTrue(stamp["stamped"], stamp)
        self.assertEqual(stamp["digest"], E._digest(E.world_fingerprint()))

        after = E.audit(self.db)
        self.assertEqual(after["rules"][0]["state"], E.FRESH, after)
        self.assertEqual(after["counts"]["UNKNOWN"], 0)

    # ------------------------------------- 2. the stamp makes the skip bite
    def test_a_stamp_from_another_world_makes_the_rule_stale_and_unserved(self):
        """Without a stamp this rule is UNKNOWN and served; with one it is STALE
        and skipped. That is the difference the change actually makes."""
        other = _other_world()
        self.store.recall_and_apply_verified(
            source_text=BUGGY,
            language="python",
            verifier=self._oracle(),
            error_class="BOUNDARY",
            required_verification_kind="TEST_SUITE",
            scope_id=SCOPE,
            context=CONTEXT,
            now_world_fingerprint=other,
        )
        audited = E.audit(self.db, now=other)
        self.assertEqual(audited["rules"][0]["state"], E.FRESH)
        audited_here = E.audit(self.db)
        self.assertEqual(audited_here["rules"][0]["state"], E.STALE, audited_here)

        oracle = self._oracle()
        hit = self.store.recall_and_apply_verified(
            source_text=BUGGY,
            language="python",
            verifier=oracle,
            error_class="BOUNDARY",
            required_verification_kind="TEST_SUITE",
            scope_id=SCOPE,
            context=CONTEXT,
        )
        self.assertIsNone(hit, "a rule proven in a different world must not be served here")
        self.assertEqual(oracle.calls, 0, "a stale rule must be skipped before the suite runs")

    # ------------------------------------ 3. weak evidence does not stamp
    def test_a_weak_verifier_hit_does_not_claim_freshness(self):
        """A contract-taught rule is never served at predicate grade, so this needs
        a legacy (contract-less) rule to exercise the weak path at all."""
        legacy_db = self.base / "legacy.sqlite"
        legacy = K.VerifiedSkillStore(legacy_db, seed=False)
        taught = legacy.crystallize_code_fix(
            before_snippet=BUGGY,
            after_snippet=FIXED,
            language="python",
            error_class="BOUNDARY",
            twin_oracle=lambda candidate: "<=" not in candidate and "<" in candidate,
        )
        self.assertTrue(taught.get("crystallized"), taught)

        hit = legacy.recall_and_apply_verified(
            source_text=BUGGY,
            language="python",
            verifier=lambda candidate: True,
            error_class="BOUNDARY",
            required_verification_kind="CALLER_PREDICATE",
        )
        self.assertIsNotNone(hit, "precondition: the weak path still recalls")
        self.assertEqual(hit["verification"]["kind"], "CALLER_PREDICATE")
        self.assertFalse(hit["world_stamp"]["stamped"])
        self.assertEqual(hit["world_stamp"]["reason"], "NOT_PROVEN_HERE")
        audited = E.audit(legacy_db)
        self.assertEqual(audited["rules"][0]["state"], E.UNKNOWN,
                         "a predicate-grade hit must leave the rule unprovenanced")

    # ------------------------------------ 4. a failed stamp cannot undo a fix
    def test_a_failed_stamp_still_returns_the_verified_fix(self):
        with mock.patch.object(E, "record_taught", side_effect=RuntimeError("disk gone")):
            hit = self._recall()
        self.assertIsNotNone(hit, "a proven fix must never be lost to a bookkeeping failure")
        self.assertEqual(hit["patched_source"].count("x < hi"), 1)
        self.assertFalse(hit["world_stamp"]["stamped"])
        self.assertIn("STAMP_FAILED", hit["world_stamp"]["reason"])


if __name__ == "__main__":
    unittest.main()
