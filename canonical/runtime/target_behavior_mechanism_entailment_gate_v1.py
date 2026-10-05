"""Fail-closed gate separating target behavior from implementation mechanisms.

A behavioral-contract registry edge may nominate a useful implementation route, but it
cannot become a mandatory Opus-5.5 acceptance obligation from incidence alone. The
canonical target is useful behavior, not internal implementation.

This gate grants zero acceptance/capability/family/ownership credit.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TARGET_BEHAVIOR_MECHANISM_ENTAILMENT_GATE_V1"
TARGET_RULE = "USEFUL_BEHAVIOR_NOT_INTERNAL_IMPLEMENTATION"
ADMISSIBLE_ENTAILMENT = {
    "EXPLICIT_TARGET_BEHAVIOR",
    "LOGICALLY_NECESSARY_OBSERVABLE_CONSEQUENCE",
}

def _zero() -> dict[str, Any]:
    return {
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "incremental_spend_usd": 0,
    }

def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(doc, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["DOC_NOT_MAPPING"], **_zero()}
    if doc.get("target_rule") != TARGET_RULE:
        errors.append("TARGET_RULE_MISMATCH")
    obligations = doc.get("obligations")
    if not isinstance(obligations, list):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": sorted(set(errors + ["OBLIGATIONS_NOT_LIST"])), **_zero()}

    rows = []
    seen: set[tuple[str, str]] = set()
    for i, row in enumerate(obligations):
        if not isinstance(row, Mapping):
            errors.append(f"MALFORMED_OBLIGATION:{i}")
            continue
        family = row.get("family")
        behavior_id = row.get("behavior_id")
        if not isinstance(family, str) or not family:
            errors.append(f"FAMILY_MISSING:{i}")
            continue
        if not isinstance(behavior_id, str) or not behavior_id:
            errors.append(f"BEHAVIOR_ID_MISSING:{i}")
            continue
        key = (family, behavior_id)
        if key in seen:
            errors.append("DUPLICATE_EDGE:" + family + "::" + behavior_id)
            continue
        seen.add(key)

        mandatory = row.get("mandatory_acceptance_obligation") is True
        relation = row.get("target_entailment_relation")
        receipt = row.get("target_entailment_receipt")
        registry_only = row.get("registry_incidence_only") is True
        contract_kind = row.get("contract_kind")

        edge_errors: list[str] = []
        if mandatory:
            if relation not in ADMISSIBLE_ENTAILMENT:
                edge_errors.append("MANDATORY_WITHOUT_TARGET_ENTAILMENT")
            if not isinstance(receipt, str) or not receipt.strip():
                edge_errors.append("MANDATORY_WITHOUT_ENTAILMENT_RECEIPT")
            if registry_only:
                edge_errors.append("REGISTRY_INCIDENCE_CANNOT_CREATE_MANDATORY_OBLIGATION")
        if contract_kind == "IMPLEMENTATION_MECHANISM" and mandatory and relation not in ADMISSIBLE_ENTAILMENT:
            edge_errors.append("IMPLEMENTATION_MECHANISM_NOT_PROVED_NECESSARY")
        if relation in {"OUT_OF_SCOPE", "SUFFICIENT_MECHANISM_ONLY", "ADJACENT_NOT_ENTAILED"} and mandatory:
            edge_errors.append("NON_ENTAILED_EDGE_MARKED_MANDATORY")

        if edge_errors:
            errors.extend(f"{family}::{behavior_id}::{e}" for e in edge_errors)
        rows.append({
            "family": family,
            "behavior_id": behavior_id,
            "mandatory": mandatory,
            "target_entailment_relation": relation,
            "admissible_as_mandatory": mandatory and not edge_errors,
        })

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "edge_count": len(rows),
        "mandatory_admissible_count": sum(1 for r in rows if r["admissible_as_mandatory"]),
        "rows": rows,
        "rule": "REGISTRY_INCIDENCE_OR_USEFUL_MECHANISM_IS_NOT_A_NECESSARY_TARGET_OBLIGATION_WITHOUT_EXPLICIT_TARGET_ENTAILMENT",
        **_zero(),
    }
