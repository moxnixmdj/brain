#!/usr/bin/env python3
"""Effect-carrying skill contracts — the three barriers and the measured no-op pair.

The first test is the measured defect itself (`SKILLS_DONT_COMPOSE_20261112_V1.md`),
refused at the CONTRACT layer (declared effects only — no state, no sequence check,
no history check). The pass condition from
`WHAT_IS_REAL_AND_THE_ONE_CLASS_OF_PAGE_20261117_V1.md` §9 rank-2:

  Pass: the known no-op pair is refused by the contract, not by the sequence check.
  Fail: a contract that accepts the pair.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from canonical.swe_kernel import effect_contract_composition_v1 as E

REPO = pathlib.Path(__file__).resolve().parents[2]


class TestMeasuredNoOpPair(unittest.TestCase):
    """The measured defect — refused by the CONTRACT, not by sequence/history."""

    def test_measured_no_op_pair_is_refused_by_the_contract(self):
        a, b = E.measured_no_op_pair()
        outcome = E.compose_contracts(a, b)

        self.assertEqual(outcome["verdict"], E.UNDO)
        self.assertEqual(
            outcome["reason"],
            "B_LOOSEN_LT_TO_LE:EFFECT_UNDO_OF_A_TIGHTEN_LE_TO_LT",
        )
        self.assertEqual(outcome["checks"]["complete_a"], "PASS")
        self.assertEqual(outcome["checks"]["complete_b"], "PASS")
        # B's P is established by A — coverage passes; undo is what refuses.
        self.assertEqual(outcome["checks"]["coverage"], "PASS")
        self.assertEqual(outcome["checks"]["undo"], E.UNDO)
        # The contract layer never touched a state or a sequence.
        self.assertNotIn("steps", outcome)
        self.assertNotIn("result", outcome)
        self.assertEqual(outcome["model_dependency_count"], 0)

    def test_no_op_pair_refusal_does_not_need_the_sequence_instrument(self):
        """The refusal is fully determined by declared effects alone."""
        a, b = E.measured_no_op_pair()
        self.assertIsNotNone(E.check_undo(a, b))
        outcome = E.compose_contracts(a, b)
        self.assertEqual(outcome["verdict"], E.UNDO)


class TestAdvanceAndChains(unittest.TestCase):
    """A genuine advance must stay compatible (fail condition of a strict rule)."""

    def test_advance_pair_is_contract_compatible(self):
        a, c = E.measured_advance_pair()
        outcome = E.compose_contracts(a, c)

        self.assertEqual(outcome["verdict"], E.PASS, outcome)
        self.assertEqual(outcome["checks"]["coverage"], "PASS")
        self.assertEqual(outcome["checks"]["undo"], "PASS")
        # C removes what A established but does NOT restore what A removed.
        self.assertFalse(
            c.established() >= a.removed() and c.removed() >= a.established()
        )

    def test_chain_of_compatible_skills_passes(self):
        a, c = E.measured_advance_pair()
        outcome = E.compose_chain([a, c])
        self.assertEqual(outcome["verdict"], E.PASS)
        self.assertEqual(outcome["reason"], "CHAIN_COMPATIBLE")

    def test_chain_stops_at_the_no_op_pair(self):
        a, b = E.measured_no_op_pair()
        outcome = E.compose_chain([a, b])
        self.assertEqual(outcome["verdict"], E.UNDO)
        self.assertEqual(outcome["refused_at_pair"], 1)


class TestBarrierVocabulary(unittest.TestCase):
    """Barrier 1 — missing observables is refused."""

    def test_missing_observables_is_refused_as_vocabulary_barrier(self):
        no_obs = E.EffectContract.of(
            "NO_OBS",
            preconditions=(),
            observables=(),
            actions=("replace",),
            verdict="pytest",
            effects=(("ESTABLISH", "x"),),
        )
        a, _ = E.measured_no_op_pair()
        outcome = E.compose_contracts(no_obs, a)
        self.assertEqual(outcome["verdict"], E.NO_OBSERVABLES)
        self.assertIn("NO_OBSERVABLES", outcome["reason"])


class TestBarrierIdentifiability(unittest.TestCase):
    """Barrier 2 — a non-separating verdict is refused."""

    def test_non_separating_verdict_is_refused(self):
        for bad in ("self", "always_pass", "majority_vote",
                    "screen", "stdout", "truthiness", ""):
            with self.subTest(verdict=bad):
                weak = E.EffectContract.of(
                    "WEAK",
                    preconditions=(),
                    observables=("source",),
                    actions=("replace",),
                    verdict=bad,
                    effects=(("ESTABLISH", "x"),),
                )
                a, _ = E.measured_no_op_pair()
                outcome = E.compose_contracts(a, weak)
                self.assertEqual(outcome["verdict"], E.NO_VERDICT)


class TestBarrierSynthesisVerification(unittest.TestCase):
    """Barrier 3 — precondition not established by prior F."""

    def test_unmet_precondition_is_refused(self):
        a, _ = E.measured_no_op_pair()
        needy = E.EffectContract.of(
            "NEEDS_SOMETHING_ELSE",
            preconditions=("comparator:<:99",),  # A does not establish this
            observables=("source",),
            actions=("replace",),
            verdict="pytest",
            effects=(("ESTABLISH", "other"),),
        )
        outcome = E.compose_contracts(a, needy)
        self.assertEqual(outcome["verdict"], E.PRECONDITION_UNMET)
        self.assertIn("comparator:<:99", outcome["reason"])

    def test_shared_axiom_precondition_does_not_require_establishment(self):
        a, _ = E.measured_no_op_pair()
        twin = E.EffectContract.of(
            "TWIN_AXIOM",
            preconditions=("comparator:<=:10",),  # same as A's own precondition
            observables=("source",),
            actions=("replace",),
            verdict="pytest",
            effects=(("ESTABLISH", "unrelated"),),
        )
        outcome = E.compose_contracts(a, twin)
        self.assertEqual(outcome["verdict"], E.PASS, outcome)


class TestReceiptsAndIntegrity(unittest.TestCase):
    def test_receipts_are_zero_model_and_carry_digests(self):
        a, b = E.measured_no_op_pair()
        outcome = E.compose_contracts(a, b)
        self.assertEqual(outcome["model_dependency_count"], 0)
        self.assertEqual(outcome["network_calls_at_run_time"], 0)
        self.assertTrue(outcome["a_sha256"])
        self.assertTrue(outcome["b_sha256"])
        self.assertNotEqual(outcome["a_sha256"], outcome["b_sha256"])

    def test_effect_kinds_are_closed(self):
        with self.assertRaisesRegex(ValueError, "EFFECT_KIND_UNSUPPORTED"):
            E.Effect("TELEPORT", "x")
        with self.assertRaisesRegex(ValueError, "EFFECT_SUBJECT_REQUIRED"):
            E.Effect("ESTABLISH", "")

    def test_audit_folds_from_the_measured_pairs(self):
        """The CLI receipt: no-op refused, advance compatible, barriers fire, audit_pass."""
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / "receipt.json"
            done = subprocess.run(
                [sys.executable,
                 str(REPO / "canonical/swe_kernel/effect_contract_composition_v1.py"),
                 "--out", str(out)],
                capture_output=True, text=True, cwd=str(REPO), timeout=60,
            )
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            receipt = json.loads(out.read_text())
        self.assertTrue(receipt["audit_pass"])
        s = receipt["summary"]
        self.assertTrue(s["no_op_pair_refused_by_contract"])
        self.assertTrue(s["advance_pair_compatible"])
        self.assertTrue(s["weak_verdict_refused"])
        self.assertTrue(s["missing_observables_refused"])
        self.assertTrue(s["contract_layer_did_not_run_sequence_or_history"])
        self.assertTrue(s["all_three_instruments_refuse_no_op"])
        self.assertTrue(s["all_three_instruments_pass_advance"])
        self.assertEqual(receipt["model_dependency_count"], 0)
        # Each instrument refused under its own name.
        cross = receipt["cross_instrument"]["no_op"]
        self.assertNotEqual(cross["sequence"]["verdict"], "PASS")
        self.assertEqual(cross["proved_composition"]["verdict"], "STEP_REVERTED_EARLIER_STATE")
        self.assertEqual(cross["contract"]["verdict"], E.UNDO)


if __name__ == "__main__":
    unittest.main()
