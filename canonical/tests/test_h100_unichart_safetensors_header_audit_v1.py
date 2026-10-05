from __future__ import annotations

import json
import struct

import pytest

from canonical.runtime.h100_unichart_safetensors_header_audit_v1 import (
    HeaderAuditError,
    parse_header_blob,
)


def _blob(header: dict) -> bytes:
    raw=json.dumps(header,separators=(",",":")).encode()
    return struct.pack("<Q",len(raw))+raw


def test_exact_enumeration_and_file_size():
    h={
      "__metadata__":{"format":"pt"},
      "a":{"dtype":"F32","shape":[2,3],"data_offsets":[0,24]},
      "b":{"dtype":"I64","shape":[2],"data_offsets":[24,40]},
      "empty":{"dtype":"F32","shape":[0],"data_offsets":[40,40]},
    }
    blob=_blob(h)
    out=parse_header_blob(blob,expected_file_size=len(blob)+40)
    assert out["tensor_count"]==3
    assert out["total_stored_elements"]==8
    assert out["floating_stored_elements"]==6
    assert out["nonfloating_stored_elements"]==2
    assert out["tensor_payload_bytes"]==40
    assert out["dtype_elements"]=={"F32":6,"I64":2}
    assert [x["name"] for x in out["tensors"]]==["a","b","empty"]
    assert len(out["tensor_manifest_sha256"])==64
    assert out["h100_credit_delta"]==0


def test_tensor_byte_mismatch_fails_closed():
    h={"a":{"dtype":"F32","shape":[2],"data_offsets":[0,7]}}
    with pytest.raises(HeaderAuditError,match="TENSOR_BYTE_MISMATCH"):
        parse_header_blob(_blob(h))


def test_payload_gap_fails_closed():
    h={
      "a":{"dtype":"F32","shape":[1],"data_offsets":[0,4]},
      "b":{"dtype":"F32","shape":[1],"data_offsets":[8,12]},
    }
    with pytest.raises(HeaderAuditError,match="PAYLOAD_GAP_OR_OVERLAP"):
        parse_header_blob(_blob(h))


def test_wrong_total_file_size_fails_closed():
    h={"a":{"dtype":"F32","shape":[1],"data_offsets":[0,4]}}
    blob=_blob(h)
    with pytest.raises(HeaderAuditError,match="FILE_SIZE_MISMATCH"):
        parse_header_blob(blob,expected_file_size=len(blob)+5)
