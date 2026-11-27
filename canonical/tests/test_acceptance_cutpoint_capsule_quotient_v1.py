from __future__ import annotations

import copy
import unittest

from canonical.runtime.acceptance_cutpoint_capsule_quotient_v1 import (
    CutpointError,
    compile_brain_cutpoint,
    verify_cutpoint,
)
from canonical.runtime.composition_state_capsule_v2 import (
    append_macrostep,
    empty_capsule,
)


RECEIPT = {
    "path": "canonical/verification/runtime-channel-mincut.json",
    "git_blob_sha": "0123456789abcdef0123456789abcdef01234567",
    "scope_complete": True,
    "cross_role_state_edges_capsule_dominated": True,
    "acceptance_relevant_evidence_edges_capsule_dominated": True,
    "unknown_dynamic_edges_fail_closed": True,
    "exact_runtime_identity_bound": True,
    "independent_or_objective": True,
}


def capsule(*, evidence_excerpt="alpha", url="https://example.test/a"):
    return append_macrostep(
        empty_capsule(),
        producer_ref="worker-a",
        producer_descriptor={"worker_id": "worker-a", "role": "research"},
        action_ref="tool:web:source",
        action_descriptor={
            "tool": "web",
            "operation": "fetch",
            "args": {"url": url},
        },
        requires=[],
        provides=["research_state"],
        values={"research_state": {"claim": "alpha"}},
        evidence_values={
            "source": {
                "url": url,
                "excerpt": evidence_excerpt,
            }
        },
        lineage={
            "research_state": [
                "evidence:source",
                "action:tool:web:source",
                "producer:worker-a",
            ]
        },
    )


def compiled(cap=None, receipt=None):
    return compile_brain_cutpoint(
        capsule=cap or capsule(),
        acceptance_facts={"quality_floor_met": True, "cell": "C1"},
        scope_authority_facts={"authorized": True, "scope": "terminal"},
        terminal_facts={"terminal": False},
        channel_receipt=receipt or RECEIPT,
    )


class Tests(unittest.TestCase):
    def test_valid_cutpoint_passes_and_retains_full_capsule(self):
        cap = capsule()
        out = compiled(cap)
        self.assertEqual(verify_cutpoint(out)["status"], "PASS")
        self.assertTrue(out["full_capsule_retained"])
        self.assertEqual(out["quotient"]["composition_capsule_v2"], cap)

    def test_same_inputs_are_deterministic(self):
        cap = capsule()
        a = compiled(cap)
        b = compiled(copy.deepcopy(cap))
        self.assertEqual(a["quotient_sha256"], b["quotient_sha256"])
        self.assertEqual(a["quotient"], b["quotient"])

    def test_different_cross_role_evidence_cannot_collapse(self):
        a = compiled(capsule(evidence_excerpt="alpha"))
        b = compiled(capsule(evidence_excerpt="beta"))
        self.assertNotEqual(a["quotient_sha256"], b["quotient_sha256"])
        self.assertNotEqual(
            a["quotient"]["composition_capsule_v2"],
            b["quotient"]["composition_capsule_v2"],
        )

    def test_different_action_parameters_cannot_collapse(self):
        a = compiled(capsule(url="https://example.test/a"))
        b = compiled(capsule(url="https://example.test/b"))
        self.assertNotEqual(a["quotient_sha256"], b["quotient_sha256"])

    def test_tampered_capsule_fails_closed(self):
        cap = capsule()
        cap["records"][0]["values"]["research_state"]["claim"] = "tampered"
        with self.assertRaises(CutpointError):
            compiled(cap)

    def test_missing_state_mediation_receipt_fails_closed(self):
        receipt = copy.deepcopy(RECEIPT)
        receipt["cross_role_state_edges_capsule_dominated"] = False
        with self.assertRaises(CutpointError):
            compiled(receipt=receipt)

    def test_missing_evidence_mediation_receipt_fails_closed(self):
        receipt = copy.deepcopy(RECEIPT)
        receipt["acceptance_relevant_evidence_edges_capsule_dominated"] = False
        with self.assertRaises(CutpointError):
            compiled(receipt=receipt)

    def test_unknown_dynamic_edges_must_fail_closed(self):
        receipt = copy.deepcopy(RECEIPT)
        receipt["unknown_dynamic_edges_fail_closed"] = False
        with self.assertRaises(CutpointError):
            compiled(receipt=receipt)

    def test_receipt_must_bind_exact_runtime(self):
        receipt = copy.deepcopy(RECEIPT)
        receipt["exact_runtime_identity_bound"] = False
        with self.assertRaises(CutpointError):
            compiled(receipt=receipt)

    def test_receipt_must_be_independent_or_objective(self):
        receipt = copy.deepcopy(RECEIPT)
        receipt["independent_or_objective"] = False
        with self.assertRaises(CutpointError):
            compiled(receipt=receipt)

    def test_cutpoint_digest_tamper_fails_closed(self):
        out = compiled()
        out["quotient"]["terminal_facts"]["terminal"] = True
        verdict = verify_cutpoint(out)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("QUOTIENT_DIGEST_MISMATCH", verdict["reason"])

    def test_partial_capsule_replacement_fails_structural_verification(self):
        out = compiled()
        out["quotient"]["composition_capsule_v2"] = {
            "schema": "PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_V2",
            "genesis_hash": out["quotient"]["composition_capsule_v2"]["genesis_hash"],
            "head_hash": out["quotient"]["composition_capsule_v2"]["head_hash"],
            "records": [],
        }
        verdict = verify_cutpoint(out)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
