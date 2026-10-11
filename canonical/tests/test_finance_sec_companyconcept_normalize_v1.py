import pytest

from canonical.runtime.finance_sec_companyconcept_normalize_v1 import (
    SecCompanyConceptNormalizationError,
    normalize_companyconcept,
)
from canonical.runtime.finance_sec_fact_selector_v1 import select_fact


URL = (
    "https://data.sec.gov/api/xbrl/companyconcept/"
    "CIK0001352010/us-gaap/WeightedAverageNumberOfSharesOutstandingBasic.json"
)


def _payload():
    return {
        "cik": 1352010,
        "entityName": "EPAM Systems, Inc.",
        "taxonomy": "us-gaap",
        "tag": "WeightedAverageNumberOfSharesOutstandingBasic",
        "label": "Weighted Average Number of Shares Outstanding Basic",
        "description": "Synthetic shape matching SEC CompanyConcept.",
        "units": {
            "shares": [
                {
                    "start": "2025-01-01",
                    "end": "2025-12-31",
                    "val": 55893000,
                    "accn": "0001352010-26-000001",
                    "fy": 2025,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2026-02-27",
                    "frame": "CY2025",
                },
                {
                    "start": "2025-01-01",
                    "end": "2025-12-31",
                    "val": 55893000,
                    "accn": "0001352010-26-000002",
                    "fy": 2025,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2026-02-27",
                },
            ]
        },
    }


def test_companyconcept_normalize_then_select_unique_value():
    doc = normalize_companyconcept(
        _payload(),
        source_url=URL,
        expected_cik10="0001352010",
        expected_taxonomy="us-gaap",
        expected_tag="WeightedAverageNumberOfSharesOutstandingBasic",
    )
    assert doc["source_native_identity_extracted"] is True
    assert doc["semantic_contract"]["fact_row_count"] == 2
    selected = select_fact(
        doc,
        fiscal_year=2025,
        forms=["10-K"],
        unit="shares",
        period_kind="duration",
    )
    assert selected["value"] == 55893000
    assert selected["all_surviving_values_equal"] is True
    assert selected["model_dependency_count"] == 0


def test_companyconcept_rejects_url_payload_identity_mismatch():
    payload = _payload()
    payload["tag"] = "NetIncomeLoss"
    with pytest.raises(
        SecCompanyConceptNormalizationError,
        match="PAYLOAD_TAG_URL_MISMATCH",
    ):
        normalize_companyconcept(payload, source_url=URL)
