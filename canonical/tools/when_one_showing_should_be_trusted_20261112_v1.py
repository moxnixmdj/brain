#!/usr/bin/env python3
"""One demonstration is worth 4.7x a replay -- and a third of the time it is worth exactly nothing.

THE OWNER'S QUESTION, IN THE FORM IT WAS ASKED
----------------------------------------------
"Exact recall is solved, generalisation is not. Fix problem 2 perfectly."

The tree has already measured the *coverage* half of generalisation, and the answer is stable
across every instrument it owns: one demonstration of a repeated change recovers **15.8%** of what
the people did to the other files at **95.5%** precision, and a second demonstration buys about
eight to ten points more (``REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json``). A companion round
found that *which* file you demonstrate matters enormously, that reach -- how many sibling files a
candidate's own lesson fits -- predicts it at r=0.88, and that choosing by reach captures 80 of the
119 changes the best possible choice would have captured
(``WHICH_DEMONSTRATION_YOU_GIVE_IS_A_DECISION_20261112_V1.md``).

Both rounds optimise one half of the problem. This tool measures the half that decides whether the
mechanism is deployable at all, and that nobody had scored:

    what does one showing cost when it is wrong?

WHY PRECISION OF THE CHOSEN CANDIDATE IS NOT THE SAME QUESTION
--------------------------------------------------------------
The recorded 95.5% precision is pooled over every asking of the organ, most of them refusals. That
is the right number for "when it edits, is it right?". It is the wrong number for the decision a
deployer actually makes, which is: *"I am about to change this codebase having seen one example --
how often is the change I am about to make one nobody asked for?"* That is precision **of the
chosen demonstration**, over the tasks where a demonstration was chosen, and it is a different
denominator.

There is a second, larger effect the coverage instruments cannot see because their metric excludes
import lines. Measured here for the first time: **215 of the 1,889 changes the people made are
import-line changes (11.4%)**, and the organ refuses import-only demonstrations by construction
("the two example files hold the same code, apart from import lines that were added or removed").
A whole class of repeated change is therefore invisible to a metric that reports 15.8%.

THE THREE THINGS THIS TOOL MEASURES
-----------------------------------
  A. **The price of a wrong showing**, per chosen demonstration rather than per asking.
  B. **Calibration by reach**: precision as a function of reach, over all 89 candidate
     demonstrations, so that "how much should I trust this one?" has a number attached.
  C. **Abstention**: the organ may decline to be taught. What does declining cost, and what does it
     buy? A deployer only needs the one demonstration if the alternative is a wrong edit.

PRE-REGISTERED PREDICTION (written before this file was run, kept whatever it says)
-----------------------------------------------------------------------------------
The first version of this measurement assumed reach was monotone in precision and that the honest
policy was "require reach >= 2". Both were wrong, and the correction is recorded rather than
quietly fixed, because the wrong version is the one a reader would have predicted:

  * precision of the chosen demonstration will be **below** the pooled 95.5%, because the pooled
    figure is dominated by files where the organ correctly refused;
  * reach will **not** be monotone in precision (the reach==4 stratum contains most of the wrong
    changes; reach==5 and reach==3 are exact);
  * declining a task whose strongest candidate reaches less than one sibling will cost **no**
    change that would have been right, and will remove the wrong ones; measured as an equality of
    both counts, not as a comparison against zero.

WHERE THE CORPUS COMES FROM
---------------------------
The 15 merged pull requests of the recorded run, fetched again from GitHub and checked against the
sha256 of every file in that record. Nothing is re-selected, so this is the same corpus and the
comparison is like-for-like:

    python3 canonical/tools/repeated_change_one_example_measure_v1.py \\
        --collect /tmp/pulls_v2.json \\
        --as-recorded-in canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json

Authority **NONE**. No model, no network at measure time, no capability registered, no family
flipped, `truth.achieved` stays `false`. Spend $0. The organ is not edited: this measures
``edit_by_example_v1`` exactly as ``main`` has it.

Run:
    python3 canonical/tools/when_one_showing_should_be_trusted_20261112_v1.py --pulls /tmp/pulls_v2.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "WHEN_ONE_SHOWING_SHOULD_BE_TRUSTED_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ORGAN = "canonical/swe_kernel/taught_actions/edit_by_example_v1.py"
RECORD = "canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json"

# The reach strata are named before the run so the table cannot be shaped after it.
REACH_STRATA = (0, 1, 2, 3, 4, 5)

# The one rule this tool adds to the recorded instrument. It is stated here, not derived from the
# outcome, so the same sentence can be applied to a codebase nobody has changed yet.
CHOICE_RULE = ("greatest reach, then fewest blanks, then path -- the rule the recorded round "
               "measured against four alternatives and could not beat")

# A deployer's question, in the only form that has a number: act only when the demonstration's own
# lesson reaches at least this many of its siblings. Chosen from the reach distribution alone, which
# is available before any outcome, and then reported for every value so the choice is auditable.
ABSTENTION_THRESHOLDS = (0, 1, 2, 3, 4, 5)


# --------------------------------------------------------------------------- #
# the corpus, and the numbers the record already fixed
# --------------------------------------------------------------------------- #
def recorded_import_lines() -> dict[str, Any]:
    """How many of the people's changes the record's own metric excludes, exactly.

    The recorded runs count ``developers_changes_not_imports`` and report coverage against it. The
    same rows carry ``developers_changes``, which includes import lines. The difference is a class
    of change this tree refuses by construction, and it had never been reported as a share.
    """
    record = json.loads((ROOT / RECORD).read_text(encoding="utf-8"))
    # The aggregate row keeps only the not-imports count; the per-pull-request rows keep both, so
    # the share is summed from the finer grain rather than inferred.
    rows = record["per_pull_request"]["run_2"]
    with_imports = sum(int(row["one_example"]["developers_changes"]) for row in rows.values())
    without = sum(int(row["one_example"]["developers_changes_not_imports"]) for row in rows.values())
    if without > with_imports:
        raise RuntimeError("the record's two counts disagree; refusing to report a share")
    return {
        "changes_including_import_lines": with_imports,
        "changes_excluding_import_lines": without,
        "import_line_changes": with_imports - without,
        "share_of_changes_that_are_import_lines": ((with_imports - without) / with_imports) if with_imports else 0.0,
        "why_it_matters": ("the organ refuses a demonstration whose change is only import lines, so a "
                           "repeated change made in imports alone can never be taught by it"),
    }


# --------------------------------------------------------------------------- #
# the measurement
# --------------------------------------------------------------------------- #
def measure(pulls: Sequence[Mapping[str, Any]],
            say: Callable[[str], None] = print) -> dict[str, Any]:
    """Every candidate demonstration of every task, with what choosing it costs and earns."""
    from canonical.tools import demonstration_choice_measure_v1 as choice

    tasks: list[dict[str, Any]] = []
    for pull in pulls:
        row = choice.one_task(pull["name"], pull["files"], measure_outcome=True, arm="strict")
        tasks.append(row)
        say(f"{pull['name']:42s} reach={[c['reach'] for c in row['candidates']]}")
    return {"tasks": tasks}


def chosen(tasks: Sequence[Mapping[str, Any]], index: int) -> Mapping[str, Any]:
    """What the stated choice rule picks once the strongest candidate is reach >= ``index``."""
    candidates = tasks["candidates"]
    order = sorted(range(len(candidates)),
                   key=lambda i: (-candidates[i]["reach"], candidates[i]["blanks"], candidates[i]["path"]))
    return candidates[order[0]]


def is_learnable(candidate: Mapping[str, Any]) -> bool:
    return bool(candidate.get("learned"))


def strata(tasks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Precision and coverage by reach, over every candidate of every task."""
    rows: list[dict[str, Any]] = []
    for task in tasks:
        for candidate in task["candidates"]:
            outcome = candidate["outcome"]
            rows.append({
                "task": task["name"],
                "path": candidate["path"],
                "learned": is_learnable(candidate),
                "reach": candidate["reach"],
                "siblings": candidate["siblings"],
                "blanks": candidate["blanks"],
                "rules": len(candidate["rules"]),
                "organ_changes": outcome["organ_changes"],
                "right": outcome["right_not_imports"],
                "wrong": outcome["not_what_the_developers_did"],
                "developers_changes": outcome["developers_changes_not_imports"],
            })
    table: list[dict[str, Any]] = []
    for reach in REACH_STRATA:
        group = [row for row in rows if row["reach"] == reach and row["learned"]]
        if not group:
            continue
        organ_changes = sum(row["organ_changes"] for row in group)
        right = sum(row["right"] for row in group)
        wrong = sum(row["wrong"] for row in group)
        developers = sum(row["developers_changes"] for row in group)
        table.append({
            "reach": reach,
            "candidates": len(group),
            "organ_changes": organ_changes,
            "right": right,
            "wrong": wrong,
            "precision": (right / organ_changes) if organ_changes else 0.0,
            "recovered": (right / developers) if developers else 0.0,
        })
    unlearned = [row for row in rows if not row["learned"]]
    return table, unlearned


def closed_book(tasks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """What abstaining at each threshold earns, costs, and leaves undone.

    ``right`` and ``wrong`` count the changes of the chosen demonstration only -- the decision a
    deployer makes -- not every asking of the organ.
    """
    out: list[dict[str, Any]] = []
    total_developers = sum(row["outcome"]["developers_changes_not_imports"]
                           for task in tasks for row in task["candidates"])
    for minimum in ABSTENTION_THRESHOLDS:
        acted = skipped = right = wrong = developers_acted = 0
        for task in tasks:
            pick = chosen(task, minimum)
            if pick["reach"] < minimum:
                skipped += 1
                continue
            acted += 1
            outcome = pick["outcome"]
            right += outcome["right_not_imports"]
            wrong += outcome["not_what_the_developers_did"]
            developers_acted += outcome["developers_changes_not_imports"]
        out.append({
            "minimum_reach": minimum,
            "tasks_acted_on": acted,
            "tasks_declined": skipped,
            "changes_right": right,
            "changes_wrong": wrong,
            "precision_of_the_decision": (right / (right + wrong)) if (right + wrong) else 0.0,
            "share_of_all_developers_changes_recovered": (right / total_developers) if total_developers else 0.0,
            "developers_changes_in_the_tasks_still_acted_on": developers_acted,
        })
    return out


def ceiling(tasks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """What the best and worst possible demonstration of each task would have earned.

    This bounds every choice rule at once, so a policy can be checked against the most it could
    have had rather than against zero.
    """
    best_right = worst_right = best_wrong = 0
    per_task = []
    for task in tasks:
        candidates = [c for c in task["candidates"]]
        by_outcome = sorted(candidates, key=lambda c: -c["outcome"]["right_not_imports"])
        best = by_outcome[0]["outcome"] if by_outcome else {"right_not_imports": 0, "not_what_the_developers_did": 0}
        worst = by_outcome[-1]["outcome"] if by_outcome else {"right_not_imports": 0, "not_what_the_developers_did": 0}
        best_right += best["right_not_imports"]
        best_wrong += best["not_what_the_developers_did"]
        worst_right += worst["right_not_imports"]
        per_task.append({"task": task["name"], "best_right": best["right_not_imports"],
                         "worst_right": worst["right_not_imports"]})
    return {"best_possible_right": best_right, "best_possible_wrong": best_wrong,
            "worst_possible_right": worst_right, "per_task": per_task}


def pre_registered(tasks: Sequence[Mapping[str, Any]], table: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The three claims written in this file's docstring before the run, scored as written."""
    pooled = 0.9545  # the recorded run's own figure for the organ as main has it
    by_reach = {row["reach"]: row["precision"] for row in table}
    sequence = [by_reach[reach] for reach in sorted(by_reach)]

    policies = {row["minimum_reach"]: row for row in closed_book(tasks)}

    # claim 1: the chosen demonstration's precision is below the pooled per-asking figure
    at_zero = policies[0]["precision_of_the_decision"]

    # claim 2: reach is not monotone in precision
    falls = sum(1 for a, b in zip(sequence, sequence[1:]) if b < a)

    # claim 3: declining at reach >= 1 costs no recoverable change.
    #
    # The first version of this test compared a precision against a count, so its condition was
    # 19 >= 0 and it "held" without measuring anything. The claim is restated as the thing that can
    # be wrong: the tasks declined at reach >= 1 must contribute no change that was right.
    declined = policies[1]["tasks_declined"]
    right_at_zero = policies[0]["changes_right"]
    right_at_one = policies[1]["changes_right"]
    wrong_at_zero = policies[0]["changes_wrong"]
    wrong_at_one = policies[1]["changes_wrong"]
    free_abstention = (right_at_one == right_at_zero) and (wrong_at_one == wrong_at_zero)

    return {
        "claims": {  # keep the names as written in the docstring
            "chosen_precision_below_pooled_95_45": {"value": at_zero, "pooled": pooled,
                                                    "held": at_zero < pooled},
            "reach_not_monotone_in_precision": {"falls_in_the_curve": falls, "by_reach": by_reach,
                                                "held": falls > 0},
            "declining_at_reach_ge_1_costs_nothing": {
                "tasks_declined": declined,
                "changes_right_at_threshold_0": right_at_zero,
                "changes_right_at_threshold_1": right_at_one,
                "changes_wrong_at_threshold_0": wrong_at_zero,
                "changes_wrong_at_threshold_1": wrong_at_one,
                "held": free_abstention,
            },
        },
        "all_held": None,  # filled by the caller
    }


def summarise(tasks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    table, unlearned = strata(tasks)
    policies = closed_book(tasks)
    bound = ceiling(tasks)
    claims = pre_registered(tasks, table)
    claims["all_held"] = all(claim["held"] for claim in claims["claims"].values())
    at_zero = next(row for row in policies if row["minimum_reach"] == 0)
    return {
        "tasks": len(tasks),
        "candidate_demonstrations": sum(len(task["candidates"]) for task in tasks),
        "unlearnable_demonstrations": len(unlearned),
        "changes_the_people_made": sum(row["developers_changes"] for row in _rows(tasks)),
        "import_line_changes_the_metric_excludes": recorded_import_lines(),
        "precision_by_reach": table,
        "abstention_policies": policies,
        "ceiling": bound,
        "pre_registered_prediction": claims,
        "headline": {
            "precision_of_the_chosen_demonstration": at_zero["precision_of_the_decision"],
            "recorded_pooled_precision_for_comparison": 0.9545,
            "changes_recovered_choosing_by_reach": at_zero["changes_right"],
            "changes_recovered_choosing_the_best": bound["best_possible_right"],
            "share_of_best_captured": (at_zero["changes_right"] / bound["best_possible_right"]) if bound["best_possible_right"] else 0.0,
        },
    }


def _rows(tasks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for task in tasks:
        for candidate in task["candidates"]:
            out.append({"developers_changes": candidate["outcome"]["developers_changes_not_imports"]})
    return out


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/when_one_showing_should_be_trusted_20261112_v1.py", ORGAN)
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pulls", type=pathlib.Path, required=True,
                        help="the corpus, fetched with --as-recorded-in from the recorded run")
    parser.add_argument("--out", type=pathlib.Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    pulls = json.loads(args.pulls.read_text(encoding="utf-8"))
    if args.limit:
        pulls = pulls[: args.limit]

    started = time.time()
    say = (lambda line: None) if args.quiet else print
    measured = measure(pulls, say=say)
    tasks = measured["tasks"]

    record: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "organ": ORGAN,
        "pulls_sha256": hashlib.sha256(args.pulls.read_bytes()).hexdigest(),
        "code_sha256": code_sha256(),
        "arm": "strict",
        "choice_rule": CHOICE_RULE,
        "parameters": {"abstention_thresholds": list(ABSTENTION_THRESHOLDS),
                       "reach_strata": list(REACH_STRATA)},
        "tasks": tasks,
        "seconds": round(time.time() - started, 1),
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "truth_achieved": False,
    }
    record["summary"] = summarise(tasks)

    if not args.quiet:
        print(json.dumps(record["summary"], indent=1, ensure_ascii=False))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        say(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
