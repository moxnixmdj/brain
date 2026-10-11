from canonical.runtime.finance_quantitative_dependency_v1 import compile_dependencies
from canonical.runtime.finance_quantitative_question_contract_v1 import compile_question


def deps(question: str) -> dict:
    return compile_dependencies(compile_question(question))


def test_dio_implies_inventory_cost_of_sales_and_period_days():
    out = deps("Calculate days inventory outstanding (DIO) for NYSE:AAA.")
    names = {x["dependency"] for x in out["dependencies"]}
    assert {"INVENTORY", "COST_OF_SALES", "FISCAL_PERIOD_DAYS"} <= names
    assert out["semantic_source_dependency_count"] == 0
    assert out["mechanically_closed_candidate"] is True


def test_market_return_and_sentiment_need_prices_not_semantics():
    out = deps(
        "Calculate closing share price return and use it to gauge market sentiment."
    )
    assert out["market_price_dependency_count"] == 2
    assert out["semantic_source_dependency_count"] == 0
    assert out["mechanically_closed_candidate"] is True


def test_adjusted_ebitda_preserves_adjustment_semantics():
    out = deps("Calculate Adjusted EBITDA and EBITDA margin.")
    semantic = {x["dependency"] for x in out["semantic_source_dependencies"]}
    assert "ADJUSTMENT_SET" in semantic
    assert out["mechanically_closed_candidate"] is False


def test_transaction_premium_preserves_offer_term_semantics():
    out = deps("Calculate the premium paid to the unaffected share price.")
    semantic = {x["dependency"] for x in out["semantic_source_dependencies"]}
    assert "OFFER_OR_TRANSACTION_PRICE" in semantic
    assert out["market_price_dependency_count"] == 1


def test_dcf_question_literals_do_not_become_model_dependencies():
    out = deps(
        "Build a DCF using an 8% discount rate and a 10x exit multiple."
    )
    assert out["question_literal_dependency_count"] >= 2
    assert out["model_dependency_count"] == 0
    assert out["benchmark_score_credit"] == 0


def test_reconciliation_remains_semantic_source_work():
    out = deps("Reconstruct the GAAP-to-Adjusted EBITDA reconciliation.")
    assert out["semantic_source_dependency_count"] >= 1
    assert out["mechanically_closed_candidate"] is False
