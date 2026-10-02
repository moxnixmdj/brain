"""Exact zero-credit solver over shared terminal certificate candidates.

This operates above the action scheduler.  It does not grant predicate, family,
execution, or promotion credit.  Given unresolved predicates and candidate
certificate obligations, it finds the candidate subset that maximizes frontier
coverage, then minimizes new reality, then certificate count, then lexicographic
certificate IDs.

The point is to schedule missing truths rather than procedures.  A certificate
may cover many predicates when the *same exact verified proposition* is a shared
precondition.  Callers must never merge merely similar semantics.
"""
from __future__ import annotations

from itertools import combinations
from math import isfinite
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_CERTIFICATE_CUT_V1"
MAX_EXACT_CERTIFICATES = 24


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "selected_certificates": [],
        "covered_predicates": [],
        "uncovered_predicates": [],
        "quotient_classes": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        return _fail("INPUT_NOT_OBJECT")

    unresolved = doc.get("unresolved_predicates")
    certificates = doc.get("certificates")
    if (
        not isinstance(unresolved, list)
        or not unresolved
        or any(not isinstance(x, str) or not x for x in unresolved)
        or len(set(unresolved)) != len(unresolved)
    ):
        return _fail("UNRESOLVED_PREDICATES_INVALID")
    if not isinstance(certificates, list):
        return _fail("CERTIFICATES_INVALID")

    unresolved_set = set(unresolved)
    parsed = []
    quotient: dict[tuple[Any, ...], list[str]] = {}

    for i, row in enumerate(certificates):
        if not isinstance(row, Mapping):
            return _fail(f"CERTIFICATE_{i}_INVALID")
        cid = row.get("id")
        targets = row.get("target_predicates")
        requires = row.get("requires", [])
        if not isinstance(cid, str) or not cid:
            return _fail(f"CERTIFICATE_{i}_ID_INVALID")
        if (
            not isinstance(targets, list)
            or not targets
            or any(not isinstance(x, str) or not x for x in targets)
            or len(set(targets)) != len(targets)
        ):
            return _fail(f"CERTIFICATE_TARGETS_INVALID:{cid}")
        if any(x not in unresolved_set for x in targets):
            return _fail(f"CERTIFICATE_TARGET_OUTSIDE_FRONTIER:{cid}")
        if (
            not isinstance(requires, list)
            or any(not isinstance(x, str) or not x for x in requires)
            or len(set(requires)) != len(requires)
        ):
            return _fail(f"CERTIFICATE_REQUIRES_INVALID:{cid}")

        raw_cost = row.get("new_reality_units", 0)
        if isinstance(raw_cost, bool) or not isinstance(raw_cost, (int, float)):
            return _fail(f"CERTIFICATE_COST_INVALID:{cid}")
        cost = float(raw_cost)
        if not isfinite(cost) or cost < 0:
            return _fail(f"CERTIFICATE_COST_INVALID:{cid}")

        parsed_row = {
            "id": cid,
            "targets": set(targets),
            "requires": tuple(sorted(requires)),
            "cost": cost,
            "certificate_class": row.get("certificate_class"),
        }
        parsed.append(parsed_row)
        qkey = (
            tuple(sorted(targets)),
            tuple(sorted(requires)),
            row.get("certificate_class"),
        )
        quotient.setdefault(qkey, []).append(cid)

    ids = [x["id"] for x in parsed]
    if len(set(ids)) != len(ids):
        return _fail("DUPLICATE_CERTIFICATE_ID")

    if len(parsed) > MAX_EXACT_CERTIFICATES:
        return {
            **_fail(f"CERTIFICATE_COUNT_EXCEEDS_{MAX_EXACT_CERTIFICATES}"),
            "status": "EXACT_SEARCH_LIMIT",
            "certificate_count": len(parsed),
        }

    quotient_classes = []
    for n, (key, members) in enumerate(sorted(quotient.items(), key=lambda x: x[0]), start=1):
        targets, requires, certificate_class = key
        quotient_classes.append({
            "quotient_id": f"Q{n:02d}",
            "member_certificate_ids": sorted(members),
            "target_predicates": list(targets),
            "requires": list(requires),
            "certificate_class": certificate_class,
        })

    best = None
    n = len(parsed)
    for size in range(n + 1):
        for combo in combinations(range(n), size):
            covered: set[str] = set()
            cost = 0.0
            chosen = []
            for idx in combo:
                cert = parsed[idx]
                covered.update(cert["targets"])
                cost += cert["cost"]
                chosen.append(cert["id"])
            chosen_t = tuple(sorted(chosen))
            key = (-len(covered), cost, len(chosen_t), chosen_t)
            if best is None or key < best[0]:
                best = (key, chosen_t, covered, cost)

    assert best is not None
    covered = set(best[2])
    uncovered = unresolved_set - covered

    return {
        "schema": SCHEMA,
        "status": "EXACT_TERMINAL_CERTIFICATE_CUT_COMPUTED",
        "errors": [],
        "unresolved_predicate_count": len(unresolved_set),
        "certificate_candidate_count": len(parsed),
        "quotient_class_count": len(quotient_classes),
        "quotient_classes": quotient_classes,
        "selected_certificates": list(best[1]),
        "selected_certificate_count": len(best[1]),
        "selected_new_reality_units": best[3],
        "covered_predicates": sorted(covered),
        "covered_predicate_count": len(covered),
        "uncovered_predicates": sorted(uncovered),
        "rule": (
            "SCHEDULE_MISSING_VERIFIED_TRUTHS_NOT_PROCEDURES__"
            "MERGE_ONLY_EXACTLY_SHARED_CERTIFICATE_OBLIGATIONS__"
            "MAXIMIZE_FRONTIER_COVERAGE_THEN_MINIMIZE_REALITY_THEN_CERTIFICATE_COUNT"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
