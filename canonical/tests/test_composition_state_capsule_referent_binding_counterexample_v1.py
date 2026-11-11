from __future__ import annotations

import hashlib
import json
import unittest

from canonical.runtime.composition_state_capsule_v1 import (
    append_macrostep,
    empty_capsule,
    verify_capsule,
)


def canonical_sha256(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class CompositionStateCapsuleReferentBindingCounterexampleTests(unittest.TestCase):
    def test_action_referent_bytes_are_not_an_input_to_v1_capsule(self):
        action_a = {"type": "tool", "args": {"path": "A"}}
        action_b = {"type": "tool", "args": {"path": "B"}}
        self.assertNotEqual(canonical_sha256(action_a), canonical_sha256(action_b))

        def build(_external_action):
            # _external_action is intentionally unavailable to append_macrostep:
            # the V1 API accepts only the caller-supplied token action_ref.
            return append_macrostep(
                empty_capsule(),
                producer="worker",
                action_ref="action:logical-name",
                requires=[],
                provides=["out"],
                values={"out": {"value": 1}},
                evidence_refs=[],
                lineage={"out": ["action:action:logical-name"]},
            )

        capsule_a = build(action_a)
        capsule_b = build(action_b)
        self.assertEqual(capsule_a, capsule_b)
        self.assertEqual(verify_capsule(capsule_a)["status"], "PASS")
        self.assertEqual(verify_capsule(capsule_b)["status"], "PASS")

    def test_non_content_addressed_action_token_is_accepted(self):
        capsule = append_macrostep(
            empty_capsule(),
            producer="worker",
            action_ref="human-readable-action-name",
            requires=[],
            provides=["out"],
            values={"out": 1},
            evidence_refs=[],
            lineage={"out": ["action:human-readable-action-name"]},
        )
        self.assertEqual(verify_capsule(capsule)["status"], "PASS")

    def test_evidence_referent_bytes_are_not_an_input_to_v1_capsule(self):
        evidence_a = {"source": "receipt", "claim": "A"}
        evidence_b = {"source": "receipt", "claim": "B"}
        self.assertNotEqual(canonical_sha256(evidence_a), canonical_sha256(evidence_b))

        def build(_external_evidence):
            return append_macrostep(
                empty_capsule(),
                producer="worker",
                action_ref="action-x",
                requires=[],
                provides=["out"],
                values={"out": 1},
                evidence_refs=["evidence:logical-name"],
                lineage={
                    "out": [
                        "evidence:evidence:logical-name",
                        "action:action-x",
                    ]
                },
            )

        capsule_a = build(evidence_a)
        capsule_b = build(evidence_b)
        self.assertEqual(capsule_a, capsule_b)
        self.assertEqual(verify_capsule(capsule_a)["status"], "PASS")
        self.assertEqual(verify_capsule(capsule_b)["status"], "PASS")

    def test_non_content_addressed_evidence_token_is_accepted(self):
        capsule = append_macrostep(
            empty_capsule(),
            producer="worker",
            action_ref="action-x",
            requires=[],
            provides=["out"],
            values={"out": 1},
            evidence_refs=["receipt-by-name-only"],
            lineage={
                "out": [
                    "evidence:receipt-by-name-only",
                    "action:action-x",
                ]
            },
        )
        self.assertEqual(verify_capsule(capsule)["status"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
