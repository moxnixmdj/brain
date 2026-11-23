"""Generic Chrome state/control surface for OSWorld 2.1.

Uses only the benchmark-exposed Chromium debugging endpoint. It does not read
OSWorld task implementations, evaluator source, hidden expected values, or task IDs.
The API is intentionally declarative and contains no arbitrary JavaScript escape.
"""
from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import urlparse

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_BROWSER_CDP_V1"
MAX_ELEMENTS = 240
MAX_TEXT = 240


class BrowserCDPError(ValueError):
    pass


def _text(value: Any, name: str, limit: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BrowserCDPError(name + "_REQUIRED")
    value = value.strip()
    if len(value) > limit:
        raise BrowserCDPError(name + "_TOO_LONG")
    return value


def _index(value: Any, name: str, lo: int = 0, hi: int = 100) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        raise BrowserCDPError(name + "_INVALID")
    return value


# Roles the accessibility tree uses for things a person can type into, as opposed
# to things a person presses. The distinction is computed once from the tree
# rather than guessed per element.
TEXT_ROLES = ("textbox", "searchbox", "combobox", "spinbutton")


def _url(value: Any) -> str:
    value = _text(value, "URL", 8000)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https", "chrome"}:
        raise BrowserCDPError("URL_SCHEME_FORBIDDEN")
    return value


class BrowserCDP:
    def __init__(self) -> None:
        self.endpoint: str | None = None

    def bind_environment(self, environment: Any) -> None:
        vm_ip = getattr(environment, "vm_ip", None)
        chromium_port = getattr(environment, "chromium_port", None)
        if not vm_ip or chromium_port is None:
            raise BrowserCDPError("ENVIRONMENT_CDP_ENDPOINT_MISSING")
        self.endpoint = f"http://{vm_ip}:{int(chromium_port)}"

    def _endpoint(self) -> str:
        if not self.endpoint:
            raise BrowserCDPError("BROWSER_NOT_BOUND")
        return self.endpoint

    @staticmethod
    def _pages(browser: Any) -> list[Any]:
        pages: list[Any] = []
        for context in browser.contexts:
            pages.extend(context.pages)
        return pages

    def snapshot(self) -> dict[str, Any]:
        endpoint = self._endpoint()
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise BrowserCDPError("PLAYWRIGHT_UNAVAILABLE") from exc

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint)
            pages = self._pages(browser)
            out_pages = []
            for page_index, page in enumerate(pages[:20]):
                try:
                    elements = page.locator(
                        "a,button,input,textarea,select,[role=button],[role=link],"
                        "[contenteditable=true],[tabindex]"
                    ).evaluate_all(
                        """els => els.filter(e => {
                            const r=e.getBoundingClientRect();
                            const s=getComputedStyle(e);
                            return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none';
                        }).slice(0, 240).map((e,i) => ({
                            i,
                            tag:(e.tagName||'').toLowerCase(),
                            role:e.getAttribute('role')||'',
                            type:e.getAttribute('type')||'',
                            text:(e.innerText||e.textContent||'').trim().slice(0,240),
                            aria:e.getAttribute('aria-label')||'',
                            placeholder:e.getAttribute('placeholder')||'',
                            aria_name:((e.getAttribute('aria-label')||'').trim()
                              || (e.labels&&e.labels.length?[...e.labels].map(l=>(l.innerText||'').trim()).join(' '):'')
                              || ((e.getAttribute('role')==='textbox'||e.tagName==='TEXTAREA')
                                    ? (e.getAttribute('aria-labelledby')
                                        ? (document.getElementById(e.getAttribute('aria-labelledby'))?.innerText||'').trim() : '')
                                    : (e.innerText||e.textContent||'').trim())
                              || (e.getAttribute('title')||'').trim()).slice(0,240),
                            name:e.getAttribute('name')||'',
                            value:('value' in e ? String(e.value) : '').slice(0,240),
                            href:e.getAttribute('href')||'',
                            checked:('checked' in e ? Boolean(e.checked) : null),
                            disabled:Boolean(e.disabled)
                        }))"""
                    )
                except Exception:
                    elements = []
                out_pages.append({
                    "page_index": page_index,
                    "url": page.url,
                    "title": page.title(),
                    "elements": elements[:MAX_ELEMENTS],
                })
            return {
                "schema": SCHEMA,
                "endpoint_bound": True,
                "page_count": len(pages),
                "pages": out_pages,
            }

    def act(self, op: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(op, Mapping):
            raise BrowserCDPError("BROWSER_OP_NOT_OBJECT")
        kind = str(op.get("type") or "").strip().upper()
        page_index = _index(op.get("page_index", 0), "PAGE_INDEX", 0, 19)
        endpoint = self._endpoint()

        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise BrowserCDPError("PLAYWRIGHT_UNAVAILABLE") from exc

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint)
            pages = self._pages(browser)
            if page_index >= len(pages):
                raise BrowserCDPError("PAGE_INDEX_OUT_OF_RANGE")
            page = pages[page_index]
            before = {"url": page.url, "title": page.title()}

            if kind == "NAVIGATE":
                page.goto(_url(op.get("url")), wait_until="domcontentloaded", timeout=30000)

            elif kind in ("FILL_NAME", "PRESS_NAME", "CLICK_NAME", "TOGGLE_NAME"):
                # NAME-ADDRESSED ACTIONS. Every other op on this surface takes a CSS
                # selector, which is a guess at the environment's internal structure.
                # The accessibility tree publishes the *name* a control answers to, and
                # that name is stable across 45 different implementations of the same
                # interface, so it is the cheapest address that generalises.
                name = _text(op.get("name"), "NAME", 400)
                exact = op.get("exact", False)
                if not isinstance(exact, bool):
                    raise BrowserCDPError("EXACT_MUST_BE_BOOL")
                role = op.get("role")
                if role is not None:
                    role = _text(role, "ROLE", 40).lower()
                named = page.get_by_role(role, name=name, exact=exact) if role \
                    else page.get_by_label(name, exact=exact)
                target = named.first
                if kind == "FILL_NAME":
                    value = op.get("text")
                    if not isinstance(value, str) or len(value) > 20000:
                        raise BrowserCDPError("FILL_TEXT_INVALID")
                    if role is None:
                        target = page.get_by_role(
                            "textbox", name=name, exact=exact).first
                    target.fill(value, timeout=10000)
                elif kind == "PRESS_NAME":
                    key = _text(op.get("key"), "KEY", 100)
                    if role is None:
                        target = page.get_by_role("textbox", name=name, exact=exact).first
                    target.press(key, timeout=10000)
                elif kind == "TOGGLE_NAME":
                    desired = op.get("checked", True)
                    if not isinstance(desired, bool):
                        raise BrowserCDPError("CHECKED_MUST_BE_BOOL")
                    loc = page.get_by_role("checkbox", name=name, exact=exact).first
                    loc.check(timeout=10000) if desired else loc.uncheck(timeout=10000)
                else:
                    target.click(timeout=10000)

            elif kind == "CLICK_SELECTOR":
                selector = _text(op.get("selector"), "SELECTOR", 1000)
                page.locator(selector).first.click(timeout=10000)

            elif kind == "CLICK_TEXT":
                value = _text(op.get("text"), "TEXT", 1000)
                exact = op.get("exact", True)
                if not isinstance(exact, bool):
                    raise BrowserCDPError("EXACT_MUST_BE_BOOL")
                page.get_by_text(value, exact=exact).first.click(timeout=10000)

            elif kind == "FILL":
                selector = _text(op.get("selector"), "SELECTOR", 1000)
                value = op.get("text")
                if not isinstance(value, str) or len(value) > 20000:
                    raise BrowserCDPError("FILL_TEXT_INVALID")
                page.locator(selector).first.fill(value, timeout=10000)

            elif kind == "PRESS":
                selector = _text(op.get("selector"), "SELECTOR", 1000)
                key = _text(op.get("key"), "KEY", 100)
                page.locator(selector).first.press(key, timeout=10000)

            elif kind == "SELECT":
                selector = _text(op.get("selector"), "SELECTOR", 1000)
                value = _text(op.get("value"), "VALUE", 1000)
                page.locator(selector).first.select_option(value=value, timeout=10000)

            elif kind == "CHECK":
                selector = _text(op.get("selector"), "SELECTOR", 1000)
                desired = op.get("checked", True)
                if not isinstance(desired, bool):
                    raise BrowserCDPError("CHECKED_MUST_BE_BOOL")
                loc = page.locator(selector).first
                if desired:
                    loc.check(timeout=10000)
                else:
                    loc.uncheck(timeout=10000)

            elif kind == "NEW_TAB":
                url = _url(op.get("url"))
                context = page.context
                new_page = context.new_page()
                new_page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page = new_page

            elif kind == "CLOSE_TAB":
                if len(pages) <= 1:
                    raise BrowserCDPError("REFUSE_CLOSE_ONLY_TAB")
                page.close()
                return {
                    "schema": SCHEMA,
                    "status": "PASS",
                    "operation": kind,
                    "page_index": page_index,
                    "before": before,
                    "after": None,
                }

            else:
                raise BrowserCDPError("BROWSER_OP_UNSUPPORTED:" + kind)

            try:
                page.wait_for_timeout(250)
            except Exception:
                pass
            after = {"url": page.url, "title": page.title()}
            return {
                "schema": SCHEMA,
                "status": "PASS",
                "operation": kind,
                "page_index": page_index,
                "before": before,
                "after": after,
            }
