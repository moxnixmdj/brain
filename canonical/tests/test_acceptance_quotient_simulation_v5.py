from __future__ import annotations

import copy
import unittest

from canonical.runtime.acceptance_quotient_simulation_v4 import (
    verify_acceptance_quotient_certificate_v4,
)
from canonical.runtime.acceptance_quotient_simulation_v5 import (
    certificate_subject_sha256,
    edge_subject_sha256,
    verify_acceptance_quotient_certificate_v5,
)
from canonical.tests.test_acceptance_quotient_simulation_v4 import base as v4_base


def receipt(seed: str, **truths):
    return {
        "path": f"canonical/verification/{seed}.json",
        "git_blob_sha": (seed[0] if seed else "a") * 40,
        **truths,
    }


def bound_base():
    cert = copy.deepcopy(v4_base())
    cert["acceptance_semantics_class"] = "UNIVERSAL_TOP_SUPPORT"
    cert["distribution_free_dominance_receipt"] = receipt(
        "d",
        class_wide_top_support_dominance_proved=True,
        scope_complete=True,
        target_distribution_irrelevant=True,
        independent_or_objective=True,
    )
    subject = certificate_subject_sha256(cert)
    cert["certificate_subject_binding_receipt"] = receipt(
        "b",
        scope_complete=True,
        binds_relation_terminal_edges_and_acceptance_class=True,
        independent_or_objective=True,
        subject_sha256=subject,
    )
    for key in (
        "abstraction_receipt",
        "relation_soundness_receipt",
        "terminal_acceptance_receipt",
        "causal_strategy_receipt",
        "distribution_free_dominance_receipt",
    ):
        cert[key]["subject_sha256"] = subject
    for edge in cert["brain_macro_edges"]:
        edge_sha = edge_subject_sha256(subject, edge)
        for key in (
            "scope_authority_receipt",
            "realizability_receipt",
            "causal_policy_binding_receipt",
        ):
            edge[key]["edge_subject_sha256"] = edge_sha
    return cert


class Tests(unittest.TestCase):
    def test_exact_subject_bound_certificate_passes(self):
        verdict = verify_acceptance_quotient_certificate_v5(bound_base())
        self.assertEqual(verdict["status"], "PASS", verdict)

    def test_v4_accepts_relation_subject_replay_v5_rejects(self):
        cert = bound_base()
        cert["target_states"] = ["T0", "TX"]
        cert["terminal_target_states"] = ["TX"]
        cert["relation"] = [["T0", "B0"], ["TX", "B1"]]
        cert["target_cut_edges"] = [{"id": "E", "from": "T0", "to": "TX"}]

        v4 = verify_acceptance_quotient_certificate_v4(copy.deepcopy(cert))
        self.assertEqual(v4["status"], "PASS", v4)

        v5 = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(v5["status"], "FAIL_CLOSED")
        self.assertIn("SUBJECT_SHA256_MISMATCH", v5["reason"])

    def test_v4_accepts_edge_replay_v5_rejects(self):
        cert = bound_base()
        cert["target_cut_edges"] = [{"id": "E2", "from": "T0", "to": "T1"}]
        cert["brain_macro_edges"][0]["covers_target_edge_ids"] = ["E2"]

        v4 = verify_acceptance_quotient_certificate_v4(copy.deepcopy(cert))
        self.assertEqual(v4["status"], "PASS", v4)

        v5 = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(v5["status"], "FAIL_CLOSED")
        self.assertIn("SUBJECT_SHA256_MISMATCH", v5["reason"])

    def test_acceptance_class_change_invalidates_old_receipts(self):
        cert = bound_base()
        cert["acceptance_semantics_class"] = "NONPROBABILISTIC_COMPLETE_ORDER"
        cert["distribution_free_dominance_receipt"].update(
            complete_order_preservation_proved=True
        )
        cert["distribution_free_dominance_receipt"].pop(
            "class_wide_top_support_dominance_proved", None
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("SUBJECT_SHA256_MISMATCH", verdict["reason"])

    def test_global_receipt_subject_mismatch_fails(self):
        cert = bound_base()
        cert["relation_soundness_receipt"]["subject_sha256"] = "0" * 64
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("RELATION_SOUNDNESS_RECEIPT_SUBJECT_SHA256_MISMATCH", verdict["reason"])

    def test_edge_receipt_subject_mismatch_fails(self):
        cert = bound_base()
        cert["brain_macro_edges"][0]["realizability_receipt"]["edge_subject_sha256"] = "0" * 64
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("REALIZABILITY_RECEIPT_EDGE_SUBJECT_SHA256_MISMATCH", verdict["reason"])

    def test_v4_failure_still_fails_v5(self):
        cert = bound_base()
        cert["causal_strategy_receipt"]["single_owned_policy"] = False
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("V4_ACCEPTANCE_CAUSAL_SEMANTIC_GRAPH_CHECK_FAILED", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
