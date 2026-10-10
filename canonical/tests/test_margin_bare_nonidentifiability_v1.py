from __future__ import annotations

from hashlib import sha256
import io
import json
import unittest
from unittest.mock import patch
import zipfile

from canonical.runtime import margin_bare_nonidentifiability_v1 as cert
from canonical.runtime import oewn_release_sense_universe_v1 as oewn


def build_zip(*, omit_profit=False, bad_profit_definition=False):
    senses = [
        {"id": cert.COLLATERAL_SENSE, "synset": cert.COLLATERAL_SYNSET},
    ]
    if not omit_profit:
        senses.append({"id": cert.PROFIT_SENSE, "synset": cert.PROFIT_SYNSET})
    entries = {"margin": {"n": {"sense": senses}}}
    noun = {
        cert.COLLATERAL_SYNSET: {
            "definition": [cert.COLLATERAL_DEFINITION],
            "members": ["margin", "security deposit"],
            "partOfSpeech": "n",
        },
    }
    if not omit_profit:
        noun[cert.PROFIT_SYNSET] = {
            "definition": [
                "tampered definition"
                if bad_profit_definition
                else cert.PROFIT_DEFINITION
            ],
            "members": ["margin", "gross profit margin"],
            "partOfSpeech": "n",
        }
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("entries-m.json", json.dumps(entries))
        zf.writestr("noun.possession.json", json.dumps(noun))
        zf.writestr("frames.json", "{}")
    return bio.getvalue()


def prove_fixture(source="Margin increased.", **zip_kwargs):
    raw = build_zip(**zip_kwargs)
    digest = sha256(raw).hexdigest()
    with patch.object(oewn, "RELEASE_SHA256", digest):
        return cert.prove(source, oewn_archive=raw)


class Tests(unittest.TestCase):
    def test_exact_bare_sentence_proves_nonidentifiability(self):
        out = prove_fixture()
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__BARE_MARGIN_UNIQUE_SENSE_NONIDENTIFIABILITY_PROVED",
        )
        self.assertTrue(out["semantic_nonidentifiability_authority"])
        self.assertFalse(out["unique_sense_identified"])
        self.assertFalse(out["unique_sense_identifiable_from_source_alone"])
        self.assertTrue(out["additional_information_required_for_unique_identity"])

    def test_two_distinct_authenticated_witness_senses_are_preserved(self):
        out = prove_fixture()
        self.assertEqual(
            out["witness_sense_ids"],
            [cert.COLLATERAL_SENSE, cert.PROFIT_SENSE],
        )
        self.assertEqual(
            set(out["witness_synset_ids"]),
            {cert.COLLATERAL_SYNSET, cert.PROFIT_SYNSET},
        )
        self.assertEqual(len(out["witness_worlds"]), 2)
        self.assertTrue(
            all(
                x["source_sentence_true_under_interpretation"]
                for x in out["witness_worlds"]
            )
        )

    def test_negative_result_does_not_require_open_world_completeness(self):
        out = prove_fixture()
        self.assertTrue(out["pass"])
        self.assertFalse(out["open_world_finance_semantics_complete"])
        self.assertFalse(
            out["hypothesis_space_completeness_required_for_this_negative_result"]
        )
        self.assertTrue(
            out["open_world_remainder_may_contain_additional_interpretations"]
        )

    def test_no_true_sense_is_selected(self):
        out = prove_fixture()
        self.assertFalse(out["unique_sense_identified"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertEqual(
            out["decision_recommendation"],
            "ACQUIRE_DECISIVE_CONTEXT_OR_ABSTAIN_FROM_SENSE_IDENTITY",
        )

    def test_case_and_optional_period_are_within_bound_scope(self):
        for source in ("margin increased", "MARGIN INCREASED."):
            out = prove_fixture(source)
            self.assertTrue(out["pass"], out)

    def test_added_context_is_not_silently_classified_by_bare_certificate(self):
        for source in (
            "Margin increased to 34%.",
            "The broker margin increased.",
            "Profit margin increased.",
            "Margin increased because collateral requirements rose.",
        ):
            out = prove_fixture(source)
            self.assertFalse(out["pass"], out)
            self.assertEqual(
                out["status"],
                "NOT_APPLICABLE__SOURCE_OUTSIDE_BARE_MARGIN_SCOPE",
            )

    def test_missing_required_witness_sense_fails_closed(self):
        out = prove_fixture(omit_profit=True)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("REQUIRED_OEWN_SENSE_NOT_UNIQUE", out["reason"])

    def test_tampered_witness_definition_fails_closed(self):
        out = prove_fixture(bad_profit_definition=True)
        self.assertFalse(out["pass"])
        self.assertIn("OEWN_DEFINITION_BINDING_MISMATCH", out["reason"])

    def test_wrong_archive_hash_fails_closed(self):
        raw = build_zip()
        out = cert.prove("Margin increased.", oewn_archive=raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "OEWN_RELEASE_UNIVERSE_NOT_AUTHENTICATED")

    def test_witness_arithmetic_is_real(self):
        out = prove_fixture()
        collateral, profit = out["witness_worlds"]
        self.assertGreater(collateral["after"], collateral["before"])
        self.assertGreater(
            profit["after"]["gross_profit"],
            profit["before"]["gross_profit"],
        )

    def test_no_terminal_acceptance_or_promotion_authority(self):
        out = prove_fixture()
        self.assertTrue(out["pass"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
