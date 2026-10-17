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

STATE = str(ROOT / "canonical/astra_runtime/state")  # absolute: runnable from anywhere

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
    # --- the browser ---------------------------------------------------
    # Two behaviours, chosen because both are easy to lose silently: the
    # loop deciding to use the browser at all, and the browser refusing to
    # act when there is no evidence. The second is the one most likely to
    # rot, because nothing fails when it is removed -- the machine simply
    # starts typing into the nearest field again.
    #
    # No browser here is a SKIP, not a FAIL. Absence is not a regression,
    # and a machine without one should not be told it is broken.
    browser_cases = 0
    try:
        import browser_v1 as B
        ok, why = B.available()
        if not ok:
            print("SKIP     browser            (%s)" % why)
        else:
            import json as _json
            import subprocess as _sp
            import os as _os
            B.ensure(["github.com"])
            browser_cases = 2

            r = A.run("what does the page at https://github.com/expressjs/express "
                      "say this project is", str(Path(STATE) / "env_hard7"),
                      binary_limit=0, iterations=1)
            b = r.get("browser") or {}
            loaded = b.get("loaded", 0)
            title = ((b.get("pages") or [{}])[0].get("title") or "")
            ok1 = loaded >= 1 and len(title) > 10
            failures += 0 if ok1 else 1
            print("%-8s %-16s loaded=%-3s %s"
                  % ("PASS" if ok1 else "FAIL", "browser_page", loaded, title[:48]))

            env = dict(_os.environ,
                       NODE_PATH=_os.path.expanduser("~/browser_build/node_modules"))
            p = B.state("https://pypi.org")
            els = (p.get("data") or {}).get("elements") or []
            named = [e for e in els if (e.get("name") or "").strip()]
            ok2 = len(named) >= 3
            failures += 0 if ok2 else 1
            print("%-8s %-16s elements=%-3s named=%-3s %s"
                  % ("PASS" if ok2 else "FAIL", "browser_state", len(els),
                     len(named), "exposes controls with the names a person reads"))
    except Exception as exc:
        print("ERROR    browser            %s: %s" % (type(exc).__name__, exc))
        failures += 1

    print("\n%d/%d as expected" % (len(CASES) + browser_cases - failures,
                                    len(CASES) + browser_cases))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
