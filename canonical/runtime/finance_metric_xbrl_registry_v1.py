#!/usr/bin/env python3
"""Bounded model-free finance metric -> SEC XBRL concept registry.

The registry maps only explicit finance metric aliases to finite standard
taxonomy candidate sets. It does not infer issuer-specific extension meaning,
choose among multiple surviving concepts, or claim a source fact is correct.

A downstream source-native SEC capability must fetch candidate concepts and a
separate selector must prove a unique period-bound fact before arithmetic use.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_FINANCE_METRIC_XBRL_REGISTRY_V1"


@dataclass(frozen=True)
class MetricSpec:
    metric_id: str
    aliases: tuple[str, ...]
    concepts: tuple[tuple[str, str], ...]
    period_kind: str
    preferred_units: tuple[str, ...]
    semantic_scope: str


_SPECS: tuple[MetricSpec, ...] = (
    MetricSpec(
        "REVENUE",
        (r"\brevenue\b", r"\bnet sales\b", r"\btotal revenues?\b"),
        (
            ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
            ("us-gaap", "Revenues"),
            ("us-gaap", "SalesRevenueNet"),
        ),
        "duration", ("USD",),
        "TOP_LINE_REVENUE_OR_NET_SALES_EXPLICITLY_NAMED",
    ),
    MetricSpec(
        "NET_INCOME",
        (r"\bnet income\b", r"\bnet earnings\b"),
        (("us-gaap", "NetIncomeLoss"),),
        "duration", ("USD",),
        "CONSOLIDATED_NET_INCOME_OR_LOSS_EXPLICITLY_NAMED",
    ),
    MetricSpec(
        "OPERATING_INCOME",
        (r"\boperating income\b", r"\bincome from operations\b"),
        (("us-gaap", "OperatingIncomeLoss"),),
        "duration", ("USD",),
        "OPERATING_INCOME_OR_LOSS_EXPLICITLY_NAMED",
    ),
    MetricSpec(
        "D_AND_A",
        (
            r"\bD&A\b",
            r"depreciation (?:and|&) amortization",
            r"depreciation & amortization",
        ),
        (
            ("us-gaap", "DepreciationDepletionAndAmortization"),
            ("us-gaap", "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment"),
            ("us-gaap", "Depreciation"),
        ),
        "duration", ("USD",),
        "DEPRECIATION_AND_AMORTIZATION_EXPLICITLY_NAMED__CANDIDATE_SET_ONLY",
    ),
    MetricSpec(
        "INVENTORY",
        (r"\binventor(?:y|ies)\b", r"merchandise inventories"),
        (
            ("us-gaap", "InventoryNet"),
            ("us-gaap", "InventoryNetOfAllowancesCustomerAdvancesAndProgressBillings"),
        ),
        "instant", ("USD",),
        "CONSOLIDATED_INVENTORY_BALANCE_EXPLICITLY_NAMED",
    ),
    MetricSpec(
        "COST_OF_SALES",
        (
            r"\bcost of sales\b",
            r"\bcost of revenue\b",
            r"\bcost of goods sold\b",
        ),
        (
            ("us-gaap", "CostOfRevenue"),
            ("us-gaap", "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization"),
            ("us-gaap", "CostOfGoodsSold"),
        ),
        "duration", ("USD",),
        "COST_OF_SALES_OR_REVENUE_EXPLICITLY_NAMED__CANDIDATE_SET_ONLY",
    ),
    MetricSpec(
        "STOCKHOLDERS_EQUITY",
        (
            r"stockholders'? equity",
            r"shareholders'? equity",
            r"\bbook equity\b",
            r"\bbook value\b",
        ),
        (
            ("us-gaap", "StockholdersEquity"),
            ("us-gaap", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
        ),
        "instant", ("USD",),
        "BOOK_EQUITY_EXPLICITLY_NAMED__NCI_SCOPE_MUST_BE_DISAMBIGUATED",
    ),
    MetricSpec(
        "CASH_AND_EQUIVALENTS",
        (
            r"cash and cash equivalents",
            r"cash, cash equivalents",
            r"\bcash balance\b",
        ),
        (
            ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
            ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
        ),
        "instant", ("USD",),
        "CASH_BALANCE_EXPLICITLY_NAMED__RESTRICTED_CASH_SCOPE_MUST_BE_DISAMBIGUATED",
    ),
    MetricSpec(
        "LONG_TERM_DEBT",
        (r"\blong[- ]term debt\b",),
        (
            ("us-gaap", "LongTermDebtCurrent"),
            ("us-gaap", "LongTermDebtNoncurrent"),
            ("us-gaap", "LongTermDebtAndFinanceLeaseObligationsCurrent"),
            ("us-gaap", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"),
        ),
        "instant", ("USD",),
        "LONG_TERM_DEBT_COMPONENTS_EXPLICITLY_NAMED__AGGREGATION_REQUIRED",
    ),
    MetricSpec(
        "INTEREST_EXPENSE",
        (r"\binterest expense\b",),
        (
            ("us-gaap", "InterestExpenseNonOperating"),
            ("us-gaap", "InterestAndDebtExpense"),
        ),
        "duration", ("USD",),
        "INTEREST_EXPENSE_EXPLICITLY_NAMED",
    ),
    MetricSpec(
        "OPERATING_LEASE_COST",
        (
            r"operating lease cost",
            r"fixed operating lease cost",
            r"\brent expense\b",
        ),
        (
            ("us-gaap", "OperatingLeaseCost"),
            ("us-gaap", "OperatingLeaseExpense"),
        ),
        "duration", ("USD",),
        "OPERATING_LEASE_COST_EXPLICITLY_NAMED__VARIABLE_AND_SHORT_TERM_SCOPE_NOT_INFERRED",
    ),
    MetricSpec(
        "SG_AND_A",
        (
            r"\bSG&A\b",
            r"selling,? general and administrative",
            r"selling general and administrative",
        ),
        (("us-gaap", "SellingGeneralAndAdministrativeExpense"),),
        "duration", ("USD",),
        "SGA_EXPENSE_EXPLICITLY_NAMED",
    ),
    MetricSpec(
        "SHARE_BASED_COMP",
        (
            r"stock[- ]based compensation",
            r"share[- ]based compensation",
            r"equity award compensation",
            r"\bSBC\b",
        ),
        (("us-gaap", "ShareBasedCompensation"),),
        "duration", ("USD",),
        "SHARE_BASED_COMPENSATION_EXPLICITLY_NAMED",
    ),
    MetricSpec(
        "CAPEX",
        (
            r"\bcapex\b",
            r"capital expenditures?",
            r"capital expenditure",
        ),
        (
            ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
            ("us-gaap", "PaymentsToAcquireProductiveAssets"),
        ),
        "duration", ("USD",),
        "CAPITAL_EXPENDITURE_EXPLICITLY_NAMED__CANDIDATE_SET_ONLY",
    ),
    MetricSpec(
        "GOODWILL",
        (r"\bgoodwill\b",),
        (("us-gaap", "Goodwill"),),
        "instant", ("USD",),
        "GOODWILL_BALANCE_EXPLICITLY_NAMED",
    ),
    MetricSpec(
        "INTANGIBLE_ASSETS_NET",
        (
            r"identifiable intangible assets,? net",
            r"intangible assets,? net",
        ),
        (
            ("us-gaap", "FiniteLivedIntangibleAssetsNet"),
            ("us-gaap", "IndefiniteLivedIntangibleAssetsExcludingGoodwill"),
        ),
        "instant", ("USD",),
        "INTANGIBLE_ASSET_SCOPE_REQUIRES_EXPLICIT_COMPONENT_AGGREGATION",
    ),
    MetricSpec(
        "WEIGHTED_AVERAGE_SHARES_BASIC",
        (
            r"basic weighted[- ]average shares",
            r"weighted[- ]average shares outstanding.*basic",
        ),
        (("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"),),
        "duration", ("shares",),
        "BASIC_WEIGHTED_AVERAGE_SHARES_EXPLICITLY_NAMED",
    ),
    MetricSpec(
        "SHARES_OUTSTANDING",
        (r"\bshares outstanding\b",),
        (("dei", "EntityCommonStockSharesOutstanding"),),
        "instant", ("shares",),
        "COVER_PAGE_COMMON_SHARES_OUTSTANDING_EXPLICITLY_NAMED",
    ),
)


def _normalize(text: str) -> str:
    return " ".join(text.split())


def resolve_metric_aliases(text: str) -> list[dict[str, object]]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("TEXT_REQUIRED")
    q = _normalize(text)
    out: list[dict[str, object]] = []
    for spec in _SPECS:
        matched = sorted({
            pattern for pattern in spec.aliases
            if re.search(pattern, q, flags=re.I | re.S) is not None
        })
        if not matched:
            continue
        out.append({
            "metric_id": spec.metric_id,
            "matched_alias_patterns": matched,
            "candidate_concepts": [
                {"taxonomy": taxonomy, "tag": tag}
                for taxonomy, tag in spec.concepts
            ],
            "period_kind": spec.period_kind,
            "preferred_units": list(spec.preferred_units),
            "semantic_scope": spec.semantic_scope,
            "unique_concept_selected": len(spec.concepts) == 1,
            "issuer_extension_required_if_no_standard_fact": True,
        })
    return out


def metric_spec(metric_id: str) -> MetricSpec:
    for spec in _SPECS:
        if spec.metric_id == metric_id:
            return spec
    raise KeyError(metric_id)


def registered_metric_ids() -> tuple[str, ...]:
    return tuple(spec.metric_id for spec in _SPECS)


__all__ = [
    "MetricSpec",
    "SCHEMA",
    "metric_spec",
    "registered_metric_ids",
    "resolve_metric_aliases",
]
