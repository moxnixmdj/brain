from __future__ import annotations

import math
import struct
import unittest

from canonical.runtime.opus55_lossless_json_ir_v1 import (
    JsonValueCapsuleError,
    decode_json_value,
    encode_json_value,
    make_capsule,
    verify_and_decode_capsule,
)


class Opus55LosslessJsonIRTests(unittest.TestCase):
    def test_round_trip_preserves_json_semantics_and_scalar_types(self) -> None:
        value = {
            "null": None,
            "false": False,
            "true": True,
            "huge_int": 2**160,
            "negative_zero": -0.0,
            "float": 1.25,
            "unicode": "é🧠",
            "nested": [{"x": 1}, [], {}],
        }
        decoded = decode_json_value(encode_json_value(value))

        self.assertEqual(decoded["null"], None)
        self.assertIs(decoded["false"], False)
        self.assertIs(decoded["true"], True)
        self.assertEqual(decoded["huge_int"], 2**160)
        self.assertEqual(decoded["float"], 1.25)
        self.assertEqual(decoded["unicode"], "é🧠")
        self.assertEqual(decoded["nested"], [{"x": 1}, [], {}])
        self.assertEqual(
            struct.pack("!d", decoded["negative_zero"]),
            struct.pack("!d", -0.0),
        )

    def test_capsule_binds_actor_schema_channel_and_raw_wire(self) -> None:
        raw = b'{"type":"thinking","signature":"opaque"}'
        value = {"type": "thinking", "signature": "opaque"}
        capsule = make_capsule(
            value,
            schema_path="types/thinking_block.py::ThinkingBlock",
            actor="OPUS55_POLICY",
            channel="MODEL_OPAQUE_CONTINUATION_STATE",
            raw_wire_bytes=raw,
        )
        self.assertEqual(verify_and_decode_capsule(capsule), value)

    def test_capsule_hash_tamper_fails_closed(self) -> None:
        capsule = make_capsule(
            {"type": "text", "text": "x"},
            schema_path="types/text_block.py::TextBlock",
            actor="OPUS55_POLICY",
            channel="MODEL_VISIBLE_OUTPUT",
        )
        capsule["actor"] = "FALLBACK_MODEL"

        with self.assertRaisesRegex(JsonValueCapsuleError, "CAPSULE_HASH_MISMATCH"):
            verify_and_decode_capsule(capsule)

    def test_raw_wire_tamper_fails_closed_even_after_capsule_rehash_is_not_recomputed(self) -> None:
        capsule = make_capsule(
            {"x": 1},
            schema_path="x",
            actor="a",
            channel="c",
            raw_wire_bytes=b'{"x":1}',
        )
        capsule["raw_wire_sha256"] = "0" * 64

        with self.assertRaisesRegex(JsonValueCapsuleError, "CAPSULE_HASH_MISMATCH"):
            verify_and_decode_capsule(capsule)

    def test_non_json_values_fail_closed(self) -> None:
        for value in (float("nan"), float("inf"), b"bytes", {1: "not-json-key"}):
            with self.subTest(value=repr(value)):
                with self.assertRaises(JsonValueCapsuleError):
                    encode_json_value(value)

    def test_cycles_fail_closed(self) -> None:
        value: list[object] = []
        value.append(value)
        with self.assertRaisesRegex(JsonValueCapsuleError, "CYCLIC_VALUE_NOT_JSON"):
            encode_json_value(value)

    def test_unknown_tag_fails_closed(self) -> None:
        with self.assertRaisesRegex(JsonValueCapsuleError, "UNKNOWN_VALUE_TAG"):
            decode_json_value({"t": "future_unknown"})


if __name__ == "__main__":
    unittest.main()
