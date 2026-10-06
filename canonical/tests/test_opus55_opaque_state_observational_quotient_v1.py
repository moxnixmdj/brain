from __future__ import annotations

import unittest

from canonical.runtime.opus55_opaque_state_observational_quotient_v1 import (
    verify_observational_equivalence,
)


def trace(sig1: str = "vendor-A", sig2: str = "vendor-B"):
    return [
        {"type": "TEXT", "actor": "USER", "payload": "solve"},
        {
            "type": "OPAQUE_STATE_EMIT",
            "actor": "OPUS55_MODEL_POLICY",
            "carrier_kind": "THINKING_SIGNATURE",
            "carrier_id": sig1,
        },
        {"type": "TOOL_USE", "actor": "OPUS55_MODEL_POLICY", "payload": {"name": "calc", "x": 2}},
        {
            "type": "OPAQUE_STATE_ECHO",
            "actor": "OPUS55_MODEL_POLICY",
            "carrier_kind": "THINKING_SIGNATURE",
            "carrier_id": sig1,
        },
        {
            "type": "OPAQUE_STATE_EMIT",
            "actor": "OPUS55_MODEL_POLICY",
            "carrier_kind": "THINKING_SIGNATURE",
            "carrier_id": sig2,
        },
        {"type": "TEXT", "actor": "OPUS55_MODEL_POLICY", "payload": "4"},
    ]


class Tests(unittest.TestCase):
    def test_vendor_bytes_alpha_rename_away(self):
        left = trace("sig-opus-123", "sig-opus-456")
        right = trace("brain-state-X", "brain-state-Y")
        self.assertEqual(
            verify_observational_equivalence(left, right)["status"],
            "EQUIVALENT",
        )

    def test_visible_semantic_difference_survives_projection(self):
        right = trace("x", "y")
        right[-1]["payload"] = "5"
        self.assertEqual(
            verify_observational_equivalence(trace(), right)["status"],
            "NOT_EQUIVALENT",
        )

    def test_distinct_carriers_cannot_be_collapsed(self):
        right = trace("same", "same")
        verdict = verify_observational_equivalence(trace(), right)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("DUPLICATE_CARRIER_EMIT", verdict["reason"])

    def test_echo_before_emit_fails_closed(self):
        bad = [{
            "type": "OPAQUE_STATE_ECHO",
            "actor": "OPUS55_MODEL_POLICY",
            "carrier_kind": "THINKING_SIGNATURE",
            "carrier_id": "x",
        }]
        verdict = verify_observational_equivalence(bad, bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ECHO_BEFORE_EMIT", verdict["reason"])

    def test_carrier_kind_is_load_bearing(self):
        right = trace("x", "y")
        right[1]["carrier_kind"] = "OTHER_OPAQUE_STATE"
        right[3]["carrier_kind"] = "OTHER_OPAQUE_STATE"
        self.assertEqual(
            verify_observational_equivalence(trace(), right)["status"],
            "NOT_EQUIVALENT",
        )

    def test_missing_actor_fails_closed(self):
        bad = [{"type": "TEXT", "payload": "semantic"}]
        verdict = verify_observational_equivalence(bad, bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ACTOR_INVALID", verdict["reason"])

    def test_unknown_event_type_fails_closed(self):
        bad = [{"type": "MAGIC", "actor": "OPUS55_MODEL_POLICY", "payload": 1}]
        verdict = verify_observational_equivalence(bad, bad)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("UNKNOWN_TYPE", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
