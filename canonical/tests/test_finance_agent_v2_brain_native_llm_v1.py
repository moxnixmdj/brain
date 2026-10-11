from __future__ import annotations

import json

import pytest

from canonical.runtime.finance_agent_v2_brain_native_llm_v1 import (
    ALLOWED_TOOLS,
    BrainNativeFinanceError,
    deterministic_document_extract,
    extract_question,
    ownership_receipt,
    plan_next,
)


def text(value: str) -> dict:
    return {"kind": "text", "text": value}


def result(name: str, value: str) -> dict:
    return {
        "kind": "tool_result",
        "tool_call": {"name": name},
        "result": value,
    }


def tools(*names: str) -> list[dict]:
    return [{"name": name} for name in names]


def all_tools() -> list[dict]:
    return tools(*sorted(ALLOWED_TOOLS))


def test_extracts_official_question_envelope():
    q = extract_question(
        [
            {"kind": "system", "text": "system"},
            text("Question:\nCalculate revenue CAGR for NYSE:ABC."),
        ]
    )
    assert q == "Calculate revenue CAGR for NYSE:ABC."


def test_unknown_tool_definition_fails_closed():
    with pytest.raises(
        BrainNativeFinanceError, match="UNRECOGNIZED_TOOL_DEFINITION"
    ):
        plan_next(
            [text("Question:\nCalculate CAGR for NYSE:ABC.")],
            tools("web_search", "mystery_model_tool"),
        )


def test_market_price_question_uses_official_price_history_first():
    call = plan_next(
        [
            text(
                "Question:\nCalculate the share price return for NYSE:ABC "
                "from 2025-01-02 to 2025-02-03."
            )
        ],
        all_tools(),
    )
    assert call.name == "price_history"
    assert call.args == {
        "ticker": "ABC",
        "start_date": "2025-01-02",
        "end_date": "2025-02-03",
        "asset_class": "equity",
    }


def test_sec_quantitative_question_discovers_source_without_model():
    call = plan_next(
        [
            text(
                "Question:\nUsing the annual filing, calculate revenue CAGR "
                "for NYSE:ABC from FY2023 to FY2025."
            )
        ],
        all_tools(),
    )
    assert call.name == "web_search"
    assert "site:sec.gov" in call.args["search_query"]
    assert call.args["end_date"] == "2026-03-01"


def test_search_result_routes_to_primary_source_parse():
    payload = json.dumps(
        [
            {
                "url": "https://example.com/commentary",
                "title": "commentary",
            },
            {
                "url": "https://www.sec.gov/Archives/edgar/data/1/a.htm",
                "title": "10-K",
            },
        ]
    )
    call = plan_next(
        [
            text("Question:\nCalculate revenue CAGR for NYSE:ABC."),
            result("web_search", payload),
        ],
        all_tools(),
    )
    assert call.name == "parse_html_page"
    assert call.args["url"].startswith("https://www.sec.gov/Archives/")


def test_parsed_document_routes_to_same_brain_native_helper():
    call = plan_next(
        [
            text("Question:\nCalculate revenue CAGR for NYSE:ABC."),
            result(
                "web_search",
                '[{"url":"https://www.sec.gov/Archives/edgar/data/1/a.htm"}]',
            ),
            result(
                "parse_html_page",
                "SUCCESS: The result has been saved to the data storage under "
                "the key: brain_finance_source_1.",
            ),
        ],
        all_tools(),
    )
    assert call.name == "retrieve_information"
    prompt = call.args["prompt"]
    assert "[OBJECTIVE]" in prompt
    assert "[DOCUMENT]{{brain_finance_source_1}}[/DOCUMENT]" in prompt


def test_helper_extraction_is_deterministic_and_relation_local():
    prompt = """
[OBJECTIVE]
operations=CAGR
metrics=REVENUE
question=Calculate revenue CAGR
[/OBJECTIVE]
[DOCUMENT]
Noise without useful facts.
Revenue for fiscal 2023 was $100 million.
Revenue for fiscal 2025 was $144 million.
Another unrelated sentence says 999.
[/DOCUMENT]
"""
    out1 = deterministic_document_extract(prompt)
    out2 = deterministic_document_extract(prompt)
    assert out1 == out2
    assert "Revenue for fiscal 2023 was $100 million." in out1
    assert "Revenue for fiscal 2025 was $144 million." in out1
    assert "Another unrelated sentence says 999." not in out1


def test_helper_rejects_unstructured_prompt_instead_of_guessing():
    assert (
        deterministic_document_extract("Please summarize this somehow.")
        == "BRAIN_NATIVE_HELPER_UNRESOLVED"
    )


def test_after_native_helper_v1_submits_evidence_not_fake_semantics():
    history = [
        text("Question:\nExplain revenue CAGR for NYSE:ABC."),
        result(
            "web_search",
            '[{"url":"https://www.sec.gov/Archives/edgar/data/1/a.htm"}]',
        ),
        result(
            "parse_html_page",
            "SUCCESS: The result has been saved to the data storage under the "
            "key: brain_finance_source_1.",
        ),
        result(
            "retrieve_information",
            "BRAIN_NATIVE_EXTRACTIVE_EVIDENCE_V1\nRevenue was 100 then 144.",
        ),
    ]
    call = plan_next(history, all_tools())
    assert call.name == "submit_final_result"
    answer = call.args["final_result"]
    assert "Brain-native Finance evidence package." in answer
    assert "SEMANTIC_OR_SOURCE_RESIDUAL_REMAINS" in answer


def test_ownership_receipt_has_zero_external_cognition():
    r = ownership_receipt()
    assert r["external_model_calls"] == 0
    assert r["external_reasoning_model_calls"] == 0
    assert r["model_dependency_count"] == 0
    assert r["custom_endpoint_used"] is False
    assert r["teacher_runtime_calls"] == 0
    assert r["target_score_claimed"] is False
    assert r["benchmark_score_credit"] == 0
