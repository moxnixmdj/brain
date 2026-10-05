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


def seed():
    cap = empty_capsule()
    return append_macrostep(
        cap,
        producer="research",
        action_ref="tool:web:source-a",
        action_spec={"tool": "web", "query": "alpha"},
        requires=[],
        provides=["evidence"],
        values={"evidence": {"claim": "alpha", "source": "source-a"}},
        evidence_inputs={
            "source-a": {
                "source": "https://example.invalid/a",
                "content_sha256": "a" * 64,
                "locator": "p1",
            }
        },
        lineage={"evidence": ["evidence:source-a", "action:tool:web:source-a"]},
    )


class Tests(unittest.TestCase):
    def test_append_only_state_handoff_and_projection(self):
        cap = seed()
        cap = append_macrostep(
            cap,
            producer="analysis",
            action_ref="tool:calc:1",
            action_spec={"tool": "calc", "expr": "40+2"},
            requires=["evidence"],
            provides=["result"],
            values={"result": {"value": 42}},
            evidence_inputs={},
            lineage={"result": ["state:evidence", "action:tool:calc:1"]},
        )
        verdict = verify_capsule(cap)
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertTrue(verdict["action_specs_content_bound"])
        self.assertTrue(verdict["evidence_units_content_bound"])
        self.assertEqual(project_context(cap, ["result"])["values"], {"result": {"value": 42}})

    def test_evidence_content_tamper_is_detected(self):
        cap = seed()
        bad = copy.deepcopy(cap)
        bad["records"][0]["evidence_inputs"]["source-a"]["locator"] = "p2"
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("EVIDENCE_HASH_MISMATCH", verdict["reason"])

    def test_action_spec_tamper_is_detected(self):
        cap = seed()
        bad = copy.deepcopy(cap)
        bad["records"][0]["action_spec"]["query"] = "beta"
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ACTION_SPEC_HASH_MISMATCH", verdict["reason"])

    def test_bare_evidence_identifier_has_no_v2_route(self):
        cap = empty_capsule()
        with self.assertRaises((CapsuleError, TypeError)):
            append_macrostep(
                cap,
                producer="x",
                action_ref="a",
                action_spec={"op": "x"},
                requires=[],
                provides=["out"],
                values={"out": 1},
                evidence_inputs=["source-a"],  # type: ignore[arg-type]
                lineage={"out": ["evidence:source-a"]},
            )

    def test_unbound_evidence_lineage_fails_closed(self):
        with self.assertRaises(CapsuleError):
            append_macrostep(
                empty_capsule(),
                producer="x",
                action_ref="a",
                action_spec={"op": "x"},
                requires=[],
                provides=["out"],
                values={"out": 1},
                evidence_inputs={},
                lineage={"out": ["evidence:not-bound", "action:a"]},
            )

    def test_noncanonical_nan_evidence_fails_closed(self):
        with self.assertRaises(CapsuleError):
            append_macrostep(
                empty_capsule(),
                producer="x",
                action_ref="a",
                action_spec={"op": "x"},
                requires=[],
                provides=["out"],
                values={"out": 1},
                evidence_inputs={"bad": {"value": float("nan")}},
                lineage={"out": ["evidence:bad", "action:a"]},
            )

    def test_state_value_tamper_is_detected(self):
        cap = seed()
        bad = copy.deepcopy(cap)
        bad["records"][0]["values"]["evidence"]["claim"] = "tampered"
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("VALUE_HASH_MISMATCH", verdict["reason"])

    def test_parent_hash_tamper_is_detected(self):
        cap = seed()
        cap = append_macrostep(
            cap,
            producer="analysis",
            action_ref="a2",
            action_spec={"op": "derive"},
            requires=["evidence"],
            provides=["out"],
            values={"out": 1},
            evidence_inputs={},
            lineage={"out": ["state:evidence", "action:a2"]},
        )
        bad = copy.deepcopy(cap)
        bad["records"][1]["parent_hash"] = "0" * 64
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("PARENT_MISMATCH", verdict["reason"])

    def test_input_binding_drift_is_detected(self):
        cap = seed()
        cap = append_macrostep(
            cap,
            producer="analysis",
            action_ref="a2",
            action_spec={"op": "derive"},
            requires=["evidence"],
            provides=["out"],
            values={"out": 1},
            evidence_inputs={},
            lineage={"out": ["state:evidence", "action:a2"]},
        )
        bad = copy.deepcopy(cap)
        bad["records"][1]["input_bindings"]["evidence"]["value_hash"] = "0" * 64
        verdict = verify_capsule(bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("INPUT_BINDING_DRIFT", verdict["reason"])

    def test_versioned_overwrite_preserves_exact_rollback(self):
        cap = seed()
        old_head = cap["head_hash"]
        cap = append_macrostep(
            cap,
            producer="revision",
            action_ref="tool:revise:1",
            action_spec={"tool": "revise", "mode": "exact"},
            requires=["evidence"],
            provides=["evidence"],
            values={"evidence": {"claim": "beta", "source": "source-a"}},
            evidence_inputs={
                "source-a": {
                    "source": "https://example.invalid/a",
                    "content_sha256": "a" * 64,
                    "locator": "p1",
                }
            },
            lineage={
                "evidence": [
                    "state:evidence",
                    "evidence:source-a",
                    "action:tool:revise:1",
                ]
            },
        )
        self.assertEqual(project_context(cap, ["evidence"])["values"]["evidence"]["claim"], "beta")
        rolled = rollback_to(cap, old_head)
        self.assertEqual(rolled["head_hash"], old_head)
        self.assertEqual(project_context(rolled, ["evidence"])["values"]["evidence"]["claim"], "alpha")

    def test_rollback_to_genesis_is_exact(self):
        self.assertEqual(rollback_to(seed(), GENESIS_HASH), empty_capsule())

    def test_unknown_rollback_target_fails_closed(self):
        with self.assertRaises(CapsuleError):
            rollback_to(seed(), "f" * 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
