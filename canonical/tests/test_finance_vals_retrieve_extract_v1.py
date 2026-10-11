import json

from canonical.runtime.finance_vals_retrieve_extract_v1 import extract_evidence


def test_extracts_exact_requested_ticker_identity_from_sec_registry_json():
    registry = {
        "0": {"cik_str": 1352010, "ticker": "EPAM", "title": "EPAM Systems, Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
    }
    prompt = "Find ticker=EPAM in this SEC registry.\n" + json.dumps(registry)
    out = extract_evidence(prompt)
    assert "[SEC_TICKER_IDENTITY]" in out
    assert '"ticker": "EPAM"' in out
    assert '"cik_str": 1352010' in out
    assert "MSFT" not in out


def test_extracts_companyconcept_rows_filtered_to_requested_year_and_form():
    concept = {
        "cik": 1352010,
        "entityName": "EPAM Systems, Inc.",
        "taxonomy": "us-gaap",
        "tag": "Revenues",
        "label": "Revenue",
        "units": {
            "USD": [
                {
                    "start": "2024-01-01", "end": "2024-12-31",
                    "val": 4720000000, "accn": "a", "fy": 2024, "fp": "FY",
                    "form": "10-K", "filed": "2025-02-28", "frame": "CY2024",
                },
                {
                    "start": "2025-01-01", "end": "2025-12-31",
                    "val": 5457056000, "accn": "b", "fy": 2025, "fp": "FY",
                    "form": "10-K", "filed": "2026-02-27", "frame": "CY2025",
                },
                {
                    "start": "2025-01-01", "end": "2025-09-30",
                    "val": 4000000000, "accn": "c", "fy": 2025, "fp": "Q3",
                    "form": "10-Q", "filed": "2025-11-01",
                },
            ]
        },
    }
    prompt = "Extract 2025 10-K revenue.\n" + json.dumps(concept)
    out = extract_evidence(prompt)
    assert "[SEC_COMPANYCONCEPT]" in out
    assert '"val": 5457056000' in out
    assert '"val": 4720000000' not in out
    assert '"val": 4000000000' not in out


def test_generic_text_extraction_preserves_relevant_numeric_source_lines():
    prompt = (
        "Extract revenue and debt.\n"
        "The company reported revenue of $120.5 million in 2025.\n"
        "Long-term debt was $42.0 million at year end.\n"
        "The office has blue carpet and seven windows."
    )
    out = extract_evidence(prompt)
    assert "revenue of $120.5 million" in out
    assert "debt was $42.0 million" in out
