from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import unittest

from canonical.runtime import professional_semantic_v2_v9_authority_gate_v1 as g


def batch():
    rows = [
        {
            "claim_id": f"{i:064x}",
            "leaf_id": f"PQ::R{i}::SEMANTIC",
            "root_id": f"R{i}",
        }
        for i in range(12)
    ]
    return {"pass": True, "rows": rows, "unique_claim_id_count": 12}


class Tests(unittest.TestCase):
    @patch.object(g.claim_batch, "verify")
    def test_missing_proof_is_explicit_nonpositive(self, verify):
        verify.return_value = batch()
        out = g.evaluate_claim(f"{3:064x}", repo_root=".")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["disposition"], g.NEGATIVE)
        self.assertFalse(out["positive_semantic_authority"])
        self.assertEqual(
            out["blocking_diagnostic"],
            "CLAIM_BOUND_POSITIVE_SEMANTIC_CERTIFICATE_REQUIRED",
        )

    @patch.object(g, "_safe_certificate")
    @patch.object(g.claim_batch, "verify")
    def test_invalid_reference_is_nonpositive_not_error_positive(self, verify, safe):
        verify.return_value = batch()
        safe.return_value = None
        out = g.evaluate_claim(
            f"{4:064x}",
            certificate_ref={"path": "canonical/evidence/x.json", "git_blob_sha": "a" * 40},
            repo_root=".",
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["disposition"], g.NEGATIVE)
        self.assertFalse(out["positive_semantic_authority"])

    @patch.object(g.trusted, "verify_certificate")
    @patch.object(g, "_safe_certificate")
    @patch.object(g.claim_batch, "verify")
    def test_trusted_verifier_rejection_forces_nonpositive(self, verify, safe, trusted):
        verify.return_value = batch()
        safe.return_value = Path("x")
        trusted.return_value = {
            "pass": False,
            "local_positive_semantic_witness_verified": False,
        }
        out = g.evaluate_claim(
            f"{5:064x}",
            certificate_ref={"path": "canonical/evidence/x.json", "git_blob_sha": "a" * 40},
            repo_root=".",
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["disposition"], g.NEGATIVE)
        self.assertFalse(out["positive_semantic_authority"])

    @patch.object(g.trusted, "verify_certificate")
    @patch.object(g, "_safe_certificate")
    @patch.object(g.claim_batch, "verify")
    def test_positive_requires_trusted_claim_bound_witness(self, verify, safe, trusted):
        verify.return_value = batch()
        safe.return_value = Path("x")
        trusted.return_value = {
            "pass": True,
            "local_positive_semantic_witness_verified": True,
        }
        out = g.evaluate_claim(
            f"{6:064x}",
            certificate_ref={"path": "canonical/evidence/x.json", "git_blob_sha": "a" * 40},
            repo_root=".",
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["disposition"], g.POSITIVE)
        self.assertTrue(out["positive_semantic_authority"])
        trusted.assert_called_once()

    @patch.object(g.claim_batch, "verify")
    def test_unknown_claim_fails_closed(self, verify):
        verify.return_value = batch()
        out = g.evaluate_claim("f" * 64, repo_root=".")
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CLAIM_NOT_CURRENT_V2_V9_SEMANTIC_CLAIM")

    @patch.object(g.claim_batch, "verify")
    def test_all_twelve_without_witnesses_are_safe_nonpositive(self, verify):
        verify.return_value = batch()
        out = g.evaluate_all({}, repo_root=".")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["claim_count"], 12)
        self.assertEqual(out["positive_claim_count"], 0)
        self.assertEqual(out["nonpositive_claim_count"], 12)
        self.assertTrue(out["universal_positive_requires_trusted_claim_bound_totality"])
        self.assertTrue(out["missing_or_invalid_proof_is_explicit_nonpositive"])
        self.assertFalse(out["positive_route_nonvacuity_proved"])
        self.assertFalse(out["semantic_property_truth_authority"])

    @patch.object(g.claim_batch, "verify")
    def test_unknown_binding_key_fails_closed(self, verify):
        verify.return_value = batch()
        out = g.evaluate_all(
            {"f" * 64: {"path": "canonical/evidence/x.json", "git_blob_sha": "a" * 40}},
            repo_root=".",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "UNKNOWN_SEMANTIC_CLAIM_BINDINGS")

    @patch.object(g.claim_batch, "verify")
    def test_global_authority_never_self_minted(self, verify):
        verify.return_value = batch()
        out = g.evaluate_all({}, repo_root=".")
        for key in (
            "semantic_property_truth_authority",
            "quality_authority",
            "acceptance_authority",
            "promotion_authority",
            "terminal_authority",
        ):
            self.assertFalse(out[key], key)
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
