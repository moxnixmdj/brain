"""Exact UniChart safetensors header enumeration for H100.

Reads only the safetensors header bytes. It enumerates every stored tensor name,
dtype, shape, and data offset, verifies the payload interval structure, and
computes exact stored tensor element/byte totals.

This does not download or execute model weights and creates no capability credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path
from typing import Any

DTYPE_BYTES = {
    "BOOL": 1,
    "U8": 1,
    "I8": 1,
    "F8_E4M3": 1,
    "F8_E5M2": 1,
    "I16": 2,
    "U16": 2,
    "F16": 2,
    "BF16": 2,
    "I32": 4,
    "U32": 4,
    "F32": 4,
    "I64": 8,
    "U64": 8,
    "F64": 8,
}
SCHEMA = "PROJECT_BRAIN_H100_UNICHART_SAFETENSORS_HEADER_ENUMERATION_V1"


class HeaderAuditError(ValueError):
    pass


def _numel(shape: list[int]) -> int:
    out = 1
    for x in shape:
        if not isinstance(x, int) or isinstance(x, bool) or x < 0:
            raise HeaderAuditError("SHAPE_INVALID")
        out *= x
    return out


def parse_header_blob(blob: bytes, *, expected_file_size: int | None = None) -> dict[str, Any]:
    if len(blob) < 8:
        raise HeaderAuditError("HEADER_PREFIX_TRUNCATED")
    header_len = struct.unpack("<Q", blob[:8])[0]
    if header_len <= 0 or header_len > 16_000_000:
        raise HeaderAuditError("HEADER_LENGTH_INVALID")
    if len(blob) != 8 + header_len:
        raise HeaderAuditError(
            f"HEADER_BLOB_LENGTH_MISMATCH:{len(blob)}!={8 + header_len}"
        )
    try:
        header = json.loads(blob[8:].decode("utf-8"))
    except Exception as exc:
        raise HeaderAuditError("HEADER_JSON_INVALID") from exc
    if not isinstance(header, dict):
        raise HeaderAuditError("HEADER_NOT_OBJECT")

    rows: list[dict[str, Any]] = []
    dtype_tensor_counts: Counter[str] = Counter()
    dtype_elements: Counter[str] = Counter()
    dtype_payload_bytes: Counter[str] = Counter()

    for name, meta in header.items():
        if name == "__metadata__":
            continue
        if not isinstance(name, str) or not name:
            raise HeaderAuditError("TENSOR_NAME_INVALID")
        if not isinstance(meta, dict):
            raise HeaderAuditError(f"TENSOR_META_INVALID:{name}")
        dtype = meta.get("dtype")
        shape = meta.get("shape")
        offsets = meta.get("data_offsets")
        if dtype not in DTYPE_BYTES:
            raise HeaderAuditError(f"DTYPE_UNSUPPORTED:{name}:{dtype}")
        if not isinstance(shape, list):
            raise HeaderAuditError(f"SHAPE_NOT_LIST:{name}")
        if (
            not isinstance(offsets, list)
            or len(offsets) != 2
            or not all(isinstance(x, int) and not isinstance(x, bool) for x in offsets)
        ):
            raise HeaderAuditError(f"OFFSETS_INVALID:{name}")
        start, end = offsets
        if start < 0 or end < start:
            raise HeaderAuditError(f"OFFSET_ORDER_INVALID:{name}")
        numel = _numel(shape)
        expected_bytes = numel * DTYPE_BYTES[dtype]
        actual_bytes = end - start
        if actual_bytes != expected_bytes:
            raise HeaderAuditError(
                f"TENSOR_BYTE_MISMATCH:{name}:{actual_bytes}!={expected_bytes}"
            )
        rows.append(
            {
                "name": name,
                "dtype": dtype,
                "shape": shape,
                "numel": numel,
                "data_start": start,
                "data_end": end,
                "payload_bytes": actual_bytes,
            }
        )
        dtype_tensor_counts[dtype] += 1
        dtype_elements[dtype] += numel
        dtype_payload_bytes[dtype] += actual_bytes

    if not rows:
        raise HeaderAuditError("NO_TENSORS")

    nonempty = sorted((r["data_start"], r["data_end"], r["name"]) for r in rows if r["data_end"] > r["data_start"])
    cursor = 0
    for start, end, name in nonempty:
        if start != cursor:
            raise HeaderAuditError(f"PAYLOAD_GAP_OR_OVERLAP:{name}:{start}!={cursor}")
        cursor = end

    payload_bytes = cursor
    exact_file_size_from_header = 8 + header_len + payload_bytes
    if expected_file_size is not None and exact_file_size_from_header != expected_file_size:
        raise HeaderAuditError(
            "FILE_SIZE_MISMATCH:"
            f"{exact_file_size_from_header}!={expected_file_size}"
        )

    total_elements = sum(r["numel"] for r in rows)
    floating_elements = sum(
        r["numel"]
        for r in rows
        if r["dtype"].startswith("F") or r["dtype"] == "BF16"
    )
    nonfloating_elements = total_elements - floating_elements
    tensor_manifest = sorted(rows, key=lambda r: r["name"])
    manifest_bytes = json.dumps(
        tensor_manifest,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    tensor_manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_SAFETENSORS_HEADER_ENUMERATION",
        "header_length_bytes": header_len,
        "tensor_count": len(rows),
        "total_stored_elements": total_elements,
        "floating_stored_elements": floating_elements,
        "nonfloating_stored_elements": nonfloating_elements,
        "tensor_payload_bytes": payload_bytes,
        "exact_file_size_from_header": exact_file_size_from_header,
        "dtype_tensor_counts": dict(sorted(dtype_tensor_counts.items())),
        "dtype_elements": dict(sorted(dtype_elements.items())),
        "dtype_payload_bytes": dict(sorted(dtype_payload_bytes.items())),
        "metadata": header.get("__metadata__", {}),
        "tensor_manifest_sha256": tensor_manifest_sha256,
        "tensors": tensor_manifest,
        "first_tensor_name": tensor_manifest[0]["name"],
        "last_tensor_name": tensor_manifest[-1]["name"],
        "hard_nonclaims": [
            "NO_CLAIM_SAFETENSORS_VALUES_WERE_DOWNLOADED_OR_COMPARED_TO_PYTORCH_BIN",
            "NO_CLAIM_LOW_BIT_CAPABILITY_PRESERVATION",
            "NO_CHARTOGRAPHY_THRESHOLD_CREDIT",
            "NO_H100_CAPABILITY_OR_TERMINAL_CREDIT",
        ],
        "h100_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--header-file", required=True)
    ap.add_argument("--expected-file-size", type=int, required=True)
    args = ap.parse_args()
    blob = Path(args.header_file).read_bytes()
    print(
        json.dumps(
            parse_header_blob(blob, expected_file_size=args.expected_file_size),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
