#!/usr/bin/env python3
"""Formula-implied dependency compiler for donor-free finance workflows.

Takes the explicit operation/metric contract and adds only dependencies forced
by the formula definition. It distinguishes standard SEC facts, market prices,
question literals, and semantic/custom-source obligations.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_QUANTITATIVE_DEPENDENCY_V1"

# Dependency kinds:
# SEC_STANDARD_METRIC: bounded metric registry can propose standard concepts.
# MARKET_PRICE: official price-history source required.
# QUESTION_LITERAL: must be explicitly present/bound from question text.
# DERIVED: another deterministic formula result.
# SEMANTIC_SOURCE: raw/custom/prose interpretation remains required.
_OPERATION_DEPS: dict[str, tuple[tuple[str, str], ...]] = {
    "CAGR": (
        ("CAGR_BASE_METRIC", "DERIVED"),
        ("START_VALUE", "DERIVED"),
        ("END_VALUE", "DERIVED"),
        ("PERIOD_COUNT", "QUESTION_LITERAL"),
    ),
    "BASIS_POINT_DELTA": (
        ("LEFT_PERCENT", "DERIVED"),
        ("RIGHT_PERCENT", "DERIVED"),
    ),
    "PERCENT_CHANGE": (
        ("NEW_VALUE", "DERIVED"),
        ("OLD_VALUE", "DERIVED"),
    ),
    "SHARE_PRICE_RETURN": (
        ("START_PRICE", "MARKET_PRICE"),
        ("END_PRICE", "MARKET_PRICE"),
    ),
    "MARKET_SENTIMENT_FROM_RETURN": (
        ("RETURN_PERCENT", "DERIVED"),
    ),
    "RANK_COMPARISON": (
        ("RANKED_METRICS", "DERIVED"),
    ),
    "AVERAGE": (
        ("AVERAGE_INPUTS", "DERIVED"),
    ),
    "DAYS_INVENTORY_OUTSTANDING": (
        ("INVENTORY", "SEC_STANDARD_METRIC"),
        ("COST_OF_SALES", "SEC_STANDARD_METRIC"),
        ("FISCAL_PERIOD_DAYS", "DERIVED"),
    ),
    "ADJUSTED_EBITDAR": (
        ("EBITDA", "DERIVED"),
        ("RENT_OR_OPERATING_LEASE_COST", "SEC_STANDARD_METRIC"),
    ),
    "ADJUSTED_EBITDA": (
        ("OPERATING_INCOME", "SEC_STANDARD_METRIC"),
        ("D_AND_A", "SEC_STANDARD_METRIC"),
        ("ADJUSTMENT_SET", "SEMANTIC_SOURCE"),
    ),
    "EBITDA_MARGIN": (
        ("EBITDA", "DERIVED"),
        ("REVENUE", "SEC_STANDARD_METRIC"),
    ),
    "PRICE_TO_BOOK": (
        ("MARKET_PRICE", "MARKET_PRICE"),
        ("SHARES_OUTSTANDING", "SEC_STANDARD_METRIC"),
        ("STOCKHOLDERS_EQUITY", "SEC_STANDARD_METRIC"),
    ),
    "DEBT_TO_EQUITY": (
        ("TOTAL_DEBT", "SEC_STANDARD_METRIC"),
        ("STOCKHOLDERS_EQUITY", "SEC_STANDARD_METRIC"),
    ),
    "DEBT_TO_TOTAL_CAPITAL": (
        ("TOTAL_DEBT", "SEC_STANDARD_METRIC"),
        ("STOCKHOLDERS_EQUITY", "SEC_STANDARD_METRIC"),
    ),
    "FIXED_CHARGE_COVERAGE": (
        ("EBITDAR", "DERIVED"),
        ("INTEREST_EXPENSE", "SEC_STANDARD_METRIC"),
        ("OPERATING_LEASE_COST", "SEC_STANDARD_METRIC"),
    ),
    "ENTERPRISE_VALUE": (
        ("MARKET_PRICE", "MARKET_PRICE"),
        ("SHARES_OUTSTANDING", "SEC_STANDARD_METRIC"),
        ("TOTAL_DEBT", "SEC_STANDARD_METRIC"),
        ("CASH_AND_EQUIVALENTS", "SEC_STANDARD_METRIC"),
        ("PREFERRED_STOCK_IF_MATERIAL", "SEMANTIC_SOURCE"),
        ("NONCONTROLLING_INTEREST_IF_MATERIAL", "SEMANTIC_SOURCE"),
    ),
    "EV_TO_EBITDA": (
        ("ENTERPRISE_VALUE", "DERIVED"),
        ("EBITDA", "DERIVED"),
    ),
    "EV_TO_REVENUE": (
        ("ENTERPRISE_VALUE", "DERIVED"),
        ("REVENUE", "SEC_STANDARD_METRIC"),
    ),
    "TRANSACTION_PREMIUM": (
        ("OFFER_OR_TRANSACTION_PRICE", "SEMANTIC_SOURCE"),
        ("UNAFFECTED_MARKET_PRICE", "MARKET_PRICE"),
    ),
    "GUIDANCE_MIDPOINT": (
        ("GUIDANCE_LOW", "SEMANTIC_SOURCE"),
        ("GUIDANCE_HIGH", "SEMANTIC_SOURCE"),
    ),
    "BEAT_MISS_PERCENT": (
        ("ACTUAL_VALUE", "DERIVED"),
        ("GUIDANCE_REFERENCE", "DERIVED"),
    ),
    "GUIDANCE_CONSERVATISM_DOMINANCE": (
        ("BEAT_MISS_SERIES", "DERIVED"),
    ),
    "INTENSITY": (
        ("INTENSITY_NUMERATOR", "DERIVED"),
        ("REVENUE", "SEC_STANDARD_METRIC"),
    ),
    "RECONCILIATION": (
        ("RECONCILIATION_COMPONENTS", "SEMANTIC_SOURCE"),
    ),
    "ADDBACKS": (
        ("ADDBACK_COMPONENTS", "SEMANTIC_SOURCE"),
    ),
    "NORMALIZATION": (
        ("NORMALIZATION_POLICY", "SEMANTIC_SOURCE"),
        ("NORMALIZATION_INPUTS", "DERIVED"),
    ),
    "MARGIN_CHANGE": (
        ("MARGIN_INPUTS", "DERIVED"),
    ),
    "DISCLOSURE_DELTA": (
        ("CROSS_FILING_DISCLOSURE_BINDING", "SEMANTIC_SOURCE"),
    ),
    "DCF": (
        ("PROJECTED_FREE_CASH_FLOWS", "DERIVED"),
        ("DISCOUNT_RATE", "QUESTION_LITERAL"),
        ("TERMINAL_VALUE", "DERIVED"),
    ),
    "EXIT_MULTIPLE_TERMINAL_VALUE": (
        ("TERMINAL_EBITDA", "DERIVED"),
        ("EXIT_MULTIPLE", "QUESTION_LITERAL"),
    ),
    "PERPETUAL_GROWTH_TERMINAL_VALUE": (
        ("NEXT_PERIOD_FCF", "DERIVED"),
        ("DISCOUNT_RATE", "QUESTION_LITERAL"),
        ("TERMINAL_GROWTH_RATE", "QUESTION_LITERAL"),
    ),
    "LBO": (
        ("ENTRY_EQUITY_VALUE", "DERIVED"),
        ("ENTRY_DEBT", "DERIVED"),
        ("PROJECTION_ASSUMPTIONS", "QUESTION_LITERAL"),
        ("FREE_CASH_FLOW_SERIES", "DERIVED"),
        ("EXIT_EQUITY_VALUE", "DERIVED"),
    ),
    "MOIC": (
        ("EXIT_EQUITY_VALUE", "DERIVED"),
        ("INITIAL_SPONSOR_EQUITY", "DERIVED"),
    ),
    "IRR": (
        ("EXIT_EQUITY_VALUE", "DERIVED"),
        ("INITIAL_SPONSOR_EQUITY", "DERIVED"),
        ("HOLD_YEARS", "QUESTION_LITERAL"),
    ),
}


def compile_dependencies(question_contract: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(question_contract, Mapping):
        raise ValueError("QUESTION_CONTRACT_REQUIRED")
    operations = question_contract.get("operations")
    if not isinstance(operations, list):
        raise ValueError("OPERATIONS_REQUIRED")

    dependencies: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    unknown_operations: list[str] = []
    for raw_op in operations:
        op = str(raw_op)
        specs = _OPERATION_DEPS.get(op)
        if specs is None:
            unknown_operations.append(op)
            continue
        for name, kind in specs:
            key = (op, name, kind)
            if key in seen:
                continue
            seen.add(key)
            dependencies.append({
                "operation": op,
                "dependency": name,
                "kind": kind,
            })

    explicit_metric_ids = sorted({
        str(row.get("metric_id"))
        for row in question_contract.get("metric_requests", [])
        if isinstance(row, Mapping) and row.get("metric_id")
    })
    semantic = [d for d in dependencies if d["kind"] == "SEMANTIC_SOURCE"]
    source_native = [d for d in dependencies if d["kind"] == "SEC_STANDARD_METRIC"]
    market = [d for d in dependencies if d["kind"] == "MARKET_PRICE"]
    literals = [d for d in dependencies if d["kind"] == "QUESTION_LITERAL"]

    return {
        "schema": SCHEMA,
        "status": "COMPILED_FORMULA_IMPLIED_DEPENDENCIES",
        "question_sha256": question_contract.get("question_sha256"),
        "operations": list(operations),
        "explicit_metric_ids": explicit_metric_ids,
        "dependencies": dependencies,
        "sec_standard_dependency_count": len(source_native),
        "market_price_dependency_count": len(market),
        "question_literal_dependency_count": len(literals),
        "semantic_source_dependencies": semantic,
        "semantic_source_dependency_count": len(semantic),
        "unknown_operations": sorted(set(unknown_operations)),
        "mechanically_closed_candidate": not semantic and not unknown_operations,
        "source_fact_binding_proved": False,
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "benchmark_score_credit": 0,
        "terminal_authority": False,
    }


__all__ = ["SCHEMA", "compile_dependencies"]
