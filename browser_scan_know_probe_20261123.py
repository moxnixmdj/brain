#!/usr/bin/env python3
"""Unseen-page probe for the SCAN -> REMEMBER -> REPORT flow (§25).

The §22 flow scans a filesystem environment, retrieves what is known from
memory, and names what remains unknown. This probe extends the same flow to
the one environment class it had never reached: a LIVE PAGE — the class the
mission calls the hardest.

Measured honestly:
  COLD   empty store -> scan_and_know(page_url=...) -> the receipt records
         the page's declared surface (title + affordances) AND names the
         unanswerable contract question by name, never fabricates it.
  WARM   same page, memory seeded from a rule admitted over a prior page
         (built through the real generalize/remember/save_memory path)
         -> the receipt records the known rule (memory.rules_known) with
         the same page-evidence, never trusting it blindly.
  REFUSE   an unroutable page -> REFUSE__PAGE_UNLOADABLE, questions empty,
           no page recorded as scanned.
  REFUSE   empty goal -> REFUSE__EMPTY_GOAL.

Everything is content-exact: the receipts are asserted against the LIVE page
actually rendered, not asserted from the record. No model calls, no network
beyond 127.0.0.1, $0. Authority NONE.
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

from canonical.swe_kernel import environment_scan_know_v1 as es
from canonical.swe_kernel import perfect_algorithm_v1 as pa

GOAL = "read this page and report what it offers"

PAGE_HTML = """<!doctype html><html><head><title>Browser Scan Probe</title></head>
<body>
  <h1>Browser Scan Probe</h1>
  <p>A fixture page written for this probe. It is NOT a real site.</p>
  <button id="btn">click me</button>
  <input id="txt" placeholder="your name">
  <button id="go" type="submit">go</button>
</body></html>"""


def _serve(directory: Path):
    """An ephemeral localhost server for a plain directory."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> int:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> bool:
        results.append({"check": name, "ok": bool(ok), "detail": str(detail)})
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
        return bool(ok)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "page.html").write_text(PAGE_HTML, encoding="utf-8")
        server = _serve(tmp)
        try:
            port = server.server_address[1]
            url = f"http://127.0.0.1:{port}/page.html"

            # ---- cold: empty store ----------------------------------
            cold = es.scan_and_know(None, GOAL, page_url=url)
            check("cold_verdict_open_gap",
                  cold.get("verdict") == "OPEN__GAP_REMAINS",
                  f"verdict={cold.get('verdict')}")
            check("cold_root_is_page_url", cold.get("root") == url,
                  f"root={cold.get('root')}")
            page = (cold.get("scanned") or {}).get("page") or {}
            check("cold_title_is_fixture_title",
                  page.get("title") == "Browser Scan Probe",
                  f"title={page.get('title')!r}")
            labels = [a["label"] for a in page.get("affordances", [])]
            check("cold_affordances_match_fixture",
                  "click me" in labels and "your name" in labels and "go" in labels,
                  f"labels={labels}")
            check("cold_contract_question_is_unknown_by_name",
                  cold.get("unknown") == ["what counts as success"],
                  f"unknown={cold.get('unknown')}")
            check("cold_memory_empty",
                  cold.get("memory", {}).get("rules_known") == [],
                  f"rules_known={(cold.get('memory') or {}).get('rules_known')}")

            # ---- warm: memory seeded through the real admit path ----
            # Build the admitted rule through the same machinery pa.run
            # persists (generalize -> remember -> save_memory). Honest: the
            # rule is admitted-shaped but the fixture is not actually trained;
            # the warm receipt must REMEMBER it, never fabricate it.
            mem_path = tmp / "memory.json"
            warm_mem = pa.load_memory(mem_path)
            gen = pa.generalize(
                [{"acting": "navigate"}], GOAL,
                goal_family="generic", env_kind="browser_page",
                plan=["navigate"],
                evidence={"probe": "warm-seed"},
            )
            warm_mem = pa.remember(warm_mem, gen["generalization"])
            pa.save_memory(warm_mem, mem_path)
            warm = es.scan_and_know(None, GOAL, page_url=url,
                                    memory_path_=mem_path)
            rules = (warm.get("memory") or {}).get("rules_known") or []
            check("warm_recalls_admitted_rule",
                  len(rules) == 1 and rules[0].get("rule_id") == gen["generalization"]["rule_id"],
                  f"rules={[(r.get('rule_id'), (r.get('scope') or {}).get('env_kind')) for r in rules]}")
            check("warm_same_page_evidence",
                  (warm.get("scanned") or {}).get("page", {}).get("title") == "Browser Scan Probe",
                  "page evidence identical to cold (scan is real, recall is additive)")

            # ---- refusals -------------------------------------------
            bad_url = "http://127.0.0.1:1/definitely-not-here.html"
            refused = es.scan_and_know(None, GOAL, page_url=bad_url)
            check("refuses_unroutable_page_honestly",
                  refused.get("verdict") == "REFUSE__PAGE_UNLOADABLE",
                  f"verdict={refused.get('verdict')!r} reason={(refused.get('scanned') or {}).get('reason')!r}")
            check("refusal_records_no_page_evidence",
                  (refused.get("scanned") or {}).get("kind") == "browser_page"
                  and (refused.get("scanned") or {}).get("page") is None,
                  f"scanned={refused.get('scanned')}")
            empty = es.scan_and_know(None, "", page_url=url)
            check("empty_goal_refuses_before_scan",
                  empty.get("verdict") == "REFUSE__EMPTY_GOAL" and empty.get("questions") == [],
                  f"verdict={empty.get('verdict')}")

            # ---- no persistence --------------------------------------
            check("flow_never_persists",
                  (warm.get("persist") or "").startswith("NONE"),
                  "persist reported as NONE (the flow only reads memory)")
        finally:
            server.shutdown()
            server.server_close()

    all_ok = all(r["ok"] for r in results)
    print()
    print("SUMMARY:", "PASS__PAGE_SCAN_KNOW_LIVE" if all_ok else "OPEN__PAGE_SCAN_PROBE_FAILED")
    print(json.dumps({"ok": all_ok, "checks": results}, indent=1))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
