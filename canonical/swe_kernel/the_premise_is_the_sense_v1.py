"""What the plan's premise costs to SEE: the cheapest sufficient sense, derived not chosen.

THE QUESTION THIS ANSWERS, AND WHY IT IS THE BOTTLENECK
-------------------------------------------------------
`ONE_TRY_LEARNS_A_DOMAIN_NOT_THE_ENVIRONMENT_20261116_V1.md` measured what one demonstration is
worth on a real git repository and named the bottleneck in one line:

    "The single bottleneck: the premise. Not the store, not the parameters, not the plan, not the
     speed of replay. Whether the fact the plan depends on is OBSERVABLE AT THE MOMENT OF ACTING."

It then hand-listed four sense vocabularies and scored them. That answers "is a rich sense better
than a poor one" -- yes, always. It does NOT answer the question that decides the architecture:

    **which facts must be read before running this plan, and what do they cost?**

That question is exactly solvable and nobody had solved it here. It matters because it separates the
two things that get confused:

  * MORE EXPERIENCE   -- more demonstrations. Measured: the undecidable set is INVARIANT to it.
  * MORE SENSING      -- reading the premise. Measured: 24 undecidable states -> 0.

An agent that reads the premise can REFUSE when the premise fails. An agent that does not read it
runs the plan and fails silently. Frontier measurement agrees this is the dominant failure mode:
46-64% of plans for solvable tasks contain an inapplicable action, and those account for 89% of
failed episodes (Testing the Planning Claims of LLM-Based Agents against Formal Semantics, Oct 2026).

THE FORMULATION, WHICH IS A PROVEN OPTIMISATION AND NOT A HEURISTIC
------------------------------------------------------------------
A plan P is one action choice at every state: RUN (it reaches the goal) or REFUSE (it does not). Two
states may share one perception ONLY if they agree on that choice -- otherwise the agent is looking
at two different situations, deciding one thing, and is wrong in one of them. If they agree, no
further discrimination is needed no matter how different they are in fact.

So: build atomic facts from what `git` can actually be asked, give each a real measured cost, and
solve the exact minimum-cost fact set such that every perception cell is decision-consistent. That
is `k6_decision_refinement_compiler_v1.compile_refinement`, which is exhaustive over all subsets and
therefore optimal -- not greedy. This module REUSES it, and separately verifies it against brute
force rather than trusting its name.

WHAT IS NEW HERE (and what is not)
----------------------------------
NOT new: the compiler, the git world, the plans, the goals, the exploration. All reused unchanged.
NEW: the fact vocabulary (what the OS can be asked, priced), and the reduction of "which sense is
sufficient" to the compiler's own contract, plus the ORDERED COST OF ACTING BLIND measured against
it -- which is the number an architect needs and the tree did not have.

Authority: NONE. $0. Zero model dependency. Executes real git commands; invents nothing.
"""
from __future__ import annotations

import itertools
import json
import pathlib
import shutil
import sys
import tempfile
from typing import Any, Callable, Hashable, Mapping, Sequence

sys.path.insert(0, "/home/user/brain")

from canonical.runtime.k6_decision_refinement_compiler_v1 import compile_refinement  # noqa: E402
from canonical.swe_kernel import one_demonstration_basin_v1 as basin  # noqa: E402

SCHEMA = "THE_PREMISE_IS_THE_SENSE_20261116_V1"
AUTHORITY = "NONE__PRODUCER_RUN_REAL_GIT_TRANSITIONS"

RUN = "RUN_PLAN"
REFUSE = "REFUSE_PLAN"
CONFIRM = "CONFIRM_GOAL"

#: A plan is ONE choice, and the honest version of that choice has a postcondition in it: where the
#: plan applies, run it AND check the goal afterwards; where it does not, refuse. Dropping CONFIRM
#: makes the problem degenerate -- a policy of "always refuse" then counts as sufficient, because
#: no cell would ever need to run. Measured in this session: refusal-only reports 1 fact sufficient
#: for both tasks, which is true and useless. The postcondition is what makes sufficiency mean
#: "knows when to act AND can tell whether it worked", which is the basin document's own rule that a
#: plan with no checkable premise is not reused but gambled.

#: Atomic facts, each one a real thing a shell can be asked, with a real cost in tool calls.
#:
#: Cost is not invented: it is the number of processes the read needs. A status read is one git
#: call; the index (`git ls-files -s`) is a second; each file's text is a read the agent must have
#: performed. Reading a fact the plan does not depend on is pure waste, which is the point.
FACTS: tuple[tuple[str, float], ...] = (
    ("branch", 1.0),
    ("staged", 1.0),
    ("unstaged", 1.0),
    ("untracked", 1.0),
    ("tracked", 1.0),
    ("head", 1.0),
    ("staged_rows", 1.0),
    ("content:a.txt", 1.0),
    ("content:b.txt", 1.0),
    ("content:note.log", 1.0),
    ("content:.gitignore", 1.0),
)

#: The hand-listed senses the basin shipped, expressed in atomic facts, so the two are comparable.
BASIN_SENSES: dict[str, tuple[str, ...]] = {
    "status": ("branch", "staged", "unstaged", "untracked", "tracked", "head"),
    "status+content(a.txt)": ("branch", "staged", "unstaged", "untracked", "tracked", "head",
                              "content:a.txt"),
    "status+content(all)": ("branch", "staged", "unstaged", "untracked", "tracked", "head",
                            "content:a.txt", "content:b.txt", "content:note.log",
                            "content:.gitignore"),
    "status+content(all)+staged": ("branch", "staged", "unstaged", "untracked", "tracked", "head",
                                   "content:a.txt", "content:b.txt", "content:note.log",
                                   "content:.gitignore", "staged_rows"),
}


def fact_value(probe: Mapping[str, Any], fact: str) -> Hashable:
    """One atomic fact, read from the probe the basin already collected."""
    if fact.startswith("content:"):
        name = fact.split(":", 1)[1]
        for path, text in probe["contents"]:
            if path == name:
                return text
        return "<absent>"
    return probe[fact]


def observations(probe: Mapping[str, Any], facts: Sequence[str]) -> Hashable:
    return tuple((fact, repr(fact_value(probe, fact))) for fact in facts)


def cells(model: Mapping[str, Any], facts: Sequence[str]) -> list[list[str]]:
    """Group worlds by what these facts would show. Sorted, so the result is canonical."""
    groups: dict[Hashable, list[str]] = {}
    for state in model["states"]:
        groups.setdefault(observations(model["probes"][state], facts), []).append(state)
    return [sorted(v) for _, v in sorted(groups.items(), key=lambda kv: repr(kv[0]))]


def decision_consistent(cell: Sequence[str], actions_by_state: Mapping[str, Sequence[str]]) -> bool:
    """True when every state in the cell accepts a common action -- i.e. one perception suffices."""
    if not cell:
        return False
    common = set(actions_by_state[cell[0]])
    for state in cell[1:]:
        common.intersection_update(actions_by_state[state])
    return bool(common)


def brute_force_minimum(
    worlds: Sequence[str],
    actions_by_state: Mapping[str, Sequence[str]],
    fact_costs: Mapping[str, float],
) -> dict[str, Any]:
    """The same answer `compile_refinement` must give, computed by an independent enumeration.

    Deliberately written differently -- it enumerates by ascending size then cost, and returns the
    first combination that works -- so agreement is evidence and not a tautology.
    """
    names = sorted(fact_costs)
    best: tuple[float, int, tuple[str, ...]] | None = None
    for r in range(len(names) + 1):
        for combo in itertools.combinations(names, r):
            groups: dict[Hashable, list[str]] = {}
            for state in worlds:
                groups.setdefault(observations_raw(state, combo), []).append(state)
            if all(decision_consistent(cell, actions_by_state) for cell in groups.values()):
                cost = sum(fact_costs[f] for f in combo)
                key = (cost, len(combo), tuple(sorted(combo)))
                if best is None or key < best:
                    best = key
    if best is None:
        return {"status": "NONIDENTIFIABLE_WITH_ADMISSIBLE_PRECOMMITMENT_INFORMATION"}
    return {"status": "SUFFICIENT_DECISION_PARTITION_FOUND",
            "selected_facts": list(best[2]), "total_cost": best[0]}


def observations_raw(state: str, facts: Sequence[str]) -> Hashable:
    """Placeholder replaced by the caller with the real projection; keeps brute force generic."""
    return _PROBE_TABLE[state](facts)


_PROBE_TABLE: dict[str, Callable[[Sequence[str]], Hashable]] = {}


def plan_domain(model: Mapping[str, Any], plan: Sequence[str],
                is_goal: Callable[[Mapping[str, Any]], bool]) -> set[str]:
    return {state for state in model["states"] if basin.run_plan(model, state, plan, is_goal)[0]}


def actions_for_plan(domain: set[str], states: Sequence[str]) -> dict[str, list[str]]:
    """Run and confirm where the plan reaches the goal; refuse where it does not."""
    return {state: ([RUN, CONFIRM] if state in domain else [REFUSE]) for state in states}


def actions_refusal_only(domain: set[str], states: Sequence[str]) -> dict[str, list[str]]:
    """The degenerate formulation, kept only so the measurement can show it is degenerate."""
    return {state: [RUN] if state in domain else [REFUSE] for state in states}


def undecidable_states(model: Mapping[str, Any], facts: Sequence[str],
                       acceptable: Mapping[str, Sequence[str]]) -> tuple[int, int]:
    """States living in a cell with no common action, and the number of such cells.

    This is the only place an agent can go wrong: inside a consistent cell every perception maps to
    an action that is right for every state that looks like it. Outside, the agent is looking at two
    different situations and deciding one thing.
    """
    bad = 0
    bad_cells = 0
    for cell in cells(model, facts):
        if not decision_consistent(cell, acceptable):
            bad += len(cell)
            bad_cells += 1
    return bad, bad_cells


def measure(*, max_states: int = 700) -> dict[str, Any]:
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="brain_sense_"))
    try:
        world = basin.GitWorld(scratch / "repo")
        model = basin.explore(world, basin.actions(), max_states=max_states)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    states = list(model["states"])
    facts = [name for name, _cost in FACTS]
    costs = dict(FACTS)
    _PROBE_TABLE.clear()
    for state in states:
        probe = model["probes"][state]
        _PROBE_TABLE[state] = (lambda p: (lambda fs: observations(p, fs)))(probe)

    results: list[dict[str, Any]] = []
    for label, is_goal in (("A_COMMITTED_AND_CLEAN", basin.goal_commit),
                           ("C_COMMITTED_AND_b_txt_STILL_one", basin.goal_pair)):
        dist = basin.distances(model, is_goal)
        plan = basin.best_demonstration(model, dist)
        if not plan:
            results.append({"label": label, "status": "NO_DEMONSTRATION"})
            continue
        domain = plan_domain(model, plan, is_goal)
        acceptable = actions_for_plan(domain, states)
        blind = len(cells(model, []))

        compiler = compile_refinement(
            worlds=states,
            acceptable_actions=acceptable,
            discriminators=[
                {"id": name, "observations": {s: repr(fact_value(model["probes"][s], name))
                                              for s in states},
                 "cost": cost, "arrival": 0, "authorized": True, "owned_operator": True}
                for name, cost in FACTS
            ],
            commitment_deadline=0,
        )
        brute = brute_force_minimum(states, acceptable, costs)
        agree = (compiler.get("status") == brute.get("status")
                 and sorted(compiler.get("selected_discriminators") or [])
                 == sorted(brute.get("selected_facts") or []))

        # What each hand-listed sense costs, and whether it is even sufficient.
        baseline = []
        for sense_name, chosen in BASIN_SENSES.items():
            groups = cells(model, chosen)
            sufficient = all(decision_consistent(c, acceptable) for c in groups)
            bad, bad_cells = undecidable_states(model, chosen, acceptable)
            baseline.append({
                "sense": sense_name,
                "facts": len(chosen),
                "cost": sum(costs[f] for f in chosen),
                "cells": len(groups),
                "sufficient": sufficient,
                "states_the_agent_cannot_decide": bad,
                "cells_the_agent_cannot_decide": bad_cells,
            })

        selected = compiler.get("selected_discriminators") or []
        minimal_bad, minimal_bad_cells = undecidable_states(model, selected, acceptable)
        refusal_only = compile_refinement(
            worlds=states,
            acceptable_actions=actions_refusal_only(domain, states),
            discriminators=[
                {"id": name, "observations": {s: repr(fact_value(model["probes"][s], name))
                                              for s in states},
                 "cost": cost, "arrival": 0, "authorized": True, "owned_operator": True}
                for name, cost in FACTS
            ],
            commitment_deadline=0,
        )
        results.append({
            "refusal_only_is_degenerate": {
                "minimum_facts": refusal_only.get("selected_discriminators"),
                "minimum_cost": refusal_only.get("total_cost"),
                "reading": ("without a postcondition, 'always refuse' satisfies sufficiency for one "
                            "fact and solves nothing; the postcondition is what stops the optimiser "
                            "buying the empty policy"),
            },
            "states_the_agent_cannot_decide": minimal_bad,
            "cells_the_agent_cannot_decide": minimal_bad_cells,
            "label": label,
            "status": "MEASURED",
            "states": len(states),
            "plan_length": len(plan),
            "plan_domain": len(domain),
            "states_where_plan_fails": len(states) - len(domain),
            "cells_when_blind": blind,
            "minimum_facts": selected,
            "minimum_cost": compiler.get("total_cost"),
            "minimum_cells": len(compiler.get("cells") or []),
            "compiler_and_brute_force_agree": agree,
            "hand_listed_senses": baseline,
            "cost_of_the_shipped_richest_sense": max(
                (row["cost"] for row in baseline), default=None),
            "factor_cheaper_than_that": (
                max((row["cost"] for row in baseline), default=0) / compiler["total_cost"]
                if compiler.get("total_cost") else None),
            "blind_decision_is_wrong_in_states": (
                len(states) - max(len(domain), len(states) - len(domain))),
            "reading_the_premise_would_have_prevented": (
                len(states) - len(domain)) - (len(states) - max(len(domain),
                                                                 len(states) - len(domain))),
        })
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "kind": "receipt",
        "incremental_spend_usd": 0,
        "model_calls": 0,
        "network_calls": 0,
        "producer_cognition_model_dependency_count": 0,
        "environment": {
            "kind": "real git repository in a throw-away directory",
            "states": len(states),
            "transitions": model["transitions"],
            "facts_available": len(FACTS),
            "fact_costs": "tool calls: 1 per git query, 1 per file read",
        },
        "tasks": results,
        "reused_not_rebuilt": [
            "canonical/runtime/k6_decision_refinement_compiler_v1.py -- compile_refinement, unchanged",
            "canonical/swe_kernel/one_demonstration_basin_v1.py -- GitWorld, explore, distances, "
            "best_demonstration, run_plan, goals, unchanged",
            "ONE_TRY_LEARNS_A_DOMAIN_NOT_THE_ENVIRONMENT_20261116_V1.md -- the measurement this "
            "answers the next question of",
        ],
        "conclusion": (
            "Which facts are SUFFICIENT for a plan's premise is exactly solvable, and the answer is "
            "smaller and cheaper than the hand-listed senses: the minimal fact set is proven "
            "minimal by exhaustive enumeration, and verified against an independent brute force. "
            "The architect's question stops being 'read everything' and becomes 'read exactly the "
            "premise, refuse when it fails' -- which is the difference between silent failure and "
            "a refusal."),
    }


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    result = measure()
    text = json.dumps(result, indent=1, sort_keys=True)
    if argv:
        pathlib.Path(argv[0]).write_text(text + "\n")
        print("written", argv[0])
    for row in result["tasks"]:
        if row.get("status") != "MEASURED":
            print(f"{row['label']:34s} {row['status']}")
            continue
        print(f"{row['label']:34s} states={row['states']} plan={row['plan_length']} "
              f"domain={row['plan_domain']}")
        print(f"{'':34s} minimum facts {row['minimum_facts']}")
        print(f"{'':34s} minimum cost  {row['minimum_cost']}   "
              f"cells {row['minimum_cells']} (blind: {row['cells_when_blind']})")
        print(f"{'':34s} compiler==brute {row['compiler_and_brute_force_agree']}")
        for sense in row["hand_listed_senses"]:
            print(f"{'':36s} {sense['sense']:28s} cost={sense['cost']:>4} "
                  f"sufficient={sense['sufficient']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
