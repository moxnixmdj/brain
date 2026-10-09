from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import mrel_necessary_property_authority_v1 as mrel

ROOT = Path(__file__).resolve().parents[2]


def request(prop, **extra):
    row = {
        "schema": mrel.REQUEST_SCHEMA,
        "scope_id": mrel.SCOPE_ID,
        "concept_id": mrel.MREL,
        "property_id": prop,
    }
    row.update(extra)
    return row


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
    def test_loss_absorption_is_one_way_authenticated(self):
        out = mrel.verify_property_request(
            request("FUNCTION::LOSS_ABSORPTION"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["edge_receipt"]["source_id"], mrel.MREL)
        self.assertEqual(
            out["edge_receipt"]["target_id"],
            "FUNCTION::LOSS_ABSORPTION",
        )
        self.assertFalse(out["reverse_inference_authorized"])

    def test_dispositional_loss_absorption_is_authenticated(self):
        out = mrel.verify_property_request(
            request("DISPOSITION::LOSS_ABSORPTION"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)

    def test_recapitalisation_and_resolution_are_authenticated(self):
        for prop in (
            "FUNCTION::RECAPITALISATION",
            "REGIME::RESOLUTION",
        ):
            out = mrel.verify_property_request(
                request(prop),
                repo_root=ROOT,
                projection_verifier=fake_projection,
            )
            self.assertTrue(out["pass"], (prop, out))

    def test_own_funds_and_eligible_liabilities_identity_is_authenticated(self):
        out = mrel.verify_property_request(
            request("COMPOSITION::OWN_FUNDS_AND_ELIGIBLE_LIABILITIES"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)

    def test_brrd_article_45c_legal_frame_is_authenticated(self):
        out = mrel.verify_property_request(
            request("LEGAL_FRAMEWORK::EU_BRRD_ARTICLE_45C"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)

    def test_property_does_not_reverse_classify_to_mrel(self):
        out = mrel.verify_property_request(
            {
                "schema": mrel.REQUEST_SCHEMA,
                "scope_id": mrel.SCOPE_ID,
                "concept_id": "FUNCTION::RECAPITALISATION",
                "property_id": mrel.MREL,
            },
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNKNOWN__PROPERTY_NOT_PROVED_IN_BOUND_SCOPE",
        )
        self.assertFalse(out["reverse_inference_authorized"])
        self.assertFalse(out["absence_means_false"])

    def test_tlac_mrel_disjointness_is_not_claimed(self):
        out = mrel.verify_property_request(
            request("DISJOINT_WITH::TLAC"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNKNOWN__PROPERTY_NOT_PROVED_IN_BOUND_SCOPE",
        )
        self.assertFalse(out["absence_means_false"])

    def test_unlisted_property_is_unknown_not_false(self):
        out = mrel.verify_property_request(
            request("COMPOSITION::CET1_ONLY"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertFalse(out["absence_means_false"])

    def test_source_authentication_failure_fails_closed(self):
        out = mrel.verify_property_request(
            request("REGIME::RESOLUTION"),
            repo_root=ROOT,
            projection_verifier=lambda _pack: {"pass": False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "PINNED_SOURCE_FRAGMENT_AUTHORITY_FAILED",
        )

    def test_unmodeled_request_field_fails_closed(self):
        out = mrel.verify_property_request(
            request("REGIME::RESOLUTION", guessed=True),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertIn("UNMODELED_REQUEST_FIELDS", out["reason"])

    def test_pack_blob_drift_fails_closed(self):
        source = ROOT / mrel.PACK_PATH
        doc = json.loads(source.read_text(encoding="utf-8"))
        doc["scope_id"] += "-tampered"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / mrel.PACK_PATH
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
            out = mrel.verify_property_request(
                request("FUNCTION::LOSS_ABSORPTION"),
                repo_root=root,
                projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"])
        self.assertIn("PACK_GIT_BLOB_DRIFT", out["reason"])

    def test_no_terminal_or_policy_authority(self):
        out = mrel.verify_property_request(
            request("REGIME::RESOLUTION"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_truth_authority"])
        self.assertTrue(out["source_authority"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
