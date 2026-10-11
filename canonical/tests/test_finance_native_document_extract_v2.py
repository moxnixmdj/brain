from canonical.runtime.finance_native_document_extract_v2 import (
    extract_with_context,
    ownership_receipt,
)


def test_context_window_preserves_year_header_above_revenue_row():
    prompt = """
[OBJECTIVE]
entity=CRWD
operations=CAGR
metrics=REVENUE
question=Calculate revenue CAGR from FY2023 to FY2025
[/OBJECTIVE]
[DOCUMENT]
Annual report
Amounts in millions
2025 2024 2023
Revenue 3953.624 3055.555 2241.236
Gross margin 75% 74% 73%
Unrelated legal prose
[/DOCUMENT]
"""
    out = extract_with_context(prompt, context_before=2, context_after=1)
    assert "2025 2024 2023" in out
    assert "Revenue 3953.624 3055.555 2241.236" in out


def test_context_window_preserves_units_neighbor():
    prompt = """
[OBJECTIVE]
metrics=CAPEX
question=Find capex
[/OBJECTIVE]
[DOCUMENT]
Consolidated cash flows
Amounts in millions
Capital expenditures 100 120 130
Other thing
[/DOCUMENT]
"""
    out = extract_with_context(prompt, context_before=1, context_after=0)
    assert "Amounts in millions" in out
    assert "Capital expenditures 100 120 130" in out


def test_unstructured_helper_prompt_fails_closed():
    assert extract_with_context("summarize this") == "BRAIN_NATIVE_HELPER_UNRESOLVED"


def test_irrelevant_document_does_not_emit_arbitrary_rows():
    prompt = """
[OBJECTIVE]
metrics=REVENUE
question=Find revenue
[/OBJECTIVE]
[DOCUMENT]
No matching financial concept here.
Another unrelated statement.
[/DOCUMENT]
"""
    assert (
        extract_with_context(prompt)
        == "BRAIN_NATIVE_HELPER_NO_RELEVANT_ROWS"
    )


def test_ownership_receipt_zero_model():
    r = ownership_receipt()
    assert r["model_dependency_count"] == 0
    assert r["external_cognition_dependency_count"] == 0
    assert r["teacher_runtime_calls"] == 0
    assert r["semantic_completion_performed"] is False
    assert r["benchmark_score_credit"] == 0
