from canonical.runtime.finance_metric_xbrl_registry_v1 import (
    registered_metric_ids,
    resolve_metric_aliases,
)


def by_id(text: str) -> dict[str, dict]:
    return {x["metric_id"]: x for x in resolve_metric_aliases(text)}


def test_common_income_statement_metrics_map_to_bounded_candidates():
    out = by_id("Use revenue, operating income, net income, D&A and SG&A.")
    assert {
        "REVENUE", "OPERATING_INCOME", "NET_INCOME", "D_AND_A", "SG_AND_A"
    } <= set(out)
    assert out["NET_INCOME"]["unique_concept_selected"] is True
    assert out["REVENUE"]["unique_concept_selected"] is False


def test_balance_sheet_and_comps_metrics_map():
    out = by_id(
        "Use inventory, stockholders' equity, cash and cash equivalents, "
        "long-term debt and goodwill."
    )
    assert {
        "INVENTORY",
        "STOCKHOLDERS_EQUITY",
        "CASH_AND_EQUIVALENTS",
        "LONG_TERM_DEBT",
        "GOODWILL",
    } <= set(out)


def test_capex_lease_interest_and_share_metrics_map():
    out = by_id(
        "Use capex, fixed operating lease cost, interest expense, "
        "basic weighted-average shares and shares outstanding."
    )
    assert {
        "CAPEX",
        "OPERATING_LEASE_COST",
        "INTEREST_EXPENSE",
        "WEIGHTED_AVERAGE_SHARES_BASIC",
        "SHARES_OUTSTANDING",
    } <= set(out)


def test_registry_never_claims_issuer_extension_semantics():
    for metric in resolve_metric_aliases("revenue cash debt capex goodwill"):
        assert metric["issuer_extension_required_if_no_standard_fact"] is True


def test_registry_has_stable_unique_metric_ids():
    ids = registered_metric_ids()
    assert len(ids) == len(set(ids))
    assert len(ids) >= 15
