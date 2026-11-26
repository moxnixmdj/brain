#!/usr/bin/env python3
"""Zero-Copy `mmap` CSR Binary Slot & Postings Index (`K3 = 0`).

Eliminates warm/cold Python `dict`/`marshal` deserialization overhead across
large inverted-index sections (`source_index`, `combined_source_index`) by
compiling postings and document rows into a single content-addressed binary CSR
image mapped read-only via `mmap.mmap(..., access=mmap.ACCESS_READ)`:

  Header (36 bytes, little-endian `<8s7I`):
    - magic:           `b"BMCSR01\\x00"` (8 bytes)
    - version:         `1` (`uint32`)
    - num_docs:        `N` (`uint32`)
    - num_terms:       `V` (`uint32`)
    - paths_offset:    byte offset of newline-joined UTF-8 path directory
    - vocab_idx_off:   byte offset of `V` vocab descriptors `<IIII`
                       (`term_byte_off, term_byte_len, df, post_start, post_len` -> `<5I` = 20B)
    - postings_off:    byte offset of packed `<II` (`doc_id, tf`) CSR array
    - doc_idx_off:     byte offset of `N + 1` `<I` byte offsets into `docs_blob`

Query path (`search_bm25_like`):
  - Binary searches the sorted UTF-8 vocabulary directly inside the `mmap` buffer
    (`O(log V)` comparisons, zero vocabulary `dict` allocation).
  - Streams only the `<II` posting slices of the query's matched tokens in
    `sorted(wanted)` order so IEEE-754 floating-point summation is bit-for-bit
    identical regardless of `PYTHONHASHSEED`.
  - Materializes JSON row metadata ONLY for the `top_k` (`k=5`) winning hits.
  - Exposes `MmapDocTableProxy` and `MmapPostingsProxy` (`collections.abc.Mapping`)
    so callers inspecting `_source_index_cache` or `model.source_index[path]`
    get full dictionary semantics without eagerly unpacking all `N` rows.

Authority: NONE. Zero model calls (`K3 = 0`), `$0` spend, stdlib only.
"""
from __future__ import annotations

import hashlib
import heapq
import json
import math
import mmap
import os
import pathlib
import struct
from collections.abc import Iterator, Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_MMAP_CSR_SLOT_INDEX_V1"
MAGIC = b"BMCSR01\x00"
VERSION = 1
_HEADER_STRUCT = struct.Struct("<8s8I")  # magic, ver, n_docs, n_terms, paths_off, paths_len, vocab_off, post_off, doc_idx_off
_VOCAB_ENTRY_STRUCT = struct.Struct("<5I")  # term_off, term_len, df, post_start, post_len
_POSTING_STRUCT = struct.Struct("<II")  # doc_id, tf


def build_csr_bytes(
    rows_by_path: Mapping[str, Mapping[str, Any]],
    df_by_term: Mapping[str, int] | None = None,
) -> bytes:
    """ deterministically compile `path -> row` into a compact CSR binary image."""
    sorted_paths = sorted(str(p) for p in rows_by_path.keys())
    path_to_id = {p: idx for idx, p in enumerate(sorted_paths)}
    num_docs = len(sorted_paths)

    postings_map: dict[str, list[tuple[int, int]]] = {}
    computed_df: dict[str, int] = {}
    doc_blobs: list[bytes] = []

    for doc_id, path in enumerate(sorted_paths):
        row = rows_by_path[path]
        doc_blobs.append(
            json.dumps(dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        )
        terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
        for raw_term, raw_tf in terms.items():
            term = str(raw_term)
            tf = int(raw_tf or 0)
            computed_df[term] = computed_df.get(term, 0) + 1
            if tf > 0:
                postings_map.setdefault(term, []).append((doc_id, tf))

    effective_df = df_by_term if df_by_term is not None else computed_df
    all_terms_set = set(postings_map.keys()) | set(str(k) for k in effective_df.keys())
    # Sort terms by raw UTF-8 bytes so binary search over UTF-8 slices is exact.
    sorted_terms = sorted(all_terms_set, key=lambda s: s.encode("utf-8"))
    num_terms = len(sorted_terms)

    paths_blob = "\n".join(sorted_paths).encode("utf-8")

    term_string_buf = bytearray()
    vocab_entries = bytearray()
    postings_buf = bytearray()
    cur_post_idx = 0

    for term in sorted_terms:
        tb = term.encode("utf-8")
        t_off = len(term_string_buf)
        term_string_buf.extend(tb)
        plist = postings_map.get(term, ())
        df_val = max(1, int(effective_df.get(term, len(plist)) or 1))
        vocab_entries.extend(
            _VOCAB_ENTRY_STRUCT.pack(t_off, len(tb), df_val, cur_post_idx, len(plist))
        )
        for doc_id, tf in plist:
            postings_buf.extend(_POSTING_STRUCT.pack(doc_id, tf))
        cur_post_idx += len(plist)

    # Assemble layout with 4-byte alignment padding between sections
    def _pad4(buf: bytearray) -> None:
        rem = len(buf) % 4
        if rem:
            buf.extend(b"\x00" * (4 - rem))

    body = bytearray(_HEADER_STRUCT.size)
    paths_off = len(body)
    body.extend(paths_blob)
    _pad4(body)

    term_strings_off = len(body)
    body.extend(term_string_buf)
    _pad4(body)

    # Adjust term_off in vocab_entries to absolute file offsets for 1-hop slice compare
    vocab_off = len(body)
    for i in range(num_terms):
        base = i * _VOCAB_ENTRY_STRUCT.size
        t_off, t_len, df_val, p_start, p_len = _VOCAB_ENTRY_STRUCT.unpack_from(vocab_entries, base)
        _VOCAB_ENTRY_STRUCT.pack_into(
            vocab_entries, base, term_strings_off + t_off, t_len, df_val, p_start, p_len
        )
    body.extend(vocab_entries)

    post_off = len(body)
    body.extend(postings_buf)

    doc_idx_off = len(body)
    docs_data_start = doc_idx_off + (num_docs + 1) * 4
    cur_doc_byte = docs_data_start
    for blob in doc_blobs:
        body.extend(struct.pack("<I", cur_doc_byte))
        cur_doc_byte += len(blob)
    body.extend(struct.pack("<I", cur_doc_byte))
    for blob in doc_blobs:
        body.extend(blob)

    _HEADER_STRUCT.pack_into(
        body,
        0,
        MAGIC,
        VERSION,
        num_docs,
        num_terms,
        paths_off,
        len(paths_blob),
        vocab_off,
        post_off,
        doc_idx_off,
    )
    return bytes(body)


def write_csr_atomic(target: pathlib.Path, csr_bytes: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    tmp.write_bytes(csr_bytes)
    tmp.replace(target)


class MmapCSRIndex:
    """Read-only `mmap`-backed CSR postings & document slot reader."""

    def __init__(self, path: pathlib.Path) -> None:
        self.path = pathlib.Path(path)
        self._fd = os.open(str(self.path), os.O_RDONLY)
        try:
            st_size = os.fstat(self._fd).st_size
            if st_size < _HEADER_STRUCT.size:
                raise ValueError("CSR_FILE_TOO_SMALL")
            self._mm = mmap.mmap(self._fd, 0, access=mmap.ACCESS_READ)
        except Exception:
            os.close(self._fd)
            self._fd = -1
            raise

        (
            magic,
            ver,
            self.num_docs,
            self.num_terms,
            paths_off,
            paths_len,
            self._vocab_off,
            self._post_off,
            self._doc_idx_off,
        ) = _HEADER_STRUCT.unpack_from(self._mm, 0)
        if magic != MAGIC or ver != VERSION:
            self.close()
            raise ValueError("CSR_HEADER_MISMATCH")

        paths_str = self._mm[paths_off : paths_off + paths_len].decode("utf-8") if paths_len else ""
        self.paths: tuple[str, ...] = tuple(paths_str.split("\n")) if paths_str else ()
        if len(self.paths) != self.num_docs:
            self.close()
            raise ValueError("CSR_PATHS_COUNT_MISMATCH")
        self.paths_folded: tuple[str, ...] = tuple(p.casefold() for p in self.paths)
        self._path_to_id: dict[str, int] | None = None
        self._doc_cache: dict[int, dict[str, Any]] = {}
        self._term_cache: dict[str, tuple[int, tuple[tuple[int, float], ...]] | None] = {}
        self._log_tf_lut: tuple[float, ...] = tuple(
            0.0 if i == 0 else (1.0 + math.log(i)) for i in range(512)
        )

    def close(self) -> None:
        if getattr(self, "_mm", None) is not None:
            try:
                self._mm.close()
            except Exception:
                pass
            self._mm = None  # type: ignore[assignment]
        if getattr(self, "_fd", -1) >= 0:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = -1

    def __del__(self) -> None:
        self.close()

    def _ensure_path_map(self) -> dict[str, int]:
        if self._path_to_id is None:
            self._path_to_id = {p: i for i, p in enumerate(self.paths)}
        return self._path_to_id

    def lookup_term(self, term: str) -> tuple[int, int, int] | None:
        """Binary search UTF-8 `term` in `mmap`; returns `(df, post_start, post_len)` or `None`."""
        mm = self._mm
        target = term.encode("utf-8")
        lo = 0
        hi = self.num_terms - 1
        v_off = self._vocab_off
        v_sz = _VOCAB_ENTRY_STRUCT.size
        while lo <= hi:
            mid = (lo + hi) >> 1
            t_off, t_len, df_val, p_start, p_len = _VOCAB_ENTRY_STRUCT.unpack_from(
                mm, v_off + mid * v_sz
            )
            cur = mm[t_off : t_off + t_len]
            if cur == target:
                return df_val, p_start, p_len
            if cur < target:
                lo = mid + 1
            else:
                hi = mid - 1
        return None

    def get_postings(self, term: str) -> tuple[tuple[str, int], ...] | None:
        hit = self.lookup_term(term)
        if hit is None:
            return None
        _df, p_start, p_len = hit
        if p_len == 0:
            return ()
        byte_start = self._post_off + p_start * _POSTING_STRUCT.size
        byte_end = byte_start + p_len * _POSTING_STRUCT.size
        paths = self.paths
        return tuple(
            (paths[doc_id], tf)
            for doc_id, tf in _POSTING_STRUCT.iter_unpack(self._mm[byte_start:byte_end])
        )

    def get_doc_by_id(self, doc_id: int) -> dict[str, Any]:
        cached = self._doc_cache.get(doc_id)
        if cached is not None:
            return dict(cached)
        start, end = struct.unpack_from("<II", self._mm, self._doc_idx_off + doc_id * 4)
        obj = json.loads(self._mm[start:end].decode("utf-8"))
        self._doc_cache[doc_id] = obj
        return dict(obj)

    def get_doc_by_path(self, path: str) -> dict[str, Any] | None:
        idx = self._ensure_path_map().get(path)
        if idx is None:
            return None
        return self.get_doc_by_id(idx)

    def iter_all_terms_df(self) -> Iterator[tuple[str, int]]:
        mm = self._mm
        v_off = self._vocab_off
        v_sz = _VOCAB_ENTRY_STRUCT.size
        for i in range(self.num_terms):
            t_off, t_len, df_val, _ps, _pl = _VOCAB_ENTRY_STRUCT.unpack_from(mm, v_off + i * v_sz)
            yield mm[t_off : t_off + t_len].decode("utf-8"), df_val

    def _term_scaled_postings(self, term: str) -> tuple[int, tuple[tuple[int, float], ...]] | None:
        if term in self._term_cache:
            return self._term_cache[term]
        hit = self.lookup_term(term)
        if hit is None or hit[2] == 0:
            self._term_cache[term] = None
            return None
        df_val, p_start, p_len = hit
        b_start = self._post_off + p_start * _POSTING_STRUCT.size
        b_end = b_start + p_len * _POSTING_STRUCT.size
        lut = self._log_tf_lut
        lut_len = len(lut)
        scaled = tuple(
            (doc_id, lut[tf] if tf < lut_len else (1.0 + math.log(tf)))
            for doc_id, tf in _POSTING_STRUCT.iter_unpack(self._mm[b_start:b_end])
        )
        res = (max(1, df_val), scaled)
        self._term_cache[term] = res
        return res

    def search_ranked(
        self,
        wanted_terms: set[str],
        query_folded: str,
        *,
        top_k: int = 5,
    ) -> list[tuple[float, str, dict[str, Any]]]:
        """Exact replica of `UnifiedModel.find_source` / `find_any_source` scoring over `mmap`."""
        n_docs = self.num_docs
        if n_docs == 0:
            return []
        total_docs = max(1, n_docs)
        scores = [0.0] * n_docs
        touched: list[int] = []
        seen = bytearray(n_docs)

        for term in sorted(wanted_terms):
            entry = self._term_scaled_postings(term)
            if entry is None:
                continue
            df, scaled = entry
            idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
            for doc_id, tf_weight in scaled:
                if not seen[doc_id]:
                    seen[doc_id] = 1
                    touched.append(doc_id)
                scores[doc_id] += idf * tf_weight

        if not touched:
            return []

        paths = self.paths
        has_slash = "/" in query_folded
        limit = max(1, int(top_k))
        if has_slash:
            paths_folded = self.paths_folded
            candidates = [
                (-(scores[d] + (8.0 if paths_folded[d] in query_folded else 0.0)), paths[d], d)
                for d in touched
                if scores[d] > 0.0
            ]
        else:
            candidates = [(-scores[d], paths[d], d) for d in touched if scores[d] > 0.0]

        top = heapq.nsmallest(limit, candidates) if len(candidates) > limit else sorted(candidates)
        return [
            (-neg_sc, path, self.get_doc_by_id(doc_id))
            for neg_sc, path, doc_id in top
        ]


class MmapDocTableProxy(Mapping[str, dict[str, Any]]):
    """Lazy `Mapping[str, dict]` backed by `MmapCSRIndex` (`O(1)` `len()`, on-demand row decode)."""

    def __init__(self, csr: MmapCSRIndex) -> None:
        self.csr = csr

    def __getitem__(self, key: str) -> dict[str, Any]:
        doc = self.csr.get_doc_by_path(key)
        if doc is None:
            raise KeyError(key)
        return doc

    def __iter__(self) -> Iterator[str]:
        return iter(self.csr.paths)

    def __len__(self) -> int:
        return self.csr.num_docs

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return key in self.csr._ensure_path_map()


class MmapDFProxy(Mapping[str, int]):
    """Lazy `Mapping[str, int]` document-frequency view backed by `MmapCSRIndex`."""

    def __init__(self, csr: MmapCSRIndex) -> None:
        self.csr = csr

    def __getitem__(self, key: str) -> int:
        hit = self.csr.lookup_term(key)
        if hit is None:
            raise KeyError(key)
        return hit[0]

    def get(self, key: str, default: Any = None) -> Any:
        hit = self.csr.lookup_term(key)
        return hit[0] if hit is not None else default

    def __iter__(self) -> Iterator[str]:
        for term, _df in self.csr.iter_all_terms_df():
            yield term

    def __len__(self) -> int:
        return self.csr.num_terms


class MmapPostingsProxy(Mapping[str, tuple[tuple[str, int], ...]]):
    """Lazy `Mapping[str, tuple[tuple[str, int], ...]]` postings view backed by `MmapCSRIndex`."""

    def __init__(self, csr: MmapCSRIndex) -> None:
        self.csr = csr

    def __getitem__(self, key: str) -> tuple[tuple[str, int], ...]:
        res = self.csr.get_postings(key)
        if res is None:
            raise KeyError(key)
        return res

    def get(self, key: str, default: Any = None) -> Any:
        res = self.csr.get_postings(key)
        return res if res is not None else default

    def __iter__(self) -> Iterator[str]:
        for term, _df in self.csr.iter_all_terms_df():
            if self.csr.get_postings(term):
                yield term

    def __len__(self) -> int:
        return self.csr.num_terms


def open_or_build_csr_index(
    name: str,
    digest: str,
    rows_by_path: Mapping[str, Mapping[str, Any]],
    *,
    df_by_term: Mapping[str, int] | None = None,
    cache_dir: pathlib.Path,
) -> MmapCSRIndex:
    """Open existing content-addressed CSR binary sidecar or atomically compile & mmap it."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = cache_dir / f"unified_model_csr_{name}_{digest[:32]}.bin"
    if not fp.is_file():
        blob = build_csr_bytes(rows_by_path, df_by_term)
        tmp = cache_dir / f".tmp_{fp.name}_{os.getpid()}"
        tmp.write_bytes(blob)
        os.replace(tmp, fp)
    return MmapCSRIndex(fp)


def csr_summary(csr: MmapCSRIndex) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "path": str(csr.path),
        "num_docs": csr.num_docs,
        "num_terms": csr.num_terms,
        "size_bytes": csr.path.stat().st_size if csr.path.is_file() else 0,
        "sha256_prefix": hashlib.sha256(csr.path.read_bytes()).hexdigest()[:16] if csr.path.is_file() else "",
        "model_calls": 0,
        "incremental_spend_usd": 0,
    }
