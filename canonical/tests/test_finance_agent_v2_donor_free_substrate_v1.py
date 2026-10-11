import json

import pytest

from canonical.runtime.finance_agent_v2_donor_free_substrate_v1 import (
    CAP_PRICE,
    CAP_READ_CONCEPT,
    CAP_READ_REGISTRY,
    CAP_STORE_CONCEPT,
    CAP_STORE_REGISTRY,
    CAP_UNRESOLVED,
    FinanceDonorFreeSubstrate,
)


def _payload(conversation):
    return {
        "task_context": json.dumps(
            {"conversation": conversation},
            sort_keys=True,
            separators=(",", ":"),
        )
    }


def _q(text):
    return [{"role": "user", "content": text}]


def test_price_route_is_derived_without_tool_catalog_or_model():
    q = (
        "Analyze price performance for NYSE: NOW from 12/31/2025 to 02/27/2026 "
        "and calculate the share price return."
    )
    substrate = FinanceDonorFreeSubstrate()
    contract = substrate("SUBPROBLEM", _payload(_q(q)))
    assert contract["required_capabilities"] == [CAP_PRICE]

    args = substrate("ARGUMENTS", {
        **_payload(_q(q)),
        "selected_capabilities": [CAP_PRICE],
    })
    assert args["arguments"] == {
        "ticker": "NOW",
        "start_date": "2025-12-31",
        "end_date": "2026-02-27",
        "asset_class": "equity",
    }


def test_sec_route_progresses_registry_identity_concept_then_fail_closed():
    q = "For NYSE: EPAM calculate FY2025 revenue from the annual filing."
    substrate = FinanceDonorFreeSubstrate()
    conversation = _q(q)

    c1 = substrate("SUBPROBLEM", _payload(conversation))
    assert c1["required_capabilities"] == [CAP_STORE_REGISTRY]
    a1 = substrate("ARGUMENTS", {
        **_payload(conversation),
        "selected_capabilities": [CAP_STORE_REGISTRY],
    })["arguments"]
    assert a1["key"] == "sec_ticker_registry"

    conversation.append({
        "role": "tool", "status": "success",
        "arguments": a1,
        "content": "Successfully parsed and saved under key sec_ticker_registry",
    })
    c2 = substrate("SUBPROBLEM", _payload(conversation))
    assert c2["required_capabilities"] == [CAP_READ_REGISTRY]

    a2 = substrate("ARGUMENTS", {
        **_payload(conversation),
        "selected_capabilities": [CAP_READ_REGISTRY],
    })["arguments"]
    assert "{{sec_ticker_registry}}" in a2["prompt"]

    conversation.append({
        "role": "tool", "status": "success",
        "arguments": a2,
        "content": (
            'BRAIN_EXTRACTIVE_EVIDENCE_ONLY\n'
            '[SEC_TICKER_IDENTITY] '
            '{"cik_str": 1352010, "ticker": "EPAM", '
            '"title": "EPAM Systems, Inc."}'
        ),
    })
    c3 = substrate("SUBPROBLEM", _payload(conversation))
    assert c3["required_capabilities"] == [CAP_STORE_CONCEPT]

    a3 = substrate("ARGUMENTS", {
        **_payload(conversation),
        "selected_capabilities": [CAP_STORE_CONCEPT],
    })["arguments"]
    assert a3["url"].startswith(
        "https://data.sec.gov/api/xbrl/companyconcept/CIK0001352010/"
    )
    assert a3["key"].startswith("sec_EPAM_REVENUE_")

    conversation.append({
        "role": "tool", "status": "success",
        "arguments": a3,
        "content": "Successfully parsed SEC JSON",
    })
    c4 = substrate("SUBPROBLEM", _payload(conversation))
    assert c4["required_capabilities"] == [CAP_READ_CONCEPT]

    a4 = substrate("ARGUMENTS", {
        **_payload(conversation),
        "selected_capabilities": [CAP_READ_CONCEPT],
    })["arguments"]
    assert "{{" + a3["key"] + "}}" in a4["prompt"]

    conversation.append({
        "role": "tool", "status": "success",
        "arguments": a4,
        "content": (
            'BRAIN_EXTRACTIVE_EVIDENCE_ONLY\n'
            '[SEC_COMPANYCONCEPT] {"tag":"RevenueFromContractWithCustomerExcludingAssessedTax"}\n'
            '[SEC_FACT] {"fy":2025,"form":"10-K","unit":"USD","val":5457056000}'
        ),
    })
    c5 = substrate("SUBPROBLEM", _payload(conversation))
    assert c5["required_capabilities"] == [CAP_UNRESOLVED]


def test_schema_judgment_uses_anonymous_schema_only():
    substrate = FinanceDonorFreeSubstrate()
    judged = substrate("SCHEMA_JUDGMENT", {
        "required_capability": CAP_PRICE,
        "anonymous_tool": {
            "description": "Fetch historical daily price data.",
            "input_schema": {
                "properties": {
                    "ticker": {}, "start_date": {}, "end_date": {}, "asset_class": {}
                }
            },
        },
    })
    assert judged == {
        "supported": True,
        "reason": "DETERMINISTIC_SCHEMA_MATCH",
    }

    rejected = substrate("SCHEMA_JUDGMENT", {
        "required_capability": CAP_PRICE,
        "anonymous_tool": {
            "description": "Evaluate arithmetic",
            "input_schema": {"properties": {"expression": {}}},
        },
    })
    assert rejected["supported"] is False


def test_unresolved_computation_has_no_tool_match_and_cannot_fall_back_to_model():
    substrate = FinanceDonorFreeSubstrate()
    judged = substrate("SCHEMA_JUDGMENT", {
        "required_capability": CAP_UNRESOLVED,
        "anonymous_tool": {
            "description": "Evaluate arithmetic",
            "input_schema": {"properties": {"expression": {}}},
        },
    })
    assert judged["supported"] is False
