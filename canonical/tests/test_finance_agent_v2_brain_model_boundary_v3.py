import asyncio
import json

from canonical.runtime import finance_agent_v2_brain_model_boundary_v3 as v3


def test_work_contract_compiles_financial_modeling_dependencies_without_facts():
    q = (
        "Create a simplified LBO model for NYSE: EPAM. Use a 30.0% offer premium, "
        "5.0x leverage, 8% interest, a 5-year hold, 10.0x exit multiple, and "
        "calculate initial sponsor equity, exit enterprise value, exit equity, "
        "IRR and MOIC."
    )
    out = v3.build_work_contract(q)

    assert "LBO" in out["operations"]
    assert "IRR" in out["operations"]
    assert "MOIC" in out["operations"]
    assert out["tickers"] == ["NYSE:EPAM"]
    assert any(
        row["kind"] == "QUESTION_LITERAL"
        for row in out["dependencies"]
    )
    assert out["source_fact_binding_proved"] is False
    assert out["benchmark_score_credit"] == 0
    assert out["model_dependency_count"] == 0


def test_work_contract_routes_market_price_requirements_without_inventing_price():
    out = v3.build_work_contract(
        "For NYSE: SUI calculate the share price return from 07/15/2025 "
        "through 07/29/2025 using closing share prices."
    )
    assert "SHARE_PRICE_RETURN" in out["operations"]
    assert "MARKET_PRICE_HISTORY" in out["source_hints"]
    assert any(
        row["kind"] == "MARKET_PRICE"
        for row in out["dependencies"]
    )
    serialized = json.dumps(out, sort_keys=True)
    assert "source_fact_binding_proved" in serialized


def test_v3_adds_internal_contract_and_preserves_v2_execution_surface(monkeypatch):
    captured = {}

    async def fake_v2(**kwargs):
        captured.update(kwargs)
        return {
            "tool_name": "calculator",
            "arguments": {"expression": "1+1"},
            "status": "BRAIN_SELECTED_OFFICIAL_VALS_TOOL_CALL",
        }

    monkeypatch.setattr(v3, "choose_v2", fake_v2)

    tools = [
        {
            "name": "calculator",
            "body": {
                "description": "calculate",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        }
    ]
    receipts = [{"tool_name": "edgar_search", "status": "success"}]
    original_history = [{"role": "user", "content": "question"}]

    out = asyncio.run(
        v3.choose_next_tool_call(
            question="For NYSE: EPAM calculate an LBO and IRR.",
            history=original_history,
            tool_definitions=tools,
            tool_receipts=receipts,
            substrate=lambda *_: {},
            max_repair_rounds=3,
        )
    )

    assert out["tool_name"] == "calculator"
    assert out["finance_work_contract_applied"] is True
    assert out["official_vals_tool_surface_unchanged"] is True
    assert captured["tool_definitions"] is tools
    assert captured["tool_receipts"] is receipts
    assert captured["max_repair_rounds"] == 3
    assert len(captured["history"]) == len(original_history) + 1
    added = captured["history"][-1]
    assert added["role"] == "system"
    assert added["brain_internal"] is True
    assert added["content"].startswith("BRAIN_FINANCE_WORK_CONTRACT_V1:")
