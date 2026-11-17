#!/usr/bin/env python3
"""Where reading beats learning, measured on the same 130 pages.

WHY THIS EXISTS BESIDE THE OTHER INSTRUMENTS
--------------------------------------------
`one_success_where_it_counts_v1` prints the LADDER: random < replay < this tree's generaliser < one
success. Every rung above `random` is measured on pages where a search was first allowed to find a
success with the page's reward visible. So the ladder answers "how well does one success generalise",
which is not the question the architecture needs. The question is:

    on which pages does learning have anything to add, and on which does reading already win?

Those are different denominators, and the ladder cannot express the difference because it never runs
the arm that has no experience at all. This tool does, on the same pages, and intersects per page.

WHAT IT REPORTS
---------------
  1. the zero-experience reading arm on all 130 pages (live, or from `--reading-from` a recorded run)
  2. for each page, whether a first success was ever found by exploration (`--ladder-from`)
  3. the intersection:
        won by reading AND demonstrable     -> learning had nothing to add
        won by reading but NEVER demonstrable -> reading beat trying outright
        demonstrable but reading lost       -> the named gap a policy may be acquired for
        neither                             -> out of reach of both

  4. `decide()` applied to every page, so the composition rule is measured, not asserted: it says
     READ on the pages reading wins and LEARN on the pages it does not, and this prints the two
     counts beside each other.

It refuses to print a board if the recorded reading run and the recorded ladder disagree about which
pages exist -- a board over mismatched denominators is the exact error it was built to stop.

AUTHORITY NONE. No model, no reward read by the arm, no parameter, $0.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

LADDER = REPO / "canonical/verification/MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json"
SCHEMA = "BRAIN_LEARN_OR_READ_BOARD_V1"


def reading_board(html_dir: str, nodes: str, *, seed: int, budget: int,
                  only: str = "") -> dict[str, bool]:
    """The zero-experience arm, per page. Live."""
    from canonical.tools import miniwob_contract_arm_arm_v1 as arm_tool

    argv = ["--html-dir", html_dir, "--nodes", nodes, "--seed", str(seed),
            "--action-budget", str(budget), "--out", "/tmp/_learn_or_read_board.json"]
    if only:
        argv += ["--only", only]
    arm_tool.main(argv)
    data = json.loads(pathlib.Path("/tmp/_learn_or_read_board.json").read_text())
    return {row["page"]: bool(row["won"]) for row in data["results"]}


def demonstrated_pages(path: pathlib.Path = LADDER) -> dict[str, str]:
    """Which pages a search ever reached, from the recorded ladder."""
    data = json.loads(path.read_text())
    return {t["task"]: str(t.get("stage")) for t in data["tasks"]}


def board(reading: dict[str, bool], stages: dict[str, str]) -> dict[str, Any]:
    missing = sorted(set(stages) - set(reading))
    if missing:
        raise SystemExit(f"REFUSED__DENOMINATORS_DISAGREE: {len(missing)} pages in the ladder are "
                         f"absent from the reading run: {missing[:5]}")
    demo = {p for p, s in stages.items() if s == "DEMONSTRATED"}
    never = set(stages) - demo
    won = {p for p, w in reading.items() if w}

    cells = {
        "reading_wins_and_demonstrable": sorted(won & demo),
        "reading_wins_where_nothing_was_demonstrable": sorted(won & never),
        "demonstrable_but_reading_lost": sorted(demo - won),
        "out_of_reach_of_both": sorted(never - won),
    }
    total = len(stages)
    return {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "pages": total,
        "reading_won": len(won),
        "demonstrable": len(demo),
        "never_demonstrable": len(never),
        "cells": {k: {"count": len(v), "pages": v} for k, v in cells.items()},
        "the_two_facts": {
            "learning_had_nothing_to_add_on": len(cells["reading_wins_and_demonstrable"]),
            "of_which_share_of_demonstrable": (
                round(len(cells["reading_wins_and_demonstrable"]) / len(demo), 4) if demo else None),
            "reading_beat_trying_on": len(cells["reading_wins_where_nothing_was_demonstrable"]),
            "named_gaps_a_policy_may_be_acquired_for": len(cells["demonstrable_but_reading_lost"]),
        },
        "what_this_is_not": ("Not a leaderboard entry: the ladder's demonstrations were found with the "
                             "page's reward visible, which a deployed agent is not given. The reading "
                             "arm never reads a reward at all."),
    }


def decide_every_page(html_dir: str, nodes: str, *, seed: int) -> dict[str, Any]:
    """`learn_or_read_v1.decide` on every page, so the composition rule is measured."""
    from canonical.runtime import learn_or_read_v1 as LR
    from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool

    bridge = tool.Bridge(html_dir, nodes, substrate="chromium")
    counts: dict[str, int] = {}
    rows = []
    try:
        for path in sorted((pathlib.Path(html_dir) / "miniwob").glob("*.html")):
            page = path.stem
            bridge.load(page)
            observation = bridge.reset(seed)
            got = LR.decide(observation.get("utterance") or "", observation)
            counts[got.outcome] = counts.get(got.outcome, 0) + 1
            rows.append({"page": page, **got.as_dict()})
    finally:
        bridge.close()
    return {"outcome_counts": counts, "rows": rows,
            "rule": LR.composition_rule()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-dir")
    parser.add_argument("--nodes", default="")
    parser.add_argument("--seed", type=int, default=1060)
    parser.add_argument("--action-budget", type=int, default=30)
    parser.add_argument("--reading-from", help="a recorded arm run instead of a live one")
    parser.add_argument("--ladder-from", default=str(LADDER))
    parser.add_argument("--decide", action="store_true", help="also measure the composition rule")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)

    if args.reading_from:
        data = json.loads(pathlib.Path(args.reading_from).read_text())
        reading = {row["page"]: bool(row["won"]) for row in data["results"]}
    elif args.html_dir:
        reading = reading_board(args.html_dir, args.nodes, seed=args.seed,
                                budget=args.action_budget)
    else:
        parser.error("--html-dir or --reading-from is required")

    result = board(reading, demonstrated_pages(pathlib.Path(args.ladder_from)))
    if args.decide:
        if not args.html_dir:
            parser.error("--decide needs --html-dir: it reads every page's observation")
        result["composition_rule"] = decide_every_page(args.html_dir, args.nodes, seed=args.seed)

    text = json.dumps(result, indent=1, sort_keys=True)
    if args.out:
        pathlib.Path(args.out).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
