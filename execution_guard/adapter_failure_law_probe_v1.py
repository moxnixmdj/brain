"""Does running a capability on a bad request inform the caller, or kill the process?

The brain is meant to run many capabilities in one life.  A capability that reports failure by
terminating the interpreter cannot be composed with anything, cannot be retried, and cannot even
be named in the error the caller sees -- the caller is gone.

This measures the law "A CAPABILITY MAY NOT KILL THE PROCESS THAT CALLED IT" over every verified
capability that could violate it:

  CENSUS    which adapters report failure with a process-exit call
            (`raise SystemExit(...)`, `sys.exit(...)`, `os._exit(...)`).
  PROBE     for each of them, in its OWN subprocess, run the least-informed request a caller can
            make (`run_adapter_locally(entry, {})`) and read what came back:
              TYPED_REFUSAL     a failure object the caller can act on
              PROCESS_KILLED    the subprocess died with no verdict
              ACCEPTED          it returned a dict, i.e. the empty request was treated as work
            A subprocess per capability is deliberate: the thing under test is process death, so
            it cannot be observed from inside the process that would die.

    python3 execution_guard/adapter_failure_law_probe_v1.py [--json OUT] [--only ids]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXIT_PATTERN = re.compile(r"\b(?:raise\s+SystemExit|sys\.exit|os\._exit)\s*\(")

CHILD = r'''
import json, sys, traceback
sys.path.insert(0, %(root)r)
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime import live_brain_route_admission_v1 as adm
cid = %(cid)r
entry = live.load_verified_registry().get(cid) or {}
try:
    result = adm.run_adapter_locally(entry, {"type": "invoke_capability", "args": {}})
except Exception as exc:                  # NOT BaseException: SystemExit IS the finding
    # The prefix matters: a killed adapter prints its OWN json error body to stdout, so
    # "the last json line" was read as a verdict and reported a process death as a refusal.
    print("PROBE_VERDICT " + json.dumps({"verdict": "TYPED_REFUSAL",
                                         "kind": type(exc).__name__,
                                         "detail": str(exc)[:300]}))
else:
    print("PROBE_VERDICT " + json.dumps({"verdict": "ACCEPTED", "result": str(result)[:300]}))
'''


def census() -> dict[str, list[str]]:
    """Capability ids whose adapter can end the process, and the adapter file for each."""
    from canonical.runtime import live_integrated_brain_v1 as live

    registry = live.load_verified_registry()
    base = ROOT / "canonical/runtime/bound_capabilities"
    out: dict[str, list[str]] = {}
    for cid, entry in sorted(registry.items()):
        module_name = str(entry.get("adapter_module") or "")
        path = base / (module_name + ".py")
        if not module_name or not path.is_file():
            continue
        if EXIT_PATTERN.search(path.read_text(encoding="utf-8", errors="replace")):
            out[cid] = [str(path.relative_to(ROOT))]
    return out


def probe(cid: str) -> dict:
    script = CHILD % {"root": str(ROOT), "cid": cid}
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                          cwd=str(ROOT), timeout=300)
    line = ""
    for candidate in reversed(proc.stdout.splitlines()):
        if candidate.startswith("PROBE_VERDICT "):
            line = candidate[len("PROBE_VERDICT "):]
            break
    if line:
        row = json.loads(line)
    else:
        # SystemExit(0) is still a process kill for the caller's purposes: the call never
        # returned a verdict.  The returncode tells a clean exit from a crash.
        row = {"verdict": "PROCESS_KILLED",
               "detail": (proc.stderr.strip().splitlines() or [""])[-1][:200],
               "returncode": proc.returncode}
    row["capability"] = cid
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--only", default="")
    ns = ap.parse_args()

    doomed = census()
    if ns.only:
        keep = set(ns.only.split(","))
        doomed = {cid: paths for cid, paths in doomed.items() if cid in keep or any(p in keep for p in paths)}
    rows = [probe(cid) for cid in sorted(doomed)]
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
        print("%-8s %-56s %s" % (row["verdict"], row["capability"][:56],
                                 str(row.get("detail") or row.get("kind") or "")[:60]))
    killed = [r["capability"] for r in rows if r["verdict"] == "PROCESS_KILLED"]
    print("\nadapters that can end the process: %d" % len(doomed))
    print(json.dumps(counts, sort_keys=True))
    if killed:
        print("callers killed with no verdict: %d" % len(killed))
    if ns.json:
        Path(ns.json).write_text(json.dumps({"counts": counts, "census": len(doomed),
                                             "rows": rows}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
