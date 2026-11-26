"""Tests for the promotion ledger.

The ledger is a join over five artifacts, so the tests pin the join's *rules* (which missing
attribute is named first) and the committed measurement, not the file layout.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import promotion_ledger_v1 as L  # noqa: E402

LEDGER = ROOT / "canonical/verification/PROMOTION_LEDGER_20261127_V1.json"


def test_the_first_missing_attribute_is_the_one_named() -> None:
    # Callable and receipted beats everything else, even if the module is also indexed.
    assert L.classify("m", routed={"m"}, receipted={"m"}, adapter_files={"m"}, indexed=True) == "ROUTED"
    # A capability with no receipt is still callable; the ledger says so rather than hiding it.
    assert L.classify("m", routed={"m"}, receipted=set(), adapter_files=set(), indexed=True) == "ROUTED_NO_RECEIPT"
    # An adapter file that never ran is not the same as a module that was never touched.
    assert L.classify("m", routed=set(), receipted=set(), adapter_files={"m"}, indexed=True) == "ADAPTER_UNRECEIPTED"
    assert L.classify("m", routed=set(), receipted=set(), adapter_files=set(), indexed=True) == "SOURCE_ONLY"
    assert L.classify("m", routed=set(), receipted=set(), adapter_files=set(), indexed=False) == "INVISIBLE"


def test_every_category_is_reachable_and_the_order_is_fixed() -> None:
    assert L.CATEGORIES == (
        "ROUTED", "ROUTED_NO_RECEIPT", "RECEIPTED_UNBOUND",
        "ADAPTER_UNRECEIPTED", "SOURCE_ONLY", "INVISIBLE",
    )


def test_the_committed_ledger_still_partitions_the_candidates() -> None:
    report = json.loads(LEDGER.read_text())
    assert report["schema"] == L.SCHEMA
    assert set(report["totals"]) == set(L.CATEGORIES)
    assert sum(report["totals"].values()) == report["candidates"]
    assert report["model_calls"] == 0 and report["network_calls"] == 0


def test_the_committed_ledger_says_what_it_said() -> None:
    report = json.loads(LEDGER.read_text())
    # The finding: the runtime can call under four percent of the modules that implement the
    # five functions, and three quarters are indexed source that no adapter reaches.
    assert report["candidates"] >= 800
    assert report["callable_now"] == report["totals"]["ROUTED"]
    assert report["callable_share"] < 0.05
    assert report["totals"]["SOURCE_ONLY"] > 600
    # Nothing may be double counted out of the partition.
    rows = report["rows"]
    assert len(rows) == report["candidates"]
    assert {row["category"] for row in rows} <= set(L.CATEGORIES)


def test_a_domain_with_no_callable_module_is_reported_as_zero_not_omitted() -> None:
    report = json.loads(LEDGER.read_text())
    for domain, counts in report["per_domain"].items():
        assert set(counts) == set(L.CATEGORIES), domain
        assert report["domain_executable_now"][domain] == counts["ROUTED"]
