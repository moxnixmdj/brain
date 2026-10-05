from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import canonical.runtime.h100_unichart_mixed_packer_v1 as p


def make_safetensors(path: Path) -> tuple[int, str]:
    tensors = [
        ("encoder.weight", "F32", [300], np.linspace(-1.5, 2.0, 300, dtype="<f4").tobytes()),
        ("decoder.weight", "F32", [257], np.linspace(-0.2, 0.7, 257, dtype="<f4").tobytes()),
        ("encoder.ids", "I64", [3], np.asarray([1, 2, 3], dtype="<i8").tobytes()),
    ]
    header = {"__metadata__": {"format": "pt"}}
    cursor = 0
    for name, dtype, shape, blob in tensors:
        header[name] = {"dtype": dtype, "shape": shape, "data_offsets": [cursor, cursor + len(blob)]}
        cursor += len(blob)
    raw = json.dumps(header, separators=(",", ":")).encode()
    out = struct.pack("<Q", len(raw)) + raw + b"".join(x[3] for x in tensors)
    path.write_bytes(out)
    audit = p.parse_header_blob(out[:8 + len(raw)], expected_file_size=len(out))
    return len(out), audit["tensor_manifest_sha256"]


class MixedPackerTests(unittest.TestCase):
    def test_code_pack_roundtrips(self):
        rng = np.random.default_rng(7)
        q4 = rng.integers(0, 16, size=(3, p.GROUP_SIZE), dtype=np.uint8)
        q3 = rng.integers(0, 8, size=(3, p.GROUP_SIZE), dtype=np.uint8)
        self.assertTrue(np.array_equal(q4, p._unpack_codes_4(p._pack_codes_4(q4).tobytes(), 3)))
        self.assertTrue(np.array_equal(q3, p._unpack_codes_3(p._pack_codes_3(q3).tobytes(), 3)))

    def test_real_file_created_and_partitioned(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "source.safetensors"
            size, manifest_sha = make_safetensors(src)
            out = td / "packed.h100ucq"
            with (
                patch.object(p, "EXPECTED_SOURCE_BYTES", size),
                patch.object(p, "EXPECTED_MANIFEST_SHA256", manifest_sha),
                patch.object(p, "EXPECTED_ENCODER_F32", 300),
                patch.object(p, "EXPECTED_DECODER_F32", 257),
                patch.object(p, "EXPECTED_I64", 3),
            ):
                receipt = p.pack_checkpoint(src, out, groups_per_chunk=1)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 0)
            self.assertEqual(receipt["status"], "PASS__REAL_MIXED_W4_ENCODER_W3_DECODER_PACKED_CHECKPOINT_CREATED")
            self.assertEqual(receipt["exact_partition"]["encoder_f32_elements"], 300)
            self.assertEqual(receipt["exact_partition"]["decoder_f32_elements"], 257)
            self.assertEqual(receipt["exact_partition"]["i64_elements"], 3)
            header = p.read_packed_header(out)
            rows = {x["name"]: x for x in header["tensors"]}
            self.assertEqual(rows["encoder.weight"]["bits"], 4)
            self.assertEqual(rows["decoder.weight"]["bits"], 3)
            self.assertEqual(rows["encoder.ids"]["storage"], "I64_RAW")
            self.assertEqual(len(receipt["packed_checkpoint_sha256"]), 64)

    def test_partial_group_does_not_use_padding_for_metadata(self):
        x = np.asarray([5.0, 6.0, 7.0], dtype=np.float32)
        record, stats = p._quantize_partial_group(x, 3)
        scale, offset = np.frombuffer(record[:4], dtype="<f2")
        self.assertGreater(float(offset), 4.9)
        self.assertGreater(float(scale), 0.0)
        self.assertEqual(stats["values"], 3)

    def test_unclassified_float_tensor_fails_closed(self):
        row = {"name": "mystery.weight", "dtype": "F32"}
        with self.assertRaisesRegex(p.PackError, "UNCLASSIFIED_FLOAT_TENSOR"):
            p._bits_for(row)


if __name__ == "__main__":
    unittest.main(verbosity=2)
