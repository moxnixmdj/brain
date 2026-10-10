from __future__ import annotations

from copy import deepcopy
import json as stdjson
from pathlib import Path
import tempfile
from unittest.mock import patch
import unittest

from canonical.runtime import coverage_cc_r3_professional_r12_semantic_verify_v4 as v


ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "canonical/governance/COVERAGE_CC_R3_PROFESSIONAL_R12_SEMANTIC_CERTIFICATE_20261011_V4.json"
ACTIVE = stdjson.loads((ROOT / v.CLAIM_PATH).read_text(encoding="utf-8"))


def run_doc(doc, *, root_id=v.ROOT_ID, active=None):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "cert.json"
        p.write_text(stdjson.dumps(doc), encoding="utf-8")
        return v.verify_certificate(
            root=ROOT,
            certificate_path=p,
            active_claim=ACTIVE if active is None else active,
            root_id=root_id,
        )


class Tests(unittest.TestCase):
    def cert(self):
        return stdjson.loads(CERT.read_text(encoding="utf-8"))

    def test_exact_current_certificate_proves_cc_r3_only(self):
        out = v.verify_certificate(
            root=ROOT,
            certificate_path=CERT,
            active_claim=ACTIVE,
            root_id=v.ROOT_ID,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_claim_verified"])
        self.assertTrue(out["material_defeater_totality_verified"])
        self.assertTrue(out["stable_c8_nonvacuity_verified"])
        self.assertTrue(out["cc_r3_terminal_closure_proved"])
        self.assertEqual(out["proof_basis"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_wrong_root_or_claim_fails_closed(self):
        out = v.verify_certificate(
            root=ROOT,
            certificate_path=CERT,
            active_claim=ACTIVE,
            root_id="CC_R2_MISSION_SOUNDNESS_V1",
        )
        self.assertFalse(out["pass"])
        self.assertIn("ROOT_ID_MISMATCH", out["errors"])

        active = deepcopy(ACTIVE)
        active["claim_id"] = "0" * 64
        out = v.verify_certificate(
            root=ROOT,
            certificate_path=CERT,
            active_claim=active,
            root_id=v.ROOT_ID,
        )
        self.assertFalse(out["pass"])
        self.assertIn("ACTIVE_CLAIM_ID_MISMATCH", out["errors"])

    def test_universal_receipt_reference_drift_fails(self):
        c = self.cert()
        c["universal_totality_independent_verification"]["git_blob_sha"] = "0" * 40
        out = run_doc(c)
        self.assertFalse(out["pass"])
        self.assertIn(
            "UNIVERSAL_TOTALITY_INDEPENDENT_VERIFICATION_REF_MISMATCH",
            out["errors"],
        )

    def test_certificate_cannot_reintroduce_finite_catalog_or_cross_subject_transport(self):
        for field, value, expected in (
            ("finite_catalog_used", True, "CERTIFICATE_FINITE_CATALOG_USED"),
            (
                "cross_subject_property_authority_transport",
                True,
                "CERTIFICATE_CROSS_SUBJECT_AUTHORITY_TRANSPORT",
            ),
        ):
            with self.subTest(field=field):
                c = self.cert()
                c["theorem"][field] = value
                out = run_doc(c)
                self.assertFalse(out["pass"])
                self.assertIn(expected, out["errors"])

    def test_independent_composition_receipt_totality_is_load_bearing(self):
        original = v.json.loads

        def altered(text, *args, **kwargs):
            obj = original(text, *args, **kwargs)
            if (
                isinstance(obj, dict)
                and obj.get("schema")
                == "PROJECT_BRAIN_PROFESSIONAL_R12_UNIVERSAL_POSITIVE_GATE_CC_R3_COMPOSITION_INDEPENDENT_VERIFY_V1"
            ):
                obj = deepcopy(obj)
                obj["truth"]["material_defeater_totality_proved"] = False
            return obj

        with patch.object(v.json, "loads", side_effect=altered):
            out = v.verify_certificate(
                root=ROOT,
                certificate_path=CERT,
                active_claim=ACTIVE,
                root_id=v.ROOT_ID,
            )
        self.assertFalse(out["pass"])
        self.assertIn("UNIVERSAL_MATERIAL_TOTALITY_NOT_INDEPENDENTLY_PROVED", out["errors"])

    def test_live_universal_runtime_rejection_wins(self):
        with patch.object(
            v.universal,
            "verify",
            return_value={
                "pass": False,
                "material_defeater_totality_proved": False,
                "cc_r3_terminal_closure_proved": False,
            },
        ):
            out = v.verify_certificate(
                root=ROOT,
                certificate_path=CERT,
                active_claim=ACTIVE,
                root_id=v.ROOT_ID,
            )
        self.assertFalse(out["pass"])
        self.assertIn("UNIVERSAL_RUNTIME_REJECTED_CURRENT_BYTES", out["errors"])

    def test_property_and_terminal_authority_remain_zero(self):
        out = v.verify_certificate(
            root=ROOT,
            certificate_path=CERT,
            active_claim=ACTIVE,
            root_id=v.ROOT_ID,
        )
        self.assertTrue(out["pass"], out)
        for key in (
            "semantic_truth_authority",
            "quality_authority",
            "acceptance_authority",
            "promotion_authority",
            "terminal_authority",
        ):
            self.assertFalse(out[key], key)
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
