#!/usr/bin/env python3
"""Unseen-page probe for the browser-env direction (§28).

The §24/§25 story proves the browser surface is bring-up-able and scannable.
This probe proves the Perfect Algorithm LOOP -- cold scan -> plan -> act ->
verify -> admit on fresh variants -> persist -> warm replay -- works on a
live page.

   TEACH  cold scan on fixture A -> admit on 2 fresh same-shape variants B,C
          -> persist the rule
   COLD   fresh fixture page D (unseen content, empty store) -> cold scan
   WARM   fresh fixture page D, memory seeded by TEACH
          -> rule replay (instant) or carried-model walk or rescan
   CONTROL  fixture A re-run with TEACH memory

Same DOM structure, different content on every fixture: title/h1/body differ,
affordance labels (click me / your name / go) and selectors (#txt, #go) are
content-invariant -- the same discipline the archive/hash/code-repair probes
use. Goal: fill #txt with "abc" and submit the form -- predicate over the
LIVE page, never a re-read. Authority NONE. Producer-run sandbox measurement.
No model calls, no network beyond 127.0.0.1, $0.
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

from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.browser_page_env_v1 import build_page_env

GOAL = "fill the input with 'abc' and submit the form"
GOAL_FAMILY = "generic"
KIND = "browser_page"
BUDGET = 6
MAX_DEPTH = 6

ACTIONS = ["fill:#txt:abc", "click:go"]

FIXTURE_BODY = """<h1>{h1}</h1>
  <p id="intro">{intro}</p>
  <div>counter=<span id="n">0</span></div>
  <button id="btn" onclick="document.getElementById('n').textContent=String(Number(document.getElementById('n').textContent)+1)">click me</button>
  <input id="txt" type="text" placeholder="your name" oninput="document.getElementById('rev').textContent=String(document.getElementById('txt').value).split('').reverse().join('')">
  <div id="rev"></div>
  <form onsubmit="event.preventDefault();document.getElementById('done').textContent='submitted:'+document.getElementById('txt').value">
    <button type="submit" id="go">go</button>
  </form>
  <div id="done"></div>"""


def _fixture_html(title: str, h1: str, intro: str) -> str:
    return ("<!doctype html><html><head><title>%s</title></head><body>\n"
            "%s\n</body></html>" % (title, FIXTURE_BODY.format(h1=h1, intro=intro)))


def _serve(directory: Path):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _predicate(state) -> bool:
    try:
        return "submitted:abc" in str(state.get("text") or "")
    except Exception:
        return False


class FreshFixture:
    """One live fixture page + its server, owned by the probe."""

    def __init__(self, servers: list, title: str, h1: str, intro: str):
        td = Path(tempfile.mkdtemp(prefix="unseen_browser_page_"))
        self.root = td / "page"
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "page.html").write_text(_fixture_html(title, h1, intro),
                                             encoding="utf-8")
        self.server = _serve(self.root)
        servers.append(self.server)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/page.html"
        self._td = td

    def close_server(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass


def _run(name, url, mem_path, fresh, results):
    rec: dict = {"case": name, "goal": GOAL, "kind": KIND, "url": url}
    env, meta = build_page_env(url, ACTIONS, goal_predicate=_predicate)
    kwargs = dict(
        goal_predicate=meta["is_goal"], env_kind=KIND, memory_path_=mem_path,
        budget=BUDGET, max_depth=MAX_DEPTH, heuristic=meta["heuristic"],
    )
    fresh_instances = list(fresh) if fresh else None
    if fresh_instances:
        kwargs.update(dict(
            unseen_instances=fresh_instances,
            fresh_reset=lambda e: e.reset(),
            fresh_act=lambda e, a: e.act(a),
            fresh_state=lambda e: e.state(),
        ))
    t0 = time.time()
    out = pa.run(env, GOAL, env.action_names(), **kwargs)
    duration = time.time() - t0
    steps = out.get("steps") or {}
    admit = steps.get("admit") or {}
    rec["result"] = {
        "pass": bool(out.get("pass")),
        "status": out.get("status"),
        "outcome": out.get("outcome"),
        "admit_verdict": admit.get("verdict"),
        "admit_reached": admit.get("reached"),
        "admit_rows": admit.get("rows"),
        "admit_persist": admit.get("persist"),
        "plan_sketch": (steps.get("learn") or {}).get("plan_sketch"),
        "memory_replay": steps.get("memory_replay"),
        "duration_s": round(duration, 3),
    }
    results.append(rec)
    try:
        env.close()
    except Exception:
        pass
    for fe in (fresh or []):
        try:
            fe.close()
        except Exception:
            pass


def main():
    servers: list = []
    results: list[dict] = []

    try:
        a = FreshFixture(servers, "Probe A", "Probe A", "the first page")
        b = FreshFixture(servers, "Probe B", "Probe B", "the second page")
        c = FreshFixture(servers, "Probe C", "Probe C", "the third page")
        d = FreshFixture(servers, "Probe D", "Probe D", "the fourth page")

        td = Path(tempfile.mkdtemp(prefix="unseen_browser_page_memory_"))
        mem = td / "memory.json"

        def fresh_envs(fixtures):
            return [build_page_env(f.url, ACTIONS, goal_predicate=_predicate)[0]
                    for f in fixtures]

        # ---- TEACH: fixture A, admission on fresh B,C ----
        _run("TEACH", a.url, mem, fresh_envs([b, c]), results)

        # ---- COLD: fresh content, empty store ----
        _run("COLD", d.url, td / "cold_memory.json", None, results)

        # ---- WARM: fresh content, memory seeded by TEACH ----
        _run("WARM", d.url, mem, None, results)

        # ---- CONTROL: fixture A, memory seeded by TEACH ----
        _run("CONTROL", a.url, mem, None, results)
    finally:
        for s in servers:
            try:
                s.shutdown()
                s.server_close()
            except Exception:
                pass

    ok_teaches = next((r for r in results if r["case"] == "TEACH"), None)
    print(json.dumps({"results": results}, indent=1, sort_keys=True))

    all_checked = {r["case"]: r["result"] for r in results}
    fails = []
    if not (ok_teaches and ok_teaches["result"].get("pass")
            and ok_teaches["result"].get("admit_verdict") == "ADMIT"):
        fails.append("TEACH did not ADMIT")
    cold = all_checked.get("COLD")
    if not (cold and cold.get("pass")):
        fails.append("COLD did not pass")
    warm = all_checked.get("WARM")
    if not (warm and warm.get("pass")):
        fails.append("WARM did not pass")
    ctrl = all_checked.get("CONTROL")
    if not (ctrl and ctrl.get("pass")):
        fails.append("CONTROL did not pass")
    if fails:
        print("PROBE: FAIL — " + "; ".join(fails))
        return 1
    print("PROBE: PASS — TEACH/COLD/WARM/CONTROL all verified live")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
