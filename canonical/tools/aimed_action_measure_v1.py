"""Can the places the instruction implies be DERIVED, and does deriving them reach the 46?

THE QUESTION
------------
After derived_value_v1 closed the typing vocabulary, the suite's remaining wall was measured
page by page: 46 unsolved pages, and every one of them has zero typeable fields
(DECLARED_TRIGGER_AND_OPERAND_TAXONOMY_20261116_V1). What those pages ask for is a PLACE --
the center of a circle, the position of "Select 108 with the slider", the date cell of
11/10/2016, the row that is the shortest flight -- and the shipped hand can only act AT AN
ELEMENT. canonical/runtime/aimed_action_v1 derives the places from the page's own structure
and the instruction's own words; the chromium bridge takes `pressat@x,y`, `moveat@x,y`,
`dropat@x,y`.

Arms (each reuses the identical search, budget, seed, state key and verdict)
---------------------------------------------------------------------------
  A  shipped hand      everything the hand already offers                (control)
  G  aimed hand        A plus the derived places and derived picks       (treatment)
  D  decoy aimed       A plus the same NUMBER of aimed-shaped actions
                       drawn from the wrong witness -- a random place, a
                       random reachable index, a random word. Same size,
                       same shape; only the RULE differs. If G does not
                       beat D, the gain is the extra offers and not the
                       derivation.

The verdict is the page's own full reward, re-read on a fresh page by replaying the plan.

Usage
-----
    python3 canonical/tools/aimed_action_measure_v1.py \
        --html-dir .../miniwob/html --node-modules-dir .../node_modules \
        --budget 400 --seed 1060 --out /tmp/aimed.jsonl \
        [--tasks ...] [--consolidate ... --receipt ...]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import aimed_action_v1 as aimed  # noqa: E402
from canonical.runtime import systematic_exploration_v1 as explorer  # noqa: E402
from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool  # noqa: E402

SCHEMA = "BRAIN_AIMED_ACTION_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
TAXONOMY = REPO / "canonical" / "verification" / "DECLARED_TRIGGER_AND_OPERAND_TAXONOMY_20261116_V1.json"


def unsolved_pages() -> list[str]:
    """The suite's unsolved pages, read from the taxonomy receipt that named them."""
    rows = json.loads(TAXONOMY.read_text())["taxonomy"]["rows"]
    return [str(row["task"]) for row in rows]


def actions_arm(observation: Mapping[str, Any], arm: str, *, seed: int = 20261116) -> list[str]:
    """How a page's offered actions are built in each arm. The shipped hand is IDENTICAL in
    all arms -- only the derived candidates differ, so any difference is the derivation."""
    everything = tool.offered_actions(observation, tool.HAND_TIER)
    if arm == "A_shipped_hand":
        return everything
    if arm == "G_aimed_hand":
        return list(dict.fromkeys(everything + aimed.aimed_actions(observation)))
    if arm == "D_decoy_aimed":
        return list(dict.fromkeys(everything + aimed.decoy_actions(observation, seed=seed)))
    raise ValueError(f"ARM_UNKNOWN:{arm}")


def measure_prices(arm: str) -> Any:
    """The treatment prices its derivations as the instruction's own; the control and the decoy
    use the shipped GuidedPrices unchanged."""
    if arm == "G_aimed_hand":
        return AimedPrices()
    return tool.GuidedPrices()


class AimedPrices:
    """GuidedPrices, plus the aimed set priced as the instruction's own: derived places and
    derived picks are free along the route (turn 1; typing turns 0), so the search tries them
    before it spends itself on the dear tiers."""

    def __init__(self) -> None:
        self._base = tool.GuidedPrices()
        self._for: Any = None
        self._aimed: dict[str, int] = {}
        self._partition_release = False

    def __call__(self, observation: Mapping[str, Any], action: str) -> tuple[int, int]:
        if observation is not self._for:
            self._for = observation
            # Free (0,0) for every derivation except the finalize button, which ends the
            # episode -- wrongly if pressed early -- and so sits one turn behind the rest:
            # early enough that it is reached at every state (it used to starve behind the
            # marks), late enough that the derivations of THAT state go first (a submit
            # pressed before them scores partial and the episode is over).
            rows = aimed.aimed_rows(observation)
            self._aimed = {
                row["action"]: (1 if row["rule"] == "FINALIZE_BUTTON" else 0)
                for row in rows
            }
            # While the instruction's own release (a partition's side of the boxes) is on
            # offer, an ARBITRARY release is not the instruction's own: priced one, so the
            # free run the search follows to its end is the partition's choreography rather
            # than every wrong place a held shape could be let go of. Only where that
            # release exists -- everywhere else the shipped prices stand unchanged.
            self._partition_release = any(
                row["rule"] == "RELEASE_IN_INSTRUCTED_BOX" for row in rows)
        if action in self._aimed:
            return 0, self._aimed[action]
        if self._partition_release and (action.startswith("drop@") or action.startswith("dropat@")):
            return 1, 1
        return self._base(observation, action)


def run_arm(bridge: Any, task: str, seed: int, *, budget: int, arm: str) -> dict[str, Any]:
    # The bridge holds ONE page: load it before the search, exactly as the shipped runner does.
    loaded = bridge.load(task)
    if not loaded.get("ok"):
        raise RuntimeError(f"PAGE_DID_NOT_LOAD:{task}")
    # The lift exists so a state is repeatable: with the page's own clock running, the same
    # action from the same state lands at different times and the explorer honestly bails
    # (OPEN__ENVIRONMENT_NOT_REPEATABLE_UNDER_THIS_STATE_KEY). Pages whose verdict arrives
    # only when their clock fires are therefore out of reach of this search -- named in the
    # receipt, not faked here.
    env = tool.SeedEnv(bridge, seed, time_limit_ms=tool.EXPLORATION_TIME_LIMIT_MS)
    started = time.time()
    # Only the treatment prices its own derivations free; the control and the decoy price every
    # action exactly as the shipped harness always has, so an arm difference is offers + rules.
    prices = measure_prices(arm)
    result = explorer.explore_to_goal(
        env, [], is_goal=tool.succeeded, is_dead=tool.failed,
        actions_of=lambda observation: actions_arm(observation, arm),
        key_of=tool.state_key, order="cheapest", cost_of=prices,
        action_budget=int(budget), reset_cost=1, include_model=False)
    rule: dict[str, Any] | None = None
    verified = False
    if result.get("pass"):
        plan = [str(a) for a in (result.get("plan_cheapest") or [])]
        replay = tool.replay_on_fresh_page(bridge, task, seed, plan)
        verified = bool(replay.get("reproduced"))
        # Which RULE produced the action that mattered: the learnable unit.
        wanted = set(plan)
        for observation, action in (replay.get("trace") or []):
            if str(action) in wanted:
                found = aimed.rule_of(observation, str(action))
                if found is not None:
                    rule = found
                    break
    return {"pass": bool(result.get("pass")), "verified_on_fresh_page": verified,
            "status": result.get("status"), "budget_spent": int(result.get("budget_spent") or 0),
            "plan_len": len(list(result.get("plan_cheapest") or [])),
            "rule": rule, "seconds": round(time.time() - started, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html-dir")
    parser.add_argument("--node-modules-dir")
    parser.add_argument("--substrate", default="chromium", choices=("chromium", "jsdom"))
    parser.add_argument("--budget", type=int, default=400)
    parser.add_argument("--seed", type=int, default=1060)
    parser.add_argument("--tasks", nargs="+", required=False,
                        help="default: the 46 unsolved pages named by the taxonomy receipt")
    parser.add_argument("--arms", nargs="+",
                        default=["A_shipped_hand", "G_aimed_hand", "D_decoy_aimed"])
    parser.add_argument("--out", required=False,
                        help="raw JSONL to write when measuring (not needed with --consolidate)")
    parser.add_argument("--consolidate", nargs="+", default=None)
    parser.add_argument("--receipt", default=None)
    args = parser.parse_args(argv)

    if args.consolidate:
        return _consolidate(args.consolidate, args.receipt)
    if not args.out:
        parser.error("--out is required to measure")
    if not args.html_dir:
        parser.error("--html-dir and --node-modules-dir are required to measure")
    tasks = args.tasks or unsolved_pages()
    bridge = tool.Bridge(args.html_dir, args.node_modules_dir, substrate=args.substrate)
    versions = bridge.versions()
    with open(args.out, "w") as handle:
        for task in tasks:
            row: dict[str, Any] = {"kind": "page", "task": task, "seed": args.seed,
                                   "budget": args.budget, "environment": versions, "arms": {}}
            started = time.time()
            for arm in args.arms:
                row["arms"][arm] = run_arm(bridge, task, args.seed, budget=args.budget, arm=arm)
            row["seconds"] = round(time.time() - started, 1)
            handle.write(json.dumps(row) + "\n")
            print(f"{task:28s} " + "  ".join(
                f"{arm.split('_')[0]}={r['pass']}/{r['budget_spent']}a"
                + (f"[{r['rule']['rule']}]" if r.get("rule") else "")
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
            "rules_that_solved": sorted({(p["arms"][arm].get("rule") or {}).get("rule")
                                         for p in pages
                                         if (p["arms"][arm].get("rule") or {}).get("rule")}),
        }
    treatment = summary["arms"].get("G_aimed_hand", {}).get("pass_tasks", [])
    control = set(summary["arms"].get("A_shipped_hand", {}).get("pass_tasks", []))
    decoy = set(summary["arms"].get("D_decoy_aimed", {}).get("pass_tasks", []))
    summary["gain_over_shipped"] = sorted(set(treatment) - control)
    summary["gain_over_decoy"] = sorted(set(treatment) - decoy)
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
