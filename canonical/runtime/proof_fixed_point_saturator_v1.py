"""Monotone fixed-point proof saturator for atomic acceptance predicates.

Consumes a compiled acceptance IR plus independently verified deduction rules.
A deduction may add proved predicates only when all declared prerequisite
predicates are already proved and the rule is independently verified,
contamination-clean, scope-complete, and receipt-bound.

No deduction is allowed to remove obligations or weaken a frozen protocol.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROOF_FIXED_POINT_SATURATOR_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "proved_predicates": [],
        "newly_proved_predicates": [],
        "unresolved_predicates": [],
        "iterations": 0,
        "trace": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def evaluate(ir: Mapping[str, Any], deductions: list[Mapping[str, Any]]) -> dict[str, Any]:
    predicates = ir.get("predicates")
    families = ir.get("families")
    if ir.get("status") not in {"PASS", "PASS_WITH_UNCOVERED_ACTION_TARGETS"}:
        return _fail("IR_NOT_PASS")
    if not isinstance(predicates, list) or not isinstance(families, list):
        return _fail("IR_SHAPE_INVALID")
    if not isinstance(deductions, list):
        return _fail("DEDUCTIONS_NOT_LIST")

    known: set[str] = set()
    initial_proved: set[str] = set()
    for row in predicates:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            return _fail("IR_PREDICATE_INVALID")
        pid = row["id"]
        if pid in known:
            return _fail(f"DUPLICATE_IR_PREDICATE:{pid}")
        known.add(pid)
        if row.get("state") == "PROVED":
            initial_proved.add(pid)

    parsed = []
    seen_ids: set[str] = set()
    for i, rule in enumerate(deductions):
        if not isinstance(rule, Mapping):
            return _fail(f"DEDUCTION_{i}_INVALID")
        rid = rule.get("id")
        requires = rule.get("requires", [])
        proves = rule.get("proves", [])
        receipt = rule.get("receipt")
        if not isinstance(rid, str) or not rid or rid in seen_ids:
            return _fail("DEDUCTION_ID_INVALID_OR_DUPLICATE")
        seen_ids.add(rid)
        if not isinstance(requires, list) or not isinstance(proves, list):
            return _fail(f"DEDUCTION_SHAPE_INVALID:{rid}")
        if any(x not in known for x in requires + proves):
            return _fail(f"DEDUCTION_UNKNOWN_PREDICATE:{rid}")
        if not proves:
            return _fail(f"DEDUCTION_PROVES_EMPTY:{rid}")
        for flag in ("verified", "independent", "contamination_clean", "scope_complete"):
            if rule.get(flag) is not True:
                return _fail(f"DEDUCTION_{flag.upper()}_REQUIRED:{rid}")
        if not isinstance(receipt, str) or not receipt:
            return _fail(f"DEDUCTION_RECEIPT_REQUIRED:{rid}")
        parsed.append({
            "id": rid,
            "requires": set(requires),
            "proves": set(proves),
            "receipt": receipt,
        })

    proved = set(initial_proved)
    trace = []
    fired: set[str] = set()
    iteration = 0
    while True:
        iteration += 1
        additions: list[tuple[dict[str, Any], list[str]]] = []
        for rule in parsed:
            if rule["id"] in fired:
                continue
            if rule["requires"] <= proved:
                new = sorted(rule["proves"] - proved)
                if new:
                    additions.append((rule, new))
                else:
                    fired.add(rule["id"])
        if not additions:
            iteration -= 1
            break
        for rule, new in sorted(additions, key=lambda x: x[0]["id"]):
            proved.update(new)
            fired.add(rule["id"])
            trace.append({
                "iteration": iteration,
                "deduction_id": rule["id"],
                "requires": sorted(rule["requires"]),
                "newly_proved": new,
                "receipt": rule["receipt"],
            })

    family_out = []
    for family in families:
        if not isinstance(family, Mapping):
            return _fail("IR_FAMILY_INVALID")
        required = family.get("required_predicates")
        if not isinstance(required, list) or any(x not in known for x in required):
            return _fail("IR_FAMILY_REQUIREMENTS_INVALID")
        missing = sorted(set(required) - proved)
        family_out.append({
            "family": family.get("family"),
            "required_predicates": sorted(required),
            "unresolved_predicates": missing,
            "acceptance_closed_by_atomic_registry": not missing,
        })

    newly = sorted(proved - initial_proved)
    return {
        "schema": SCHEMA,
        "status": "FIXED_POINT_REACHED",
        "errors": [],
        "initial_proved_predicates": sorted(initial_proved),
        "proved_predicates": sorted(proved),
        "newly_proved_predicates": newly,
        "unresolved_predicates": sorted(known - proved),
        "iterations": iteration,
        "trace": trace,
        "families": family_out,
        "closed_residual_family_count": sum(
            row["acceptance_closed_by_atomic_registry"] for row in family_out
        ),
        "rule": (
            "MONOTONE_PROOF_ADDITION_ONLY__EVERY_DERIVATION_MUST_BE_INDEPENDENT_"
            "CONTAMINATION_CLEAN_SCOPE_COMPLETE_AND_RECEIPT_BOUND"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
