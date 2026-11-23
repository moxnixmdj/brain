#!/usr/bin/env python3
"""Carried-walk durability across the process boundary — multi-page (§37).

§30/§31 measured the carried-model walk within ONE process (single-page and
the two-page redirect shape); §36 measured the single-page carried walk across
the process boundary (TEACH in process A -> disk priors-only memory -> fresh
processes B/C replay from disk). §33/§34 measured RULE REPLAY durability
(single-page and the two-page redirect shape). The multi-page carried walk
across the process boundary — enter data on page A, land on page B — is the
last unmeasured cell in the carried-walk durability matrix. §37 closes it:
§31's honest priors-only construction over the §29 two-page fixture, with the
WARM arms running in FRESH processes reading only the disk file.

Honest design:
  - Parent builds fresh fixtures A, D (shared HTTP servers, parent-owned);
    children never own servers.
  - CHILD_A (process A): TEACH-NO-FRESH on fixture A's page A -> admission
    REFUSED (no fresh instances) -> priors persisted to disk, no rule.
  - Parent copies the priors-only memory to per-arm files (the warm arms' own
    full-scan save would overwrite a shared file — §30's trap).
  - CHILD_B (fresh process): WALK-D on fresh fixture D (different content)
    against the disk-loaded priors-only memory -> honest expectation: carried
    walk refused (0 edges, content-derived keys) -> full scan re-derives -> PASS.
  - CHILD_C (fresh process): WALK-A on fixture A (same content) against the
    disk-loaded priors-only memory -> honest expectation: carried walk reaches
    the goal across the redirect -> PASS.

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


def _serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class MultiFixture:
    def __init__(self, servers, title_a, h1_a, title_b, h1_b, intro, tag):
        td = Path(tempfile.mkdtemp(prefix=f"unseen_walkxcr_multi_{tag}_"))
        self.root = td / "page"
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "a.html").write_text(
            PAGE_A_HTML.format(title_a=title_a, h1_a=h1_a, intro=intro),
            encoding="utf-8")
        (self.root / "b.html").write_text(
            PAGE_B_HTML.format(title_b=title_b, h1_b=h1_b),
            encoding="utf-8")
        self.server = _serve(self.root)
        servers.append(self.server)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/a.html"

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

goal = "fill the name on page A and land on page B with the result"
actions = ["fill:#txt:abc", "click:go"]
env, meta = build_page_env(url_a, actions, goal_predicate=pred, wait_s=0.7)
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

goal = "fill the name on page A and land on page B with the result"
actions = ["fill:#txt:abc", "click:go"]
env, meta = build_page_env(url, actions, goal_predicate=pred, wait_s=0.7)
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


def _walk_counter(out: str, key: str):
    for line in out.splitlines():
        if key in line:
            m = re.search(re.escape(key) + r"\s*(\d+)", line)
            if m:
                return int(m.group(1))
            return None
    return None


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
        a = MultiFixture(servers, "Walkxcr A", "Walkxcr A", "Result A", "Result",
                         "the first workflow", "a")
        d = MultiFixture(servers, "Walkxcr D", "Walkxcr D", "Result D", "Result",
                         "the fourth workflow", "d")

        td = Path(tempfile.mkdtemp(prefix="unseen_walkxcr_multi_memory_"))
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
        print("summary:", json.dumps({k: v for k, v in results.items()
                                      if k not in ("walk_d_out", "walk_a_out")}, indent=1))

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

        print("PROBE: PASS — multi-page carried walk persists across the process boundary: "
              "process A TEACH -> disk priors-only memory -> fresh process B honestly "
              "refuses the walk across content -> full scan re-derives -> PASS; fresh "
              "process C walks the carried model across the redirect -> "
              "PASS__CARRIED_WALK_REACHED_GOAL")
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


if __name__ == "__main__":
    raise SystemExit(main())
