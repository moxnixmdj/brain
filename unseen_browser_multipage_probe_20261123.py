#!/usr/bin/env python3
"""Unseen-multi-page probe (§29): the same loop, over a two-page workflow.

§28 measured the Perfect-Algorithm loop on a single page. A real computer task
is multi-page: enter data on page A, submit, land on page B, and verify the
result — data carried between pages, not re-derived. This probe extends the
SAME env (browser_page_env_v1) and the SAME admission/persistence chain over
two pages with a real cross-page transition (a URL query-param carry) — the
honest shape of a web workflow.

   TEACH  cold scan on fixture A -> plan -> verify page B -> admit on 2 fresh
          same-shape variants -> persist the rule
   COLD   fresh fixture D (different content, empty store) -> cold scan
   WARM   same fresh fixture D, memory seeded by TEACH -> rule replay
   CONTROL  fixture A re-run with TEACH memory

Content-invariant actions (same DOM structure, different titles/bodies):
  fill:#txt:abc  -- write the name into the form on page A
  click:go       -- submit; window.location redirects to /b.html?name=abc
Goal predicate (content-exact, never a re-read): "submitted:abc" in the
live page text after the redirect. Authority NONE. Producer-run sandbox
measurement. No model calls, no network beyond 127.0.0.1, $0.
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

GOAL = "fill the name on page A and land on page B with the result"
GOAL_FAMILY = "generic"
KIND = "browser_page"
BUDGET = 6
MAX_DEPTH = 6
ACTIONS = ["fill:#txt:abc", "click:go"]

PAGE_A_HTML = """<!doctype html><html><head><title>{title_a}</title></head><body>
  <h1>{h1_a}</h1>
  <p id="intro">{intro}</p>
  <form onsubmit="event.preventDefault();window.location='b.html?name='+encodeURIComponent(document.getElementById('txt').value)">
    <input id="txt" type="text" placeholder="your name">
    <button type="submit" id="go">go</button>
  </form>
</body></html>"""

PAGE_B_HTML = """<!doctype html><html><head><title>{title_b}</title></head><body>
  <h1>{h1_b}</h1>
  <div id="out"></div>
  <script>
    const params = new URLSearchParams(window.location.search);
    document.getElementById('out').textContent = 'submitted:' + (params.get('name') || '');
  </script>
</body></html>"""


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


class MultiFixture:
    """A two-page fixture served from one temp directory."""

    def __init__(self, servers, title_a, h1_a, title_b, h1_b, intro):
        self.td = Path(tempfile.mkdtemp(prefix="unseen_browser_multipage_"))
        self.root = self.td / "page"
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "a.html").write_text(
            PAGE_A_HTML.format(title_a=title_a, h1_a=h1_a, intro=intro),
            encoding="utf-8")
        (self.root / "b.html").write_text(
            PAGE_B_HTML.format(title_b=title_b, h1_b=h1_b),
            encoding="utf-8")
        self.server = _serve(self.root)
        servers.append(self.server)
        self.url_a = f"http://127.0.0.1:{self.server.server_address[1]}/a.html"

    def close(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass


def _run(name, url, mem_path, fresh, results):
    rec: dict = {"case": name, "goal": GOAL, "kind": KIND, "url": url}
    env, meta = build_page_env(url, ACTIONS, goal_predicate=_predicate,
                               wait_s=0.7)
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
        a = MultiFixture(servers, "Page A Probe", "Page A", "Result A", "Result",
                         "the first workflow")
        b = MultiFixture(servers, "Page A Probe", "Page A", "Result B", "Result B",
                         "the second workflow")
        c = MultiFixture(servers, "Page C Probe", "Page C", "Result C", "Result C",
                         "the third workflow")
        d = MultiFixture(servers, "Page D Probe", "Page D", "Result D", "Result D",
                         "the fourth workflow")

        td = Path(tempfile.mkdtemp(prefix="unseen_browser_multipage_memory_"))
        mem = td / "memory.json"

        # ---- TEACH: fixture A, admission on fresh B + fresh C ----
        env_b = build_page_env(b.url_a, ACTIONS, goal_predicate=_predicate,
                                wait_s=0.7)[0]
        env_c = build_page_env(c.url_a, ACTIONS, goal_predicate=_predicate,
                                wait_s=0.7)[0]
        _run("TEACH", a.url_a, mem, [env_b, env_c], results)

        # ---- COLD: fresh content, empty store ----
        _run("COLD", d.url_a, td / "cold_memory.json", None, results)

        # ---- WARM: fresh content, memory seeded by TEACH ----
        _run("WARM", d.url_a, mem, None, results)

        # ---- CONTROL: fixture A, memory seeded by TEACH ----
        _run("CONTROL", a.url_a, mem, None, results)
    finally:
        for s in servers:
            try:
                s.shutdown()
                s.server_close()
            except Exception:
                pass

    print(json.dumps({"results": results}, indent=1, sort_keys=True))

    all_checked = {r["case"]: r["result"] for r in results}
    fails = []
    tch = all_checked.get("TEACH")
    if not (tch and tch.get("pass") and tch.get("admit_verdict") == "ADMIT"
            and tch.get("admit_persist")):
        fails.append("TEACH did not ADMIT + persist")
    if not (all_checked.get("COLD") or {}).get("pass"):
        fails.append("COLD did not pass")
    if not (all_checked.get("WARM") or {}).get("pass"):
        fails.append("WARM did not pass")
    if not (all_checked.get("CONTROL") or {}).get("pass"):
        fails.append("CONTROL did not pass")
    if fails:
        print("PROBE: FAIL — " + "; ".join(fails))
        return 1
    print("PROBE: PASS — TEACH/COLD/WARM/CONTROL all verified live across pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
