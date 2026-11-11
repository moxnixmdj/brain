#!/usr/bin/env python3
"""Fail-closed root classification precedence for LiveBench IF.

An exact failure on a proxy population is valuable evidence about that proxy.
It is not evidence that the official comparator population failed unless row
identity (or an equivalent content-addressed population equivalence) is bound.

This reducer prevents downstream exact-score evidence from silently overriding
an upstream population-identity uncertainty.
"""
from __future__ import annotations
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_ROOT_IDENTITY_PRECEDENCE_V1"


def adjudicate(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    official_population_identity_bound = bool(
        args.get("official_population_identity_bound", False)
    )
    proxy_v6_exact_fail = bool(args.get("proxy_v6_exact_fail", False))
    official_exact_fail = bool(args.get("official_exact_fail", False))
    official_exact_pass = bool(args.get("official_exact_pass", False))

    if official_exact_fail and official_exact_pass:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_CONTRADICTORY_OFFICIAL_SCORE_EVIDENCE",
            "terminal_predicate_root": None,
            "proxy_failure_preserved": proxy_v6_exact_fail,
            "root1_authorized": False,
        }

    if official_exact_pass:
        return {
            "schema": SCHEMA,
            "status": "OFFICIAL_PREDICATE_PROVED_PASS",
            "terminal_predicate_root": "CLOSED_PASS",
            "proxy_failure_preserved": proxy_v6_exact_fail,
            "root1_authorized": False,
        }

    if official_exact_fail:
        return {
            "schema": SCHEMA,
            "status": "OFFICIAL_PREDICATE_PROVED_FALSE",
            "terminal_predicate_root": "ROOT1_POSITIVE_OPERATIVE_GAP",
            "proxy_failure_preserved": proxy_v6_exact_fail,
            "root1_authorized": True,
        }

    if proxy_v6_exact_fail and official_population_identity_bound:
        return {
            "schema": SCHEMA,
            "status": "PROXY_EXACT_FAIL_PROMOTABLE_BY_PROVED_POPULATION_IDENTITY",
            "terminal_predicate_root": "ROOT1_POSITIVE_OPERATIVE_GAP",
            "proxy_failure_preserved": True,
            "root1_authorized": True,
        }

    if proxy_v6_exact_fail:
        return {
            "schema": SCHEMA,
            "status": "PROXY_EXACT_FAIL_QUARANTINED_FROM_OFFICIAL_ROOT_CLASSIFICATION",
            "terminal_predicate_root": "ROOT2_ONLY",
            "reason": "OFFICIAL_POPULATION_IDENTITY_UNPROVED",
            "proxy_failure_preserved": True,
            "root1_authorized": False,
        }

    return {
        "schema": SCHEMA,
        "status": "OFFICIAL_SCORE_UNRESOLVED",
        "terminal_predicate_root": "ROOT2_ONLY",
        "reason": "NO_ADMISSIBLE_OFFICIAL_PASS_OR_FAIL_RESULT",
        "proxy_failure_preserved": False,
        "root1_authorized": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return adjudicate(args)


if __name__ == "__main__":
    import json
    print(json.dumps(adjudicate({}), indent=2, sort_keys=True))
