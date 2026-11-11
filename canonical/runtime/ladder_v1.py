"""The ladder: three ways to address a widget, in order of cost, with the rung named.

Measured, on the same goal on two pages:

    structured page (roles, labels)   address_v1 gives role=textbox name="filter" exactly.
                                      Reuse: zero model calls, 4/4 across layouts.
    canvas page (one node: Canvas)    address_v1 finds NOTHING. find(role=textbox) is None.

That is not a defect to hide. It is the shape of "anything on a computer": some interfaces
declare their structure, some only draw it, and the agent must know WHICH it is looking at
before it decides how to act.

    RUNG 1  ADDRESSED     the page declares roles and names.  cost: ~3 CDP reads.
                          exact, reproducible, no model.
    RUNG 2  ANCHORED      no roles, but the widget has appearance.  cost: one template match.
                          works when the thing looks like something.  Decays when the
                          library grows, and cannot locate an empty field at all (r70).
    RUNG 3  LOOKED-AT     nothing to address and nothing distinctive to match.  cost: a model
                          reading pixels on every step, plus a model verifying every step.
                          This is what every computer-use agent does by default, and it is
                          the rung this file exists to make visible as the expensive one.

The rung is chosen by MEASUREMENT, not by preference: try the cheapest, record why it failed,
fall through.  A run reports the rung it used, so a benchmark can never quietly charge the
fast path's cost to the slow path's success.
"""
from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from canonical.runtime import address_v1 as A

SCHEMA = "LADDER_V1"
RUNGS = {"ADDRESSED": 1, "ANCHORED": 2, "LOOKED_AT": 3}


def probe(address: A.Address, role: str | None, name: str | None) -> dict[str, Any]:
    """Which rung can address this widget?  Measured, not chosen."""
    if role or name:
        hit = A.find(address, role=role, name=name)
        if hit:
            return {"rung": "ADDRESSED", "cost": "3 CDP reads", "target": hit}
        why1 = (f"the page declares no {role or ''} {name or ''}".strip())
    else:
        why1 = "no role or name was given to look for"
    try:
        nodes = [n for n in A.ax_nodes(address) if n["box"]]
    except Exception:
        nodes = []
    return {"rung": None, "why_not_addressed": why1,
            "addressable_nodes": len(nodes),
            "roles_present": sorted({n["role"] for n in nodes})[:10]}


def run_looked_at(goal: str, browser: Any, propose, verify, shot_dir: str,
                  budget: int = 6) -> dict[str, Any]:
    """Rung 3: the model on every step.  Wraps the existing act loop and labels the cost."""
    from canonical.runtime import act_loop_v1 as L
    calls = {"propose": 0, "verify": 0}

    def _propose(step, g):
        calls["propose"] += 1
        return propose(step, g)

    def _verify(path):
        calls["verify"] += 1
        return verify(path)

    t0 = time.time()
    res = L.act(goal, browser, propose=_propose, verify=_verify, shot_dir=shot_dir,
                budget=budget)
    return {"schema": SCHEMA, "rung": "LOOKED_AT", "rung_number": 3,
            "result": res["verdict"], "because": res.get("because"),
            "model_calls": calls["propose"] + calls["verify"],
            "proposals": calls["propose"], "verifications": calls["verify"],
            "steps": res.get("steps_used"), "seconds": round(time.time() - t0, 2),
            "screenshots": len(res.get("trajectory", [])) * 2,
            "trajectory": res.get("trajectory", [])}


def compare(runs: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """The cost table.  What a benchmark should report and almost never does."""
    out = {}
    for name, r in runs.items():
        out[name] = {"rung": r.get("rung"), "model_calls": r.get("model_calls", 0),
                     "steps": r.get("steps"), "seconds": r.get("seconds"),
                     "result": r.get("result")}
    fast = [v for v in out.values() if v["rung"] in ("ADDRESSED", "ANCHORED")]
    slow = [v for v in out.values() if v["rung"] == "LOOKED_AT"]
    if fast and slow:
        f = sum(v["model_calls"] for v in fast) / len(fast)
        s = sum(v["model_calls"] for v in slow) / len(slow)
        out["_ratio"] = {"mean_model_calls_fast_rung": round(f, 2),
                         "mean_model_calls_slow_rung": round(s, 2),
                         "how_many_times_more_expensive": round(s / f, 2) if f else None}
    return out
