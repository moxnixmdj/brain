"""Which action made the episode fail? Ask the environment by running it again.

THE PROBLEM
-----------
r109 measured every per-step oracle this project built against the real grader:
agreement 2/12. r108 found three "verified" steps and all three lost the episode.
The conclusion drawn then was that a GUI emits no localisation signal, so the
universal learning contract could never honestly set `verified_coverage=True`
for a web step, and every task routed to LEARN forever.

That conclusion was wrong, and 2026 says why.

Famas (arXiv 2509.13782) applies SPECTRUM-BASED FAULT LOCALISATION to agent
trajectories. The move is not to look harder at a single step. It is to run the
SAME task many times, keep every trajectory with its outcome, and score each
action by how strongly it co-occurs with failure:

        ochiai(action) = failures containing it / sqrt(runs containing it * total failures)

That is precisely the formula this repository already uses on CODE, where it
localised 6 of 6 seeded defects at rank 1-2 on an unseen 851-test repository.
The signal was never missing. Nobody had run the repeated episodes that produce
it.

WHAT THIS MODULE DOES, AND WHAT IT REFUSES TO DO
-----------------------------------------------
It runs a declared policy N times against one task, records each trajectory as an
ordered tuple of action keys, reads the OUTCOME ONLY FROM THE ENVIRONMENT (the
caller supplies `reward_fn`, which for MiniWob is WOB_DONE_GLOBAL /
WOB_REWARD_GLOBAL -- never this module's opinion), and returns a ranked list of
suspect actions.

It does not choose actions, does not read the page, and cannot succeed an
episode on its own authority. `trusted` is True only when the spectrum
SEPARATES: a top suspect with Ochiai strictly greater than every other action's,
on a run set containing at least one success and one failure. When every action
appears in both, or in neither, the verdict is ABSTAIN -- because a spectrum
that does not separate is not evidence, and r108/r109 are what happens when such
a spectrum is treated as one.

THE HONEST LIMIT, STATED BEFORE ANY MEASUREMENT
----------------------------------------------
Ochiai needs variance. If the policy is deterministic and always fails, every
action appears in every run and every action gets the same score: no separation,
no attribution. The mechanism can only localise where the repeated executions
actually differ. That is not a defect to be patched later; it is the condition
under which the method is sound.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Hashable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_REPEAT_EXECUTION_SPECTRUM_V1"

SEPARATED = "SPECTRUM_SEPARATES"
NO_SEPARATION = "SPECTRUM_DOES_NOT_SEPARATE"
INSUFFICIENT = "INSUFFICIENT_VARIANCE"
NO_FAILURES = "NO_FAILURES_TO_ATTRIBUTE"
NO_RUNS = "NO_RUNS"
NO_DISCRIMINATOR = "NO_DISCRIMINATING_ACTION"
NO_CONTRAST = "NO_OUTCOME_CONTRAST"
SOURCES_DISAGREE = "OCHIAI_AND_CONTRAST_DISAGREE"


class SpectrumError(ValueError):
    pass


def ochiai(runs_with: int, runs_total: int, failures_total: int, failures_with: int) -> float:
    """Standard Ochiai. Zero when either side is empty; never NaN."""
    if runs_total <= 0 or failures_total <= 0 or runs_with <= 0:
        return 0.0
    value = failures_with / math.sqrt(runs_with * failures_total)
    # failures_with <= failures_total and failures_with <= runs_with, so the value lies
    # in [0, 1]; clamp only to absorb floating point.
    return max(0.0, min(1.0, value))


def contrast(rows: Sequence[Mapping[str, Any]], min_support: int = 2) -> dict[str, Any]:
    """Rank by outcome contrast rather than by failure frequency.

    r121 measured why this must exist. On MiniWob click-option the repeated spectrum
    gave Ochiai 0.8040 to `submit` and 0.5222 to `select:1`/`select:2`. But `submit`
    failed only in the runs that had already selected a wrong option (success rate
    1/9), while `select:1` and `select:2` NEVER succeeded (0/3) and `select:0` did
    (1/3). Ochiai's frequency term rewards ubiquity, so it named the frequent innocent
    action. Co-occurrence with failure is not causation even across repeated runs.

    Contrast asks the question the spectrum was supposed to answer: among runs that
    contained this action, did ANY of them succeed? An action that never co-occurs
    with success, while some other action does, is the discriminating suspect.
    """
    disc = [r for r in rows if r.get("discriminating")]
    sufficiently_supported = [r for r in disc if r["runs_with"] >= min_support]
    ever_succeeds = [r for r in disc if r["successes_with"] > 0]
    never_succeeds = [r for r in sufficiently_supported if r["successes_with"] == 0]
    never_succeeds.sort(key=lambda r: (-r["runs_with"], -r["failures_with"], str(r["action"])))
    return {
        "never_succeeds": never_succeeds,
        "ever_succeeds": ever_succeeds,
        "sufficient_support": sufficiently_supported,
        "min_support": min_support,
    }


def _with_contrast(rows):
    for row in rows:
        row["success_rate"] = (round(row["successes_with"] / row["runs_with"], 6)
                               if row["runs_with"] else None)
    return rows


def attribute(
    trajectories: Sequence[Sequence[Hashable]],
    outcomes: Sequence[bool],
) -> dict[str, Any]:
    """Rank actions by Ochiai against failure.

    `trajectories[i]` is the ordered list of action keys attempted in run i.
    `outcomes[i]` is True iff that run achieved the environment's goal.
    An action counts as "present in a run" at most once per run, regardless of how
    many times it was taken -- repetition inside one episode is a policy property,
    not evidence about the action.
    """
    if len(trajectories) != len(outcomes):
        raise SpectrumError("TRAJECTORY_AND_OUTCOME_LENGTH_MISMATCH")
    runs_total = len(trajectories)
    if runs_total == 0:
        return {"schema": SCHEMA, "status": NO_RUNS, "suspects": [], "trusted": False,
                "runs": 0, "failures": 0, "successes": 0}

    failures_total = sum(1 for o in outcomes if not o)
    successes_total = runs_total - failures_total

    present: dict[Hashable, int] = {}
    present_in_failure: dict[Hashable, int] = {}
    for traj, ok in zip(trajectories, outcomes):
        seen = set(traj)
        for key in seen:
            present[key] = present.get(key, 0) + 1
            if not ok:
                present_in_failure[key] = present_in_failure.get(key, 0) + 1

    rows = []
    for key, runs_with in present.items():
        f_with = present_in_failure.get(key, 0)
        # A DISCRIMINATOR varies across runs. An action present in every run is
        # consistent with every outcome and therefore cannot explain the difference
        # between them; an action present in no run cannot be reported at all.
        # Measured on MiniWob click-option (r121): without this guard Ochiai ranks the
        # ubiquitous `start` action first at 0.9574 purely because high counts inflate
        # f/sqrt(n_runs*fails). That is a false attribution, not a localisation.
        discriminating = 0 < runs_with < runs_total
        rows.append({
            "action": key,
            "runs_with": runs_with,
            "failures_with": f_with,
            "successes_with": runs_with - f_with,
            "discriminating": discriminating,
            "ochiai": round(ochiai(runs_with, runs_total, failures_total, f_with), 6),
        })
    rows = _with_contrast(rows)
    rows.sort(key=lambda r: (not r["discriminating"], -r["ochiai"], -r["failures_with"],
                             r["runs_with"], str(r["action"])))

    base = {
        "schema": SCHEMA,
        "runs": runs_total,
        "failures": failures_total,
        "successes": successes_total,
        "suspects": rows,
    }

    if failures_total == 0:
        return {**base, "status": NO_FAILURES, "trusted": False,
                "reason": "every run succeeded; there is nothing to attribute"}
    if successes_total == 0:
        return {**base, "status": INSUFFICIENT, "trusted": False,
                "reason": "no successful run; Ochiai has no contrast to measure against"}
    if not rows:
        return {**base, "status": INSUFFICIENT, "trusted": False,
                "reason": "no actions were recorded"}

    top = rows[0]
    runner_up = rows[1]["ochiai"] if len(rows) > 1 else 0.0
    if not top["discriminating"]:
        return {**base, "status": NO_DISCRIMINATOR, "trusted": False,
                "reason": "no action varies with the outcome; every action either appears in "
                          "all runs or in none, so the spectrum cannot separate a cause "
                          "from a constant"}
    if top["ochiai"] <= 0.0 or top["ochiai"] <= runner_up:
        return {**base, "status": NO_SEPARATION, "trusted": False,
                "reason": "the top score does not exceed the next; the spectrum cannot "
                          "distinguish a responsible action from an incidental one"}

    # Ochiai ranked something. Before certifying it, demand the outcome contrast.
    con = contrast(rows)
    never = con["never_succeeds"]
    if not never:
        return {**base, "status": NO_CONTRAST, "trusted": False, "contrast": con,
                "reason": "no sufficiently supported action never co-occurs with success; "
                          "the failure is not attributable to any single action"}
    if top["action"] not in {r["action"] for r in never}:
        return {**base, "status": SOURCES_DISAGREE, "trusted": False, "contrast": con,
                "top": top, "contrast_top": never[0],
                "reason": "Ochiai's top suspect co-occurs with success, so it cannot be the "
                          "cause; the frequency term rewarded ubiquity. The contrast suspect "
                          "is " + str(never[0]["action"]) + " and is reported instead, but the "
                          "two statistics disagreeing means the attribution is not trusted"}

    return {**base, "status": SEPARATED, "trusted": True, "contrast": con,
            "top": never[0], "ochiai_top": top,
            "margin": round(top["ochiai"] - runner_up, 6),
            "reason": "Ochiai's top suspect is also an action that never co-occurs with "
                      "success; both statistics agree"}


def run_and_attribute(
    policy: Callable[[int], Sequence[Hashable]],
    reward_fn: Callable[[int], bool],
    *,
    runs: int = 10,
) -> dict[str, Any]:
    """Execute `policy(run_index)` `runs` times, reading the outcome from `reward_fn`.

    The policy performs the episode and returns its action keys. The outcome comes
    from the environment, never from the policy -- a policy that could report its own
    success would make this the same self-certified oracle that r109 already refuted.
    """
    if runs <= 0:
        raise SpectrumError("RUNS_MUST_BE_POSITIVE")
    trajectories: list[Sequence[Hashable]] = []
    outcomes: list[bool] = []
    for i in range(runs):
        trajectories.append(tuple(policy(i)))
        outcomes.append(bool(reward_fn(i)))
    result = attribute(trajectories, outcomes)
    result["attribution_from_environment"] = True
    return result


def as_verified_coverage(spectrum: Mapping[str, Any]) -> dict[str, Any]:
    """Translate a spectrum into the one field the learning contract gates on.

    `universal_learning_contract_v1.route_input` opens the known-capability route
    only for literal True. This is the only function in the project that may
    produce that True for a GUI step, and it does so only on a spectrum that
    separated AND had real failures to attribute.
    """
    trusted = spectrum.get("status") == SEPARATED and spectrum.get("trusted") is True
    return {
        "schema": SCHEMA + "_COVERAGE",
        "verified_coverage": bool(trusted),
        "basis": spectrum.get("status"),
        "top_action": (spectrum.get("top") or {}).get("action") if trusted else None,
        "margin": spectrum.get("margin") if trusted else None,
        "refusal_reason": None if trusted else spectrum.get("reason"),
    }
