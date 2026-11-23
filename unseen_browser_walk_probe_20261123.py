#!/usr/bin/env python3
"""Carried-model walk on live pages (§30).

§28/§29 measured the Perfect-Algorithm loop on live pages — and its WARM and
CONTROL arms passed via instant RULE REPLAY (the stored plan executes, the
goal is observed). The carried-model WALK path — the within-kind transfer
mechanism, the one §27/§29/§30 were designed for — has never been measured on
a live page. §10 (archives) measured it honestly and found it refuses across
content: the carried model's keys are content-derived (state_key hashes the
observed page: title, text, elements), so a fresh page's root is absent from
the taught model and the walk explores 0 edges.

This probe measures the same question on a live page, honestly, via the
§10 priors-only construction:

  TEACH-NO-FRESH  cold scan on fixture A (no fresh instances offered) ->
                  admit REFUSED -> PRIORS persisted, no rule stored.
  WALK-D          fresh fixture D (different text content) against the
                  priors-only memory -> honest expectation: warm-walk refused
                  (0 edges, content-derived keys) -> full scan re-derives -> PASS.
  WALK-A          fixture A (same content) against the priors-only memory ->
                  honest expectation: warm-walk reaches the goal -> PASS.

Same DOM structure, different text/title/body content on every fixture.
Goal predicate content-exact over the LIVE page (never a re-read).
Authority NONE. Producer-run sandbox measurement. No model calls,
no network beyond 127.0.0.1, $0.
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
    def __init__(self, servers: list, title: str, h1: str, intro: str):
        td = Path(tempfile.mkdtemp(prefix="unseen_walk_pages_"))
        self.root = td / "page"
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "page.html").write_text(
            _fixture_html(title, h1, intro), encoding="utf-8")
        self.server = _serve(self.root)
        servers.append(self.server)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/page.html"
        self._td = td

    def close(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass


def _run(name, url, mem_path, results):
    rec: dict = {"case": name, "goal": GOAL, "kind": KIND, "url": url}
    env, meta = build_page_env(url, ACTIONS, goal_predicate=_predicate)
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
    mem_replay = steps.get("memory_replay")
    rec["result"] = {
        "pass": bool(out.get("pass")),
        "status": out.get("status"),
        "outcome": out.get("outcome"),
        "admit_verdict": admit.get("verdict"),
        "admit_persist": admit.get("persist"),
        "plan_sketch": (steps.get("learn") or {}).get("plan_sketch"),
        "memory_replay": mem_replay,
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
        a = FreshFixture(servers, "Walk A Probe", "Walk A", "the first page")
        d = FreshFixture(servers, "Walk D Probe", "Walk D", "the fourth page")

        td = Path(tempfile.mkdtemp(prefix="unseen_walk_pages_memory_"))
        teach_mem = td / "teach_memory.json"

        # ---- TEACH-NO-FRESH: fixture A; no fresh instances offered ----
        # admission must REFUSE (no fresh to replay) -> no rule persisted;
        # priors must still be saved.
        _run("TEACH-NO-FRESH", a.url, teach_mem, results)

        # The walk arms each get their own read-only copy of the TEACH memory.
        # (A single shared file is silently OVERWRITTEN by a walk arm's own
        # full-scan priors-save -- the exact failure this probe must not hide.)
        import shutil
        walk_d_mem = td / "walk_d_memory.json"
        walk_a_mem = td / "walk_a_memory.json"
        shutil.copyfile(teach_mem, walk_d_mem)
        shutil.copyfile(teach_mem, walk_a_mem)

        # ---- WALK-D: fresh fixture D (different content), priors-only memory ----
        # honest expectation: walk refused (0 edges) -> full scan re-derives
        _run("WALK-D", d.url, walk_d_mem, results)

        # ---- WALK-A: fixture A (same content), priors-only memory ----
        # honest expectation: walk reaches the goal via the live page
        _run("WALK-A", a.url, walk_a_mem, results)
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
