"""Run every environment and check the verdicts are still the expected ones.

Made after a long stretch of edits to shared modules: taskfile_read_v1,
explore_v1, compose_v1, autonomous_v1, interaction_v1. A change to any of
them can silently alter behaviour everywhere, and the failures this session
kept producing were all of that kind -- a fix in one place quietly
reversing a guarantee in another.

So the expectation is written down next to the case, and a mismatch is
reported rather than trusted.

Note what is deliberately expected: two environments are supposed to
REFUSE. env_hard6 is the decoy trap, where every shortcut points at the
wrong file, and env_hard has no report task at all. A sweep that expects
everything to pass would be a sweep that cannot detect a system which
started claiming success it had not earned.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical/runtime"))

STATE = "canonical/astra_runtime/state/"

CASES = [
    # environment, goal, dirs to reset before running, expected verdict
    ("env_hard4",   "produce a report from the data", ["out", "data"], True,
     "chains fetch->transform after dependency failure"),
    ("env_inplace", "format the code",                None,            True,
     "recognises work that only modifies a file"),
    ("env_hard7",   "produce a report",               None,            True,
     "verified by the environment's own check, not by filename"),
    ("env_hard6",   "produce the report",             ["out"],         False,
     "REFUSES: task named report produces a decoy"),
    ("env_hard",    "produce a report from the data", ["out"],         False,
     "REFUSES: no report task exists here"),
    ("env_monster",  "produce a report from the data", ["out", "data"], True,
     "fifteen traps at once: destroyer, decoy, chain, liar, phantoms"),
    ("env_monster2", "produce a report",              ["out"],          True,
     "MUST NOT BE POISONED: reads sources before acting"),
]


def main() -> int:
    import autonomous_v1 as A
    failures = 0
    for env, goal, reset, expected, why in CASES:
        path = Path(STATE) / env
        if not path.is_dir():
            print("MISSING  %-12s (%s)" % (env, why))
            failures += 1
            continue
        for d in reset or []:
            shutil.rmtree(path / d, ignore_errors=True)
            os.makedirs(path / d, exist_ok=True)
        try:
            verdict = A.run(goal, str(path), binary_limit=0,
                            iterations=8)["verification"]
        except Exception as exc:
            print("ERROR    %-12s %s: %s" % (env, type(exc).__name__, exc))
            failures += 1
            continue
        ok = verdict["verified"] == expected
        failures += 0 if ok else 1
        print("%-8s %-12s verified=%-5s (expected %-5s) %-30s %s"
              % ("PASS" if ok else "FAIL", env, verdict["verified"],
                 expected, verdict["reason"], why))
    print("\n%d/%d as expected" % (len(CASES) - failures, len(CASES)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
