#!/usr/bin/env python3
"""Which demonstration you hand over matters more than how many you hand over.

THE OWNER'S QUESTION, IN ITS SHARPEST FORM
------------------------------------------
"Give the model the smartest actions, let it experience them once, and it has them permanently."
The tree has already measured the *count* half of that answer many times (one showing is literal,
two showings are general). This tool measures a different half, and it is the half the word
"smartest" actually points at:

    the SAME change, demonstrated on task T, recovers between 0% and 100% of what the people
    on T actually did to the other files, depending only on WHICH file of T was demonstrated.

That spread is already in the recorded run
(``canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json``) but nobody has asked
whether it can be *predicted before the demonstration is chosen*. If it can, then choosing the
demonstration is a capability that costs nothing and buys what a second demonstration buys. If it
cannot, then "give it the smartest action" is a phrase with no mechanism behind it and the count
is all there is.

WHY THIS IS THE RIGHT EXPERIMENT AND NOT ANOTHER RESTATEMENT
------------------------------------------------------------
The chooser has to work without running the organ on the task, because in the real setting the
task's other files have not been changed yet -- there is nothing to compare against. So the only
information available at choice time is the set of candidate demonstrations themselves. This tool
therefore measures two predictors that use nothing but the candidates:

  A. **reach, by the organ's own rules** (``REACH``). For each candidate demonstration, learn its
     rules and count how many *other candidate files* those rules would fit. A demonstration whose
     lesson fits many of its siblings is a lesson about this task; one whose lesson fits only
     itself is a lesson about itself. No outcome is consulted.
  B. **agreement with the siblings** (nothing). Not measured: a file has no "after" until someone
     changes it, so there is no second opinion to take. A says what can be said.

The measurement is the correlation between A and what actually happened, and then, the only number
that matters: how much of the best-possible recovery does choosing by A get, compared with
choosing at random and choosing the worst.

PRE-REGISTERED PREDICTION (written before the run, kept whatever it says)
-------------------------------------------------------------------------
  * reach and recovered share are positively correlated, r >= 0.30, over all (task, candidate)
    pairs;
  * choosing the demonstration with the greatest reach recovers at least 80% of what choosing the
    best possible demonstration would have recovered, on the tasks where candidates differ.

Either can fail. A failure is reported as a failure and nothing here is patched afterwards.

WHAT IS AND IS NOT CLAIMED
--------------------------
No capability is registered, no tolerance is widened, ``truth.achieved`` stays false, $0 is spent
and no model is called. The corpus is other people's merged pull requests, fetched through ``gh``
and verified against the hashes recorded with the earlier run. The organ is not modified. The
result says nothing about tasks where a project made only one kind of change in one file.

    python3 canonical/tools/demonstration_choice_measure_v1.py --pulls /tmp/pulls_v2.json \
        --out canonical/verification/DEMONSTRATION_CHOICE_20261112_V1.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import signal
import statistics as st
import sys
import time
import warnings
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_DEMONSTRATION_CHOICE_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ORGAN = "canonical/swe_kernel/taught_actions/edit_by_example_v1.py"

CALL_LIMIT_S = 30
MIN_PAIRS_FOR_CORRELATION = 30


class TookTooLong(Exception):
    pass


def _alarm(signum, frame):
    raise TookTooLong()


def _bounded(ask: Callable[[], Any]) -> Any:
    previous = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(CALL_LIMIT_S)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return ask()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def organ_module():
    from canonical.swe_kernel.taught_actions import edit_by_example_v1
    return edit_by_example_v1


# --------------------------------------------------------------------------- #
# A. reach: how many sibling files a demonstration's own lesson fits
# --------------------------------------------------------------------------- #
def lesson_rules(example: Mapping[str, str]) -> list[Any]:
    """The rules a candidate demonstration gives, or [] when the organ refuses to learn it."""
    organ = organ_module()
    try:
        return _bounded(lambda: organ.learn(example["before"], example["after"]))
    except Exception:
        return []


def fits_anywhere(rules: Sequence[Any], text: str) -> bool:
    """Would these rules find anything to change in this text?  The organ's own matcher, no edits."""
    if not rules:
        return False
    organ = organ_module()
    try:
        _text, count = _bounded(lambda: organ.rewrite(list(rules), text, "a sibling", leave_unshown=True))
        return count > 0
    except Exception:
        return False


def reach_of(index: int, files: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """How many of the OTHER candidate files this candidate's lesson fits, and how specific it is."""
    rules = lesson_rules(files[index])
    others = [other for other in range(len(files)) if other != index]
    fitted = [other for other in others if fits_anywhere(rules, files[other]["before"])]
    blanks = sum(len(organ_module().blanks_in(rule.pattern)) for rule in rules)
    return {
        "rules": [str(rule) for rule in rules],
        "learned": bool(rules),
        "reach": len(fitted),
        "reach_share": (len(fitted) / len(others)) if others else 0.0,
        "fits_itself": fits_anywhere(rules, files[index]["before"]) if rules else False,
        "blanks": blanks,
        "siblings": len(others),
    }


# --------------------------------------------------------------------------- #
# what actually happened, using the recorded instrument rather than a new one
# --------------------------------------------------------------------------- #
ARMS = {
    # The two ways of repeating the recorded run measured. The strict arm changes the whole file or
    # nothing; the ceiling arm keeps every place the lesson or its wider reading fits, as if a
    # sufficient check had settled each try in its favour. Both are the recorded tool's own entry
    # points, so this tool cannot drift from that instrument.
    "strict": "the_organ",
    "every_try_kept": "the_organ_with_every_try_kept",
}


def recovered(files: Sequence[Mapping[str, str]], example_at: int, arm: str = "every_try_kept") -> dict[str, Any]:
    """The recorded measure's own scoring: what share of the developers' other changes came back."""
    from canonical.tools import repeated_change_one_example_measure_v1 as measure

    organ = getattr(measure, ARMS[arm])
    example = files[example_at]
    right = asked = target_changes = not_theirs = organ_changes = 0
    for other, target in enumerate(files):
        if other == example_at:
            continue
        got, _why = organ(target["before"], example["before"], example["after"])
        one = measure.score(target["before"], target["after"], got)
        asked += 1
        right += one["right_not_imports"]
        target_changes += one["developers_changes_not_imports"]
        not_theirs += one["not_what_the_developers_did"]
        organ_changes += one["organ_changes"]
    return {
        "asked": asked,
        "right_not_imports": right,
        "developers_changes_not_imports": target_changes,
        "not_what_the_developers_did": not_theirs,
        "organ_changes": organ_changes,
        "share_recovered": (right / target_changes) if target_changes else 0.0,
    }


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #
def one_task(name: str, files: Sequence[Mapping[str, str]], *, measure_outcome: bool = True,
             arm: str = "every_try_kept") -> dict[str, Any]:
    candidates = []
    for index, example in enumerate(files):
        row = {"path": example["path"], "bytes": len(example["before"].encode("utf-8")),
               **reach_of(index, files)}
        if measure_outcome:
            row["outcome"] = recovered(files, index, arm)
            row["share_recovered"] = row["outcome"]["share_recovered"]
        candidates.append(row)

    out: dict[str, Any] = {"name": name, "files": len(files), "candidates": candidates}
    if measure_outcome:
        # A baseline the rule has to beat: the biggest candidate file, which needs no reasoning at all.
        by_size = sorted(range(len(candidates)),
                         key=lambda i: (-candidates[i]["bytes"], candidates[i]["path"]))[0]
        out["chosen_by_size"] = candidates[by_size]["path"]
    if not measure_outcome:
        return out

    shares = [row["share_recovered"] for row in candidates]
    reaches = [row["reach"] for row in candidates]
    best = max(shares)
    worst = min(shares)
    # The rule: among the candidates, prefer the greatest reach; ties by fewer blanks (more specific
    # lesson), then by the file's own path so the choice is deterministic and not cherry-picked.
    order = sorted(range(len(candidates)),
                   key=lambda i: (-reaches[i], candidates[i]["blanks"], candidates[i]["path"]))
    picked = order[0]
    out.update({
        "best_possible_recovered": best,
        "worst_possible_recovered": worst,
        "mean_recovered": st.mean(shares) if shares else 0.0,
        "spread": best - worst,
        "chosen_by_reach": candidates[picked]["path"],
        "chosen_reach": reaches[picked],
        "chosen_recovered": shares[picked],
        "chosen_is_best": abs(shares[picked] - best) < 1e-12,
        "chosen_is_worst": abs(shares[picked] - worst) < 1e-12,
        "share_of_best_captured": (shares[picked] / best) if best else None,
        "candidates_differ": (best - worst) > 1e-12,
        "size_choice_recovered": shares[by_size],
        "share_of_best_captured_by_size": (shares[by_size] / best) if best else None,
    })
    return out


# --------------------------------------------------------------------------- #
# the summary, and the pre-registered tests
# --------------------------------------------------------------------------- #
def pearson(xs: Sequence[float], ys: Sequence[float]) -> dict[str, Any]:
    n = len(xs)
    if n < 3:
        return {"r": None, "n": n, "reason": "TOO_FEW_PAIRS"}
    mx, my = st.mean(xs), st.mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return {"r": None, "n": n, "reason": "NO_VARIATION_IN_ONE_AXIS"}
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)
    return {"r": round(r, 4), "n": n, "reason": None}


def summarise(tasks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    pairs = [(row["reach"], row["share_recovered"])
             for task in tasks for row in task["candidates"]]
    xs = [float(a) for a, _ in pairs]
    ys = [float(b) for _, b in pairs]
    correlation = pearson(xs, ys)

    differ = [task for task in tasks if task["candidates_differ"]]
    captured = [task["share_of_best_captured"] for task in differ
                if task["share_of_best_captured"] is not None]

    def total(candidates: Sequence[Mapping[str, Any]], field: str) -> float:
        return sum(row["outcome"][field] for row in candidates)

    all_candidates = [row for task in tasks for row in task["candidates"]]
    total_target = total(all_candidates, "developers_changes_not_imports")
    mean_total = st.mean([row["share_recovered"] for row in all_candidates]) if all_candidates else 0.0

    chosen_right = sum(task["candidates"][
        next(i for i, row in enumerate(task["candidates"]) if row["path"] == task["chosen_by_reach"])
    ]["outcome"]["right_not_imports"] for task in tasks)
    best_right = sum(max(row["outcome"]["right_not_imports"] for row in task["candidates"]) for task in tasks)
    worst_right = sum(min(row["outcome"]["right_not_imports"] for row in task["candidates"]) for task in tasks)

    prediction = {
        "reach_and_recovered_are_positively_correlated_r_ge_0_30":
            bool(correlation["r"] is not None and correlation["r"] >= 0.30),
        "choosing_by_reach_captures_ge_80_percent_of_best_on_tasks_where_candidates_differ":
            bool(captured and st.mean(captured) >= 0.80),
    }
    return {
        "tasks": len(tasks),
        "tasks_where_candidates_differ": len(differ),
        "candidate_pairs": len(pairs),
        "correlation_reach_to_recovered": correlation,
        "mean_share_recovered_choosing_at_random": round(mean_total, 4),
        "changes_recovered_choosing_by_reach": chosen_right,
        "changes_recovered_choosing_the_best": best_right,
        "changes_recovered_choosing_the_worst": worst_right,
        "changes_the_developers_made": total_target,
        "changes_recovered_choosing_the_largest_file": sum(
            task["candidates"][next(i for i, row in enumerate(task["candidates"])
                                    if row["path"] == task["chosen_by_size"])]["outcome"]["right_not_imports"]
            for task in tasks),
        "share_of_best_captured_by_size_mean": (
            round(st.mean([task["share_of_best_captured_by_size"] for task in differ
                           if task["share_of_best_captured_by_size"] is not None]), 4) if differ else None),
        "share_of_best_captured_mean": round(st.mean(captured), 4) if captured else None,
        "share_of_best_captured_median": round(st.median(captured), 4) if captured else None,
        # Only tasks where the candidates actually differ can say anything about a choice: where
        # every candidate recovers the same, the choice is trivially both the best and the worst.
        "tasks_where_the_choice_was_the_best_possible": sum(
            1 for task in tasks if task["candidates_differ"] and task["chosen_is_best"]),
        "tasks_where_the_choice_was_the_worst_possible": sum(
            1 for task in tasks if task["candidates_differ"] and task["chosen_is_worst"]),
        "honest_capture": honest_capture(tasks),
        "pre_registered_prediction": prediction,
        "prediction_held": all(prediction.values()),
    }


def honest_capture(tasks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """What the rule earns WITHOUT the arbitrary tie-break, and where its decisions are real.

    The choice rule has two parts and only one of them is a decision. `reach` separates candidates
    into groups, and it is data: it is computed before any outcome is read. The tie-break inside a
    group (fewest blanks, then the file's path) is NOT data -- the path is whatever `gh` happened to
    call the file. Counting a tie broken by path as a success would credit the rule with a choice it
    did not make.

    So this reads the outcome twice. Where the greatest reach belongs to exactly ONE candidate the
    rule has genuinely decided, and that is the only place a capture rate is evidence. Where several
    candidates share the greatest reach, the honest expectation is that one of them at random will be
    taken -- and its mean capture is reported as what the rule is worth there, not the best of them.
    """
    decided, tied = [], []
    for task in tasks:
        if not task["candidates_differ"]:
            continue
        best = max(row["share_recovered"] for row in task["candidates"])
        if not best:
            continue
        top = max(row["reach"] for row in task["candidates"])
        at_top = [row["share_recovered"] for row in task["candidates"] if row["reach"] == top]
        (decided if len(at_top) == 1 else tied).append({
            "name": task["name"],
            "capture_expected": st.mean(at_top) / best,
            "capture_best_in_group": max(at_top) / best,
            "group": len(at_top),
        })
    every = decided + tied
    return {
        "tasks_where_the_rule_actually_decided": len(decided),
        "tasks_where_the_top_reach_was_tied": len(tied),
        "capture_where_the_rule_decided_mean": (
            round(st.mean([row["capture_expected"] for row in decided]), 4) if decided else None),
        "capture_where_the_top_reach_was_tied_mean": (
            round(st.mean([row["capture_expected"] for row in tied]), 4) if tied else None),
        "honest_capture_all_differing_tasks_mean": (
            round(st.mean([row["capture_expected"] for row in every]), 4) if every else None),
        "honest_capture_all_differing_tasks_median": (
            round(st.median([row["capture_expected"] for row in every]), 4) if every else None),
        "per_task": every,
    }


def _fmt(value: Any) -> str:
    return "n/a" if value is None else "%.2f" % value


def code_sha256() -> dict[str, str]:
    out = {}
    for relative in (ORGAN, "canonical/tools/repeated_change_one_example_measure_v1.py",
                     "canonical/tools/demonstration_choice_measure_v1.py"):
        path = ROOT / relative
        out[relative] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "ABSENT"
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pulls", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, default=None)
    parser.add_argument("--reach-only", action="store_true",
                        help="only the candidates' reach; runs the organ on no file it was not shown")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--arm", choices=sorted(ARMS), default="every_try_kept",
                        help="which of the recorded tool's ways of repeating to measure")
    args = parser.parse_args(argv)

    pulls = json.loads(args.pulls.read_text(encoding="utf-8"))
    if args.limit:
        pulls = pulls[: args.limit]

    started = time.time()
    tasks = []
    for pull in pulls:
        row = one_task(pull["name"], pull["files"], measure_outcome=not args.reach_only, arm=args.arm)
        tasks.append(row)
        if not args.reach_only:
            print(f"{pull['name']:42s} reach={[c['reach'] for c in row['candidates']]} "
                  f"recovered={[round(c['share_recovered'], 2) for c in row['candidates']]} "
                  f"chosen->{_fmt(row['share_of_best_captured'])} of best", flush=True)

    record: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "organ": ORGAN,
        "pulls_sha256": hashlib.sha256(args.pulls.read_bytes()).hexdigest(),
        "code_sha256": code_sha256(),
        "reach_only": bool(args.reach_only),
        "arm": args.arm,
        "parameters": {"call_limit_s": CALL_LIMIT_S,
                       "choice_rule": "greatest reach, then fewest blanks, then path"},
        "tasks": tasks,
        "seconds": round(time.time() - started, 1),
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
    }
    if not args.reach_only:
        record["summary"] = summarise(tasks)
        print(json.dumps(record["summary"], indent=1))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
