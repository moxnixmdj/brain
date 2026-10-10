from __future__ import annotations
from pathlib import Path
import unittest

from canonical.runtime import tlac_mrel_authenticated_sense_selector_v1 as s
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as old

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

class Tests(unittest.TestCase):
    def test_mrel_context_selects_mrel(self):
        text=(
            "The minimum requirement for own funds and eligible liabilities "
            "is determined by the resolution authority under Article 45c."
        )
        out=s.resolve(
            text,source_id="doc:mrel",
            repo_root=ROOT,projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["selected_concept_id"],old.MREL)
        self.assertTrue(out["bounded_scope_identity_authority"])
        self.assertFalse(out["global_identity_authority"])

    def test_tlac_context_selects_tlac(self):
        text=(
            "The FSB TLAC standard establishes Minimum External TLAC for G-SIBs."
        )
        out=s.resolve(
            text,source_id="doc:tlac",
            repo_root=ROOT,projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["selected_concept_id"],old.TLAC)

    def test_decisive_results_match_existing_pair_resolver(self):
        cases=[
            (
                "The minimum requirement for own funds and eligible liabilities "
                "is determined by the resolution authority under Article 45c."
            ),
            (
                "The FSB TLAC standard establishes Minimum External TLAC for G-SIBs."
            ),
        ]
        for i,text in enumerate(cases):
            new=s.resolve(
                text,source_id=f"doc:{i}",
                repo_root=ROOT,projection_verifier=fake_projection,
            )
            legacy=old.resolve_relative(
                text,
                source_id=f"doc:{i}",
                candidate_concept_ids=list(old.DOMAIN),
                repo_root=ROOT,
                projection_verifier=fake_projection,
            )
            self.assertTrue(new["pass"],new)
            self.assertTrue(legacy["pass"],legacy)
            self.assertEqual(
                new["selected_concept_id"],
                legacy["selected_concept_id"],
            )

    def test_insufficient_context_returns_minimum_next_observation(self):
        text="This requirement increases loss absorption."
        out=s.resolve(
            text,source_id="doc:open",
            repo_root=ROOT,projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__MINIMUM_AUTHENTICATED_CONTEXT_DISCRIMINATOR_REQUIRED",
        )
        self.assertEqual(out["next_observation_id"],old.OBSERVATION_ID)
        self.assertEqual(
            out["next_information_request"]["observation_id"],
            old.OBSERVATION_ID,
        )
        self.assertEqual(
            set(out["surviving_candidate_ids"]),
            set(old.DOMAIN),
        )

    def test_conflicting_context_fails_closed(self):
        text=(
            "The minimum requirement for own funds and eligible liabilities "
            "is determined by the resolution authority. "
            "The FSB TLAC standard establishes Minimum External TLAC for G-SIBs."
        )
        out=s.resolve(
            text,source_id="doc:conflict",
            repo_root=ROOT,projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_no_terminal_or_open_world_authority(self):
        text=(
            "The FSB TLAC standard establishes Minimum External TLAC for G-SIBs."
        )
        out=s.resolve(
            text,source_id="doc:tlac",
            repo_root=ROOT,projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"])
        self.assertFalse(out["global_identity_authority"])
        self.assertFalse(out["open_world_ontology_complete"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
