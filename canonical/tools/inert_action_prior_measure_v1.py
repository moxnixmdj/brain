"""Does knowing which actions are inert make a never-solved page solvable in fewer actions?

The question, in one line
-------------------------
`WHERE_THE_WALL_ACTUALLY_IS_20261116_V1.md` measured the wall: 50,154 actions to solve 1 of 37
held-out pages, 8.34 actions per distinguishable state, and a required budget that grows like
`8.34 ** depth`. It named the only lever that changes the exponent -- a prior over actions --
and left it at "to be built". This tool builds the smallest such prior that is still honest,
and measures it on the same pages, with the page's own reward as the only verdict.

What is measured, and why two arms are not enough
-------------------------------------------------
The candidate prior (`canonical/runtime/inert_action_prior_v1.py`) says: an action whose
AFFORDANCE class has never changed anything is postponed behind actions that have. Three
questions have to be separated, and each has a different answer:

  A  BASELINE     the shipped guided search, unchanged.
  B  CLASS        the prior learned on OTHER pages only, then applied to this page at zero
                  cost. This is the one that matters: it is what "learn it once, use it
                  everywhere" means, and it cannot cheat by looking at the page it is scored on.
  C  PAGE-LOCAL   every offered action measured inert-or-not on THIS page from reset, then
                  applied. This is an ORACLE for the same information, and it is an UPPER
                  BOUND: it is charged nothing for the probe it would need in real use. If C
                  does not beat A, the information is worthless and B cannot be worth anything.
                  If C beats A but B does not, the prior exists but does not transfer -- which
                  is a fact about affordance keys, and the design's whole claim.
  D  SHUFFLED     the same prior as B with the per-class effect counts permuted among classes
                  (fixed seed). It holds the SHAPE of B -- the same number of deferred classes,
                  the same prices -- and breaks only the association between an affordance and
                  what it did. If B does not beat D, the key carries no information and the
                  mechanism is dead however good C looks. This arm exists to be able to lose.

Integrity rules, enforced here rather than promised
---------------------------------------------------
1. GOAL-FREE PROBE. The probe that learns inertness reads the elements the agent can see and
   nothing else. `is_goal`, `done` and `raw_reward` are not consulted anywhere in the probe, and
   `changed` is a comparison of (elements, holding) before and after -- the same two fields the
   agent's own state key uses. A prior that read the reward would be the deployment oracle this
   work exists to remove.
2. NO PEEKING ACROSS THE SPLIT. Arm B's prior is built from pages outside the scored set. The
   tool asserts that no scored page contributed a row.
3. THE VERDICT IS THE PAGE'S OWN. Coverage is `succeeded()` -- the page's full reward, the
   unmodified rule from the measurement module -- and the search is the unmodified explorer.
   The harness re-reads the verdict from the page, not from the search's own return value.
4. ONE RESET PER PROBE ACTION, so no action's effect is masked by another's. An action is
   probed in exactly the state it would be offered in.
5. NOTHING IS PROMOTED. No capability is registered, no family is flipped, no receipt claims
   authority. Authority is NONE; the numbers are producer-run sandbox measurements.

Usage
-----
    python3 canonical/tools/inert_action_prior_measure_v1.py \
        --html-dir /path/to/miniwob-plusplus/miniwob/html --node-modules-dir /path/to/node_modules \
        --budget 400 --seed 1060 --out /tmp/inert.jsonl [--tasks a b c]

    python3 canonical/tools/inert_action_prior_measure_v1.py --consolidate /tmp/inert*.jsonl \
        --receipt canonical/verification/INERT_ACTION_PRIOR_20261116_V1.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time
from typing import Any, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import systematic_exploration_v1 as explorer  # noqa: E402
from canonical.runtime.inert_action_prior_v1 import (  # noqa: E402
    DEFERRED_SURCHARGE, InertActionPrior, classify,
)
from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool  # noqa: E402

SCHEMA = "BRAIN_INERT_ACTION_PRIOR_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
BASELINE_RECEIPT = REPO / "canonical/verification/WHERE_THE_WALL_ACTUALLY_IS_20261116_V1.json"

#: How many of one page's offered actions the goal-free probe measures. The probe pays one reset
#: per action, so this is the one place the measurement could buy itself a result with compute.
#: Fixed before any run and reported in every row.
PROBE_ACTION_CAP = 64

#: The pages the 1500-action budget never solved -- the same set the wall measurement scored.
#: Derived from that receipt, never typed here.
UNSOLVED = ("SEARCH_WORLD__STILL_UNEXPLORED_WHEN_THE_BUDGET_RAN_OUT",
            "STATE_WORLD__PAGE_BEHAVES_DIFFERENTLY_ON_WHAT_LOOKS_THE_SAME")

#: Pages that DID yield a first success. Used only as a regression guard: a prior that solves
#: new pages by breaking solved ones is not a gain.
SOLVED_GUARD = ("use-slider",)


def ended(observation: Mapping[str, Any]) -> bool:
    """The episode is over. The agent can see this: the page stops taking input and shows its
    cover. `raw_reward` is NOT read -- that is the oracle, and a prior that reads it is the
    deployment oracle this work exists to remove."""
    return bool(observation.get("done"))


def visible(observation: Mapping[str, Any]) -> tuple:
    """Everything the agent can see about the page's content, and nothing else.

    `utterance` is left out on purpose: it does not change when an action is taken, and
    including it would only add a constant. `done`, `raw_reward` and `js_errors` are left out
    because they are the oracle, not the world.
    """
    elements = observation.get("elements") or []
    body = tuple((e.get("tag"), str(e.get("type") or ""), str(e.get("text") or ""),
                  str(e.get("value") or ""), str(e.get("checked")), str(e.get("selected")),
                  tuple(e.get("box") or ()), str(e.get("classes") or ""))
                 for e in elements)
    return (body, str(observation.get("holding")), str(observation.get("waited_s")),
            str(observation.get("selection") or ""))


def probe_page(bridge: Any, task: str, seed: int, *, limit: int | None,
               max_actions: int | None = None) -> dict[str, Any]:
    """Learn, goal-free, which offered actions do nothing from the initial state of one page.

    One reset per action so no effect masks another. An action that ends the episode is recorded
    as `episode_ended` and its `changed` value is still whatever the visible world did -- the
    probe is not allowed to use `done` to decide anything.
    """
    bridge.load(task)
    start = bridge.reset(seed, time_limit_ms=limit)
    offered = tool.offered_actions(start, tool.HAND_TIER)
    if max_actions is not None:
        offered = offered[:int(max_actions)]
    before = visible(start)
    rows: list[dict[str, Any]] = []
    started = time.time()
    for action in offered:
        fresh = bridge.reset(seed, time_limit_ms=limit)
        before = visible(fresh)
        try:
            after = bridge.act(tool.parse_action(action))
        except Exception as error:  # noqa: BLE001 -- one action must not take the page with it
            rows.append({"kind": "probe", "task": task, "action": action, "observation": fresh,
                         "changed": None, "error": type(error).__name__})
            bridge.restart()
            bridge.load(task)
            continue
        # An episode ENDING is a change the agent can see. Leaving it out was measured wrong on
        # 2026-11-16: MiniWoB++ starts a look-alike next episode, so a press that ends one is
        # indistinguishable from a press that does nothing, and every button looked inert.
        changed = ended(after) or visible(after) != before
        rows.append({"kind": "probe", "task": task, "action": action, "observation": fresh,
                     "changed": changed, "error": None})
    return {"task": task, "offered": len(offered), "rows": rows,
            "seconds": round(time.time() - started, 1)}


def page_local_prior(rows: Sequence[Mapping[str, Any]], task: str) -> dict[str, bool]:
    """Arm C: inert-or-not for this page's initial-state actions, keyed by the action string.

    This is an oracle: it was paid for with one reset per action and is charged nothing."""
    return {str(r["action"]): bool(r["changed"]) for r in rows
            if r.get("task") == task and r.get("changed") is not None}


class Composed:
    """`cost_of` for the explorer: the shipped guided price, with deferred affordances last.

    `local` (arm C) defers an action seen inert on this page from this state. `prior` (arm B)
    defers an action whose CLASS has never done anything anywhere else. Both are ORDERS: a
    deferred action is still offered, still tried if the budget lasts.
    """

    def __init__(self, guided: Any, *, prior: InertActionPrior | None = None,
                 local: Mapping[str, bool] | None = None) -> None:
        self._guided = guided
        self._prior = prior
        self._local = dict(local or {})

    def __call__(self, observation: Mapping[str, Any], action: str) -> tuple[int, int]:
        price, turn = self._guided(observation, action)
        if self._local.get(str(action)) is False:
            return int(price) + DEFERRED_SURCHARGE, 9
        if self._prior is not None and self._prior.is_deferred(classify(observation, action)):
            return int(price) + DEFERRED_SURCHARGE, 9
        return int(price), int(turn)


def run_arm(bridge: Any, task: str, seed: int, *, budget: int, cost_of: Any) -> dict[str, Any]:
    """One search of one page under one price list. The verdict is the page's own reward."""
    env = tool.SeedEnv(bridge, seed, time_limit_ms=tool.EXPLORATION_TIME_LIMIT_MS)
    started = time.time()
    result = explorer.explore_to_goal(
        env, [], is_goal=tool.succeeded, is_dead=tool.failed,
        actions_of=lambda observation: tool.offered_actions(observation, tool.HAND_TIER),
        key_of=tool.state_key, order="cheapest", cost_of=cost_of,
        action_budget=int(budget), reset_cost=1, include_model=False)
    verified = False
    if result.get("pass"):
        # RE-READ THE VERDICT FROM THE PAGE: replay the plan on a fresh page and let the page
        # itself say whether it succeeded. The explorer's own `pass` is never the evidence.
        replay = tool.replay_on_fresh_page(bridge, task, seed, list(result.get("plan_cheapest") or []))
        verified = bool(replay.get("reproduced"))
    return {"pass": bool(result.get("pass")), "verified_on_fresh_page": verified,
            "status": result.get("status"), "budget_spent": int(result.get("budget_spent") or 0),
            "acts": int(result.get("acts") or 0), "states": int(result.get("state_count") or 0),
            "plan_len": len(list(result.get("plan_cheapest") or [])),
            "seconds": round(time.time() - started, 1)}


def measure_page(bridge: Any, task: str, *, seed: int, budget: int,
                 build_prior: Any) -> dict[str, Any]:
    """All three arms on one page, the probe paid once and charged to nobody."""
    row: dict[str, Any] = {"kind": "page", "task": task, "seed": int(seed), "budget": int(budget)}
    probe = probe_page(bridge, task, seed, limit=tool.EXPLORATION_TIME_LIMIT_MS,
                       max_actions=PROBE_ACTION_CAP)
    rows = [r for r in probe["rows"] if r.get("changed") is not None]
    inert = sum(1 for r in rows if r["changed"] is False)
    row.update(probe_offered=probe["offered"], probe_measured=len(rows), probe_inert=inert,
               probe_seconds=probe["seconds"],
               inert_share=round(inert / len(rows), 4) if rows else None)
    local = page_local_prior(probe["rows"], task)
    prior = build_prior()
    shuffled = shuffled_twin(prior)
    row["arms"] = {
        "A_baseline": run_arm(bridge, task, seed, budget=budget, cost_of=tool.GuidedPrices()),
        "B_class_prior": run_arm(bridge, task, seed, budget=budget,
                                 cost_of=Composed(tool.GuidedPrices(), prior=prior)),
        "C_page_local": run_arm(bridge, task, seed, budget=budget,
                                cost_of=Composed(tool.GuidedPrices(), local=local)),
        "D_shuffled_prior": run_arm(bridge, task, seed, budget=budget,
                                    cost_of=Composed(tool.GuidedPrices(), prior=shuffled)),
    }
    row["prior_rows_used"] = len(rows)
    return row


def shuffled_twin(prior: InertActionPrior, *, seed: int = 20261116) -> InertActionPrior:
    """The control: B's counts with the `changes` permuted among classes.

    Same classes, same tries, same number of deferred classes (to within the effect of the
    permutation), and no association left between an affordance and what it did. Built
    deterministically so the control is reproducible and nobody can shuffle until it loses.
    """
    import random

    table = prior.table()
    classes = sorted(table)
    changes = [int(table[c]["changes"]) for c in classes]
    rng = random.Random(seed)
    rng.shuffle(changes)
    twin = InertActionPrior(min_observations=prior._min)  # noqa: SLF001 -- the twin is the same kind
    for cls, n_changes in zip(classes, changes):
        for _ in range(int(table[cls]["tries"])):
            twin._tries[cls] = twin._tries.get(cls, 0) + 1  # noqa: SLF001
        if n_changes:
            twin._changes[cls] = n_changes  # noqa: SLF001
    return twin


def unsolved_pages(receipt: pathlib.Path = BASELINE_RECEIPT) -> list[str]:
    """The pages the wall measurement found unreached, derived from that receipt."""
    data = json.loads(receipt.read_text())
    worlds = (data.get("summary") or {}).get("worlds") or {}
    out: list[str] = []
    for world in UNSOLVED:
        out += list((worlds.get(world) or {}).get("tasks") or [])
    return sorted(set(out))


def holdout_split(tasks: Sequence[str], *, seed: int = 20261116, share: float = 0.5) -> tuple[list[str], list[str]]:
    """Split pages by a hash of the name, so the split cannot be chosen after the numbers.

    Arm B's prior is learned on `learn` and scored on `score`; a page in the scored half never
    contributes a row to the prior that judges it.
    """
    ordered = sorted(tasks, key=lambda t: hashlib.sha256(f"{seed}:{t}".encode()).hexdigest())
    cut = max(1, int(round(len(ordered) * float(share))))
    return ordered[:cut], ordered[cut:]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html-dir")
    parser.add_argument("--node-modules-dir")
    parser.add_argument("--substrate", default="chromium", choices=("chromium", "jsdom"))
    parser.add_argument("--budget", type=int, default=400)
    parser.add_argument("--seed", type=int, default=1060)
    parser.add_argument("--probe-seed", type=int, default=1060)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--learn-tasks", nargs="*", default=None,
                        help="pages arm B learns from; default: the solved half of the split")
    parser.add_argument("--parts", type=int, default=1)
    parser.add_argument("--part", type=int, default=0)
    parser.add_argument("--out", required=False,
                        help="raw JSONL to write when measuring (not needed with --consolidate)")
    parser.add_argument("--consolidate", nargs="+", default=None)
    parser.add_argument("--receipt", default=None)
    args = parser.parse_args(argv)

    if args.consolidate:
        return _consolidate(args.consolidate, args.receipt)
    if not args.out:
        parser.error("--out is required to measure")
    if not args.html_dir or not args.node_modules_dir:
        parser.error("--html-dir and --node-modules-dir are required to measure")

    scored = sorted(args.tasks) if args.tasks else holdout_split(unsolved_pages())[1]
    learn = (sorted(args.learn_tasks) if args.learn_tasks
             else holdout_split(unsolved_pages())[0] + list(SOLVED_GUARD))
    assert not set(scored) & set(learn), "SCORED_PAGE_CONTRIBUTES_TO_ITS_OWN_PRIOR"
    mine = [t for i, t in enumerate(scored) if i % max(1, args.parts) == args.part]

    bridge = tool.Bridge(args.html_dir, args.node_modules_dir, substrate=args.substrate)
    versions = bridge.versions()

    # Arm B's prior: learned from the learn half only, one probe per page, goal-free.
    learn_prior = InertActionPrior()
    learn_rows = 0
    with open(args.out + ".learn", "w") as handle:
        for task in learn:
            probe = probe_page(bridge, task, args.probe_seed,
                               limit=tool.EXPLORATION_TIME_LIMIT_MS)
            for r in probe["rows"]:
                if r.get("changed") is None:
                    continue
                learn_prior.observe(r["observation"], r["action"], changed=bool(r["changed"]))
                learn_rows += 1
                handle.write(json.dumps(r) + "\n")
    build = lambda: learn_prior  # noqa: E731 -- one prior, shared by every scored page

    with open(args.out, "w") as handle:
        for task in mine:
            row = measure_page(bridge, task, seed=args.seed, budget=args.budget, build_prior=build)
            row["learn_rows_total"] = learn_rows
            row["environment"] = versions
            handle.write(json.dumps(row) + "\n")
            print(f"{task:26s} inert={row['inert_share']} "
                  + " ".join(f"{k}={v['pass']}/{v['budget_spent']}a" for k, v in row["arms"].items()),
                  flush=True)
    bridge.close()
    return 0


def _consolidate(paths: Sequence[str], receipt: str | None) -> int:
    """Fold raw rows into a receipt. Every total is a sum over rows that were written, never a
    number typed by hand."""
    pages: list[dict[str, Any]] = []
    probe_rows: list[dict[str, Any]] = []
    for path in paths:
        for line in pathlib.Path(path).read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            (pages if row.get("kind") == "page" else probe_rows).append(row)
    arms = ("A_baseline", "B_class_prior", "C_page_local", "D_shuffled_prior")
    summary: dict[str, Any] = {"pages": len(pages), "probe_rows": len(probe_rows), "arms": {}}
    for arm in arms:
        solved = [p["task"] for p in pages if p["arms"][arm]["pass"]]
        verified = [p["task"] for p in pages if p["arms"][arm]["verified_on_fresh_page"]]
        summary["arms"][arm] = {
            "pass": len(solved), "pass_tasks": sorted(solved),
            "verified_on_fresh_page": len(verified), "verified_tasks": sorted(verified),
            "actions_spent": sum(int(p["arms"][arm]["budget_spent"]) for p in pages),
            "seconds": round(sum(float(p["arms"][arm]["seconds"]) for p in pages), 1),
        }
    measured = sum(1 for p in pages if p.get("inert_share") is not None)
    summary["learn_prior"] = {
        "classes": None, "deferred_classes": None, "digest": None,
        "rows": (pages[0].get("learn_rows_total") if pages else None),
    }
    summary["inert_share_mean"] = (
        round(sum(float(p["inert_share"]) for p in pages if p.get("inert_share") is not None)
              / measured, 4) if measured else None)
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
