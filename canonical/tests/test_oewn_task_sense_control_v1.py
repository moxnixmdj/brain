from __future__ import annotations

from hashlib import sha256
import io
import json
import unittest
from unittest.mock import patch
import zipfile

from canonical.runtime import oewn_task_sense_control_v1 as control
from canonical.runtime.authenticated_context_concept_bridge_v1 import CONTEXT_AUTHORITY_SCHEMA
from canonical.runtime.authoritative_typed_context_compiler_v1 import compile_typed_context


SCOPE="finance:margin-task"


def fixture_zip():
    entries={
        "margin":{
            "n":{
                "sense":[
                    {"id":"margin%1:21:01::","synset":"10000001-n"},
                    {"id":"margin%1:21:02::","synset":"10000002-n"},
                ]
            }
        }
    }
    noun={
        "10000001-n":{
            "definition":["profit sense"],
            "members":["margin","profit margin"],
            "partOfSpeech":"n",
        },
        "10000002-n":{
            "definition":["collateral sense"],
            "members":["margin","security deposit"],
            "partOfSpeech":"n",
        },
    }
    bio=io.BytesIO()
    with zipfile.ZipFile(bio,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("entries-m.json",json.dumps(entries))
        z.writestr("noun.possession.json",json.dumps(noun))
        z.writestr("frames.json",json.dumps({}))
    return bio.getvalue()


def authority_for(raw, *, same=False, omit_second=False, wrong_universe=False):
    enum=control.enumerate_release_universe(raw,"margin",part_of_speech="n")
    ids=enum["sense_ids"]
    mappings=[
        {
            "sense_id":ids[0],
            "attributes":{"phase":"income_statement","domain":"finance"},
            "terminal_signature_complete":True,
            "terminal_signature":{"action":"SAME" if same else "PROFIT"},
        }
    ]
    if not omit_second:
        mappings.append({
            "sense_id":ids[1],
            "attributes":{"phase":"collateral","domain":"finance"},
            "terminal_signature_complete":True,
            "terminal_signature":{"action":"SAME" if same else "COLLATERAL"},
        })
    def verify(_receipt):
        return {
            "pass":True,
            "schema":control.MAPPING_AUTHORITY_SCHEMA,
            "scope_id":SCOPE,
            "release_id":enum["release"]["release_id"],
            "archive_sha256":enum["release"]["archive_sha256"],
            "lemma":enum["release"]["lemma"],
            "requested_part_of_speech":enum["release"]["requested_part_of_speech"],
            "sense_universe_sha256":(
                "0"*64 if wrong_universe else enum["sense_universe_sha256"]
            ),
            "mapping_complete_for_release_senses":True,
            "task_semantics_authenticated":True,
            "verification_authority_mutated":False,
            "mappings":mappings,
            "observations":[{
                "observation_id":"CHECK_PHASE",
                "outcome_map_complete":True,
                "outcomes":{ids[0]:"income_statement",ids[1]:"collateral"},
                "cost_units":1,
            }],
            "receipt_sha256":"a"*64,
        }
    return verify


def context_source(phase="collateral"):
    return json.dumps({
        "schema_id":"finance-case-v1",
        "fields":{
            "phase":{"type":"STRING","value":phase},
            "domain":{"type":"STRING","value":"finance"},
        },
    },sort_keys=True)


def context_verifier(source):
    compiled=compile_typed_context(source,source_id="case.json")
    def verify(_receipt):
        return {
            "pass":True,
            "schema":CONTEXT_AUTHORITY_SCHEMA,
            "scope_id":SCOPE,
            "source_id":"case.json",
            "raw_source_sha256":compiled["raw_source_sha256"],
            "typed_context_sha256":compiled["typed_context_sha256"],
            "source_authorized_for_scope":True,
            "field_semantics_authenticated":True,
            "verification_authority_mutated":False,
            "attribute_projection":[{
                "registry_attribute":"phase",
                "field_name":"phase",
                "field_type":"STRING",
            }],
            "receipt_sha256":"b"*64,
        }
    return verify


class Tests(unittest.TestCase):
    def run_bound(self, raw, **kwargs):
        with patch.object(control.oewn,"RELEASE_SHA256",sha256(raw).hexdigest()):
            verifier=kwargs.pop("mapping_authority_verifier",None)
            if verifier is None:
                verifier=authority_for(raw)
            return control.resolve(
                archive=raw,
                lemma="margin",
                part_of_speech="n",
                scope_id=SCOPE,
                mapping_authority_receipt={"candidate":True},
                mapping_authority_verifier=verifier,
                **kwargs,
            )

    def test_missing_mapping_authority_stays_open(self):
        raw=fixture_zip()
        with patch.object(control.oewn,"RELEASE_SHA256",sha256(raw).hexdigest()):
            out=control.resolve(
                archive=raw,lemma="margin",part_of_speech="n",scope_id=SCOPE,
                mapping_authority_receipt=None,mapping_authority_verifier=None,
            )
        self.assertFalse(out["pass"])
        self.assertTrue(out["release_candidate_set_complete"])
        self.assertFalse(out["task_mapping_authenticated"])
        self.assertEqual(out["status"],"OPEN__AUTHENTICATED_TASK_SENSE_MAPPING_REQUIRED")

    def test_mapping_must_cover_every_release_sense(self):
        raw=fixture_zip()
        with patch.object(control.oewn,"RELEASE_SHA256",sha256(raw).hexdigest()):
            verifier=authority_for(raw,omit_second=True)
            out=control.resolve(
                archive=raw,lemma="margin",part_of_speech="n",scope_id=SCOPE,
                mapping_authority_receipt={"candidate":True},
                mapping_authority_verifier=verifier,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("TASK_MAPPING_DOES_NOT_COVER_EXACT_RELEASE_SENSE_SET",out["reason"])

    def test_wrong_universe_binding_is_rejected(self):
        raw=fixture_zip()
        with patch.object(control.oewn,"RELEASE_SHA256",sha256(raw).hexdigest()):
            verifier=authority_for(raw,wrong_universe=True)
            out=control.resolve(
                archive=raw,lemma="margin",part_of_speech="n",scope_id=SCOPE,
                mapping_authority_receipt={"candidate":True},
                mapping_authority_verifier=verifier,
            )
        self.assertFalse(out["pass"])
        self.assertFalse(out["task_mapping_authenticated"])
        self.assertEqual(out["status"],"OPEN__AUTHENTICATED_TASK_SENSE_MAPPING_REQUIRED")

    def test_no_context_uses_existing_minimum_discriminator(self):
        raw=fixture_zip()
        out=self.run_bound(raw)
        self.assertFalse(out["pass"],out)
        self.assertTrue(out["release_candidate_set_complete"])
        self.assertTrue(out["task_mapping_authenticated"])
        self.assertTrue(out["derived_registry_authenticated"])
        self.assertEqual(out["next_observation_id"],"CHECK_PHASE")
        self.assertEqual(len(out["concept_universe_result"]["candidate_concept_ids"]),2)

    def test_terminally_equivalent_senses_stop_without_identity(self):
        raw=fixture_zip()
        with patch.object(control.oewn,"RELEASE_SHA256",sha256(raw).hexdigest()):
            out=control.resolve(
                archive=raw,lemma="margin",part_of_speech="n",scope_id=SCOPE,
                mapping_authority_receipt={"candidate":True},
                mapping_authority_verifier=authority_for(raw,same=True),
            )
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["intended_sense_identified"])
        self.assertEqual(len(out["concept_universe_result"]["candidate_concept_ids"]),2)

    def test_authenticated_context_selects_collateral_sense(self):
        raw=fixture_zip(); source=context_source("collateral")
        out=self.run_bound(
            raw,
            raw_context_source=source,
            context_source_id="case.json",
            context_authority_receipt={"candidate":True},
            context_authority_verifier=context_verifier(source),
        )
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["intended_sense_identified"])
        self.assertIn("margin%1:21:02::",out["intended_concept_id"])

    def test_context_still_cannot_self_authorize(self):
        raw=fixture_zip(); source=context_source("collateral")
        out=self.run_bound(
            raw,
            raw_context_source=source,
            context_source_id="case.json",
        )
        self.assertFalse(out["pass"])
        self.assertFalse(out["context_result"]["context_source_authorized"])

    def test_release_enumeration_preserves_both_senses_in_registry(self):
        raw=fixture_zip()
        out=self.run_bound(raw)
        concepts=out["derived_registry"]["concepts"]
        self.assertEqual(len(concepts),2)
        self.assertEqual(
            {x["attributes"]["oewn_sense_id"] for x in concepts},
            {"margin%1:21:01::","margin%1:21:02::"},
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
