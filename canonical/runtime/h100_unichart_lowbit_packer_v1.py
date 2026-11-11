"""Deterministic low-bit UniChart packer for the H100 research path.

Input:
  - one safetensors checkpoint with exact F32/I64 tensor classes,
  - optional ancillary files required by the frozen runtime bundle.

Transformation:
  - F32 tensors whose names begin with "encoder." -> W4 affine group-256,
  - all other F32 tensors -> W3 affine group-256,
  - I64 tensors -> lossless little-endian int64 bytes,
  - group boundary resets at every tensor,
  - each quantized group stores FP16 scale + FP16 offset,
  - quantized codes are packed LSB-first and padded only at group boundary.

The packer is benchmark-blind. It consumes no task labels, prompts, or model outputs.
It fails closed if the complete emitted bundle exceeds 100,000,000 bytes.

This module intentionally does not claim capability preservation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
from pathlib import Path
from typing import Any, BinaryIO

H100_BUDGET_BYTES = 100_000_000
GROUP_SIZE = 256
SCHEMA = "PROJECT_BRAIN_H100_UNICHART_LOWBIT_PACKER_RESULT_V1"
MAGIC = b"H100UC1\0"


class PackerError(ValueError):
    pass


def _numel(shape: list[int]) -> int:
    out = 1
    for dim in shape:
        if not isinstance(dim, int) or isinstance(dim, bool) or dim < 0:
            raise PackerError("SHAPE_INVALID")
        out *= dim
    return out


def _parse_safetensors_header(f: BinaryIO) -> tuple[dict[str, Any], int]:
    prefix = f.read(8)
    if len(prefix) != 8:
        raise PackerError("SAFETENSORS_PREFIX_TRUNCATED")
    header_len = struct.unpack("<Q", prefix)[0]
    if header_len <= 0 or header_len > 16_000_000:
        raise PackerError("SAFETENSORS_HEADER_LENGTH_INVALID")
    raw = f.read(header_len)
    if len(raw) != header_len:
        raise PackerError("SAFETENSORS_HEADER_TRUNCATED")
    try:
        header = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise PackerError("SAFETENSORS_HEADER_JSON_INVALID") from exc
    if not isinstance(header, dict):
        raise PackerError("SAFETENSORS_HEADER_NOT_OBJECT")
    return header, 8 + header_len


def _tensor_rows(header: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name, meta in header.items():
        if name == "__metadata__":
            continue
        if not isinstance(name, str) or not name:
            raise PackerError("TENSOR_NAME_INVALID")
        if not isinstance(meta, dict):
            raise PackerError(f"TENSOR_META_INVALID:{name}")
        dtype = meta.get("dtype")
        shape = meta.get("shape")
        offsets = meta.get("data_offsets")
        if dtype not in {"F32", "I64"}:
            raise PackerError(f"UNSUPPORTED_DTYPE:{name}:{dtype}")
        if not isinstance(shape, list):
            raise PackerError(f"SHAPE_NOT_LIST:{name}")
        if (
            not isinstance(offsets, list)
            or len(offsets) != 2
            or not all(isinstance(x, int) and not isinstance(x, bool) for x in offsets)
        ):
            raise PackerError(f"OFFSETS_INVALID:{name}")
        start, end = offsets
        if start < 0 or end < start:
            raise PackerError(f"OFFSET_ORDER_INVALID:{name}")
        numel = _numel(shape)
        expected = numel * (4 if dtype == "F32" else 8)
        if end - start != expected:
            raise PackerError(f"TENSOR_BYTE_MISMATCH:{name}:{end-start}!={expected}")
        rows.append(
            {
                "name": name,
                "dtype": dtype,
                "shape": shape,
                "numel": numel,
                "data_start": start,
                "data_end": end,
            }
        )
    if not rows:
        raise PackerError("NO_TENSORS")
    rows.sort(key=lambda r: (r["data_start"], r["name"]))
    cursor = 0
    for row in rows:
        if row["data_start"] != cursor:
            raise PackerError(
                f"PAYLOAD_GAP_OR_OVERLAP:{row['name']}:{row['data_start']}!={cursor}"
            )
        cursor = row["data_end"]
    return rows


def bits_for_tensor(name: str, dtype: str) -> int | None:
    if dtype == "I64":
        return None
    if dtype != "F32":
        raise PackerError(f"UNSUPPORTED_DTYPE_FOR_BITS:{dtype}")
    return 4 if name.startswith("encoder.") else 3


def _pack_codes(codes: list[int], bits: int) -> bytes:
    limit = (1 << bits) - 1
    out = bytearray()
    acc = 0
    nbits = 0
    for q in codes:
        if q < 0 or q > limit:
            raise PackerError("QUANT_CODE_OUT_OF_RANGE")
        acc |= q << nbits
        nbits += bits
        while nbits >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            nbits -= 8
    if nbits:
        out.append(acc & 0xFF)
    expected = math.ceil(len(codes) * bits / 8)
    if len(out) != expected:
        raise PackerError(f"PACKED_LENGTH_MISMATCH:{len(out)}!={expected}")
    return bytes(out)


def _unpack_codes(blob: bytes, count: int, bits: int) -> list[int]:
    mask = (1 << bits) - 1
    out: list[int] = []
    acc = 0
    nbits = 0
    i = 0
    while len(out) < count:
        while nbits < bits:
            if i >= len(blob):
                raise PackerError("PACKED_CODES_TRUNCATED")
            acc |= blob[i] << nbits
            i += 1
            nbits += 8
        out.append(acc & mask)
        acc >>= bits
        nbits -= bits
    return out


def quantize_group(values: list[float], bits: int) -> tuple[bytes, bytes]:
    if not values:
        raise PackerError("EMPTY_QUANT_GROUP")
    qmax = (1 << bits) - 1
    if not all(math.isfinite(v) for v in values):
        raise PackerError("NONFINITE_SOURCE_WEIGHT")
    lo = min(values)
    hi = max(values)
    if hi == lo:
        scale = 0.0
        offset = lo
        codes = [0] * len(values)
    else:
        scale = (hi - lo) / qmax
        offset = lo
        codes = [
            min(qmax, max(0, int(round((v - offset) / scale))))
            for v in values
        ]
    try:
        meta = struct.pack("<ee", scale, offset)
    except OverflowError as exc:
        raise PackerError("FP16_METADATA_OVERFLOW") from exc
    return meta, _pack_codes(codes, bits)


def dequantize_group(meta: bytes, packed: bytes, count: int, bits: int) -> list[float]:
    if len(meta) != 4:
        raise PackerError("QUANT_METADATA_LENGTH_INVALID")
    scale, offset = struct.unpack("<ee", meta)
    codes = _unpack_codes(packed, count, bits)
    if scale == 0.0:
        return [float(offset)] * count
    return [float(offset + scale * q) for q in codes]


def projected_tensor_bytes(numel: int, *, dtype: str, bits: int | None) -> int:
    if dtype == "I64":
        return numel * 8
    if dtype != "F32" or bits not in {3, 4}:
        raise PackerError("PROJECTED_TENSOR_CLASS_INVALID")
    groups = math.ceil(numel / GROUP_SIZE)
    full, rem = divmod(numel, GROUP_SIZE)
    payload = full * math.ceil(GROUP_SIZE * bits / 8)
    if rem:
        payload += math.ceil(rem * bits / 8)
    metadata = groups * 4
    return payload + metadata


def projected_checkpoint_bytes(rows: list[dict[str, Any]]) -> int:
    return sum(
        projected_tensor_bytes(
            row["numel"],
            dtype=row["dtype"],
            bits=bits_for_tensor(row["name"], row["dtype"]),
        )
        for row in rows
    )


def _iter_f32_groups(
    f: BinaryIO,
    *,
    absolute_start: int,
    numel: int,
):
    f.seek(absolute_start)
    remaining = numel
    while remaining:
        n = min(GROUP_SIZE, remaining)
        raw = f.read(n * 4)
        if len(raw) != n * 4:
            raise PackerError("F32_TENSOR_TRUNCATED")
        values = list(struct.unpack("<" + "f" * n, raw))
        yield values
        remaining -= n


def _copy_exact(f: BinaryIO, out: BinaryIO, *, absolute_start: int, byte_count: int) -> None:
    f.seek(absolute_start)
    remaining = byte_count
    while remaining:
        chunk = f.read(min(1 << 20, remaining))
        if not chunk:
            raise PackerError("SOURCE_TENSOR_TRUNCATED")
        out.write(chunk)
        remaining -= len(chunk)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def build_packed_checkpoint(source: Path, output: Path) -> dict[str, Any]:
    source = Path(source)
    output = Path(output)
    with source.open("rb") as f:
        header, payload_base = _parse_safetensors_header(f)
        rows = _tensor_rows(header)
        manifest: list[dict[str, Any]] = []

        with output.open("wb+") as out:
            # Reserve magic + uint64 manifest length. Manifest is appended at end.
            out.write(MAGIC)
            out.write(struct.pack("<Q", 0))

            for row in rows:
                start = out.tell()
                bits = bits_for_tensor(row["name"], row["dtype"])
                if row["dtype"] == "I64":
                    _copy_exact(
                        f,
                        out,
                        absolute_start=payload_base + row["data_start"],
                        byte_count=row["numel"] * 8,
                    )
                    groups = 0
                else:
                    groups = 0
                    for values in _iter_f32_groups(
                        f,
                        absolute_start=payload_base + row["data_start"],
                        numel=row["numel"],
                    ):
                        meta, packed = quantize_group(values, bits)
                        out.write(meta)
                        out.write(packed)
                        groups += 1
                end = out.tell()
                manifest.append(
                    {
                        "name": row["name"],
                        "dtype": row["dtype"],
                        "shape": row["shape"],
                        "numel": row["numel"],
                        "bits": bits,
                        "groups": groups,
                        "data_start": start,
                        "data_end": end,
                    }
                )

            manifest_obj = {
                "schema": "PROJECT_BRAIN_H100_UNICHART_PACKED_CHECKPOINT_V1",
                "source_sha256": _sha256(source),
                "group_size": GROUP_SIZE,
                "f32_policy": "ENCODER_W4_OTHER_W3",
                "group_metadata": "FP16_SCALE_PLUS_FP16_OFFSET",
                "bit_order": "LSB_FIRST",
                "i64_policy": "LOSSLESS_LITTLE_ENDIAN_BYTES",
                "tensors": manifest,
            }
            manifest_bytes = json.dumps(
                manifest_obj,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            manifest_offset = out.tell()
            out.write(manifest_bytes)
            final_size = out.tell()

            out.seek(len(MAGIC))
            out.write(struct.pack("<Q", len(manifest_bytes)))
            out.flush()

    if final_size > H100_BUDGET_BYTES:
        output.unlink(missing_ok=True)
        raise PackerError(
            f"H100_BUDGET_EXCEEDED:{final_size}>{H100_BUDGET_BYTES}"
        )

    return {
        "schema": SCHEMA,
        "status": "PACKED_CHECKPOINT_CREATED__CAPABILITY_UNPROVED",
        "source": str(source),
        "source_sha256": manifest_obj["source_sha256"],
        "output": str(output),
        "output_sha256": _sha256(output),
        "output_bytes": final_size,
        "h100_budget_bytes": H100_BUDGET_BYTES,
        "margin_bytes": H100_BUDGET_BYTES - final_size,
        "tensor_count": len(rows),
        "manifest_offset": manifest_offset,
        "manifest_bytes": len(manifest_bytes),
        "projected_tensor_region_bytes": projected_checkpoint_bytes(rows),
        "hard_nonclaims": [
            "NO_CLAIM_CAPABILITY_PRESERVATION",
            "NO_CHARTOGRAPHY_THRESHOLD_CREDIT",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "h100_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def bundle_audit(
    *,
    packed_checkpoint: Path,
    ancillary_files: list[Path],
) -> dict[str, Any]:
    packed_checkpoint = Path(packed_checkpoint)
    rows = []
    total = packed_checkpoint.stat().st_size
    rows.append(
        {
            "path": str(packed_checkpoint),
            "bytes": packed_checkpoint.stat().st_size,
            "sha256": _sha256(packed_checkpoint),
            "role": "PACKED_CHECKPOINT",
        }
    )
    seen = {packed_checkpoint.resolve()}
    for raw in ancillary_files:
        p = Path(raw)
        rp = p.resolve()
        if rp in seen:
            raise PackerError("DUPLICATE_BUNDLE_FILE")
        seen.add(rp)
        size = p.stat().st_size
        total += size
        rows.append(
            {
                "path": str(p),
                "bytes": size,
                "sha256": _sha256(p),
                "role": "ANCILLARY",
            }
        )
    passed = total <= H100_BUDGET_BYTES
    return {
        "schema": "PROJECT_BRAIN_H100_UNICHART_COMPLETE_BUNDLE_AUDIT_V1",
        "status": "PASS__COMPLETE_BUNDLE_WITHIN_H100" if passed else "FAIL__H100_BUDGET_EXCEEDED",
        "pass": passed,
        "total_bytes": total,
        "h100_budget_bytes": H100_BUDGET_BYTES,
        "margin_bytes": H100_BUDGET_BYTES - total,
        "files": rows,
        "h100_credit_delta": 0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--ancillary", action="append", default=[])
    ap.add_argument("--result-json")
    args = ap.parse_args()

    result = build_packed_checkpoint(Path(args.source), Path(args.output))
    if args.ancillary:
        result["complete_bundle"] = bundle_audit(
            packed_checkpoint=Path(args.output),
            ancillary_files=[Path(x) for x in args.ancillary],
        )
        if not result["complete_bundle"]["pass"]:
            Path(args.output).unlink(missing_ok=True)
            raise PackerError("COMPLETE_BUNDLE_EXCEEDS_H100")

    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.result_json:
        Path(args.result_json).write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
