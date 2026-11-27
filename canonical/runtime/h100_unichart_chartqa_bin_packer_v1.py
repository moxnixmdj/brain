"""Direct deterministic low-bit packer for the exact UniChart ChartQA PyTorch ZIP checkpoint.

This parser does NOT import torch and does NOT execute arbitrary pickle globals.
It accepts only the four globals observed in the pinned donor:
- torch._utils._rebuild_tensor_v2
- torch.FloatStorage
- torch.LongStorage
- collections.OrderedDict

It reconstructs tensor metadata into inert descriptors, validates that every tensor
is a full contiguous view of its backing storage, permits exact aliases only, and
packs every physical storage once:
- encoder F32 storages -> W4 affine group-256
- decoder/other F32 storages -> W3 affine group-256
- I64 storages -> lossless raw bytes

The transformation is benchmark-blind and zero-credit.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import math
import pickle
import struct
import zipfile
from pathlib import Path
from typing import Any

from canonical.runtime.h100_unichart_lowbit_packer_v1 import (
    GROUP_SIZE,
    H100_BUDGET_BYTES,
    MAGIC,
    PackerError,
    _sha256,
    bits_for_tensor,
    quantize_group,
)

SCHEMA = "PROJECT_BRAIN_H100_UNICHART_CHARTQA_BIN_PACKER_RESULT_V1"


class StorageType:
    __slots__ = ("name", "itemsize", "dtype")
    def __init__(self, name: str, itemsize: int, dtype: str):
        self.name = name
        self.itemsize = itemsize
        self.dtype = dtype
    def __repr__(self) -> str:
        return self.name


FLOAT_STORAGE = StorageType("FloatStorage", 4, "F32")
LONG_STORAGE = StorageType("LongStorage", 8, "I64")


class StorageRef:
    __slots__ = ("stype", "key", "location", "size")
    def __init__(self, stype: StorageType, key: Any, location: Any, size: Any):
        self.stype = stype
        self.key = str(key)
        self.location = str(location)
        self.size = int(size)


def _rebuild_tensor_v2(
    storage: StorageRef,
    storage_offset: int,
    size: Any,
    stride: Any,
    requires_grad: Any,
    backward_hooks: Any,
    *rest: Any,
) -> dict[str, Any]:
    return {
        "__tensor__": True,
        "storage_key": storage.key,
        "storage_dtype": storage.stype.dtype,
        "storage_numel": storage.size,
        "storage_offset": int(storage_offset),
        "shape": [int(x) for x in size],
        "stride": [int(x) for x in stride],
        "requires_grad": bool(requires_grad),
    }


class RestrictedTorchUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        if module == "collections" and name == "OrderedDict":
            return collections.OrderedDict
        if module == "torch._utils" and name == "_rebuild_tensor_v2":
            return _rebuild_tensor_v2
        if module == "torch" and name == "FloatStorage":
            return FLOAT_STORAGE
        if module == "torch" and name == "LongStorage":
            return LONG_STORAGE
        raise PackerError(f"PICKLE_GLOBAL_FORBIDDEN:{module}.{name}")

    def persistent_load(self, pid: Any):
        if (
            not isinstance(pid, tuple)
            or len(pid) < 5
            or pid[0] != "storage"
        ):
            raise PackerError("PERSISTENT_ID_INVALID")
        _, stype, key, location, size, *rest = pid
        if stype not in (FLOAT_STORAGE, LONG_STORAGE):
            raise PackerError("STORAGE_TYPE_INVALID")
        return StorageRef(stype, key, location, size)


def _numel(shape: list[int]) -> int:
    out = 1
    for d in shape:
        if d < 0:
            raise PackerError("SHAPE_INVALID")
        out *= d
    return out


def _contiguous_stride(shape: list[int]) -> list[int]:
    acc = 1
    rev = []
    for d in reversed(shape):
        rev.append(acc)
        acc *= d
    return list(reversed(rev))


def parse_checkpoint_metadata(path: Path) -> dict[str, Any]:
    path = Path(path)
    with zipfile.ZipFile(path, "r") as z:
        names = z.namelist()
        pkls = [n for n in names if n.endswith("/data.pkl")]
        if len(pkls) != 1:
            raise PackerError(f"DATA_PKL_COUNT_INVALID:{len(pkls)}")
        root = RestrictedTorchUnpickler(io.BytesIO(z.read(pkls[0]))).load()
        if not isinstance(root, dict):
            raise PackerError("ROOT_STATE_DICT_NOT_MAPPING")

        tensor_rows: list[dict[str, Any]] = []
        storage_users: dict[str, list[str]] = collections.defaultdict(list)
        storage_meta: dict[str, dict[str, Any]] = {}

        for name, t in root.items():
            if not isinstance(name, str) or not name:
                raise PackerError("TENSOR_NAME_INVALID")
            if not isinstance(t, dict) or t.get("__tensor__") is not True:
                raise PackerError(f"NON_TENSOR_STATE_ENTRY:{name}")
            numel = _numel(t["shape"])
            if t["storage_offset"] != 0:
                raise PackerError(f"NONZERO_STORAGE_OFFSET_UNSUPPORTED:{name}")
            if numel != t["storage_numel"]:
                raise PackerError(f"PARTIAL_STORAGE_VIEW_UNSUPPORTED:{name}")
            if numel > 1 and t["stride"] != _contiguous_stride(t["shape"]):
                raise PackerError(f"NONCONTIGUOUS_TENSOR_UNSUPPORTED:{name}")

            key = t["storage_key"]
            storage_users[key].append(name)
            expected = {
                "dtype": t["storage_dtype"],
                "numel": t["storage_numel"],
            }
            if key in storage_meta and storage_meta[key] != expected:
                raise PackerError(f"STORAGE_ALIAS_METADATA_CONFLICT:{key}")
            storage_meta[key] = expected
            tensor_rows.append({"name": name, **t, "numel": numel})

        data_entries = {
            n.rsplit("/", 1)[-1]: n
            for n in names
            if "/data/" in n and not n.endswith("/")
        }
        if set(data_entries) != set(storage_meta):
            missing = sorted(set(storage_meta) - set(data_entries))
            extra = sorted(set(data_entries) - set(storage_meta))
            raise PackerError(
                "STORAGE_ENTRY_SET_MISMATCH:"
                f"missing={missing[:3]}:extra={extra[:3]}"
            )

        storages = []
        for key in sorted(storage_meta, key=lambda x: int(x) if x.isdigit() else x):
            meta = storage_meta[key]
            entry = data_entries[key]
            info = z.getinfo(entry)
            itemsize = 4 if meta["dtype"] == "F32" else 8
            expected_bytes = meta["numel"] * itemsize
            if info.file_size != expected_bytes:
                raise PackerError(
                    f"STORAGE_SIZE_MISMATCH:{key}:{info.file_size}!={expected_bytes}"
                )
            aliases = sorted(storage_users[key])
            bit_choices = {
                bits_for_tensor(alias, meta["dtype"])
                for alias in aliases
            }
            if len(bit_choices) != 1:
                raise PackerError(
                    f"ALIAS_PRECISION_CONFLICT:{key}:{aliases}"
                )
            bits = next(iter(bit_choices))
            storages.append(
                {
                    "key": key,
                    "entry": entry,
                    "dtype": meta["dtype"],
                    "numel": meta["numel"],
                    "bytes": info.file_size,
                    "aliases": aliases,
                    "bits": bits,
                }
            )

        return {
            "tensor_count": len(tensor_rows),
            "storage_count": len(storages),
            "alias_storage_count": sum(1 for s in storages if len(s["aliases"]) > 1),
            "tensor_rows": sorted(tensor_rows, key=lambda r: r["name"]),
            "storages": storages,
            "unique_f32_elements": sum(s["numel"] for s in storages if s["dtype"] == "F32"),
            "unique_i64_elements": sum(s["numel"] for s in storages if s["dtype"] == "I64"),
            "unique_storage_bytes": sum(s["bytes"] for s in storages),
        }


def _pack_storage_stream(src, out, *, numel: int, bits: int) -> int:
    remaining = numel
    groups = 0
    while remaining:
        n = min(GROUP_SIZE, remaining)
        raw = src.read(n * 4)
        if len(raw) != n * 4:
            raise PackerError("F32_STORAGE_TRUNCATED")
        values = struct.unpack("<" + "f" * n, raw)
        meta, packed = quantize_group(list(values), bits)
        out.write(meta)
        out.write(packed)
        remaining -= n
        groups += 1
    if src.read(1):
        raise PackerError("F32_STORAGE_TRAILING_BYTES")
    return groups


def build_packed_checkpoint(
    source: Path,
    output: Path,
    *,
    expected_source_sha256: str | None = None,
) -> dict[str, Any]:
    source = Path(source)
    output = Path(output)
    source_sha = _sha256(source)
    if expected_source_sha256 and source_sha != expected_source_sha256:
        raise PackerError(
            f"SOURCE_SHA256_MISMATCH:{source_sha}!={expected_source_sha256}"
        )

    parsed = parse_checkpoint_metadata(source)
    manifest_storages = []

    with zipfile.ZipFile(source, "r") as z, output.open("wb+") as out:
        out.write(MAGIC)
        out.write(struct.pack("<Q", 0))

        for storage in parsed["storages"]:
            start = out.tell()
            with z.open(storage["entry"], "r") as src:
                if storage["dtype"] == "I64":
                    remaining = storage["bytes"]
                    while remaining:
                        chunk = src.read(min(1 << 20, remaining))
                        if not chunk:
                            raise PackerError("I64_STORAGE_TRUNCATED")
                        out.write(chunk)
                        remaining -= len(chunk)
                    if src.read(1):
                        raise PackerError("I64_STORAGE_TRAILING_BYTES")
                    groups = 0
                else:
                    groups = _pack_storage_stream(
                        src,
                        out,
                        numel=storage["numel"],
                        bits=storage["bits"],
                    )
            end = out.tell()
            manifest_storages.append(
                {
                    "key": storage["key"],
                    "dtype": storage["dtype"],
                    "numel": storage["numel"],
                    "bits": storage["bits"],
                    "groups": groups,
                    "aliases": storage["aliases"],
                    "data_start": start,
                    "data_end": end,
                }
            )

        manifest_obj = {
            "schema": "PROJECT_BRAIN_H100_UNICHART_CHARTQA_PACKED_CHECKPOINT_V1",
            "source_sha256": source_sha,
            "group_size": GROUP_SIZE,
            "f32_policy": "ENCODER_W4_OTHER_W3",
            "group_metadata": "FP16_SCALE_PLUS_FP16_OFFSET",
            "bit_order": "LSB_FIRST",
            "i64_policy": "LOSSLESS_LITTLE_ENDIAN_BYTES",
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
            "storages": manifest_storages,
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
        "status": "PACKED_FINE_TUNED_CHARTQA_CHECKPOINT_CREATED__CAPABILITY_UNPROVED",
        "source_sha256": source_sha,
        "output_sha256": _sha256(output),
        "output_bytes": final_size,
        "margin_bytes": H100_BUDGET_BYTES - final_size,
        "h100_budget_bytes": H100_BUDGET_BYTES,
        "manifest_bytes": len(manifest_bytes),
        "manifest_offset": manifest_offset,
        "tensor_count": parsed["tensor_count"],
        "storage_count": parsed["storage_count"],
        "alias_storage_count": parsed["alias_storage_count"],
        "unique_f32_elements": parsed["unique_f32_elements"],
        "unique_i64_elements": parsed["unique_i64_elements"],
        "unique_storage_bytes": parsed["unique_storage_bytes"],
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--expected-source-sha256")
    ap.add_argument("--result-json")
    args = ap.parse_args()
    result = build_packed_checkpoint(
        Path(args.source),
        Path(args.output),
        expected_source_sha256=args.expected_source_sha256,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.result_json:
        Path(args.result_json).write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
