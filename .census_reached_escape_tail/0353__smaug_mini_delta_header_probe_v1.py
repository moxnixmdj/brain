#!/usr/bin/env python3
"""Header-only storage geometry probe for Smaug-Mini vs Qwen3.8-27B.

No weight tensors are downloaded. Safetensors exposes tensor dtype, shape and byte
offsets in a JSON header at the beginning of each shard, so HTTP Range requests
are sufficient to build an exact tensor-byte manifest.

This tool does NOT claim that the published merged BF16 delta remains exactly
low-rank. It reports rank-dependent factor-storage bounds for 2-D candidate
matrices and keeps exact reconstruction as a separate verification requirement.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable

SCHEMA = "PROJECT_BRAIN_SMAUG_MINI_DELTA_HEADER_PROBE_V1"
BASE_REPO = "Qwen/Qwen3.8-27B"
BASE_REV = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
TUNED_REPO = "abacusai/Smaug-Mini"
TUNED_REV = "2750fd9f1e67e004111a53a6d9a39c15fbbd33ef"
INDEX_NAME = "model.safetensors.index.json"

_DTYPE_BYTES = {
    "BOOL": 1,
    "U8": 1, "I8": 1,
    "U16": 2, "I16": 2, "F16": 2, "BF16": 2,
    "U32": 4, "I32": 4, "F32": 4,
    "U64": 8, "I64": 8, "F64": 8,
}


def hf_resolve(repo: str, rev: str, path: str) -> str:
    return f"https://huggingface.co/{repo}/resolve/{rev}/{path}"


def _url_bytes(url: str, range_header: str | None = None) -> bytes:
    req = urllib.request.Request(url)
    if range_header:
        req.add_header("Range", range_header)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_json(url: str, get_bytes: Callable[[str, str | None], bytes] = _url_bytes) -> dict[str, Any]:
    return json.loads(get_bytes(url, None).decode("utf-8"))


def fetch_safetensors_header(
    url: str,
    get_bytes: Callable[[str, str | None], bytes] = _url_bytes,
) -> dict[str, Any]:
    first = get_bytes(url, "bytes=0-7")
    if len(first) != 8:
        raise ValueError(f"HEADER_LENGTH_PREFIX_INVALID:{url}:{len(first)}")
    header_len = struct.unpack("<Q", first)[0]
    if header_len <= 2 or header_len > 128 * 1024 * 1024:
        raise ValueError(f"HEADER_LENGTH_OUT_OF_RANGE:{url}:{header_len}")
    raw = get_bytes(url, f"bytes=8-{7 + header_len}")
    if len(raw) != header_len:
        raise ValueError(f"HEADER_RANGE_LENGTH_MISMATCH:{url}:{len(raw)}:{header_len}")
    return json.loads(raw.decode("utf-8"))


def tensor_nbytes(meta: dict[str, Any]) -> int:
    offsets = meta.get("data_offsets")
    if isinstance(offsets, list) and len(offsets) == 2:
        return int(offsets[1]) - int(offsets[0])
    dtype = str(meta["dtype"])
    shape = [int(x) for x in meta["shape"]]
    b = _DTYPE_BYTES[dtype]
    return math.prod(shape) * b


def declared_unchanged_surface(name: str) -> str | None:
    # Smaug-Mini model card: vision tower + multimodal projection are bitwise
    # identical to base; MTP head was inherited and not retrained.
    if name.startswith("model.visual."):
        return "VISION_AND_MULTIMODAL_PUBLICLY_DECLARED_BITWISE_IDENTICAL"
    if name.startswith("mtp."):
        return "MTP_PUBLICLY_DECLARED_INHERITED_NOT_RETRAINED"
    return None


def candidate_lora_factor_bytes(shape: list[int], rank: int, bytes_per_factor: int = 2) -> int | None:
    if len(shape) != 2:
        return None
    m, n = int(shape[0]), int(shape[1])
    return int(rank) * (m + n) * int(bytes_per_factor)


@dataclass(frozen=True)
class TensorMeta:
    name: str
    shard: str
    dtype: str
    shape: tuple[int, ...]
    nbytes: int

    @classmethod
    def from_header(cls, name: str, shard: str, meta: dict[str, Any]) -> "TensorMeta":
        return cls(
            name=name,
            shard=shard,
            dtype=str(meta["dtype"]),
            shape=tuple(int(x) for x in meta["shape"]),
            nbytes=tensor_nbytes(meta),
        )


def load_repo_headers(
    repo: str,
    rev: str,
    fetch_json_fn: Callable[[str], dict[str, Any]],
    fetch_header_fn: Callable[[str], dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, TensorMeta]]:
    index = fetch_json_fn(hf_resolve(repo, rev, INDEX_NAME))
    weight_map = dict(index["weight_map"])
    by_shard: dict[str, list[str]] = defaultdict(list)
    for name, shard in weight_map.items():
        by_shard[str(shard)].append(str(name))

    tensors: dict[str, TensorMeta] = {}
    for shard in sorted(by_shard):
        header = fetch_header_fn(hf_resolve(repo, rev, shard))
        for name in by_shard[shard]:
            if name not in header:
                raise ValueError(f"INDEX_HEADER_DISAGREEMENT:{repo}:{shard}:{name}")
            tensors[name] = TensorMeta.from_header(name, shard, header[name])
    return index, tensors


def compare_geometry(
    base: dict[str, TensorMeta],
    tuned: dict[str, TensorMeta],
    ranks: tuple[int, ...] = (8, 16, 32, 64, 128, 256),
) -> dict[str, Any]:
    base_names, tuned_names = set(base), set(tuned)
    if base_names != tuned_names:
        return {
            "status": "FAIL_CLOSED",
            "missing_from_tuned": sorted(base_names - tuned_names),
            "missing_from_base": sorted(tuned_names - base_names),
        }

    mismatches = []
    class_bytes: dict[str, int] = defaultdict(int)
    candidate_2d = []
    total_bytes = 0
    for name in sorted(base):
        b, t = base[name], tuned[name]
        if b.dtype != t.dtype or b.shape != t.shape or b.nbytes != t.nbytes:
            mismatches.append({
                "name": name,
                "base": {"dtype": b.dtype, "shape": list(b.shape), "nbytes": b.nbytes},
                "tuned": {"dtype": t.dtype, "shape": list(t.shape), "nbytes": t.nbytes},
            })
            continue
        total_bytes += t.nbytes
        unchanged = declared_unchanged_surface(name)
        cls = "DECLARED_UNCHANGED" if unchanged else "DELTA_CANDIDATE"
        class_bytes[cls] += t.nbytes
        if not unchanged and len(t.shape) == 2:
            candidate_2d.append(t)

    if mismatches:
        return {"status": "FAIL_CLOSED", "geometry_mismatches": mismatches}

    bounds = {}
    for rank in ranks:
        factor_bytes = sum(
            candidate_lora_factor_bytes(list(t.shape), rank) or 0
            for t in candidate_2d
        )
        bounds[str(rank)] = {
            "bf16_factor_bytes_if_every_2d_delta_candidate_rank_le_r": factor_bytes,
            "fraction_of_full_model": factor_bytes / total_bytes if total_bytes else None,
            "hard_nonclaim": "NOT_EXACT_PUBLISHED_DELTA_SIZE_AND_NOT_A_PROVEN_TRAINING_RANK",
        }

    return {
        "status": "PASS_GEOMETRY_ONLY",
        "tensor_count": len(base),
        "full_tensor_bytes_from_headers": total_bytes,
        "declared_unchanged_bytes": class_bytes["DECLARED_UNCHANGED"],
        "delta_candidate_bytes": class_bytes["DELTA_CANDIDATE"],
        "declared_unchanged_fraction": class_bytes["DECLARED_UNCHANGED"] / total_bytes if total_bytes else None,
        "candidate_2d_matrix_count": len(candidate_2d),
        "rank_storage_bounds": bounds,
        "hard_nonclaims": [
            "HEADERS_DO_NOT_PROVE_TENSOR_VALUE_EQUALITY",
            "PUBLIC_MODEL_CARD_CLAIM_IS_THE_ONLY_BASIS_FOR_DECLARED_UNCHANGED_CLASS",
            "BF16_MERGE_ROUNDING_CAN_RAISE_NUMERICAL_RANK",
            "LOW_RANK_FACTORS_REQUIRE_RECONSTRUCTION_OR_BEHAVIORAL_QUALIFICATION",
        ],
    }


def run_live() -> dict[str, Any]:
    def fj(url: str) -> dict[str, Any]:
        return fetch_json(url)

    def fh(url: str) -> dict[str, Any]:
        return fetch_safetensors_header(url)

    base_index, base = load_repo_headers(BASE_REPO, BASE_REV, fj, fh)
    tuned_index, tuned = load_repo_headers(TUNED_REPO, TUNED_REV, fj, fh)
    result = compare_geometry(base, tuned)
    return {
        "schema": SCHEMA,
        "base": {"repo": BASE_REPO, "revision": BASE_REV, "index_total_size": base_index.get("metadata", {}).get("total_size")},
        "tuned": {"repo": TUNED_REPO, "revision": TUNED_REV, "index_total_size": tuned_index.get("metadata", {}).get("total_size")},
        "result": result,
        "network_payload_rule": "ONLY_INDEX_JSON_PLUS_SAFETENSORS_HEADER_RANGES__NO_WEIGHT_DATA",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compact", action="store_true")
    ns = ap.parse_args()
    out = run_live()
    print(json.dumps(out, indent=None if ns.compact else 2, sort_keys=True))


if __name__ == "__main__":
    main()
