from __future__ import annotations

import json
import struct
import unittest

from canonical.runtime.h100_unichart_safetensors_header_audit_v1 import (
    HeaderAuditError,
    parse_header_blob,
)


def _blob(header: dict) -> bytes:
    raw=json.dumps(header,separators=(",",":")).encode()
    return struct.pack("<Q",len(raw))+raw


class UniChartSafetensorsHeaderAuditTests(unittest.TestCase):
    def test_exact_enumeration_and_file_size(self):
        h={
          "__metadata__":{"format":"pt"},
          "a":{"dtype":"F32","shape":[2,3],"data_offsets":[0,24]},
          "b":{"dtype":"I64","shape":[2],"data_offsets":[24,40]},
          "empty":{"dtype":"F32","shape":[0],"data_offsets":[40,40]},
        }
        blob=_blob(h)
        out=parse_header_blob(blob,expected_file_size=len(blob)+40)
        self.assertEqual(out["tensor_count"],3)
        self.assertEqual(out["total_stored_elements"],8)
        self.assertEqual(out["floating_stored_elements"],6)
        self.assertEqual(out["nonfloating_stored_elements"],2)
        self.assertEqual(out["tensor_payload_bytes"],40)
        self.assertEqual(out["dtype_elements"],{"F32":6,"I64":2})
        self.assertEqual([x["name"] for x in out["tensors"]],["a","b","empty"])
        self.assertEqual(len(out["tensor_manifest_sha256"]),64)
        self.assertEqual(out["h100_credit_delta"],0)

    def test_tensor_byte_mismatch_fails_closed(self):
        h={"a":{"dtype":"F32","shape":[2],"data_offsets":[0,7]}}
        with self.assertRaisesRegex(HeaderAuditError,"TENSOR_BYTE_MISMATCH"):
            parse_header_blob(_blob(h))

    def test_payload_gap_fails_closed(self):
        h={
          "a":{"dtype":"F32","shape":[1],"data_offsets":[0,4]},
          "b":{"dtype":"F32","shape":[1],"data_offsets":[8,12]},
        }
        with self.assertRaisesRegex(HeaderAuditError,"PAYLOAD_GAP_OR_OVERLAP"):
            parse_header_blob(_blob(h))

    def test_wrong_total_file_size_fails_closed(self):
        h={"a":{"dtype":"F32","shape":[1],"data_offsets":[0,4]}}
        blob=_blob(h)
        with self.assertRaisesRegex(HeaderAuditError,"FILE_SIZE_MISMATCH"):
            parse_header_blob(blob,expected_file_size=len(blob)+5)


if __name__=="__main__":
    unittest.main(verbosity=2)
