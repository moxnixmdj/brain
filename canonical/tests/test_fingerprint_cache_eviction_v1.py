"""A cache must evict what is unused, not what arrived first.

Measured 2026-11-03 on `407cc3c`, before the fix: a fingerprint key written and then read
**20 times** was evicted by 256 one-shot keys, while the one-shot key written most recently
survived. The cache was FIFO. A fingerprint costs 5-8 s of real acting to produce; the reuse it
exists to buy was therefore silently paid for again, forever, by exactly the goals that were
used the most.

This is the failure mode the repository keeps finding (see the honest-baseline note): a green
verdict over work that did not happen. The cache reported a hit rate of zero for its hottest
key and nothing anywhere called it a defect.

The three pins below are the whole policy, and they are deliberately about what is *observable*:
  * a hot key survives churn;
  * the store stays bounded;
  * a read is not made expensive to achieve the first thing.
"""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest

from canonical.runtime import transfer_learning_v1 as tl


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    path = tmp_path / "fp.json"
    monkeypatch.setenv("BRAIN_TRANSFER_LEARNING_FINGERPRINTS", str(path))
    return path


def _touch_now(path: Path, key: str) -> None:
    """Record a use 'an hour later', without waiting an hour."""
    data = tl._fp_load()
    data["fingerprints"][key]["_used"] = time.time()
    tl._fp_save(data)


def test_a_key_used_repeatedly_survives_churn_of_one_shot_keys(cache):
    tl.cache_fingerprint("hot", {"probe": 1})
    for i in range(tl.FP_MAX + 40):
        tl.cache_fingerprint(f"one-shot-{i}", {"probe": i})
        if i % 8 == 0:
            _touch_now(cache, "hot")
    assert tl.cached_fingerprint("hot") is not None, (
        "the key with the most evidence of use was evicted; eviction is still FIFO")


def test_the_store_stays_bounded(cache):
    for i in range(tl.FP_MAX * 2):
        tl.cache_fingerprint(f"k{i}", {"probe": i})
    assert len(tl._fp_load()["fingerprints"]) == tl.FP_MAX


def test_the_least_recently_used_key_is_the_one_that_goes(cache):
    tl.cache_fingerprint("stale", {"probe": 0})
    data = tl._fp_load()
    data["fingerprints"]["stale"]["_used"] = 1.0          # long ago
    tl._fp_save(data)
    for i in range(tl.FP_MAX):
        tl.cache_fingerprint(f"fresh-{i}", {"probe": i})
    assert tl.cached_fingerprint("stale") is None
    assert tl.cached_fingerprint(f"fresh-{tl.FP_MAX - 1}") is not None


def test_a_read_stays_cheap(cache):
    """A hit must not rewrite the file on every read: 0.39 ms read vs 3.2 ms write measured."""
    for i in range(tl.FP_MAX):
        tl.cache_fingerprint(f"k{i}", {"probe": i})
    before = cache.stat().st_mtime_ns
    for _ in range(50):
        assert tl.cached_fingerprint("k0") is not None
    assert cache.stat().st_mtime_ns == before, (
        "50 consecutive reads rewrote the cache file; the touch is not rate-limited")


def test_rows_written_before_the_fix_are_treated_as_oldest(cache):
    """A pre-existing cache has no `_used` on its rows. Losing those is the safe direction:
    they are re-measured by acting, whereas keeping them could evict a key in active use."""
    cache.write_text('{"fingerprints": {"legacy": {"probe": 0}}}', encoding="utf-8")
    assert tl.cached_fingerprint("legacy") == {"probe": 0}   # still readable
    for i in range(tl.FP_MAX):
        tl.cache_fingerprint(f"new-{i}", {"probe": i})
    assert tl.cached_fingerprint("legacy") is None
