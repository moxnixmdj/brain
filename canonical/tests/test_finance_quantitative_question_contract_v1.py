from canonical.runtime.finance_quantitative_question_contract_v1 import compile_question


def ops(question: str) -> set[str]:
    return set(compile_question(question)["operations"])


def test_cagr_bps_and_tickers_compile_without_category_label():
    out = compile_question(
        "For NASDAQ:AAA and NYSE:BBB, calculate the 3-year revenue CAGR "
        "and state the difference in basis points."
    )
    assert out["tickers"] == ["NASDAQ:AAA", "NYSE:BBB"]
    assert {"CAGR", "BASIS_POINT_DELTA"} <= set(out["operations"])
    assert out["model_dependency_count"] == 0
    assert out["semantic_adequacy_proved"] is False


def test_inventory_workflow_is_structural_candidate():
    out = compile_question(
        "Compare average inventory and days inventory outstanding (DIO) "
        "for NYSE:AAA and NYSE:BBB."
    )
    assert {"AVERAGE", "DAYS_INVENTORY_OUTSTANDING"} <= set(out["operations"])
    assert out["fully_structured_candidate"] is True


def test_market_return_ranking_compiles():
    out = compile_question(
        "Using closing share prices from 01/02/2025 through 02/27/2026, "
        "calculate share price return and rank NASDAQ:AAA and NASDAQ:BBB."
    )
    assert {"SHARE_PRICE_RETURN", "RANK_COMPARISON"} <= set(out["operations"])
    assert "MARKET_PRICE_HISTORY" in out["source_hints"]


def test_comparables_formula_families_compile():
    out = compile_question(
        "Compare price to book, debt to equity, debt to total capital, "
        "EV/EBITDA, and EBITDA margin for NYSE:AAA and NYSE:BBB."
    )
    assert {
        "PRICE_TO_BOOK",
        "DEBT_TO_EQUITY",
        "DEBT_TO_TOTAL_CAPITAL",
        "EV_TO_EBITDA",
        "EBITDA_MARGIN",
    } <= set(out["operations"])


def test_fixed_charge_coverage_and_adjusted_ebitdar_compile():
    out = compile_question(
        "Calculate FCCR using Adjusted EBITDAR divided by fixed charges."
    )
    assert {"FIXED_CHARGE_COVERAGE", "ADJUSTED_EBITDAR"} <= set(out["operations"])


def test_transaction_math_compiles_but_strategic_tail_stays_open():
    out = compile_question(
        "Calculate the premium paid to the unaffected share price, EV/FY2025 Revenue, "
        "and EV/Adjusted EBITDA, then explain the strategic rationale."
    )
    assert {"TRANSACTION_PREMIUM", "EV_TO_REVENUE", "EV_TO_EBITDA"} <= set(out["operations"])
    assert out["semantic_tail_required"] is True
    assert out["fully_structured_candidate"] is False


def test_guidance_and_earnings_math_compile():
    out = compile_question(
        "Using the midpoint of each guidance range, calculate capex intensity "
        "and the beat / (miss) % versus actual results."
    )
    assert {"GUIDANCE_MIDPOINT", "INTENSITY", "BEAT_MISS_PERCENT"} <= set(out["operations"])


def test_adjustment_reconciliation_compiles():
    out = compile_question(
        "Reconstruct the GAAP-to-Adjusted EBITDA reconciliation, identify add-backs, "
        "and normalize gross margin."
    )
    assert {"ADJUSTED_EBITDA", "RECONCILIATION", "ADDBACKS", "NORMALIZATION", "MARGIN_CHANGE"} <= set(out["operations"])


def test_dcf_terminal_methods_compile():
    out = compile_question(
        "Build a 5-year DCF using an exit multiple and perpetual growth terminal value."
    )
    assert {"DCF", "EXIT_MULTIPLE_TERMINAL_VALUE", "PERPETUAL_GROWTH_TERMINAL_VALUE"} <= set(out["operations"])


def test_lbo_irr_moic_compile():
    out = compile_question(
        "Create a simplified LBO take-private and calculate sponsor equity, IRR and MOIC."
    )
    assert {"LBO", "IRR", "MOIC"} <= set(out["operations"])


def test_qualitative_question_does_not_fake_quantitative_coverage():
    out = compile_question(
        "Who are NASDAQ:AAA's competitors and what risks does management discuss?"
    )
    assert out["quantitative_candidate"] is False
    assert out["semantic_tail_required"] is True
    assert out["benchmark_score_credit"] == 0



def test_market_sentiment_is_compiled_as_deterministic_return_consequence():
    out = compile_question(
        "Calculate the closing share price return and use it to gauge market sentiment."
    )
    assert {"SHARE_PRICE_RETURN", "MARKET_SENTIMENT_FROM_RETURN"} <= set(out["operations"])
    assert out["semantic_tail_required"] is False


def test_guidance_conservatism_is_compiled_as_strict_dominance_candidate():
    out = compile_question(
        "Compare beat / (miss) % across guidance and determine which company gave more conservative guidance."
    )
    assert {"BEAT_MISS_PERCENT", "GUIDANCE_CONSERVATISM_DOMINANCE"} <= set(out["operations"])
    assert out["semantic_tail_required"] is False


def test_strategic_investments_label_does_not_create_fake_semantic_tail():
    out = compile_question(
        'Build a DCF and exclude the value of "strategic investments".'
    )
    assert "DCF" in out["operations"]
    assert out["semantic_tail_required"] is False


def test_source_hints_are_advisory_only():
    out = compile_question(
        "Use the 8-K and annual report plus closing share price to calculate a return."
    )
    assert {"SEC_8K", "ANNUAL_FILING", "MARKET_PRICE_HISTORY"} <= set(out["source_hints"])
    assert out["source_fact_binding_proved"] is False
