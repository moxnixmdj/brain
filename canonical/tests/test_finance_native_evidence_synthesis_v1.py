from decimal import Decimal

import pytest

from canonical.runtime.finance_native_evidence_synthesis_v1 import (
    FinanceEvidenceSynthesisError,
    extract_metric_series,
    format_revenue_growth,
    synthesize_revenue_growth,
)


def test_explicit_same_line_revenue_bindings():
    evidence = """
Revenue for FY2023 was $2,241.236 million.
Revenue for FY2025 was $3,953.624 million.
"""
    out = extract_metric_series(evidence, "REVENUE")
    assert out["status"] == "BOUND"
    assert out["series"] == {
        "2023": "2241.236",
        "2025": "3953.624",
    }


def test_exact_table_header_row_binding():
    evidence = """
2025 2024 2023
Revenue 3,953.624 3,055.555 2,241.236
Gross margin 75% 74% 73%
"""
    out = extract_metric_series(evidence, "REVENUE")
    assert out["series"]["2025"] == "3953.624"
    assert out["series"]["2023"] == "2241.236"


def test_conflicting_values_fail_closed():
    evidence = """
Revenue for FY2025 was $100 million.
Revenue for FY2025 was $101 million.
"""
    with pytest.raises(
        FinanceEvidenceSynthesisError, match="CONFLICTING_METRIC_VALUE"
    ):
        extract_metric_series(evidence, "REVENUE")


def test_two_company_cagr_and_basis_point_comparison():
    q = (
        "For NASDAQ:CRWD and NASDAQ:PANW, which company achieved the higher "
        "2-year revenue CAGR, and by how many basis points from FY 2023 to FY 2025?"
    )
    out = synthesize_revenue_growth(
        q,
        {
            "CRWD": (
                "Revenue for FY2023 was $2241.236 million.\n"
                "Revenue for FY2025 was $3953.624 million."
            ),
            "PANW": (
                "Revenue for FY2023 was $6892.7 million.\n"
                "Revenue for FY2025 was $9221.5 million."
            ),
        },
    )
    assert out["status"] == "PASS__BOUND_REVENUE_GROWTH"
    assert out["all_entities_bound"] is True
    assert out["results"]["CRWD"]["display_percent"] == "32.82%"
    assert out["results"]["PANW"]["display_percent"] == "15.67%"
    assert out["basis_point_comparison"]["higher"] == "CRWD"
    assert out["basis_point_comparison"]["display_bps"] == "1715"
    text = format_revenue_growth(out)
    assert "CRWD has the higher revenue CAGR by 1715 basis points." in text


def test_one_year_revenue_growth_without_cagr_keyword():
    q = "Compare FY2024 to FY2025 revenue growth for NASDAQ:AAA and NYSE:BBB."
    out = synthesize_revenue_growth(
        q,
        {
            "AAA": "FY2024 revenue was 100. FY2025 revenue was 125.",
            "BBB": "FY2024 revenue was 200. FY2025 revenue was 220.",
        },
    )
    assert out["method"] == "PERCENT_CHANGE"
    assert out["results"]["AAA"]["display_percent"] == "25.00%"
    assert out["results"]["BBB"]["display_percent"] == "10.00%"
    assert out["ranking_high_to_low"] == ["AAA", "BBB"]


def test_missing_one_company_fact_does_not_claim_all_bound():
    q = "Compare revenue CAGR from FY2023 to FY2025 for NASDAQ:AAA and NYSE:BBB."
    out = synthesize_revenue_growth(
        q,
        {
            "AAA": "FY2023 revenue was 100. FY2025 revenue was 121.",
            "BBB": "FY2025 revenue was 300.",
        },
    )
    assert out["status"] == "PASS__BOUND_REVENUE_GROWTH"
    assert out["all_entities_bound"] is False
    assert set(out["results"]) == {"AAA"}


def test_non_revenue_metric_is_not_invented():
    with pytest.raises(
        FinanceEvidenceSynthesisError, match="METRIC_NOT_SUPPORTED"
    ):
        extract_metric_series("FY2025 EBITDA was 100.", "EBITDA")
