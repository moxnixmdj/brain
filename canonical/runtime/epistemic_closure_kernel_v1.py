"""Exact finite epistemic-closure and minimum-discriminator kernel.

This module is deliberately narrow. It never invents semantic worlds. Given an
explicit finite admissible world set, it:
1) filters worlds by observed facts;
2) decides only when all surviving worlds require the same decision;
3) otherwise computes an exact minimum-cost set of authorized observable facts
   that separates every pair of worlds requiring different decisions; or
4) returns principled abstention when no such discriminator exists.

It grants no capability/family credit and consumes no fresh evidence.
"""
from __future__ import annotations

from itertools import combinations
from math import isfinite
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_EPISTEMIC_CLOSURE_KERNEL_V1"
MAX_EXACT_FACTS = 20
Scalar = str | int | float | bool | None


def _scalar(v: Any) -> bool:
    return v is None or isinstance(v, (str, int, float, bool))


def _cost(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    x = float(v)
    return x if isfinite(x) and x >= 0 else None


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "decision": None,
        "minimum_discriminator_facts": [],
        "minimum_discriminator_exact": False,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    observed = doc.get("observed_facts", {})
    worlds = doc.get("worlds")
    queries = doc.get("queryable_facts", [])

    if not isinstance(observed, Mapping) or any(
        not isinstance(k, str) or not k or not _scalar(v)
        for k, v in observed.items()
    ):
        return _fail("OBSERVED_FACTS_INVALID")
    if not isinstance(worlds, list) or not worlds:
        return _fail("WORLDS_REQUIRED")
    if not isinstance(queries, list):
        return _fail("QUERYABLE_FACTS_INVALID")

    parsed_worlds: list[tuple[str, dict[str, Scalar], str]] = []
    ids: set[str] = set()
    for i, row in enumerate(worlds):
        if not isinstance(row, Mapping):
            return _fail(f"WORLD_{i}_INVALID")
        wid = row.get("id")
        decision = row.get("decision")
        facts = row.get("facts")
        if not isinstance(wid, str) or not wid or wid in ids:
            return _fail("WORLD_IDENTITIES_INVALID_OR_DUPLICATE")
        if not isinstance(decision, str) or not decision:
            return _fail(f"WORLD_DECISION_INVALID:{wid}")
        if not isinstance(facts, Mapping) or any(
            not isinstance(k, str) or not k or not _scalar(v)
            for k, v in facts.items()
        ):
            return _fail(f"WORLD_FACTS_INVALID:{wid}")
        ids.add(wid)
        parsed_worlds.append((wid, dict(facts), decision))

    surviving = [
        w for w in parsed_worlds
        if all(k in w[1] and w[1][k] == v for k, v in observed.items())
    ]
    if not surviving:
        return _fail("NO_ADMISSIBLE_WORLD_AFTER_OBSERVATIONS")

    decisions = sorted({w[2] for w in surviving})
    if len(decisions) == 1:
        return {
            "schema": SCHEMA,
            "status": "DECIDE",
            "errors": [],
            "decision": decisions[0],
            "surviving_world_ids": [w[0] for w in surviving],
            "surviving_decisions": decisions,
            "minimum_discriminator_facts": [],
            "minimum_discriminator_exact": True,
            "reason": "ALL_ADMISSIBLE_WORLDS_AGREE",
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    query_rows: list[tuple[str, float]] = []
    seen_facts: set[str] = set()
    for i, row in enumerate(queries):
        if not isinstance(row, Mapping):
            return _fail(f"QUERY_{i}_INVALID")
        fact = row.get("fact")
        cost = _cost(row.get("cost", 0))
        if not isinstance(fact, str) or not fact or fact in seen_facts:
            return _fail("QUERY_IDENTITIES_INVALID_OR_DUPLICATE")
        if cost is None:
            return _fail(f"QUERY_COST_INVALID:{fact}")
        seen_facts.add(fact)
        if row.get("authorized", True) is True and row.get("available", True) is True:
            if fact not in observed:
                if not all(fact in w[1] for w in surviving):
                    return _fail(f"QUERY_FACT_NOT_MODELED_IN_ALL_SURVIVING_WORLDS:{fact}")
                query_rows.append((fact, cost))

    if len(query_rows) > MAX_EXACT_FACTS:
        return {
            "schema": SCHEMA,
            "status": "AMBIGUOUS_EXACT_SEARCH_LIMIT",
            "errors": [],
            "decision": None,
            "surviving_world_ids": [w[0] for w in surviving],
            "surviving_decisions": decisions,
            "minimum_discriminator_facts": [],
            "minimum_discriminator_exact": False,
            "reason": f"QUERYABLE_FACT_COUNT_EXCEEDS_{MAX_EXACT_FACTS}",
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    conflicting_pairs: list[tuple[int, int]] = []
    for i in range(len(surviving)):
        for j in range(i + 1, len(surviving)):
            if surviving[i][2] != surviving[j][2]:
                conflicting_pairs.append((i, j))

    separators: dict[str, set[tuple[int, int]]] = {}
    for fact, _ in query_rows:
        separators[fact] = {
            pair for pair in conflicting_pairs
            if surviving[pair[0]][1][fact] != surviving[pair[1]][1][fact]
        }

    pair_set = set(conflicting_pairs)
    coverable = set().union(*(separators[f] for f, _ in query_rows)) if query_rows else set()
    if pair_set - coverable:
        unresolved = [
            {
                "world_a": surviving[i][0],
                "decision_a": surviving[i][2],
                "world_b": surviving[j][0],
                "decision_b": surviving[j][2],
            }
            for i, j in sorted(pair_set - coverable)
        ]
        return {
            "schema": SCHEMA,
            "status": "ABSTAIN_NONIDENTIFIABLE",
            "errors": [],
            "decision": None,
            "surviving_world_ids": [w[0] for w in surviving],
            "surviving_decisions": decisions,
            "minimum_discriminator_facts": [],
            "minimum_discriminator_exact": True,
            "unresolvable_decision_conflicts": unresolved,
            "reason": "AUTHORIZED_OBSERVABLES_CANNOT_SEPARATE_ALL_DIFFERENT_DECISION_WORLDS",
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    best: tuple[tuple[float, int, tuple[str, ...]], tuple[str, ...]] | None = None
    facts = [f for f, _ in query_rows]
    cost_by_fact = dict(query_rows)
    for n in range(len(facts) + 1):
        for combo in combinations(facts, n):
            covered = set().union(*(separators[f] for f in combo)) if combo else set()
            if covered != pair_set:
                continue
            chosen = tuple(sorted(combo))
            key = (sum(cost_by_fact[f] for f in combo), len(combo), chosen)
            if best is None or key < best[0]:
                best = (key, chosen)

    assert best is not None
    return {
        "schema": SCHEMA,
        "status": "QUERY_MINIMUM_DISCRIMINATOR",
        "errors": [],
        "decision": None,
        "surviving_world_ids": [w[0] for w in surviving],
        "surviving_decisions": decisions,
        "minimum_discriminator_facts": list(best[1]),
        "minimum_discriminator_total_cost": best[0][0],
        "minimum_discriminator_exact": True,
        "reason": "MINIMUM_COST_FACT_SET_SEPARATES_EVERY_DIFFERENT_DECISION_WORLD_PAIR",
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
