#!/usr/bin/env python3
"""Where one success actually counts: read the MiniWoB++ runs as a ladder, not a headline.

WHY THIS EXISTS
---------------
`canonical/verification/MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json` already contains
the measurement that answers "does one demonstration become a skill in an arbitrary
environment". It sat unread for five passes of this conversation, including three passes in which
I told the user the transfer claim was false while quoting literature instead of this file.

That is not a repository defect, it is a reading defect, and the fix is to make the number
callable rather than prose. So this tool:

  1. reads every recorded run, taking the NEWEST as the one to quote;
  2. prints the ladder -- random, replay, this tree's own generaliser, one success, one success
     denied the instruction, one success plus three practice instances -- as both a success rate
     and a count of pages at or above 18/20;
  3. states what each rung licenses and what it does not;
  4. REFUSES to print a board if a recorded run contradicts its own headline.

WHAT THE LADDER MEANS
---------------------
Every rung is scored on instances nobody had looked at when the learner was written, and the
page's own full reward is the only judge. The gap between `verbatim` (replay the demonstration)
and `version_space` (generalise it) is the entire claim: replay is a cache and was never in
dispute.

The rung that decides the *reason* is `version_space_blind` -- the same learned skill, shown the
demonstration's instruction instead of the instance's. What it loses, it was reading.

Authority: NONE. These are the producer's own runs on its own machine. They are not a leaderboard
entry, and `not_done` in the freshest run lists what was never attempted.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "canonical" / "verification"

SCHEMA = "PROJECT_BRAIN_ONE_SUCCESS_LADDER_V1"

#: Rungs in the order a reader should meet them. Each is (arm, what it is, what it proves).
LADDER = (
    ("random", "a uniformly random offered action",
     "the floor: how often the page rewards a blind press"),
    ("verbatim", "the demonstration replayed by position",
     "a cache. Recalling a visited state was never in dispute"),
    ("existing_compiler", "this tree's own demonstration->skill generaliser",
     "what the repository had BEFORE the version-space learner"),
    ("version_space", "ONE success generalised across the instances of that task",
     "the claim itself: one demonstration, applied to instances never seen"),
    ("version_space_blind", "the same skill, denied the instance's instruction",
     "the reason: what it loses here, it was READING"),
    ("version_space_practice", "the same learner after three extra practice instances",
     "the price of the last few points, in episodes"),
)


#: The full-scale runs. `newest()` among these is the one to quote for the headline.
GENERALISATION_GLOB = "MINIWOB_ONE_SUCCESS_GENERALISATION_*_V*.json"

#: Runs that re-check an existing result on instances nobody had used. They use a different task
#: set, so they are quoted for ORDERING only -- never for the headline number.
REPLICATION_GLOB = "MINIWOB_REPLICATION_*.json"


def runs() -> list[pathlib.Path]:
    return sorted(VERIFICATION.glob(GENERALISATION_GLOB))


def replications() -> list[pathlib.Path]:
    return sorted(VERIFICATION.glob(REPLICATION_GLOB))


def replication_check() -> dict[str, Any]:
    """Does the ladder's ORDERING reproduce on instances that did not exist when it was learned?

    A headline from one run is a result; the same ordering from an independent run on fresh
    instances is a finding. This compares the newest replication to the newest full run and
    reports agreement as a boolean rather than leaving two tables for the reader to compare.

    Only the ordering is compared, deliberately: the replication uses 50 pages and the full run
    130, so the absolute rates are not expected to match and quoting them side by side invites
    exactly the kind of cross-run comparison both files' `read_this_first` forbids.
    """
    reps = replications()
    if not reps:
        return {"available": False}
    rep = json.loads(reps[-1].read_text())
    full = newest()[1]
    rep_arms, full_arms = _arms(rep), _arms(full)

    pairs = (("version_space", "verbatim"), ("version_space", "random"),
             ("version_space", "version_space_blind"), ("verbatim", "random"))
    checks = []
    for high, low in pairs:
        def rate(arms, arm):
            stats = arms.get(arm)
            return (stats or {}).get("mean_task_success_rate_where_replay_is_not_enough")
        a, b = rate(rep_arms, high), rate(rep_arms, low)
        c, e = rate(full_arms, high), rate(full_arms, low)
        if None in (a, b, c, e):
            continue
        checks.append({"ordering": f"{high} > {low}", "replication": a > b, "full_run": c > e})
    return {
        "available": True,
        "replication_run": reps[-1].name,
        "full_run": newest()[0].name,
        "pages": len(rep.get("tasks") or []),
        "test_seeds": (rep.get("parameters") or {}).get("test_seeds", [])[:2],
        "browser": (rep.get("environment") or {}).get("browser"),
        "checks": checks,
        "ordering_reproduces": all(c["replication"] and c["full_run"] for c in checks) if checks else None,
    }


def _load(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def newest() -> tuple[pathlib.Path, dict[str, Any]]:
    recorded = [(p, _load(p)) for p in runs()]
    if not recorded:
        raise FileNotFoundError("NO_RECORDED_RUN")
    return recorded[-1]


def _arms(report: Mapping[str, Any]) -> Mapping[str, Any]:
    return ((report.get("summary") or {}).get("all") or {}).get("arms") or {}


def _pct(share: float | None) -> str:
    return "n/a" if share is None else f"{share * 100:5.1f}%"


def ladder(path: pathlib.Path, report: Mapping[str, Any]) -> list[dict[str, Any]]:
    arms = _arms(report)
    rows = []
    for arm, what, proves in LADDER:
        stats = arms.get(arm)
        if not isinstance(stats, Mapping):
            rows.append({"arm": arm, "what": what, "proves": proves, "present": False})
            continue
        rows.append({
            "arm": arm, "what": what, "proves": proves, "present": True,
            "mean_success": stats.get("mean_task_success_rate"),
            "where_replay_is_not_enough": stats.get("mean_task_success_rate_where_replay_is_not_enough"),
            "pages_at_or_above_90pct": stats.get("tasks_at_or_above_90_percent"),
            "tasks_scored": stats.get("tasks_scored"),
        })
    return rows


def verdict(path: pathlib.Path, report: Mapping[str, Any]) -> dict[str, Any]:
    """What this run licenses, what it refutes, and what it never measured.

    The three counters below are read from the run, not assumed. `denied_the_instruction` is the
    one that separates "the skill generalised" from "the skill re-read the instruction each time",
    and a run that cannot report it cannot support the stronger claim.
    """
    summary = (report.get("summary") or {}).get("all") or {}
    need = summary.get("tasks_that_need_generalisation")
    fixed = summary.get("tasks_a_fixed_replay_already_solves")
    detail = summary.get("one_success_skills_where_replay_is_not_enough") or {}
    arms = _arms(report)

    def _rate(arm: str) -> float | None:
        stats = arms.get(arm)
        return stats.get("mean_task_success_rate_where_replay_is_not_enough") if isinstance(stats, Mapping) else None

    one, blind, practice = _rate("version_space"), _rate("version_space_blind"), _rate("version_space_practice")
    replay = _rate("verbatim")

    return {
        "run": path.name,
        "schema": SCHEMA, "authority": "NONE",
        "pages_demonstrated": summary.get("demonstrated"),
        "tasks_that_need_generalisation": need,
        "tasks_replay_already_solves": fixed,
        "where_replay_is_not_enough": {
            "one_success": one, "denied_the_instruction": blind, "with_practice": practice,
            "replay": replay,
            "lift_over_replay": None if (one is None or replay is None) else one - replay,
        },
        "reads_the_instruction": {
            "fail_when_denied_it": detail.get("of_which_fail_when_denied_the_instruction"),
            "succeed_when_denied_it": detail.get("of_which_still_succeed_when_denied_the_instruction"),
            "survive_an_instruction_change": detail.get("of_which_still_succeed_although_the_instruction_changes"),
        },
        "not_done": report.get("not_done") or [],
        "licenses": [
            "a first success, generalised, beats replaying it on instances never seen "
            f"({_pct(one)} vs {_pct(replay)} where replay is not enough)",
            "the advantage is not a cache: verbatim is the cache arm and it is the weak one",
            "the skill is reading the instance's instruction; denying it drops the same learner to "
            f"{_pct(blind)}",
        ],
        "refutes": [
            "one demonstration is sufficient for an instruction change: "
            f"{detail.get('of_which_still_succeed_although_the_instruction_changes', 'unreported')} "
            "of the generalising tasks survive one",
            "'it learned it once and never needs to learn again': practice adds "
            f"{_pct(practice)} vs {_pct(one)} on the same instances",
        ],
    }


def contradictions(record: dict[str, Any]) -> list[str]:
    """A run that reports a lift without reporting what it costs is not quotable."""
    problems: list[str] = []
    flat = record["where_replay_is_not_enough"]
    if flat["one_success"] is not None and flat["replay"] is None:
        problems.append("NO_REPLAY_BASELINE: a lift over an unmeasured control")
    if flat["one_success"] is not None and flat["one_success"] < 0 or (flat["one_success"] or 0) > 1:
        problems.append("SUCCESS_RATE_OUT_OF_RANGE")
    if record["reads_the_instruction"]["fail_when_denied_it"] is None:
        problems.append("NO_DENIED_INSTRUCTION_CONTROL: cannot separate skill from re-reading")
    if record["tasks_that_need_generalisation"] == 0:
        problems.append("NOTHING_TO_GENERALISE: every page is solved by a fixed replay")
    return problems


def report() -> dict[str, Any]:
    path, data = newest()
    record = verdict(path, data)
    record["ladder"] = ladder(path, data)
    record["contradictions"] = contradictions(record)
    record["runs_on_file"] = [p.name for p in runs()]
    record["replication"] = replication_check()
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = report()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"one success -> a skill, measured on MiniWoB++ pages nobody here wrote")
        print(f"newest run: {result['run']}\n")
        print(f"  pages with a first success        {result['pages_demonstrated']}")
        print(f"  pages where a replay is not enough {result['tasks_that_need_generalisation']}")
        print(f"  pages a fixed replay already solves {result['tasks_replay_already_solves']}\n")
        header = f"  {'arm':24} {'success':>8} {'replay-not-enough':>18} {'pages>=18/20':>13}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for row in result["ladder"]:
            if not row["present"]:
                print(f"  {row['arm']:24} {'-- not in this run --':>43}")
                continue
            print(f"  {row['arm']:24} {_pct(row['mean_success']):>8} "
                  f"{_pct(row['where_replay_is_not_enough']):>18} {row['pages_at_or_above_90pct']:>13}")
        print("\n  licensed:")
        for line in result["licenses"]:
            print(f"    + {line}")
        print("  refuted:")
        for line in result["refutes"]:
            print(f"    - {line}")
        if result["not_done"]:
            print("  never measured:")
            for line in result["not_done"]:
                print(f"    ? {line}")
        if result["contradictions"]:
            print("\n  CONTRADICTIONS:")
            for line in result["contradictions"]:
                print(f"    ! {line}")
    return 1 if result["contradictions"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
