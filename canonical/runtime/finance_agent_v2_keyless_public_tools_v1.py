from __future__ import annotations

import base64
import csv
import io
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, urlparse

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_KEYLESS_PUBLIC_TOOLS_V1"
MAX_END_DATE = "2026-03-01"
BING_SEARCH_URL = "https://www.bing.com/search"
SEC_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
YAHOO_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
PUBLIC_HOSTS = (
    "www.bing.com",
    "efts.sec.gov",
    "www.sec.gov",
    "query1.finance.yahoo.com",
)


def _iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except Exception as exc:
        raise ValueError(f"INVALID_{field.upper()}_DATE") from exc


def _clamp_end(value: str | None) -> str:
    if not value:
        return MAX_END_DATE
    _iso_date(value, "end")
    return min(value, MAX_END_DATE)


def _bing_filter(start_date: str | None, end_date: str | None) -> str:
    epoch = date(1970, 1, 1)
    start = _iso_date(start_date, "start") if start_date else epoch
    end = _iso_date(_clamp_end(end_date), "end")
    if start > end:
        raise ValueError("START_DATE_AFTER_END_DATE")
    start_days = (start - epoch).days
    end_days = (end - epoch).days
    if start_days < 0:
        start_days = 0
    return f'ex1:"ez5_{start_days}_{end_days}"'


def _decode_bing_href(href: str) -> str:
    try:
        parsed = urlparse(href)
        if parsed.hostname not in {"www.bing.com", "bing.com"} or not parsed.path.startswith("/ck/"):
            return href
        encoded = parse_qs(parsed.query).get("u", [""])[0]
        if not encoded.startswith("a1"):
            return href
        payload = encoded[2:]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8")
        if decoded.startswith(("http://", "https://")):
            return decoded
    except Exception:
        pass
    return href


def _normalize_ciks(ciks: Sequence[str] | str | None) -> list[str]:
    if ciks is None:
        return []
    values = [ciks] if isinstance(ciks, str) else list(ciks)
    out: list[str] = []
    for raw in values:
        digits = "".join(ch for ch in str(raw) if ch.isdigit())
        if not digits:
            continue
        normalized = digits.zfill(10)
        if normalized not in out:
            out.append(normalized)
    return out


def _sec_filing_url(hit: Mapping[str, Any]) -> str | None:
    source = hit.get("_source") if isinstance(hit, Mapping) else None
    if not isinstance(source, Mapping):
        return None
    ciks = source.get("ciks")
    if not isinstance(ciks, list) or not ciks:
        return None
    doc_id = str(hit.get("_id") or "")
    if ":" not in doc_id:
        return None
    accession, filename = doc_id.split(":", 1)
    cik = str(ciks[0]).lstrip("0") or "0"
    accession_path = accession.replace("-", "")
    if not accession_path or not filename:
        return None
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_path}/{filename}"


def _sec_results(payload: Mapping[str, Any], top_n: int) -> list[dict[str, Any]]:
    hits_obj = payload.get("hits") if isinstance(payload, Mapping) else None
    raw_hits = hits_obj.get("hits") if isinstance(hits_obj, Mapping) else None
    if not isinstance(raw_hits, list):
        return []
    out: list[dict[str, Any]] = []
    for hit in raw_hits[: max(0, int(top_n))]:
        if not isinstance(hit, Mapping):
            continue
        src = hit.get("_source")
        if not isinstance(src, Mapping):
            continue
        url = _sec_filing_url(hit)
        forms = src.get("root_forms") if isinstance(src.get("root_forms"), list) else []
        displays = src.get("display_names") if isinstance(src.get("display_names"), list) else []
        title_parts = [str(x) for x in displays[:1]] + [str(x) for x in forms[:1]]
        title = " - ".join(x for x in title_parts if x) or str(src.get("file_description") or "SEC filing")
        row = {
            "url": url,
            "filing_url": url,
            "title": title,
            "file_date": src.get("file_date"),
            "period_ending": src.get("period_ending"),
            "forms": forms,
            "ciks": src.get("ciks"),
            "display_names": displays,
            "file_description": src.get("file_description"),
        }
        row["content"] = " | ".join(
            str(x)
            for x in (
                row.get("file_date"),
                row.get("period_ending"),
                row.get("file_description"),
            )
            if x
        )
        out.append(row)
    return out


def _yahoo_symbol(ticker: str, asset_class: str) -> str:
    t = ticker.strip()
    cls = asset_class.strip().lower()
    if not t:
        raise ValueError("TICKER_REQUIRED")
    if cls in {"equity", "etf"}:
        return t.upper()
    compact = "".join(ch for ch in t.lower() if ch.isalnum())
    if cls == "crypto":
        if len(compact) <= 3:
            raise ValueError("CRYPTO_PAIR_REQUIRED")
        quote = compact[-3:].upper()
        base = compact[:-3].upper()
        return f"{base}-{quote}"
    if cls == "fx":
        if len(compact) != 6:
            raise ValueError("FX_PAIR_MUST_HAVE_SIX_LETTERS")
        return f"{compact.upper()}=X"
    raise ValueError("UNSUPPORTED_ASSET_CLASS")


def _yahoo_period(date_value: str, *, inclusive_end: bool = False) -> int:
    d = _iso_date(date_value, "price")
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    if inclusive_end:
        dt += timedelta(days=1)
    return int(dt.timestamp())


def _yahoo_csv(payload: Mapping[str, Any]) -> str:
    chart = payload.get("chart") if isinstance(payload, Mapping) else None
    if not isinstance(chart, Mapping):
        raise ValueError("YAHOO_CHART_MISSING")
    if chart.get("error") not in (None, False):
        raise ValueError("YAHOO_CHART_ERROR")
    results = chart.get("result")
    if not isinstance(results, list) or not results:
        return ""
    result = results[0]
    if not isinstance(result, Mapping):
        return ""
    timestamps = result.get("timestamp")
    indicators = result.get("indicators")
    if not isinstance(timestamps, list) or not isinstance(indicators, Mapping):
        return ""
    quotes = indicators.get("quote")
    quote = quotes[0] if isinstance(quotes, list) and quotes and isinstance(quotes[0], Mapping) else {}
    adj_rows = indicators.get("adjclose")
    adj = adj_rows[0].get("adjclose") if isinstance(adj_rows, list) and adj_rows and isinstance(adj_rows[0], Mapping) else []
    headers = ["date", "open", "high", "low", "close", "adjClose", "volume"]
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    for idx, ts in enumerate(timestamps):
        try:
            day = datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
        except Exception:
            continue

        def value(name: str) -> Any:
            arr = quote.get(name) if isinstance(quote, Mapping) else None
            return arr[idx] if isinstance(arr, list) and idx < len(arr) else None

        adj_value = adj[idx] if isinstance(adj, list) and idx < len(adj) else None
        writer.writerow([
            day,
            value("open") if value("open") is not None else "N/A",
            value("high") if value("high") is not None else "N/A",
            value("low") if value("low") is not None else "N/A",
            value("close") if value("close") is not None else "N/A",
            adj_value if adj_value is not None else "N/A",
            value("volume") if value("volume") is not None else "N/A",
        ])
    rows = buf.getvalue().strip()
    return rows if rows.count("\n") >= 1 else ""


def install_keyless_public_tools(*, get_agent_module: Any, tools_module: Any) -> dict[str, Any]:
    """Replace only the three credential-bound Finance Agent tools.

    Tool names, descriptions and parameter schemas stay aligned with the pinned
    Vals harness. The replacement backends use public unauthenticated endpoints:
    SEC EFTS/Archives, Bing consumer web search, and Yahoo chart history.
    No provider API key, paid account, or external reasoning model is used.
    """
    Tool = tools_module.Tool
    originals = {
        "get_tavily": get_agent_module.TavilyWebSearch,
        "get_edgar": get_agent_module.EDGARSearch,
        "get_price": get_agent_module.PriceHistory,
        "tools_tavily": getattr(tools_module, "TavilyWebSearch", None),
        "tools_edgar": getattr(tools_module, "EDGARSearch", None),
        "tools_price": getattr(tools_module, "PriceHistory", None),
    }

    OriginalWeb = originals["get_tavily"]
    OriginalEdgar = originals["get_edgar"]
    OriginalPrice = originals["get_price"]

    async def sec_search(
        *,
        search_query: str,
        start_date: str = "1970-01-01",
        end_date: str = MAX_END_DATE,
        top_n_results: int = 20,
        page: int = 1,
        form_types: Sequence[str] | str | None = None,
        ciks: Sequence[str] | str | None = None,
    ) -> list[dict[str, Any]]:
        start = _iso_date(start_date, "start").isoformat()
        end = _clamp_end(end_date)
        if start > end:
            raise ValueError("START_DATE_AFTER_END_DATE")
        params: dict[str, Any] = {
            "q": search_query,
            "dateRange": "custom",
            "startdt": start,
            "enddt": end,
            "from": max(0, (int(page) - 1) * 100),
            "size": max(1, min(100, int(top_n_results))),
        }
        if form_types:
            forms = [form_types] if isinstance(form_types, str) else list(form_types)
            params["forms"] = ",".join(str(x) for x in forms)
        normalized_ciks = _normalize_ciks(ciks)
        if normalized_ciks:
            params["ciks"] = ",".join(normalized_ciks)
        headers = {
            "User-Agent": "ProjectBrain/1.0 finance-research",
            "Accept": "application/json",
        }
        async with tools_module.aiohttp.ClientSession() as session:
            async with session.get(
                SEC_EFTS_URL,
                params=params,
                headers=headers,
                timeout=tools_module.aiohttp.ClientTimeout(total=60),
            ) as response:
                response.raise_for_status()
                payload = await response.json()
        return _sec_results(payload, int(top_n_results))

    class KeylessWebSearch(Tool):
        name = OriginalWeb.name
        description = OriginalWeb.description
        parameters = OriginalWeb.parameters
        required = OriginalWeb.required

        async def _execute_search(
            self,
            search_query: str,
            start_date: str | None = None,
            end_date: str = MAX_END_DATE,
            number_of_results: int = 10,
        ) -> list[dict[str, Any]]:
            end = _clamp_end(end_date)
            start = start_date or "1970-01-01"
            sec_query = " ".join(
                token for token in search_query.replace("site:sec.gov", " ").split()
                if token
            )
            if sec_query:
                try:
                    sec = await sec_search(
                        search_query=sec_query,
                        start_date=start,
                        end_date=end,
                        top_n_results=number_of_results,
                    )
                    if sec:
                        return sec[: int(number_of_results)]
                except Exception:
                    pass

            params = {
                "q": search_query,
                "mkt": "en-US",
                "setlang": "en-US",
                "filters": _bing_filter(start, end),
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            async with tools_module.aiohttp.ClientSession() as session:
                async with session.get(
                    BING_SEARCH_URL,
                    params=params,
                    headers=headers,
                    timeout=tools_module.aiohttp.ClientTimeout(total=60),
                ) as response:
                    response.raise_for_status()
                    html = await response.text()
            soup = tools_module.BeautifulSoup(html, "html.parser")
            out: list[dict[str, Any]] = []
            for item in soup.select("li.b_algo"):
                link = item.select_one("h2 a[href]")
                if link is None:
                    continue
                href = _decode_bing_href(str(link.get("href") or ""))
                if not href.startswith(("http://", "https://")):
                    continue
                paragraph = item.select_one(".b_caption p") or item.find("p")
                out.append({
                    "url": href,
                    "title": link.get_text(" ", strip=True),
                    "content": paragraph.get_text(" ", strip=True) if paragraph is not None else "",
                })
                if len(out) >= max(1, min(20, int(number_of_results))):
                    break
            return out

        async def execute(self, args: dict[str, Any], state: dict[str, Any], logger: Any) -> Any:
            try:
                kwargs = {k: v for k, v in args.items() if k in self.parameters}
                results = await self._execute_search(**kwargs)
                return tools_module.ToolOutput(output=json.dumps(results, default=str))
            except Exception as exc:
                message = str(exc)
                logger.warning(f"Keyless web search failed: {message}")
                return tools_module.ToolOutput(output=message, error=message)

    class KeylessEDGARSearch(Tool):
        name = OriginalEdgar.name
        description = OriginalEdgar.description
        parameters = OriginalEdgar.parameters
        required = OriginalEdgar.required

        async def _execute_search(self, **kwargs: Any) -> list[dict[str, Any]]:
            return await sec_search(**kwargs)

        async def execute(self, args: dict[str, Any], state: dict[str, Any], logger: Any) -> Any:
            try:
                kwargs = {k: v for k, v in args.items() if k in self.parameters}
                results = await self._execute_search(**kwargs)
                return tools_module.ToolOutput(output=json.dumps(results, default=str))
            except Exception as exc:
                message = str(exc)
                logger.warning(f"Keyless EDGAR search failed: {message}")
                return tools_module.ToolOutput(output=message, error=message)

    class KeylessPriceHistory(Tool):
        name = OriginalPrice.name
        description = OriginalPrice.description
        parameters = OriginalPrice.parameters
        required = OriginalPrice.required

        async def execute(self, args: dict[str, Any], state: dict[str, Any], logger: Any) -> Any:
            try:
                ticker = str(args["ticker"]).strip()
                start = _iso_date(str(args["start_date"]), "start").isoformat()
                end = _clamp_end(str(args["end_date"]))
                if start > end:
                    raise ValueError("START_DATE_AFTER_END_DATE")
                asset_class = str(args.get("asset_class") or "").strip().lower()
                symbol = _yahoo_symbol(ticker, asset_class)
                url = f"{YAHOO_CHART_BASE}/{symbol}"
                params = {
                    "period1": _yahoo_period(start),
                    "period2": _yahoo_period(end, inclusive_end=True),
                    "interval": "1d",
                    "events": "history",
                    "includeAdjustedClose": "true",
                }
                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                }
                async with tools_module.aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=tools_module.aiohttp.ClientTimeout(total=60),
                    ) as response:
                        response.raise_for_status()
                        payload = await response.json()
                csv_text = _yahoo_csv(payload)
                if not csv_text:
                    csv_text = f"No pricing data returned for {ticker} ({asset_class}) {start}..{end}"
                return tools_module.ToolOutput(output=csv_text)
            except Exception as exc:
                message = str(exc)
                logger.warning(f"Keyless price history failed: {message}")
                return tools_module.ToolOutput(output=message, error=message)

    get_agent_module.TavilyWebSearch = KeylessWebSearch
    get_agent_module.EDGARSearch = KeylessEDGARSearch
    get_agent_module.PriceHistory = KeylessPriceHistory
    if originals["tools_tavily"] is not None:
        tools_module.TavilyWebSearch = KeylessWebSearch
    if originals["tools_edgar"] is not None:
        tools_module.EDGARSearch = KeylessEDGARSearch
    if originals["tools_price"] is not None:
        tools_module.PriceHistory = KeylessPriceHistory

    def restore() -> None:
        get_agent_module.TavilyWebSearch = originals["get_tavily"]
        get_agent_module.EDGARSearch = originals["get_edgar"]
        get_agent_module.PriceHistory = originals["get_price"]
        if originals["tools_tavily"] is not None:
            tools_module.TavilyWebSearch = originals["tools_tavily"]
        if originals["tools_edgar"] is not None:
            tools_module.EDGARSearch = originals["tools_edgar"]
        if originals["tools_price"] is not None:
            tools_module.PriceHistory = originals["tools_price"]

    return {
        "schema": SCHEMA,
        "status": "PASS__KEYLESS_PUBLIC_FINANCE_TOOLS_INSTALLED",
        "replaced_tools": ["web_search", "edgar_search", "price_history"],
        "public_hosts": list(PUBLIC_HOSTS),
        "credential_env_vars_required": [],
        "provider_account_dependency_count": 0,
        "billing_credential_dependency_count": 0,
        "external_general_purpose_model_runtime_cognition": 0,
        "incremental_spend_usd": 0,
        "restore": restore,
    }


__all__ = [
    "SCHEMA",
    "MAX_END_DATE",
    "PUBLIC_HOSTS",
    "_bing_filter",
    "_decode_bing_href",
    "_normalize_ciks",
    "_sec_filing_url",
    "_sec_results",
    "_yahoo_symbol",
    "_yahoo_period",
    "_yahoo_csv",
    "install_keyless_public_tools",
]
