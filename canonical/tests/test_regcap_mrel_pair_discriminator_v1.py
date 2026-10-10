from __future__ import annotations

import unittest

from canonical.runtime import regcap_mrel_pair_discriminator_v1 as pair
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel


def fake_projection(pack):
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": sorted(
                str(row["fragment_id"]) for row in pack.get("fragments", [])
            ),
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


def span(text):
    surface = "loss-absorbing cushion"
    start = text.index(surface)
    return start, start + len(surface)


class Tests(unittest.TestCase):
    def test_ccob_mrel_authority_is_pair_scoped(self):
        out = pair.verify_authority(
            pair.CCOB_MREL,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["candidate_domain"]),
            {regcap.CCOB, mrel.MREL},
        )
        self.assertTrue(out["candidate_universe_complete"])
        self.assertFalse(out["open_world_ontology_complete"])
        self.assertFalse(out["concept_disjointness_authority"])

    def test_ccyb_mrel_authority_is_pair_scoped(self):
        out = pair.verify_authority(
            pair.CCYB_MREL,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["candidate_domain"]),
            {regcap.CCYB, mrel.MREL},
        )

    def test_ccob_structural_context_selects_ccob_in_pair(self):
        text = (
            "The loss-absorbing cushion is a 2.5% CET1 layer "
            "above the regulatory minimum capital requirement."
        )
        start, end = span(text)
        out = pair.resolve_relative(
            text,
            source_id="doc:ccob",
            start=start,
            end=end,
            pair_id=pair.CCOB_MREL,
            candidate_concept_ids=[regcap.CCOB, mrel.MREL],
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["relative_selection_authority"])
        self.assertEqual(out["selected_concept_id"], regcap.CCOB)
        self.assertFalse(out["global_semantic_identity_authority"])

    def test_ccyb_release_context_selects_ccyb_in_pair(self):
        text = (
            "The loss-absorbing cushion is released when system-wide risk "
            "crystallises or dissipates."
        )
        start, end = span(text)
        out = pair.resolve_relative(
            text,
            source_id="doc:ccyb",
            start=start,
            end=end,
            pair_id=pair.CCYB_MREL,
            candidate_concept_ids=[regcap.CCYB, mrel.MREL],
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.CCYB)

    def test_ccyb_extension_context_selects_ccyb_in_pair(self):
        text = (
            "The loss-absorbing cushion extends the size of the capital "
            "conservation buffer and is met with CET1."
        )
        start, end = span(text)
        out = pair.resolve_relative(
            text,
            source_id="doc:ccyb2",
            start=start,
            end=end,
            pair_id=pair.CCYB_MREL,
            candidate_concept_ids=[regcap.CCYB, mrel.MREL],
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.CCYB)

    def test_mrel_context_selects_mrel_against_ccob(self):
        text = (
            "The loss-absorbing cushion is the minimum requirement for own "
            "funds and eligible liabilities and is determined by the "
            "resolution authority."
        )
        start, end = span(text)
        out = pair.resolve_relative(
            text,
            source_id="doc:mrel1",
            start=start,
            end=end,
            pair_id=pair.CCOB_MREL,
            candidate_concept_ids=[regcap.CCOB, mrel.MREL],
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], mrel.MREL)

    def test_mrel_context_selects_mrel_against_ccyb(self):
        text = (
            "The loss-absorbing cushion is the minimum requirement for own "
            "funds and eligible liabilities and is determined by the "
            "resolution authority."
        )
        start, end = span(text)
        out = pair.resolve_relative(
            text,
            source_id="doc:mrel2",
            start=start,
            end=end,
            pair_id=pair.CCYB_MREL,
            candidate_concept_ids=[regcap.CCYB, mrel.MREL],
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], mrel.MREL)

    def test_shared_loss_absorption_only_stays_open(self):
        text = "The loss-absorbing cushion protects the institution."
        start, end = span(text)
        out = pair.resolve_relative(
            text,
            source_id="doc:open",
            start=start,
            end=end,
            pair_id=pair.CCOB_MREL,
            candidate_concept_ids=[regcap.CCOB, mrel.MREL],
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__NO_BOUND_PAIR_CONTEXT_SIGNATURE")
        self.assertFalse(out["relative_selection_authority"])

    def test_mixed_ccob_and_mrel_markers_fail_closed(self):
        text = (
            "The loss-absorbing cushion is a 2.5% CET1 layer above the "
            "regulatory minimum capital requirement and is the minimum "
            "requirement for own funds and eligible liabilities and is "
            "determined by the resolution authority."
        )
        start, end = span(text)
        out = pair.resolve_relative(
            text,
            source_id="doc:mixed",
            start=start,
            end=end,
            pair_id=pair.CCOB_MREL,
            candidate_concept_ids=[regcap.CCOB, mrel.MREL],
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CONFLICTING_PAIR_CONTEXT_SIGNATURES")

    def test_wrong_pair_candidate_set_fails_closed(self):
        text = (
            "The loss-absorbing cushion is released when system-wide risk "
            "crystallises or dissipates."
        )
        start, end = span(text)
        out = pair.resolve_relative(
            text,
            source_id="doc:badpair",
            start=start,
            end=end,
            pair_id=pair.CCYB_MREL,
            candidate_concept_ids=[regcap.CCOB, mrel.MREL],
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CANDIDATE_SET_MUST_EQUAL_BOUND_PAIR")

    def test_source_authority_failure_fails_closed(self):
        out = pair.verify_authority(
            pair.CCOB_MREL,
            projection_verifier=lambda _pack: {"pass": False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SOURCE_AUTHORITY_FAILED", out["reason"])

    def test_no_terminal_or_global_identity_authority(self):
        text = (
            "The loss-absorbing cushion is released when system-wide risk "
            "crystallises or dissipates."
        )
        start, end = span(text)
        out = pair.resolve_relative(
            text,
            source_id="doc:ccyb3",
            start=start,
            end=end,
            pair_id=pair.CCYB_MREL,
            candidate_concept_ids=[regcap.CCYB, mrel.MREL],
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["global_semantic_identity_authority"])
        self.assertFalse(out["concept_equivalence_authority"])
        self.assertFalse(out["concept_disjointness_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
