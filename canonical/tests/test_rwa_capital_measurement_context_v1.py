from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import rwa_capital_measurement_context_v1 as rwa

ROOT=Path(__file__).resolve().parents[2]


def fake_projection(pack):
    return {
        "pass":True,
        "receipt":{
            "fragment_ids":sorted(
                str(row["fragment_id"]) for row in pack.get("fragments",[])
            ),
            "receipt_sha256":"a"*64,
        },
        "source_fragment_authority":True,
        "terminal_authority":False,
    }


def resolve(text,target="capital ratio"):
    start=text.lower().index(target.lower())
    end=start+len(target)
    return rwa.resolve_occurrence(
        text,start=start,end=end,repo_root=ROOT,
        projection_verifier=fake_projection,
    )


class Tests(unittest.TestCase):
    def test_rwa_full_denominator_proves_measurement_frame(self):
        out=resolve("The capital ratio stood at 12.5% of risk-weighted assets.")
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_frame_id"],rwa.FRAME_ID)
        self.assertEqual(out["denominator_normalized"],"RISK_WEIGHTED_ASSETS")
        self.assertEqual(out["measurement_value_percent"],"12.5")
        self.assertTrue(out["measurement_basis_authority"])
        self.assertTrue(out["frame_authority"])

    def test_rwa_abbreviation_proves_same_frame(self):
        out=resolve("The capital ratio was 11% of RWA.")
        self.assertTrue(out["pass"],out)
        self.assertEqual(set(out["proved_atom_ids"]),set(rwa.PROVED_ATOMS))

    def test_bank_possessive_surface_is_allowed(self):
        out=resolve("The bank's capital ratio increased to 13.2% of RWA.")
        self.assertTrue(out["pass"],out)

    def test_explicit_cet1_modifier_does_not_mint_cet1_identity(self):
        out=resolve("The CET1 capital ratio stood at 10% of RWA.")
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["capital_tier_identity_authority"])
        self.assertFalse(out["concept_identity_authority"])

    def test_missing_denominator_is_unresolved(self):
        out=resolve("The capital ratio stood at 12.5%.")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"UNRESOLVED__NO_UNIQUE_RWA_MEASUREMENT_SIGNATURE")

    def test_total_assets_denominator_is_unresolved(self):
        out=resolve("The capital ratio stood at 12.5% of total assets.")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"UNRESOLVED__NO_UNIQUE_RWA_MEASUREMENT_SIGNATURE")

    def test_working_capital_ratio_modifier_is_rejected(self):
        text="The working capital ratio stood at 12.5% of RWA."
        start=text.index("capital ratio")
        out=rwa.resolve_occurrence(
            text,start=start,end=start+len("capital ratio"),repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"UNRESOLVED__UNSUPPORTED_PRENOMINAL_CAPITAL_RATIO_MODIFIER")

    def test_negated_context_is_unresolved(self):
        out=resolve("The capital ratio was not 12.5% of RWA.")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"UNRESOLVED__NEGATED_OR_NEGATIVE_LOCAL_CONTEXT")

    def test_non_capital_ratio_target_is_unresolved(self):
        text="The leverage ratio stood at 5% of RWA."
        start=text.index("leverage ratio")
        out=rwa.resolve_occurrence(
            text,start=start,end=start+len("leverage ratio"),repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"UNRESOLVED__TARGET_OCCURRENCE_OUTSIDE_BOUND_CAPITAL_RATIO_SURFACE")

    def test_source_authentication_failure_fails_closed(self):
        text="The capital ratio stood at 12.5% of RWA."
        start=text.index("capital ratio")
        out=rwa.resolve_occurrence(
            text,start=start,end=start+len("capital ratio"),repo_root=ROOT,
            projection_verifier=lambda _pack:{"pass":False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("PINNED_BASEL_SOURCE_AUTHORITY_FAILED",out["reason"])

    def test_pack_blob_drift_fails_closed(self):
        source=ROOT/rwa.PACK_PATH
        doc=json.loads(source.read_text(encoding="utf-8"))
        doc["scope_id"]+="-tampered"
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            target=root/rwa.PACK_PATH
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(doc,sort_keys=True),encoding="utf-8")
            text="The capital ratio stood at 12.5% of RWA."
            start=text.index("capital ratio")
            out=rwa.resolve_occurrence(
                text,start=start,end=start+len("capital ratio"),repo_root=root,
                projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("PACK_GIT_BLOB_DRIFT",out["reason"])

    def test_no_leaf_or_terminal_authority(self):
        out=resolve("The capital ratio was 9% of RWA.")
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["concept_identity_authority"])
        self.assertFalse(out["capital_tier_identity_authority"])
        self.assertFalse(out["buffer_identity_authority"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
