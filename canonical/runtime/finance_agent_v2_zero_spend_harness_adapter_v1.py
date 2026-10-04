from __future__ import annotations

import hashlib
import inspect
import itertools
import threading
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any, Callable, Mapping

from canonical.runtime import zero_spend_provider_guard_v1 as zero_guard

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_ZERO_SPEND_HARNESS_ADAPTER_V1"
PINNED_TOOLS_GIT_BLOB_SHA = "19b85ce4e110e39f410c52b2efa0e33f651fa6d1"
PINNED_GET_AGENT_GIT_BLOB_SHA = "22c012241a430975266fb7f8d2fe7af8e9f1b8d4"
REQUIRED_PROVIDERS = ("tavily", "sec_api", "tiingo")

class HarnessAdapterBlocked(RuntimeError):
    pass

def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def _module_source_bytes(module: Any) -> bytes:
    source = inspect.getsourcefile(module) or getattr(module, "__file__", None)
    if not source:
        raise HarnessAdapterBlocked("MODULE_SOURCE_PATH_REQUIRED")
    path = Path(source)
    if not path.exists():
        raise HarnessAdapterBlocked("MODULE_SOURCE_NOT_FOUND")
    return path.read_bytes()

def verify_pinned_vals_modules(tools_module: Any, get_agent_module: Any) -> dict[str, Any]:
    tools_sha = _git_blob_sha(_module_source_bytes(tools_module))
    get_agent_sha = _git_blob_sha(_module_source_bytes(get_agent_module))
    if tools_sha != PINNED_TOOLS_GIT_BLOB_SHA:
        raise HarnessAdapterBlocked("VALS_TOOLS_SOURCE_DRIFT")
    if get_agent_sha != PINNED_GET_AGENT_GIT_BLOB_SHA:
        raise HarnessAdapterBlocked("VALS_GET_AGENT_SOURCE_DRIFT")
    for name in ("TavilyWebSearch", "EDGARSearch", "PriceHistory", "AsyncTavilyClient", "aiohttp"):
        if not hasattr(tools_module, name):
            raise HarnessAdapterBlocked("VALS_TOOLS_SHAPE_DRIFT:" + name)
    for name in ("get_agent", "TavilyWebSearch", "EDGARSearch", "PriceHistory"):
        if not hasattr(get_agent_module, name):
            raise HarnessAdapterBlocked("VALS_GET_AGENT_SHAPE_DRIFT:" + name)
    return {
        "schema": SCHEMA,
        "status": "PASS__PINNED_VALS_MODULES",
        "tools_git_blob_sha": tools_sha,
        "get_agent_git_blob_sha": get_agent_sha,
    }

def _status_from_exception(exc: BaseException) -> int | None:
    for value in (
        getattr(exc, "status", None),
        getattr(exc, "status_code", None),
        getattr(getattr(exc, "response", None), "status", None),
        getattr(getattr(exc, "response", None), "status_code", None),
    ):
        if isinstance(value, int):
            return value
    return None

def _provider_for_url(url: Any) -> str | None:
    try:
        host = (urlsplit(str(url)).hostname or "").lower()
    except Exception:
        return None
    if host == "api.sec-api.io":
        return "sec_api"
    if host == "api.tiingo.com":
        return "tiingo"
    return None

class ProviderAudit:
    def __init__(self, snapshot_provider: Callable[[str], Mapping[str, Any]]):
        if not callable(snapshot_provider):
            raise HarnessAdapterBlocked("SNAPSHOT_PROVIDER_REQUIRED")
        self._snapshot_provider = snapshot_provider
        self._sequence = itertools.count(1)
        self._lock = threading.Lock()
        self._stats = {
            provider: {
                "attempted_calls": 0,
                "observed_calls": 0,
                "guard_trip_count": 0,
                "quota_exhaustion_count": 0,
                "payment_required_count": 0,
                "paid_charge_count": 0,
                "observed_cost_usd": 0,
            }
            for provider in REQUIRED_PROVIDERS
        }

    def begin(self, provider_id: str) -> tuple[str, Mapping[str, Any]]:
        if provider_id not in self._stats:
            raise HarnessAdapterBlocked("UNKNOWN_PROVIDER:" + provider_id)
        snapshot = self._snapshot_provider(provider_id)
        call_id = f"{provider_id}:{next(self._sequence)}"
        try:
            zero_guard.authorize_call(snapshot, provider_id=provider_id, call_id=call_id)
        except Exception:
            with self._lock:
                self._stats[provider_id]["guard_trip_count"] += 1
            raise
        with self._lock:
            self._stats[provider_id]["attempted_calls"] += 1
        return call_id, snapshot

    def finish(
        self,
        provider_id: str,
        call_id: str,
        snapshot: Mapping[str, Any],
        *,
        status: int | None,
    ) -> dict[str, Any]:
        quota = status == 429
        payment = status == 402
        outcome = {
            "provider_id": provider_id,
            "call_id": call_id,
            "paid_charge_observed": False,
            "quota_exhausted": quota,
            "payment_required": payment,
            "overage_observed": False,
            "observed_cost_usd": 0,
        }
        try:
            result = zero_guard.observe_call(
                snapshot,
                provider_id=provider_id,
                call_id=call_id,
                outcome=outcome,
            )
        except Exception:
            with self._lock:
                stat = self._stats[provider_id]
                stat["observed_calls"] += 1
                stat["guard_trip_count"] += 1
                if quota:
                    stat["quota_exhaustion_count"] += 1
                if payment:
                    stat["payment_required_count"] += 1
            raise
        with self._lock:
            self._stats[provider_id]["observed_calls"] += 1
        return result

    def summaries(self) -> list[dict[str, Any]]:
        out = []
        with self._lock:
            for provider in REQUIRED_PROVIDERS:
                stat = dict(self._stats[provider])
                out.append({
                    "provider_id": provider,
                    **stat,
                    "all_calls_guarded": stat["attempted_calls"] == stat["observed_calls"]
                    and stat["guard_trip_count"] == 0,
                })
        return out

    def finalize(self, *, evaluation_completed: bool) -> dict[str, Any]:
        return zero_guard.finalize_run(
            self.summaries(),
            required_provider_ids=REQUIRED_PROVIDERS,
            evaluation_completed=evaluation_completed,
        )

class _TavilyClientProxy:
    def __init__(self, inner: Any, audit: ProviderAudit):
        self._inner = inner
        self._audit = audit

    async def search(self, *args: Any, **kwargs: Any) -> Any:
        call_id, snapshot = self._audit.begin("tavily")
        try:
            result = await self._inner.search(*args, **kwargs)
        except BaseException as exc:
            self._audit.finish(
                "tavily", call_id, snapshot, status=_status_from_exception(exc)
            )
            raise
        self._audit.finish("tavily", call_id, snapshot, status=200)
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

class _GuardedRequestContext:
    def __init__(self, inner: Any, audit: ProviderAudit, provider_id: str):
        self._inner = inner
        self._audit = audit
        self._provider_id = provider_id
        self._entered = False

    async def __aenter__(self) -> Any:
        call_id, snapshot = self._audit.begin(self._provider_id)
        try:
            response = await self._inner.__aenter__()
            self._entered = True
        except BaseException as exc:
            self._audit.finish(
                self._provider_id,
                call_id,
                snapshot,
                status=_status_from_exception(exc),
            )
            raise
        try:
            self._audit.finish(
                self._provider_id,
                call_id,
                snapshot,
                status=getattr(response, "status", None),
            )
        except BaseException as exc:
            try:
                await self._inner.__aexit__(type(exc), exc, exc.__traceback__)
            finally:
                self._entered = False
            raise
        return response

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> Any:
        self._entered = False
        return await self._inner.__aexit__(exc_type, exc, tb)

class _ClientSessionProxy:
    def __init__(self, inner: Any, audit: ProviderAudit):
        self._inner = inner
        self._audit = audit

    async def __aenter__(self) -> "_ClientSessionProxy":
        await self._inner.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> Any:
        return await self._inner.__aexit__(exc_type, exc, tb)

    def get(self, url: Any, *args: Any, **kwargs: Any) -> Any:
        inner = self._inner.get(url, *args, **kwargs)
        provider = _provider_for_url(url)
        return _GuardedRequestContext(inner, self._audit, provider) if provider else inner

    def post(self, url: Any, *args: Any, **kwargs: Any) -> Any:
        inner = self._inner.post(url, *args, **kwargs)
        provider = _provider_for_url(url)
        return _GuardedRequestContext(inner, self._audit, provider) if provider else inner

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

class _AiohttpProxy:
    def __init__(self, original: Any, audit: ProviderAudit):
        self._original = original
        self._audit = audit

    def ClientSession(self, *args: Any, **kwargs: Any) -> _ClientSessionProxy:
        return _ClientSessionProxy(
            self._original.ClientSession(*args, **kwargs), self._audit
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)

class Installation:
    def __init__(
        self,
        tools_module: Any,
        *,
        original_aiohttp: Any,
        original_tavily_ctor: Any,
        audit: ProviderAudit,
    ):
        self.tools_module = tools_module
        self.original_aiohttp = original_aiohttp
        self.original_tavily_ctor = original_tavily_ctor
        self.audit = audit
        self._restored = False

    def restore(self) -> None:
        if self._restored:
            return
        self.tools_module.aiohttp = self.original_aiohttp
        self.tools_module.AsyncTavilyClient = self.original_tavily_ctor
        if getattr(self.tools_module, "_brain_zero_spend_installation", None) is self:
            delattr(self.tools_module, "_brain_zero_spend_installation")
        self._restored = True

    def finalize(self, *, evaluation_completed: bool) -> dict[str, Any]:
        return self.audit.finalize(evaluation_completed=evaluation_completed)

def install(
    tools_module: Any,
    get_agent_module: Any,
    *,
    snapshot_provider: Callable[[str], Mapping[str, Any]],
) -> Installation:
    verify_pinned_vals_modules(tools_module, get_agent_module)
    if getattr(tools_module, "_brain_zero_spend_installation", None) is not None:
        raise HarnessAdapterBlocked("ADAPTER_ALREADY_INSTALLED")
    audit = ProviderAudit(snapshot_provider)
    original_aiohttp = tools_module.aiohttp
    original_tavily_ctor = tools_module.AsyncTavilyClient

    def guarded_tavily_ctor(*args: Any, **kwargs: Any) -> _TavilyClientProxy:
        return _TavilyClientProxy(
            original_tavily_ctor(*args, **kwargs),
            audit,
        )

    installation = Installation(
        tools_module,
        original_aiohttp=original_aiohttp,
        original_tavily_ctor=original_tavily_ctor,
        audit=audit,
    )
    tools_module.aiohttp = _AiohttpProxy(original_aiohttp, audit)
    tools_module.AsyncTavilyClient = guarded_tavily_ctor
    tools_module._brain_zero_spend_installation = installation
    return installation
