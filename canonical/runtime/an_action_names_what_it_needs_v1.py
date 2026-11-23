"""AN ACTION NAMES WHAT IT NEEDS. The dependency graph is in the arguments, not in knowledge.

THE CEILING THIS REMOVES, MEASURED.

`environment_learning_v1` learns an environment by walking it at random and recording what each action does.
That is correct and it does not scale, for a reason that has nothing to do with cleverness:

    a task needing FIVE ordered steps, first run 2026-11-23
        budget  60   FAIL_CLOSED__GOAL_NEVER_OBSERVED
        budget 150   FAIL_CLOSED__GOAL_NEVER_OBSERVED
        budget 400   FAIL_CLOSED__GOAL_NEVER_OBSERVED

Random walking finds a five-step chain only by chance, and the chance falls exponentially with depth. OSWorld 2.0
averages **318 steps per task**. Blind search cannot reach it. More budget is not a plan.

THE FACT THAT CHANGES IT. Every real action states its own precondition in its own arguments:

    ('cp', 'a.txt', 's1')   needs `a.txt` to exist, and produces `s1`
    ('cp', 's1',    's2')   needs `s1`   to exist -- which the previous action produces

At the start of a five-step chain, EXACTLY ONE action is possible. The dependency graph was written down in the
command line. Nothing has to learn it, and nothing has to know that `cp` copies.

WHAT THIS IS NOT.

    - It is not a rule that "cp needs its source to exist". That WOULD be knowledge of `cp`, and it would be
      wrong for `rm` (whose argument must exist) and for `touch` (whose argument must NOT).
    - It is this: an action's operands that are not marked as options, and are not its output, must already be
      present. That holds for every program because it is what an argument IS -- a name the program is asked to
      do something with. A program that violates it is one that invents paths, and it is treated as a weaker
      signal rather than a crash.

So this module offers a PREFERENCE and the learner keeps wandering. A wrong preference costs attempts; it can
never make the learner unable to act, because every action remains available at every state.

AUTHORITY NONE. No model, no parameters, no knowledge of any program, $0.
"""
from __future__ import annotations

import pathlib
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_AN_ACTION_NAMES_WHAT_IT_NEEDS_V1"


def _parts(action: Any) -> list[tuple[str, str]]:
    """The action as (kind, text): 'flag' for an option, 'word' for an operand. Order preserved.

    A flag ATTACHES TO THE OPERAND AFTER IT. That is why `tar -cf x.tar dir` creates `x.tar` from `dir` --
    `x.tar` follows the flag `-f`. Reading the LAST operand as the output got that backwards, and reading
    "everything but the last" as what it needs then demanded the archive exist before creating it. Measured
    2026-11-23 on exactly that command.
    """
    parts: list[tuple[str, str]] = []
    if not isinstance(action, (tuple, list)):
        return parts
    for piece in action[1:]:
        if not isinstance(piece, str) or not piece:
            continue
        parts.append(("flag" if piece.startswith("-") else "word", piece))
    return parts


def needs_and_produces(action: Any) -> dict[str, Any]:
    """What an action reads and what it writes, as far as its own arguments say.

    THE RULE IS POSITIONAL, AND IT IS THE ONLY ONE THAT FITS EVERY SHAPE MEASURED SO FAR:

        cp a b            operand after a flag?  no  -> last word is the output, the rest are read
        tar -cf x.tar dir output follows the flag -> x.tar is made, dir is read
        gzip -k log       one word, no flag      -> log is read, and the world decides what appears
        mkdir -p scratch  one word after a flag  -> scratch is made, nothing is read

    `produces` is None when no operand is marked as an output -- because the arguments do not say, and a guess
    about what a program writes is a precondition invented rather than read. `gzip` is that case and it is
    recorded as such rather than patched with knowledge of `gzip`.
    """
    parts = _parts(action)
    words = [(index, text) for index, (kind, text) in enumerate(parts) if kind == "word"]
    if not words:
        return {"needs": [], "produces": None, "operands": 0, "shape": "NO_OPERANDS", "parts": parts}

    # the operand immediately following a flag is an OUTPUT when another word follows it
    marked = None
    for index, (kind, _text) in enumerate(parts):
        if kind != "flag" or index + 1 >= len(parts) or parts[index + 1][0] != "word":
            continue
        after_flag = parts[index + 1][1]
        later_words = [t for k, t in parts[index + 2:] if k == "word"]
        earlier_words = [t for k, t in parts[:index] if k == "word"]
        if len(words) >= 2:
            marked = after_flag
            break
        if earlier_words and not later_words:
            # `gzip -k log`: the flag follows nothing and marks nothing; the operand is read, not written
            break
        # ONE WORD, AFTER A FLAG, AND NOTHING ELSE. Two real shapes look like this and they are opposite:
        #   `mkdir -p scratch`   scratch is MADE
        #   `rm -f notes.txt`    notes.txt is REMOVED -- so it must already exist
        # The arguments cannot tell them apart, so this returns NO produces and keeps the word as a need.
        # Choosing "made" for both would have `rm` demand a file that must not exist. Measured 2026-11-23.
        return {"needs": [after_flag], "produces": None, "operands": 1,
                "shape": "ONE_WORD_AFTER_FLAG_UNDECIDABLE", "parts": parts}

    if marked is None:
        if len(words) == 1:
            return {"needs": [words[0][1]], "produces": None, "operands": 1,
                    "shape": "ONE_OPERAND_NO_OUTPUT", "parts": parts}
        return {"needs": [t for _i, t in words[:-1]], "produces": words[-1][1],
                "operands": len(words), "shape": "LAST_IS_OUTPUT", "parts": parts}

    needs = [t for _i, t in words if t != marked]
    return {"needs": needs, "produces": marked, "operands": len(words),
            "shape": "FLAGGED_OUTPUT", "parts": parts}


def _present(name: str, state: Iterable[str]) -> bool:
    """Is this name in the state? Compared by basename, because a state may hold paths and an action may not."""
    have = {str(s) for s in state}
    if name in have:
        return True
    base = pathlib.PurePath(name).name
    return base in {pathlib.PurePath(h).name for h in have} or base in have


def possible_actions(actions: Sequence[Any], state: Iterable[str]) -> list[Any]:
    """The actions whose named inputs are already present -- the frontier of what can be done now."""
    state = list(state)
    return [a for a in actions if all(_present(n, state) for n in needs_and_produces(a)["needs"])]


def distance_to_goal(actions: Sequence[Any], state: Iterable[str], goal_name: str) -> int:
    """How many actions still separate this state from producing `goal_name`, read off the arguments alone.

    Zero when the goal is already present. `inf` when no chain of these actions produces it -- which is a real
    answer (this action set cannot reach this goal) and not a failure to compute.
    """
    state = list(state)
    if _present(goal_name, state):
        return 0
    # what produces the goal, what produces that, and so on -- a backward walk through the arguments
    frontier, seen, depth = {goal_name}, {goal_name}, 0
    while frontier:
        depth += 1
        producers = [a for a in actions if needs_and_produces(a)["produces"] in frontier]
        if not producers:
            return float("inf")
        new: set[str] = set()
        for action in producers:
            for need in needs_and_produces(action)["needs"]:
                if _present(need, state):
                    # a producer can fire as soon as its inputs are here, including these
                    return depth
                if need not in seen:
                    new.add(need)
        seen |= new
        frontier = new
        if depth > len(actions) + 1:
            return float("inf")
    return float("inf")


def heuristic(actions: Sequence[Any], goal_name: str):
    """A `state -> score` function for `environment_learning_v1.learn_model(heuristic=...)`.

    Lower is closer. It is the number of actions still needed, which is exactly the estimate a search that knows
    the dependency graph would use, and it is read from the actions rather than assumed about them.
    """
    def score(state: Iterable[str]) -> float:
        return float(distance_to_goal(actions, state, goal_name))
    return score


def plan_from_arguments(actions: Sequence[Any], state: Iterable[str], goal_name: str) -> list[Any] | None:
    """The ordered actions that produce `goal_name`, read off their own arguments. No search, no learning.

    WHY THIS REPLACES RANDOM SEARCH FOR THIS CASE, MEASURED. A twenty-step dependent chain, first run
    2026-11-23, random walk WITH the distance heuristic:

        budget 80, max_depth 22    FAIL_CLOSED__GOAL_NEVER_OBSERVED     23.8s

    The cause is arithmetic, not tuning. At the start of that chain exactly ONE of twenty actions is possible;
    the other nineteen do nothing when tried. Every random pick is therefore almost surely a wasted step, and
    the walk almost never survives twenty consecutive steps without one.

    But the plan is not hidden. `('cp','s19','s20')` names `s19` as what it needs and `s20` as what it makes, so
    the chain s1 -> s2 -> ... -> s20 is written down in the arguments. Reading it is O(n), and executing it is n
    steps. Searching for it is exponential in n and fails at n=20.

    THE PLAN IS STILL A HYPOTHESIS. It is returned unverified, and `execute_plan` checks the goal afterwards. A
    dependency chain that the arguments describe and the world does not honour is caught by execution, not
    assumed by construction.
    """
    state = list(state)
    if _present(goal_name, state):
        return []
    have = [str(s) for s in state]
    produced: set[str] = set()
    order: list[Any] = []
    remaining = list(actions)
    # grow the chain forward from what is present, taking only actions whose inputs are all satisfied
    changed = True
    while changed and not _present(goal_name, [str(x) for x in have] + list(produced)):
        changed = False
        for action in list(remaining):
            spec = needs_and_produces(action)
            if spec["produces"] is None:
                continue
            if not all(_present(n, [str(x) for x in have] + list(produced)) for n in spec["needs"]):
                continue
            order.append(action)
            produced.add(str(spec["produces"]))
            remaining.remove(action)
            changed = True
            break
    if not _present(goal_name, [str(x) for x in have] + list(produced)):
        return None
    return order


def execute_plan(env: Any, plan: Sequence[Any], is_goal, *, reset: bool = True,
                 max_steps: int | None = None) -> dict[str, Any]:
    """Run the plan and check the goal. A plan that was never run is a hypothesis, not an answer."""
    if reset:
        env.reset()
    taken: list[Any] = []
    for action in plan:
        if max_steps is not None and len(taken) >= max_steps:
            break
        env.act(action)
        taken.append(action)
    reached = bool(is_goal(env.state()))
    return {"schema": SCHEMA, "pass": reached, "executed": taken, "steps": len(taken),
            "status": "PASS__PLAN_FROM_ARGUMENTS_EXECUTED_GOAL_OBSERVED" if reached
                      else "FAIL_CLOSED__PLAN_EXECUTED_GOAL_NOT_OBSERVED",
            "authority": "GOAL_OBSERVED_AFTER_EXECUTION" if reached else "GOAL_NOT_OBSERVED"}
