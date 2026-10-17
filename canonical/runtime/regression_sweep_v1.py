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
    ("env_toolchain", "run the tests and record the result", ["out"],   True,
     "declared runner absent: composes one, verified by the solver"),
    ("env_node_toolchain", "run the tests and record the result", ["out"], True,
     "other language, no shared code: wrapper -> mocha -> node --test"),
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
            # The accessible name lives in aria/placeholder/name/text
            # depending on the control; this is what a person would call it.
            named = [e for e in els if (e.get("aria") or e.get("placeholder")
                                        or e.get("name") or e.get("text") or "").strip()]
            ok2 = len(named) >= 3
            failures += 0 if ok2 else 1
            print("%-8s %-16s elements=%-3s named=%-3s %s"
                  % ("PASS" if ok2 else "FAIL", "browser_state", len(els),
                     len(named), "exposes controls with the names a person reads"))
    except Exception as exc:
        print("ERROR    browser            %s: %s" % (type(exc).__name__, exc))
        failures += 1

    failures += attested_state_checks()
    failures += anytime_validity_checks()
    total = len(CASES) + browser_cases + _ATTESTED_CASES + _ANYTIME_CASES

    print("\n%d/%d as expected" % (total - failures, total))
    return 1 if failures else 0


_ATTESTED_CASES = 4
_ANYTIME_CASES = 3


def attested_state_checks() -> int:
    """The substrate: did the action change the world, and into what.

    Guards the three verdicts that matter, because each is a way the
    check could start agreeing when it should stay silent: crediting a
    command that exited zero and did nothing, crediting a program that
    forged its own evidence, and calling an unreadable world unchanged.
    """
    import os as _os_local
    import shutil
    import sys as _sys_local
    import tempfile
    from pathlib import Path as _P

    print()
    try:
        from canonical.runtime import attested_state_v1 as A
    except ImportError:
        _sys_local.path.insert(0, _os_local.path.dirname(_os_local.path.abspath(__file__)))
        import attested_state_v1 as A

    spec = {"goal": "run the tests and record the result"}
    check = A.tests_ran_in("out/report.txt")
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        _P(tmp, "out").mkdir()
        _P(tmp, "liar.py").write_text(
            "import pathlib\n"
            "pathlib.Path('out/report.txt').write_text('All tests passed\\n')\n")
        _P(tmp, "honest.py").write_text(
            "import pathlib\n"
            "pathlib.Path('out/report.txt').write_text('Ran 3 tests\\nOK\\n')\n")

        cases = [
            # (label, action, expected verdict, why it must be so)
            ("idle_exit_zero", "echo 'no tests here' && exit 0",
             A.UNCHANGED, "exits zero and changes nothing: no credit"),
            ("forged_report", "python3 liar.py",
             A.POSTCONDITION_FAILED, "writes the report without running anything"),
            ("real_report", "python3 honest.py",
             A.VERIFIED, "the report carries evidence a run happened"),
        ]
        for label, action, expected, why in cases:
            shutil.rmtree(_os_local.path.join(tmp, "out"), ignore_errors=True)
            _P(tmp, "out").mkdir()
            try:
                r = A.attest(action, tmp, files=["out/report.txt"], trees=["out"],
                             spec=spec, check=check)
                got, ok = r["verdict"], r["verdict"] == expected
            except Exception as exc:
                got, ok = f"{type(exc).__name__}: {exc}", False
            bad += 0 if ok else 1
            print("%-8s %-16s %-21s %s"
                  % ("PASS" if ok else "FAIL", "attested", got if ok else
                     "%s (want %s)" % (got, expected), why))

        # An unreadable channel must never be reported as unchanged.
        sealed = A.attest("true", tmp, trees=["out"], spec=spec)
        other = A.matches(sealed, {"goal": "a different question entirely"})
        bad += 0 if not other else 1
        print("%-8s %-16s %-21s %s"
              % ("PASS" if not other else "FAIL", "attested",
                 "rejected" if not other else "ACCEPTED",
                 "a receipt for one question is not an answer to another"))
    return bad


def anytime_validity_checks() -> int:
    """The gate that decides what counts as an improvement must itself hold.

    Two things are guarded, and the first is the strange one: that the
    OLD gate is measurably broken. If a future change made paired-two-
    sigma start behaving under peeking, this case would fail -- which is
    the point, because it means the number below is being re-measured
    rather than remembered.
    """
    print()
    try:
        from canonical.runtime import anytime_validity_v1 as V
    except ImportError:
        import os as _o
        import sys as _s2
        _s2.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
        import anytime_validity_v1 as V

    trials = 600
    bad = 0
    rows = [
        # (label, measured, must be <=, why)
        ("shipped gate, expected noise",
         V.false_positive_rate(lambda d: V.betting(d), 1.0, trials, 30),
         0.05, "holds its promise where it was tuned"),
        ("shipped gate, 4x that noise",
         V.false_positive_rate(lambda d: V.betting(d), 4.0, trials, 30),
         0.05, "holds it on a world it was never tuned for"),
    ]
    for label, rate, ceiling, why in rows:
        ok = rate <= ceiling
        bad += 0 if ok else 1
        print("%-8s %-16s %-21s %s"
              % ("PASS" if ok else "FAIL", "anytime", "%.1f%% false positives"
                 % (rate * 100), why))

    # The counter-example: the old gate, measured so the claim stays honest.
    broken = V.false_positive_rate(lambda d: V.paired_two_sigma(d), 1.0, trials, 30)
    ok = broken > 0.25
    bad += 0 if ok else 1
    print("%-8s %-16s %-21s %s"
          % ("PASS" if ok else "FAIL", "anytime", "%.1f%% false positives"
             % (broken * 100),
             "the old gate is measurably broken under peeking -- as claimed"))
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
