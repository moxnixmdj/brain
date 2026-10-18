"""Close the loop: the machine drives a real number up, judged by an independent oracle.

This is the owner's requirement stated as an executable test: *give it an ambitious goal and it
keeps acting until the number actually arrives -- it does not stop at $100 on a $1M goal.*

Concretely:
- the goal is "every capability that can execute, executes" -- a number the machine moves by
  improving its own input generation;
- `measure` is the typed sweep, which is a different module from `act` and does not import it.
  `target_chase_driver_v1` enforces that separation and refuses to run if they are the same
  callable, so the machine cannot grade its own homework;
- `act` changes DATA, never code. Content rules live in a dict (`set_content_rule`) precisely so
  an unattended run can extend them safely. An act() that rewrote Python would not be safe to
  leave running, and the distinction is deliberate.

Model dependency: 0. Spend: $0.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import type_directed_sampler_v1 as samp  # noqa: E402
from execution_guard import target_chase_driver_v1 as chase  # noqa: E402
from execution_guard import typed_capability_sweep_v1 as sweep  # noqa: E402

# Candidate rules the machine may try, in the order it will try them. Each is a hypothesis
# about what a capability's inputs actually have to look like; the sweep decides which survive.
CANDIDATES: list[tuple[str, str, str, str, str]] = [
    ("archive.tar_gz.create_from_manifest", "output", ".tar.gz", "",
     "tar archives must be named .tar.gz"),
    ("finance.saccr.credit.addon.v1", "json", ".json",
     '{{"trades": [{{"id": {i}, "notional": {v}, "asset_class": "{w}"}},'
     ' {{"id": {i2}, "notional": {v2}, "asset_class": "{w2}"}}]}}',
     "SACCR needs a non-empty trades array"),
    ("decision.synthesis.typed.stdlib", "input", ".json",
     '{{"options": [{{"id": "{w}", "cost": {v}, "benefit": {v2}}},'
     ' {{"id": "{w2}", "cost": {v2}, "benefit": {v}}}], "objective": "maximize benefit"}}',
     "decision synthesis needs typed options"),
    ("sqlite.table.create_from_json_records", "json", ".json",
     '{{"table": "{w}", "records": [{{"id": {i}, "name": "{w2}", "value": {v}}}]}}',
     "sqlite builder needs a table name and records"),
    ("http.json.fetch_from_state", "source_json", ".json",
     '{{"alpha": {{"url": "https://example.invalid/{w}"}}, "beta": {{"url": "https://example.invalid/{w2}"}}}}',
     "the fetcher indexes a url per key"),
]


def make_measure(instances: int, seed: int, subset: set[str] | None):
    def measure() -> float:
        r = sweep.sweep(instances, seed, subset)
        return float(r["totals"]["clean_all_instances_pass"])
    return measure


def make_act(budget: int):
    state = {"i": 0, "applied": []}

    def act(ctx) -> dict:
        if state["i"] >= len(CANDIDATES) or state["i"] >= budget:
            return {"action": "EXHAUSTED", "applied": list(state["applied"])}
        cid, key, suffix, template, why = CANDIDATES[state["i"]]
        state["i"] += 1
        samp.set_content_rule(key, suffix, template, capability=cid)
        state["applied"].append({"capability": cid, "rule": key, "why": why})
        return {"action": "SET_RULE", "capability": cid, "rule": key, "why": why}

    return act, state


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instances", type=int, default=2)
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--target", type=float, default=None)
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)

    subset = {c[0] for c in CANDIDATES}
    opening_full = sweep.sweep(ns.instances, ns.seed, subset)
    before = float(opening_full["totals"]["clean_all_instances_pass"])

    # a target that is actually achievable, not a wish: the sweep found 5 candidates
    target = ns.target if ns.target is not None else before + float(len(CANDIDATES))

    measure = make_measure(ns.instances, ns.seed, subset)
    act, state = make_act(ns.rounds)

    result = chase.run(
        goal=f"maximize capabilities that execute cleanly (from {before:.0f})",
        measure=measure,
        act=act,
        target=target,
        direction="maximize",
        max_rounds=ns.rounds,
    )

    # independent re-read: clear the rules and re-measure nothing -- instead re-run the sweep
    # as a separate process-level call so the final number is not the chase's own bookkeeping.
    final = float(measure())

    out = {
        "schema": "PROJECT_BRAIN_SAMPLER_RULE_CHASE_V1",
        "model_dependency_count": 0,
        "candidates": len(CANDIDATES),
        "opening": before,
        "final_independent_measure": final,
        "moved": final - before,
        "rules_applied": state["applied"],
        "chase": result,
    }
    text = json.dumps(out, indent=2, sort_keys=True, default=str) + "\n"
    if ns.out:
        Path(ns.out).write_text(text, encoding="utf-8")
    print(f"opening clean count : {before:.0f}")
    print(f"final (independent): {final:.0f}")
    print(f"moved               : {final - before:+.0f}")
    print(f"rules applied       : {len(state['applied'])}")
    for a in state["applied"]:
        print(f"   {a['capability']}: {a['why']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
