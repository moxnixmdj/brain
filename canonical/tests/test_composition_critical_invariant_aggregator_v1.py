from __future__ import annotations

import copy
import unittest

from canonical.runtime.composition_critical_invariant_aggregator_v1 import (
    verify_critical_invariant_certificate,
)


def receipt(name: str):
    return {
        "path": f"canonical/verification/{name}.json",
        "git_blob_sha": "0123456789abcdef0123456789abcdef01234567",
        "proved": True,
        "scope_complete": True,
        "independent_or_objective": True,
    }


def base():
    return {
        "critical_invariants": [
            {"id": "state_preserved", "critical": True},
            {"id": "provenance_complete", "critical": True},
        ],
        "registry_receipt": {
            "path": "canonical/verification/registry.json",
            "git_blob_sha": "1123456789abcdef0123456789abcdef01234567",
            "scope_complete_for_frozen_acceptance": True,
            "independent_or_objective": True,
        },
        "invariant_receipts": {
            "state_preserved": receipt("state"),
            "provenance_complete": receipt("provenance"),
        },
    }


class Tests(unittest.TestCase):
    def test_complete_registry_and_proofs_pass(self):
        verdict = verify_critical_invariant_certificate(base())
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertEqual(verdict["critical_failure_count"], 0)

    def test_registry_scope_completeness_is_load_bearing(self):
        cert = base()
        cert["registry_receipt"]["scope_complete_for_frozen_acceptance"] = False
        verdict = verify_critical_invariant_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("SCOPE_COMPLETE_FOR_FROZEN_ACCEPTANCE_NOT_TRUE", verdict["reason"])

    def test_registry_independence_is_load_bearing(self):
        cert = base()
        cert["registry_receipt"]["independent_or_objective"] = False
        self.assertEqual(
            verify_critical_invariant_certificate(cert)["status"],
            "FAIL_CLOSED",
        )

    def test_missing_invariant_receipt_fails_closed(self):
        cert = base()
        del cert["invariant_receipts"]["state_preserved"]
        verdict = verify_critical_invariant_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("INVARIANT_RECEIPT_MISSING", verdict["reason"])

    def test_extra_invariant_receipt_fails_closed(self):
        cert = base()
        cert["invariant_receipts"]["ghost"] = receipt("ghost")
        verdict = verify_critical_invariant_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("INVARIANT_RECEIPT_EXTRA", verdict["reason"])

    def test_unproved_invariant_fails_closed(self):
        cert = base()
        cert["invariant_receipts"]["state_preserved"]["proved"] = False
        verdict = verify_critical_invariant_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("PROVED_NOT_TRUE", verdict["reason"])

    def test_nonscope_complete_invariant_fails_closed(self):
        cert = base()
        cert["invariant_receipts"]["state_preserved"]["scope_complete"] = False
        verdict = verify_critical_invariant_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("SCOPE_COMPLETE_NOT_TRUE", verdict["reason"])

    def test_duplicate_registry_id_fails_closed(self):
        cert = base()
        cert["critical_invariants"].append(
            {"id": "state_preserved", "critical": True}
        )
        verdict = verify_critical_invariant_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("DUPLICATE", verdict["reason"])

    def test_noncritical_member_fails_closed(self):
        cert = base()
        cert["critical_invariants"][0]["critical"] = False
        verdict = verify_critical_invariant_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("NOT_CRITICAL", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
