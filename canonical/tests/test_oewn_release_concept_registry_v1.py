from __future__ import annotations

import io
import json
import unittest
from hashlib import sha256
from unittest.mock import patch
import zipfile

from canonical.runtime import oewn_release_sense_universe_v1 as sense
from canonical.runtime import oewn_release_concept_registry_v1 as bridge
from canonical.runtime.bounded_authenticated_concept_universe_v1 import resolve


def archive_bytes():
    entries={
        "margin":{"n":{"sense":[
            {"id":"margin%1:21:01::","synset":"10000001-n"},
            {"id":"margin%1:21:02::","synset":"10000002-n"},
        ]}}
    }
    synsets={
        "10000001-n":{
            "definition":["profit sense"],
            "members":["margin","gross profit margin"],
            "partOfSpeech":"n",
            "domain_topic":["00000001-n"],
        },
        "10000002-n":{
            "definition":["broker collateral sense"],
            "members":["margin","security deposit"],
            "partOfSpeech":"n",
            "hypernym":["00000002-n"],
        },
    }
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("entries-m.json",json.dumps(entries))
        z.writestr("entries-a.json","{}")
        z.writestr("noun.possession.json",json.dumps(synsets))
        z.writestr("frames.json","{}")
    return b.getvalue()


def build(raw):
    digest=sha256(raw).hexdigest()
    with patch.object(sense,"RELEASE_SHA256",digest),patch.object(bridge,"RELEASE_SHA256",digest):
        return bridge.build_registry(raw,"margin",part_of_speech="n")


class Tests(unittest.TestCase):
    def test_builds_exact_two_sense_registry_without_selecting_sense(self):
        raw=archive_bytes()
        out=build(raw)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["sense_count"],2)
        self.assertTrue(out["candidate_set_complete_relative_to_oewn_release"])
        self.assertFalse(out["intended_sense_identified"])
        self.assertTrue(out["lexical_identity_terminal_signatures_only"])
        self.assertFalse(out["task_terminal_equivalence_claimed"])
        self.assertEqual(
            {x["attributes"]["synset_id"] for x in out["registry"]["concepts"]},
            {"10000001-n","10000002-n"},
        )

    def test_source_derived_receipt_authenticates_exact_registry_only(self):
        raw=archive_bytes()
        digest=sha256(raw).hexdigest()
        with patch.object(sense,"RELEASE_SHA256",digest),patch.object(bridge,"RELEASE_SHA256",digest):
            built=bridge.build_registry(raw,"margin",part_of_speech="n")
            receipt=bridge.issue_authority_receipt(raw,built["registry"])
            verified=bridge.verify_authority_receipt(raw,built["registry"],receipt)
        self.assertTrue(verified["pass"],verified)
        self.assertTrue(verified["scope_completeness_authenticated"])
        self.assertTrue(verified["concept_semantics_authenticated"])
        self.assertEqual(verified["registry_sha256"],built["registry_sha256"])

    def test_modified_registry_cannot_reuse_source_receipt(self):
        raw=archive_bytes()
        digest=sha256(raw).hexdigest()
        with patch.object(sense,"RELEASE_SHA256",digest),patch.object(bridge,"RELEASE_SHA256",digest):
            built=bridge.build_registry(raw,"margin",part_of_speech="n")
            receipt=bridge.issue_authority_receipt(raw,built["registry"])
            changed=json.loads(json.dumps(built["registry"]))
            changed["concepts"][0]["attributes"]["lexname"]="noun.fake"
            out=bridge.verify_authority_receipt(raw,changed,receipt)
        self.assertFalse(out["pass"])
        self.assertFalse(out["concept_semantics_authenticated"])

    def test_authenticated_registry_stays_ambiguous_without_context(self):
        raw=archive_bytes()
        digest=sha256(raw).hexdigest()
        with patch.object(sense,"RELEASE_SHA256",digest),patch.object(bridge,"RELEASE_SHA256",digest):
            built=bridge.build_registry(raw,"margin",part_of_speech="n")
            receipt=bridge.issue_authority_receipt(raw,built["registry"])
            verifier=bridge.make_authority_verifier(raw,built["registry"])
            out=resolve(
                built["registry"],
                {},
                authority_receipt=receipt,
                authority_verifier=verifier,
            )
        self.assertFalse(out["pass"])
        self.assertTrue(out["authenticated_scope_completeness"])
        self.assertEqual(len(out["candidate_concept_ids"]),2)
        self.assertFalse(out["semantic_truth_authority"])

    def test_exact_authorized_attribute_can_reduce_to_unique_lexical_sense(self):
        raw=archive_bytes()
        digest=sha256(raw).hexdigest()
        with patch.object(sense,"RELEASE_SHA256",digest),patch.object(bridge,"RELEASE_SHA256",digest):
            built=bridge.build_registry(raw,"margin",part_of_speech="n")
            receipt=bridge.issue_authority_receipt(raw,built["registry"])
            verifier=bridge.make_authority_verifier(raw,built["registry"])
            out=resolve(
                built["registry"],
                {"required_attributes":{"synset_id":"10000002-n"}},
                authority_receipt=receipt,
                authority_verifier=verifier,
            )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["candidate_concept_ids"],["OEWN2025::margin%1:21:02::"])

    def test_terminal_signatures_are_identity_only_and_never_collapse_distinct_senses(self):
        raw=archive_bytes()
        out=build(raw)
        signatures=[x["terminal_signature"] for x in out["registry"]["concepts"]]
        self.assertEqual(len({json.dumps(x,sort_keys=True) for x in signatures}),2)
        for row in signatures:
            self.assertEqual(row["scope"],"OEWN_2025_LEXICAL_SENSE_IDENTITY_ONLY")

    def test_empty_or_absent_sense_universe_does_not_mint_registry(self):
        raw=archive_bytes()
        digest=sha256(raw).hexdigest()
        with patch.object(sense,"RELEASE_SHA256",digest),patch.object(bridge,"RELEASE_SHA256",digest):
            out=bridge.build_registry(raw,"absent",part_of_speech="n")
        self.assertFalse(out["pass"])
        self.assertIn("NONEMPTY_SENSE_UNIVERSE_REQUIRED",out["reason"])


if __name__=="__main__":
    unittest.main(verbosity=2)
