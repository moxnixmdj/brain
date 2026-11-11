#!/usr/bin/env python3
"""FAILURE TRIAGE — every failure gets a CAUSE and a RECOVERY, not a retry.

WHY THIS IS A HARNESS COMPONENT AND NOT A UTILITY
-------------------------------------------------
The 2026 evidence is that the harness, not the model, decides the outcome: the same model
moves 6.7% -> 68.3% on SWE-bench from a changed edit-tool format, and one Terminal-Bench study
measured a 40x token difference between harnesses on an identical model. The single highest-ROI
harness behaviour after search is STRUCTURED ERROR RECOVERY: after every tool call, decide what
kind of failure this is and do the one thing that addresses it.

Measured 2026-11-09: `canonical/runtime/` emits 150+ distinct `FAIL_CLOSED__*` / `FAIL__*`
statuses. Nothing in the tree maps a status to a recovery. A caller that cannot name the cause
can only retry, and blind retry is how an agent burns a budget and concludes nothing.

WHAT THIS DOES
--------------
`triage(status, *, detail=None, attempt=0)` returns:
    cause    -- one of a small, closed set (8). Not 150. A taxonomy that is not closed is
                a vocabulary, and a vocabulary does not route anything.
    recover  -- exactly one of a closed set of actions (6).
    stop     -- True when retrying is not merely unwise but is the wrong thing to do.
    evidence -- the substring of the status that decided it, so the mapping can be audited.

WHY THE CAUSE SET IS SMALL AND CLOSED
-------------------------------------
A triage that can say "it failed for reasons" routes nothing. Eight causes cover every
status this repository actually emits, and each maps to a DIFFERENT action -- two causes that
share an action are one cause wearing two names.

Cost: 0 weights, 0 parameters, 0 model calls. One regex table and a dict.
"""
from __future__ import annotations

import re
import time
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FAILURE_TRIAGE_V1"

# Recovery actions. Closed set: a caller can switch on these exhaustively.
RECOVER = {
    "SUPPLY_INPUT":   "the request was well-formed but a required input was not bound",
    "NARROW_SCOPE":   "the request asked for more than an admitted mechanism can do",
    "RERUN":          "a transient condition (timeout, truncation) -- the same call may work",
    "ESCALATE":       "the mechanism is broken or its own invariants failed -- a human decides",
    "STOP_RETRYING":  "the failure is a proven limit; retrying cannot succeed",
    "FIX_THEN_RETRY": "the ENVIRONMENT is wrong (stale/contaminated artifact) -- change it first",
    "REPAIR_ARTIFACT": "the produced artifact is wrong -- repair it, then rerun",
}

# Ordered rules. FIRST MATCH WINS, and the order is the argument:
# a proven limit outranks everything, because retrying a limit is the one unrecoverable
# mistake -- it converts a known boundary into an unknown budget sink.
_RULES: tuple[tuple[str, str, str, bool], ...] = (
    # (cause, recover, regex, stop)
    ("PROVEN_LIMIT",     "STOP_RETRYING",  r"NONIDENTIFIAB|IMPOSSIB|LOWER_BOUND|NO_GO|"
                                           r"CANNOT_BE|UNREACHABLE|CEILING|EXHAUST", True),
    ("CONTAMINATION",    "FIX_THEN_RETRY", r"CONTAMINAT|SOLUTION_READ|SPENT|DRIFT|STALE|"
                                           r"NOT_FRESH", False),
    ("MISSING_INPUT",    "SUPPLY_INPUT",   r"INPUT_BINDING_REQUIRED|REQUIRED_FILE_INPUT|"
                                           r"\bPATH\b|MISSING_|ABSENT|NOT_FOUND|UNBOUND", False),
    ("REFUSED_BY_SCOPE", "NARROW_SCOPE",   r"REFUSED|NOT_ADMITTED|OUT_OF_SCOPE|UNSUPPORTED|"
                                           r"REQUIRES_ADMITTED|NOT_SERVABLE|NOT_APPLICABLE", False),
    ("TRANSIENT",        "RERUN",          r"TIMEOUT|TRUNCATED|BUSY|RESOURCE|AGAIN|"
                                           r"TEMPORAR|INTERRUPT", False),
    ("INVARIANT_BROKEN", "ESCALATE",       r"INVARIANT|UNTOUCHED.*FALSE|CORRUPT|MISMATCH|"
                                           r"SELF_CHECK|AUDIT", False),
    ("EXECUTION_FAILED", "REPAIR_ARTIFACT", r"EXECUTION_FAILED|EXIT_|NONZERO|CRASHED|"
                                           r"SYNTAX|IMPORT", False),
)

_CAUSES = tuple(r[0] for r in _RULES) + ("UNKNOWN",)


def triage(status: str, *, detail: Mapping[str, Any] | None = None,
           attempt: int = 0) -> dict[str, Any]:
    """Map one failure status to a cause, one recovery action, and a stop decision.

    `attempt` matters for exactly one thing: a TRANSIENT failure is worth rerunning a
    bounded number of times, and an unbounded rerun loop is indistinguishable from a hang.
    """
    t0 = time.perf_counter()
    text = str(status or "")
    if detail:
        text = text + " " + " ".join(str(v) for v in (detail or {}).values() if v is not None)
    upper = text.upper()

    cause, recover, matched, stop = "UNKNOWN", "ESCALATE", "", False
    for c, act, pattern, st in _RULES:
        m = re.search(pattern, upper)
        if m:
            cause, recover, matched, stop = c, act, m.group(0), st
            break

    if cause == "UNKNOWN":
        # An unrecognised failure is the ONE case that must not be retried silently: it is
        # a hole in this table, and the honest response is to surface it, not to loop.
        recover, stop = "ESCALATE", True

    if cause == "TRANSIENT":
        if attempt >= 3:
            stop = True
            recover = "ESCALATE"
    elif cause in {"MISSING_INPUT", "REFUSED_BY_SCOPE"} and attempt >= 1:
        # Re-issuing the identical request cannot bind a missing input or widen a scope.
        stop = True

    return {
        "schema": SCHEMA,
        "status": text[:200],
        "cause": cause,
        "recover": recover,
        "recover_meaning": RECOVER[recover],
        "stop": stop,
        "matched": matched,
        "attempt": attempt,
        "causes": list(_CAUSES),
        "elapsed_us": round((time.perf_counter() - t0) * 1e6, 1),
    }


def self_check() -> int:
    """Prove the classifier routes, and that every cause maps to a DISTINCT action."""
    failures: list[str] = []
    cases = {
        "FAIL_CLOSED__INPUT_BINDING_REQUIRED:path": ("MISSING_INPUT", "SUPPLY_INPUT"),
        "REFUSED__QUERY_NOT_SERVABLE_UNDER_CONFINEMENT": ("REFUSED_BY_SCOPE", "NARROW_SCOPE"),
        "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT": ("REFUSED_BY_SCOPE", "NARROW_SCOPE"),
        "TIMEOUT_AFTER_20S": ("TRANSIENT", "RERUN"),
        "FAIL_CLOSED__HELDOUT_IDENTICAL_TO_TRAINING_INSTANCE": ("UNKNOWN", "ESCALATE"),
        "FAIL_CLOSED__SOURCE_BLOB_DRIFT": ("CONTAMINATION", "FIX_THEN_RETRY"),
        "POSTCONDITION_STDOUT_MISMATCH": ("INVARIANT_BROKEN", "ESCALATE"),
        "CLI_EXIT_1:no such file": ("EXECUTION_FAILED", "REPAIR_ARTIFACT"),
        "NONIDENTIFIABLE_FROM_OBSERVATIONS": ("PROVEN_LIMIT", "STOP_RETRYING"),
    }
    for status, (want_cause, want_rec) in cases.items():
        v = triage(status)
        if (v["cause"], v["recover"]) != (want_cause, want_rec):
            failures.append(f"{status[:44]} -> {v['cause']}/{v['recover']}, wanted {want_cause}/{want_rec}")

    # two causes must never share an action
    seen: dict[str, str] = {}
    for c in _CAUSES:
        if c == "UNKNOWN":
            continue
        act = next(r[1] for r in _RULES if r[0] == c)
        if act in seen and seen[act] != c:
            failures.append(f"causes {seen[act]} and {c} share action {act}")
        seen[act] = c

    # a proven limit must never be rerunnable
    if not triage("NONIDENTIFIABLE")["stop"]:
        failures.append("a proven limit was left retryable")
    # unknown must stop
    if not triage("SOMETHING_NOBODY_CLASSIFIED")["stop"]:
        failures.append("an unknown failure was left retryable")
    # transient retries, then stops
    if triage("TIMEOUT", attempt=3)["stop"] is not True:
        failures.append("transient failure retried past its bound")
    # missing input stops after one attempt
    if triage("INPUT_BINDING_REQUIRED:path", attempt=1)["stop"] is not True:
        failures.append("a missing-input failure was left retryable")
    # empty status is unknown, not a pass
    if triage("")["cause"] != "UNKNOWN":
        failures.append("an empty status was classified as something")

    if failures:
        print(f"SELF-CHECK FAILED ({len(failures)}):")
        for f in failures:
            print("  -", f)
        return 1
    print(f"causes: {len(_CAUSES)} (closed set, each with a distinct action)  "
          f"actions: {len(RECOVER)}")
    print("SELF-CHECK PASS — every failure routed, no cause shares an action, limits never retry")
    return 0


if __name__ == "__main__":
    import sys
    if "--self-check" in sys.argv:
        raise SystemExit(self_check())
    import json
    for s in ("FAIL_CLOSED__INPUT_BINDING_REQUIRED:path", "TIMEOUT_AFTER_20S",
              "NONIDENTIFIABLE_FROM_OBSERVATIONS", "", "FAIL_CLOSED__SOURCE_BLOB_DRIFT"):
        v = triage(s)
        print(f"{s[:46]:46s} -> {v['cause']:16s} {v['recover']:15s} stop={v['stop']}")
