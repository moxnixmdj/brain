from __future__ import annotations

import asyncio
import unittest

from canonical.runtime import finance_agent_v2_zero_spend_harness_adapter_v1 as a
from canonical.runtime import zero_spend_provider_guard_v1 as g

def snap(provider: str, **kw):
    x={
      "provider_id":provider,
      "receipt_verified":True,
      "snapshot_fresh":True,
      "free_plan_active":True,
      "paid_fallback_enabled":False,
      "overage_enabled":False,
      "billing_charge_path_enabled":False,
      "incremental_spend_usd":0,
      "account_hash":"0123456789abcdef0123456789abcdef",
      "snapshot_hash":"fedcba9876543210fedcba9876543210",
    }
    x.update(kw)
    return x

class Exc(Exception):
    def __init__(self,status):
        self.status=status

class FakeTavily:
    def __init__(self, *, status=200):
        self.status=status
    async def search(self,*args,**kwargs):
        if self.status != 200:
            raise Exc(self.status)
        return {"results":[{"ok":True}]}

class FakeResponse:
    def __init__(self,status=200,payload=None):
        self.status=status
        self.payload=payload if payload is not None else {"filings":[]}
    def raise_for_status(self):
        if self.status >= 400:
            raise Exc(self.status)
    async def json(self):
        return self.payload

class FakeRequestContext:
    def __init__(self,response):
        self.response=response
    async def __aenter__(self):
        return self.response
    async def __aexit__(self,*args):
        return False

class FakeSession:
    def __init__(self,status=200):
        self.status=status
    async def __aenter__(self):
        return self
    async def __aexit__(self,*args):
        return False
    def get(self,url,*args,**kwargs):
        return FakeRequestContext(FakeResponse(self.status))
    def post(self,url,*args,**kwargs):
        return FakeRequestContext(FakeResponse(self.status))

class Tests(unittest.TestCase):
    def test_url_classification_is_exact_to_billable_hosts(self):
        self.assertEqual(a._provider_for_url("https://api.sec-api.io/full-text-search"),"sec_api")
        self.assertEqual(a._provider_for_url("https://api.tiingo.com/tiingo/daily/AAPL/prices"),"tiingo")
        self.assertIsNone(a._provider_for_url("https://www.sec.gov/Archives/x"))
        self.assertIsNone(a._provider_for_url("https://example.com/api.tiingo.com.evil"))
        self.assertIsNone(a._provider_for_url("https://example.com/path/api.tiingo.com/prices"))

    def test_tavily_success_is_guarded_and_observed(self):
        audit=a.ProviderAudit(lambda p:snap(p))
        proxy=a._TavilyClientProxy(FakeTavily(),audit)
        out=asyncio.run(proxy.search(query="x"))
        self.assertEqual(out["results"][0]["ok"],True)
        s={x["provider_id"]:x for x in audit.summaries()}
        self.assertEqual((s["tavily"]["attempted_calls"],s["tavily"]["observed_calls"]),(1,1))
        self.assertEqual(s["tavily"]["guard_trip_count"],0)

    def test_tavily_429_fails_closed(self):
        audit=a.ProviderAudit(lambda p:snap(p))
        proxy=a._TavilyClientProxy(FakeTavily(status=429),audit)
        with self.assertRaises(g.ZeroSpendBlocked):
            asyncio.run(proxy.search(query="x"))

    def test_aiohttp_sec_and_tiingo_each_guard_actual_request_context(self):
        async def run():
            audit=a.ProviderAudit(lambda p:snap(p))
            sec=a._ClientSessionProxy(FakeSession(),audit)
            async with sec.post("https://api.sec-api.io/full-text-search") as response:
                self.assertEqual(response.status,200)
            tiingo=a._ClientSessionProxy(FakeSession(),audit)
            async with tiingo.get("https://api.tiingo.com/tiingo/daily/AAPL/prices") as response:
                self.assertEqual(response.status,200)
            summaries={x["provider_id"]:x for x in audit.summaries()}
            self.assertEqual(summaries["sec_api"]["attempted_calls"],1)
            self.assertEqual(summaries["sec_api"]["observed_calls"],1)
            self.assertEqual(summaries["tiingo"]["attempted_calls"],1)
            self.assertEqual(summaries["tiingo"]["observed_calls"],1)
        asyncio.run(run())

    def test_nonprovider_aiohttp_request_is_not_counted(self):
        async def run():
            audit=a.ProviderAudit(lambda p:snap(p))
            session=a._ClientSessionProxy(FakeSession(),audit)
            async with session.get("https://www.sec.gov/Archives/test") as response:
                self.assertEqual(response.status,200)
            self.assertTrue(all(x["attempted_calls"]==0 for x in audit.summaries()))
        asyncio.run(run())

    def test_payment_or_quota_status_fails_closed_before_response_reaches_tool(self):
        for status in (402,429):
            async def run(status=status):
                audit=a.ProviderAudit(lambda p:snap(p))
                session=a._ClientSessionProxy(FakeSession(status=status),audit)
                async with session.get("https://api.tiingo.com/tiingo/daily/AAPL/prices"):
                    pass
            with self.assertRaises(g.ZeroSpendBlocked):
                asyncio.run(run())

    def test_snapshot_callback_is_reinvoked_per_network_call(self):
        calls=[]
        def provider(p):
            calls.append(p)
            return snap(p,snapshot_hash=f"snapshot-{len(calls):016d}")
        async def run():
            audit=a.ProviderAudit(provider)
            proxy=a._TavilyClientProxy(FakeTavily(),audit)
            await proxy.search(query="a")
            await proxy.search(query="b")
        asyncio.run(run())
        self.assertEqual(calls,["tavily","tavily"])

    def test_full_run_can_finalize_without_preproved_call_counts(self):
        audit=a.ProviderAudit(lambda p:snap(p))
        audit._stats["tavily"]["attempted_calls"]=700
        audit._stats["tavily"]["observed_calls"]=700
        audit._stats["sec_api"]["attempted_calls"]=80
        audit._stats["sec_api"]["observed_calls"]=80
        audit._stats["tiingo"]["attempted_calls"]=300
        audit._stats["tiingo"]["observed_calls"]=300
        out=audit.finalize(evaluation_completed=True)
        self.assertTrue(out["score_eligibility_zero_spend_gate"])

    def test_incomplete_run_never_finalizes(self):
        audit=a.ProviderAudit(lambda p:snap(p))
        with self.assertRaises(g.ZeroSpendBlocked):
            audit.finalize(evaluation_completed=False)

if __name__=="__main__":
    unittest.main(verbosity=2)
