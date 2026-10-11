"""Deterministic donor-free DNA storage codec capability.

General-purpose bytes <-> DNA oligo coding with:
- homopolymer-free rotating ternary encoding,
- deterministic whitening / GC balancing,
- per-packet CRC32 integrity,
- systematic Reed-Solomon-style erasure coding over GF(256),
- reverse-complement orientation recovery,
- multi-block reconstruction and whole-payload digest verification.

No network, model, package, or benchmark-specific dependency is required.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
import pathlib
import struct
import zlib
from typing import Any, Iterable, Sequence

SCHEMA = "PROJECT_BRAIN_DNA_STORAGE_CODEC_V1"
MODEL_DEPENDENCY_COUNT = 0
NETWORK_DEPENDENCY_COUNT = 0

_BASES = "ACGT"
_MAGIC = b"DB"
_VERSION = 1
_HEADER = struct.Struct(">2sBBBBBBBIH8s")
_CRC = struct.Struct(">I")
_DEFAULT_SHARD_SIZE = 16
_DEFAULT_MAX_DATA_SHARDS = 24
_DEFAULT_PARITY_SHARDS = 4
_MIN_GC = 0.40
_MAX_GC = 0.60


class DNAStorageCodecError(RuntimeError):
    pass


def reverse_complement(seq: str) -> str:
    table = str.maketrans("ACGTacgt", "TGCAtgca")
    return str(seq).translate(table)[::-1].upper()


def gc_fraction(seq: str) -> float:
    seq = str(seq).upper()
    if not seq:
        return 0.0
    return sum(ch in "GC" for ch in seq) / len(seq)


def max_homopolymer(seq: str) -> int:
    seq = str(seq).upper()
    if not seq:
        return 0
    best = run = 1
    for a, b in zip(seq, seq[1:]):
        if a == b:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _byte_to_trits(value: int) -> list[int]:
    if not 0 <= value <= 255:
        raise ValueError(value)
    out = [0] * 6
    x = value
    for i in range(5, -1, -1):
        out[i] = x % 3
        x //= 3
    return out


def _trits_to_byte(trits: Sequence[int]) -> int:
    if len(trits) != 6:
        raise DNAStorageCodecError("TRIT_GROUP_LENGTH_INVALID")
    value = 0
    for digit in trits:
        if digit not in (0, 1, 2):
            raise DNAStorageCodecError("TRIT_INVALID")
        value = value * 3 + digit
    if value > 255:
        raise DNAStorageCodecError("TRIT_BYTE_OUT_OF_RANGE")
    return value


def _trits_to_dna(trits: Iterable[int], *, previous: str = "A") -> str:
    prev = previous
    out: list[str] = []
    for digit in trits:
        choices = tuple(base for base in _BASES if base != prev)
        if digit not in (0, 1, 2):
            raise DNAStorageCodecError("TRIT_INVALID")
        base = choices[digit]
        out.append(base)
        prev = base
    return "".join(out)


def _dna_to_trits(seq: str, *, previous: str = "A") -> list[int]:
    prev = previous
    out: list[int] = []
    for raw in str(seq).upper():
        if raw not in _BASES:
            raise DNAStorageCodecError("DNA_ALPHABET_INVALID")
        choices = tuple(base for base in _BASES if base != prev)
        if raw == prev:
            raise DNAStorageCodecError("DNA_HOMOPOLYMER_VIOLATION")
        try:
            digit = choices.index(raw)
        except ValueError as exc:
            raise DNAStorageCodecError("DNA_ROTATING_CODE_INVALID") from exc
        out.append(digit)
        prev = raw
    return out


def _whitening_stream(length: int, salt: int) -> bytes:
    if not 0 <= salt <= 255:
        raise ValueError(salt)
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(b"PB-DNA-V1" + bytes([salt]) + counter.to_bytes(4, "big")).digest())
        counter += 1
    return bytes(out[:length])


def _xor_bytes(raw: bytes, mask: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(raw, mask))


def _encode_packet_bytes(raw: bytes, salt: int) -> str:
    whitened = _xor_bytes(raw, _whitening_stream(len(raw), salt))
    trits = _byte_to_trits(salt)
    for b in whitened:
        trits.extend(_byte_to_trits(b))
    return _trits_to_dna(trits)


def _decode_packet_bytes(seq: str) -> bytes:
    trits = _dna_to_trits(seq)
    if len(trits) < 6 or len(trits) % 6:
        raise DNAStorageCodecError("DNA_LENGTH_NOT_BYTE_ALIGNED")
    salt = _trits_to_byte(trits[:6])
    data = bytes(_trits_to_byte(trits[i:i+6]) for i in range(6, len(trits), 6))
    return _xor_bytes(data, _whitening_stream(len(data), salt))


def _balanced_packet_dna(raw: bytes) -> str:
    best: tuple[float, int, str] | None = None
    for salt in range(256):
        seq = _encode_packet_bytes(raw, salt)
        gc = gc_fraction(seq)
        penalty = abs(gc - 0.5)
        candidate = (penalty, salt, seq)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
        if _MIN_GC <= gc <= _MAX_GC:
            return seq
    assert best is not None
    return best[2]


_GF_EXP = [0] * 512
_GF_LOG = [0] * 256
_x = 1
for _i in range(255):
    _GF_EXP[_i] = _x
    _GF_LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _GF_EXP[_i] = _GF_EXP[_i - 255]


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _gf_inv(a: int) -> int:
    if a == 0:
        raise DNAStorageCodecError("GF_ZERO_NOT_INVERTIBLE")
    return _GF_EXP[255 - _GF_LOG[a]]


def _gf_pow(a: int, n: int) -> int:
    if n == 0:
        return 1
    if a == 0:
        return 0
    return _GF_EXP[(_GF_LOG[a] * n) % 255]


def _matrix_identity(n: int) -> list[list[int]]:
    return [[1 if r == c else 0 for c in range(n)] for r in range(n)]


def _matrix_multiply(a: Sequence[Sequence[int]], b: Sequence[Sequence[int]]) -> list[list[int]]:
    if not a or not b or len(a[0]) != len(b):
        raise DNAStorageCodecError("GF_MATRIX_SHAPE_INVALID")
    rows, inner, cols = len(a), len(b), len(b[0])
    out = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for k in range(inner):
            av = a[r][k]
            if av == 0:
                continue
            for c in range(cols):
                bv = b[k][c]
                if bv:
                    out[r][c] ^= _gf_mul(av, bv)
    return out


def _matrix_invert(matrix: Sequence[Sequence[int]]) -> list[list[int]]:
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise DNAStorageCodecError("GF_MATRIX_NOT_SQUARE")
    left = [list(map(int, row)) for row in matrix]
    right = _matrix_identity(n)
    for col in range(n):
        pivot = next((r for r in range(col, n) if left[r][col] != 0), None)
        if pivot is None:
            raise DNAStorageCodecError("GF_MATRIX_SINGULAR")
        if pivot != col:
            left[col], left[pivot] = left[pivot], left[col]
            right[col], right[pivot] = right[pivot], right[col]
        inv = _gf_inv(left[col][col])
        if inv != 1:
            left[col] = [_gf_mul(x, inv) for x in left[col]]
            right[col] = [_gf_mul(x, inv) for x in right[col]]
        for r in range(n):
            if r == col:
                continue
            factor = left[r][col]
            if factor == 0:
                continue
            left[r] = [x ^ _gf_mul(factor, y) for x, y in zip(left[r], left[col])]
            right[r] = [x ^ _gf_mul(factor, y) for x, y in zip(right[r], right[col])]
    return right


def _generator_matrix(k: int, m: int) -> list[list[int]]:
    n = k + m
    if not 1 <= k <= 255 or not 0 <= m or n > 255:
        raise DNAStorageCodecError("SHARD_COUNT_OUT_OF_RANGE")
    vandermonde = [[_gf_pow(r + 1, c) for c in range(k)] for r in range(n)]
    top_inv = _matrix_invert(vandermonde[:k])
    return _matrix_multiply(vandermonde, top_inv)


def _linear_combine(coeffs: Sequence[int], shards: Sequence[bytes], size: int) -> bytes:
    out = bytearray(size)
    for coefficient, shard in zip(coeffs, shards):
        if coefficient == 0:
            continue
        for i, value in enumerate(shard):
            if value:
                out[i] ^= _gf_mul(coefficient, value)
    return bytes(out)


def _digest8(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()[:8]


def _build_packet(*, block_index: int, block_count: int, k: int, m: int,
                  shard_index: int, shard_size: int, original_length: int,
                  block_length: int, digest8: bytes, shard: bytes) -> bytes:
    if len(shard) != shard_size:
        raise DNAStorageCodecError("SHARD_SIZE_MISMATCH")
    header = _HEADER.pack(
        _MAGIC, _VERSION, block_index, block_count, k, m, shard_index,
        shard_size, original_length, block_length, digest8,
    )
    body = header + shard
    return body + _CRC.pack(zlib.crc32(body) & 0xFFFFFFFF)


def _parse_packet_bytes(packet: bytes) -> dict[str, Any]:
    if len(packet) < _HEADER.size + _CRC.size:
        raise DNAStorageCodecError("PACKET_TOO_SHORT")
    header = packet[:_HEADER.size]
    magic, version, block_index, block_count, k, m, shard_index, shard_size, original_length, block_length, digest = _HEADER.unpack(header)
    if magic != _MAGIC or version != _VERSION:
        raise DNAStorageCodecError("PACKET_MAGIC_OR_VERSION_INVALID")
    expected_len = _HEADER.size + shard_size + _CRC.size
    if len(packet) != expected_len:
        raise DNAStorageCodecError("PACKET_LENGTH_INVALID")
    body = packet[:-_CRC.size]
    expected_crc = _CRC.unpack(packet[-_CRC.size:])[0]
    if (zlib.crc32(body) & 0xFFFFFFFF) != expected_crc:
        raise DNAStorageCodecError("PACKET_CRC_MISMATCH")
    if block_count < 1 or block_index >= block_count:
        raise DNAStorageCodecError("BLOCK_INDEX_INVALID")
    if k < 1 or m < 0 or k + m > 255 or shard_index >= k + m:
        raise DNAStorageCodecError("SHARD_METADATA_INVALID")
    if shard_size < 1 or block_length > k * shard_size:
        raise DNAStorageCodecError("SHARD_GEOMETRY_INVALID")
    return {
        "block_index": block_index,
        "block_count": block_count,
        "data_shards": k,
        "parity_shards": m,
        "shard_index": shard_index,
        "shard_size": shard_size,
        "original_length": original_length,
        "block_length": block_length,
        "digest8": digest,
        "shard": packet[_HEADER.size:-_CRC.size],
    }


def decode_oligo_packet(seq: str) -> dict[str, Any]:
    errors: list[str] = []
    candidates = [str(seq).strip().upper()]
    rc = reverse_complement(candidates[0])
    if rc != candidates[0]:
        candidates.append(rc)
    for orientation, candidate in enumerate(candidates):
        try:
            packet = _decode_packet_bytes(candidate)
            parsed = _parse_packet_bytes(packet)
            parsed["orientation"] = "forward" if orientation == 0 else "reverse_complement"
            return parsed
        except Exception as exc:
            errors.append(type(exc).__name__ + ":" + str(exc))
    raise DNAStorageCodecError("OLIGO_PACKET_INVALID:" + "|".join(errors[:2]))


def encode_bytes(data: bytes, *, shard_size: int = _DEFAULT_SHARD_SIZE,
                 parity_shards: int = _DEFAULT_PARITY_SHARDS,
                 max_data_shards: int = _DEFAULT_MAX_DATA_SHARDS) -> list[str]:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise DNAStorageCodecError("DATA_BYTES_REQUIRED")
    data = bytes(data)
    if not 1 <= shard_size <= 255:
        raise DNAStorageCodecError("SHARD_SIZE_INVALID")
    if not 0 <= parity_shards <= 64:
        raise DNAStorageCodecError("PARITY_SHARDS_INVALID")
    if not 1 <= max_data_shards <= 255 - parity_shards:
        raise DNAStorageCodecError("MAX_DATA_SHARDS_INVALID")
    block_capacity = shard_size * max_data_shards
    block_count = max(1, math.ceil(len(data) / block_capacity))
    if block_count > 255:
        raise DNAStorageCodecError("PAYLOAD_TOO_LARGE_FOR_V1")
    digest = _digest8(data)
    oligos: list[str] = []
    for block_index in range(block_count):
        chunk = data[block_index * block_capacity:(block_index + 1) * block_capacity]
        block_length = len(chunk)
        k = max(1, math.ceil(block_length / shard_size))
        m = min(parity_shards, 255 - k)
        padded = chunk + b"\0" * (k * shard_size - block_length)
        data_shards = [padded[i * shard_size:(i + 1) * shard_size] for i in range(k)]
        generator = _generator_matrix(k, m)
        shards = list(data_shards)
        for row_index in range(k, k + m):
            shards.append(_linear_combine(generator[row_index], data_shards, shard_size))
        for shard_index, shard in enumerate(shards):
            packet = _build_packet(
                block_index=block_index, block_count=block_count, k=k, m=m,
                shard_index=shard_index, shard_size=shard_size,
                original_length=len(data), block_length=block_length,
                digest8=digest, shard=shard,
            )
            seq = _balanced_packet_dna(packet)
            if max_homopolymer(seq) != 1:
                raise AssertionError("rotating code invariant")
            oligos.append(seq)
    return oligos


def _consensus_by_index(packets: Sequence[dict[str, Any]]) -> dict[int, bytes]:
    grouped: dict[int, list[bytes]] = defaultdict(list)
    for row in packets:
        grouped[int(row["shard_index"])].append(bytes(row["shard"]))
    selected: dict[int, bytes] = {}
    for index, values in grouped.items():
        counts = Counter(values)
        ranked = counts.most_common()
        if not ranked:
            continue
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            continue
        selected[index] = ranked[0][0]
    return selected


def decode_oligos(oligos: Sequence[str]) -> bytes:
    if isinstance(oligos, (str, bytes)) or not isinstance(oligos, Sequence):
        raise DNAStorageCodecError("OLIGOS_SEQUENCE_REQUIRED")
    valid: list[dict[str, Any]] = []
    for seq in oligos:
        if not isinstance(seq, str) or not seq.strip():
            continue
        try:
            valid.append(decode_oligo_packet(seq))
        except DNAStorageCodecError:
            continue
    if not valid:
        raise DNAStorageCodecError("NO_VALID_PACKETS")
    signatures = Counter(
        (r["block_count"], r["original_length"], r["digest8"]) for r in valid
    )
    signature, count = signatures.most_common(1)[0]
    if len(signatures) > 1:
        top = signatures.most_common(2)
        if len(top) > 1 and top[0][1] == top[1][1]:
            raise DNAStorageCodecError("PAYLOAD_IDENTITY_AMBIGUOUS")
    block_count, original_length, digest = signature
    selected_payload_rows = [r for r in valid if (r["block_count"], r["original_length"], r["digest8"]) == signature]
    reconstructed_blocks: list[bytes] = []
    for block_index in range(block_count):
        rows = [r for r in selected_payload_rows if r["block_index"] == block_index]
        if not rows:
            raise DNAStorageCodecError("BLOCK_MISSING")
        geometry = Counter((r["data_shards"], r["parity_shards"], r["shard_size"], r["block_length"]) for r in rows)
        geom, _ = geometry.most_common(1)[0]
        k, m, shard_size, block_length = geom
        rows = [r for r in rows if (r["data_shards"], r["parity_shards"], r["shard_size"], r["block_length"]) == geom]
        by_index = _consensus_by_index(rows)
        available = sorted(by_index)
        if len(available) < k:
            raise DNAStorageCodecError("INSUFFICIENT_VALID_SHARDS")
        chosen = available[:k]
        generator = _generator_matrix(k, m)
        matrix = [generator[index] for index in chosen]
        inverse = _matrix_invert(matrix)
        chosen_shards = [by_index[index] for index in chosen]
        data_shards = [
            _linear_combine(inverse[row], chosen_shards, shard_size)
            for row in range(k)
        ]
        reconstructed_blocks.append(b"".join(data_shards)[:block_length])
    data = b"".join(reconstructed_blocks)[:original_length]
    if _digest8(data) != digest:
        raise DNAStorageCodecError("WHOLE_PAYLOAD_DIGEST_MISMATCH")
    return data


def encode_file(input_path: str | pathlib.Path, output_path: str | pathlib.Path, **kwargs: Any) -> dict[str, Any]:
    src = pathlib.Path(input_path)
    dst = pathlib.Path(output_path)
    data = src.read_bytes()
    oligos = encode_bytes(data, **kwargs)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(oligos) + "\n", encoding="ascii")
    return {
        "schema": SCHEMA,
        "status": "PASS__DNA_STORAGE_ENCODED",
        "input_bytes": len(data),
        "oligo_count": len(oligos),
        "output_path": str(dst),
        "output_sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
        "model_dependency_count": 0,
        "network_dependency_count": 0,
    }


def decode_file(input_path: str | pathlib.Path, output_path: str | pathlib.Path) -> dict[str, Any]:
    src = pathlib.Path(input_path)
    dst = pathlib.Path(output_path)
    oligos = [line.strip() for line in src.read_text(encoding="ascii", errors="ignore").splitlines() if line.strip()]
    data = decode_oligos(oligos)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return {
        "schema": SCHEMA,
        "status": "PASS__DNA_STORAGE_DECODED",
        "output_bytes": len(data),
        "output_path": str(dst),
        "output_sha256": hashlib.sha256(data).hexdigest(),
        "model_dependency_count": 0,
        "network_dependency_count": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    enc = sub.add_parser("encode")
    enc.add_argument("input")
    enc.add_argument("output")
    enc.add_argument("--shard-size", type=int, default=_DEFAULT_SHARD_SIZE)
    enc.add_argument("--parity-shards", type=int, default=_DEFAULT_PARITY_SHARDS)
    enc.add_argument("--max-data-shards", type=int, default=_DEFAULT_MAX_DATA_SHARDS)
    dec = sub.add_parser("decode")
    dec.add_argument("input")
    dec.add_argument("output")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.mode == "encode":
        result = encode_file(args.input, args.output, shard_size=args.shard_size,
                             parity_shards=args.parity_shards, max_data_shards=args.max_data_shards)
    else:
        result = decode_file(args.input, args.output)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
