from __future__ import annotations

import json
import math
import struct
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.h100_unichart_lowbit_packer_v1 import (
    GROUP_SIZE,
    H100_BUDGET_BYTES,
    PackerError,
    _pack_codes,
    _unpack_codes,
    bits_for_tensor,
    bundle_audit,
    dequantize_group,
    projected_tensor_bytes,
    quantize_group,
)


class H100UniChartLowBitPackerTests(unittest.TestCase):
    def test_tensor_precision_policy(self):
        self.assertEqual(bits_for_tensor("encoder.encoder.layers.0.x", "F32"), 4)
        self.assertEqual(bits_for_tensor("decoder.model.layers.0.x", "F32"), 3)
        self.assertIsNone(bits_for_tensor("encoder.encoder.embeddings.position_ids", "I64"))

    def test_packed_code_lengths_are_exact(self):
        for bits in (3, 4):
            for n in (1, 2, 7, 8, 255, 256):
                limit=(1<<bits)-1
                codes=[i%(limit+1) for i in range(n)]
                blob=_pack_codes(codes,bits)
                self.assertEqual(len(blob),math.ceil(n*bits/8))
                self.assertEqual(_unpack_codes(blob,n,bits),codes)

    def test_quantize_dequantize_constant_group(self):
        meta,packed=quantize_group([1.25]*17,3)
        out=dequantize_group(meta,packed,17,3)
        self.assertEqual(len(meta),4)
        self.assertTrue(all(abs(x-1.25)<1e-3 for x in out))

    def test_quantize_dequantize_finite_group(self):
        src=[-1.0,-0.5,0.0,0.5,1.0]
        meta,packed=quantize_group(src,4)
        out=dequantize_group(meta,packed,len(src),4)
        self.assertEqual(len(out),len(src))
        self.assertLess(max(abs(a-b) for a,b in zip(src,out)),0.15)

    def test_nonfinite_weight_fails_closed(self):
        with self.assertRaisesRegex(PackerError,"NONFINITE_SOURCE_WEIGHT"):
            quantize_group([0.0,float("nan")],3)

    def test_projected_group_metadata_resets_per_tensor(self):
        # 257 values require 2 groups, not one cross-tensor shared group.
        expected=math.ceil(256*3/8)+4+math.ceil(1*3/8)+4
        self.assertEqual(
            projected_tensor_bytes(257,dtype="F32",bits=3),
            expected,
        )

    def test_i64_is_lossless_size(self):
        self.assertEqual(projected_tensor_bytes(200_000,dtype="I64",bits=None),1_600_000)

    def test_complete_bundle_audit_counts_every_file(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            packed=root/"m.bin"
            tok=root/"tok.model"
            cfg=root/"cfg.json"
            packed.write_bytes(b"x"*100)
            tok.write_bytes(b"y"*20)
            cfg.write_bytes(b"z"*3)
            out=bundle_audit(packed_checkpoint=packed,ancillary_files=[tok,cfg])
            self.assertTrue(out["pass"])
            self.assertEqual(out["total_bytes"],123)
            self.assertEqual(out["h100_credit_delta"],0)

    def test_duplicate_bundle_file_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x"
            p.write_bytes(b"x")
            with self.assertRaisesRegex(PackerError,"DUPLICATE_BUNDLE_FILE"):
                bundle_audit(packed_checkpoint=p,ancillary_files=[p])

    def test_budget_constant_is_decimal_100mb(self):
        self.assertEqual(H100_BUDGET_BYTES,100_000_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
