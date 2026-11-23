#!/usr/bin/env python3
"""Unseen-content probe for the CODE-REPAIR direction (2026-11-23).

The Perfect Algorithm specialist twin (learn_and_admit_code_repair) with REAL,
repo-shaped files. Honestly measured:

  1. teach the strict/inclusive boundary lesson from one pair;
  2. admit via the gate on a held-out REPAIRED defect and a held-out PRESERVED
     (already-correct) defect -- not just any two broken snippets;
  3. persist the admitted rule to an on-disk store;
  4. replay the rule on a fresh (never-taught) defect file: apply the rule,
     materialize the repaired file, run the real failing test in a subprocess;
  5. cross-process: a completely fresh process loads only the store and replays
     the rule on another fresh defect file, executed for real.

Zero model calls, zero network, $0.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PHASE_TEACH = r'''
import sys
from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.lesson_admission_gate_v1 import Victim

mem = pa.load_memory(sys.argv[1])
BEFORE = "def add_check(x):\n    return x <= 100\n"
AFTER  = "def add_check(x):\n    return x < 100\n"
POINTS = (0, 99, 100, 101, 1001, 5000)

def strict_spec(_source, point):
    return point < 100

# held-out: a defect in another function this lesson never saw
transfer = Victim("transfer_defect",
                  "def tally(z):\n    return z <= 100\n",
                  strict_spec, POINTS)
# held-out: already correct under its own contract, rule must not break it
guarded = Victim("guarded_ok",
                 "def bounded(n):\n    if n > 1000:\n        return n <= 100\n    return n < 100\n",
                 strict_spec, POINTS)

out = pa.learn_and_admit_code_repair(
    BEFORE, AFTER, [transfer, guarded],
    memory=mem, memory_path_=sys.argv[1],
)
print("verdict:", out["verdict"], "persist:", out.get("persist"),
      "rule_id:", (out.get("generalization") or {}).get("rule_id"))
print("reason:", out.get("reason"))
print("counts:", (out.get("gate") or {}).get("counts"))
'''

PHASE_REPLAY = r'''
import subprocess, sys, tempfile
from pathlib import Path
from canonical.swe_kernel import perfect_algorithm_v1 as pa

mem = pa.load_memory(sys.argv[1])
rules = [r for r in mem.get("rules") or [] if r.get("kind") == "code_rule"]
print("code_rule rules on disk:", len(rules))
if not rules:
    print("NO_RULES_ON_DISK"); sys.exit(1)
rule = rules[0]["rule"]

POINTS = (0, 99, 100, 101, 1001, 5000)
probe_out = pa.replay_code_repair(
    rule,
    "def count_ok(n):\n    return n <= 100\n",
    lambda _s, point: point < 100,
    list(POINTS))
print("replay verdict:", probe_out["verdict"], "passed:", probe_out["passed"])

repaired = (probe_out.get("repaired_source") or "").strip()
if repaired:
    tmp = Path(tempfile.mkdtemp(prefix="code_repair_replay_"))
    (tmp / "fresh_module.py").write_text(repaired)
    (tmp / "test_fresh.py").write_text(
        "from fresh_module import count_ok\n"
        "assert count_ok(0) is True\n"
        "assert count_ok(99) is True\n"
        "assert count_ok(100) is False\n"
        "assert count_ok(101) is False\n"
        "print('PASS')\n")
    proc = subprocess.run([sys.executable, "test_fresh.py"],
                          cwd=str(tmp), capture_output=True, text=True, timeout=15)
    print("real test stdout:", proc.stdout.strip()[:100])
    print("real test rc:", proc.returncode)
    print("REAL-FILE REPAIR VERIFIED:", proc.returncode == 0 and "PASS" in proc.stdout)
'''

PHASE_REPLAY_FRESH_PROCESS = r'''
import subprocess, sys, tempfile
from pathlib import Path
from canonical.swe_kernel import perfect_algorithm_v1 as pa

mem = pa.load_memory(sys.argv[1])
rules = [r for r in mem.get("rules") or [] if r.get("kind") == "code_rule"]
print("FRESH-PROCESS rules on disk:", len(rules))
rule = rules[0]["rule"]

POINTS = (0, 99, 100, 101, 1001, 5000)
probe_out = pa.replay_code_repair(
    rule,
    "def window(z):\n    return z <= 100\n",
    lambda _s, point: point < 100,
    list(POINTS))
print("replay verdict:", probe_out["verdict"], "passed:", probe_out["passed"])

repaired = (probe_out.get("repaired_source") or "").strip()
if repaired:
    tmp = Path(tempfile.mkdtemp(prefix="code_repair_fresh2_"))
    (tmp / "fresh_module.py").write_text(repaired)
    (tmp / "test_fresh.py").write_text(
        "from fresh_module import window\n"
        "assert window(0) is True\n"
        "assert window(99) is True\n"
        "assert window(100) is False\n"
        "assert window(101) is False\n"
        "print('PASS')\n")
    proc = subprocess.run([sys.executable, "test_fresh.py"],
                          cwd=str(tmp), capture_output=True, text=True, timeout=15)
    print("real test stdout:", proc.stdout.strip()[:100])
    print("FRESH-PROCESS REAL-FILE REPAIR VERIFIED:",
          proc.returncode == 0 and "PASS" in proc.stdout)
'''


def run_phase(name, code, argv):
    proc = subprocess.run([sys.executable, "-c", code] + argv,
                          capture_output=True, text=True,
                          cwd=str(ROOT), timeout=200)
    print(f"--- {name} (rc={proc.returncode}) stdout ---")
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print("STDERR:", proc.stderr.strip()[-2000:])
    return proc.returncode


def main():
    tmp = Path(tempfile.mkdtemp(prefix="code_repair_probe_"))
    mem = tmp / "memory.json"

    rc1 = run_phase("TEACH (in-process)", PHASE_TEACH, [str(mem)])

    rc2 = run_phase("REPLAY (same process)", PHASE_REPLAY, [str(mem)])

    rc3 = run_phase("FRESH-PROCESS REPLAY", PHASE_REPLAY_FRESH_PROCESS, [str(mem)])

    print("summary rc:", rc1, rc2, rc3)


if __name__ == "__main__":
    main()
