#!/usr/bin/env python3
from __future__ import annotations
import unittest

from canonical.runtime import public_source_federation_v2 as fed
from canonical.runtime import federated_retrieval_epoch_gate_v1 as gate
from canonical.runtime import residual_witness_retrieval_compiler_v1 as core
from canonical.runtime import residual_witness_backend_router_v1 as router


class RetrievalV4Tests(unittest.TestCase):
    def queries(self):
        rows=[{"text":"generic english search phrase","basis":"RESIDUAL_EFFECT"} for _ in range(12)]
        rows += [
            {"text":"valid_route_top1","basis":"OBSERVABLE_API_SYMBOLS"},
            {"text":"工具发现 Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
            {"text":"اكتشاف الأدوات Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
            {"text":"обнаружение инструментов Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
            {"text":"उपकरण खोज Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
            {"text":"descubrimiento de herramientas Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
        ]
        return rows

    def base_program(self):
        return core.compile_residual({
            "residual_id":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
            "effect":"find matched Toolathlon evidence",
            "required_capabilities":["valid_route_top1 comparator"],
            "observables":{"api_symbols":["valid_route_top1"]},
            "constraints":{"incremental_spend_usd":0},
        })

    def test_selector_preserves_exact_anchor_and_cross_script_diversity(self):
        selected=fed.select_queries(self.queries(),max_queries=8)
        texts={x["text"] for x in selected}
        scripts={x["script"] for x in selected}
        self.assertIn("valid_route_top1",texts)
        for script in ("CJK","ARABIC","CYRILLIC","DEVANAGARI"):
            self.assertIn(script,scripts,(script,selected))

    def test_late_multilingual_queries_reach_every_source_group(self):
        out=fed.compile_federation(self.queries(),max_queries_per_source=8)
        domains={x["domain"] for x in out["requests"]}
        self.assertEqual(len(domains),14,out)
        for domain in domains:
            scripts={x["script"] for x in out["requests"] if x["domain"]==domain}
            for script in ("CJK","ARABIC","CYRILLIC","DEVANAGARI"):
                self.assertIn(script,scripts,(domain,scripts))
        self.assertTrue(out["nonlatin_selected"])

    def test_router_plan_is_open_web_only_and_content_addressed(self):
        federation=fed.compile_federation(self.queries(),max_queries_per_source=8)
        plan=gate.compile_router_plan(self.base_program(),federation)
        self.assertEqual(plan["action_count"],len(federation["requests"]))
        self.assertEqual(len({x["action_id"] for x in plan["actions"]}),plan["action_count"])
        self.assertTrue(all(x["surface"]=="OPEN_WEB" for x in plan["actions"]))
        self.assertEqual(len(plan["plan_sha256"]),64)

    def test_actual_verified_router_contract_accepts_v4_actions_with_fake_provider(self):
        plan=gate.compile_router_plan(self.base_program(),fed.compile_federation(self.queries(),max_queries_per_source=8))
        sub=gate.router_subprogram(self.base_program(),plan)
        state=core.initial_state(sub)
        def fake(action):
            return {"backend_id":"FAKE_PUBLIC_WEB","candidates":[],"complete":False,"independently_complete":False}
        receipts=[]
        for action in plan["actions"]:
            result=router.execute_action(sub,state,action,fake)
            state=result["state"]
            receipts.append({"action_id":action["action_id"],"router_status":result["status"],"acceptance_credit":result["acceptance_credit"]})
        verdict=gate.evaluate(plan,receipts)
        self.assertTrue(verdict["pass"],verdict)
        self.assertTrue(verdict["epoch_consumption_authorized"],verdict)
        self.assertFalse(verdict["nonexistence_claim_authorized"],verdict)
        self.assertEqual(verdict["acceptance_credit"],0)

    def test_missing_receipt_blocks_epoch_consumption(self):
        plan=gate.compile_router_plan(self.base_program(),fed.compile_federation([{"text":"valid_route_top1","basis":"OBSERVABLE_API_SYMBOLS"}],max_queries_per_source=1))
        receipts=[{"action_id":x["action_id"],"router_status":"BACKEND_EXECUTED","acceptance_credit":0} for x in plan["actions"][:-1]]
        out=gate.evaluate(plan,receipts)
        self.assertFalse(out["pass"],out)
        self.assertFalse(out["epoch_consumption_authorized"],out)
        self.assertTrue(any(x.startswith("MISSING_ROUTER_RECEIPTS:") for x in out["errors"]),out)

    def test_unbound_backend_does_not_count_as_attempt(self):
        plan=gate.compile_router_plan(self.base_program(),fed.compile_federation([{"text":"valid_route_top1","basis":"OBSERVABLE_API_SYMBOLS"}],max_queries_per_source=1))
        receipts=[{"action_id":x["action_id"],"router_status":"BACKEND_UNBOUND","acceptance_credit":0} for x in plan["actions"]]
        out=gate.evaluate(plan,receipts)
        self.assertFalse(out["pass"],out)
        self.assertFalse(out["epoch_consumption_authorized"],out)
        self.assertTrue(any(x.startswith("RECEIPT_NOT_ATTEMPTED:") for x in out["errors"]),out)

    def test_failed_attempts_can_consume_epoch_but_never_prove_nonexistence(self):
        plan=gate.compile_router_plan(self.base_program(),fed.compile_federation([{"text":"valid_route_top1","basis":"OBSERVABLE_API_SYMBOLS"}],max_queries_per_source=1))
        receipts=[{"action_id":x["action_id"],"router_status":"BACKEND_FAILED_TRANSIENT","acceptance_credit":0} for x in plan["actions"]]
        out=gate.evaluate(plan,receipts)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["epoch_consumption_authorized"],out)
        self.assertFalse(out["nonexistence_claim_authorized"],out)
        self.assertFalse(out["complete"],out)


if __name__=="__main__":
    unittest.main(verbosity=2)
