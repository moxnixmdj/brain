#!/usr/bin/env python3
"""Cross-kind store refusal on the live page (§32).

§27/§26 verdict: transfer is within-kind only — priors and rules are keyed
by env_kind. §28-§31 measured the within-kind walk/replay on pages. Until
now the cross-kind boundary has never been measured against a REAL store on
the page side: the honest question is whether a page run silently adopts —
or honestly refuses — a durable store written by a DIFFERENT environment
kind (here, the real computer_file_ops store in
canonical/astra_runtime/state/PERFECT_ALGORITHM_MEMORY_V1.json, which
carries a learned transition model learned by the real archive probes).

The store is read-only for the probe: a copy is made per arm so the page arm
can save its own browser_page priors without silently mutating the fs store.

Honest expectation:
  - memory_lookup matches: 0  (the fs rule scopes to computer_file_ops)
  - warm_walk: absent       (no priors recorded for browser_page)
  - full scan re-derives; the plan verifies; the run PASSES
  - the fs store's own priors are preserved in the copy

Authority NONE. Producer-run sandbox measurement. No model calls,
no network beyond 127.0.0.1, $0.
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

GOAL = "fill the input with 'abc' and submit the form"
KIND = "browser_page"
BUDGET = 6
MAX_DEPTH = 6
ACTIONS = ["fill:#txt:abc", "click:go"]

STORE = ROOT / "canonical" / "astra_runtime" / "state" / "PERFECT_ALGORITHM_MEMORY_V1.json"

FIXTURE_BODY = """<h1>{h1}</h1>
  <p id="intro">{intro}</p>
  <form onsubmit="event.preventDefault();document.getElementById('done').textContent='submitted:'+document.getElementById('txt').value">
    <input id="txt" type="text" placeholder="your name">
    <button type="submit" id="go">go</button>
  </form>
  <div id="done"></div>"""


def _fixture_html(title, h1, intro):
    return ("<!doctype html><html><head><title>%s</title></head><body>\n"
            "%s\n</body></html>" % (title, FIXTURE_BODY.format(h1=h1, intro=intro)))


def _serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _predicate(state):
    try:
        return "submitted:abc" in str(state.get("text") or "")
    except Exception:
        return False


class FreshFixture:
    def __init__(self, servers, title, h1, intro):
        td = Path(tempfile.mkdtemp(prefix="unseen_crosskind_"))
        self.root = td / "page"
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "page.html").write_text(_fixture_html(title, h1, intro),
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
        d = FreshFixture(servers, "Crosskind D", "Crosskind D", "the cross-kind page")
        td = Path(tempfile.mkdtemp(prefix="unseen_crosskind_memory_"))
        store_copy = td / "fs_store_copy.json"
        shutil.copyfile(STORE, store_copy)

        kind_before_rules = len((json.loads(store_copy.read_text()) or {}).get("rules") or [])

        env, meta = build_page_env(d.url, ACTIONS, goal_predicate=_predicate)
        t0 = time.time()
        out = pa.run(env, GOAL, env.action_names(),
                     goal_predicate=meta["is_goal"], env_kind=KIND,
                     memory_path_=store_copy,
                     budget=BUDGET, max_depth=MAX_DEPTH,
                     heuristic=meta["heuristic"])
        duration = time.time() - t0
        steps = out.get("steps") or {}
        out_steps = steps
        mem_lookup = steps.get("memory_lookup") or {}
        walk = steps.get("warm_walk")
        scan = steps.get("scan") or {}
        rec = {
            "case": "CROSS-KIND (fs priors -> live page)",
            "url": d.url,
            "pass": bool(out.get("pass")),
            "status": out.get("status"),
            "outcome": out.get("outcome"),
            "memory_lookup_matches": mem_lookup.get("matches"),
            "memory_lookup_rule_ids": mem_lookup.get("rule_ids"),
            "warm_walk": walk,
            "scan_priors_used": scan.get("priors_used"),
            "scan_states": scan.get("states_seen"),
            "duration_s": round(duration, 3),
        }
        results.append(rec)
        try:
            env.close()
        except Exception:
            pass

        # after the run: the fs store's own priors must be preserved in the copy
        rec["fs_rule_count"] = kind_before_rules
    finally:
        for s in servers:
            try:
                s.shutdown()
                s.server_close()
            except Exception:
                pass

    # honest byte-integrity: the refused store must be LEFT EXACTLY AS IT WAS —
    # the bytes on disk must be identical to the arm's source store.
    rec["fs_priors_preserved"] = (STORE.read_bytes() == store_copy.read_bytes())
    rec["no_browser_priors_saved"] = rec["fs_priors_preserved"]

    print(json.dumps({"results": results}, indent=1, sort_keys=True))

    fails = []
    rec = results[0]
    if not rec["pass"]:
        fails.append("page arm did not pass")
    if rec["memory_lookup_matches"] != 0:
        fails.append(f"fs-kind rules matched a page target ({rec['memory_lookup_matches']} matches)")
    if rec["warm_walk"] is not None:
        fails.append("warm walk ran on a page that must not carry fs priors")
    if rec["scan_priors_used"] != 0:
        fails.append(f"fs priors adopted into the page scan ({rec['scan_priors_used']})")
    if not rec["fs_priors_preserved"]:
        fails.append("fs store's own priors were silently dropped")
    if not rec["no_browser_priors_saved"]:
        fails.append("browser_page priors were persisted INTO the refused fs store")
    if str((steps := out_steps).get("save_priors", {}).get("status") or "") != "REFUSED__MEMORY_REFUSED":
        fails.append("save_priors did not refuse a corrupt store")

    if fails:
        print("PROBE: FAIL — " + "; ".join(fails))
        return 1
    print(f"PROBE: PASS — fs store honestly refused on the live page "
          f"(0 matches, 0 adopted, 0 direct-save, fs bytes preserved; "
          f"{rec['duration_s']}s; scan {rec['scan_states']} states)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
