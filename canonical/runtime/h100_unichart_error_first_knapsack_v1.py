"""Source-only error-first precision knapsack for the H100 UniChart ChartQA donor.

This implements the already-precommitted policy:
- all F32 physical storages start at affine W3 group-256,
- I64 physical storages remain lossless,
- for every F32 group, compute source-only reconstruction SSE under W3 and W4,
- rank by descending (SSE_W3 - SSE_W4), then tensor name, then group index,
- upgrade the longest ranked prefix that keeps the COMPLETE bundle <= 100,000,000 bytes,
- never inspect prompts, labels, benchmark outputs, or packed-model answers.

The output stores a one-bit precision bitmap in its counted manifest.
Capability preservation is deliberately outside this module.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

from canonical.runtime.h100_unichart_chartqa_bin_packer_v1 import (
    parse_checkpoint_metadata,
)
from canonical.runtime.h100_unichart_lowbit_packer_v1 import (
    GROUP_SIZE,
    H100_BUDGET_BYTES,
    MAGIC,
    PackerError,
    _sha256,
    quantize_group,
)

SCHEMA = "PROJECT_BRAIN_H100_UNICHART_ERROR_FIRST_KNAPSACK_RESULT_V1"
PACKED_SCHEMA = "PROJECT_BRAIN_H100_UNICHART_ERROR_FIRST_PACKED_CHECKPOINT_V1"


def _group_payload_bytes(count: int, bits: int) -> int:
    return 4 + math.ceil(count * bits / 8)


def _bitmap(total: int, selected: set[int]) -> bytes:
    out = bytearray((total + 7) // 8)
    for idx in selected:
        if idx < 0 or idx >= total:
            raise PackerError("PRECISION_BITMAP_INDEX_OUT_OF_RANGE")
        out[idx // 8] |= 1 << (idx % 8)
    return bytes(out)


def _bitmap_get(blob: bytes, idx: int) -> bool:
    return bool(blob[idx // 8] & (1 << (idx % 8)))


def _sse_rows(x: np.ndarray, bits: int) -> np.ndarray:
    if x.ndim != 2 or x.shape[1] < 1 or x.shape[1] > GROUP_SIZE:
        raise PackerError("SSE_MATRIX_SHAPE_INVALID")
    if not np.isfinite(x).all():
        raise PackerError("NONFINITE_SOURCE_WEIGHT")
    qmax = (1 << bits) - 1
    lo = x.min(axis=1).astype(np.float32)
    hi = x.max(axis=1).astype(np.float32)
    scale = (hi - lo) / np.float32(qmax)
    q = np.zeros(x.shape, dtype=np.uint8)
    mask = scale != 0
    if mask.any():
        raw = np.rint(
            (x[mask] - lo[mask, None]) / scale[mask, None]
        )
        q[mask] = np.clip(raw, 0, qmax).astype(np.uint8)
    with np.errstate(over="ignore", invalid="ignore"):
        scale16 = scale.astype(np.float16).astype(np.float32)
        offset16 = lo.astype(np.float16).astype(np.float32)
    if not np.isfinite(scale16).all() or not np.isfinite(offset16).all():
        raise PackerError("FP16_METADATA_OVERFLOW")
    recon = offset16[:, None] + scale16[:, None] * q.astype(np.float32)
    err = x.astype(np.float64) - recon.astype(np.float64)
    return np.sum(err * err, axis=1)


def score_source_groups(
    source: Path,
    parsed: dict[str, Any],
    *,
    chunk_groups: int = 4096,
) -> tuple[list[tuple[float, str, int, int]], float, float, int]:
    scores: list[tuple[float, str, int, int]] = []
    total_sse3 = 0.0
    total_sse4 = 0.0
    global_idx = 0
    with zipfile.ZipFile(source, "r") as z:
        for storage in parsed["storages"]:
            if storage["dtype"] != "F32":
                continue
            tie_name = storage["aliases"][0]
            local_idx = 0
            remaining = int(storage["numel"])
            with z.open(storage["entry"], "r") as src:
                while remaining:
                    groups = min(chunk_groups, math.ceil(remaining / GROUP_SIZE))
                    want_values = min(remaining, groups * GROUP_SIZE)
                    raw = src.read(want_values * 4)
                    if len(raw) != want_values * 4:
                        raise PackerError("KNAPSACK_SOURCE_TRUNCATED")
                    vals = np.frombuffer(raw, dtype="<f4")
                    full, rem = divmod(want_values, GROUP_SIZE)
                    pos = 0
                    if full:
                        mat = vals[: full * GROUP_SIZE].reshape(full, GROUP_SIZE)
                        s3 = _sse_rows(mat, 3)
                        s4 = _sse_rows(mat, 4)
                        for j in range(full):
                            b = float(s3[j] - s4[j])
                            scores.append((b, tie_name, local_idx, global_idx))
                            total_sse3 += float(s3[j])
                            total_sse4 += float(s4[j])
                            local_idx += 1
                            global_idx += 1
                        pos = full * GROUP_SIZE
                    if rem:
                        mat = vals[pos:].reshape(1, rem)
                        s3 = _sse_rows(mat, 3)
                        s4 = _sse_rows(mat, 4)
                        b = float(s3[0] - s4[0])
                        scores.append((b, tie_name, local_idx, global_idx))
                        total_sse3 += float(s3[0])
                        total_sse4 += float(s4[0])
                        local_idx += 1
                        global_idx += 1
                    remaining -= want_values
                if src.read(1):
                    raise PackerError("KNAPSACK_SOURCE_TRAILING_BYTES")
    scores.sort(key=lambda row: (-row[0], row[1], row[2]))
    return scores, total_sse3, total_sse4, global_idx


def _layout(
    parsed: dict[str, Any],
    selected: set[int],
    *,
    source_sha256: str,
    total_f32_groups: int,
) -> tuple[dict[str, Any], int]:
    precision = _bitmap(total_f32_groups, selected)
    cursor = len(MAGIC) + 8
    global_idx = 0
    storages: list[dict[str, Any]] = []
    for storage in parsed["storages"]:
        start = cursor
        group_start = global_idx
        groups = 0
        if storage["dtype"] == "I64":
            cursor += int(storage["bytes"])
        else:
            remaining = int(storage["numel"])
            while remaining:
                n = min(GROUP_SIZE, remaining)
                bits = 4 if global_idx in selected else 3
                cursor += _group_payload_bytes(n, bits)
                global_idx += 1
                groups += 1
                remaining -= n
        storages.append(
            {
                "key": storage["key"],
                "dtype": storage["dtype"],
                "numel": storage["numel"],
                "aliases": storage["aliases"],
                "groups": groups,
                "group_start": group_start if storage["dtype"] == "F32" else None,
                "data_start": start,
                "data_end": cursor,
            }
        )
    if global_idx != total_f32_groups:
        raise PackerError(
            f"F32_GROUP_COUNT_MISMATCH:{global_idx}!={total_f32_groups}"
        )
    manifest = {
        "schema": PACKED_SCHEMA,
        "source_sha256": source_sha256,
        "group_size": GROUP_SIZE,
        "base_precision": 3,
        "upgrade_precision": 4,
        "selection_policy": "SOURCE_ONLY_DESC_SSE3_MINUS_SSE4_THEN_TENSOR_NAME_GROUP_INDEX",
        "group_metadata": "FP16_SCALE_PLUS_FP16_OFFSET",
        "bit_order": "LSB_FIRST",
        "i64_policy": "LOSSLESS_LITTLE_ENDIAN_BYTES",
        "total_f32_groups": total_f32_groups,
        "selected_w4_groups": len(selected),
        "precision_bitmap_b64": base64.b64encode(precision).decode("ascii"),
        "tensor_count": parsed["tensor_count"],
        "storage_count": parsed["storage_count"],
        "tensor_aliases": [
            {
                "name": row["name"],
                "storage_key": row["storage_key"],
                "shape": row["shape"],
                "stride": row["stride"],
                "dtype": row["storage_dtype"],
            }
            for row in parsed["tensor_rows"]
        ],
        "storages": storages,
    }
    manifest_bytes = json.dumps(
        manifest, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return manifest, cursor + len(manifest_bytes)


def choose_prefix(
    parsed: dict[str, Any],
    ranked_scores: list[tuple[float, str, int, int]],
    *,
    source_sha256: str,
    ancillary_bytes: int,
) -> tuple[set[int], dict[str, Any], int]:
    total_groups = len(ranked_scores)
    ordered_ids = [row[3] for row in ranked_scores]

    def size_for(k: int):
        selected = set(ordered_ids[:k])
        manifest, packed_size = _layout(
            parsed,
            selected,
            source_sha256=source_sha256,
            total_f32_groups=total_groups,
        )
        return packed_size + ancillary_bytes, selected, manifest, packed_size

    lo, hi = 0, total_groups
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        complete, selected, manifest, packed = size_for(mid)
        if complete <= H100_BUDGET_BYTES:
            best = (selected, manifest, packed, complete)
            lo = mid + 1
        else:
            hi = mid - 1
    if best is None:
        raise PackerError("ALL_W3_COMPLETE_BUNDLE_EXCEEDS_H100")
    selected, manifest, packed, complete = best
    return selected, manifest, complete


def _pack_group(values: np.ndarray, bits: int) -> bytes:
    meta, codes = quantize_group(values.astype(np.float32).tolist(), bits)
    return meta + codes


def build_knapsack_checkpoint(
    source: Path,
    output: Path,
    *,
    expected_source_sha256: str,
    ancillary_bytes: int,
) -> dict[str, Any]:
    source = Path(source)
    output = Path(output)
    source_sha = _sha256(source)
    if source_sha != expected_source_sha256:
        raise PackerError(
            f"SOURCE_SHA256_MISMATCH:{source_sha}!={expected_source_sha256}"
        )
    parsed = parse_checkpoint_metadata(source)
    ranked, total_sse3, total_sse4, total_groups = score_source_groups(
        source, parsed
    )
    selected, manifest, projected_complete = choose_prefix(
        parsed,
        ranked,
        source_sha256=source_sha,
        ancillary_bytes=ancillary_bytes,
    )
    precision = base64.b64decode(manifest["precision_bitmap_b64"])
    selected_benefit = sum(row[0] for row in ranked if row[3] in selected)

    manifest_storages = {s["key"]: s for s in manifest["storages"]}
    with zipfile.ZipFile(source, "r") as z, output.open("wb+") as out:
        out.write(MAGIC)
        out.write(struct.pack("<Q", 0))
        global_idx = 0
        for storage in parsed["storages"]:
            expected = manifest_storages[storage["key"]]
            if out.tell() != expected["data_start"]:
                raise PackerError("KNAPSACK_LAYOUT_START_MISMATCH")
            with z.open(storage["entry"], "r") as src:
                if storage["dtype"] == "I64":
                    remaining = int(storage["bytes"])
                    while remaining:
                        chunk = src.read(min(1 << 20, remaining))
                        if not chunk:
                            raise PackerError("KNAPSACK_I64_TRUNCATED")
                        out.write(chunk)
                        remaining -= len(chunk)
                    if src.read(1):
                        raise PackerError("KNAPSACK_I64_TRAILING_BYTES")
                else:
                    remaining = int(storage["numel"])
                    while remaining:
                        n = min(GROUP_SIZE, remaining)
                        raw = src.read(n * 4)
                        if len(raw) != n * 4:
                            raise PackerError("KNAPSACK_F32_TRUNCATED")
                        vals = np.frombuffer(raw, dtype="<f4")
                        bits = 4 if _bitmap_get(precision, global_idx) else 3
                        out.write(_pack_group(vals, bits))
                        global_idx += 1
                        remaining -= n
                    if src.read(1):
                        raise PackerError("KNAPSACK_F32_TRAILING_BYTES")
            if out.tell() != expected["data_end"]:
                raise PackerError("KNAPSACK_LAYOUT_END_MISMATCH")

        manifest_bytes = json.dumps(
            manifest, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        manifest_offset = out.tell()
        out.write(manifest_bytes)
        final_size = out.tell()
        out.seek(len(MAGIC))
        out.write(struct.pack("<Q", len(manifest_bytes)))
        out.flush()

    complete = final_size + ancillary_bytes
    if complete > H100_BUDGET_BYTES:
        output.unlink(missing_ok=True)
        raise PackerError(
            f"COMPLETE_BUNDLE_EXCEEDS_H100:{complete}>{H100_BUDGET_BYTES}"
        )
    if complete != projected_complete:
        raise PackerError(
            f"PROJECTED_ACTUAL_SIZE_MISMATCH:{projected_complete}!={complete}"
        )

    return {
        "schema": SCHEMA,
        "status": "SOURCE_ONLY_KNAPSACK_PACKED__CAPABILITY_UNPROVED__ACTIVATION_CONDITIONAL",
        "source_sha256": source_sha,
        "output_sha256": _sha256(output),
        "output_bytes": final_size,
        "ancillary_bytes": ancillary_bytes,
        "complete_bundle_bytes": complete,
        "margin_bytes": H100_BUDGET_BYTES - complete,
        "h100_budget_bytes": H100_BUDGET_BYTES,
        "tensor_count": parsed["tensor_count"],
        "storage_count": parsed["storage_count"],
        "total_f32_groups": total_groups,
        "selected_w4_groups": len(selected),
        "selected_w3_groups": total_groups - len(selected),
        "precision_bitmap_sha256": hashlib.sha256(precision).hexdigest(),
        "manifest_bytes": final_size - manifest_offset,
        "aggregate_source_sse_all_w3": total_sse3,
        "aggregate_source_sse_all_w4": total_sse4,
        "aggregate_selected_sse_reduction_vs_all_w3": selected_benefit,
        "hard_nonclaims": [
            "PRECOMPUTED_SOURCE_ONLY_CANDIDATE_DOES_NOT_ACTIVATE_UNLESS_FROZEN_COARSE_GATE_FAILS",
            "LOWER_WEIGHT_RECONSTRUCTION_SSE_DOES_NOT_PROVE_CAPABILITY_PRESERVATION",
            "NO_CHARTOGRAPHY_THRESHOLD_CREDIT",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "h100_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--expected-source-sha256", required=True)
    ap.add_argument("--ancillary-bytes", type=int, required=True)
    ap.add_argument("--result-json")
    args = ap.parse_args()
    result = build_knapsack_checkpoint(
        Path(args.source),
        Path(args.output),
        expected_source_sha256=args.expected_source_sha256,
        ancillary_bytes=args.ancillary_bytes,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.result_json:
        Path(args.result_json).write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
