"""Fail-closed fixed-point coverage closure gate.

This does not pretend that a hand-written checklist is complete.  It requires a
sealed mission identity, an independently verified closure-operator-set receipt,
then computes the least fixed point of receipt-bound closure rules.  Acceptance
requires every obligation in that generated universe to carry an independent
coverage receipt.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_COVERAGE_CLOSURE_GATE_V1"


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _valid_sha(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def _receipt_ok(r: Any) -> bool:
    return isinstance(r, Mapping) and r.get("independently_verified") is True and _valid_sha(r.get("sha256"))


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": reason,
        "coverage_authority": False, "promotion_authority": False, "terminal_authority": False,
        "terminal_credit_delta": 0, "incremental_spend_usd": 0, **extra,
    }


def close_coverage(*, mission_scope_sha256: str, seeds: Iterable[str], rules: Iterable[Mapping[str, Any]],
                   operator_set_completeness_receipt: Mapping[str, Any],
                   coverage_receipts: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if not _valid_sha(mission_scope_sha256):
        return _fail("MISSION_SCOPE_SHA256_INVALID")
    if not _receipt_ok(operator_set_completeness_receipt):
        return _fail("CLOSURE_OPERATOR_SET_COMPLETENESS_UNPROVED")

    universe = {str(x) for x in seeds if isinstance(x, str) and x}
    if not universe:
        return _fail("SEEDS_EMPTY")

    compiled_rules = []
    ids = set()
    for row in rules:
        if not isinstance(row, Mapping) or not isinstance(row.get("rule_id"), str) or not row["rule_id"]:
            return _fail("RULE_INVALID")
        if row["rule_id"] in ids:
            return _fail("DUPLICATE_RULE_ID", rule_id=row["rule_id"])
        ids.add(row["rule_id"])
        when = row.get("when_all")
        add = row.get("add")
        if not isinstance(when, list) or not isinstance(add, list) or not add:
            return _fail("RULE_SHAPE_INVALID", rule_id=row["rule_id"])
        if not all(isinstance(x, str) and x for x in when + add):
            return _fail("RULE_TOKEN_INVALID", rule_id=row["rule_id"])
        if not _valid_sha(row.get("receipt_sha256")):
            return _fail("RULE_RECEIPT_INVALID", rule_id=row["rule_id"])
        compiled_rules.append((row["rule_id"], frozenset(when), frozenset(add), row["receipt_sha256"]))

    changed = True
    firings: list[dict[str, Any]] = []
    fired = set()
    while changed:
        changed = False
        for rule_id, when, add, receipt_sha in compiled_rules:
            if when <= universe:
                new = set(add) - universe
                if new:
                    universe |= new
                    changed = True
                    firings.append({"rule_id": rule_id, "added": sorted(new), "receipt_sha256": receipt_sha})
                fired.add(rule_id)

    missing = []
    receipt_digests = {}
    for obligation in sorted(universe):
        r = coverage_receipts.get(obligation)
        if not _receipt_ok(r) or r.get("obligation") not in (None, obligation):
            missing.append(obligation)
        else:
            receipt_digests[obligation] = r["sha256"]
    if missing:
        return _fail(
            "GENERATED_UNIVERSE_NOT_FULLY_COVERED",
            mission_scope_sha256=mission_scope_sha256,
            universe=sorted(universe), uncovered_obligations=missing,
            fixed_point_reached=True,
        )

    core = {
        "mission_scope_sha256": mission_scope_sha256,
        "operator_set_completeness_receipt_sha256": operator_set_completeness_receipt["sha256"],
        "universe": sorted(universe),
        "coverage_receipt_sha256": receipt_digests,
        "rule_firings": firings,
        "declared_rule_ids": sorted(ids),
        "fired_rule_ids": sorted(fired),
    }
    return {
        "schema": SCHEMA, "pass": True,
        "status": "PASS__GENERATIVE_SCOPE_FIXED_POINT_CLOSED__ALL_DERIVED_OBLIGATIONS_RECEIPT_COVERED",
        "reason": None, **core, "closure_receipt_sha256": _sha(core),
        "coverage_authority": True, "promotion_authority": False, "terminal_authority": False,
        "terminal_credit_delta": 0, "incremental_spend_usd": 0,
    }
