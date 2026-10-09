from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import regcap_necessary_property_authority_v1 as regcap


ROOT = Path(__file__).resolve().parents[2]


def request(concept, prop, **extra):
    row = {
        "schema": regcap.REQUEST_SCHEMA,
        "scope_id": regcap.SCOPE_ID,
        "concept_id": concept,
        "property_id": prop,
    }
    row.update(extra)
    return row


def fake_source_result(source_pack):
    ids = sorted(
        str(row["fragment_id"])
        for row in source_pack.get("fragments", [])
    )
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": ids,
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_ccob_loss_absorption_is_one_way_authenticated_property(self):
        with patch.object(regcap, "verify_projection_pack", side_effect=fake_source_result):
            out = regcap.verify_property_request(
                request(regcap.CCOB, "FUNCTION::LOSS_ABSORPTION"),
                repo_root=ROOT,
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relation"], "ENTAILS")
        self.assertEqual(out["edge_receipt"]["source_id"], regcap.CCOB)
        self.assertEqual(
            out["edge_receipt"]["target_id"],
            "FUNCTION::LOSS_ABSORPTION",
        )
        self.assertFalse(out["reverse_inference_authorized"])
        self.assertFalse(out["exact_concept_identity_authority"])

    def test_ccob_cet1_and_above_minimum_are_authenticated(self):
        with patch.object(regcap, "verify_projection_pack", side_effect=fake_source_result):
            cet1 = regcap.verify_property_request(
                request(regcap.CCOB, "COMPOSITION::CET1"),
                repo_root=ROOT,
            )
            above = regcap.verify_property_request(
                request(regcap.CCOB, "POSITION::ABOVE_REGULATORY_MINIMUM"),
                repo_root=ROOT,
            )
        self.assertTrue(cet1["pass"], cet1)
        self.assertTrue(above["pass"], above)

    def test_ccyb_macroprudential_discriminators_are_authenticated(self):
        properties = [
            "DOMAIN::MACRO_FINANCIAL",
            "TRIGGER::EXCESS_CREDIT_GROWTH_SYSTEM_WIDE_RISK",
            "RELEASE::SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
            "COMPOSITION::CET1",
            "RELATION::EXTENDS_CCOB",
        ]
        with patch.object(regcap, "verify_projection_pack", side_effect=fake_source_result):
            results = [
                regcap.verify_property_request(
                    request(regcap.CCYB, prop),
                    repo_root=ROOT,
                )
                for prop in properties
            ]
        self.assertTrue(all(x["pass"] for x in results), results)

    def test_tlac_resolution_bundle_is_authenticated(self):
        properties = [
            "SCOPE::G_SIB",
            "FUNCTION::LOSS_ABSORPTION",
            "FUNCTION::RECAPITALISATION",
            "REGIME::RESOLUTION",
        ]
        with patch.object(regcap, "verify_projection_pack", side_effect=fake_source_result):
            results = [
                regcap.verify_property_request(
                    request(regcap.TLAC, prop),
                    repo_root=ROOT,
                )
                for prop in properties
            ]
        self.assertTrue(all(x["pass"] for x in results), results)

    def test_all_three_rivals_entail_same_dispositional_loss_absorption_atom(self):
        with patch.object(regcap, "verify_projection_pack", side_effect=fake_source_result):
            results = [
                regcap.verify_property_request(
                    request(concept, "DISPOSITION::LOSS_ABSORPTION"),
                    repo_root=ROOT,
                )
                for concept in (regcap.CCOB, regcap.CCYB, regcap.TLAC)
            ]
        self.assertTrue(all(x["pass"] for x in results), results)
        self.assertEqual(
            {x["edge_receipt"]["target_id"] for x in results},
            {"DISPOSITION::LOSS_ABSORPTION"},
        )
        self.assertTrue(
            all(x["reverse_inference_authorized"] is False for x in results)
        )

    def test_loss_absorption_property_does_not_reverse_classify_to_tlac(self):
        with patch.object(regcap, "verify_projection_pack", side_effect=fake_source_result):
            out = regcap.verify_property_request(
                request(
                    "FUNCTION::LOSS_ABSORPTION",
                    regcap.TLAC,
                ),
                repo_root=ROOT,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNKNOWN__PROPERTY_NOT_PROVED_IN_BOUND_SCOPE",
        )
        self.assertFalse(out["reverse_inference_authorized"])
        self.assertFalse(out["absence_means_false"])

    def test_unlisted_property_is_unknown_not_false(self):
        with patch.object(regcap, "verify_projection_pack", side_effect=fake_source_result):
            out = regcap.verify_property_request(
                request(regcap.CCOB, "REGIME::RESOLUTION"),
                repo_root=ROOT,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNKNOWN__PROPERTY_NOT_PROVED_IN_BOUND_SCOPE",
        )
        self.assertFalse(out["absence_means_false"])

    def test_source_authentication_failure_fails_closed(self):
        with patch.object(
            regcap,
            "verify_pack",
            return_value={"pass": False, "reason": "RAW_SOURCE_SHA256_MISMATCH"},
        ):
            out = regcap.verify_property_request(
                request(regcap.TLAC, "REGIME::RESOLUTION"),
                repo_root=ROOT,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "PINNED_SOURCE_FRAGMENT_AUTHORITY_FAILED",
        )

    def test_unmodeled_request_field_fails_closed(self):
        out = regcap.verify_property_request(
            request(
                regcap.CCOB,
                "FUNCTION::LOSS_ABSORPTION",
                guessed_identity="CCOB",
            ),
            repo_root=ROOT,
        )
        self.assertFalse(out["pass"])
        self.assertIn("UNMODELED_REQUEST_FIELDS", out["reason"])

    def test_pack_blob_drift_fails_closed(self):
        source = ROOT / regcap.PACK_PATH
        raw = json.loads(source.read_text(encoding="utf-8"))
        raw["scope_id"] = raw["scope_id"] + "-tampered"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / regcap.PACK_PATH
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps(raw, sort_keys=True),
                encoding="utf-8",
            )
            out = regcap.verify_property_request(
                request(regcap.CCOB, "FUNCTION::LOSS_ABSORPTION"),
                repo_root=root,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("PACK_GIT_BLOB_DRIFT", out["reason"])

    def test_authority_never_grants_terminal_credit(self):
        with patch.object(regcap, "verify_projection_pack", side_effect=fake_source_result):
            out = regcap.verify_property_request(
                request(regcap.TLAC, "REGIME::RESOLUTION"),
                repo_root=ROOT,
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
