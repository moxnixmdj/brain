"""The 37 held-out pages that never gave a first success: is that budget, or is it the vocabulary?

The question
------------
`MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json` is the strongest coverage measurement
this repository has: real headless Chromium (153.0.8010.0), real mouse and key input, the
whole hand (press, triple-press, type, hover, grab, drop, nudge, wait), guided ordering, and
600 actions of search per page. On the held-out split it found a first success on 55 of 92
pages. **37 pages never produced one turn of a successful episode at all.**

Two very different worlds produce that same number, and the difference decides the whole
roadmap:

  * BUDGET        the page is reachable with the hand as it is, and 600 actions was not enough.
                  The fix is cheap: spend more search. Nothing about the vocabulary changes.
  * VOCABULARY    the hand cannot express what the page asks for -- a drag to a place that is
                  not an element, a scroll inside a box, typed text that is not one word of the
                  instruction, a point read off a picture. Repetition and budget cannot close
                  it, however long you search, because the action that would succeed is not in
                  the set being tried. The fix is structural: add the primitive.

The explorer already answers this per page, and the answer is not an opinion. When it stops
with `FAIL_CLOSED__REACHABLE_SPACE_EXHAUSTED_GOAL_ABSENT` it has tried every action reachable
from every state it can tell apart, and no success was among them: for the agent's own state
abstraction, that is a proof that this hand cannot reach the goal. When it stops with
`OPEN__ACTION_BUDGET_EXHAUSTED_GOAL_NOT_OBSERVED` there were still untried actions: the page
is not known to be out of reach, only unexplored.

So this tool re-runs exactly those pages with the same hand, the same substrate, the same
guided order and 2.5x the budget, and reports which of the two worlds each page is in. A page
that is still closed at 1500 was never a budget problem, and no amount of searching will
change it. A page that converts was one, and the coverage number was an artefact of 600.

What this is not
----------------
Not a capability claim, not a leaderboard entry, and not an independent run: the producer ran
it. It scores nothing on unseen instances -- it only asks whether one success exists at all.
It does not add an action, change the hand, or touch the learner. It is a diagnosis of where
the wall is, and its output is a ranked list of primitives, in the order of how many pages each
one is the only thing standing in the way of.

Usage
-----
    python3 canonical/tools/miniwob_where_the_wall_actually_is_v1.py \
        --html-dir <miniwob-plusplus/miniwob/html> --node-modules-dir <dir with node_modules> \
        --budget 1500 --part 0 --parts 2 --out /tmp/wall_part0.jsonl
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool  # noqa: E402

SCHEMA = "BRAIN_MINIWOB_WHERE_THE_WALL_ACTUALLY_IS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
BASELINE_RECEIPT = REPO / "canonical/verification/MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json"
BASELINE_BUDGET = 600          # what the baseline receipt spent per page
BUDGET_UNDER_TEST = 1500       # what the jsdom one-success run spent; 2.5x the baseline

# What each terminal status means for the question above. Kept explicit so the receipt can be
# read without knowing the explorer. There are FOUR worlds, not two, and they have different
# repairs; collapsing them is how a roadmap gets built on the wrong one.
REACHED = "REACHED__FIRST_SUCCESS_FOUND_WITH_THE_SAME_HAND"
ACTION_VOCABULARY = "ACTION_WORLD__EVERY_REACHABLE_ACTION_TRIED_AND_NO_GOAL_AMONG_THEM"
BLIND_TO_STATE = "STATE_WORLD__PAGE_BEHAVES_DIFFERENTLY_ON_WHAT_LOOKS_THE_SAME"
NO_ACTION_OFFERED = "NO_WORLD__THIS_VOCABULARY_OFFERED_NOTHING_TO_TRY"
SEARCH_BUDGET = "SEARCH_WORLD__STILL_UNEXPLORED_WHEN_THE_BUDGET_RAN_OUT"
UNKNOWN_WORLD = "UNKNOWN__PAGE_OR_BRIDGE_ERROR"

# Which repair each world implies, so the receipt ranks work rather than only counting it.
REPAIR = {
    ACTION_VOCABULARY: "add_the_missing_action_primitive",
    BLIND_TO_STATE: "add_the_missing_observable_or_reduce_the_page_to_a_state_the_look_can_tell_apart",
    NO_ACTION_OFFERED: "add_the_missing_action_primitive",
    SEARCH_BUDGET: "improve_the_prior_over_actions_or_spend_more_search",
    REACHED: "none",
    UNKNOWN_WORLD: "repair_the_instrument",
}


def unsolved_held_out(baseline: pathlib.Path = BASELINE_RECEIPT) -> list[dict[str, Any]]:
    """The held-out pages that produced no first success in the baseline, with what it spent.

    Derived, never typed by hand: a page is in the set because the receipt says its stage is
    not DEMONSTRATED and its split is held_out. If the receipt changes, the set changes with it.
    """
    receipt = json.loads(baseline.read_text())
    out = []
    for row in receipt["tasks"]:
        if row.get("split") != "held_out":
            continue
        if row.get("stage") == tool.STAGE_DEMONSTRATED:
            continue
        acquisition = row.get("acquisition") or {}
        out.append({"task": row["task"], "stage_at_600": row.get("stage"),
                    "reason_at_600": row.get("reason"),
                    "budget_spent_at_600": acquisition.get("budget_spent")})
    out.sort(key=lambda r: r["task"])
    return out


def world_of(stage: str, statuses: Sequence[str]) -> str:
    """Which world this page's failure is in.

    Precedence matters. A page that stops because the same look behaved two different ways has
    told us something about the OBSERVATION, and searching longer over an observation that
    merges distinct states cannot help: that verdict outranks the budget one. Only a closed
    exhaustion is a proof that the action set cannot reach the goal, so it is reported only when
    every run closed that way.
    """
    if stage == tool.STAGE_DEMONSTRATED:
        return REACHED
    if tool.explorer.OPEN_UNSTABLE in statuses:
        return BLIND_TO_STATE
    if tool.explorer.OPEN_NO_VOCABULARY in statuses:
        return NO_ACTION_OFFERED
    if statuses and all(s == tool.explorer.FAIL_EXHAUSTED for s in statuses):
        return ACTION_VOCABULARY
    if tool.explorer.OPEN_BUDGET in statuses:
        return SEARCH_BUDGET
    return UNKNOWN_WORLD


def summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Count the worlds, and say for each which repair it is asking for. No hand-typed totals:
    everything here is a fold over the rows the run wrote."""
    by_world: dict[str, list[str]] = {}
    for row in rows:
        # Recomputed from the recorded statuses, never read back from a stored label: a label
        # written by an older build of this file must not decide today's answer.
        by_world.setdefault(world_of(str(row.get("stage")), list(row.get("statuses") or [])),
                            []).append(str(row["task"]))
    worlds = {world: {"tasks": sorted(tasks), "count": len(tasks), "repair": REPAIR.get(world, "?")}
              for world, tasks in sorted(by_world.items())}
    return {
        "pages_measured": len(rows),
        "worlds": worlds,
        "reached": len(by_world.get(REACHED, [])),
        "not_reached": len(rows) - len(by_world.get(REACHED, [])),
        "budget_spent_total": sum(int(r.get("budget_spent") or 0) for r in rows),
        "states_seen_total": sum(int(r.get("states_seen") or 0) for r in rows),
        "seconds_total": round(sum(float(r.get("seconds") or 0) for r in rows), 1),
    }


def measure(bridge: Any, task: str, *, budget: int, seed: int) -> dict[str, Any]:
    started = time.time()
    row: dict[str, Any] = {"task": task, "budget": int(budget)}
    try:
        shown = tool.demonstrate(bridge, task, seed, action_budget=int(budget), search="guided")
        acquisition = shown.get("acquisition") or {}
        statuses = [str(run.get("status")) for run in (acquisition.get("runs") or [])]
        row.update(
            stage=shown["stage"],
            reason=shown.get("reason"),
            statuses=statuses,
            world=world_of(shown["stage"], statuses),
            budget_spent=acquisition.get("budget_spent"),
            states_seen=sum(int(run.get("states") or 0) for run in (acquisition.get("runs") or [])),
            acts=sum(int(run.get("acts") or 0) for run in (acquisition.get("runs") or [])),
            resets=sum(int(run.get("resets") or 0) for run in (acquisition.get("runs") or [])),
            tier=acquisition.get("tier"),
            steps_found=acquisition.get("steps_found"),
            trace_actions=None if not shown.get("trace") else [a for _, a in shown["trace"]],
        )
    except Exception as error:  # noqa: BLE001 -- one page must not take the others with it
        bridge.restart()
        row.update(stage="NOT_MEASURED", reason=type(error).__name__, detail=str(error)[:200],
                   world=UNKNOWN_WORLD)
    row["seconds"] = round(time.time() - started, 1)
    return row


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html-dir", required=True)
    parser.add_argument("--node-modules-dir", required=True,
                        help="directory that CONTAINS node_modules (the chromium bridge appends it)")
    parser.add_argument("--substrate", default="chromium", choices=("chromium", "jsdom"))
    parser.add_argument("--budget", type=int, default=BUDGET_UNDER_TEST)
    parser.add_argument("--seed", type=int, default=tool.DEMO_SEED)
    parser.add_argument("--part", type=int, default=0)
    parser.add_argument("--parts", type=int, default=1)
    parser.add_argument("--tasks", nargs="*", default=None, help="default: derived from the baseline receipt")
    parser.add_argument("--baseline", default=str(BASELINE_RECEIPT))
    parser.add_argument("--out", required=True)
    parser.add_argument("--consolidate", nargs="+", default=None,
                        help="instead of measuring: fold these JSONL files (raw rows) into a receipt")
    args = parser.parse_args(argv)

    if args.consolidate:
        header, rows = {}, []
        for path in args.consolidate:
            for line in open(path):
                record = json.loads(line)
                if record.get("kind") == "header":
                    header = record
                elif record.get("kind") == "task":
                    record["world"] = world_of(str(record.get("stage")), list(record.get("statuses") or []))
                    rows.append(record)
        rows.sort(key=lambda r: r["task"])
        receipt = {"schema": SCHEMA, "authority": AUTHORITY, "kind": "receipt",
                   "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "header": header, "summary": summarise(rows), "tasks": rows,
                   "producer_cognition_model_dependency_count": 0, "incremental_spend_usd": 0}
        pathlib.Path(args.out).write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
        print(json.dumps(receipt["summary"]["worlds"], indent=1))
        print("reached", receipt["summary"]["reached"], "of", receipt["summary"]["pages_measured"])
        return 0

    if args.parts < 1 or not 0 <= args.part < args.parts:
        raise SystemExit("PART_OUT_OF_RANGE")
    work = ([{"task": t, "stage_at_600": None, "reason_at_600": None, "budget_spent_at_600": None}
             for t in args.tasks] if args.tasks else unsolved_held_out(pathlib.Path(args.baseline)))
    mine = work[args.part::args.parts]

    bridge = tool.Bridge(args.html_dir, args.node_modules_dir, substrate=args.substrate)
    try:
        versions = bridge.versions()
        with open(args.out, "a") as handle:
            handle.write(json.dumps({"schema": SCHEMA, "authority": AUTHORITY, "kind": "header",
                                     "baseline": str(args.baseline), "baseline_budget": BASELINE_BUDGET,
                                     "budget": int(args.budget), "substrate": args.substrate,
                                     "versions": versions, "part": args.part, "parts": args.parts,
                                     "assigned": [w["task"] for w in mine],
                                     "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                     "producer_cognition_model_dependency_count": 0,
                                     "incremental_spend_usd": 0}) + "\n")
            for item in mine:
                row = measure(bridge, item["task"], budget=args.budget, seed=args.seed)
                row.update({"kind": "task", "stage_at_600": item["stage_at_600"],
                            "budget_spent_at_600": item["budget_spent_at_600"]})
                handle.write(json.dumps(row, sort_keys=True) + "\n")
                handle.flush()
                print(f"{row['task']:<28} {row.get('stage'):<34} {row.get('world'):<56} "
                      f"spent={row.get('budget_spent')} states={row.get('states_seen')} "
                      f"{row.get('seconds')}s", flush=True)
    finally:
        bridge.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
