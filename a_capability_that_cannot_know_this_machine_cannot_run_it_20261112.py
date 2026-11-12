"""Which capabilities cannot say that THIS machine cannot run them.

THE QUESTION THIS ANSWERS, AND WHY IT IS THE ONE THAT MATTERS NOW.

Rounds 3-5 established that a success teaches HOW but never WHEN, that interfaces
beat learners, and that evidence must be addressed to the environment that observed
it. They left one premise of the owner's plan standing, and this round tested it:

    "give our model a try in all those new coding environments ... after he does
     them at least once, he would learn all of those permanently"

A "try" is only informative if the machine can tell whether it FAILED BECAUSE IT
CANNOT ACT HERE. Measured on this tree: 56 of 145 capabilities declare no
preconditions at all. For those rows no perception check can ever fail, so the
front door cannot distinguish "this box lacks qrencode" from "qrencode is here and
the job is fine".

THE MEASUREMENT IS NOT AN OPINION ABOUT THE ROWS. IT IS A COUNTERFACTUAL.

For every candidate row this module does three things:

  1. REPORTS what the row declares, so the finding is falsifiable by inspection;
  2. PROBES the fact the row is missing, using the SAME sensor the front door
     uses, so the repair is known to be decidable and not merely plausible;
  3. INJECTS that one fact into a copy of the registry (the file is never
     touched -- it is owner-protected) and re-runs the front door on the same
     sentence, before and after.

If the before and after differ, the row's undeclared precondition is load-bearing
and the row was lying to itself. If they do not differ, that is reported too: the
injection is not assumed to matter, it is measured to matter.

WHAT IS DELIBERATELY NOT DONE HERE.

The registry is a protected path. AGENTS.md is explicit -- "Say so in the PR
description and stop. Do not work around it." So this module produces the EVIDENCE
for the change and stops. It does not write the registry, does not use the
unprotected snapshot to override it (that would be the workaround the rule forbids
in spirit), and does not guess at rows.

THE DERIVATION IS DELIBERATELY NARROW.

A row is a candidate only when its own id names a runtime that
`world_probe_v1._RUNTIME_KINDS` can already verify with `shutil.which`. That is a
handful of rows and every one is reviewable by eye. Widening it -- inferring that
`python.source.audit.ast` needs a python runtime because it says "python" -- would
add a dozen rows of argument and no new measurement, and an audit nobody trusts is
worth less than a small one they can check.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA = "A_CAPABILITY_THAT_CANNOT_KNOW_THIS_MACHINE_CANNOT_RUN_IT_V1"
# This module sits at the repo root, not under canonical/, so the anchor is
# its own directory rather than two levels up.
ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

# Names the sensor's alphabet does not spell the way the capability id does.
# Kept explicit and tiny: an alias table that grows silently is a place for
# mistakes to hide.
_ALIASES = {
    "sqlite": "sqlite3",
    "tar": "gnu_tar",
}


def load_registry():
    doc = json.loads((ROOT / REGISTRY_PATH).read_text(encoding="utf-8"))
    return doc["capabilities"]


def _tokens(cid):
    return set(re.findall(r"[a-z0-9]+", str(cid or "").lower()))


def runtimes_named(cid):
    """The runtimes a capability's own id names, in the sensor's vocabulary."""
    from canonical.runtime import world_probe_v1 as WP

    named = [k for k in WP._RUNTIME_KINDS if k in _tokens(cid)]
    for word, canonical in _ALIASES.items():
        if word in _tokens(cid) and canonical not in named:
            named.append(canonical)
    return sorted(set(named))


def rows_with_no_preconditions(registry=None):
    reg = registry if registry is not None else load_registry()
    return sorted(cid for cid, v in reg.items() if not (v.get("requires") or []))


def candidates(registry=None):
    """Rows that declare nothing AND name a runtime the sensor can decide.

    Returns [{"capability_id", "runtime", "precondition", "declared"}].
    """
    reg = registry if registry is not None else load_registry()
    out = []
    for cid in rows_with_no_preconditions(reg):
        for runtime in runtimes_named(cid):
            out.append({
                "capability_id": cid,
                "runtime": runtime,
                "precondition": f"{runtime}.runtime.available",
                "declared": list(reg[cid].get("requires") or []),
            })
    return out


def probe(precondition, root=None):
    """Would the front door's own sensor decide that fact, right now?"""
    from canonical.runtime import world_probe_v1 as WP

    return WP.probe_effect(precondition, root=root or ROOT)


def _goal_for(cid, registry):
    """A sentence that routes to this capability, built from its own keywords.

    Using the row's own keywords keeps the probe honest: it tests the row the
    repository ships, not a sentence invented to flatter either side.
    """
    words = [str(x) for x in ((registry.get(cid) or {}).get("keywords") or [])][:6]
    return " ".join(words) if words else str(cid).replace(".", " ").replace("_", " ")


def counterfactual(cid, precondition, registry=None, root=None):
    """Re-run the front door with and without one added precondition.

    The registry file is never written: a deep copy is handed to `act`, which
    accepts a registry argument. This is the only way to measure the change
    without touching a protected path.
    """
    import copy

    from canonical.runtime import grounded_action_v1 as GA

    base = registry if registry is not None else load_registry()
    goal = _goal_for(cid, base)

    def _one(reg):
        r = GA.act(goal, root=root or ROOT, registry=reg, memory=False,
                   bridge=False, computer_use=False)
        rejected = {str(x.get("capability_id")): x
                    for x in (r.get("rejected") or []) if isinstance(x, dict)}
        return {
            "selected": r.get("capability_id"),
            "status": r.get("status"),
            "this_row_rejected_because": (rejected.get(cid) or {}).get("why"),
        }

    after = copy.deepcopy(base)
    after[cid] = dict(after[cid], requires=list(after[cid].get("requires") or []) + [precondition])
    return {"goal": goal, "before": _one(base), "after": _one(after)}


def audit(registry=None, root=None):
    reg = registry if registry is not None else load_registry()
    rows = []
    for row in candidates(reg):
        decided = probe(row["precondition"], root=root)
        row = dict(row)
        row["sensor"] = {"true": bool(decided.get("true")), "how": decided.get("how")}
        row["counterfactual"] = counterfactual(row["capability_id"], row["precondition"],
                                                registry=reg, root=root)
        rows.append(row)
    return {
        "schema": SCHEMA,
        "registry": REGISTRY_PATH,
        "capabilities": len(reg),
        "declaring_no_preconditions": len(rows_with_no_preconditions(reg)),
        "candidates": len(rows),
        "sensor_decides": sum(1 for r in rows if r["sensor"]["how"].endswith(("path_executable", "executable_absent"))),
        "counterfactual_changed_the_outcome": sum(
            1 for r in rows if r["counterfactual"]["before"] != r["counterfactual"]["after"]),
        "rows": rows,
        "authority": "NONE -- sandbox measurement on the shipped registry; "
                     "the registry is owner-protected and was NOT modified",
    }


def main():
    out = audit()
    for r in out["rows"]:
        b, a = r["counterfactual"]["before"], r["counterfactual"]["after"]
        print(f"{r['capability_id']}")
        print(f"   declared requires : {r['declared']}")
        print(f"   missing fact      : {r['precondition']}  -> {r['sensor']['how']}")
        print(f"   before            : {b['status']}  (this row: {b['this_row_rejected_because']})")
        print(f"   after             : {a['status']}  (this row: {a['this_row_rejected_because']})")
    print()
    print(f"capabilities                                  {out['capabilities']}")
    print(f"declaring no preconditions                    {out['declaring_no_preconditions']}")
    print(f"candidates naming a decidable runtime         {out['candidates']}")
    print(f"of those, the sensor decides the missing fact {out['sensor_decides']}")
    print(f"of those, the injection changes the outcome   {out['counterfactual_changed_the_outcome']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
