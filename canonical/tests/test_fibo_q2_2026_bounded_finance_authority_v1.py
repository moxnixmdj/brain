from __future__ import annotations

import copy
from pathlib import Path
import unittest

from canonical.runtime import fibo_q2_2026_bounded_finance_authority_v1 as fibo

ROOT = Path(__file__).resolve().parents[2]

PROMISSORY_NOTE = "https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/PromissoryNote"
DEBT_INSTRUMENT = "https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/DebtInstrument"
FINANCIAL_INSTRUMENT = "https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/FinancialInstrument"
SECURITY = "https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/Security"


class FiboBoundedFinanceAuthorityTests(unittest.TestCase):
    def test_exact_pack_authenticates(self):
        out = fibo.load_pack(repo_root=ROOT)
        self.assertTrue(out["pass"])
        self.assertEqual(out["concept_count"], 241)
        self.assertEqual(out["edge_count"], 164)
        self.assertFalse(out["open_world_finance_ontology_complete"])
        self.assertFalse(out["terminal_authority"])

    def test_exact_label_is_candidate_only(self):
        out = fibo.exact_label_candidates("financial instrument", repo_root=ROOT)
        self.assertTrue(out["pass"])
        self.assertEqual(out["candidate_concept_ids"], [FINANCIAL_INSTRUMENT])
        self.assertFalse(out["contextual_semantic_identity_proved"])
        self.assertFalse(out["semantic_truth_authority"])

    def test_direct_edge_receipt_is_authenticated(self):
        request = fibo.make_edge_request(PROMISSORY_NOTE, DEBT_INSTRUMENT, repo_root=ROOT)
        out = fibo.verify_edge_receipt(request, repo_root=ROOT)
        self.assertTrue(out["pass"])
        self.assertEqual(out["relation"], "ENTAILS")
        self.assertTrue(out["source_semantics_authenticated"])
        self.assertTrue(out["target_semantics_authenticated"])
        self.assertTrue(out["relation_semantics_authenticated"])
        self.assertFalse(out["verification_authority_mutated"])

    def test_transitive_entailment_reuses_existing_dag_kernel(self):
        out = fibo.prove_entailment(PROMISSORY_NOTE, FINANCIAL_INSTRUMENT, repo_root=ROOT)
        self.assertTrue(out["pass"])
        self.assertTrue(out["left_entails_right"])
        self.assertEqual(
            out["left_to_right_path"],
            [PROMISSORY_NOTE, DEBT_INSTRUMENT, FINANCIAL_INSTRUMENT],
        )
        self.assertEqual(out["accepted_entailment_edge_count"], 2)
        self.assertFalse(out["terminal_authority"])

    def test_reverse_missing_path_remains_unknown(self):
        out = fibo.build_entailment_evidence(
            FINANCIAL_INSTRUMENT, PROMISSORY_NOTE, repo_root=ROOT
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"], "UNKNOWN__NO_POSITIVE_ENTAILMENT_PATH_IN_BOUND_SCOPE"
        )
        self.assertFalse(out["non_entailment_proved"])

    def test_fabricated_direct_edge_is_rejected(self):
        request = fibo.make_edge_request(PROMISSORY_NOTE, DEBT_INSTRUMENT, repo_root=ROOT)
        request["target_id"] = SECURITY
        out = fibo.verify_edge_receipt(request, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EDGE_NOT_DECLARED_IN_PINNED_FIBO_SCOPE")

    def test_pack_binding_tamper_is_rejected(self):
        request = fibo.make_edge_request(PROMISSORY_NOTE, DEBT_INSTRUMENT, repo_root=ROOT)
        request["pack_git_blob_sha"] = "0" * 40
        out = fibo.verify_edge_receipt(request, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EDGE_REQUEST_PACK_BINDING_INVALID")

    def test_out_of_scope_label_does_not_create_concept(self):
        out = fibo.exact_label_candidates("definitely not a FIBO term", repo_root=ROOT)
        self.assertTrue(out["pass"])
        self.assertEqual(out["candidate_concept_ids"], [])
        self.assertFalse(out["contextual_semantic_identity_proved"])


if __name__ == "__main__":
    unittest.main()
