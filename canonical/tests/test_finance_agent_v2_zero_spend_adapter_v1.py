from __future__ import annotations

import asyncio
import types
import unittest

from canonical.runtime import finance_agent_v2_zero_spend_adapter_v1 as a
from canonical.runtime import zero_spend_provider_guard_v1 as g


def snap(provider: str):
    return {
        "provider_id": provider,
        "receipt_verified": True,
        "snapshot_fresh": True,
        "free_plan_active": True,
        "paid_fallback_enabled": False,
        "overage_enabled": False,
        "billing_charge_path_enabled": False,
        "incremental_spend_usd": 0,
        "account_hash": provider + "-account-0123456789abcdef",
        "snapshot_hash": provider + "-snapshot-0123456789abcdef",
    }


def safe_outcome(provider_id, call_id, result, exc):
    return {
        "provider_id": provider_id,
        "call_id": call_id,
        "paid_charge_observed": False,
        "quota_exhausted": False,
        "payment_required": False,
        "overage_observed": False,
        "observed_cost_usd": 0,
    }


class FakeContext:
    def __init__(self, result=None, exc=None):
        self.result = result if result is not None else object()
        self.exc = exc
        self.exit_calls = 0
    async def __aenter__(self):
        if self.exc:
            raise self.exc
        return self.result
    async def __aexit__(self, exc_type, exc, tb):
        self.exit_calls += 1
        return False


class FakeSession:
    get_calls = []
    post_calls = []
    last_context = None
    def get(self, url, *args, **kwargs):
        self.__class__.get_calls.append(str(url))
        ctx = FakeContext(result={"url": str(url)})
        self.__class__.last_context = ctx
        return ctx
    def post(self, url, *args, **kwargs):
        self.__class__.post_calls.append(str(url))
        ctx = FakeContext(result={"url": str(url)})
        self.__class__.last_context = ctx
        return ctx


class FakeTavilyClient:
    def __init__(self):
        self.calls = 0
    async def search(self, *args, **kwargs):
        self.calls += 1
        return {"results": [{"ok": True}]}


class FakeWebSearch:
    name = "web_search"
    def __init__(self):
        self.client = FakeTavilyClient()


def tools_module():
    return types.SimpleNamespace(
        aiohttp=types.SimpleNamespace(ClientSession=FakeSession)
    )


class Tests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeSession.get_calls = []
        FakeSession.post_calls = []
        self.mod = tools_module()
        self.web = FakeWebSearch()
        self.snapshots = {p: snap(p) for p in ("tavily", "sec_api", "tiingo")}
        FakeSession.last_context = None
        self.out = a.install_adapter(
            tools_module=self.mod,
            tool_instances=[self.web],
            snapshots=self.snapshots,
            outcome_observer=safe_outcome,
        )
        self.state = self.out["state"]

    async def asyncTearDown(self):
        self.out["restore"]()

    async def test_tavily_each_attempt_guarded_and_observed(self):
        await self.web.client.search(query="x")
        await self.web.client.search(query="y")
        x = self.state.ledger("tavily")
        self.assertEqual((x.attempted_calls, x.observed_calls), (2, 2))

    async def test_sec_and_tiingo_lower_level_requests_are_guarded(self):
        s = self.mod.aiohttp.ClientSession()
        async with s.post("https://api.sec-api.io/full-text-search") as _:
            pass
        async with s.post("https://api.sec-api.io/full-text-search") as _:
            pass
        async with s.get("https://api.tiingo.com/tiingo/daily/AAPL/prices") as _:
            pass
        self.assertEqual(self.state.ledger("sec_api").attempted_calls, 2)
        self.assertEqual(self.state.ledger("sec_api").observed_calls, 2)
        self.assertEqual(self.state.ledger("tiingo").attempted_calls, 1)
        self.assertEqual(self.state.ledger("tiingo").observed_calls, 1)

    async def test_unrelated_aiohttp_request_not_counted(self):
        s = self.mod.aiohttp.ClientSession()
        async with s.get("https://www.sec.gov/Archives/example") as _:
            pass
        self.assertEqual(self.state.ledger("sec_api").attempted_calls, 0)
        self.assertEqual(self.state.ledger("tiingo").attempted_calls, 0)

    async def test_finalize_zero_trip_run(self):
        await self.web.client.search(query="x")
        s = self.mod.aiohttp.ClientSession()
        async with s.post("https://api.sec-api.io/full-text-search") as _:
            pass
        async with s.get("https://api.tiingo.com/tiingo/daily/AAPL/prices") as _:
            pass
        out = self.state.finalize(evaluation_completed=True)
        self.assertTrue(out["score_eligibility_zero_spend_gate"])

    async def test_quota_trip_fails_closed(self):
        async def bad(provider_id, call_id, result, exc):
            out = dict(safe_outcome(provider_id, call_id, result, exc))
            if provider_id == "tavily":
                out["quota_exhausted"] = True
            return out
        self.out["restore"]()
        self.out = a.install_adapter(
            tools_module=self.mod,
            tool_instances=[self.web],
            snapshots={p: snap(p) for p in ("tavily", "sec_api", "tiingo")},
            outcome_observer=bad,
        )
        self.state = self.out["state"]
        with self.assertRaises(g.ZeroSpendBlocked):
            await self.web.client.search(query="x")
        self.assertEqual(self.state.ledger("tavily").guard_trip_count, 1)

    async def test_missing_snapshot_blocks_install(self):
        self.out["restore"]()
        with self.assertRaises(g.ZeroSpendBlocked):
            a.install_adapter(
                tools_module=self.mod,
                tool_instances=[FakeWebSearch()],
                snapshots={"tavily": snap("tavily"), "sec_api": snap("sec_api")},
                outcome_observer=safe_outcome,
            )
        self.out = {"restore": lambda: None}

    async def test_exactly_one_tavily_boundary_required(self):
        self.out["restore"]()
        with self.assertRaises(g.ZeroSpendBlocked):
            a.install_adapter(
                tools_module=self.mod,
                tool_instances=[],
                snapshots={p: snap(p) for p in ("tavily", "sec_api", "tiingo")},
                outcome_observer=safe_outcome,
            )
        self.out = {"restore": lambda: None}

    async def test_restore_restores_http_methods(self):
        before_get = self.mod.aiohttp.ClientSession.get
        self.out["restore"]()
        after_get = self.mod.aiohttp.ClientSession.get
        self.assertIsNot(before_get, after_get)
        self.out = {"restore": lambda: None}


    async def test_invalidated_snapshot_blocks_before_tavily_provider_call(self):
        self.snapshots["tavily"]["paid_fallback_enabled"] = True
        with self.assertRaises(g.ZeroSpendBlocked):
            await self.web.client.search(query="must-not-run")
        self.assertEqual(self.web.client.calls, 0)
        self.assertEqual(self.state.ledger("tavily").attempted_calls, 0)

    async def test_http_context_is_closed_when_post_response_observer_fails_closed(self):
        async def quota_trip(provider_id, call_id, result, exc):
            out = dict(safe_outcome(provider_id, call_id, result, exc))
            if provider_id == "sec_api":
                out["quota_exhausted"] = True
            return out
        self.out["restore"]()
        self.out = a.install_adapter(
            tools_module=self.mod,
            tool_instances=[self.web],
            snapshots={p: snap(p) for p in ("tavily", "sec_api", "tiingo")},
            outcome_observer=quota_trip,
        )
        self.state = self.out["state"]
        session = self.mod.aiohttp.ClientSession()
        with self.assertRaises(g.ZeroSpendBlocked):
            async with session.post("https://api.sec-api.io/full-text-search") as _:
                pass
        self.assertIsNotNone(FakeSession.last_context)
        self.assertEqual(FakeSession.last_context.exit_calls, 1)
        self.assertEqual(self.state.ledger("sec_api").guard_trip_count, 1)

    async def test_host_suffix_spoof_is_not_reclassified_as_provider_call(self):
        session = self.mod.aiohttp.ClientSession()
        async with session.post("https://api.sec-api.io.evil.example/full-text-search") as _:
            pass
        self.assertEqual(self.state.ledger("sec_api").attempted_calls, 0)


class OriginalTavilyTool:
    name = "web_search"
    def __init__(self):
        self.client = FakeTavilyClient()


class PreGetAgentIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_pre_get_agent_patch_preserves_construction_and_guards_calls(self):
        mod = tools_module()
        get_agent_mod = types.SimpleNamespace(TavilyWebSearch=OriginalTavilyTool)
        original_cls = get_agent_mod.TavilyWebSearch
        out = a.install_before_get_agent(
            get_agent_module=get_agent_mod,
            tools_module=mod,
            snapshots={p: snap(p) for p in ("tavily", "sec_api", "tiingo")},
            outcome_observer=safe_outcome,
        )
        try:
            tool = get_agent_mod.TavilyWebSearch()
            self.assertIsInstance(tool, OriginalTavilyTool)
            await tool.client.search(query="x")
            await tool.client.search(query="y")
            self.assertEqual(out["state"].ledger("tavily").attempted_calls, 2)
            self.assertEqual(out["state"].ledger("tavily").observed_calls, 2)

            sess = mod.aiohttp.ClientSession()
            async with sess.post("https://api.sec-api.io/full-text-search") as _:
                pass
            async with sess.get("https://api.tiingo.com/tiingo/daily/AAPL/prices") as _:
                pass
            self.assertEqual(out["state"].ledger("sec_api").attempted_calls, 1)
            self.assertEqual(out["state"].ledger("tiingo").attempted_calls, 1)
        finally:
            out["restore"]()
        self.assertIs(get_agent_mod.TavilyWebSearch, original_cls)

    async def test_pre_get_agent_missing_class_fails_closed(self):
        mod = tools_module()
        with self.assertRaises(g.ZeroSpendBlocked):
            a.install_before_get_agent(
                get_agent_module=types.SimpleNamespace(),
                tools_module=mod,
                snapshots={p: snap(p) for p in ("tavily", "sec_api", "tiingo")},
                outcome_observer=safe_outcome,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
