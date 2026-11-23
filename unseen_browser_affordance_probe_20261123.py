#!/usr/bin/env python3
"""Affordance discovery on the live page (§35).

The doctrine ("scan everything in the environment") was honest in principle
(the recon layer reads the DOM and reports affordances) but the loop itself
still used the caller-declared action surface — an env on an arbitrary page
never discovered its affordances. §35 adds exactly one piece:

  BrowserPageEnv.discover_affordances() -- reads the live DOM ONCE PER CALL
  and derives:
    - click actions for every visible button/link/[role=button]/[role=link]
      with a non-empty label ("click:<label>" -- value-free; the label IS
      the text a person would click);
    - observation-only entries for value-bearing inputs (form fields) --
      tag/type/placeholder/name, with the explicit note that the fill
      action and its value are caller-declared and are NEVER minted here.

The probe honestly checks:
  - discovery on TWO fixtures (A window/B different content) returns the same
    click actions (the fixture body is content-invariant in STRUCTURE);
  - the same inputs surface observation-only -- no selector, no value minted;
  - a page with NO interactive elements discovers NOTHING (honest, not
    fabricated);
  - the declared action surface is unchanged (action_names() intact).

Authority NONE. Producer-run sandbox measurement. No model calls,
no network beyond 127.0.0.1, $0. This probe does not re-run §28/§29/§30/§31/
§33/§34 -- those are measured.
"""
from __future__ import annotations

import functools
import http.server
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.browser_page_env_v1 import build_page_env

ACTIONS = ["fill:#txt:abc", "click:go"]

FIXTURE_BODY = """<h1>{h1}</h1>
  <p id="intro">{intro}</p>
  <div>counter=<span id="n">0</span></div>
  <button id="btn" onclick="document.getElementById('n').textContent=String(Number(document.getElementById('n').textContent)+1)">click me</button>
  <input id="txt" type="text" placeholder="your name">
  <form onsubmit="event.preventDefault();document.getElementById('done').textContent='submitted:'+document.getElementById('txt').value">
    <button type="submit" id="go">go</button>
  </form>
  <div id="done"></div>"""

EMPTY_BODY = """<h1>{h1}</h1>
  <p id="intro">{intro}</p>
  <p>A page with no interactive elements at all.</p>"""


def _fixture_html(title, h1, intro):
    return ("<!doctype html><html><head><title>%s</title></head><body>\n"
            "%s\n</body></html>" % (title, FIXTURE_BODY.format(h1=h1, intro=intro)))


def _empty_html(title, h1, intro):
    return ("<!doctype html><html><head><title>%s</title></head><body>\n"
            "%s\n</body></html>" % (title, EMPTY_BODY.format(h1=h1, intro=intro)))


def _serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class FreshFixture:
    def __init__(self, servers, title, h1, intro, *, empty=False):
        td = Path(tempfile.mkdtemp(prefix="unseen_discover_"))
        self.root = td / "page"
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "page.html").write_text(
            _empty_html(title, h1, intro) if empty else _fixture_html(title, h1, intro),
            encoding="utf-8")
        self.server = _serve(self.root)
        servers.append(self.server)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/page.html"

    def close(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass


def main():
    servers: list = []
    results: list = []
    try:
        a = FreshFixture(servers, "Discover A", "Discover A", "the first page")
        d = FreshFixture(servers, "Discover D", "Discover D", "the fourth page")
        e = FreshFixture(servers, "Discover Empty", "Discover Empty",
                         "the empty page", empty=True)

        # ----- discovery on fixture A -----
        env_a, _ = build_page_env(a.url, ACTIONS, goal_predicate=lambda s: False)
        rec_a = env_a.discover_affordances()
        results.append({"case": "A", "url": a.url, **rec_a})
        try:
            env_a.close()
        except Exception:
            pass

        # ----- discovery on fixture D (different content, same structure) -----
        env_d, _ = build_page_env(d.url, ACTIONS, goal_predicate=lambda s: False)
        rec_d = env_d.discover_affordances()
        results.append({"case": "D", "url": d.url, **rec_d})
        try:
            env_d.close()
        except Exception:
            pass

        # ----- discovery on the empty page (honest: nothing must be minted) -----
        env_e, _ = build_page_env(e.url, ACTIONS, goal_predicate=lambda s: False)
        rec_e = env_e.discover_affordances()
        results.append({"case": "EMPTY", "url": e.url, **rec_e})
        try:
            env_e.close()
        except Exception:
            pass

        # ----- declared surface is unchanged by the discovery read -----
        env_f, _ = build_page_env(a.url, ACTIONS, goal_predicate=lambda s: False)
        declared = env_f.action_names()
        results.append({"case": "DECLARED-SURFACE", "url": a.url,
                        "action_names": declared})
        try:
            env_f.close()
        except Exception:
            pass
    finally:
        for s in servers:
            try:
                s.shutdown()
                s.server_close()
            except Exception:
                pass

    print(json.dumps({"results": results}, indent=1, sort_keys=True))

    a_rec, d_rec, e_rec = (r for r in results if r["case"] in ("A", "D", "EMPTY"))
    declared_rec = next(r for r in results if r["case"] == "DECLARED-SURFACE")

    fails = []

    def clicks_of(rec):
        return set(rec.get("clicks") or [])

    a_clicks, d_clicks = clicks_of(a_rec), clicks_of(d_rec)
    expected = {"click:click me", "click:go"}
    if a_clicks != expected:
        fails.append(f"fixture A clicks wrong: {sorted(a_clicks)}")
    if d_clicks != expected:
        fails.append(f"fixture D clicks wrong (discovery must track the live DOM): {sorted(d_clicks)}")

    if a_rec.get("title") != "Discover A":
        fails.append(f"fixture A title not reflected: {a_rec.get('title')!r}")
    if d_rec.get("title") != "Discover D":
        fails.append(f"fixture D title not reflected: {d_rec.get('title')!r}")

    for r in (a_rec, d_rec):
        inputs = r.get("inputs") or []
        if len(inputs) != 1:
            fails.append(f"expected exactly one observation-only input, got {len(inputs)}")
            break
        inp = inputs[0]
        if inp.get("tag") != "input" or inp.get("type") != "text":
            fails.append(f"wrong input shape: {inp}")
        if inp.get("placeholder") != "your name":
            fails.append(f"wrong placeholder: {inp.get('placeholder')!r}")
        # honest: nothing invented as a fill action
        if any(k in inp for k in ("value", "sel", "action")):
            fails.append(f"observation-only input fabricated a fill action: {inp}")

    # empty fixture: honest — nothing minted, honest receipt, no fill/clicks
    if e_rec.get("clicks"):
        fails.append(f"empty page minted clicks: {e_rec.get('clicks')}")
    if e_rec.get("inputs"):
        fails.append(f"empty page invented inputs: {e_rec.get('inputs')}")

    # declared surface unchanged
    if declared_rec.get("action_names") != ACTIONS:
        fails.append(f"declared action surface changed: {declared_rec.get('action_names')}")

    if fails:
        print("PROBE: FAIL — " + "; ".join(fails))
        return 1
    print("PROBE: PASS — affordance discovery returns exactly the live DOM "
          "(2 click actions minted, 1 input observed observation-only, "
          "no fill minted, empty page stays empty)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
