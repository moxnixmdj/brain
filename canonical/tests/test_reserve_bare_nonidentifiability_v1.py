from __future__ import annotations

from hashlib import sha256
import io
import json
import unittest
from unittest.mock import patch
import zipfile

from canonical.runtime import reserve_bare_nonidentifiability_v1 as reserve
from canonical.runtime import oewn_release_sense_universe_v1 as oewn


def make_zip(*,tamper_stock_definition=False):
    entries={
        "reserve":{
            "n":{
                "sense":[
                    {"id":reserve.STOCK_SENSE,"synset":reserve.STOCK_SYNSET},
                    {"id":reserve.MEDICAL_SENSE,"synset":reserve.MEDICAL_SYNSET},
                ]
            }
        }
    }
    possession={
        reserve.STOCK_SYNSET:{
            "definition":[
                "tampered definition"
                if tamper_stock_definition
                else reserve.STOCK_DEFINITION
            ],
            "members":["reserve","stockpile"],
            "partOfSpeech":"n",
        }
    }
    quantity={
        reserve.MEDICAL_SYNSET:{
            "definition":[reserve.MEDICAL_DEFINITION],
            "members":["reserve"],
            "partOfSpeech":"n",
        }
    }
    bio=io.BytesIO()
    with zipfile.ZipFile(bio,"w",zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("entries-r.json",json.dumps(entries))
        zf.writestr("noun.possession.json",json.dumps(possession))
        zf.writestr("noun.quantity.json",json.dumps(quantity))
        zf.writestr("frames.json","{}")
    return bio.getvalue()


class Tests(unittest.TestCase):
    def test_bare_reserve_is_pairwise_nonidentifiable(self):
        raw=make_zip()
        digest=sha256(raw).hexdigest()
        with patch.object(oewn,"RELEASE_SHA256",digest):
            out=reserve.prove(
                "Reserve increased.",
                source_id="doc:A",
                oewn_archive=raw,
            )
        self.assertTrue(out["pass"],out)
        self.assertEqual(
            out["status"],
            "PASS__BARE_RESERVE_UNIQUE_SENSE_NONIDENTIFIABILITY_PROVED",
        )
        self.assertTrue(out["semantic_nonidentifiability_authority"])
        self.assertFalse(out["unique_sense_identified"])
        self.assertEqual(
            set(out["witness_sense_ids"]),
            {reserve.STOCK_SENSE,reserve.MEDICAL_SENSE},
        )
        self.assertTrue(out["generic_pairwise_result"]["pass"])

    def test_both_witness_worlds_make_increased_true(self):
        raw=make_zip()
        digest=sha256(raw).hexdigest()
        with patch.object(oewn,"RELEASE_SHA256",digest):
            out=reserve.prove(
                "Reserve increased.",
                source_id="doc:A",
                oewn_archive=raw,
            )
        self.assertTrue(out["pass"],out)
        self.assertTrue(
            all(x["source_sentence_true_under_interpretation"] for x in out["witness_worlds"])
        )
        self.assertTrue(all(x["predicate_check"] for x in out["witness_worlds"]))

    def test_release_relative_inventory_does_not_claim_finance_completeness(self):
        raw=make_zip()
        digest=sha256(raw).hexdigest()
        with patch.object(oewn,"RELEASE_SHA256",digest):
            out=reserve.prove(
                "Reserve increased.",
                source_id="doc:A",
                oewn_archive=raw,
            )
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["open_world_finance_semantics_complete"])
        self.assertFalse(out["finance_domain_identity_authority"])
        self.assertTrue(out["open_world_remainder_may_contain_additional_interpretations"])

    def test_source_outside_exact_bare_form_is_not_applicable(self):
        raw=make_zip()
        digest=sha256(raw).hexdigest()
        with patch.object(oewn,"RELEASE_SHA256",digest):
            out=reserve.prove(
                "The reserve increased.",
                source_id="doc:A",
                oewn_archive=raw,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "NOT_APPLICABLE__SOURCE_OUTSIDE_BARE_RESERVE_SCOPE",
        )

    def test_missing_source_id_fails_closed(self):
        raw=make_zip()
        digest=sha256(raw).hexdigest()
        with patch.object(oewn,"RELEASE_SHA256",digest):
            out=reserve.prove(
                "Reserve increased.",
                source_id="",
                oewn_archive=raw,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"SOURCE_ID_REQUIRED")

    def test_release_hash_mismatch_fails_closed(self):
        raw=make_zip()
        with patch.object(oewn,"RELEASE_SHA256","0"*64):
            out=reserve.prove(
                "Reserve increased.",
                source_id="doc:A",
                oewn_archive=raw,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"OEWN_RELEASE_UNIVERSE_NOT_AUTHENTICATED")

    def test_definition_binding_tamper_fails_closed(self):
        raw=make_zip(tamper_stock_definition=True)
        digest=sha256(raw).hexdigest()
        with patch.object(oewn,"RELEASE_SHA256",digest):
            out=reserve.prove(
                "Reserve increased.",
                source_id="doc:A",
                oewn_archive=raw,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("OEWN_DEFINITION_BINDING_MISMATCH",out["reason"])

    def test_generic_pairwise_theorem_is_load_bearing(self):
        raw=make_zip()
        digest=sha256(raw).hexdigest()
        with patch.object(oewn,"RELEASE_SHA256",digest), patch.object(
            reserve.generic,
            "prove",
            return_value={"pass":False,"status":"FAIL_CLOSED","reason":"TEST"},
        ):
            out=reserve.prove(
                "Reserve increased.",
                source_id="doc:A",
                oewn_archive=raw,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "GENERIC_PAIRWISE_NONIDENTIFIABILITY_NOT_PROVED",
        )

    def test_no_semantic_truth_policy_or_terminal_authority(self):
        raw=make_zip()
        digest=sha256(raw).hexdigest()
        with patch.object(oewn,"RELEASE_SHA256",digest):
            out=reserve.prove(
                "Reserve increased.",
                source_id="doc:A",
                oewn_archive=raw,
            )
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
