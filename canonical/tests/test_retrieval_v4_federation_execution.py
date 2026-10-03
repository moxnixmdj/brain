#!/usr/bin/env python3
from __future__ import annotations
import unittest

from canonical.runtime import public_source_federation_v2 as f2
from canonical.runtime import public_source_federation_executor_v1 as ex


class RetrievalV4FederationTests(unittest.TestCase):
    def queries(self):
        rows=[{"text":f"generic english query {i}","basis":"RESIDUAL_EFFECT"} for i in range(12)]
        rows += [
            {"text":"valid_route_top1","basis":"OBSERVABLE_API_SYMBOLS"},
            {"text":"工具发现 Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
            {"text":"اكتشاف الأدوات Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
            {"text":"обнаружение инструментов Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
            {"text":"descubrimiento de herramientas Toolathlon","basis":"MULTILINGUAL_BRIDGE_VARIANT"},
        ]
        return rows

    def test_default_budget_preserves_technical_and_cross_script_queries(self):
        selected=f2.select_queries(self.queries(),max_queries=8)
        texts={x["text"] for x in selected}
        scripts={x["script"] for x in selected}
        self.assertIn("valid_route_top1",texts)
        self.assertIn("CJK",scripts)
        self.assertIn("ARABIC",scripts)
        self.assertIn("CYRILLIC",scripts)
        self.assertLessEqual(len(selected),8)

    def test_multilingual_queries_reach_every_federated_source(self):
        out=f2.compile_federation(self.queries(),max_queries_per_source=8)
        self.assertTrue(out["nonlatin_available"],out)
        self.assertTrue(out["nonlatin_selected"],out)
        domains={x["domain"] for x in out["requests"]}
        self.assertGreaterEqual(len(domains),14)
        for domain in domains:
            rows=[x for x in out["requests"] if x["domain"]==domain]
            scripts={x["script"] for x in rows}
            self.assertIn("CJK",scripts,(domain,scripts))
            self.assertIn("ARABIC",scripts,(domain,scripts))
            self.assertIn("CYRILLIC",scripts,(domain,scripts))

    def test_first_execution_wave_covers_each_source_once(self):
        fed=f2.compile_federation(self.queries(),max_queries_per_source=8)
        wave=ex.plan_wave(fed["requests"],wave_size=14)
        self.assertEqual(len(wave),14)
        self.assertEqual(len({x["domain"] for x in wave}),14)

    def test_executor_records_empty_and_failure_as_unknown(self):
        fed=f2.compile_federation(self.queries(),max_queries_per_source=2)
        calls=[]
        def fake(query,limit=8,timeout=12,query_override=None):
            calls.append(query)
            if "site:github.com" in query:
                return {"status":"CANDIDATES_DISCOVERED","candidates":[
                    {"url":"https://github.com/example/repo","title":"hit"},
                    {"url":"https://evil.invalid/offdomain","title":"off"}
                ]}
            if "site:gitlab.com" in query:
                raise RuntimeError("temporary")
            return {"status":"DISCOVERY_UNAVAILABLE","candidates":[]}
        out=ex.execute(fed,discover_fn=fake,wave_size=14)
        self.assertFalse(out["complete"])
        self.assertFalse(out["nonexistence_claim_authorized"])
        self.assertEqual(out["acceptance_credit"],0)
        self.assertTrue(any(x["state"]=="QUERIED_NO_CANDIDATE__UNKNOWN" for x in out["traces"]),out)
        self.assertTrue(any(x["state"]=="FAILED_TRANSIENT__UNKNOWN" for x in out["traces"]),out)
        self.assertTrue(any(x["url"]=="https://github.com/example/repo" for x in out["candidates"]),out)
        self.assertFalse(any("evil.invalid" in x["url"] for x in out["candidates"]),out)

    def test_consumed_requests_are_not_replayed(self):
        fed=f2.compile_federation(self.queries(),max_queries_per_source=2)
        first=ex.plan_wave(fed["requests"],wave_size=14)
        consumed=[x["request_id"] for x in first]
        second=ex.plan_wave(fed["requests"],consumed_request_ids=consumed,wave_size=14)
        self.assertFalse(set(consumed)&{x["request_id"] for x in second})
        self.assertEqual(len({x["domain"] for x in second}),14)

    def test_epoch_is_content_addressed_and_deterministic(self):
        fed=f2.compile_federation([{"text":"valid_route_top1","basis":"OBSERVABLE_API_SYMBOLS"}],max_queries_per_source=1)
        def fake(query,limit=8,timeout=12,query_override=None):
            domain=query.split()[0][5:]
            return {"status":"CANDIDATES_DISCOVERED","candidates":[{"url":f"https://{domain}/x","title":"x"}]}
        a=ex.execute(fed,discover_fn=fake,wave_size=14)
        b=ex.execute(fed,discover_fn=fake,wave_size=14)
        self.assertEqual(a["source_epoch_sha256"],b["source_epoch_sha256"])
        self.assertEqual(a["remaining_request_count"],0)
        self.assertFalse(a["nonexistence_claim_authorized"])


if __name__=="__main__":
    unittest.main(verbosity=2)
