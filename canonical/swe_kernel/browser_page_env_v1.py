#!/usr/bin/env python3
"""A live page as an env for the generic Perfect-Algorithm scan loop.

The §22/§25 flows scan and remember a page; the scan-level code-repair env
(§23) and file-transform envs prove the scan→plan→act→verify→admit→persist
chain end to end over a file. This env is the SAME protocol over a LIVE PAGE:
same reset/act/state/snapshot/restore discipline, same flat-heuristic
honesty, same plan/admit/persist chain (perfect_algorithm_v1.run), no other
machinery.

What makes it a page env, and what makes it honest:

  Actions are operations on the page, declared by the caller — the page's own
  declared surface, not instance coordinates. Three kinds, all thin:
    "click:<text>"           -- click the visible element whose text is <text>
    "fill:<selector>:<value>"-- fill the named input with <value>
    "press:<selector>:<key>" -- press <key> on the named element

  State is the live page read through a fresh CDP connection — NOT a
  re-navigation (which would discard every click/fill the env performed).
  Every probe the scan performs is one navigate+read cycle, so every acted
  page change is genuinely unobservable through state() unless it survives
  the probe — which is exactly what the probe must do to be honest.

  Reset = navigate fresh (a page is a fresh document every load; the honest
  "restore" is a fresh load, and restore(token) does exactly that). Snapshot
  records the state identity (the page's fresh URL), never a byte blob.

  The honest oracle (`is_goal`) is caller-provided — the page declares no
  contract (§25), so the caller states the goal. Heuristic is flat (0.0 at
  goal, 1.0 elsewhere): the best-first scan then walks the frontier.

  Refuses to claim: it is not the filesystem env; it does not carry a model
  across kinds; it does not claim cross-kind transfer (§27).

Model calls: 0. Network: 0 beyond 127.0.0.1 (the page is the sandbox's own).
Spend: $0.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_BROWSER_PAGE_ENV_V1"
AUTHORITY = "NONE__OBSERVED_LIVE_PAGE_EVIDENCE_AND_GATES"
KIND = "browser_page"


def _port() -> str:
    import os
    return os.environ.get("BRAIN_BROWSER_PORT", "9222")


def _live_state() -> dict[str, Any]:
    """One fresh CDP connection, one live read of the page (never navigates)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        cdp = p.chromium.connect_over_cdp(f"http://127.0.0.1:{_port()}")
        pages: list = []
        for context in cdp.contexts:
            pages.extend(context.pages)
        if not pages:
            raise RuntimeError("no live page")
        page = pages[0]
        text = page.locator("body").inner_text()
        return {
            "url": page.url,
            "title": page.title(),
            "text": text,
            "text_chars": len(text),
            "elements": _live_elements(page),
            "inputs": _live_inputs(page),
        }


def _live_inputs(page) -> dict[str, Any]:
    """Record the live form-field values so restore can re-apply them.

    This is the one piece of page state that is genuinely replayable: the
    form fields. Everything else on a page (the counter, the done line) is
    derived from the inputs and the actions, and is never trusted.
    """
    try:
        rows = page.locator("input,textarea,select").evaluate_all(
            """els => els.map(e => {
                let sel;
                if (e.id) sel = '#'+e.id;
                else if (e.name) sel = '[name=\"'+e.name.replace(/\"/g,'')+'\"]';
                else sel = e.tagName.toLowerCase();
                return {sel, value: 'value' in e ? e.value : ''};
            })"""
        )
        out: dict[str, Any] = {}
        for row in rows:
            try:
                sel = str(row.get("sel") or "").strip()
                if sel:
                    out[sel] = str(row.get("value") or "")
            except Exception:
                continue
        return out
    except Exception:
        return {}


class BrowserPageEnv:
    """A live page driven by the repo's own CDP browser driver."""

    def __init__(self, url: str, actions: Sequence[str], *,
                 env_kind: str = KIND, wait_s: float = 0.4) -> None:
        self._url = url
        self.kind = env_kind
        self.actions = tuple(str(a) for a in actions)
        self.wait_s = float(wait_s)
        self.reset()

    # -- lifecycle -- #
    def reset(self) -> None:
        from canonical.runtime import browser_v1 as browser
        browser.bind().act({"type": "NAVIGATE", "url": self._url})
        time.sleep(self.wait_s)

    def close(self) -> None:
        # the browser is shared/external — nothing owned here (no teardown)
        return None

    # -- env protocol -- #
    def act(self, action: str) -> bool:
        name = str(action)
        if name.startswith("click:"):
            text = name[len("click:"):].strip()
            if not text:
                return False
            op = {"type": "CLICK_TEXT", "text": text}
        elif name.startswith("fill:"):
            parts = name[len("fill:"):].split(":", 2)
            if len(parts) != 2 or not parts[0]:
                return False
            sel, value = parts
            op = {"type": "FILL", "selector": sel, "text": value}
        elif name.startswith("press:"):
            parts = name[len("press:"):].split(":", 1)
            if len(parts) != 2 or not parts[0] or not parts[1]:
                return False
            sel, key = parts
            op = {"type": "PRESS", "selector": sel, "key": key}
        else:
            return False
        try:
            from canonical.runtime import browser_v1 as browser
            browser.bind().act(op)
        except Exception:
            return False
        time.sleep(self.wait_s)
        return True

    def state(self) -> dict[str, Any]:
        # fresh CDP read of the LIVE page — never re-navigates, so the clicks
        #/fills this env performed are genuinely visible (the honesty rule)
        return _live_state()

    def snapshot(self) -> dict[str, Any]:
        # snapshot = the live state, INCLUDING the form-field values.
        # restore(token) re-applies the same values on a fresh load.
        return self.state()

    def restore(self, token: Mapping[str, Any]) -> None:
        # honest "restore" for a page: fresh load of the env ROOT (the URL the
        # env was constructed for), then re-apply the recorded form-field
        # values. Everything else derived from the form (the reversed span,
        # the done line, a redirect to another page) is NOT restored -- it is
        # re-derived by the same actions that produced it, never trusted.
        # The token's url is NOT honored: an env's identity is the fixture it
        # was built with, never where a probe last left the page.
        values = (token or {}).get("inputs") or {}
        self.reset()
        if values:
            try:
                from canonical.runtime import browser_v1 as browser
                for sel, value in values.items():
                    uc = str(value)
                    browser.bind().act({"type": "FILL",
                                        "selector": str(sel),
                                        "text": uc})
                    time.sleep(0.05)
            except Exception:
                pass
        time.sleep(self.wait_s)

    def action_names(self) -> list[str]:
        return list(self.actions)


def _live_elements(page) -> list[dict[str, Any]]:
    try:
        return page.locator(
            "a,button,input,textarea,select,[role=button],[role=link],"
            "[contenteditable=true],[tabindex]"
        ).evaluate_all(
            """els => els.filter(e => {
                const r=e.getBoundingClientRect();
                const s=getComputedStyle(e);
                return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none';
            }).slice(0, 80).map((e,i) => ({
                i, tag:(e.tagName||'').toLowerCase(),
                role:e.getAttribute('role')||'',
                type:e.getAttribute('type')||'',
                text:(e.innerText||e.textContent||'').trim().slice(0,240),
                aria:e.getAttribute('aria-label')||'',
                placeholder:e.getAttribute('placeholder')||'',
                name:e.getAttribute('name')||'',
                disabled:Boolean(e.disabled)
            }))"""
        )
    except Exception:
        return []


def build_page_env(
    url: str,
    actions: Sequence[str],
    *,
    goal_predicate: Callable[[Any], bool] | None = None,
    env_kind: str = KIND,
    wait_s: float = 0.4,
) -> tuple[BrowserPageEnv, dict[str, Any]]:
    """Construct the env plus the meta the perfect-algorithm loop needs.

    Returns (env, meta) with:
      is_goal    -- real goal predicate over the LIVE page (caller-provided;
                    flat default refuses)
      heuristic  -- flat 0.0 at goal, 1.0 elsewhere (honest)
      env_kind   -- "browser_page" (the honest default)
    """
    env = BrowserPageEnv(url, actions, env_kind=env_kind, wait_s=wait_s)

    def is_goal(state: Any) -> bool:
        if callable(goal_predicate):
            return bool(goal_predicate(state))
        # honest default: refuse to claim the goal without a predicate
        return False

    def heuristic(state: Any) -> float:
        try:
            if callable(goal_predicate):
                return 0.0 if goal_predicate(state) else 1.0
            return 1.0
        except Exception:
            return 1.0

    meta = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "is_goal": is_goal,
        "heuristic": heuristic,
        "env_kind": env_kind,
    }
    return env, meta
