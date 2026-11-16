#!/usr/bin/env python3
"""How many oracle questions does it take to identify a real program?

Every prior identifiability measurement in this repository used a hand-built space of a few dozen
toy rules (`FINITE_IDENTIFIABILITY_KERNEL_001`, the MiniWoB contrast probe: 13.05 of 32 survivors
after one demonstration, ~2.76 chosen experiences to settle). Those numbers decide nothing about
software engineering until the space is the one real repairs live in.

This tool asks the same question in that space and nowhere else:

    the hypothesis space = every candidate program a merged generator enumerates for a real
    published bug (thousands of programs, each `compile()`-checked, none written by hand)

    one demonstration   = one published input/output example, which is exactly what "show it once"
                          means and nothing more

    an oracle question  = "does the true program agree with this particular input?" -- answered by
                          the corpus's own published expected value, never by the answer key source

    identified          = one candidate program survives every answer

The measurement is *cost in oracle questions*, so it is a property of the space and the questions
chosen, not of a search budget: the discriminator is the tree's own
`canonical/runtime/finite_identifiability.py` (`select_discriminator`, minimum worst case remaining,
then expected remaining, then cost). Two baselines use the same outcome table, so the only variable
is *which* question is asked next:

    EIG        the kernel's minimax split
    CORPUS     the corpus's own published order
    RANDOM     a uniformly random unused question, averaged over shuffles

Third outcome measured per task: whether the thing identified is actually a repair, and whether a
repair was in the space at all. A space with no repair in it can still be identified -- to the wrong
program, confidently. That number is reported rather than hidden, because it is the vocabulary wall
wearing the opposite coat.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import random
import signal
import sys
import time
from typing import Any, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

import grammar_closed_repair_v1 as gen  # noqa: E402
import finite_identifiability as fi  # noqa: E402

MATCH = "MATCH"
NO = "NO"


# --------------------------------------------------------------------------------------------------
# outcomes
# --------------------------------------------------------------------------------------------------
def outcomes_for(source: str, function_name: str, probes: Sequence[Sequence[Any]],
                 expected: Sequence[Any], per_example_timeout: float) -> list[str] | None:
    """For each probe: would this candidate agree with the corpus's published answer?

    Returns None when the candidate cannot be installed at all -- `_enumerate` already `compile()`s
    every candidate, but a rewrite can still produce a function that raises on import.
    """
    namespace: dict[str, Any] = {}
    try:
        exec(compile(source, "<candidate>", "exec"), namespace)  # noqa: S102
        function = namespace.get(function_name)
        if function is None:
            return None
    except Exception:  # noqa: BLE001
        return None
    labels: list[str] = []
    for args, want in zip(probes, expected):
        try:
            signal.setitimer(signal.ITIMER_REAL, per_example_timeout)
            got = function(*copy_args(args))
            signal.setitimer(signal.ITIMER_REAL, 0)
        except gen._Timeout:
            signal.setitimer(signal.ITIMER_REAL, 0)
            labels.append(NO)
            continue
        except Exception:  # noqa: BLE001
            signal.setitimer(signal.ITIMER_REAL, 0)
            labels.append(NO)
            continue
        labels.append(MATCH if gen._equal(got, want) else NO)
    return labels


def copy_args(args: Sequence[Any]) -> list[Any]:
    import copy
    return copy.deepcopy(list(args))


# --------------------------------------------------------------------------------------------------
# protocol
# --------------------------------------------------------------------------------------------------
def settle(live: list[int], table: dict[int, list[str]], order: Sequence[int]) -> dict[str, Any]:
    """Ask questions in `order`, keeping only candidates that answer as the true program does.

    The true program's answer is MATCH by construction (the corpus's expected values are ground
    truth), so one answer eliminates every candidate that predicted NO for that question.
    """
    asked = 0
    for probe in order:
        remaining = [h for h in live if table[h][probe] == MATCH]
        asked += 1
        if not remaining:
            return {"outcome": "CONTRADICTION", "asked": asked, "survivors": []}
        if len(remaining) == 1:
            return {"outcome": "IDENTIFIED", "asked": asked, "survivors": remaining}
        if len(remaining) == len(live):
            continue  # the question separated nothing; legal but uninformative
        live = remaining
    if len(live) == 1:
        return {"outcome": "IDENTIFIED", "asked": asked, "survivors": live}
    return {"outcome": "NONIDENTIFIABLE", "asked": asked, "survivors": live}


def eig_order(live: list[int], table: dict[int, list[str]], probes: Sequence[int]) -> list[int]:
    """Order the questions by the tree's own minimax discriminator, one choice at a time."""
    order: list[int] = []
    remaining = list(live)
    for _ in range(len(probes)):
        hyp = [fi.Hypothesis(str(h)) for h in remaining]
        exps = []
        for probe in probes:
            if probe in order:
                continue
            exps.append(fi.Experiment(str(probe), {str(h): table[h][probe] for h in remaining}))
        if not exps:
            break
        chosen = fi.select_discriminator(hyp, exps, {})
        if chosen.get("status") != "SELECT_EXPERIMENT":
            break
        probe = int(chosen["experiment_id"])
        order.append(probe)
        remaining = [h for h in remaining if table[h][probe] == MATCH]
        if len(remaining) <= 1:
            break
    return order


def elimination_order(live: list[int], table: dict[int, list[str]],
                      probes: Sequence[int]) -> list[int]:
    """The objective that is actually correct here, and why the kernel's is not.

    `select_discriminator` minimises the *worst case* part of a split, which is right when the
    answer to a question is unknown. Here the answer is never unknown: the question is "does the
    true program agree with this input?", and the true program agrees by definition. So every
    candidate that predicts NO is eliminated with certainty, and the best next question is simply
    the one that eliminates the most -- argmax |{h : h predicts NO}|. A balanced split is the right
    rule for a question whose answer you do not know, and a strictly worse rule for this one.
    """
    order: list[int] = []
    remaining = list(live)
    for _ in range(len(probes)):
        best_probe, best_gain = None, 0
        for probe in probes:
            if probe in order:
                continue
            gain = sum(1 for h in remaining if table[h][probe] == NO)
            if gain > best_gain:
                best_probe, best_gain = probe, gain
        if best_probe is None:
            break
        order.append(best_probe)
        remaining = [h for h in remaining if table[h][best_probe] == MATCH]
        if len(remaining) <= 1:
            break
    return order


def settle_to_repairs(live: list[int], table: dict[int, list[str]],
                      order: Sequence[int], repairs: Sequence[int]) -> dict[str, Any]:
    """The stopping rule that the repair question actually asks for.

    Unique identification is the wrong target. What a repair needs is that *every* surviving
    candidate is a repair -- four behaviourally identical correct programs are not a failure, they
    are four correct answers. So the question is not "how many queries to isolate one program" but
    "how many queries until no wrong program is still alive".
    """
    repair_set = set(repairs)
    asked = 0
    current = list(live)
    for probe in order:
        asked += 1
        current = [h for h in current if table[h][probe] == MATCH]
        if not current:
            return {"outcome": "CONTRADICTION", "asked": asked, "survivors": []}
        if set(current) <= repair_set:
            return {"outcome": "SUFFICIENT", "asked": asked, "survivors": current}
    if set(current) <= repair_set:
        return {"outcome": "SUFFICIENT", "asked": asked, "survivors": current}
    return {"outcome": "INSUFFICIENT", "asked": asked, "survivors": current}


def measure_task(root: pathlib.Path, name: str, *, per_example_timeout: float,
                 budget_s: float, shuffles: int, seed: int) -> dict[str, Any]:
    started = time.time()
    row: dict[str, Any] = {"task": name, "kind": "task"}
    examples = gen.examples_of(root, name)
    row["examples"] = len(examples)
    if len(examples) < 2:
        row["stage"] = "TOO_FEW_EXAMPLES"
        return row
    source = (root / "python_programs" / f"{name}.py").read_text()
    tree = ast.parse(source)
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
    if function is None:
        row["stage"] = "NO_FUNCTION"
        return row
    row["function"] = function.name
    if not gen._install_alarm():
        row["stage"] = "UNMEASURABLE__NO_TIMER"
        return row

    candidates = gen._enumerate(tree, gen.atoms_of(function))
    seen: set[str] = set()
    sources: list[str] = []
    for candidate in candidates:
        text = candidate["source"]
        if text in seen:
            continue
        seen.add(text)
        sources.append(text)
    row["space_size"] = len(sources)
    row["enumerated_raw"] = len(candidates)
    if not sources:
        row["stage"] = "EMPTY_SPACE"
        return row

    probes = [args for args, _ in examples]
    expected = [want for _, want in examples]

    # Phase 1 -- one demonstration, which is the first published example and nothing else.
    # Every candidate is asked only this one question, because that is all "show it once" buys.
    table: dict[int, list[str]] = {}
    live_after_one: list[int] = []
    for index, text in enumerate(sources):
        labels = outcomes_for(text, function.name, probes[:1], expected[:1], per_example_timeout)
        if labels is None:
            table[index] = [NO] * len(probes)
            continue
        table[index] = labels + [NO] * (len(probes) - 1)
        if labels[0] == MATCH:
            live_after_one.append(index)
        if time.time() - started > budget_s:
            row["stage"] = "BUDGET_EXHAUSTED_WHILE_PREDICTING"
            row["predicted"] = len(table)
            return row

    # Phase 2 -- only the survivors need predicting on the remaining questions.
    for index in live_after_one:
        labels = outcomes_for(sources[index], function.name, probes, expected, per_example_timeout)
        if labels is None:
            table[index] = [NO] * len(probes)
            continue
        table[index] = labels
        if time.time() - started > budget_s:
            row["stage"] = "BUDGET_EXHAUSTED_WHILE_PREDICTING_SURVIVORS"
            row["predicted"] = len(table)
            row["survivors_after_one_demonstration"] = len(live_after_one)
            return row
    row["predictable"] = sum(1 for v in table.values() if any(x == MATCH for x in v) or v)
    row["survivors_after_one_demonstration"] = len(live_after_one)
    row["bits_before"] = round(_log2(len(table)), 3)
    row["bits_after_one"] = round(_log2(len(live_after_one)), 3)

    # a space with no repair in it can still be identified -- to the wrong program
    repair_ids = [h for h in table if all(l == MATCH for l in table[h])]
    row["repairs_in_space"] = len(repair_ids)

    if not live_after_one:
        row["stage"] = "DEMONSTRATION_EXCLUDED_EVERYTHING"
        return row
    if len(live_after_one) == 1:
        row["stage"] = "IDENTIFIED_AFTER_ONE"
        row["elim_asked"] = 0
        row["minimax_asked"] = 0
        row["corpus_asked"] = 0
        row["random_asked_mean"] = 0.0
        row["random_asked_min"] = 0
        row["random_asked_max"] = 0
        row["survivor_is_repair"] = live_after_one[0] in repair_ids
        row["sufficient_outcome"] = "SUFFICIENT" if row["survivor_is_repair"] else "INSUFFICIENT"
        row["sufficient_asked"] = 0
        row["survivors_after_all_examples"] = 1
        row["all_survivors_are_repairs"] = row["survivor_is_repair"]
        row["seconds"] = round(time.time() - started, 1)
        return row

    remaining_probes = list(range(1, len(probes)))
    minimax_order = eig_order(live_after_one, table, remaining_probes)
    minimax = settle(live_after_one, table,
                     minimax_order + [p for p in remaining_probes if p not in minimax_order])
    elim_order = elimination_order(live_after_one, table, remaining_probes)
    elim = settle(live_after_one, table, elim_order + [p for p in remaining_probes if p not in elim_order])
    corpus = settle(live_after_one, table, remaining_probes)

    rng = random.Random(seed)
    random_asked = []
    for _ in range(shuffles):
        shuffled = remaining_probes[:]
        rng.shuffle(shuffled)
        random_asked.append(settle(live_after_one, table, shuffled)["asked"])

    row["stage"] = elim["outcome"]
    row["elim_asked"] = elim["asked"]
    row["minimax_asked"] = minimax["asked"]
    row["corpus_asked"] = corpus["asked"]
    row["corpus_outcome"] = corpus["outcome"]
    row["random_asked_mean"] = round(sum(random_asked) / len(random_asked), 2)
    row["random_asked_min"] = min(random_asked)
    row["random_asked_max"] = max(random_asked)
    sufficient = settle_to_repairs(
        live_after_one, table,
        elim_order + [p for p in remaining_probes if p not in elim_order], repair_ids)
    row["sufficient_outcome"] = sufficient["outcome"]
    row["sufficient_asked"] = sufficient["asked"]
    row["survivors_after_all_examples"] = len(sufficient["survivors"])
    row["all_survivors_are_repairs"] = sufficient["outcome"] == "SUFFICIENT"
    row["survivors_after_elim"] = len(elim["survivors"])
    if elim["survivors"]:
        survivor = elim["survivors"][0]
        row["survivor_is_repair"] = survivor in repair_ids
    row["seconds"] = round(time.time() - started, 1)
    return row


def _log2(n: int) -> float:
    import math
    return math.log2(n) if n > 0 else 0.0


# --------------------------------------------------------------------------------------------------
# receipt
# --------------------------------------------------------------------------------------------------
def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    measured = [r for r in rows if "elim_asked" in r]
    identified = [r for r in measured if r.get("stage") == "IDENTIFIED"]
    return {
        "schema": "BRAIN_IDENTIFICATION_COST_IN_A_REAL_SPACE_V1",
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "network_calls_at_run_time": 0,
        "tasks_measured": len(measured),
        "tasks_identified": len(identified),
        "stages": _tally(r.get("stage") for r in rows),
        "elim_asked_total": sum(r["elim_asked"] for r in identified),
        "minimax_asked_total": sum(r["minimax_asked"] for r in identified),
        "corpus_asked_total": sum(r.get("corpus_asked", 0) for r in measured),
        "random_asked_total": round(sum(r.get("random_asked_mean", 0) for r in measured), 2),
        "bits_after_one_demonstration": {
            "median": _median([r["bits_after_one"] for r in measured]),
            "max": max((r["bits_after_one"] for r in measured), default=0),
        },
        "survivors_after_one_demonstration": {
            "median": _median([r["survivors_after_one_demonstration"] for r in measured]),
            "max": max((r["survivors_after_one_demonstration"] for r in measured), default=0),
        },
        "sufficient_to_only_repairs": sum(1 for r in measured if r.get("all_survivors_are_repairs")),
        "sufficient_asked_total": sum(r.get("sufficient_asked", 0) for r in measured
                                      if r.get("all_survivors_are_repairs")),
        "insufficient_after_all_examples": sum(1 for r in measured
                                               if not r.get("all_survivors_are_repairs")),
        "identified_as_repair": sum(1 for r in identified if r.get("survivor_is_repair")),
        "identified_as_anything_else": sum(1 for r in identified if not r.get("survivor_is_repair")),
        "tasks_with_a_repair_in_space": sum(1 for r in measured if r.get("repairs_in_space")),
        "rows": list(rows),
    }


def _tally(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        key = str(value)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return round((ordered[mid - 1] + ordered[mid]) / 2, 2)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", default=None)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--consolidate", default=None)
    parser.add_argument("--per-example-timeout", type=float, default=0.05)
    parser.add_argument("--budget-s", type=float, default=120.0)
    parser.add_argument("--shuffles", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20261116)
    args = parser.parse_args(argv)

    if args.consolidate:
        rows = [json.loads(line) for line in pathlib.Path(args.consolidate).read_text().splitlines()
                if line.strip()]
        receipt = summarise([r for r in rows if r.get("kind") == "task"])
        text = json.dumps(receipt, indent=1, sort_keys=False)
        pathlib.Path(args.receipt or args.out).write_text(text + "\n")
        print(text[:1400])
        return 0

    root = pathlib.Path(args.quixbugs or "")
    if not root.is_dir():
        print("--quixbugs is required", file=sys.stderr)
        return 2
    names = args.tasks or sorted(p.stem for p in (root / "python_programs").glob("*.py"))
    out = pathlib.Path(args.out)
    rows: list[dict[str, Any]] = []
    with out.open("w") as handle:
        for name in names:
            try:
                row = measure_task(root, name, per_example_timeout=args.per_example_timeout,
                                   budget_s=args.budget_s, shuffles=args.shuffles,
                                   seed=args.seed)
            except Exception as error:  # noqa: BLE001
                row = {"task": name, "kind": "task", "stage": f"INSTRUMENT_ERROR:{type(error).__name__}"}
            rows.append(row)
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(f"{name:<26} {row.get('stage',''):<28} "
                  f"|H|={row.get('space_size','?'):<6} one={row.get('survivors_after_one_demonstration','?'):<6} "
                  f"elim={row.get('elim_asked','?'):<3} minimax={row.get('minimax_asked','?'):<3} "
                  f"corpus={row.get('corpus_asked','?'):<3} "
                  f"rand={row.get('random_asked_mean','?'):<6} {row.get('seconds','?')}s")
    receipt = summarise([r for r in rows if r.get("kind") == "task"])
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
