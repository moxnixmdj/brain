#!/usr/bin/env python3
"""Persistent content-addressable cache for hardcore software engineering.

Never recompute what has already been verified. Stores on disk, keyed by
SHA-256 of (capability_id + canonical inputs), so cache survives across
sessions, process restarts, and machine reboots.

Cache entries:
  * AST indexes (tree-sitter parse trees per file)
  * Verified patches (patch → test results → verified)
  * Fault localization results (source → suspiciousness ranking)
  * Test execution results (test command → pass/fail)
  * Capability execution results (capability_id + inputs → output)

All entries are content-addressed: identical inputs always produce identical
cache keys. Cache is append-only; entries are never mutated in place.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = ROOT / "canonical" / "cache"

SCHEMA = "PROJECT_BRAIN_PERSISTENT_CACHE_V1"


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _sha(obj: Any) -> str:
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


class PersistentCache:
    """Content-addressable persistent cache on disk.

    Layout:
      <cache_dir>/
        <kind>/          # ast, patch, fault, test, capability
          <sha256[0:2]>/ # sharding for filesystem scalability
            <sha256[2:]>.json  # the entry
    """

    def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._hits = 0
        self._misses = 0

    # -- internal path helpers ------------------------------------------------

    def _entry_path(self, kind: str, key: str) -> Path:
        return self.cache_dir / kind / key[:2] / f"{key[2:]}.json"

    def _write_atomic(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-",
                                   suffix=".json")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # -- public API -----------------------------------------------------------

    def get(self, kind: str, obj: Any) -> Optional[dict[str, Any]]:
        """Look up an entry by content hash. Returns the stored value or None."""
        key = _sha({"kind": kind, "obj": obj})
        path = self._entry_path(kind, key)
        if not path.is_file():
            self._misses += 1
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            self._misses += 1
            return None
        # Verify content address matches
        if entry.get("_key") != key:
            self._misses += 1
            return None
        self._hits += 1
        return entry.get("value")

    def put(self, kind: str, obj: Any, value: Any,
            ttl_seconds: Optional[int] = None) -> str:
        """Store a value content-addressed. Returns the cache key."""
        key = _sha({"kind": kind, "obj": obj})
        path = self._entry_path(kind, key)
        if path.is_file():
            return key  # already present — idempotent

        entry = {
            "_key": key,
            "_kind": kind,
            "_created_at": time.time(),
            "_ttl_seconds": ttl_seconds,
            "_schema": SCHEMA,
            "value": value,
        }
        self._write_atomic(path, json.dumps(entry, indent=2,
                                            ensure_ascii=False).encode("utf-8"))
        return key

    def has(self, kind: str, obj: Any) -> bool:
        return self.get(kind, obj) is not None

    def delete(self, kind: str, obj: Any) -> bool:
        key = _sha({"kind": kind, "obj": obj})
        path = self._entry_path(kind, key)
        if path.is_file():
            path.unlink()
            # Try to clean up empty shard dir
            try:
                path.parent.rmdir()
            except OSError:
                pass
            return True
        return False

    def stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total else 0.0
        # Count entries on disk
        entry_count = 0
        for kind_dir in self.cache_dir.iterdir():
            if kind_dir.is_dir():
                for shard in kind_dir.iterdir():
                    if shard.is_dir():
                        entry_count += len(list(shard.glob("*.json")))
        return {
            "schema": SCHEMA,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "entry_count": entry_count,
            "cache_dir": str(self.cache_dir),
        }

    def clear(self, kind: Optional[str] = None) -> int:
        """Clear all entries, or all entries of a given kind. Returns count deleted."""
        deleted = 0
        targets = [self.cache_dir / kind] if kind else \
            [d for d in self.cache_dir.iterdir() if d.is_dir()]
        for kind_dir in targets:
            if not kind_dir.is_dir():
                continue
            for shard in kind_dir.iterdir():
                if not shard.is_dir():
                    continue
                for f in shard.glob("*.json"):
                    f.unlink()
                    deleted += 1
                try:
                    shard.rmdir()
                except OSError:
                    pass
            try:
                kind_dir.rmdir()
            except OSError:
                pass
        return deleted


# ---------------------------------------------------------------------------
# Module-level singleton cache
# ---------------------------------------------------------------------------

_cache: Optional[PersistentCache] = None


def get_cache() -> PersistentCache:
    global _cache
    if _cache is None:
        _cache = PersistentCache()
    return _cache


def cache_get(kind: str, obj: Any) -> Optional[dict[str, Any]]:
    return get_cache().get(kind, obj)


def cache_put(kind: str, obj: Any, value: Any,
              ttl_seconds: Optional[int] = None) -> str:
    return get_cache().put(kind, obj, value, ttl_seconds=ttl_seconds)


def cache_has(kind: str, obj: Any) -> bool:
    return get_cache().has(kind, obj)


# ---------------------------------------------------------------------------
# Pre-typed convenience wrappers for SWE workloads
# ---------------------------------------------------------------------------

def cache_ast_index(file_path: str, source_hash: str,
                    ast_data: dict[str, Any],
                    ttl_seconds: int = 86400 * 7) -> str:
    """Cache a tree-sitter AST index for a source file."""
    return cache_put("ast", {"file": file_path, "source_hash": source_hash},
                     ast_data, ttl_seconds=ttl_seconds)


def cache_get_ast_index(file_path: str, source_hash: str
                        ) -> Optional[dict[str, Any]]:
    return cache_get("ast", {"file": file_path, "source_hash": source_hash})


def cache_verified_patch(patch_hash: str, test_command: str,
                         test_results: list[dict[str, Any]],
                         verified: bool,
                         ttl_seconds: int = 86400 * 30) -> str:
    """Cache a verified patch result."""
    return cache_put("patch", {"patch_hash": patch_hash,
                               "test_command": test_command},
                     {"test_results": test_results, "verified": verified},
                     ttl_seconds=ttl_seconds)


def cache_get_verified_patch(patch_hash: str, test_command: str
                             ) -> Optional[dict[str, Any]]:
    return cache_get("patch", {"patch_hash": patch_hash,
                               "test_command": test_command})


def cache_fault_localization(source_file: str,
                             test_results_hash: str,
                             suspiciousness: float,
                             ttl_seconds: int = 86400) -> str:
    """Cache fault localization result for a source file."""
    return cache_put("fault", {"file": source_file,
                               "test_results_hash": test_results_hash},
                     {"suspiciousness": suspiciousness},
                     ttl_seconds=ttl_seconds)


def cache_get_fault_localization(source_file: str,
                                 test_results_hash: str
                                 ) -> Optional[dict[str, Any]]:
    return cache_get("fault", {"file": source_file,
                               "test_results_hash": test_results_hash})


def cache_test_result(test_command_hash: str,
                      result: dict[str, Any],
                      ttl_seconds: int = 86400) -> str:
    """Cache a test execution result."""
    return cache_put("test", {"command_hash": test_command_hash},
                     result, ttl_seconds=ttl_seconds)


def cache_get_test_result(test_command_hash: str
                          ) -> Optional[dict[str, Any]]:
    return cache_get("test", {"command_hash": test_command_hash})


def cache_capability_result(capability_id: str,
                            inputs_hash: str,
                            result: dict[str, Any],
                            ttl_seconds: int = 86400) -> str:
    """Cache a capability execution result."""
    return cache_put("capability", {"capability_id": capability_id,
                                    "inputs_hash": inputs_hash},
                     result, ttl_seconds=ttl_seconds)


def cache_get_capability_result(capability_id: str,
                                inputs_hash: str
                                ) -> Optional[dict[str, Any]]:
    return cache_get("capability", {"capability_id": capability_id,
                                    "inputs_hash": inputs_hash})
