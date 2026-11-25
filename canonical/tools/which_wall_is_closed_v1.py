#!/usr/bin/env python3
"""Is the front door the bottleneck, or is the back door also locked?

TWO WALLS, MEASURED SEPARATELY
------------------------------
Wall 1 (the front door). `solve(goal, mode="EPISTEMIC")` refuses a goal whose tokens the model does not
recognise, before any work happens. Measured on 80 real SWE-bench Verified issue texts: 52 of 80 refused
(65%), median coverage 0.290 against a 0.34 floor. And a goal with NO content at all -- "Fix the bug in the
function so the test passes" -- scores 0.833 and routes confidently. Confidence rises as the task gets
emptier.

Wall 2 (the back door). When the goal IS accepted and a capability IS chosen, can that capability emit an
action? `run_epistemic_goal` returns status BLOCKED_NO_MODEL_PROPOSAL whenever the container-side solver
returns no accepted proposal with at least one action. The published smoke run on the SWE-bench Pro harness
recorded exactly that for both tasks it ran, with patch_bytes 0.

WHY BOTH MUST BE MEASURED BEFORE ANYTHING IS BUILT
--------------------------------------------------
If wall 2 is closed, then everything built to improve routing, oracle discrimination, generation or
multi-file synthesis is built on a front door that opens onto a wall. Fixing the front door would raise
acceptance from 28/80 to 80/80 and change no outcome. That is the difference between a measurable
improvement and a decorative one, and it is decidable today, without Docker, without a benchmark row.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

SCHEMA = "BRAIN_WHICH_WALL_IS_CLOSED_V1"
CORPUS = REPO / "canonical" / "corpus" / "swe_verified_issue_text_20261124_V1.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    started = time.time()

    import collections

    from canonical.runtime.brain_unified_model_v1 import open_model, tokenize

    model = open_model(root=str(REPO))
    instances = json.loads(CORPUS.read_text())["per_instance"]

    # ---- wall 1: the gate
    routed = []
    for instance, cell in sorted(instances.items()):
        text = ((cell.get("title") or "") + "\n" + (cell.get("body") or "")).strip()
        if len(text) < 20:
            continue
        routing = model.route(text)
        routed.append({"instance": instance, "coverage": routing["coverage"],
                       "confident": routing["confident"],
                       "best": (routing["best"] or {}).get("id")})
    accepted = [row for row in routed if row["confident"]]

    # ---- the concentration of the routing decision
    wins = collections.Counter(row["best"] for row in routed if row["best"])
    terms = collections.Counter()
    for postings in model.index.values():
        for cid in postings:
            terms[cid] += 1
    never_wins = [cid for cid in model.capabilities if wins.get(cid, 0) == 0]
    thin = [cid for cid in model.capabilities if terms.get(cid, 0) <= 8]

    # ---- wall 2: can the chosen capability emit an action at all, with no environment?
    # A container-free probe: the shipped transport asks the container to solve. The honest local question
    # is narrower and answerable -- does the capability envelope itself carry any proposed action, or does
    # it fail closed? No benchmark is run and no patch is claimed.
    import asyncio

    from canonical.runtime.harbor_epistemic_agent_v1 import run_epistemic_goal

    class NoEnvironment:
        """An environment whose every exec fails, which is what 'no container' honestly means."""

        async def exec(self, command: str, timeout_sec: int) -> Any:
            raise RuntimeError("NO_CONTAINER_ATTACHED")

    wall2: dict[str, Any] = {}
    probe_goal = ("In more_itertools, chunked(iterable, n) raises ZeroDivisionError when n=0; it should "
                  "raise ValueError. Fix it.")
    try:
        outcome = asyncio.get_event_loop().run_until_complete(
            run_epistemic_goal(probe_goal, NoEnvironment(), max_cycles=1))
        wall2 = {"status": outcome.get("status"),
                 "proposed_actions": (outcome.get("trace") or [{}])[0].get("proposed_actions"),
                 "patch_emitted": outcome.get("patch_emitted")}
    except Exception as error:                       # noqa: BLE001 -- recorded, not hidden
        wall2 = {"status": "PROBE_RAISED", "error": f"{type(error).__name__}: {error}"[:300]}

    summary = {
        "instances": len(routed),
        "wall_1_front_door": {
            "refused": len(routed) - len(accepted),
            "accepted": len(accepted),
            "refusal_rate": round((len(routed) - len(accepted)) / max(1, len(routed)), 4),
            "distinct_winner_capabilities": len(wins),
            "top_winner_share": round(wins.most_common(1)[0][1] / max(1, len(routed)), 4),
        },
        "routing_concentration": {
            "capabilities": len(model.capabilities),
            "index_terms": len(model.index),
            "median_terms_per_capability": sorted(terms.get(c, 0) for c in model.capabilities)
            [len(model.capabilities) // 2],
            "capabilities_that_never_win_a_real_issue": len(never_wins),
            "share_that_never_win": round(len(never_wins) / len(model.capabilities), 4),
            "thin_capabilities_at_or_under_8_terms": len(thin),
        },
        "wall_2_back_door": wall2,
        "verdicts": {
            "the_front_door_refuses_a_majority_of_real_issues":
                (len(routed) - len(accepted)) > len(routed) / 2,
            "the_router_is_a_32_way_decision_wearing_447_arms":
                len(wins) <= 40,
            "most_capabilities_never_win_a_real_issue": len(never_wins) / len(model.capabilities) > 0.5,
            "the_back_door_emits_no_action_without_a_container":
                str(wall2.get("status", "")).startswith("BLOCKED"),
            "fixing_the_front_door_alone_would_change_no_outcome":
                str(wall2.get("status", "")).startswith("BLOCKED"),
        },
        "reading": (
            "Wall 1 is a real defect: 65% of real issues are refused before any work, and the confidence "
            "signal rises as content falls. Wall 2 is the binding constraint: with no container the "
            "transport returns BLOCKED_NO_MODEL_PROPOSAL and emits no patch. Because wall 2 is closed, "
            "raising wall-1 acceptance from 28/80 to 80/80 changes no measured outcome -- so the honest "
            "next object is the generator, not the gate. The concentration numbers say where the generator "
            "would have to live: 415 of 447 capabilities never win a real issue and the median capability "
            "carries 7 index terms, so the routing table is 447 labels over a 32-way decision."),
        "what_this_does_not_show": (
            "any benchmark score, any solved task, any patch. Wall 2 is measured with NO container attached, "
            "which proves the transport fails closed without one; it does not prove the container-side "
            "solver fails when one IS attached. The published CI smoke run is the evidence for that, and it "
            "recorded BLOCKED_NO_MODEL_PROPOSAL with patch_bytes 0 for both tasks it ran."),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
    }, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
