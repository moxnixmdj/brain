from __future__ import annotations

import math
import unittest

from canonical.runtime.opus55_schema_lossless_ir_encoder_v1 import (
    ACTORS,
    CHANNEL_KEYS,
    EncoderError,
    decode,
    encode,
    round_trip_equal,
    schema_members,
)

class Tests(unittest.TestCase):
    def test_every_frozen_member_round_trips_losslessly(self):
        total = 0
        for channel in CHANNEL_KEYS:
            for member in schema_members(channel):
                payload = {
                    "member": member,
                    "nested": [1, True, None, {"unicode": "Δ", "float": 1.25}],
                }
                self.assertTrue(
                    round_trip_equal(channel, member, payload, actor="UNKNOWN"),
                    (channel, member),
                )
                total += 1
        self.assertEqual(total, 178)

    def test_same_payload_different_schema_members_do_not_collapse(self):
        members = schema_members("stable.response_content")
        a = encode("stable.response_content", members[0], {"x": 1}, actor="OPUS55_POLICY")
        b = encode("stable.response_content", members[1], {"x": 1}, actor="OPUS55_POLICY")
        self.assertNotEqual(a, b)
        self.assertEqual(decode(a), {"x": 1})
        self.assertEqual(decode(b), {"x": 1})

    def test_unknown_member_fails_closed(self):
        with self.assertRaisesRegex(EncoderError, "UNKNOWN_SCHEMA_MEMBER"):
            encode("stable.response_content", "FutureGhostBlock", {}, actor="UNKNOWN")

    def test_unknown_channel_fails_closed(self):
        with self.assertRaisesRegex(EncoderError, "UNKNOWN_CHANNEL"):
            encode("future.channel", "TextBlock", {}, actor="UNKNOWN")

    def test_actor_is_explicit_not_inferred(self):
        member = schema_members("stable.response_content")[0]
        for actor in ACTORS:
            ir = encode("stable.response_content", member, {"x": 1}, actor=actor)
            self.assertEqual(ir["actor"], actor)
        with self.assertRaisesRegex(EncoderError, "UNKNOWN_ACTOR"):
            encode("stable.response_content", member, {}, actor="CLAIMED_BY_VIBES")

    def test_non_json_and_nan_fail_closed(self):
        member = schema_members("stable.response_content")[0]
        with self.assertRaisesRegex(EncoderError, "NON_JSON_PAYLOAD"):
            encode("stable.response_content", member, {1, 2}, actor="UNKNOWN")
        with self.assertRaisesRegex(EncoderError, "NON_JSON_PAYLOAD"):
            encode("stable.response_content", member, {"x": math.nan}, actor="UNKNOWN")

    def test_tampered_ir_identity_fails_closed(self):
        member = schema_members("stable.response_content")[0]
        ir = encode("stable.response_content", member, {"x": 1}, actor="UNKNOWN")
        ir["schema_member"] = "FutureGhostBlock"
        with self.assertRaisesRegex(EncoderError, "IR_MEMBER_NOT_IN_FROZEN_SCHEMA"):
            decode(ir)

    def test_all_expected_channel_counts(self):
        expected = {
            "stable.response_content": 12,
            "stable.request_content": 16,
            "stable.tool_definition": 21,
            "stable.stop_reason": 7,
            "stable.request_control": 18,
            "beta.response_content": 18,
            "beta.request_content": 25,
            "beta.tool_definition": 28,
            "beta.stop_reason": 8,
            "beta.request_control": 25,
        }
        self.assertEqual({k: len(schema_members(k)) for k in CHANNEL_KEYS}, expected)

if __name__ == "__main__":
    unittest.main(verbosity=2)
