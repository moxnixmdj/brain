from __future__ import annotations

import base64
import types
import unittest
from pathlib import Path

from canonical.runtime import finance_agent_v2_keyless_public_tools_v1 as m


class OriginalWeb:
    name = "web_search"
    description = "web"
    parameters = {"search_query": {"type": "string"}}
    required = ["search_query"]


class OriginalEdgar:
    name = "edgar_search"
    description = "edgar"
    parameters = {"search_query": {"type": "string"}}
    required = ["search_query"]


class OriginalPrice:
    name = "price_history"
    description = "price"
    parameters = {"ticker": {"type": "string"}}
    required = ["ticker"]


class FakeTool:
    pass


class FakeToolOutput:
    def __init__(self, output="", error=None, done=False):
        self.output = output
        self.error = error
        self.done = done


def fake_modules():
    ga = types.SimpleNamespace(
        TavilyWebSearch=OriginalWeb,
        EDGARSearch=OriginalEdgar,
        PriceHistory=OriginalPrice,
    )
    tm = types.SimpleNamespace(
        Tool=FakeTool,
        ToolOutput=FakeToolOutput,
        TavilyWebSearch=OriginalWeb,
        EDGARSearch=OriginalEdgar,
        PriceHistory=OriginalPrice,
        aiohttp=types.SimpleNamespace(),
        BeautifulSoup=object,
    )
    return ga, tm


class Tests(unittest.TestCase):
    def test_bing_filter_exact_cutoff(self):
        self.assertEqual(
            m._bing_filter("2024-01-01", "2026-03-01"),
            'ex1:"ez5_19723_20513"',
        )
        self.assertEqual(
            m._bing_filter(None, "2026-03-01"),
            'ex1:"ez5_0_20513"',
        )
        self.assertEqual(
            m._bing_filter("2024-01-01", "2027-01-01"),
            'ex1:"ez5_19723_20513"',
        )

    def test_decode_bing_redirect(self):
        target = "https://www.sec.gov/Archives/example.htm"
        encoded = base64.urlsafe_b64encode(target.encode()).decode().rstrip("=")
        href = "https://www.bing.com/ck/a?u=a1" + encoded
        self.assertEqual(m._decode_bing_href(href), target)
        self.assertEqual(m._decode_bing_href(target), target)

    def test_normalize_ciks(self):
        self.assertEqual(
            m._normalize_ciks(["320193", "0000320193", "1652044"]),
            ["0000320193", "0001652044"],
        )

    def test_sec_filing_projection(self):
        hit = {
            "_id": "0000320193-25-000079:aapl-20250927.htm",
            "_source": {
                "ciks": ["0000320193"],
                "display_names": ["APPLE INC"],
                "root_forms": ["10-K"],
                "file_date": "2025-10-31",
                "period_ending": "2025-09-27",
                "file_description": "10-K",
            },
        }
        url = (
            "https://www.sec.gov/Archives/edgar/data/320193/"
            "000032019325000079/aapl-20250927.htm"
        )
        self.assertEqual(m._sec_filing_url(hit), url)
        rows = m._sec_results({"hits": {"hits": [hit]}}, 10)
        self.assertEqual(rows[0]["url"], url)
        self.assertEqual(rows[0]["forms"], ["10-K"])

    def test_yahoo_symbol(self):
        self.assertEqual(m._yahoo_symbol("aapl", "equity"), "AAPL")
        self.assertEqual(m._yahoo_symbol("btcusd", "crypto"), "BTC-USD")
        self.assertEqual(m._yahoo_symbol("eurusd", "fx"), "EURUSD=X")
        with self.assertRaises(ValueError):
            m._yahoo_symbol("eur", "fx")

    def test_yahoo_csv_prefers_raw_close(self):
        payload = {
            "chart": {
                "error": None,
                "result": [{
                    "timestamp": [1767312000],
                    "indicators": {
                        "quote": [{
                            "open": [100.0],
                            "high": [105.0],
                            "low": [99.0],
                            "close": [101.25],
                            "volume": [1000],
                        }],
                        "adjclose": [{"adjclose": [98.75]}],
                    },
                }],
            }
        }
        out = m._yahoo_csv(payload)
        self.assertIn("date,open,high,low,close,adjClose,volume", out)
        self.assertIn("101.25,98.75,1000", out)

    def test_install_requires_no_provider_credentials(self):
        ga, tm = fake_modules()
        out = m.install_keyless_public_tools(
            get_agent_module=ga,
            tools_module=tm,
        )
        self.assertEqual(out["credential_env_vars_required"], [])
        self.assertEqual(out["provider_account_dependency_count"], 0)
        self.assertEqual(out["billing_credential_dependency_count"], 0)
        self.assertEqual(
            out["external_general_purpose_model_runtime_cognition"],
            0,
        )
        self.assertEqual(ga.TavilyWebSearch.name, "web_search")
        self.assertEqual(ga.EDGARSearch.name, "edgar_search")
        self.assertEqual(ga.PriceHistory.name, "price_history")
        self.assertNotEqual(ga.TavilyWebSearch, OriginalWeb)
        out["restore"]()
        self.assertIs(ga.TavilyWebSearch, OriginalWeb)
        self.assertIs(ga.EDGARSearch, OriginalEdgar)
        self.assertIs(ga.PriceHistory, OriginalPrice)

    def test_source_contains_no_keyed_provider_secret_names(self):
        text = Path(m.__file__).read_text(encoding="utf-8")
        for token in (
            "TAVILY_API_KEY",
            "SEC_EDGAR_API_KEY",
            "PRICING_DATA_API_KEY",
            "TIINGO_API_KEY",
        ):
            self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
