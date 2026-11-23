#!/usr/bin/env python3
"""Unseen-page probe for the BROWSER surface (§24).

The §6-gate surface the repo had no measurable evidence on: a live browser,
driven by the repo's own CDP driver (osworld_v21_browser_cdp_v1), through a
real headless Chromium served over localhost (a fixture page the agent has
never seen). The loop drives the page with its own ops; the probe verifies
the DOM for real (test-side instrumentation, never counted as capability).

Assertions, all honest:
  1. the page snapshot reports its interactive elements (button, input, submit);
  2. CLICK_TEXT "click me" increments the counter span 0 -> 1;
  3. FILL "input#txt" with "abc" reverses the reversed span to "cba";
  4. CLICK_TEXT "go" submits the form: the done span becomes "submitted:abc";
  5. a late element appears after its timeout;
  6. an honest refusal: an op for an element that does not exist fails loudly.

Authority NONE. Producer-run sandbox measurement. No model calls, no network
(the page is localhost), $0.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import browser_v1 as browser

PORT = "9222"
URL = "http://127.0.0.1:8791/probe.html"


def _eval(js: str) -> object:
    """Read the live page for the probe's own verification (test-side)."""
    import types
    from playwright.sync_api import sync_playwright

    OC = browser._load_cdp_driver()
    b = OC.BrowserCDP()
    b.bind_environment(types.SimpleNamespace(vm_ip="127.0.0.1", chromium_port=int(PORT)))
    with sync_playwright() as p:
        browser_cdp = p.chromium.connect_over_cdp(
            f"http://127.0.0.1:{PORT}")
        pages = []
        for context in browser_cdp.contexts:
            pages.extend(context.pages)
        return pages[0].evaluate(js)


def main() -> int:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append({"check": name, "ok": bool(ok), "detail": detail})
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")

    # 0. browser is actually up and readable
    ok, why = browser.ensure([])
    check("browser_up", ok, why)

    # 1. load + snapshot
    state = browser.state(URL)
    check("load_page", bool(state.get("ok")),
          state.get("reason") or "title/elements")
    elements = (state.get("data") or {}).get("elements") or []
    check("interactive_elements", len(elements) >= 3,
          f"elements: {[(e['tag'], e['text'].strip()) for e in elements]}")

    # 2. click the button -> counter increments
    click = browser.act({"type": "CLICK_TEXT", "text": "click me"})
    counter = _eval("document.getElementById('n').textContent")
    check("click_increments_counter", click.get("status") == "PASS" and counter == "1",
          f"op={click.get('status')} counter={counter}")

    # 3. fill the input -> reversed output follows the reverse
    fill = browser.act({"type": "FILL", "selector": "input#txt", "text": "abc"})
    reversed_text = _eval("document.getElementById('rev').textContent")
    check("fill_reverses_output", fill.get("status") == "PASS" and reversed_text == "cba",
          f"op={fill.get('status')} reversed={reversed_text}")

    # 4. submit the form -> done span reports the submitted text
    submit = browser.act({"type": "CLICK_TEXT", "text": "go"})
    done = _eval("document.getElementById('done').textContent")
    check("submit_reports_submitted_text", submit.get("status") == "PASS" and done == "submitted:abc",
          f"op={submit.get('status')} done={done!r}")

    # 5. the late element appears after its timeout
    time.sleep(1.0)
    late = _eval("document.getElementById('late').textContent")
    check("late_element_appears", late == "APPEARED_LATER", late)

    # 6. honest refusal: an element that does not exist fails loudly
    refused = False
    try:
        browser.act({"type": "CLICK_TEXT", "text": "no such button anywhere"})
    except Exception as e:
        refused = True
        refused_why = str(e)[:120]
    check("refusal_is_honest", refused,
          refused_why if refused else "no error was raised (NOT honest)")

    all_ok = all(r["ok"] for r in results)
    print()
    print("SUMMARY:", "PASS__BROWSER_INTERFACED" if all_ok else "OPEN__BROWSER_CHECK_FAILED")
    print(json.dumps({"ok": all_ok, "checks": results}, indent=1))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
