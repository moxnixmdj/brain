from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import tlac_mrel_identity_discriminator_v1 as pair

ROOT = Path(__file__).resolve().parents[2]


def fake_projection(pack):
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": sorted(
                str(row["fragment_id"])
                for row in pack.get("fragments", [])
            ),
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_authority_is_complete_only_for_declared_pair_scope(self):
        out = pair.verify_authority(
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(set(out["candidate_domain"]), {pair.TLAC, pair.MREL})
        self.assertTrue(out["candidate_universe_complete"])
        self.assertEqual(
            out["candidate_universe_complete_only_for_scope_id"],
            pair.SCOPE_ID,
        )
        self.assertFalse(out["open_world_ontology_complete"])

    def test_mrel_governing_context_selects_mrel(self):
        text = (
            "The minimum requirement for own funds and eligible liabilities "
            "shall be determined by the resolution authority under Article 45c."
        )
        out = pair.resolve_relative(
            text,
            source_id="doc:mrel",
            candidate_concept_ids=[pair.TLAC, pair.MREL],
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], pair.MREL)
        self.assertEqual(
            out["observed_outcome"],
            pair.OUTCOMES[pair.MREL],
        )
        self.assertFalse(out["global_semantic_identity_authority"])

    def test_tlac_governing_context_selects_tlac(self):
        text = (
            "Under the FSB TLAC standard, each G-SIB must meet "
            "Minimum External TLAC."
        )
        out = pair.resolve_relative(
            text,
            source_id="doc:tlac",
            candidate_concept_ids=[pair.TLAC, pair.MREL],
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], pair.TLAC)

    def test_shared_resolution_signature_remains_unresolved(self):
        text = (
            "The requirement provides loss-absorbing and recapitalisation "
            "capacity available in resolution."
        )
        out = pair.resolve_relative(
            text,
            source_id="doc:shared",
            candidate_concept_ids=[pair.TLAC, pair.MREL],
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__NO_BOUND_TLAC_MREL_IDENTITY_DISCRIMINATOR",
        )

    def test_mixed_pair_markers_fail_closed(self):
        text = (
            "The minimum requirement for own funds and eligible liabilities "
            "shall be determined by the resolution authority under Article 45c. "
            "Under the FSB TLAC standard, each G-SIB must meet Minimum External TLAC."
        )
        out = pair.compile_context(text, source_id="doc:mixed")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "CONFLICTING_TLAC_MREL_CONTEXT_SIGNATURES",
        )

    def test_negated_mrel_setter_does_not_select_mrel(self):
        text = (
            "The minimum requirement for own funds and eligible liabilities "
            "is not determined by the resolution authority under Article 45c."
        )
        out = pair.compile_context(text, source_id="doc:neg")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__NO_BOUND_TLAC_MREL_IDENTITY_DISCRIMINATOR",
        )

    def test_candidate_set_must_be_exact_pair(self):
        text = (
            "Under the FSB TLAC standard, each G-SIB must meet "
            "Minimum External TLAC."
        )
        out = pair.resolve_relative(
            text,
            source_id="doc:tlac",
            candidate_concept_ids=[pair.TLAC],
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "CANDIDATE_SET_MUST_EQUAL_BOUND_TLAC_MREL_PAIR",
        )

    def test_source_authentication_failure_fails_closed(self):
        out = pair.verify_authority(
            repo_root=ROOT,
            projection_verifier=lambda _pack: {"pass": False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("PINNED_SOURCE_FRAGMENT_AUTHORITY_FAILED", out["reason"])

    def test_pack_blob_drift_fails_closed(self):
        source = ROOT / pair.PACK_PATH
        doc = json.loads(source.read_text(encoding="utf-8"))
        doc["scope_id"] += "-tampered"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / pair.PACK_PATH
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps(doc, sort_keys=True),
                encoding="utf-8",
            )
            out = pair.verify_authority(
                repo_root=root,
                projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("PACK_GIT_BLOB_DRIFT", out["reason"])

    def test_no_terminal_or_global_pair_claim(self):
        out = pair.verify_authority(
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["concept_equivalence_authority"])
        self.assertFalse(out["concept_disjointness_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
