from __future__ import annotations

import json

from canonical.runtime.finance_agent_v2_brain_native_llm_v1 import ALLOWED_TOOLS
from canonical.runtime.finance_agent_v2_brain_native_llm_v2 import (
    ownership_receipt_v2,
    plan_next_v2,
    synthesize_market,
)


def text(value: str) -> dict:
    return {"kind": "text", "text": value}


def result(name: str, args: dict, value: str) -> dict:
    return {
        "kind": "tool_result",
        "tool_call": {"name": name, "args": args},
        "result": value,
    }


def tools() -> list[dict]:
    return [{"name": name} for name in sorted(ALLOWED_TOOLS)]


def csv_prices(a: str, b: str) -> str:
    return (
        "date,open,high,low,close\n"
        f"2025-01-02,0,0,0,{a}\n"
        f"2026-02-27,0,0,0,{b}\n"
    )


QUESTION = (
    "Question:\nFor NASDAQ: DKNG and NYSE: FLUT, what are the companies' "
    "share price return from 01/02/2025 through 02/27/2026? "
    "Use the closing share prices at each date and rank them."
)


def test_multi_entity_market_planner_fetches_each_ticker_once():
    h = [text(QUESTION)]
    c1 = plan_next_v2(h, tools())
    assert c1.name == "price_history"
    assert c1.args["ticker"] == "DKNG"

    h.append(result("price_history", c1.args, csv_prices("100", "120")))
    c2 = plan_next_v2(h, tools())
    assert c2.name == "price_history"
    assert c2.args["ticker"] == "FLUT"

    h.append(result("price_history", c2.args, csv_prices("100", "80")))
    c3 = plan_next_v2(h, tools())
    assert c3.name == "submit_final_result"
    assert "DKNG: 20.00%" in c3.args["final_result"]
    assert "FLUT: (20.00%)" in c3.args["final_result"]
    assert "DKNG > FLUT" in c3.args["final_result"]


def test_market_synthesis_uses_raw_closes_and_deterministic_ranking():
    h = [
        text(QUESTION),
        result(
            "price_history",
            {
                "ticker": "DKNG",
                "start_date": "2025-01-02",
                "end_date": "2026-02-27",
                "asset_class": "equity",
            },
            csv_prices("50", "75"),
        ),
        result(
            "price_history",
            {
                "ticker": "FLUT",
                "start_date": "2025-01-02",
                "end_date": "2026-02-27",
                "asset_class": "equity",
            },
            csv_prices("200", "150"),
        ),
    ]
    out = synthesize_market(QUESTION.removeprefix("Question:\n"), h)
    assert out is not None
    assert out["raw_close_only"] is True
    assert out["ranking_high_to_low"] == ["DKNG", "FLUT"]
    vals = {x["ticker"]: x for x in out["details"]}
    assert vals["DKNG"]["display_return"] == "50.00%"
    assert vals["FLUT"]["display_return"] == "(25.00%)"


def test_mixed_market_and_revenue_continues_to_per_entity_sources():
    q = (
        "Question:\nFor NASDAQ: DKNG and NYSE: FLUT, calculate share price "
        "return from 01/02/2025 through 02/27/2026 and FY2025 revenue growth."
    )
    h = [
        text(q),
        result(
            "price_history",
            {
                "ticker": "DKNG",
                "start_date": "2025-01-02",
                "end_date": "2026-02-27",
                "asset_class": "equity",
            },
            csv_prices("100", "120"),
        ),
        result(
            "price_history",
            {
                "ticker": "FLUT",
                "start_date": "2025-01-02",
                "end_date": "2026-02-27",
                "asset_class": "equity",
            },
            csv_prices("100", "80"),
        ),
    ]
    c = plan_next_v2(h, tools())
    assert c.name == "web_search"
    assert "DKNG" in c.args["search_query"]

    h.append(
        result(
            "web_search",
            c.args,
            json.dumps(
                [{"url": "https://www.sec.gov/Archives/edgar/data/1/dkng.htm"}]
            ),
        )
    )
    c = plan_next_v2(h, tools())
    assert c.name == "parse_html_page"
    assert c.args["key"] == "brain_finance_dkng_source_1"

    h.append(
        result(
            "parse_html_page",
            c.args,
            "SUCCESS: The result has been saved to the data storage under the "
            "key: brain_finance_dkng_source_1.",
        )
    )
    c = plan_next_v2(h, tools())
    assert c.name == "retrieve_information"
    assert "{{brain_finance_dkng_source_1}}" in c.args["prompt"]

    h.append(
        result(
            "retrieve_information",
            c.args,
            "BRAIN_NATIVE_EXTRACTIVE_EVIDENCE_V1\nDKNG revenue 2025 was 10.",
        )
    )
    c = plan_next_v2(h, tools())
    assert c.name == "web_search"
    assert "FLUT" in c.args["search_query"]


def test_per_entity_pipeline_reaches_second_entity_then_submission():
    q = "Question:\nCompare FY2025 revenue growth for NASDAQ:AAA and NYSE:BBB."
    h = [text(q)]

    for ticker in ("AAA", "BBB"):
        c = plan_next_v2(h, tools())
        assert c.name == "web_search"
        assert ticker in c.args["search_query"]
        h.append(
            result(
                "web_search",
                c.args,
                json.dumps(
                    [{"url": f"https://www.sec.gov/Archives/{ticker.lower()}.htm"}]
                ),
            )
        )
        c = plan_next_v2(h, tools())
        assert c.name == "parse_html_page"
        h.append(
            result(
                "parse_html_page",
                c.args,
                "SUCCESS: The result has been saved to the data storage under the "
                f"key: brain_finance_{ticker.lower()}_source_1.",
            )
        )
        c = plan_next_v2(h, tools())
        assert c.name == "retrieve_information"
        h.append(
            result(
                "retrieve_information",
                c.args,
                f"BRAIN_NATIVE_EXTRACTIVE_EVIDENCE_V1\n{ticker} revenue evidence.",
            )
        )

    c = plan_next_v2(h, tools())
    assert c.name == "submit_final_result"
    answer = c.args["final_result"]
    assert "AAA revenue evidence" in answer
    assert "BBB revenue evidence" in answer


def test_v2_ownership_receipt_remains_zero_model():
    r = ownership_receipt_v2()
    assert r["external_model_calls"] == 0
    assert r["external_reasoning_model_calls"] == 0
    assert r["model_dependency_count"] == 0
    assert r["custom_endpoint_used"] is False
    assert r["teacher_runtime_calls"] == 0
    assert r["multi_entity_source_binding"] is True
    assert r["mechanical_market_synthesis"] is True
    assert r["benchmark_score_credit"] == 0
