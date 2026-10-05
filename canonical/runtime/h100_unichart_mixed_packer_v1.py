"""Deterministic mixed W4/W3 UniChart packer for the H100 experiment.

Format H100UCQ1:
  8-byte magic: b"H100UCQ1"
  8-byte little-endian unsigned JSON-header length
  compact UTF-8 JSON header
  payload records in original safetensors payload order

F32 tensors under encoder.* use affine W4 group-256 quantization.
F32 tensors under decoder.* use affine W3 group-256 quantization.
Each quantization group stores FP16 scale + FP16 offset followed by fixed-width
packed codes. The last group is zero-padded only after its metadata is computed
from real values, so padding cannot alter quantization parameters.
I64 tensors are copied losslessly.

This runtime proves/creates a packed execution subject. It does not prove that
low-bit inference preserves UniChart capability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import mmap
import os
import struct
from pathlib import Path
from typing import Any

import numpy as np

from canonical.runtime.h100_unichart_safetensors_header_audit_v1 import parse_header_blob

MAGIC = b"H100UCQ1"
SCHEMA = "PROJECT_BRAIN_H100_UNICHART_MIXED_PACK_V1"
GROUP_SIZE = 256
EXPECTED_SOURCE_BYTES = 809_095_376
EXPECTED_MANIFEST_SHA256 = "8b32480b8f7981f3c8413941e522034f3779bef1187374f2ca836bc29af314c5"
EXPECTED_ENCODER_F32 = 74_180_728
EXPECTED_DECODER_F32 = 127_677_440
EXPECTED_I64 = 200_000
H100_BUDGET_BYTES = 100_000_000


class PackError(RuntimeError):
    pass


def _sha256(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _read_source_manifest(source: Path) -> tuple[dict[str, Any], int]:
    if source.stat().st_size != EXPECTED_SOURCE_BYTES:
        raise PackError(f"SOURCE_SIZE_MISMATCH:{source.stat().st_size}!={EXPECTED_SOURCE_BYTES}")
    with source.open("rb") as f:
        first8 = f.read(8)
        if len(first8) != 8:
            raise PackError("SOURCE_HEADER_PREFIX_TRUNCATED")
        header_len = struct.unpack("<Q", first8)[0]
        if header_len <= 0 or header_len > 16_000_000:
            raise PackError("SOURCE_HEADER_LENGTH_INVALID")
        f.seek(0)
        header_blob = f.read(8 + header_len)
    audit = parse_header_blob(header_blob, expected_file_size=EXPECTED_SOURCE_BYTES)
    if audit["tensor_manifest_sha256"] != EXPECTED_MANIFEST_SHA256:
        raise PackError(
            "SOURCE_MANIFEST_SHA_MISMATCH:"
            f"{audit['tensor_manifest_sha256']}!={EXPECTED_MANIFEST_SHA256}"
        )
    return audit, 8 + header_len


def _bits_for(row: dict[str, Any]) -> int | None:
    dtype = row["dtype"]
    name = row["name"]
    if dtype == "I64":
        return None
    if dtype != "F32":
        raise PackError(f"UNSUPPORTED_SOURCE_DTYPE:{name}:{dtype}")
    if name.startswith("encoder."):
        return 4
    if name.startswith("decoder."):
        return 3
    raise PackError(f"UNCLASSIFIED_FLOAT_TENSOR:{name}")


def _code_bytes_per_group(bits: int) -> int:
    if bits not in (3, 4):
        raise PackError(f"BITS_INVALID:{bits}")
    return GROUP_SIZE * bits // 8


def _pack_codes_4(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=np.uint8).reshape(-1, GROUP_SIZE)
    lo = q[:, 0::2]
    hi = q[:, 1::2]
    return (lo | (hi << 4)).astype(np.uint8, copy=False)


def _pack_codes_3(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=np.uint8).reshape(-1, GROUP_SIZE)
    x = q.reshape(q.shape[0], GROUP_SIZE // 8, 8).astype(np.uint32)
    w = (
        x[:, :, 0]
        | (x[:, :, 1] << 3)
        | (x[:, :, 2] << 6)
        | (x[:, :, 3] << 9)
        | (x[:, :, 4] << 12)
        | (x[:, :, 5] << 15)
        | (x[:, :, 6] << 18)
        | (x[:, :, 7] << 21)
    )
    out = np.empty((q.shape[0], GROUP_SIZE * 3 // 8), dtype=np.uint8)
    out[:, 0::3] = (w & 0xFF).astype(np.uint8)
    out[:, 1::3] = ((w >> 8) & 0xFF).astype(np.uint8)
    out[:, 2::3] = ((w >> 16) & 0xFF).astype(np.uint8)
    return out


def _unpack_codes_4(blob: bytes, groups: int) -> np.ndarray:
    b = np.frombuffer(blob, dtype=np.uint8).reshape(groups, GROUP_SIZE // 2)
    q = np.empty((groups, GROUP_SIZE), dtype=np.uint8)
    q[:, 0::2] = b & 0x0F
    q[:, 1::2] = (b >> 4) & 0x0F
    return q


def _unpack_codes_3(blob: bytes, groups: int) -> np.ndarray:
    b = np.frombuffer(blob, dtype=np.uint8).reshape(groups, GROUP_SIZE * 3 // 8)
    lo = b[:, 0::3].astype(np.uint32)
    mi = b[:, 1::3].astype(np.uint32)
    hi = b[:, 2::3].astype(np.uint32)
    w = lo | (mi << 8) | (hi << 16)
    q8 = np.empty((groups, GROUP_SIZE // 8, 8), dtype=np.uint8)
    for i in range(8):
        q8[:, :, i] = ((w >> (3 * i)) & 0x7).astype(np.uint8)
    return q8.reshape(groups, GROUP_SIZE)


def _quantize_full_groups(block: np.ndarray, bits: int) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    if block.ndim != 2 or block.shape[1] != GROUP_SIZE:
        raise PackError("BLOCK_SHAPE_INVALID")
    if not np.isfinite(block).all():
        raise PackError("NONFINITE_WEIGHT")
    levels = (1 << bits) - 1
    mins = block.min(axis=1).astype(np.float32)
    maxs = block.max(axis=1).astype(np.float32)
    raw_scales = (maxs - mins) / np.float32(levels)
    scale16 = raw_scales.astype(np.float16)
    offset16 = mins.astype(np.float16)
    varying = maxs != mins
    if np.any(varying & (scale16 == 0)):
        raise PackError("QUANT_SCALE_UNDERFLOW")
    if not np.isfinite(scale16).all() or not np.isfinite(offset16).all():
        raise PackError("QUANT_METADATA_NONFINITE")
    s = scale16.astype(np.float32)
    o = offset16.astype(np.float32)
    q = np.zeros(block.shape, dtype=np.uint8)
    if np.any(varying):
        raw = np.rint((block[varying] - o[varying, None]) / s[varying, None])
        q[varying] = np.clip(raw, 0, levels).astype(np.uint8)
    recon = o[:, None] + s[:, None] * q.astype(np.float32)
    err = block - recon
    stats = {
        "sse": float(np.sum(err * err, dtype=np.float64)),
        "sae": float(np.sum(np.abs(err), dtype=np.float64)),
        "source_ss": float(np.sum(block * block, dtype=np.float64)),
        "max_abs_error": float(np.max(np.abs(err))) if err.size else 0.0,
        "values": int(block.size),
    }
    meta = np.empty((block.shape[0], 2), dtype="<f2")
    meta[:, 0] = scale16
    meta[:, 1] = offset16
    codes = _pack_codes_4(q) if bits == 4 else _pack_codes_3(q)
    return meta.view(np.uint8).reshape(block.shape[0], 4), codes, stats


def _quantize_partial_group(values: np.ndarray, bits: int) -> tuple[bytes, dict[str, float]]:
    values = np.asarray(values, dtype=np.float32).reshape(-1)
    if not (0 < len(values) < GROUP_SIZE):
        raise PackError("PARTIAL_GROUP_LENGTH_INVALID")
    if not np.isfinite(values).all():
        raise PackError("NONFINITE_WEIGHT")
    levels = (1 << bits) - 1
    mn = np.float32(values.min())
    mx = np.float32(values.max())
    raw_scale = np.float32(0.0 if mx == mn else (mx - mn) / np.float32(levels))
    scale16 = np.float16(raw_scale)
    offset16 = np.float16(mn)
    if mx != mn and scale16 == 0:
        raise PackError("QUANT_SCALE_UNDERFLOW")
    if not np.isfinite(scale16) or not np.isfinite(offset16):
        raise PackError("QUANT_METADATA_NONFINITE")
    s = np.float32(scale16)
    o = np.float32(offset16)
    q_real = np.zeros(len(values), dtype=np.uint8)
    if mx != mn:
        q_real = np.clip(np.rint((values - o) / s), 0, levels).astype(np.uint8)
    recon = o + s * q_real.astype(np.float32)
    err = values - recon
    q = np.zeros((1, GROUP_SIZE), dtype=np.uint8)
    q[0, : len(values)] = q_real
    codes = _pack_codes_4(q) if bits == 4 else _pack_codes_3(q)
    meta = np.asarray([scale16, offset16], dtype="<f2").view(np.uint8).tobytes()
    stats = {
        "sse": float(np.sum(err * err, dtype=np.float64)),
        "sae": float(np.sum(np.abs(err), dtype=np.float64)),
        "source_ss": float(np.sum(values * values, dtype=np.float64)),
        "max_abs_error": float(np.max(np.abs(err))) if err.size else 0.0,
        "values": int(values.size),
    }
    return meta + codes.tobytes(), stats


def _merge_stats(dst: dict[str, float], src: dict[str, float]) -> None:
    for k in ("sse", "sae", "source_ss", "values"):
        dst[k] += src[k]
    dst["max_abs_error"] = max(dst["max_abs_error"], src["max_abs_error"])


def _build_output_header(audit: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = sorted(audit["tensors"], key=lambda r: (r["data_start"], r["name"]))
    out_rows: list[dict[str, Any]] = []
    cursor = 0
    encoder_f32 = decoder_f32 = i64 = 0
    for row in rows:
        bits = _bits_for(row)
        numel = int(row["numel"])
        if bits is None:
            length = numel * 8
            kind = "I64_RAW"
            i64 += numel
            groups = 0
            record_bytes = 0
        else:
            groups = math.ceil(numel / GROUP_SIZE) if numel else 0
            record_bytes = 4 + _code_bytes_per_group(bits)
            length = groups * record_bytes
            kind = f"QAFFINE_W{bits}_G{GROUP_SIZE}_F16_SCALE_OFFSET"
            if bits == 4:
                encoder_f32 += numel
            else:
                decoder_f32 += numel
        out_rows.append(
            {
                "name": row["name"],
                "shape": row["shape"],
                "source_dtype": row["dtype"],
                "source_data_start": row["data_start"],
                "source_data_end": row["data_end"],
                "numel": numel,
                "storage": kind,
                "bits": bits,
                "group_size": GROUP_SIZE if bits else None,
                "group_count": groups,
                "record_bytes": record_bytes,
                "packed_data_start": cursor,
                "packed_data_end": cursor + length,
            }
        )
        cursor += length
    if encoder_f32 != EXPECTED_ENCODER_F32:
        raise PackError(f"ENCODER_COUNT_MISMATCH:{encoder_f32}!={EXPECTED_ENCODER_F32}")
    if decoder_f32 != EXPECTED_DECODER_F32:
        raise PackError(f"DECODER_COUNT_MISMATCH:{decoder_f32}!={EXPECTED_DECODER_F32}")
    if i64 != EXPECTED_I64:
        raise PackError(f"I64_COUNT_MISMATCH:{i64}!={EXPECTED_I64}")
    header = {
        "schema": SCHEMA,
        "source_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "source_file_bytes": EXPECTED_SOURCE_BYTES,
        "quantization": {
            "encoder_f32_bits": 4,
            "decoder_f32_bits": 3,
            "group_size": GROUP_SIZE,
            "metadata": "FP16_SCALE_PLUS_FP16_OFFSET",
            "rounding": "IEEE_RINT_TIES_TO_EVEN",
            "last_group_rule": "METADATA_FROM_REAL_VALUES_THEN_ZERO_PAD_CODES",
        },
        "exact_partition": {
            "encoder_f32_elements": encoder_f32,
            "decoder_f32_elements": decoder_f32,
            "i64_elements": i64,
        },
        "tensor_count": len(out_rows),
        "payload_bytes": cursor,
        "tensors": out_rows,
    }
    return header, out_rows


def pack_checkpoint(source: Path, output: Path, *, groups_per_chunk: int = 4096) -> dict[str, Any]:
    if groups_per_chunk <= 0:
        raise PackError("GROUPS_PER_CHUNK_INVALID")
    audit, source_payload_base = _read_source_manifest(source)
    header, rows = _build_output_header(audit)
    header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    stats = {
        "encoder": {"sse": 0.0, "sae": 0.0, "source_ss": 0.0, "max_abs_error": 0.0, "values": 0.0},
        "decoder": {"sse": 0.0, "sae": 0.0, "source_ss": 0.0, "max_abs_error": 0.0, "values": 0.0},
    }
    with source.open("rb") as sf, output.open("wb") as out:
        mm = mmap.mmap(sf.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            out.write(MAGIC)
            out.write(struct.pack("<Q", len(header_bytes)))
            out.write(header_bytes)
            for row in rows:
                numel = int(row["numel"])
                src_off = source_payload_base + int(row["source_data_start"])
                if row["storage"] == "I64_RAW":
                    out.write(mm[src_off : src_off + numel * 8])
                    continue
                bits = int(row["bits"])
                partition = "encoder" if bits == 4 else "decoder"
                full_groups = numel // GROUP_SIZE
                remainder = numel % GROUP_SIZE
                done_groups = 0
                while done_groups < full_groups:
                    g = min(groups_per_chunk, full_groups - done_groups)
                    value_start = done_groups * GROUP_SIZE
                    count = g * GROUP_SIZE
                    arr = np.frombuffer(
                        mm,
                        dtype="<f4",
                        count=count,
                        offset=src_off + value_start * 4,
                    )
                    block = np.array(arr, dtype=np.float32, copy=True).reshape(g, GROUP_SIZE)
                    del arr
                    meta, codes, st = _quantize_full_groups(block, bits)
                    records = np.empty((g, 4 + _code_bytes_per_group(bits)), dtype=np.uint8)
                    records[:, :4] = meta
                    records[:, 4:] = codes
                    out.write(records.tobytes(order="C"))
                    _merge_stats(stats[partition], st)
                    done_groups += g
                if remainder:
                    value_start = full_groups * GROUP_SIZE
                    arr = np.frombuffer(
                        mm,
                        dtype="<f4",
                        count=remainder,
                        offset=src_off + value_start * 4,
                    )
                    values = np.array(arr, dtype=np.float32, copy=True)
                    del arr
                    record, st = _quantize_partial_group(values, bits)
                    out.write(record)
                    _merge_stats(stats[partition], st)
        finally:
            mm.close()

    expected_bytes = len(MAGIC) + 8 + len(header_bytes) + int(header["payload_bytes"])
    actual_bytes = output.stat().st_size
    if actual_bytes != expected_bytes:
        raise PackError(f"PACKED_SIZE_MISMATCH:{actual_bytes}!={expected_bytes}")
    for part in ("encoder", "decoder"):
        s = stats[part]
        n = int(s["values"])
        s["values"] = n
        s["rmse"] = math.sqrt(s["sse"] / n) if n else 0.0
        s["mae"] = s["sae"] / n if n else 0.0
        s["relative_mse"] = s["sse"] / s["source_ss"] if s["source_ss"] else 0.0
    return {
        "schema": "PROJECT_BRAIN_H100_UNICHART_MIXED_PACK_RECEIPT_V1",
        "status": "PASS__REAL_MIXED_W4_ENCODER_W3_DECODER_PACKED_CHECKPOINT_CREATED"
        if actual_bytes <= H100_BUDGET_BYTES
        else "FAIL__PACKED_CHECKPOINT_EXCEEDS_H100",
        "source_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "packed_checkpoint_bytes": actual_bytes,
        "h100_budget_bytes": H100_BUDGET_BYTES,
        "packed_checkpoint_margin_bytes": H100_BUDGET_BYTES - actual_bytes,
        "packed_checkpoint_sha256": _sha256(output),
        "tensor_count": header["tensor_count"],
        "exact_partition": header["exact_partition"],
        "payload_bytes": header["payload_bytes"],
        "header_bytes": len(header_bytes),
        "quantization_error": stats,
        "hard_nonclaims": [
            "PACKED_FILE_CREATION_DOES_NOT_PROVE_CAPABILITY_PRESERVATION",
            "PACKED_FILE_ALONE_DOES_NOT_INCLUDE_THE_COMPLETE_ANCILLARY_RUNTIME_BUNDLE",
            "NO_CHARTOGRAPHY_THRESHOLD_CREDIT",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "h100_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def read_packed_header(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        magic = f.read(len(MAGIC))
        if magic != MAGIC:
            raise PackError("PACKED_MAGIC_INVALID")
        raw = f.read(8)
        if len(raw) != 8:
            raise PackError("PACKED_HEADER_PREFIX_TRUNCATED")
        n = struct.unpack("<Q", raw)[0]
        if n <= 0 or n > 16_000_000:
            raise PackError("PACKED_HEADER_LENGTH_INVALID")
        data = f.read(n)
        if len(data) != n:
            raise PackError("PACKED_HEADER_TRUNCATED")
    return json.loads(data.decode("utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--groups-per-chunk", type=int, default=4096)
    args = ap.parse_args()
    receipt = pack_checkpoint(
        Path(args.source),
        Path(args.output),
        groups_per_chunk=args.groups_per_chunk,
    )
    Path(args.receipt).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
