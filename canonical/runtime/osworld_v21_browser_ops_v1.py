"""Generic CDP browser operations for the Brain OSWorld 2.1 agent.

Uses the same Playwright-over-CDP mechanism present in the official OSWorld
setup controller. This surface is generic and task-blind: it exposes ordinary
browser operations only and carries no benchmark/evaluator/task-source access.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_BROWSER_OPS_V1"
MAX_OPS = 8
MAX_TEXT = 8000
MAX_SELECTOR = 1000
MAX_TIMEOUT_MS = 30000


class BrowserOpsError(ValueError):
    pass


def _text(value: Any, name: str, max_len: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or not value:
        raise BrowserOpsError(name + "_REQUIRED")
    if len(value) > max_len:
        raise BrowserOpsError(name + "_TOO_LONG")
    return value


def _timeout(value: Any) -> int:
    if value is None:
        return 10000
    if isinstance(value, bool) or not isinstance(value, int) or not 100 <= value <= MAX_TIMEOUT_MS:
        raise BrowserOpsError("TIMEOUT_INVALID")
    return value


def validate_ops(raw: Any) -> list[Mapping[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise BrowserOpsError("OPS_REQUIRED")
    if len(raw) > MAX_OPS:
        raise BrowserOpsError("TOO_MANY_OPS")
    if any(not isinstance(x, Mapping) for x in raw):
        raise BrowserOpsError("OP_NOT_OBJECT")
    allowed = {
        "OPEN_URL", "BACK", "FORWARD", "RELOAD",
        "CLICK_ROLE", "CLICK_TEXT", "CLICK_SELECTOR",
        "FILL_LABEL", "FILL_ROLE", "FILL_SELECTOR",
        "PRESS_SELECTOR", "SELECT_OPTION", "CHECK_SELECTOR", "UNCHECK_SELECTOR",
        "EXTRACT_TEXT", "EXTRACT_URL", "EXTRACT_TITLE",
    }
    out = []
    for op in raw:
        kind = str(op.get("type") or "").strip().upper()
        if kind not in allowed:
            raise BrowserOpsError("UNSUPPORTED_BROWSER_OP:" + kind)
        out.append(dict(op))
    return out


def _page(browser: Any) -> Any:
    if not browser.contexts:
        raise BrowserOpsError("NO_BROWSER_CONTEXT")
    context = browser.contexts[0]
    if not context.pages:
        return context.new_page()
    return context.pages[-1]


def execute_cdp_ops(endpoint: str, raw_ops: Any) -> dict[str, Any]:
    endpoint = _text(endpoint, "CDP_ENDPOINT", 2048)
    if not endpoint.startswith(("http://", "https://")):
        raise BrowserOpsError("CDP_ENDPOINT_INVALID")
    ops = validate_ops(raw_ops)

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise BrowserOpsError("PLAYWRIGHT_UNAVAILABLE") from exc

    receipts: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(endpoint)
        try:
            for raw in ops:
                kind = str(raw.get("type") or "").strip().upper()
                page = _page(browser)
                timeout = _timeout(raw.get("timeout_ms"))

                if kind == "OPEN_URL":
                    url = _text(raw.get("url"), "URL", 4096)
                    page.goto(url, timeout=timeout)
                    result: Any = page.url
                elif kind == "BACK":
                    page.go_back(timeout=timeout)
                    result = page.url
                elif kind == "FORWARD":
                    page.go_forward(timeout=timeout)
                    result = page.url
                elif kind == "RELOAD":
                    page.reload(timeout=timeout)
                    result = page.url
                elif kind == "CLICK_ROLE":
                    role = _text(raw.get("role"), "ROLE", 64)
                    name = _text(raw.get("name"), "NAME", 512)
                    page.get_by_role(role, name=name, exact=bool(raw.get("exact", False))).click(timeout=timeout)
                    result = True
                elif kind == "CLICK_TEXT":
                    value = _text(raw.get("text"), "TEXT", 512)
                    page.get_by_text(value, exact=bool(raw.get("exact", False))).click(timeout=timeout)
                    result = True
                elif kind == "CLICK_SELECTOR":
                    selector = _text(raw.get("selector"), "SELECTOR", MAX_SELECTOR)
                    page.locator(selector).first.click(timeout=timeout)
                    result = True
                elif kind == "FILL_LABEL":
                    label = _text(raw.get("label"), "LABEL", 512)
                    value = _text(raw.get("value"), "VALUE")
                    page.get_by_label(label, exact=bool(raw.get("exact", False))).fill(value, timeout=timeout)
                    result = True
                elif kind == "FILL_ROLE":
                    role = _text(raw.get("role"), "ROLE", 64)
                    name = _text(raw.get("name"), "NAME", 512)
                    value = _text(raw.get("value"), "VALUE")
                    page.get_by_role(role, name=name, exact=bool(raw.get("exact", False))).fill(value, timeout=timeout)
                    result = True
                elif kind == "FILL_SELECTOR":
                    selector = _text(raw.get("selector"), "SELECTOR", MAX_SELECTOR)
                    value = _text(raw.get("value"), "VALUE")
                    page.locator(selector).first.fill(value, timeout=timeout)
                    result = True
                elif kind == "PRESS_SELECTOR":
                    selector = _text(raw.get("selector"), "SELECTOR", MAX_SELECTOR)
                    key = _text(raw.get("key"), "KEY", 64)
                    page.locator(selector).first.press(key, timeout=timeout)
                    result = True
                elif kind == "SELECT_OPTION":
                    selector = _text(raw.get("selector"), "SELECTOR", MAX_SELECTOR)
                    value = _text(raw.get("value"), "VALUE", 512)
                    result = page.locator(selector).first.select_option(value=value, timeout=timeout)
                elif kind == "CHECK_SELECTOR":
                    selector = _text(raw.get("selector"), "SELECTOR", MAX_SELECTOR)
                    page.locator(selector).first.check(timeout=timeout)
                    result = True
                elif kind == "UNCHECK_SELECTOR":
                    selector = _text(raw.get("selector"), "SELECTOR", MAX_SELECTOR)
                    page.locator(selector).first.uncheck(timeout=timeout)
                    result = True
                elif kind == "EXTRACT_TEXT":
                    selector = raw.get("selector")
                    if selector is None:
                        result = page.locator("body").inner_text(timeout=timeout)
                    else:
                        result = page.locator(_text(selector, "SELECTOR", MAX_SELECTOR)).first.inner_text(timeout=timeout)
                    if len(result) > MAX_TEXT:
                        result = result[:MAX_TEXT]
                elif kind == "EXTRACT_URL":
                    result = page.url
                elif kind == "EXTRACT_TITLE":
                    result = page.title()
                else:
                    raise BrowserOpsError("UNREACHABLE_BROWSER_OP")

                receipts.append({
                    "type": kind,
                    "ok": True,
                    "result": result,
                    "url": page.url,
                })
        finally:
            browser.close()

    body = json.dumps(receipts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "schema": SCHEMA,
        "operation_count": len(receipts),
        "receipts": receipts,
        "receipt_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }
