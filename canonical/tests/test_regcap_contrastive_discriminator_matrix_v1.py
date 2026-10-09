from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import regcap_contrastive_discriminator_matrix_v1 as matrix
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap

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
    def test_matrix_is_complete_only_relative_to_three_named_concepts(self):
        out = matrix.verify_matrix(
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["candidate_domain"]),
            {regcap.CCOB, regcap.CCYB, regcap.TLAC},
        )
        self.assertTrue(out["outcome_maps_complete_relative_to_matrix_domain"])
        self.assertFalse(out["candidate_universe_complete"])
        self.assertFalse(out["open_world_ontology_complete"])

    def test_framework_class_separates_tlac_from_basel_buffers(self):
        out = matrix.verify_matrix(
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        row = next(
            x for x in out["observations"]
            if x["observation_id"] == "FRAMEWORK_CLASS"
        )
        self.assertEqual(
            row["outcomes"][regcap.CCOB],
            "BASEL_CAPITAL_BUFFER_ABOVE_REGULATORY_MINIMUM",
        )
        self.assertEqual(
            row["outcomes"][regcap.CCYB],
            "BASEL_CAPITAL_BUFFER_ABOVE_REGULATORY_MINIMUM",
        )
        self.assertEqual(
            row["outcomes"][regcap.TLAC],
            "SEPARATE_MINIMUM_TLAC_REQUIREMENT",
        )

    def test_releasability_class_separates_all_three_relative_to_matrix(self):
        out = matrix.relative_one_step_discriminators(
            [regcap.CCOB, regcap.CCYB, regcap.TLAC],
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        ids = {
            row["observation_id"]
            for row in out["one_step_discriminators"]
        }
        self.assertIn("RELEASABILITY_CLASS", ids)
        self.assertNotIn("FRAMEWORK_CLASS", ids)
        self.assertFalse(out["candidate_universe_complete"])
        self.assertTrue(out["relative_only"])

    def test_ccob_ccyb_pair_has_releasability_separator(self):
        out = matrix.relative_one_step_discriminators(
            [regcap.CCOB, regcap.CCYB],
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        ids = {
            row["observation_id"]
            for row in out["one_step_discriminators"]
        }
        self.assertIn("RELEASABILITY_CLASS", ids)

    def test_ccob_tlac_pair_has_framework_separator(self):
        out = matrix.relative_one_step_discriminators(
            [regcap.CCOB, regcap.TLAC],
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        ids = {
            row["observation_id"]
            for row in out["one_step_discriminators"]
        }
        self.assertIn("FRAMEWORK_CLASS", ids)

    def test_functional_signature_class_uniquely_separates_three_rivals(self):
        out = matrix.verify_matrix(
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        row = next(
            x for x in out["observations"]
            if x["observation_id"] == "FUNCTIONAL_SIGNATURE_CLASS"
        )
        self.assertEqual(
            len(set(row["outcomes"].values())),
            3,
        )
        self.assertEqual(
            row["outcomes"][regcap.CCOB],
            "DRAWDOWN_AS_LOSSES_ARE_INCURRED",
        )
        self.assertEqual(
            row["outcomes"][regcap.CCYB],
            "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
        )
        self.assertEqual(
            row["outcomes"][regcap.TLAC],
            "G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
        )

    def test_structural_signature_class_uniquely_separates_three_rivals(self):
        out = matrix.verify_matrix(
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        row = next(
            x for x in out["observations"]
            if x["observation_id"] == "STRUCTURAL_SIGNATURE_CLASS"
        )
        self.assertEqual(len(set(row["outcomes"].values())), 3)
        rel = matrix.relative_one_step_discriminators(
            [regcap.CCOB, regcap.CCYB, regcap.TLAC],
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        ids = {
            x["observation_id"]
            for x in rel["one_step_discriminators"]
        }
        self.assertIn("FUNCTIONAL_SIGNATURE_CLASS", ids)
        self.assertIn("STRUCTURAL_SIGNATURE_CLASS", ids)

    def test_candidate_outside_matrix_fails_closed(self):
        out = matrix.relative_one_step_discriminators(
            [regcap.CCOB, "REGCAP::MREL"],
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CANDIDATE_OUTSIDE_MATRIX_DOMAIN")

    def test_source_authentication_failure_fails_closed(self):
        out = matrix.verify_matrix(
            repo_root=ROOT,
            projection_verifier=lambda _pack: {"pass": False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("PINNED_SOURCE_FRAGMENT_AUTHORITY_FAILED", out["reason"])

    def test_missing_required_fragment_fails_closed(self):
        def verifier(pack):
            ids = [
                str(row["fragment_id"])
                for row in pack.get("fragments", [])
            ]
            if ids:
                ids = ids[:-1]
            return {
                "pass": True,
                "receipt": {
                    "fragment_ids": ids,
                    "receipt_sha256": "b" * 64,
                },
            }

        out = matrix.verify_matrix(
            repo_root=ROOT,
            projection_verifier=verifier,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("REQUIRED_FRAGMENT_NOT_AUTHENTICATED", out["reason"])

    def test_pack_blob_drift_fails_closed(self):
        source = ROOT / matrix.PACK_PATH
        doc = json.loads(source.read_text(encoding="utf-8"))
        doc["scope_id"] += "-tampered"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / matrix.PACK_PATH
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps(doc, sort_keys=True),
                encoding="utf-8",
            )
            out = matrix.verify_matrix(
                repo_root=root,
                projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("PACK_GIT_BLOB_DRIFT", out["reason"])

    def test_no_terminal_or_global_completeness_authority(self):
        out = matrix.verify_matrix(
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["candidate_universe_complete"])
        self.assertFalse(out["open_world_ontology_complete"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
