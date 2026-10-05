from __future__ import annotations

import copy
import unittest

from canonical.runtime.composition_state_capsule_v2 import (
    CapsuleError,
    GENESIS_HASH,
    append_macrostep,
    empty_capsule,
    project_context,
    rollback_to,
    verify_capsule,
)


PRODUCER = {"worker_id": "worker-a", "role": "research"}
ACTION = {
    "tool": "web",
    "operation": "fetch",
    "args": {"url": "https://example.test/a"},
}
EVIDENCE = {
    "source-a": {
        "url": "https://example.test/a",
        "sha256": "abc",
        "excerpt": "alpha",
    }
}


def seed():
    return append_macrostep(
        empty_capsule(),
        producer_ref="worker-a",
        producer_descriptor=PRODUCER,
        action_ref="tool:web:source-a",
        action_descriptor=ACTION,
        requires=[],
        provides=["evidence"],
        values={"evidence": {"claim": "alpha"}},
        evidence_values=EVIDENCE,
        lineage={
            "evidence": [
                "evidence:source-a",
                "action:tool:web:source-a",
                "producer:worker-a",
            ]
        },
    )


class Tests(unittest.TestCase):
    def test_valid_handoff_passes(self):
        cap = seed()
        cap = append_macrostep(
            cap,
            producer_ref="worker-b",
            producer_descriptor={
                "worker_id": "worker-b",
                "role": "analysis",
            },
            action_ref="calc:1",
            action_descriptor={
                "tool": "calculator",
                "expression": "6*7",
            },
            requires=["evidence"],
            provides=["result"],
            values={"result": 42},
            evidence_values={},
            lineage={
                "result": [
                    "state:evidence",
                    "action:calc:1",
                    "producer:worker-b",
                ]
            },
        )
        self.assertEqual(verify_capsule(cap)["status"], "PASS")
        self.assertEqual(
            project_context(cap, ["result"])["values"]["result"],
            42,
        )

    def test_evidence_payload_tamper_fails_closed(self):
        cap = seed()
        bad = copy.deepcopy(cap)
        bad["records"][0]["evidence_values"]["source-a"]["excerpt"] = "changed"
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("EVIDENCE_HASH_MISMATCH", verdict["reason"])

    def test_action_descriptor_tamper_fails_closed(self):
        cap = seed()
        bad = copy.deepcopy(cap)
        bad["records"][0]["action_descriptor"]["args"]["url"] = (
            "https://example.test/b"
        )
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ACTION_HASH_MISMATCH", verdict["reason"])

    def test_producer_descriptor_tamper_fails_closed(self):
        cap = seed()
        bad = copy.deepcopy(cap)
        bad["records"][0]["producer_descriptor"]["worker_id"] = "worker-z"
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("PRODUCER_HASH_MISMATCH", verdict["reason"])

    def test_same_evidence_label_different_payload_changes_head(self):
        a = seed()
        b = append_macrostep(
            empty_capsule(),
            producer_ref="worker-a",
            producer_descriptor=PRODUCER,
            action_ref="tool:web:source-a",
            action_descriptor=ACTION,
            requires=[],
            provides=["evidence"],
            values={"evidence": {"claim": "alpha"}},
            evidence_values={
                "source-a": {
                    "url": "https://example.test/a",
                    "sha256": "DIFFERENT",
                }
            },
            lineage={
                "evidence": [
                    "evidence:source-a",
                    "action:tool:web:source-a",
                    "producer:worker-a",
                ]
            },
        )
        self.assertNotEqual(a["head_hash"], b["head_hash"])

    def test_same_action_label_different_parameters_changes_head(self):
        a = seed()
        b = append_macrostep(
            empty_capsule(),
            producer_ref="worker-a",
            producer_descriptor=PRODUCER,
            action_ref="tool:web:source-a",
            action_descriptor={
                "tool": "web",
                "operation": "fetch",
                "args": {"url": "https://example.test/b"},
            },
            requires=[],
            provides=["evidence"],
            values={"evidence": {"claim": "alpha"}},
            evidence_values=EVIDENCE,
            lineage={
                "evidence": [
                    "evidence:source-a",
                    "action:tool:web:source-a",
                    "producer:worker-a",
                ]
            },
        )
        self.assertNotEqual(a["head_hash"], b["head_hash"])

    def test_missing_action_lineage_rejected(self):
        with self.assertRaises(CapsuleError):
            append_macrostep(
                empty_capsule(),
                producer_ref="worker-a",
                producer_descriptor=PRODUCER,
                action_ref="tool:web:source-a",
                action_descriptor=ACTION,
                requires=[],
                provides=["out"],
                values={"out": 1},
                evidence_values={},
                lineage={"out": ["producer:worker-a"]},
            )

    def test_missing_producer_lineage_rejected(self):
        with self.assertRaises(CapsuleError):
            append_macrostep(
                empty_capsule(),
                producer_ref="worker-a",
                producer_descriptor=PRODUCER,
                action_ref="tool:web:source-a",
                action_descriptor=ACTION,
                requires=[],
                provides=["out"],
                values={"out": 1},
                evidence_values={},
                lineage={"out": ["action:tool:web:source-a"]},
            )

    def test_state_value_tamper_detected(self):
        cap = seed()
        bad = copy.deepcopy(cap)
        bad["records"][0]["values"]["evidence"]["claim"] = "tampered"
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("VALUE_HASH_MISMATCH", verdict["reason"])

    def test_rollback_exact_prefix(self):
        cap = seed()
        head = cap["head_hash"]
        cap = append_macrostep(
            cap,
            producer_ref="worker-b",
            producer_descriptor={
                "worker_id": "worker-b",
                "role": "analysis",
            },
            action_ref="calc:1",
            action_descriptor={
                "tool": "calculator",
                "expression": "6*7",
            },
            requires=["evidence"],
            provides=["result"],
            values={"result": 42},
            evidence_values={},
            lineage={
                "result": [
                    "state:evidence",
                    "action:calc:1",
                    "producer:worker-b",
                ]
            },
        )
        rolled = rollback_to(cap, head)
        self.assertEqual(rolled["head_hash"], head)
        self.assertEqual(
            project_context(rolled, ["evidence"])["values"]["evidence"]["claim"],
            "alpha",
        )
        self.assertEqual(
            rollback_to(cap, GENESIS_HASH),
            empty_capsule(),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
