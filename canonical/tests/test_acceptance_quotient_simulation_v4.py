from __future__ import annotations

import copy
import unittest

from canonical.runtime.acceptance_quotient_simulation_v3 import (
    verify_acceptance_quotient_certificate_v3,
)
from canonical.runtime.acceptance_quotient_simulation_v4 import (
    certificate_subject_sha256,
    edge_subject_sha256,
    verify_acceptance_quotient_certificate_v4,
)
from canonical.tests.test_acceptance_quotient_simulation_v3 import base as v3_base


def receipt(seed: str, **truths):
    return {
        "path": f"canonical/verification/{seed}.json",
        "git_blob_sha": (seed[0] if seed else "a") * 40,
        **truths,
    }


def bound_base():
    cert = copy.deepcopy(v3_base())
    subject = certificate_subject_sha256(cert)
    cert["certificate_subject_binding_receipt"] = receipt(
        "b",
        scope_complete=True,
        binds_relation_terminal_and_edges=True,
        independent_or_objective=True,
        subject_sha256=subject,
    )
    for key in (
        "abstraction_receipt",
        "relation_soundness_receipt",
        "terminal_acceptance_receipt",
        "causal_strategy_receipt",
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
    def test_bound_certificate_passes(self):
        verdict = verify_acceptance_quotient_certificate_v4(bound_base())
        self.assertEqual(verdict["status"], "PASS", verdict)

    def test_v3_accepts_relation_subject_replay_that_v4_rejects(self):
        cert = bound_base()
        cert["target_states"] = ["T0", "TX"]
        cert["terminal_target_states"] = ["TX"]
        cert["relation"] = [["T0", "B0"], ["TX", "B1"]]
        cert["target_cut_edges"] = [{"id": "E", "from": "T0", "to": "TX"}]

        v3 = verify_acceptance_quotient_certificate_v3(copy.deepcopy(cert))
        self.assertEqual(v3["status"], "PASS", v3)

        v4 = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(v4["status"], "FAIL_CLOSED")
        self.assertIn("SUBJECT_SHA256_MISMATCH", v4["reason"])

    def test_v3_accepts_edge_subject_replay_that_v4_rejects(self):
        cert = bound_base()
        cert["target_cut_edges"] = [{"id": "E2", "from": "T0", "to": "T1"}]
        cert["brain_macro_edges"][0]["covers_target_edge_ids"] = ["E2"]

        v3 = verify_acceptance_quotient_certificate_v3(copy.deepcopy(cert))
        self.assertEqual(v3["status"], "PASS", v3)

        v4 = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(v4["status"], "FAIL_CLOSED")
        self.assertIn("SUBJECT_SHA256_MISMATCH", v4["reason"])

    def test_global_receipt_must_bind_exact_subject(self):
        cert = bound_base()
        cert["relation_soundness_receipt"]["subject_sha256"] = "0" * 64
        verdict = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("RELATION_SOUNDNESS_RECEIPT_SUBJECT_SHA256_MISMATCH", verdict["reason"])

    def test_edge_receipt_must_bind_exact_edge_subject(self):
        cert = bound_base()
        cert["brain_macro_edges"][0]["realizability_receipt"]["edge_subject_sha256"] = "0" * 64
        verdict = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("REALIZABILITY_RECEIPT_EDGE_SUBJECT_SHA256_MISMATCH", verdict["reason"])

    def test_subject_binding_receipt_is_mandatory(self):
        cert = bound_base()
        cert.pop("certificate_subject_binding_receipt")
        verdict = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("CERTIFICATE_SUBJECT_BINDING_RECEIPT_INVALID", verdict["reason"])

    def test_v3_failure_still_fails_v4(self):
        cert = bound_base()
        cert["causal_strategy_receipt"]["single_owned_policy"] = False
        verdict = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("V3_CAUSAL_SEMANTIC_OR_GRAPH_CHECK_FAILED", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
