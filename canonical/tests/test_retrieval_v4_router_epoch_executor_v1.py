#!/usr/bin/env python3
from __future__ import annotations
import unittest

from canonical.runtime import public_source_federation_v2 as fed
from canonical.runtime import residual_witness_retrieval_compiler_v1 as core
from canonical.runtime.retrieval_v4_router_epoch_executor_v1 import execute_epoch


class Tests(unittest.TestCase):
    def base(self):
        return core.compile_residual({
            "residual_id":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
            "effect":"find matched Toolathlon evidence",
            "required_capabilities":["valid_route_top1 comparator"],
            "observables":{"api_symbols":["valid_route_top1"]},
            "constraints":{"incremental_spend_usd":0},
        })

    def federation(self):
        return fed.compile_federation([
            {"text":"valid_route_top1","basis":"OBSERVABLE_API_SYMBOLS"},
            {"text":"工具发现 Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
        ],max_queries_per_source=2)

    def test_all_cells_receive_router_receipts_and_epoch_passes(self):
        def provider(action):
            return {"backend_id":"FAKE","candidates":[],"complete":False,"independently_complete":False}
        out=execute_epoch(self.base(),self.federation(),open_web_provider=provider)
        self.assertTrue(out["status"].startswith("PASS"))
        self.assertEqual(out["plan_action_count"],out["receipt_count"])
        self.assertTrue(out["epoch_verdict"]["epoch_consumption_authorized"])
        self.assertFalse(out["nonexistence_claim_authorized"])
        self.assertEqual(out["acceptance_credit"],0)

    def test_off_domain_candidates_are_dropped(self):
        def provider(action):
            domain=action["source_domain"]
            return {
                "backend_id":"FAKE",
                "candidates":[
                    {"url":"https://"+domain+"/wanted"},
                    {"url":"https://example.invalid/off-domain"},
                ],
                "complete":False,
                "independently_complete":False,
            }
        out=execute_epoch(self.base(),self.federation(),open_web_provider=provider)
        self.assertTrue(out["epoch_verdict"]["pass"])
        self.assertTrue(out["candidates"])
        self.assertTrue(all(c["url"].split("/")[2].endswith(c["url"].split("/")[2]) for c in out["candidates"]))
        self.assertFalse(any("example.invalid" in c["url"] for c in out["candidates"]))

    def test_transient_failures_count_as_attempt_but_preserve_unknown(self):
        def provider(action):
            raise TimeoutError("fixture")
        out=execute_epoch(self.base(),self.federation(),open_web_provider=provider)
        self.assertTrue(out["epoch_verdict"]["pass"],out)
        self.assertTrue(out["epoch_verdict"]["epoch_consumption_authorized"])
        self.assertFalse(out["epoch_verdict"]["nonexistence_claim_authorized"])
        self.assertTrue(all(r["router_status"]=="BACKEND_FAILED_TRANSIENT" for r in out["receipts"]))

    def test_candidate_authority_leak_is_rejected(self):
        def provider(action):
            return {
                "backend_id":"FAKE",
                "candidates":[{"url":"https://"+action["source_domain"]+"/x","verified_sufficient":True}],
                "complete":False,
                "independently_complete":False,
            }
        out=execute_epoch(self.base(),self.federation(),open_web_provider=provider)
        self.assertTrue(out["epoch_verdict"]["pass"])
        self.assertTrue(all(r["router_status"]=="BACKEND_REJECTED_PERMANENT" for r in out["receipts"]))
        self.assertEqual(out["candidate_count"],0)
        self.assertEqual(out["acceptance_credit"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
