"""The one-shot-regime census must partition the registry, not sort it by vibe.

The failure mode this test exists to prevent is a census that quietly counts a *declaration* as a
*verification*, or that drops a capability it cannot classify. Both would inflate the only number
anyone will quote from it.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

import sys

sys.path.insert(0, str(ROOT))

from one_shot_regime_census_20261112 import (  # noqa: E402
    DECLARED,
    NONE,
    RECEIPTED,
    census,
    truthy,
)


def test_every_capability_lands_in_exactly_one_cell():
    result = census()
    records = result["records"]
    assert len(records) == result["summary"]["capabilities"]
    assert len({r["capability_id"] for r in records}) == len(records)
    assert sum(result["summary"]["cells"].values()) == len(records)


def test_the_three_strengths_are_mutually_exclusive_by_construction():
    for r in census()["records"]:
        strength = r["verifier_strength"]
        assert strength in (RECEIPTED, DECLARED, NONE)
        if strength == RECEIPTED:
            assert r["independence_markers"] and r["receipt_present"]
        elif strength == DECLARED:
            assert r["independence_markers"] and not r["receipt_present"]
        else:
            # NONE means "no independence was declared". A receipt may still sit on disk; a
            # receipt nobody attributed to an independent party is not a check, and the census
            # counts it separately rather than promoting it.
            assert r["independence_markers"] == []


def test_a_declaration_without_a_receipt_is_not_counted_as_safe():
    result = census()
    safe = set(result["one_shot_safe_ids"])
    declared_only = [
        r["capability_id"] for r in result["records"] if r["verifier_strength"] == DECLARED
    ]
    assert declared_only, "the DECLARED tier must not be empty, or this test proves nothing"
    assert not safe.intersection(declared_only)
    assert result["summary"]["one_shot_safe"] == len(safe)


def test_named_verifiers_count_and_negations_do_not():
    # `independently_verified_by` names the verifier; that is a declaration.
    assert truthy("archive.verify.tar_gz.gnu") is True
    # A marker whose value says no check happened is not a declaration.
    for negative in ("", "false", "no", "pending", "unverified", "unknown"):
        assert truthy(negative) is False
    assert truthy(True) is True
    assert truthy(0) is False


def test_every_orphan_receipt_is_actually_absent():
    result = census()
    for path in result["orphan_receipt_paths"]:
        assert not (ROOT / path).exists(), path
    assert result["summary"]["orphan_receipts"] == len(result["orphan_receipt_paths"])


def test_the_summary_is_derived_from_the_records():
    result = census()
    records, summary = result["records"], result["summary"]
    assert summary["typed_interface"] == sum(r["typed_interface"] for r in records)
    assert summary["receipted"] == sum(r["verifier_strength"] == RECEIPTED for r in records)
    assert summary["runtime_predicate_is_self_reported"] == sum(
        r["runtime_predicate_is_self_reported"] for r in records
    )
    assert summary["typed_but_unchecked"] == sum(
        r["typed_interface"] and r["verifier_strength"] == NONE for r in records
    )


def test_the_census_is_deterministic():
    first = json.dumps(census(), sort_keys=True)
    second = json.dumps(census(), sort_keys=True)
    assert first == second
