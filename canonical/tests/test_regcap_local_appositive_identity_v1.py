from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_local_appositive_identity_v1 as app
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap


def fake_projection(pack):
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": sorted(
                str(x["fragment_id"]) for x in pack.get("fragments", [])
            ),
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_ccob_apposition_proves_local_identity(self):
        text = "The capital conservation buffer, a loss-absorbing cushion, remains usable."
        cs = text.index("capital conservation buffer")
        ce = cs + len("capital conservation buffer")
        ds = text.index("loss-absorbing cushion")
        de = ds + len("loss-absorbing cushion")
        with patch.object(app, "verify_projection_pack", side_effect=fake_projection):
            out = app.prove_local_equivalence(
                source_id="doc:A",
                source_text=text,
                concept_id=regcap.CCOB,
                concept_start=cs,
                concept_end=ce,
                descriptor_start=ds,
                descriptor_end=de,
                projection_verifier=fake_projection,
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relation"], "LOGICAL_EQUIVALENCE_IN_SCOPE")
        self.assertTrue(out["dag_result"]["logical_equivalence_in_scope"])
        self.assertFalse(out["global_alias_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_tlac_abbreviation_apposition_proves_local_identity(self):
        text = "TLAC, a loss-absorbing cushion, supports orderly resolution."
        cs = 0
        ce = 4
        ds = text.index("loss-absorbing cushion")
        de = ds + len("loss-absorbing cushion")
        out = app.prove_local_equivalence(
            source_id="doc:B",
            source_text=text,
            concept_id=regcap.TLAC,
            concept_start=cs,
            concept_end=ce,
            descriptor_start=ds,
            descriptor_end=de,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["concept_id"], regcap.TLAC)

    def test_ccyb_apposition_proves_local_identity(self):
        text = "The countercyclical buffer, a loss-absorbing cushion, may be released."
        cs = text.index("countercyclical buffer")
        ce = cs + len("countercyclical buffer")
        ds = text.index("loss-absorbing cushion")
        de = ds + len("loss-absorbing cushion")
        out = app.prove_local_equivalence(
            source_id="doc:C",
            source_text=text,
            concept_id=regcap.CCYB,
            concept_start=cs,
            concept_end=ce,
            descriptor_start=ds,
            descriptor_end=de,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)

    def test_naked_phrase_has_no_local_identity(self):
        text = "loss-absorbing cushion"
        out = app.evaluate_edge_evidence(
            {
                "schema": app.EDGE_EVIDENCE_SCHEMA,
                "source_id": "doc:A",
                "source_text": text,
                "concept_id": regcap.CCOB,
                "concept_start": 0,
                "concept_end": len("loss"),
                "descriptor_start": 0,
                "descriptor_end": len(text),
                "direction": "DESCRIPTOR_TO_CONCEPT",
            },
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertFalse(out["global_alias_authority"])

    def test_missing_appositive_commas_is_unresolved(self):
        text = "The capital conservation buffer is a loss-absorbing cushion."
        cs = text.index("capital conservation buffer")
        ce = cs + len("capital conservation buffer")
        ds = text.index("loss-absorbing cushion")
        de = ds + len("loss-absorbing cushion")
        out = app.evaluate_edge_evidence(
            {
                "schema": app.EDGE_EVIDENCE_SCHEMA,
                "source_id": "doc:A",
                "source_text": text,
                "concept_id": regcap.CCOB,
                "concept_start": cs,
                "concept_end": ce,
                "descriptor_start": ds,
                "descriptor_end": de,
                "direction": "DESCRIPTOR_TO_CONCEPT",
            },
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__APPOSITIVE_BRIDGE_NOT_CERTIFIED",
        )

    def test_wrong_descriptor_is_unresolved(self):
        text = "TLAC, a recapitalisation resource, is used in resolution."
        cs = 0
        ce = 4
        ds = text.index("recapitalisation resource")
        de = ds + len("recapitalisation resource")
        out = app.evaluate_edge_evidence(
            {
                "schema": app.EDGE_EVIDENCE_SCHEMA,
                "source_id": "doc:A",
                "source_text": text,
                "concept_id": regcap.TLAC,
                "concept_start": cs,
                "concept_end": ce,
                "descriptor_start": ds,
                "descriptor_end": de,
                "direction": "DESCRIPTOR_TO_CONCEPT",
            },
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "UNRESOLVED__DESCRIPTOR_OUTSIDE_BOUND_SCOPE")

    def test_untrusted_surface_fails_closed(self):
        text = "Mystery Buffer, a loss-absorbing cushion, exists."
        cs = 0
        ce = len("Mystery Buffer")
        ds = text.index("loss-absorbing cushion")
        de = ds + len("loss-absorbing cushion")
        out = app.evaluate_edge_evidence(
            {
                "schema": app.EDGE_EVIDENCE_SCHEMA,
                "source_id": "doc:A",
                "source_text": text,
                "concept_id": regcap.CCOB,
                "concept_start": cs,
                "concept_end": ce,
                "descriptor_start": ds,
                "descriptor_end": de,
                "direction": "DESCRIPTOR_TO_CONCEPT",
            },
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CONCEPT_SURFACE_NOT_AUTHENTICATED", out["reason"])

    def test_source_authority_failure_fails_closed(self):
        text = "TLAC, a loss-absorbing cushion, exists."
        ds = text.index("loss-absorbing cushion")
        de = ds + len("loss-absorbing cushion")
        out = app.evaluate_edge_evidence(
            {
                "schema": app.EDGE_EVIDENCE_SCHEMA,
                "source_id": "doc:A",
                "source_text": text,
                "concept_id": regcap.TLAC,
                "concept_start": 0,
                "concept_end": 4,
                "descriptor_start": ds,
                "descriptor_end": de,
                "direction": "DESCRIPTOR_TO_CONCEPT",
            },
            projection_verifier=lambda _pack: {"pass": False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("OFFICIAL_SURFACE_SOURCE_AUTHORITY_FAILED", out["reason"])

    def test_local_scope_changes_with_source_bytes(self):
        text1 = "TLAC, a loss-absorbing cushion, exists."
        text2 = "TLAC, a loss-absorbing cushion, remains."
        def run(text):
            ds = text.index("loss-absorbing cushion")
            de = ds + len("loss-absorbing cushion")
            return app.prove_local_equivalence(
                source_id="doc:A",
                source_text=text,
                concept_id=regcap.TLAC,
                concept_start=0,
                concept_end=4,
                descriptor_start=ds,
                descriptor_end=de,
                projection_verifier=fake_projection,
            )
        a = run(text1)
        b = run(text2)
        self.assertTrue(a["pass"], a)
        self.assertTrue(b["pass"], b)
        self.assertNotEqual(a["local_scope_id"], b["local_scope_id"])

    def test_no_global_alias_or_terminal_credit(self):
        text = "TLAC, a loss-absorbing cushion, exists."
        ds = text.index("loss-absorbing cushion")
        de = ds + len("loss-absorbing cushion")
        out = app.prove_local_equivalence(
            source_id="doc:A",
            source_text=text,
            concept_id=regcap.TLAC,
            concept_start=0,
            concept_end=4,
            descriptor_start=ds,
            descriptor_end=de,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["global_alias_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
