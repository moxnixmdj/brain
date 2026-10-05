from __future__ import annotations

import copy
import unittest

from canonical.runtime.composition_state_capsule_v1 import empty_capsule
from canonical.runtime.composition_state_capsule_referent_binding_v1 import (
    append_bound_macrostep,
    content_sha256,
    verify_binding,
)


def build(action, evidence):
    return append_bound_macrostep(
        empty_capsule(),
        producer="worker",
        action=action,
        requires=[],
        provides=["out"],
        values={"out": {"value": 1}},
        evidence={"source": evidence},
        lineage={"out": ["action", "evidence:source"]},
    )


class CompositionStateCapsuleReferentBindingTests(unittest.TestCase):
    def test_distinct_actions_produce_distinct_bound_capsules(self):
        a = build({"type": "tool", "args": {"path": "A"}}, {"claim": "same"})
        b = build({"type": "tool", "args": {"path": "B"}}, {"claim": "same"})
        self.assertNotEqual(
            a["binding_receipt"]["action_sha256"],
            b["binding_receipt"]["action_sha256"],
        )
        self.assertNotEqual(
            a["capsule"]["records"][0]["action_ref"],
            b["capsule"]["records"][0]["action_ref"],
        )
        self.assertNotEqual(
            a["capsule"]["records"][0]["record_hash"],
            b["capsule"]["records"][0]["record_hash"],
        )
        self.assertEqual(verify_binding(a["capsule"], a["binding_receipt"])["status"], "PASS")

    def test_distinct_evidence_produces_distinct_bound_capsules(self):
        a = build({"type": "tool"}, {"claim": "A"})
        b = build({"type": "tool"}, {"claim": "B"})
        self.assertNotEqual(
            a["binding_receipt"]["evidence"]["source"]["sha256"],
            b["binding_receipt"]["evidence"]["source"]["sha256"],
        )
        self.assertNotEqual(
            a["capsule"]["records"][0]["evidence_refs"],
            b["capsule"]["records"][0]["evidence_refs"],
        )
        self.assertNotEqual(
            a["capsule"]["records"][0]["record_hash"],
            b["capsule"]["records"][0]["record_hash"],
        )

    def test_action_receipt_tamper_fails_closed(self):
        out = build({"type": "tool", "args": {"x": 1}}, {"claim": "A"})
        receipt = copy.deepcopy(out["binding_receipt"])
        receipt["action"]["args"]["x"] = 2
        verdict = verify_binding(out["capsule"], receipt)
        self.assertEqual(verdict["status"], "FAIL_CLOSED", verdict)

    def test_action_hash_field_tamper_fails_closed(self):
        out = build({"type": "tool"}, {"claim": "A"})
        receipt = copy.deepcopy(out["binding_receipt"])
        receipt["action_sha256"] = "0" * 64
        verdict = verify_binding(out["capsule"], receipt)
        self.assertEqual(verdict["status"], "FAIL_CLOSED", verdict)
        self.assertIn("ACTION_HASH_MISMATCH", verdict["reason"])

    def test_evidence_content_tamper_fails_closed(self):
        out = build({"type": "tool"}, {"claim": "A"})
        receipt = copy.deepcopy(out["binding_receipt"])
        receipt["evidence"]["source"]["content"]["claim"] = "B"
        verdict = verify_binding(out["capsule"], receipt)
        self.assertEqual(verdict["status"], "FAIL_CLOSED", verdict)

    def test_evidence_hash_field_tamper_fails_closed(self):
        out = build({"type": "tool"}, {"claim": "A"})
        receipt = copy.deepcopy(out["binding_receipt"])
        receipt["evidence"]["source"]["sha256"] = "0" * 64
        verdict = verify_binding(out["capsule"], receipt)
        self.assertEqual(verdict["status"], "FAIL_CLOSED", verdict)
        self.assertIn("EVIDENCE_HASH_MISMATCH", verdict["reason"])

    def test_record_hash_rebind_fails_closed(self):
        out = build({"type": "tool"}, {"claim": "A"})
        receipt = copy.deepcopy(out["binding_receipt"])
        receipt["record_hash"] = "f" * 64
        verdict = verify_binding(out["capsule"], receipt)
        self.assertEqual(verdict["status"], "FAIL_CLOSED", verdict)
        self.assertIn("RECORD_HASH_MISMATCH", verdict["reason"])

    def test_receipt_hashes_are_actual_content_hashes(self):
        action = {"type": "tool", "args": {"x": [1, 2, 3]}}
        evidence = {"claim": "A", "source": {"id": 7}}
        out = build(action, evidence)
        receipt = out["binding_receipt"]
        self.assertEqual(receipt["action_sha256"], content_sha256(action))
        self.assertEqual(
            receipt["evidence"]["source"]["sha256"],
            content_sha256(evidence),
        )

    def test_verifier_never_claims_no_bypass(self):
        out = build({"type": "tool"}, {"claim": "A"})
        verdict = verify_binding(out["capsule"], out["binding_receipt"])
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertFalse(verdict["no_bypass_proved"])
        self.assertEqual(verdict["acceptance_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
