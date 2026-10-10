from __future__ import annotations
from pathlib import Path
import unittest

from canonical.runtime import tlac_mrel_bounded_sense_truth_certificate_v1 as c
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as tlac

ROOT=Path(__file__).resolve().parents[2]

def fake_projection(pack):
    return {
        "pass":True,
        "receipt":{
            "fragment_ids":sorted(
                str(x["fragment_id"]) for x in pack.get("fragments",[])
            ),
            "receipt_sha256":"a"*64,
        },
        "source_fragment_authority":True,
        "terminal_authority":False,
    }

def payload(text,target):
    return {
        "truth_kind":c.TRUTH_KIND,
        "predicate_id":"caller-label",
        "source_text":text,
        "source_id":"doc:test",
        "target_concept_id":target,
    }

class Tests(unittest.TestCase):
    def test_selected_target_is_true(self):
        text="The FSB TLAC standard establishes Minimum External TLAC for G-SIBs."
        out=c.evaluate(
            payload(text,tlac.TLAC),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["predicate_truth"],"TRUE")
        self.assertEqual(out["selected_concept_id"],tlac.TLAC)
        self.assertTrue(out["semantic_truth_authority"])
        self.assertTrue(out["semantic_identity_authority"])

    def test_uniquely_selected_rival_is_false_inside_pair_scope(self):
        text="The FSB TLAC standard establishes Minimum External TLAC for G-SIBs."
        out=c.evaluate(
            payload(text,tlac.MREL),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["predicate_truth"],"FALSE")
        self.assertEqual(out["selected_concept_id"],tlac.TLAC)
        self.assertTrue(out["candidate_universe_complete"])
        self.assertEqual(
            out["candidate_universe_complete_only_for_scope_id"],
            tlac.SCOPE_ID,
        )

    def test_insufficient_context_remains_unknown_and_requests_minimum_observation(self):
        text="This requirement increases loss absorption."
        out=c.evaluate(
            payload(text,tlac.TLAC),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["predicate_truth"],"UNKNOWN")
        self.assertEqual(
            out["next_observation_id"],
            tlac.OBSERVATION_ID,
        )
        self.assertEqual(
            out["next_information_request"]["observation_id"],
            tlac.OBSERVATION_ID,
        )
        self.assertFalse(out["semantic_truth_authority"])

    def test_unsupported_target_fails_closed(self):
        text="The FSB TLAC standard establishes Minimum External TLAC for G-SIBs."
        out=c.evaluate(
            payload(text,"REGCAP::CCOB"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("TARGET_CONCEPT_UNSUPPORTED",out["reason"])

    def test_no_global_or_terminal_authority(self):
        text=(
            "The minimum requirement for own funds and eligible liabilities "
            "is determined by the resolution authority under Article 45c."
        )
        out=c.evaluate(
            payload(text,tlac.MREL),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["global_identity_authority"])
        self.assertFalse(out["open_world_ontology_complete"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
