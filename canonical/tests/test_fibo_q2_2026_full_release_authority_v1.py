from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import fibo_q2_2026_full_release_authority_v1 as fibo
from canonical.runtime import semantic_relation_control_v1 as semantic_relation

ROOT = Path(__file__).resolve().parents[2]

ASSET_BACKED_CDS = (
    "https://spec.edmcouncil.org/fibo/ontology/DER/CreditDerivatives/"
    "CreditDefaultSwaps/AssetBackedCreditDefaultSwap"
)
CREDIT_DEFAULT_SWAP = (
    "https://spec.edmcouncil.org/fibo/ontology/DER/CreditDerivatives/"
    "CreditDefaultSwaps/CreditDefaultSwap"
)
LOAN = (
    "https://spec.edmcouncil.org/fibo/ontology/LOAN/LoansGeneral/"
    "Loans/Loan"
)
OFFERING_PROCESS = (
    "https://spec.edmcouncil.org/fibo/ontology/BP/SecuritiesIssuance/"
    "IssuanceProcess/OfferingProcess"
)
OFFERING = (
    "https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/"
    "FinancialProductsAndServices/Offering"
)


class FiboFullReleaseAuthorityTests(unittest.TestCase):
    def test_exact_full_pack_authenticates(self):
        out = fibo.load_pack(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["source_file_count"], 295)
        self.assertEqual(out["concept_count"], 2671)
        self.assertEqual(out["edge_count"], 3443)
        self.assertEqual(out["ambiguous_exact_label_surface_count"], 5)
        self.assertFalse(out["open_world_finance_ontology_complete"])
        self.assertFalse(out["imported_external_ontology_closure_complete"])
        self.assertFalse(out["terminal_authority"])

    def test_new_outside_core_exact_label_is_available(self):
        out = fibo.exact_label_candidates("loan", repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["candidate_concept_ids"], [LOAN])
        self.assertFalse(out["contextual_semantic_identity_proved"])
        self.assertFalse(out["semantic_truth_authority"])

    def test_ambiguous_exact_label_remains_multiple_candidates(self):
        out = fibo.exact_label_candidates("offering", repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["candidate_concept_ids"],
            sorted([OFFERING_PROCESS, OFFERING]),
        )
        self.assertFalse(out["contextual_semantic_identity_proved"])

    def test_derivatives_direct_edge_receipt_is_authenticated(self):
        request = fibo.make_edge_request(
            ASSET_BACKED_CDS,
            CREDIT_DEFAULT_SWAP,
            repo_root=ROOT,
        )
        out = fibo.verify_edge_receipt(request, repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relation"], "ENTAILS")
        self.assertTrue(out["relation_semantics_authenticated"])
        self.assertFalse(out["verification_authority_mutated"])

    def test_live_semantic_relation_controller_consumes_full_pack_receipt(self):
        built = fibo.build_entailment_evidence(
            ASSET_BACKED_CDS,
            CREDIT_DEFAULT_SWAP,
            repo_root=ROOT,
        )
        self.assertTrue(built["pass"], built)
        out = semantic_relation.resolve(
            {
                "left_id": ASSET_BACKED_CDS,
                "right_id": CREDIT_DEFAULT_SWAP,
                "left_surface": "asset-backed credit default swap",
                "right_surface": "credit default swap",
                "scope_id": fibo.SCOPE_ID,
                "required_relation": "LEFT_ENTAILS_RIGHT",
                "entailment_dag_evidence": built["evidence"],
                "expected_entailment_dag_sha256": built["evidence_sha256"],
            },
            relation_edge_verifier=lambda receipt: fibo.verify_edge_receipt(
                receipt,
                repo_root=ROOT,
            ),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertFalse(out["terminal_authority"])

    def test_reverse_missing_path_remains_unknown(self):
        out = fibo.build_entailment_evidence(
            CREDIT_DEFAULT_SWAP,
            ASSET_BACKED_CDS,
            repo_root=ROOT,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "UNKNOWN__NO_POSITIVE_ENTAILMENT_PATH_IN_BOUND_SCOPE",
        )
        self.assertFalse(out["non_entailment_proved"])

    def test_fabricated_direct_edge_is_rejected(self):
        request = fibo.make_edge_request(
            ASSET_BACKED_CDS,
            CREDIT_DEFAULT_SWAP,
            repo_root=ROOT,
        )
        request["target_id"] = LOAN
        out = fibo.verify_edge_receipt(request, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "EDGE_NOT_DECLARED_IN_PINNED_FIBO_SCOPE",
        )

    def test_pack_binding_tamper_is_rejected(self):
        request = fibo.make_edge_request(
            ASSET_BACKED_CDS,
            CREDIT_DEFAULT_SWAP,
            repo_root=ROOT,
        )
        request["pack_git_blob_sha"] = "0" * 40
        out = fibo.verify_edge_receipt(request, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "EDGE_REQUEST_PACK_BINDING_INVALID",
        )

    def test_corrupted_pack_bytes_fail_closed(self):
        source = ROOT / fibo.PACK_PATH
        raw = bytearray(source.read_bytes())
        raw[-1] ^= 1
        with TemporaryDirectory() as td:
            temp_root = Path(td)
            target = temp_root / fibo.PACK_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            with self.assertRaisesRegex(
                fibo.FiboFullReleaseAuthorityError,
                "PACK_GIT_BLOB_DRIFT",
            ):
                fibo.load_pack(repo_root=temp_root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
