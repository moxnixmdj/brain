"""Content-addressed lossless evidence store for TB-Science cognition.

Active planner context may be bounded, but omission from that context must never
mean destruction. Every observation is stored as canonical JSON addressed by its
SHA-256. The planner sees a compact directory and can request exact fixed-size
chunks by (evidence_id, chunk_index).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_SCIENCE_EVIDENCE_STORE_V1"
CHUNK_CHARS = 1024
MAX_EVIDENCE_ENTRIES = 128
MAX_EVIDENCE_REQUESTS = 4
MAX_CHUNK_INDEX = 4095


class EvidenceStoreError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EvidenceStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._descriptors: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []

    @classmethod
    def from_environment(cls) -> "EvidenceStore":
        explicit = str(os.environ.get("BRAIN_EVIDENCE_STORE_DIR") or "").strip()
        if explicit:
            return cls(explicit)
        journal = str(os.environ.get("BRAIN_CAUSAL_JOURNAL_DIR") or "").strip()
        if not journal:
            raise EvidenceStoreError("BRAIN_EVIDENCE_STORE_DIR_REQUIRED")
        return cls(Path(journal).parent / "BRAIN_EVIDENCE_STORE")

    def put(self, value: Any, *, cycle: int | None = None) -> dict[str, Any]:
        text = canonical_json(value)
        evidence_id = _sha_text(text)
        if evidence_id not in self._descriptors:
            if len(self._order) >= MAX_EVIDENCE_ENTRIES:
                raise EvidenceStoreError("EVIDENCE_DIRECTORY_CAPACITY_EXCEEDED")
            path = self.root / (evidence_id + ".json")
            if path.exists():
                existing = path.read_text(encoding="utf-8")
                if existing != text or _sha_text(existing) != evidence_id:
                    raise EvidenceStoreError("EVIDENCE_CONTENT_ADDRESS_COLLISION")
            else:
                tmp = self.root / (evidence_id + ".tmp")
                tmp.write_text(text, encoding="utf-8")
                os.replace(tmp, path)
            kind = value.get("kind") if isinstance(value, dict) else None
            descriptor = {
                "evidence_id": evidence_id,
                "kind": str(kind or type(value).__name__),
                "chars": len(text),
                "chunk_chars": CHUNK_CHARS,
                "chunk_count": max(1, (len(text) + CHUNK_CHARS - 1) // CHUNK_CHARS),
            }
            if isinstance(cycle, int) and not isinstance(cycle, bool):
                descriptor["cycle"] = cycle
            self._descriptors[evidence_id] = descriptor
            self._order.append(evidence_id)
        return dict(self._descriptors[evidence_id])

    def directory(self) -> list[dict[str, Any]]:
        return [dict(self._descriptors[eid]) for eid in self._order]

    def read_full(self, evidence_id: str) -> str:
        if evidence_id not in self._descriptors:
            raise EvidenceStoreError("EVIDENCE_ID_UNKNOWN")
        path = self.root / (evidence_id + ".json")
        text = path.read_text(encoding="utf-8")
        if _sha_text(text) != evidence_id:
            raise EvidenceStoreError("EVIDENCE_CONTENT_HASH_MISMATCH")
        return text

    def read_chunk(self, evidence_id: str, chunk_index: int) -> dict[str, Any]:
        if (
            not isinstance(chunk_index, int)
            or isinstance(chunk_index, bool)
            or chunk_index < 0
            or chunk_index > MAX_CHUNK_INDEX
        ):
            raise EvidenceStoreError("EVIDENCE_CHUNK_INDEX_INVALID")
        text = self.read_full(evidence_id)
        count = max(1, (len(text) + CHUNK_CHARS - 1) // CHUNK_CHARS)
        if chunk_index >= count:
            raise EvidenceStoreError("EVIDENCE_CHUNK_INDEX_OUT_OF_RANGE")
        start = chunk_index * CHUNK_CHARS
        end = min(len(text), start + CHUNK_CHARS)
        content = text[start:end]
        return {
            "kind": "BRAIN_EXACT_EVIDENCE_CHUNK",
            "evidence_id": evidence_id,
            "chunk_index": chunk_index,
            "chunk_count": count,
            "char_start": start,
            "char_end": end,
            "full_chars": len(text),
            "chunk_sha256": _sha_text(content),
            "content": content,
        }

    def resolve_requests(self, requests: Any) -> list[dict[str, Any]]:
        if requests is None:
            return []
        if not isinstance(requests, list) or len(requests) > MAX_EVIDENCE_REQUESTS:
            raise EvidenceStoreError("EVIDENCE_REQUESTS_INVALID")
        out: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()
        for row in requests:
            if not isinstance(row, dict):
                raise EvidenceStoreError("EVIDENCE_REQUEST_OBJECT_REQUIRED")
            evidence_id = row.get("evidence_id")
            chunk_index = row.get("chunk_index")
            if (
                not isinstance(evidence_id, str)
                or len(evidence_id) != 64
                or any(c not in "0123456789abcdef" for c in evidence_id)
            ):
                raise EvidenceStoreError("EVIDENCE_REQUEST_ID_INVALID")
            if not isinstance(chunk_index, int) or isinstance(chunk_index, bool):
                raise EvidenceStoreError("EVIDENCE_CHUNK_INDEX_INVALID")
            key = (evidence_id, chunk_index)
            if key in seen:
                continue
            seen.add(key)
            out.append(self.read_chunk(evidence_id, chunk_index))
        return out

    def reconstruct(self, evidence_id: str) -> str:
        text = self.read_full(evidence_id)
        chunks = [
            self.read_chunk(evidence_id, i)["content"]
            for i in range(max(1, (len(text) + CHUNK_CHARS - 1) // CHUNK_CHARS))
        ]
        rebuilt = "".join(chunks)
        if rebuilt != text or _sha_text(rebuilt) != evidence_id:
            raise EvidenceStoreError("EVIDENCE_RECONSTRUCTION_MISMATCH")
        return rebuilt
