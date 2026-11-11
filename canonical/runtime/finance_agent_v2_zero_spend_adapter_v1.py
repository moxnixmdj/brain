from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Mapping, MutableMapping, Sequence
from urllib.parse import urlparse

from canonical.runtime import zero_spend_provider_guard_v1 as guard

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_ZERO_SPEND_ADAPTER_V1"

OutcomeObserver = Callable[[str, str, Any | None, BaseException | None], Mapping[str, Any] | Awaitable[Mapping[str, Any]]]

@dataclass
class ProviderLedger:
    attempted_calls: int = 0
    observed_calls: int = 0
    guard_trip_count: int = 0
    quota_exhaustion_count: int = 0
    payment_required_count: int = 0
    paid_charge_count: int = 0
    observed_cost_usd: str = "0"

@dataclass
class AdapterState:
    snapshots: Mapping[str, Mapping[str, Any]]
    outcome_observer: OutcomeObserver
    ledgers: MutableMapping[str, ProviderLedger] = field(default_factory=dict)
    next_call_number: int = 1

    def ledger(self, provider_id: str) -> ProviderLedger:
        return self.ledgers.setdefault(provider_id, ProviderLedger())

    def new_call_id(self, provider_id: str) -> str:
        cid = f"{provider_id}:{self.next_call_number}"
        self.next_call_number += 1
        return cid

    async def observe(self, provider_id: str, call_id: str, result: Any | None, exc: BaseException | None) -> None:
        raw = self.outcome_observer(provider_id, call_id, result, exc)
        if hasattr(raw, "__await__"):
            raw = await raw  # type: ignore[assignment]
        if not isinstance(raw, Mapping):
            raise guard.ZeroSpendBlocked("OUTCOME_OBSERVER_MUST_RETURN_MAPPING")
        ledger = self.ledger(provider_id)
        try:
            receipt = guard.observe_call(
                self.snapshots[provider_id],
                provider_id=provider_id,
                call_id=call_id,
                outcome=raw,
            )
        except guard.ZeroSpendBlocked:
            ledger.guard_trip_count += 1
            if raw.get("quota_exhausted") is True:
                ledger.quota_exhaustion_count += 1
            if raw.get("payment_required") is True:
                ledger.payment_required_count += 1
            if raw.get("paid_charge_observed") is True:
                ledger.paid_charge_count += 1
            raise
        ledger.observed_calls += 1
        ledger.observed_cost_usd = str(receipt.get("incremental_spend_usd", 0))

    def authorize(self, provider_id: str, call_id: str) -> None:
        if provider_id not in self.snapshots:
            raise guard.ZeroSpendBlocked("PROVIDER_ACCOUNT_SNAPSHOT_MISSING:" + provider_id)
        guard.authorize_call(self.snapshots[provider_id], provider_id=provider_id, call_id=call_id)
        self.ledger(provider_id).attempted_calls += 1

    def summaries(self, required_provider_ids: Sequence[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for provider_id in required_provider_ids:
            x = self.ledger(provider_id)
            out.append({
                "provider_id": provider_id,
                "attempted_calls": x.attempted_calls,
                "observed_calls": x.observed_calls,
                "all_calls_guarded": True,
                "guard_trip_count": x.guard_trip_count,
                "quota_exhaustion_count": x.quota_exhaustion_count,
                "payment_required_count": x.payment_required_count,
                "paid_charge_count": x.paid_charge_count,
                "observed_cost_usd": x.observed_cost_usd,
            })
        return out

    def finalize(self, *, evaluation_completed: bool) -> dict[str, Any]:
        required = ("tavily", "sec_api", "tiingo")
        return guard.finalize_run(
            self.summaries(required),
            required_provider_ids=required,
            evaluation_completed=evaluation_completed,
        )


def _provider_for_url(url: Any) -> str | None:
    host = (urlparse(str(url)).hostname or "").lower()
    if host == "api.sec-api.io":
        return "sec_api"
    if host == "api.tiingo.com":
        return "tiingo"
    return None


class _GuardedRequestContext:
    def __init__(self, inner: Any, state: AdapterState, provider_id: str, call_id: str):
        self._inner = inner
        self._state = state
        self._provider_id = provider_id
        self._call_id = call_id

    async def __aenter__(self) -> Any:
        try:
            result = await self._inner.__aenter__()
        except BaseException as exc:
            await self._state.observe(self._provider_id, self._call_id, None, exc)
            raise
        try:
            await self._state.observe(self._provider_id, self._call_id, result, None)
        except BaseException:
            # If the post-response observer fails closed (quota/payment/overage/cost
            # signal, malformed evidence, etc.), exit the already-entered provider
            # response context before propagating the guard failure. Otherwise the
            # abort path can leak an open HTTP response/connection.
            exc = __import__("sys").exc_info()
            try:
                await self._inner.__aexit__(*exc)
            finally:
                raise
        return result

    async def __aexit__(self, exc_type: Any, exc: BaseException | None, tb: Any) -> Any:
        return await self._inner.__aexit__(exc_type, exc, tb)


def install_adapter(
    *,
    tools_module: Any,
    tool_instances: Sequence[Any],
    snapshots: Mapping[str, Mapping[str, Any]],
    outcome_observer: OutcomeObserver,
) -> dict[str, Any]:
    """
    Patch the exact Finance Agent v2 provider boundaries:
      - TavilyWebSearch.client.search
      - aiohttp.ClientSession.get/post only when host is api.sec-api.io or api.tiingo.com

    This placement is below the benchmark's retry decorators, so every provider attempt,
    including retries, crosses the guard.
    """
    state = AdapterState(snapshots=snapshots, outcome_observer=outcome_observer)

    for provider_id in ("tavily", "sec_api", "tiingo"):
        if provider_id not in snapshots:
            raise guard.ZeroSpendBlocked("PROVIDER_ACCOUNT_SNAPSHOT_MISSING:" + provider_id)
        guard.validate_account_snapshot(snapshots[provider_id], provider_id=provider_id)

    tavily_wrapped = 0
    tavily_restores: list[tuple[Any, Any]] = []
    for tool in tool_instances:
        if getattr(tool, "name", None) != "web_search":
            continue
        client = getattr(tool, "client", None)
        original_search = getattr(client, "search", None)
        if original_search is None or not callable(original_search):
            raise guard.ZeroSpendBlocked("TAVILY_SEARCH_BOUNDARY_MISSING")

        async def guarded_search(*args: Any, __orig=original_search, **kwargs: Any) -> Any:
            call_id = state.new_call_id("tavily")
            state.authorize("tavily", call_id)
            try:
                result = await __orig(*args, **kwargs)
            except BaseException as exc:
                await state.observe("tavily", call_id, None, exc)
                raise
            await state.observe("tavily", call_id, result, None)
            return result

        client.search = guarded_search
        tavily_restores.append((client, original_search))
        tavily_wrapped += 1

    if tavily_wrapped != 1:
        raise guard.ZeroSpendBlocked(f"EXPECTED_EXACTLY_ONE_TAVILY_TOOL_GOT_{tavily_wrapped}")

    session_cls = tools_module.aiohttp.ClientSession
    original_get = session_cls.get
    original_post = session_cls.post

    def wrap_http(original: Callable[..., Any]) -> Callable[..., Any]:
        def wrapped(session_self: Any, url: Any, *args: Any, **kwargs: Any) -> Any:
            provider_id = _provider_for_url(url)
            if provider_id is None:
                return original(session_self, url, *args, **kwargs)
            call_id = state.new_call_id(provider_id)
            state.authorize(provider_id, call_id)
            inner = original(session_self, url, *args, **kwargs)
            return _GuardedRequestContext(inner, state, provider_id, call_id)
        return wrapped

    session_cls.get = wrap_http(original_get)
    session_cls.post = wrap_http(original_post)

    return {
        "schema": SCHEMA,
        "status": "PASS__FINANCE_AGENT_PROVIDER_BOUNDARIES_GUARDED",
        "state": state,
        "restore": lambda: _restore_all(session_cls, original_get, original_post, tavily_restores),
        "covered_boundaries": [
            "TavilyWebSearch.client.search",
            "aiohttp.ClientSession.post@api.sec-api.io",
            "aiohttp.ClientSession.get@api.tiingo.com",
        ],
        "incremental_spend_usd": 0,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
    }


def _restore_all(
    session_cls: Any,
    original_get: Any,
    original_post: Any,
    tavily_restores: Sequence[tuple[Any, Any]],
) -> None:
    session_cls.get = original_get
    session_cls.post = original_post
    for client, original_search in tavily_restores:
        client.search = original_search


def install_before_get_agent(
    *,
    get_agent_module: Any,
    tools_module: Any,
    snapshots: Mapping[str, Mapping[str, Any]],
    outcome_observer: OutcomeObserver,
) -> dict[str, Any]:
    """
    Install the zero-spend guard before invoking the unmodified first-party
    finance_agent.get_agent.get_agent function.

    The get_agent module constructs TavilyWebSearch from its module-global class.
    Replacing only that class with a behavior-preserving guarded subclass lets the
    original harness create the tool normally while ensuring every underlying
    Tavily client.search attempt is guarded. SEC API and Tiingo remain covered at
    their aiohttp request boundaries, below retry decorators.
    """
    state = AdapterState(snapshots=snapshots, outcome_observer=outcome_observer)
    for provider_id in ("tavily", "sec_api", "tiingo"):
        if provider_id not in snapshots:
            raise guard.ZeroSpendBlocked("PROVIDER_ACCOUNT_SNAPSHOT_MISSING:" + provider_id)
        guard.validate_account_snapshot(snapshots[provider_id], provider_id=provider_id)

    original_tavily_cls = getattr(get_agent_module, "TavilyWebSearch", None)
    if original_tavily_cls is None:
        raise guard.ZeroSpendBlocked("GET_AGENT_TAVILY_CLASS_MISSING")

    class GuardedTavilyWebSearch(original_tavily_cls):  # type: ignore[misc,valid-type]
        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, **kwargs)
            original_search = getattr(self.client, "search", None)
            if original_search is None or not callable(original_search):
                raise guard.ZeroSpendBlocked("TAVILY_SEARCH_BOUNDARY_MISSING")

            async def guarded_search(*a: Any, **kw: Any) -> Any:
                call_id = state.new_call_id("tavily")
                state.authorize("tavily", call_id)
                try:
                    result = await original_search(*a, **kw)
                except BaseException as exc:
                    await state.observe("tavily", call_id, None, exc)
                    raise
                await state.observe("tavily", call_id, result, None)
                return result

            self.client.search = guarded_search

    GuardedTavilyWebSearch.__name__ = getattr(original_tavily_cls, "__name__", "TavilyWebSearch")
    GuardedTavilyWebSearch.__qualname__ = getattr(original_tavily_cls, "__qualname__", "TavilyWebSearch")
    get_agent_module.TavilyWebSearch = GuardedTavilyWebSearch

    session_cls = tools_module.aiohttp.ClientSession
    original_get = session_cls.get
    original_post = session_cls.post

    def wrap_http(original: Callable[..., Any]) -> Callable[..., Any]:
        def wrapped(session_self: Any, url: Any, *args: Any, **kwargs: Any) -> Any:
            provider_id = _provider_for_url(url)
            if provider_id is None:
                return original(session_self, url, *args, **kwargs)
            call_id = state.new_call_id(provider_id)
            state.authorize(provider_id, call_id)
            inner = original(session_self, url, *args, **kwargs)
            return _GuardedRequestContext(inner, state, provider_id, call_id)
        return wrapped

    session_cls.get = wrap_http(original_get)
    session_cls.post = wrap_http(original_post)

    def restore() -> None:
        session_cls.get = original_get
        session_cls.post = original_post
        get_agent_module.TavilyWebSearch = original_tavily_cls

    return {
        "schema": SCHEMA,
        "status": "PASS__PRE_GET_AGENT_PROVIDER_BOUNDARIES_GUARDED",
        "state": state,
        "restore": restore,
        "covered_boundaries": [
            "get_agent_module.TavilyWebSearch->client.search",
            "aiohttp.ClientSession.post@api.sec-api.io",
            "aiohttp.ClientSession.get@api.tiingo.com",
        ],
        "incremental_spend_usd": 0,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
    }
