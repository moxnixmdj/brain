#!/usr/bin/env python3
"""Carried-walk durability across the process boundary (§36).

§30 measured the carried-model walk in ONE process: TEACH-NO-FRESH on fixture A
(priors saved, no rule) -> WALK-D (different content, honest 0-edge refusal ->
full scan) and WALK-A (same content, walk reaches the goal). §33/§34 measured
cross-process persistence for RULE REPLAY (single-page + multi-page). The
carried-walk path -- the within-kind transfer mechanism itself -- has never
been measured across the process boundary.

Honest design:
  - Parent builds fresh fixtures A, D (shared HTTP servers, parent-owned);
    children never own servers.
  - CHILD_A (process A): TEACH-NO-FRESH on fixture A -> admission REFUSED
    (no fresh instances) -> priors persisted to disk, no rule.
  - Parent copies the priors-only memory to per-arm files (the walk arms' own
    full-scan save would overwrite a shared file).
  - CHILD_B (fresh process): WALK-D on fixture D (different content) against
    the disk-loaded priors-only memory -> honest expectation: carried walk
    refused (0 edges, content-derived keys) -> full scan re-derives -> PASS.
  - CHILD_C (fresh process): WALK-A on fixture A (same content) against the
    disk-loaded priors-only memory -> honest expectation: carried walk reaches
    the goal -> PASS.

Honest checks: the memory file must hold schema PROJECT_BRAIN_PA_MEMORY_V1,
>=1 priors row, 0 rules (no admission without fresh instances); children must
re-read the disk file, not an in-memory copy.

Authority NONE. Producer-run sandbox measurement. No model calls,
no network beyond 127.0.0.1, $0.
"""
from __future__ import annotations

import functools
import http.server
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def _fixture_html(title, h1, intro):
    return ("<!doctype html><html><head><title>%s</title></head><body>\n"
            "%s\n</body></html>" % (title, FIXTURE_BODY.format(h1=h1, intro=intro)))


def _serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class FreshFixture:
    def __init__(self, servers, title, h1, intro, tag):
        td = Path(tempfile.mkdtemp(prefix=f"unseen_walkxcr_page_{tag}_"))
        self.root = td / "page"
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "page.html").write_text(
            _fixture_html(title, h1, intro), encoding="utf-8")
        self.server = _serve(self.root)
        servers.append(self.server)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/page.html"

    def close(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass


CHILD_TEACH = r'''
import sys
from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.browser_page_env_v1 import build_page_env

mem, url_a = sys.argv[1], sys.argv[2]

def pred(state):
    try:
        return "submitted:abc" in str(state.get("text") or "")
    except Exception:
        return False

goal = "fill the input with 'abc' and submit the form"
actions = ["fill:#txt:abc", "click:go"]
env, meta = build_page_env(url_a, actions, goal_predicate=pred)
out = pa.run(
    env, goal, env.action_names(),
    goal_predicate=meta["is_goal"], env_kind="browser_page",
    memory_path_=mem, budget=6, max_depth=6,
    heuristic=meta["heuristic"],
)
steps = out.get("steps") or {}
print("TEACH pass:", out.get("pass"), "status:", out.get("status"),
      "outcome:", out.get("outcome"),
      "admit:", (steps.get("admit") or {}).get("verdict"),
      "persist:", (steps.get("admit") or {}).get("persist"),
      "save_priors:", (steps.get("save_priors") or {}).get("status"))
try:
    env.close()
except Exception:
    pass
'''

CHILD_WALK = r'''
import sys
from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.browser_page_env_v1 import build_page_env

mem, url = sys.argv[1], sys.argv[2]

def pred(state):
    try:
        return "submitted:abc" in str(state.get("text") or "")
    except Exception:
        return False

goal = "fill the input with 'abc' and submit the form"
actions = ["fill:#txt:abc", "click:go"]
env, meta = build_page_env(url, actions, goal_predicate=pred)
out = pa.run(
    env, goal, env.action_names(),
    goal_predicate=meta["is_goal"], env_kind="browser_page",
    memory_path_=mem, budget=6, max_depth=6,
    heuristic=meta["heuristic"],
)
steps = out.get("steps") or {}
walk = steps.get("warm_walk") or {}
scan = steps.get("scan") or {}
print("WARM-WALK pass:", out.get("pass"), "status:", out.get("status"),
      "outcome:", out.get("outcome"),
      "walk_status:", walk.get("status"),
      "walk_edges:", (walk.get("counters") or {}).get("edges"),
      "walk_act_calls:", (walk.get("counters") or {}).get("act_calls"),
      "priors_used:", walk.get("priors_used"),
      "scan_states:", scan.get("states_seen"))
try:
    env.close()
except Exception:
    pass
'''


def run_phase(name, code, argv, timeout=400):
    t0 = time.time()
    proc = subprocess.run([sys.executable, "-c", code] + argv,
                          capture_output=True, text=True,
                          cwd=str(ROOT), timeout=timeout)
    dur = time.time() - t0
    print(f"--- {name} ({round(dur,1)}s) stdout ---")
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print("STDERR:", proc.stderr.strip()[-2000:])
    return proc.returncode, proc.stdout


def main():
    servers: list = []
    results: dict = {}
    try:
        a = FreshFixture(servers, "Walkxcr A", "Walkxcr A", "the first page", "a")
        d = FreshFixture(servers, "Walkxcr D", "Walkxcr D", "the fourth page", "d")

        td = Path(tempfile.mkdtemp(prefix="unseen_walkxcr_memory_"))
        mem = td / "memory.json"

        rc1, out1 = run_phase("phase 1: TEACH-NO-FRESH (process A)", CHILD_TEACH,
                              [str(mem), a.url])
        results["teach_rc"] = rc1
        results["memory_file"] = str(mem)

        # ---- honest disk check of the TEACH memory ----
        disk = {}
        try:
            data = json.loads(mem.read_text())
            rules = data.get("rules") or []
            priors = data.get("priors") or {}
            brow = priors.get(KIND) or {}
            model = brow.get("model") or {}
            disk = {
                "schema": data.get("schema"),
                "rules": len(rules),
                "priors_model_present": bool(model),
                "priors_rows": sum(len(r or {}) for r in model.values()),
            }
        except Exception as e:
            disk = {"error": str(e)[:200]}
        results["disk_check"] = disk

        # Copy the priors-only memory to per-arm files: the warm arms' full-scan
        # save would otherwise overwrite a single shared file (§30's trap).
        import shutil
        walk_d_mem = td / "walk_d_memory.json"
        walk_a_mem = td / "walk_a_memory.json"
        shutil.copyfile(mem, walk_d_mem)
        shutil.copyfile(mem, walk_a_mem)

        rc2, out2 = run_phase("phase 2: WALK-D (process B, fresh, different content)", CHILD_WALK,
                              [str(walk_d_mem), d.url])
        results["walk_d_rc"] = rc2
        results["walk_d_out"] = out2.strip()

        rc3, out3 = run_phase("phase 3: WALK-A (process C, fresh, same content)", CHILD_WALK,
                              [str(walk_a_mem), a.url])
        results["walk_a_rc"] = rc3
        results["walk_a_out"] = out3.strip()

        print()
        print("summary:", json.dumps({k: v for k, v in results.items() if k != "walk_d_out" and k != "walk_a_out"}, indent=1))

        # ----- assertions -----
        fails = []
        if rc1 != 0:
            fails.append("TEACH phase exited non-zero")
        if "TEACH pass: True" not in out1:
            fails.append("TEACH phase did not pass")
        if "admit: REFUSED" not in out1:
            fails.append("TEACH phase did not refuse admission")
        if "persist: False" not in out1:
            fails.append("TEACH phase persisted a rule without admission")
        if "save_priors: PASS__PRIORS_SAVED" not in out1:
            fails.append("TEACH phase did not save priors")

        if disk.get("error"):
            fails.append(f"memory file unreadable: {disk['error']}")
        else:
            if disk.get("schema") != "PROJECT_BRAIN_PA_MEMORY_V1":
                fails.append(f"memory schema wrong: {disk.get('schema')}")
            if disk.get("rules") != 0:
                fails.append(f"memory holds rules without admission: {disk.get('rules')}")
            if not (disk.get("priors_model_present") and (disk.get("priors_rows") or 0) > 0):
                fails.append("memory holds no browser_page priors model")

        if rc2 != 0:
            fails.append("WALK-D phase exited non-zero")
        if "WARM-WALK pass: True" not in out2:
            fails.append("WALK-D did not pass")
        if "walk_status: OPEN__CARRIED_WALK_FAILED" not in out2:
            fails.append("WALK-D did not honestly refuse the carried walk")
        wd_edges = _walk_counter(out2, "walk_edges:")
        if wd_edges != 0:
            fails.append(f"WALK-D walk explored edges across content ({wd_edges})")
        if "outcome: CARRIED_MODEL_WALK_REACHED" in out2:
            fails.append("WALK-D walk should not reach the goal across content")

        if rc3 != 0:
            fails.append("WALK-A phase exited non-zero")
        if "WARM-WALK pass: True" not in out3:
            fails.append("WALK-A did not pass")
        if "outcome: CARRIED_MODEL_WALK_REACHED" not in out3:
            fails.append("WALK-A did not reach the goal via the carried walk")
        if "walk_status: PASS__CARRIED_WALK_REACHED_GOAL" not in out3:
            fails.append("WALK-A walk receipt is not a PASS")

        if fails:
            print("PROBE: FAIL — " + "; ".join(fails))
            return 1

        print("PROBE: PASS — carried-model walk persists across the process boundary: "
              "process A TEACH -> disk priors-only memory -> fresh process B honestly "
              "refuses the walk across content -> full scan re-derives -> PASS; fresh "
              "process C walks the carried model -> PASS__CARRIED_WALK_REACHED_GOAL")
        print(f"  disk: schema={disk.get('schema')} rules={disk.get('rules')} "
              f"priors_rows={disk.get('priors_rows')} model_present={disk.get('priors_model_present')}")
        return 0
    finally:
        for s in servers:
            try:
                s.shutdown()
                s.server_close()
            except Exception:
                pass


def _walk_counter(out: str, key: str):
    for line in out.splitlines():
        if key in line:
            m = re.search(re.escape(key) + r"\s*(\d+)", line)
            if m:
                return int(m.group(1))
            return None
    return None


if __name__ == "__main__":
    raise SystemExit(main())
