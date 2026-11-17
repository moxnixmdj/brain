"""Is the wall a budget, or is it that the value the page wants cannot be EXPRESSED?

The question, and why the previous tool could not answer it
-----------------------------------------------------------
`inert_action_prior_measure_v1` priced the action set honestly (47% of the hand changes
nothing) and then measured that pricing it buys no coverage. That tool's own negative result
points at the next thing: at 400 actions -- well below the 1500 that the wall measurement
spent -- the same pages fail. So they are not budget problems. They are GENERATOR problems.

Everything the shipped hand can type is a literal: a quoted span of the instruction, a word of
the instruction, or a string already on the page (`type_candidates`). A page whose answer is
`7` from `7 + 0 =`, or `et` from the last word of a 900-character text area, or `19:55` from
`7:55 PM`, is therefore unreachable at ANY budget: no hypothesis generator can build the
action, and an oracle can choose only among the hypotheses it is shown. That is the same
defect the coding side already measured (a fix no rule can build is unreachable, not slow),
moved from the edit to the operand.

Arms (each reuses the identical search, budget, seed, state key and verdict)
---------------------------------------------------------------------------
  A  shipped hand      presses + the existing typed-literal vocabulary          (control)
  E  derived hand      presses + `canonical/runtime/derived_value_v1` values    (treatment)
  U  union             presses + both                                          (is anything lost?)
  D  decoy derived     presses + the same NUMBER of derived-shaped values, made
                       from the wrong witness (a random word, a random offset), so the arm
                       has the same size and shape as E and only the RULE differs. If E does
                       not beat D, the gain is the extra values and not the derivation.

The verdict is the page's own full reward, re-read on a fresh page by replaying the plan.

Usage
-----
    python3 canonical/tools/derived_value_measure_v1.py \
        --html-dir .../miniwob/html --node-modules-dir .../node_modules \
        --budget 400 --seed 1060 --tasks simple-arithmetic simple-algebra scroll-text \
        --out /tmp/derived.jsonl [--consolidate ... --receipt ...]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time
from typing import Any, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import derived_value_v1 as derived  # noqa: E402
from canonical.runtime import systematic_exploration_v1 as explorer  # noqa: E402
from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool  # noqa: E402

SCHEMA = "BRAIN_DERIVED_VALUE_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

#: How a page's offered actions are built in each arm. Pressing, hovering and the rest of the
#: hand are IDENTICAL across arms -- only what may be typed differs, so any difference is the
#: typing vocabulary and nothing else.
def actions_arm(observation: Mapping[str, Any], arm: str, *, seed: int = 20261116) -> list[str]:
    everything = tool.offered_actions(observation, tool.HAND_TIER)
    shipped = [a for a in everything if a.startswith("type@")]
    rest = [a for a in everything if not a.startswith("type@")]
    if arm == "A_shipped_hand":
        return rest + shipped
    if arm == "E_derived_hand":
        return rest + derived.typed_actions(observation)
    if arm == "U_union":
        out = rest + derived.typed_actions(observation) + shipped
        return list(dict.fromkeys(out))
    if arm == "D_decoy_derived":
        return rest + _decoy(observation, count=len(derived.typed_actions(observation)), seed=seed)
    raise ValueError(f"ARM_UNKNOWN:{arm}")


def _decoy(observation: Mapping[str, Any], *, count: int, seed: int) -> list[str]:
    """Values with E's shape and E's length, drawn from the wrong witness on purpose.

    A word of the instruction that is not quoted, and a word of the page -- i.e. exactly the
    kind of value the shipped hand already tries -- shuffled so the arm is not a subset of A.
    The point is that E's success cannot be explained by "more values on offer".
    """
    rng = random.Random(seed)
    fields = [int(e["index"]) for e in observation.get("elements") or [] if e.get("can_type")]
    pool = derived.words_of(observation.get("utterance"))
    for _, _, text in derived.visible_texts(observation):
        pool += derived.words_of(text)[:5]
    pool = [w for w in pool if w and len(w) <= 40]
    rng.shuffle(pool)
    out: list[str] = []
    for value in pool[:max(1, count)]:
        for index in fields:
            out.append(f"type@{index}={value}")
    return out


def run_arm(bridge: Any, task: str, seed: int, *, budget: int, arm: str) -> dict[str, Any]:
    # The bridge holds ONE page: load it before the search, exactly as the shipped runner does.
    loaded = bridge.load(task)
    if not loaded.get("ok"):
        raise RuntimeError(f"PAGE_DID_NOT_LOAD:{task}")
    env = tool.SeedEnv(bridge, seed, time_limit_ms=tool.EXPLORATION_TIME_LIMIT_MS)
    started = time.time()
    result = explorer.explore_to_goal(
        env, [], is_goal=tool.succeeded, is_dead=tool.failed,
        actions_of=lambda observation: actions_arm(observation, arm),
        key_of=tool.state_key, order="cheapest", cost_of=tool.GuidedPrices(),
        action_budget=int(budget), reset_cost=1, include_model=False)
    rule: dict[str, Any] | None = None
    verified = False
    if result.get("pass"):
        plan = [str(a) for a in (result.get("plan_cheapest") or [])]
        replay = tool.replay_on_fresh_page(bridge, task, seed, plan)
        verified = bool(replay.get("reproduced"))
        # Which RULE produced the typed value that mattered: this is the learnable unit.
        typed = [a for a in plan if a.startswith("type@")]
        if typed:
            first = (replay.get("trace") or [])
            for observation, action in first:
                if str(action) in typed:
                    rule = derived.rule_of(observation, str(action))
                    break
    return {"pass": bool(result.get("pass")), "verified_on_fresh_page": verified,
            "status": result.get("status"), "budget_spent": int(result.get("budget_spent") or 0),
            "plan_len": len(list(result.get("plan_cheapest") or [])),
            "typed_rule": rule, "seconds": round(time.time() - started, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html-dir")
    parser.add_argument("--node-modules-dir")
    parser.add_argument("--substrate", default="chromium", choices=("chromium", "jsdom"))
    parser.add_argument("--budget", type=int, default=400)
    parser.add_argument("--seed", type=int, default=1060)
    parser.add_argument("--tasks", nargs="+", required=False)
    parser.add_argument("--arms", nargs="+",
                        default=["A_shipped_hand", "E_derived_hand", "U_union", "D_decoy_derived"])
    parser.add_argument("--out", required=False,
                        help="raw JSONL to write when measuring (not needed with --consolidate)")
    parser.add_argument("--consolidate", nargs="+", default=None)
    parser.add_argument("--receipt", default=None)
    args = parser.parse_args(argv)

    if args.consolidate:
        return _consolidate(args.consolidate, args.receipt)
    if not args.out:
        parser.error("--out is required to measure")
    if not (args.html_dir and args.tasks):
        parser.error("--html-dir, --node-modules-dir and --tasks are required to measure")
    bridge = tool.Bridge(args.html_dir, args.node_modules_dir, substrate=args.substrate)
    versions = bridge.versions()
    with open(args.out, "w") as handle:
        for task in args.tasks:
            row: dict[str, Any] = {"kind": "page", "task": task, "seed": args.seed,
                                   "budget": args.budget, "environment": versions, "arms": {}}
            started = time.time()
            for arm in args.arms:
                row["arms"][arm] = run_arm(bridge, task, args.seed, budget=args.budget, arm=arm)
            row["seconds"] = round(time.time() - started, 1)
            handle.write(json.dumps(row) + "\n")
            print(f"{task:22s} " + "  ".join(
                f"{arm.split('_')[0]}={r['pass']}/{r['budget_spent']}a"
                + (f"[{r['typed_rule']['rule']}]" if r.get("typed_rule") else "")
                for arm, r in row["arms"].items()), flush=True)
    bridge.close()
    return 0


def _consolidate(paths: Sequence[str], receipt: str | None) -> int:
    pages: list[dict[str, Any]] = []
    for path in paths:
        pages += [json.loads(line) for line in pathlib.Path(path).read_text().splitlines() if line.strip()]
    arms = sorted({arm for page in pages for arm in page["arms"]})
    summary: dict[str, Any] = {"pages": len(pages), "arms": {}}
    for arm in arms:
        solved = [p["task"] for p in pages if p["arms"][arm]["pass"]]
        summary["arms"][arm] = {
            "pass": len(solved), "pass_tasks": sorted(solved),
            "verified": sum(1 for p in pages if p["arms"][arm]["verified_on_fresh_page"]),
            "actions_spent": sum(int(p["arms"][arm]["budget_spent"]) for p in pages),
            "seconds": round(sum(float(p["arms"][arm]["seconds"]) for p in pages), 1),
            "rules_that_solved": sorted({(p["arms"][arm].get("typed_rule") or {}).get("rule")
                                         for p in pages
                                         if (p["arms"][arm].get("typed_rule") or {}).get("rule")}),
        }
    out = {"schema": SCHEMA, "authority": AUTHORITY, "kind": "receipt",
           "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "incremental_spend_usd": 0, "producer_cognition_model_dependency_count": 0,
           "summary": summary, "pages": pages}
    text = json.dumps(out, indent=1, sort_keys=True)
    if receipt:
        pathlib.Path(receipt).write_text(text + "\n")
        print(f"written {receipt}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
