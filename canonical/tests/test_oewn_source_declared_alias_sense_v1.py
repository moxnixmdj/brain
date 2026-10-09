from __future__ import annotations
import io
import unittest
from unittest.mock import patch

from canonical.runtime import oewn_source_declared_alias_sense_v1 as subject
from canonical.runtime.oewn_release_sense_universe_v1 import RELEASE_ID,RELEASE_SHA256,SCHEMA as OEWN_SCHEMA


def universe(*,duplicate_alias=False):
    rows=[
        ("margin%1:25:00::","13926393-n",["margin","border","perimeter"]),
        ("margin%1:07:00::","05127983-n",["margin"]),
        ("margin%1:21:01::","13372293-n",["margin","security deposit"]),
        ("margin%1:21:02::","13281661-n",["margin","gross profit","gross profit margin"]),
        ("margin%1:10:00::","06401041-n",["margin"]),
        ("margin%1:07:01::","04757264-n",["margin","allowance","leeway","tolerance"]),
    ]
    if duplicate_alias:
        rows[-1][2].append("security deposit")
    return {
        "schema":OEWN_SCHEMA,"status":"PASS","pass":True,
        "release_id":RELEASE_ID,"archive_sha256":RELEASE_SHA256,
        "lemma":"margin","requested_part_of_speech":"n",
        "candidate_set_complete_relative_to_release":True,
        "open_world_english_sense_completeness_claimed":False,
        "senses":[
            {"sense_id":sid,"synset_id":syn,"part_of_speech":"n","members":members}
            for sid,syn,members in rows
        ],
    }


def projection():
    return {
        "pass":True,"source_id":"SEC_FOREX_2013",
        "url":"https://www.sec.gov/answers/forcurr.htm",
        "matched_fragments":[{
            "fragment_id":"margin-alias",
            "text":'You will be required to deposit an amount of money (usually called a “security deposit” or “margin”) with a forex dealer.',
        }],
        "receipt":{"receipt_sha256":"a"*64},
    }


class Tests(unittest.TestCase):
    def test_unique_authenticated_alias_selects_broker_margin_sense(self):
        with patch.object(subject,"verify_projection_pack",return_value=projection()):
            out=subject.resolve(
                sense_universe=universe(),
                source_projection_pack={"schema":"ignored-by-mock"},
                fragment_id="margin-alias",ambiguous_term="margin",
            )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["selected_sense_id"],"margin%1:21:01::")
        self.assertEqual(out["selected_synset_id"],"13372293-n")
        self.assertEqual(out["declared_alias"],"security deposit")
        self.assertTrue(out["source_scoped_sense_binding_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_unauthenticated_source_stays_open(self):
        with patch.object(subject,"verify_projection_pack",return_value={"pass":False,"status":"FAIL_CLOSED"}):
            out=subject.resolve(
                sense_universe=universe(),source_projection_pack={},
                fragment_id="margin-alias",ambiguous_term="margin",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__AUTHENTICATED_SOURCE_ALIAS_FRAGMENT_REQUIRED")

    def test_alias_not_naming_lemma_stays_open(self):
        p=projection()
        p["matched_fragments"][0]["text"]='This is usually called a “deposit” or “performance bond”.'
        with patch.object(subject,"verify_projection_pack",return_value=p):
            out=subject.resolve(
                sense_universe=universe(),source_projection_pack={},
                fragment_id="margin-alias",ambiguous_term="margin",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__SOURCE_ALIAS_DOES_NOT_NAME_AMBIGUOUS_TERM")

    def test_nonunique_alias_never_selects(self):
        with patch.object(subject,"verify_projection_pack",return_value=projection()):
            out=subject.resolve(
                sense_universe=universe(duplicate_alias=True),source_projection_pack={},
                fragment_id="margin-alias",ambiguous_term="margin",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__DECLARED_ALIAS_NOT_UNIQUE_ACROSS_OEWN_RELEASE_SENSES")

    def test_incomplete_universe_fails_closed(self):
        u=universe(); u["candidate_set_complete_relative_to_release"]=False
        with patch.object(subject,"verify_projection_pack",return_value=projection()):
            out=subject.resolve(
                sense_universe=u,source_projection_pack={},
                fragment_id="margin-alias",ambiguous_term="margin",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("COMPLETENESS_UNPROVED",out["reason"])

    def test_unsupported_alias_prose_fails_closed(self):
        p=projection()
        p["matched_fragments"][0]["text"]="Margin is basically collateral in this context."
        with patch.object(subject,"verify_projection_pack",return_value=p):
            out=subject.resolve(
                sense_universe=universe(),source_projection_pack={},
                fragment_id="margin-alias",ambiguous_term="margin",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("SUPPORTED_ALIAS_DECLARATION",out["reason"])


if __name__=="__main__":
    unittest.main(verbosity=2)
