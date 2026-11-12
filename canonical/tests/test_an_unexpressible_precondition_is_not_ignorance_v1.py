#!/usr/bin/env python3
"""Teeth for the wall behind "show it once and it learns permanently".

Measured on real producer output: two directories with IDENTICAL sensed facts gave opposite real
outcomes, because the cause (a `.docx.intent.json` sidecar) has no fact in the sensor's vocabulary.
Twenty extra real runs changed nothing. The learner answered INCONSISTENT, which has no survivors,
so the plan was still OFFERED in the world where it had just failed and nothing said why.

These tests protect: the witness is produced; admission behaviour is NOT changed (withholding on
undetermined evidence is the ban this store has met four times); and a discovered observable is a
generalisable KIND that survives renamed held-out worlds, never a fingerprint of one filename.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.runtime import applicability_v1 as APP
from canonical.runtime import chain_v1 as C
from canonical.runtime import macro_v1 as MC
from canonical.runtime import precondition_discovery_v1 as PD

SIDECAR = "docx.intent_sidecar.available"
SHARED = frozenset({"manifest.json.available", "structured.json.available"})


class TheGapIsWitnessedNotGuessed(unittest.TestCase):
    def test_equal_states_with_opposite_outcomes_produce_a_witness(self):
        gap = APP.vocabulary_gap([(SHARED, True), (SHARED, False)])
        self.assertIsNotNone(gap)
        self.assertEqual(gap["kind"], "SAME_OBSERVED_STATE_OPPOSITE_OUTCOMES")
        self.assertEqual(gap["facts"], sorted(SHARED))
        self.assertEqual(gap["outcomes"], [False, True])

    def test_different_states_with_opposite_outcomes_are_not_a_gap(self):
        # That is an ordinary, learnable contrast -- the vocabulary is doing its job.
        self.assertIsNone(APP.vocabulary_gap([(SHARED | {SIDECAR}, True), (SHARED, False)]))

    def test_sparse_evidence_is_not_a_gap(self):
        self.assertIsNone(APP.vocabulary_gap([]))
        self.assertIsNone(APP.vocabulary_gap([(SHARED, True)]))
        self.assertIsNone(APP.vocabulary_gap([(SHARED, False), (frozenset(), False)]))

    def test_repetition_cannot_clear_the_gap(self):
        rows = [(SHARED, True), (SHARED, False)] * 25
        self.assertIsNotNone(APP.vocabulary_gap(rows))
        self.assertEqual(APP.learn(rows).status, APP.INCONSISTENT)

    def test_the_gap_does_not_change_admission(self):
        # The load-bearing refusal: no survivors means never withhold. A gap must not become a ban.
        boundary = APP.learn([(SHARED, True), (SHARED, False)])
        self.assertEqual(boundary.status, APP.INCONSISTENT)
        self.assertFalse(APP.explains_failure(boundary, SHARED))
        self.assertFalse(APP.explains_failure(boundary, frozenset()))

    def test_the_store_reader_and_the_pure_function_agree(self):
        with tempfile.TemporaryDirectory() as tmp:
            state, saved = MC.STATE, MC.STATE.read_bytes() if MC.STATE.is_file() else None
            try:
                MC.STATE = Path(tmp) / "m.json"
                clauses = ["verify the docx a.docx", "create a tar.gz archive from the manifest"]
                key = MC.signature(clauses)
                steps = [{"capability_id": "x.one", "verified": True},
                         {"capability_id": "x.two", "verified": True}]
                MC.record(clauses, steps, context=SHARED)
                MC.note_failure(key, context=SHARED)
                direct = APP.vocabulary_gap(MC._evidence_rows(
                    (MC._load().get("macros") or {}).get(key) or {}))
                self.assertEqual(MC.vocabulary_gap(key), direct)
                self.assertIsNotNone(MC.vocabulary_gap(key))
                self.assertTrue(MC.applicable(key, SHARED), "a gap must not ban the plan")
            finally:
                MC.STATE = state
                if saved is not None:
                    state.write_bytes(saved)

    def test_an_unknown_key_has_no_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            state, saved = MC.STATE, MC.STATE.read_bytes() if MC.STATE.is_file() else None
            try:
                MC.STATE = Path(tmp) / "m.json"
                self.assertIsNone(MC.vocabulary_gap("never.recorded.key"))
                self.assertIsNone(MC.vocabulary_gap(""))
            finally:
                MC.STATE = state
                if saved is not None:
                    state.write_bytes(saved)

    def test_the_live_path_reports_the_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            state, saved = MC.STATE, MC.STATE.read_bytes() if MC.STATE.is_file() else None
            try:
                MC.STATE = Path(tmp) / "m.json"
                goal = ("verify the docx canonical/astra_runtime/tmp/DOCX_INTENT_VERIFY.docx "
                        "and create a tar.gz archive from the manifest")
                result = C.run(goal, memory=True)
                self.assertIn("vocabulary_gap", result)
            finally:
                MC.STATE = state
                if saved is not None:
                    state.write_bytes(saved)


class ADiscoveredObservableMustBeAKind(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _world(self, name, *, doc="REPORT", sidecar):
        root = self.base / name
        (root / "sub").mkdir(parents=True, exist_ok=True)
        (root / "sub" / (doc + ".docx")).write_bytes(b"x")
        (root / "manifest.json").write_text("{}", encoding="utf-8")
        if sidecar:
            (root / "sub" / (doc + ".docx.intent.json")).write_text("{}", encoding="utf-8")
        return root

    def test_the_shortest_separating_suffix_is_chosen(self):
        good = self._world("good", sidecar=True)
        bad = self._world("bad", sidecar=False)
        found = PD.discover([good], [bad])
        self.assertTrue(found.found)
        self.assertEqual(found.suffix, ".intent.json",
                         "a longer suffix would fit too but generalise less")

    def test_a_filename_fingerprint_is_never_offered(self):
        good = self._world("good", doc="UNIQUE_REPORT_NAME", sidecar=True)
        bad = self._world("bad", doc="UNIQUE_REPORT_NAME", sidecar=False)
        found = PD.discover([good], [bad])
        self.assertTrue(found.found)
        self.assertNotIn("unique_report_name", found.suffix)

    def test_a_suffix_that_fails_a_renamed_held_out_world_is_rejected(self):
        good = self._world("good", sidecar=True)
        bad = self._world("bad", sidecar=False)
        # Held-out "success" world has no sidecar at all: no honest suffix can pass.
        ho = self._world("ho", doc="OTHER", sidecar=False)
        found = PD.discover([good], [bad], held_out_success=[ho])
        self.assertFalse(found.found)
        self.assertEqual(found.status, PD.NO_CANDIDATE)
        self.assertTrue(any(not r["correct"] for r in found.verified_on),
                        "the rejected candidate must show WHICH world falsified it")

    def test_renamed_held_out_worlds_are_survived(self):
        good = self._world("good", doc="ALPHA", sidecar=True)
        bad = self._world("bad", doc="ALPHA", sidecar=False)
        ho_good = self._world("ho_good", doc="BETA_RENAMED", sidecar=True)
        ho_bad = self._world("ho_bad", doc="GAMMA_RENAMED", sidecar=False)
        found = PD.discover([good], [bad],
                            held_out_success=[ho_good], held_out_failure=[ho_bad])
        self.assertTrue(found.found)
        self.assertTrue(all(r["correct"] for r in found.verified_on))
        self.assertEqual(len(found.verified_on), 4)

    def test_worlds_that_differ_by_nothing_observable_yield_no_candidate(self):
        good = self._world("good", sidecar=True)
        same = self._world("same", sidecar=True)
        found = PD.discover([good], [same])
        self.assertFalse(found.found)
        self.assertEqual(found.status, PD.NO_CANDIDATE)

    def test_both_classes_of_world_are_required(self):
        good = self._world("good", sidecar=True)
        self.assertEqual(PD.discover([good], []).status, PD.NO_WORLDS)
        self.assertEqual(PD.discover([], [good]).status, PD.NO_WORLDS)

    def test_the_observable_is_evaluated_against_the_real_directory(self):
        good = self._world("good", sidecar=True)
        bad = self._world("bad", sidecar=False)
        self.assertTrue(PD.holds(good, ".intent.json"))
        self.assertFalse(PD.holds(bad, ".intent.json"))
        (bad / "nested").mkdir()
        (bad / "nested" / "other.intent.json").write_text("{}", encoding="utf-8")
        self.assertTrue(PD.holds(bad, ".intent.json"),
                        "the observable must re-read the world, not remember it")


if __name__ == "__main__":
    unittest.main()
