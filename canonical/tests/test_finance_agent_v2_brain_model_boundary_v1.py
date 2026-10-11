from __future__ import annotations
import asyncio
import unittest

from canonical.runtime.finance_agent_v2_brain_model_boundary_v1 import (
    FinanceModelBoundaryError,
    choose_next_tool_call,
    normalize_vals_tools,
)

TOOLS = [
    {
        "name": "edgar_search",
        "body": {
            "description": "Search SEC filings.",
            "properties": {"search_query": {"type": "string"}},
            "required": ["search_query"],
        },
    },
    {
        "name": "submit_final_result",
        "body": {
            "description": "Submit the final result to the user.",
            "properties": {"final_result": {"type": "string"}},
            "required": ["final_result"],
        },
    },
]

class Substrate:
    def __init__(self, finish=False):
        self.finish = finish
    async def __call__(self, kind, payload):
        if kind == "SUBPROBLEM":
            return {
                "goal": "finish" if self.finish else "research",
                "required_capabilities": [
                    "SUBMIT_FINAL_ANSWER" if self.finish else "SEARCH_SEC"
                ],
                "constraint": None,
            }
        if kind == "SCHEMA_JUDGMENT":
            d = payload["anonymous_tool"]["description"].lower()
            c = payload["required_capability"]
            return {"supported": (
                (c == "SEARCH_SEC" and "sec filing" in d)
                or (c == "SUBMIT_FINAL_ANSWER" and "submit the final" in d)
            )}
        if kind == "ARGUMENTS":
            d = payload["anonymous_selected_tool"]["description"].lower()
            if "sec filing" in d:
                return {"arguments": {"search_query": "revenue"}}
            return {"arguments": {"final_result": "answer"}}
        raise AssertionError(kind)

class Tests(unittest.TestCase):
    def test_normalize(self):
        out = normalize_vals_tools(TOOLS)
        self.assertEqual([x["tool_id"] for x in out], ["edgar_search", "submit_final_result"])

    def test_research_then_submit(self):
        async def run():
            a = await choose_next_tool_call(
                history=[{"role": "user", "content": "q"}],
                tool_definitions=TOOLS,
                substrate=Substrate(False),
            )
            self.assertEqual(a["tool_name"], "edgar_search")
            b = await choose_next_tool_call(
                history=[
                    {"role": "user", "content": "q"},
                    {"role": "tool", "name": "edgar_search", "content": "x"},
                ],
                tool_definitions=TOOLS,
                substrate=Substrate(True),
            )
            self.assertEqual(b["tool_name"], "submit_final_result")
            self.assertEqual(b["arguments"], {"final_result": "answer"})
        asyncio.run(run())

    def test_bad_schema_fails_closed(self):
        with self.assertRaises(FinanceModelBoundaryError):
            normalize_vals_tools([{"name": "x", "body": {"properties": {}}}])

if __name__ == "__main__":
    unittest.main()
