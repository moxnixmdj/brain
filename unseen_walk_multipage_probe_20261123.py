#!/usr/bin/env python3
"""Carried-model walk over a two-page workflow (§31).

§30 measured the carried-model walk on a single live page (same-content
CONTROL reached via walk, different-content refused honestly with 0 edges).
§29 measured the two-page workflow loop (rule replay instant). Neither
measured the carried-model walk over a MULTI-PAGE chain: enter data on page A,
submit, land on page B, verify the result — with a real cross-page redirect
and a carried state key that changes identity across the redirect.

This probe runs §30's honest priors-only construction over the §29 fixture:

  TEACH-NO-FRESH  cold scan on fixture A (no fresh instances offered) ->
                 admit REFUSED -> PRIORS persisted, no rule stored.
  WALK-D          fresh fixture D (different text content) against the
                 priors-only memory -> honest expectation: warm-walk refused
                 (0 edges, content-derived keys) -> full scan -> PASS.
  WALK-A          fixture A (same content) against the priors-only memory ->
                 honest expectation: the carried walk reaches the goal
                 across the redirect -> PASS.

Same DOM structure on every fixture; different titles/bodies. Goal predicate
content-exact over the live page text after the redirect (never a re-read).
No model calls, no network beyond 127.0.0.1, $0. Authority NONE.
Producer-run sandbox measurement.
"""
from __future__ import annotations

import functools
import http.server
import json
import shutil
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
    def __init__(self, servers, title_a, h1_a, title_b, h1_b, intro):
        self.td = Path(tempfile.mkdtemp(prefix="unseen_walk_multipage_"))
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


def _run(name, url, mem_path, results):
    rec: dict = {"case": name, "goal": GOAL, "kind": KIND, "url": url}
    env, meta = build_page_env(url, ACTIONS, goal_predicate=_predicate,
                               wait_s=0.7)
    kwargs = dict(
        goal_predicate=meta["is_goal"], env_kind=KIND, memory_path_=mem_path,
        budget=BUDGET, max_depth=MAX_DEPTH, heuristic=meta["heuristic"],
    )
    t0 = time.time()
    out = pa.run(env, GOAL, env.action_names(), **kwargs)
    duration = time.time() - t0
    steps = out.get("steps") or {}
    admit = steps.get("admit") or {}
    walk = steps.get("warm_walk")
    scan = steps.get("scan")
    rec["result"] = {
        "pass": bool(out.get("pass")),
        "status": out.get("status"),
        "outcome": out.get("outcome"),
        "admit_verdict": admit.get("verdict"),
        "admit_persist": admit.get("persist"),
        "plan_sketch": (steps.get("learn") or {}).get("plan_sketch"),
        "warm_walk": walk,
        "warm_path": ("carried_walk" if walk and walk.get("status", "").startswith("PASS") else
                      "carried_walk_attempted" if walk else
                      "full_scan"),
        "scan_states": (scan or {}).get("states_seen"),
        "duration_s": round(duration, 3),
    }
    results.append(rec)
    try:
        env.close()
    except Exception:
        pass


def main():
    servers: list = []
    results: list[dict] = []
    try:
        a = MultiFixture(servers, "Walk A Probe", "Walk A", "Result A", "Result",
                         "the first workflow")
        d = MultiFixture(servers, "Walk D Probe", "Walk D", "Result D", "Result",
                         "the fourth workflow")

        td = Path(tempfile.mkdtemp(prefix="unseen_walk_multipage_memory_"))
        teach_mem = td / "teach_memory.json"

        # ---- TEACH-NO-FRESH: fixture A; no fresh instances offered ----
        # admission must REFUSE (no fresh to replay) -> no rule persisted;
        # priors must still be saved.
        _run("TEACH-NO-FRESH", a.url_a, teach_mem, results)

        # The walk arms each get their own read-only copy of the TEACH memory.
        # (A shared file would be overwritten by a walk arm's own full-scan
        # priors-save -- the defect §30 caught.)
        walk_d_mem = td / "walk_d_memory.json"
        walk_a_mem = td / "walk_a_memory.json"
        shutil.copyfile(teach_mem, walk_d_mem)
        shutil.copyfile(teach_mem, walk_a_mem)

        # ---- WALK-D: fresh fixture D (different content), priors-only memory ----
        _run("WALK-D", d.url_a, walk_d_mem, results)

        # ---- WALK-A: fixture A (same content), priors-only memory ----
        _run("WALK-A", a.url_a, walk_a_mem, results)
    finally:
        for s in servers:
            try:
                s.shutdown()
                s.server_close()
            except Exception:
                pass

    print(json.dumps({"results": results}, indent=1, sort_keys=True))

    by_case = {r["case"]: r["result"] for r in results}
    fails = []

    teach = by_case.get("TEACH-NO-FRESH")
    if not (teach and teach.get("pass")):
        fails.append("TEACH-NO-FRESH did not pass")
    if not (teach and teach.get("admit_verdict") == "REFUSED"):
        fails.append("TEACH-NO-FRESH did not REFUSE admission")
    if not (teach and teach.get("admit_persist") is False):
        fails.append("TEACH-NO-FRESH persisted a rule without admission")

    wd = by_case.get("WALK-D")
    if not (wd and wd.get("pass")):
        fails.append("WALK-D did not pass")
    wd_walk = (wd or {}).get("warm_walk") or {}
    if not (wd_walk and wd_walk.get("status") == "OPEN__CARRIED_WALK_FAILED"):
        fails.append("WALK-D did not honestly refuse the carried walk")
    wd_edges = (((wd_walk or {}).get("counters") or {}).get("edges") or 0)
    if wd_edges != 0:
        fails.append("WALK-D walk explored edges across content (keys must not carry)")

    wa = by_case.get("WALK-A")
    if not (wa and wa.get("pass")):
        fails.append("WALK-A did not pass")
    if not (wa and wa.get("outcome") == "CARRIED_MODEL_WALK_REACHED"):
        fails.append("WALK-A did not reach the goal via the carried walk")
    wa_walk = (wa or {}).get("warm_walk") or {}
    if not (wa_walk and str(wa_walk.get("status") or "").startswith("PASS")):
        fails.append("WALK-A walk receipt is not a PASS")

    if fails:
        print("PROBE: FAIL — " + "; ".join(fails))
        return 1

    teach_dur = teach.get("duration_s")
    wd_dur = wd.get("duration_s")
    wa_dur = wa.get("duration_s")
    wa_counters = ((wa_walk or {}).get("counters") or {})
    print("PROBE: PASS — TEACH-NO-FRESH pass + REFUSED; WALK-D honest refusal + full scan; "
          f"WALK-A carried walk reached ({wa_dur}s, "
          f"{wa_counters.get('act_calls')} act calls, {wa_counters.get('edges')} edges, "
          f"{wa_counters.get('resets')} resets)")
    print(f"  durations: TEACH {teach_dur}s  WALK-D {wd_dur}s  WALK-A {wa_dur}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
