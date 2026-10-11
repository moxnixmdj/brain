from __future__ import annotations
import asyncio
import unittest

from canonical.runtime.finance_agent_v2_brain_model_boundary_v2 import (
    FinanceModelBoundaryV2Error,
    choose_next_tool_call,
)

TOOLS = [
    {
        "name":"calculator",
        "body":{
            "description":"Evaluate a mathematical expression.",
            "properties":{"expression":{"type":"string"}},
            "required":["expression"],
        },
    },
    {
        "name":"submit_final_result",
        "body":{
            "description":"Submit the final result to the user.",
            "properties":{"final_result":{"type":"string"}},
            "required":["final_result"],
        },
    },
]

class RepairingSubstrate:
    def __init__(self):
        self.saw_repair=False

    async def __call__(self, kind, payload):
        context=str(payload.get("task_context") or "")
        if "BRAIN_PRESUBMIT_REPAIR_REQUIRED" in context:
            self.saw_repair=True

        if kind=="SUBPROBLEM":
            if self.saw_repair:
                return {
                    "goal":"obtain verified arithmetic evidence",
                    "required_capabilities":["ARITHMETIC"],
                    "constraint":None,
                }
            return {
                "goal":"finish",
                "required_capabilities":["SUBMIT"],
                "constraint":None,
            }

        if kind=="SCHEMA_JUDGMENT":
            desc=payload["anonymous_tool"]["description"].lower()
            cap=payload["required_capability"]
            return {"supported":(
                (cap=="SUBMIT" and "submit the final" in desc)
                or (cap=="ARITHMETIC" and "mathematical expression" in desc)
            )}

        if kind=="ARGUMENTS":
            desc=payload["anonymous_selected_tool"]["description"].lower()
            if "submit the final" in desc:
                return {
                    "arguments":{
                        "final_result":(
                            'Revenue CAGR is 32.82%.\n'
                            '{"sources":[{"url":"https://www.sec.gov/x","name":"SEC"}]}'
                        )
                    }
                }
            return {"arguments":{"expression":"(200/113.37)**0.5-1"}}

        raise AssertionError(kind)

class FixedSubmitSubstrate:
    async def __call__(self,kind,payload):
        if kind=="SUBPROBLEM":
            return {"goal":"finish","required_capabilities":["SUBMIT"],"constraint":None}
        if kind=="SCHEMA_JUDGMENT":
            return {
                "supported":"submit the final" in payload["anonymous_tool"]["description"].lower()
            }
        if kind=="ARGUMENTS":
            return {
                "arguments":{
                    "final_result":(
                        'Revenue CAGR is 32.82%.\n'
                        '{"sources":[{"url":"https://www.sec.gov/x","name":"SEC"}]}'
                    )
                }
            }
        raise AssertionError(kind)

class Tests(unittest.TestCase):
    def test_missing_calculator_repairs_into_calculator_action(self):
        async def run():
            substrate=RepairingSubstrate()
            out=await choose_next_tool_call(
                question="Calculate revenue CAGR.",
                history=[{"role":"user","content":"Calculate revenue CAGR."}],
                tool_definitions=TOOLS,
                tool_receipts=[],
                substrate=substrate,
            )
            self.assertEqual(out["tool_name"],"calculator")
            self.assertTrue(out["presubmit_guard_applied"])
            self.assertEqual(out["repair_rounds"],1)
        asyncio.run(run())

    def test_verified_calculator_allows_submit(self):
        async def run():
            out=await choose_next_tool_call(
                question="Calculate revenue CAGR.",
                history=[{"role":"user","content":"Calculate revenue CAGR."}],
                tool_definitions=TOOLS,
                tool_receipts=[
                    {"tool_name":"calculator","status":"ok","result":"0.3282"}
                ],
                substrate=FixedSubmitSubstrate(),
            )
            self.assertEqual(out["tool_name"],"submit_final_result")
            self.assertTrue(out["presubmit_audits"][-1]["pass"])
            self.assertEqual(out["repair_rounds"],0)
        asyncio.run(run())

    def test_unrepaired_submit_fails_closed(self):
        async def run():
            with self.assertRaisesRegex(
                FinanceModelBoundaryV2Error,
                "PRESUBMIT_REPAIR_BUDGET_EXHAUSTED",
            ):
                await choose_next_tool_call(
                    question="Calculate revenue CAGR.",
                    history=[{"role":"user","content":"Calculate revenue CAGR."}],
                    tool_definitions=TOOLS,
                    tool_receipts=[],
                    substrate=FixedSubmitSubstrate(),
                    max_repair_rounds=1,
                )
        asyncio.run(run())

if __name__=="__main__":
    unittest.main()
