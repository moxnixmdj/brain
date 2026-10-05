from __future__ import annotations

import copy
import unittest

from canonical.runtime.composition_state_capsule_v2 import (
    CapsuleError,
    GENESIS_HASH,
    append_macrostep,
    empty_capsule,
    make_content_ref,
    project_context,
    rollback_to,
    verify_capsule,
)


def action(name, payload=None):
    return make_content_ref(name, {"action": name, "payload": payload or {}})


def evidence(name, payload=None):
    return make_content_ref(name, {"evidence": name, "payload": payload or {}})


def seed():
    cap = empty_capsule()
    a = action("web-source-a", {"url": "https://example.test/a"})
    e = evidence("source-a", {"claim": "alpha"})
    cap = append_macrostep(
        cap,
        producer="research",
        action_ref=a,
        requires=[],
        provides=["evidence"],
        values={"evidence": {"claim": "alpha", "source": "source-a"}},
        evidence_refs=[e],
        lineage={"evidence": ["evidence:source-a", "action:web-source-a"]},
    )
    return cap


class Tests(unittest.TestCase):
    def test_content_bound_state_handoff_and_projection(self):
        cap = seed()
        a = action("calc-1", {"expression": "40+2"})
        cap = append_macrostep(
            cap,
            producer="analysis",
            action_ref=a,
            requires=["evidence"],
            provides=["result"],
            values={"result": {"value": 42}},
            evidence_refs=[],
            lineage={"result": ["state:evidence", "action:calc-1"]},
        )
        verdict = verify_capsule(cap)
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertTrue(verdict["action_lineage_is_content_bound"])
        self.assertTrue(verdict["evidence_lineage_is_content_bound"])
        ctx = project_context(cap, ["result"])
        self.assertEqual(ctx["values"], {"result": {"value": 42}})
        self.assertNotIn("evidence", ctx["values"])

    def test_action_content_tamper_is_detected(self):
        cap = seed()
        bad = copy.deepcopy(cap)
        bad["records"][0]["action_ref"]["content"]["payload"]["url"] = "https://evil.test/"
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ACTION_CONTENT_HASH_MISMATCH", verdict["reason"])

    def test_evidence_content_tamper_is_detected(self):
        cap = seed()
        bad = copy.deepcopy(cap)
        bad["records"][0]["evidence_refs"][0]["content"]["payload"]["claim"] = "tampered"
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("EVIDENCE_ITEM_CONTENT_HASH_MISMATCH", verdict["reason"])

    def test_fake_action_hash_is_rejected_before_commit(self):
        bad_action = action("a")
        bad_action["sha256"] = "0" * 64
        with self.assertRaisesRegex(CapsuleError, "ACTION_REF_CONTENT_HASH_MISMATCH"):
            append_macrostep(
                empty_capsule(),
                producer="x",
                action_ref=bad_action,
                requires=[],
                provides=["out"],
                values={"out": 1},
                evidence_refs=[],
                lineage={"out": ["action:a"]},
            )

    def test_fake_evidence_hash_is_rejected_before_commit(self):
        e = evidence("e")
        e["sha256"] = "0" * 64
        with self.assertRaisesRegex(CapsuleError, "EVIDENCE_REFS_ITEM_CONTENT_HASH_MISMATCH"):
            append_macrostep(
                empty_capsule(),
                producer="x",
                action_ref=action("a"),
                requires=[],
                provides=["out"],
                values={"out": 1},
                evidence_refs=[e],
                lineage={"out": ["evidence:e", "action:a"]},
            )

    def test_state_input_binding_is_exact_prior_version(self):
        cap = seed()
        cap = append_macrostep(
            cap,
            producer="analysis",
            action_ref=action("a2"),
            requires=["evidence"],
            provides=["out"],
            values={"out": 1},
            evidence_refs=[],
            lineage={"out": ["state:evidence", "action:a2"]},
        )
        bad = copy.deepcopy(cap)
        bad["records"][1]["input_bindings"]["evidence"]["value_hash"] = "0" * 64
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("INPUT_BINDING_DRIFT", verdict["reason"])

    def test_undeclared_state_lineage_fails_closed(self):
        cap = seed()
        with self.assertRaisesRegex(CapsuleError, "UNDECLARED_STATE_LINEAGE"):
            append_macrostep(
                cap,
                producer="x",
                action_ref=action("a"),
                requires=[],
                provides=["out"],
                values={"out": 1},
                evidence_refs=[],
                lineage={"out": ["state:evidence", "action:a"]},
            )

    def test_unbound_evidence_lineage_fails_closed(self):
        with self.assertRaisesRegex(CapsuleError, "UNBOUND_EVIDENCE_LINEAGE"):
            append_macrostep(
                empty_capsule(),
                producer="x",
                action_ref=action("a"),
                requires=[],
                provides=["out"],
                values={"out": 1},
                evidence_refs=[],
                lineage={"out": ["evidence:not-bound", "action:a"]},
            )

    def test_value_tamper_is_detected(self):
        cap = seed()
        bad = copy.deepcopy(cap)
        bad["records"][0]["values"]["evidence"]["claim"] = "tampered"
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("VALUE_HASH_MISMATCH", verdict["reason"])

    def test_parent_tamper_is_detected(self):
        cap = seed()
        cap = append_macrostep(
            cap,
            producer="analysis",
            action_ref=action("a2"),
            requires=["evidence"],
            provides=["out"],
            values={"out": 1},
            evidence_refs=[],
            lineage={"out": ["state:evidence", "action:a2"]},
        )
        bad = copy.deepcopy(cap)
        bad["records"][1]["parent_hash"] = "0" * 64
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("PARENT_MISMATCH", verdict["reason"])

    def test_exact_prefix_rollback(self):
        cap = seed()
        old_head = cap["head_hash"]
        cap = append_macrostep(
            cap,
            producer="revision",
            action_ref=action("revise-1"),
            requires=["evidence"],
            provides=["evidence"],
            values={"evidence": {"claim": "beta"}},
            evidence_refs=[],
            lineage={"evidence": ["state:evidence", "action:revise-1"]},
        )
        rolled = rollback_to(cap, old_head)
        self.assertEqual(rolled["head_hash"], old_head)
        self.assertEqual(project_context(rolled, ["evidence"])["values"]["evidence"]["claim"], "alpha")

    def test_rollback_to_genesis(self):
        self.assertEqual(rollback_to(seed(), GENESIS_HASH), empty_capsule())


if __name__ == "__main__":
    unittest.main(verbosity=2)
