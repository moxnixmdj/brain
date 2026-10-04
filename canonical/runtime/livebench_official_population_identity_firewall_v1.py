#!/usr/bin/env python3
"""Fail-closed identity firewall for the official LiveBench IF comparator.

The project has a content-addressed older public HF proxy and a separate official
2026 leaderboard aggregate. Equal population/task counts do not establish row
identity. This reducer prevents a proxy-only proof from authorizing a
single-scorer-family critical-path collapse.

A single-family collapse is admissible only when the official comparator rows
are identity-bound to a population whose release dates select that family.
Otherwise the only identity-independent route is a successor whose verified
coverage spans every scorer family still consistent with official evidence.
"""
from __future__ import annotations

from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_OFFICIAL_POPULATION_IDENTITY_FIREWALL_V1"


def adjudicate(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    official_row_identity_bound = bool(args.get("official_row_identity_bound", False))
    official_scorer_family = str(args.get("official_scorer_family") or "").strip().upper()
    universal_legacy_verified = bool(args.get("universal_legacy_verified", False))
    universal_modern_verified = bool(args.get("universal_modern_verified", False))
    proxy_only_evidence = bool(args.get("proxy_only_evidence", False))

    if official_scorer_family not in {"", "LEGACY_IFEVAL", "MODERN_IFBENCH"}:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": "UNKNOWN_OFFICIAL_SCORER_FAMILY",
            "single_family_collapse_authorized": False,
            "release_agnostic_successor_authorized": False,
        }

    if official_row_identity_bound and not official_scorer_family:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": "IDENTITY_BOUND_WITHOUT_SCORER_FAMILY",
            "single_family_collapse_authorized": False,
            "release_agnostic_successor_authorized": False,
        }

    if official_row_identity_bound and official_scorer_family:
        return {
            "schema": SCHEMA,
            "status": "PASS_OFFICIAL_IDENTITY_BOUND",
            "reason": "OFFICIAL_ROW_IDENTITY_AND_SCORER_FAMILY_BOUND",
            "official_scorer_family": official_scorer_family,
            "single_family_collapse_authorized": True,
            "release_agnostic_successor_authorized": False,
            "proxy_only_evidence": proxy_only_evidence,
        }

    if universal_legacy_verified and universal_modern_verified:
        return {
            "schema": SCHEMA,
            "status": "PASS_IDENTITY_IRRELEVANT_BY_UNIVERSAL_COVERAGE",
            "reason": "BOTH_STILL_POSSIBLE_SCORER_FAMILIES_ARE_VERIFIED",
            "official_scorer_family": None,
            "single_family_collapse_authorized": False,
            "release_agnostic_successor_authorized": True,
            "proxy_only_evidence": proxy_only_evidence,
        }

    missing = []
    if not universal_legacy_verified:
        missing.append("LEGACY_IFEVAL_VERIFIED_COVERAGE")
    if not universal_modern_verified:
        missing.append("MODERN_IFBENCH_VERIFIED_COVERAGE")
    return {
        "schema": SCHEMA,
        "status": "BLOCKED_OFFICIAL_POPULATION_IDENTITY_UNPROVED",
        "reason": (
            "PROXY_CARDINALITY_OR_RELEASE_METADATA_DOES_NOT_BIND_THE_OFFICIAL_"
            "2026_COMPARATOR_ROW_SET"
        ),
        "official_scorer_family": None,
        "single_family_collapse_authorized": False,
        "release_agnostic_successor_authorized": False,
        "proxy_only_evidence": proxy_only_evidence,
        "missing_for_identity_independent_route": missing,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return adjudicate(args)


if __name__ == "__main__":
    import json
    print(json.dumps(adjudicate({}), indent=2, sort_keys=True))
