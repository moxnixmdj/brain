#!/usr/bin/env python3
"""Measure the contract arm on every MiniWoB page, with no reward anywhere in the policy.

The arm is the one that reads the instruction: `instruction_contract_v1.compile_contract` turns
the words into clauses, `instruction_policy_v1.ContractArm` turns the clauses into actions. The
page's own reward is read **only after** the arm says it is finished, and only to record whether
it was right. That ordering is the whole measurement: an arm that looks at the reward has not
understood the instruction, and a number produced by such an arm says nothing about understanding.

This file exists because the previous harness lived in `/tmp` and was lost with the sandbox. A
measurement you cannot re-run is a memory, not a result.

    python3 -m canonical.tools.miniwob_contract_arm_arm_v1 \
        --html-dir /path/to/miniwob/html --nodes /path/to/node_modules \
        --seed 1060 --action-budget 30 --out /tmp/arm.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import instruction_policy_v1 as policy  # noqa: E402
from canonical.tools import miniwob_one_success_generalisation_measure_v1 as measure  # noqa: E402


def pages(html_dir: pathlib.Path) -> list[str]:
    # The chromium bridge resolves `<html-dir>/miniwob/<task>.html`, so a checkout passes the
    # directory that CONTAINS `miniwob/`. Honour both shapes.
    if (html_dir / "miniwob").is_dir():
        html_dir = html_dir / "miniwob"
    """Every page the substrate ships, by directory name. No page is skipped: a skipped page is a
    place the measurement cannot be wrong, which is the same as a place it cannot be right."""
    # Substrates differ: a checkout may hold `task/index.html` or flattened `task.html`. Both are
    # accepted and neither is privileged, so the same command measures any checkout.
    nested = {p.parent.name for p in html_dir.glob("*/index.html")}
    flat = {p.stem for p in html_dir.glob("*.html")}
    return sorted(nested | flat)


def run_page(bridge: Any, task: str, seed: int, budget: int) -> dict[str, Any]:
    bridge.load(task)
    observation = bridge.reset(seed)
    utterance = str(observation.get("utterance") or "")

    arm = policy.ContractArm()
    arm.begin(observation, seed)

    actions: list[str] = []
    for _ in range(int(budget)):
        if measure.succeeded(observation) or measure.failed(observation):
            break
        action = arm.next_action(observation)
        if action is None:
            break
        actions.append(action)
        observation = bridge.act(measure.parse_action(action))
        if not observation.get("elements"):
            break

    # The reward is read HERE and only here, after the arm has stopped.
    won = bool(measure.succeeded(observation))
    # THE ARM'S OWN VERDICT, NOT THE LABEL ON IT. Measured 2026-11-16: six pages were refused with
    # `refused_part` (half an instruction understood) while `refusal` was None, and the census
    # counted them as neither refused nor failing -- a measurement that under-reports its own
    # refusals is measuring its optimism. The refusal is what the arm DID.
    label = arm.contract.get("refusal")
    if label is None and arm.refused:
        part = arm.contract.get("refused_part")
        label = f"REFUSED__HALF_UNDERSTOOD:{part}" if part else "REFUSED__THE_ARM_CANNOT_ACT"
    # AND THE OTHER HALF OF THE SAME LIE: an arm that is NOT refused, holds a clause, and still
    # emits nothing has failed to turn its own clause into an action. Calling that "not refused"
    # made 16 pages invisible in the census -- the arm had understood the words and could not
    # reach the thing. A refusal that costs no words spent is still a refusal, and it must be
    # counted as one or the census measures only the failures that are convenient to name.
    if label is None and not arm.refused and not actions and not won:
        held = [str(c.get("operator")) for c in arm.contract.get("clauses") or []]
        label = ("REFUSED__THE_CLAUSE_COULD_NOT_BECOME_AN_ACTION:" + ",".join(held)
                 if held else "REFUSED__NOTHING_TO_ACT_ON")
    return {
        "page": task,
        "utterance": utterance,
        "refused": bool(arm.refused),
        "refusal": label,
        "refused_part": arm.contract.get("refused_part"),
        "operators": [c["operator"] for c in arm.contract.get("clauses") or []],
        "actions": actions,
        "won": won,
        "failed": bool(measure.failed(observation)),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-dir", required=True)
    parser.add_argument("--nodes", default="")
    parser.add_argument("--seed", type=int, default=1060)
    parser.add_argument("--action-budget", type=int, default=30)
    parser.add_argument("--only", default="", help="comma separated page names")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)

    html_dir = pathlib.Path(args.html_dir)
    wanted = [p.strip() for p in args.only.split(",") if p.strip()]
    names = wanted or pages(html_dir)

    bridge = measure.Bridge(str(html_dir), args.nodes, substrate="chromium")
    results = []
    try:
        for index, task in enumerate(names, 1):
            try:
                row = run_page(bridge, task, args.seed, args.action_budget)
            except Exception as error:                      # a page that will not load is data
                row = {"page": task, "won": False, "refused": True,
                       "refusal": f"PAGE_ERROR:{type(error).__name__}", "actions": [],
                       "operators": [], "failed": False, "utterance": ""}
            results.append(row)
            mark = "W" if row["won"] else ("R" if row["refused"] else ".")
            print(f"{index:3}/{len(names)} {mark} {task:34} {(row['refusal'] or '')[:44]}", flush=True)
    finally:
        bridge.close()

    won = sum(1 for r in results if r["won"])
    refusals: dict[str, int] = {}
    for row in results:
        if row["refusal"]:
            refusals[row["refusal"]] = refusals.get(row["refusal"], 0) + 1
    summary = {
        "pages": len(results),
        "won": won,
        "rate": round(won / len(results), 4) if results else 0.0,
        "refused": sum(1 for r in results if r["refused"]),
        "refusals": dict(sorted(refusals.items(), key=lambda kv: -kv[1])),
        "seed": args.seed,
        "action_budget": args.action_budget,
        "authority": "NONE -- SANDBOX MEASUREMENT",
        "results": results,
    }
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=1))
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(summary, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
