import pytest

from canonical.runtime.finance_sec_fact_selector_v1 import (
    FinanceFactSelectionError,
    select_fact,
)


def doc(rows):
    q = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
    facts = []
    for i, row in enumerate(rows):
        subject = f"XBRL_FACT:{q}:{i}"
        for key, value in row.items():
            facts.append({
                "subject": subject,
                "predicate": key,
                "object": value,
                "source": {"path": "raw.json", "artifact": "a" * 64, "uri": "https://data.sec.gov/example"},
            })
    return {
        "schema": "PROJECT_BRAIN_SEC_COMPANYCONCEPT_SOURCE_NATIVE_SEMANTICS_V1",
        "source_native_identity_extracted": True,
        "concept_qname": q,
        "source_sha256": "a" * 64,
        "source_url": "https://data.sec.gov/example",
        "semantic_contract": {"facts": facts, "entities": [], "relations": [], "templates": [], "ambiguities": []},
    }


def duration_row(value, *, filed, accn, fy=2025, start="2025-01-01", end="2025-12-31", form="10-K", unit="USD"):
    return {
        "val": value,
        "unit": unit,
        "start": start,
        "end": end,
        "filed": filed,
        "accn": accn,
        "fy": fy,
        "fp": "FY",
        "form": form,
    }


def test_latest_filing_selects_restated_historical_value():
    source = doc([
        duration_row(100, filed="2026-02-01", accn="old"),
        duration_row(105, filed="2027-02-01", accn="restated"),
    ])
    out = select_fact(
        source,
        fiscal_year=2025,
        forms=["10-K"],
        unit="USD",
        period_kind="duration",
    )
    assert out["value"] == 105
    assert out["latest_filed"] == "2027-02-01"
    assert out["pre_latest_filing_row_count"] == 2


def test_duplicate_latest_rows_are_allowed_only_if_value_equal():
    source = doc([
        duration_row(105, filed="2027-02-01", accn="a"),
        duration_row(105, filed="2027-02-01", accn="b"),
    ])
    out = select_fact(source, fiscal_year=2025, period_kind="duration")
    assert out["value"] == 105
    assert out["surviving_row_count"] == 2
    assert out["all_surviving_values_equal"] is True


def test_conflicting_latest_rows_fail_closed():
    source = doc([
        duration_row(105, filed="2027-02-01", accn="a"),
        duration_row(106, filed="2027-02-01", accn="b"),
    ])
    with pytest.raises(FinanceFactSelectionError, match="CONFLICTING_SURVIVING_VALUES"):
        select_fact(source, fiscal_year=2025, period_kind="duration")


def test_period_end_and_form_filters_are_load_bearing():
    source = doc([
        duration_row(100, filed="2026-02-01", accn="annual", form="10-K"),
        duration_row(
            25,
            filed="2025-11-01",
            accn="quarter",
            start="2025-07-01",
            end="2025-09-30",
            form="10-Q",
        ),
    ])
    out = select_fact(
        source,
        period_end="2025-09-30",
        forms=["10-Q"],
        period_kind="duration",
    )
    assert out["value"] == 25
    assert out["selected_fact"]["accn"] == "quarter"


def test_missing_match_fails_closed():
    source = doc([duration_row(100, filed="2026-02-01", accn="annual")])
    with pytest.raises(FinanceFactSelectionError, match="NO_FACT_MATCH"):
        select_fact(source, fiscal_year=2024)


def test_source_verification_is_not_self_certified():
    source = doc([duration_row(100, filed="2026-02-01", accn="annual")])
    out = select_fact(source, fiscal_year=2025)
    assert out["source_independent_verification_required"] is True
    assert out["semantic_truth_beyond_bound_xbrl_concept_claimed"] is False
    assert out["terminal_authority"] is False
