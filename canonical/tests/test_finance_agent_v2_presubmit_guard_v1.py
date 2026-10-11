from __future__ import annotations
import unittest

from canonical.runtime.finance_agent_v2_presubmit_guard_v1 import (
    compile_requirements,
    evaluate,
)

SOURCES='''{
  "sources": [
    {"url": "https://www.sec.gov/example", "name": "SEC filing"}
  ]
}'''

class Tests(unittest.TestCase):
    def test_compiler_detects_public_contract_requirements(self):
        q=(
            "For NASDAQ:SUI, use the 8-K and calculate the percent change in "
            "closing share price after the announcement."
        )
        out=compile_requirements(q)
        self.assertTrue(out["requires_calculator"])
        self.assertTrue(out["requires_price_history"])
        self.assertTrue(out["requires_sec_evidence"])
        self.assertEqual(out["tickers"],["SUI"])

    def test_complete_evidence_allows_submit(self):
        q=(
            "For NASDAQ:SUI, use the 8-K and calculate the percent change in "
            "closing share price after the announcement."
        )
        receipts=[
            {"tool_name":"edgar_search","status":"ok","result":"filing"},
            {"tool_name":"price_history","status":"ok","result":"csv"},
            {"tool_name":"calculator","status":"ok","result":"2.20"},
        ]
        out=evaluate(
            question=q,
            final_result="The result is 2.20%.\n"+SOURCES,
            tool_receipts=receipts,
        )
        self.assertTrue(out["pass"],out)

    def test_missing_calculator_blocks(self):
        out=evaluate(
            question="Calculate 2-year revenue CAGR for NASDAQ:CRWD.",
            final_result="32.82%\n"+SOURCES,
            tool_receipts=[{"tool_name":"edgar_search","status":"ok","result":"x"}],
        )
        self.assertFalse(out["pass"])
        self.assertIn(
            "CALCULATION_REQUEST_WITHOUT_SUCCESSFUL_CALCULATOR_RECEIPT",
            out["errors"],
        )

    def test_price_fallback_requires_failed_price_attempt(self):
        q="Calculate closing share price return for NYSE:SUI."
        no_attempt=evaluate(
            question=q,
            final_result="2.20%\n"+SOURCES,
            tool_receipts=[
                {"tool_name":"calculator","status":"ok","result":"2.20"},
                {"tool_name":"web_search","status":"ok","result":"prices"},
            ],
        )
        self.assertFalse(no_attempt["pass"])
        with_fallback=evaluate(
            question=q,
            final_result="2.20%\n"+SOURCES,
            tool_receipts=[
                {"tool_name":"calculator","status":"ok","result":"2.20"},
                {"tool_name":"price_history","status":"error","error":"unavailable"},
                {"tool_name":"web_search","status":"ok","result":"prices"},
            ],
        )
        self.assertTrue(with_fallback["pass"],with_fallback)

    def test_filing_question_requires_sec_receipt(self):
        out=evaluate(
            question="Using the company's 10-K, identify revenue.",
            final_result="$100 million\n"+SOURCES,
            tool_receipts=[],
        )
        self.assertFalse(out["pass"])
        self.assertIn("FILING_REQUEST_WITHOUT_SEC_EVIDENCE_RECEIPT",out["errors"])

    def test_sources_dictionary_is_mandatory(self):
        out=evaluate(
            question="What does management say about AI?",
            final_result="Management sees a tailwind.",
            tool_receipts=[],
        )
        self.assertFalse(out["pass"])
        self.assertIn("FINAL_SOURCES_DICTIONARY_MISSING_OR_INVALID",out["errors"])


    def test_retrieved_margin_does_not_force_calculator(self):
        out=compile_requirements("What Adjusted EBITDA margin did the company report?")
        self.assertFalse(out["requires_calculator"])

    def test_sources_dictionary_must_be_terminal(self):
        out=evaluate(
            question="What does management say about AI?",
            final_result='Answer.\n'+SOURCES+'\nTrailing prose',
            tool_receipts=[],
        )
        self.assertFalse(out["pass"])
        self.assertIn("FINAL_SOURCES_DICTIONARY_MISSING_OR_INVALID",out["errors"])

if __name__=="__main__":
    unittest.main()
