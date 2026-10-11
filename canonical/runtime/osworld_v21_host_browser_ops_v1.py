"""Constrained host-side Chrome controller for OSWorld 2.1.

Uses the benchmark host's existing Playwright dependency and the DesktopEnv CDP
bridge. No arbitrary JavaScript is exposed. Every operation is generic and
task-id agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

MAX_TEXT = 20000
MAX_VALUE = 4000
MAX_TABS = 32


class BrowserOpsError(ValueError):
    pass


def _text(value: Any, name: str, max_len: int = MAX_VALUE) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BrowserOpsError(name + "_REQUIRED")
    if len(value) > max_len:
        raise BrowserOpsError(name + "_TOO_LONG")
    return value


@dataclass
class OSWorldHostBrowser:
    remote_debugging_url: str | None = None

    def bind_environment(self, environment: Any) -> None:
        vm_ip = getattr(environment, "vm_ip", None)
        port = getattr(environment, "chromium_port", None)
        if not vm_ip or port is None:
            raise BrowserOpsError("DESKTOP_ENV_CDP_ENDPOINT_MISSING")
        self.remote_debugging_url = f"http://{vm_ip}:{int(port)}"

    def _connect(self):
        if not self.remote_debugging_url:
            raise BrowserOpsError("BROWSER_ENVIRONMENT_NOT_BOUND")
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise BrowserOpsError("PLAYWRIGHT_UNAVAILABLE") from exc
        pw = sync_playwright().start()
        try:
            browser = pw.chromium.connect_over_cdp(self.remote_debugging_url)
        except Exception:
            pw.stop()
            raise
        return pw, browser

    @staticmethod
    def _active_page(browser):
        if not browser.contexts:
            raise BrowserOpsError("NO_BROWSER_CONTEXT")
        pages = browser.contexts[0].pages
        if not pages:
            raise BrowserOpsError("NO_BROWSER_PAGE")
        return pages[-1]

    def run(self, op: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(op, Mapping):
            raise BrowserOpsError("BROWSER_OP_NOT_OBJECT")
        kind = str(op.get("type") or "").strip().upper()
        pw, browser = self._connect()
        try:
            page = self._active_page(browser)

            if kind == "OBSERVE":
                pages = browser.contexts[0].pages[:MAX_TABS]
                tabs = [{"title": p.title(), "url": p.url} for p in pages]
                body = ""
                try:
                    body = page.locator("body").inner_text(timeout=5000)
                except Exception:
                    body = ""
                return {
                    "type": kind,
                    "active_url": page.url,
                    "active_title": page.title(),
                    "tabs": tabs,
                    "visible_text": body[:MAX_TEXT],
                }

            if kind == "NAVIGATE":
                url = _text(op.get("url"), "URL")
                if not (url.startswith("http://") or url.startswith("https://") or url.startswith("chrome://")):
                    raise BrowserOpsError("URL_SCHEME_NOT_ALLOWED")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                return {"type": kind, "url": page.url, "title": page.title()}

            if kind == "CLICK_TEXT":
                text = _text(op.get("text"), "TEXT")
                exact = bool(op.get("exact", True))
                page.get_by_text(text, exact=exact).first.click(timeout=10000)
                return {"type": kind, "text": text, "url": page.url}

            if kind == "CLICK_ROLE":
                role = _text(op.get("role"), "ROLE", 64)
                name = _text(op.get("name"), "NAME")
                page.get_by_role(role, name=name, exact=bool(op.get("exact", True))).first.click(timeout=10000)
                return {"type": kind, "role": role, "name": name, "url": page.url}

            if kind == "FILL_LABEL":
                label = _text(op.get("label"), "LABEL")
                value = _text(op.get("value"), "VALUE")
                page.get_by_label(label, exact=bool(op.get("exact", True))).first.fill(value, timeout=10000)
                return {"type": kind, "label": label, "url": page.url}

            if kind == "FILL_PLACEHOLDER":
                placeholder = _text(op.get("placeholder"), "PLACEHOLDER")
                value = _text(op.get("value"), "VALUE")
                page.get_by_placeholder(placeholder, exact=bool(op.get("exact", True))).first.fill(value, timeout=10000)
                return {"type": kind, "placeholder": placeholder, "url": page.url}

            if kind == "PRESS":
                key = _text(op.get("key"), "KEY", 64)
                page.keyboard.press(key)
                return {"type": kind, "key": key, "url": page.url}

            if kind == "SELECT_LABEL":
                label = _text(op.get("label"), "LABEL")
                value = _text(op.get("value"), "VALUE")
                page.get_by_label(label, exact=bool(op.get("exact", True))).first.select_option(value=value, timeout=10000)
                return {"type": kind, "label": label, "value": value, "url": page.url}

            raise BrowserOpsError("BROWSER_OP_UNSUPPORTED:" + kind)
        finally:
            # Do not call browser.close() on a CDP-attached task Chrome: that can
            # terminate the benchmark browser itself. Stopping Playwright only
            # releases the client connection.
            pw.stop()
