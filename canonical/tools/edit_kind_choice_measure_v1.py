#!/usr/bin/env python3
"""The choice among candidates, counted on bugs whose fixes are known, then tried on bugs nobody showed.

What came before. 2,864 real fixes shown once to the edit-kind learner repair 55 of the 100 scored
HumanEvalFix bugs within 200 candidates, no more than 1,000 fixes do, and no more than the same
pairs shown backwards (EXPERT_FIXES_DOSE_RESPONSE_20261112_V1.json). The published fix is among
the candidates of 46 bugs and among the first 200 of 34: what is missing is the choice.

What is asked here. The lessons stay the same 2,864 fixes. What is added is experience of another
sort: 64 bugs whose fixes are known (the development bugs of HumanEvalFix; none is a scored bug).
On each of them every operator of the lessons that fits is tried, and it is counted, by kind of
operator, by how many lessons gave it and by how many candidates it makes, whether the bug's
published fix is among its candidates (canonical/runtime/edit_kind_choice_v1.py). From the counts
the candidates of a new bug are ordered. Does that order repair more of the 100 scored bugs,
within the same 200 candidates, than the learner's own order by votes?

Three steps, each a way of running this tool.

  --count        the counts, one set per development bug, for the lessons one way round
  --places       before any scored bug is touched: every development bug in turn is ordered with
                 the counts of the OTHER 63, and the place of its published fix is written down under
                 the learner's votes and under the two ways of putting the counted shares together.
                 No test is run. This decides which way is used, and whether the scored run is made at all
  (neither)      the measurement: for each bug and each way round of the lessons, the learner's own
                 order and the counted order, at most 200 candidates of each run against the tests

The control is the same lessons shown backwards, with their own counts made the same way.

A bug is repaired when a candidate passes its tests, in the tree's candidate screen and again in a
fresh interpreter. A repair is right as far as checked when it is the published fix or answers
like it on the extra inputs of HumanEval+ Mini.

Written down before the scored run, after the development bugs had been ordered (step two): see
EXPECTED below.

Zero model calls. Nothing here gives authority to anything.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import shutil
import statistics
import sys
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_choice_v1 as choice  # noqa: E402
from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.tools import expert_fixes_dose_response_measure_v1 as dose  # noqa: E402
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef  # noqa: E402
from canonical.tools import humanevalfix_experience_stream_measure_v1 as stream  # noqa: E402

SCHEMA = "BRAIN_EDIT_KIND_CHOICE_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
BUDGET = 200
RANKS = (1, 10, 100, 200)
DIRECTIONS = ("forwards", "backwards")
VOTES, COUNTED = "votes", "counted"       # the learner's own order; the order by the counts
EXPECTED = "NOT YET WRITTEN"              # replaced before the scored run; see the record


# --------------------------------------------------------------------------- #
# the counts
# --------------------------------------------------------------------------- #
def counted_on(bugs: Sequence[Mapping[str, Any]], lessons: kinds.Lessons, say: Callable[[str], None] | None = None) -> dict[str, dict[str, Any]]:
    """For every bug: the counts it alone gives, with its published fix as what should be among the candidates."""
    out: dict[str, dict[str, Any]] = {}
    for number, bug in enumerate(bugs, 1):
        started = time.monotonic()
        counts = choice.Counts()
        got = choice.count_program(counts, lessons, bug["buggy"], bug["fixed"])
        out[bug["name"]] = {**counts.as_dict(), **(got or {"operators_that_fitted": 0, "operators_that_held_the_fix": 0}),
                            "could_be_read": got is not None, "seconds": round(time.monotonic() - started, 2)}
        if say:
            say(f"{number:3d} {bug['name']:11s} fitted {out[bug['name']]['operators_that_fitted']:5d}  held the fix "
                f"{out[bug['name']]['operators_that_held_the_fix']:4d}  {out[bug['name']]['seconds']:6.1f} s")
    return out


def put_together(per_bug: Mapping[str, Mapping[str, Any]], without: Sequence[str] = ()) -> choice.Counts:
    """The counts of all the bugs but those named."""
    whole = choice.Counts()
    for name, counts in per_bug.items():
        if name not in without:
            whole.take(choice.Counts.from_dict(counts))
    return whole


# --------------------------------------------------------------------------- #
# the place of the published fix, with no test run
# --------------------------------------------------------------------------- #
def place_of(order: Sequence[tuple[str, float, Any]], wanted: str, compiles: dict[str, bool]) -> int | None:
    """The place of `wanted` among the candidates that are programs, counting from 1; None when it is not there."""
    place = 0
    for candidate, _, _ in order:
        if candidate not in compiles:
            compiles[candidate] = kinds.is_a_program(candidate)
        if compiles[candidate]:
            place += 1
            if candidate == wanted:
                return place
    return None


def places_of_the_fix(bug: Mapping[str, Any], lessons: kinds.Lessons, table: choice.Table) -> dict[str, Any]:
    published = ast.unparse(ast.parse(bug["fixed"]))
    found = choice.shares(lessons, bug["buggy"], table)
    compiles: dict[str, bool] = {}
    return {"candidates": len(found), VOTES: place_of(choice.ordered(found, None), published, compiles),
            choice.SUM: place_of(choice.ordered(found, choice.SUM), published, compiles),
            choice.MOST: place_of(choice.ordered(found, choice.MOST), published, compiles)}


def places_summary(per_bug: Mapping[str, Mapping[str, Any]], budget: int = BUDGET) -> dict[str, Any]:
    out: dict[str, Any] = {"bugs": len(per_bug)}
    for how in (VOTES, choice.SUM, choice.MOST):
        found = [row[how] for row in per_bug.values() if row[how] is not None]
        out[how] = {"published_fix_among_the_candidates": len(found),
                    "published_fix_within": {str(rank): sum(1 for place in found if place <= rank) for rank in (1, 10, 50, 100, budget, 1000)},
                    "place_median": statistics.median(found) if found else None,
                    "mean_of_one_over_the_place": round(sum(1.0 / place for place in found) / max(1, len(per_bug)), 4)}
    for how in (choice.SUM, choice.MOST):
        both = [(row[VOTES], row[how]) for row in per_bug.values() if row[VOTES] is not None]
        out[how]["against_the_votes"] = {"nearer_the_front": sum(1 for old, new in both if new < old), "further_back": sum(1 for old, new in both if new > old),
                                         "the_same_place": sum(1 for old, new in both if new == old),
                                         "came_within_the_budget": sum(1 for old, new in both if old > budget >= new),
                                         "fell_out_of_the_budget": sum(1 for old, new in both if old <= budget < new)}
    return out


def chosen_how(summary: Mapping[str, Any], budget: int = BUDGET) -> str:
    """The way of putting shares together that has the published fix within the budget for more
    bugs; equal: the higher mean of one over the place; still equal: the sum."""
    key = lambda how: (summary[how]["published_fix_within"][str(budget)], summary[how]["mean_of_one_over_the_place"])
    return choice.MOST if key(choice.MOST) > key(choice.SUM) else choice.SUM


# --------------------------------------------------------------------------- #
# the measurement: one bug
# --------------------------------------------------------------------------- #
def asked(bench: hef.Bench, order: Sequence[tuple[str, float, Any]], budget: int, extra: Mapping[str, Any] | None,
          known: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The candidates in the order given, at most `budget` of them run against the tests."""
    published = ast.unparse(ast.parse(bench.bug["fixed"]))
    programs = 0
    place = None
    for candidate in bench.in_order(order):
        programs += 1
        if place is None and candidate == published:
            place = programs
    rank, program, _ = bench.first_pass(order, budget)
    out: dict[str, Any] = {"candidates": programs, "published_fix_rank": place, "first_pass_rank": rank, "repaired": rank is not None,
                           "is_the_published_fix": False, "right_as_far_as_checked": False}
    if program is not None:
        verdict = stream.judged(bench, program, extra, known)
        out["is_the_published_fix"] = verdict["is_the_published_fix"]
        out["right_as_far_as_checked"] = verdict["right_as_far_as_checked"]
    return out


def one_bug(bug: Mapping[str, Any], memories: Mapping[str, kinds.Lessons], tables: Mapping[str, choice.Table], where: pathlib.Path, *,
            how: str, budget: int = BUDGET, extra: Mapping[str, Any] | None = None,
            check: Callable[[Sequence[str]], int | None] | None = None,
            accepted: Callable[[str], bool] | None = None) -> dict[str, Any]:
    """Each way round of the lessons, in the learner's own order and in the counted order."""
    started = time.monotonic()
    hef.lay_out(bug, where)
    check = check or (lambda programs: hef.screen(where, programs))
    accepted = accepted or (lambda program: hef.accept(bug, program))
    out: dict[str, Any] = {"bug_type": bug["bug_type"]}
    buggy, fixed = ast.unparse(ast.parse(bug["buggy"])), ast.unparse(ast.parse(bug["fixed"]))
    out["benchmark_holds"] = {"buggy_fails_in_the_screen": check([buggy]) is None, "published_fix_passes_in_the_screen": check([fixed]) == 0,
                              "buggy_fails_in_a_fresh_interpreter": not accepted(bug["buggy"]),
                              "published_fix_passes_in_a_fresh_interpreter": bool(accepted(bug["fixed"]))}
    out["usable"] = all(out["benchmark_holds"].values())
    if not out["usable"]:
        return out
    bench = hef.Bench(bug, check, accepted)
    known: dict[str, dict[str, Any]] = {}
    for direction, lessons in memories.items():
        found = choice.shares(lessons, bug["buggy"], tables[direction])
        out[direction] = {VOTES: asked(bench, choice.ordered(found, None), budget, extra, known),
                          COUNTED: asked(bench, choice.ordered(found, how), budget, extra, known)}
        del found
    out["candidates_run"] = bench.runs
    out["screen_said_pass_fresh_interpreter_said_no"] = bench.screen_said_pass_fresh_interpreter_said_no
    out["seconds"] = round(time.monotonic() - started, 2)
    return out


# --------------------------------------------------------------------------- #
# what it came to
# --------------------------------------------------------------------------- #
def summarise(per_bug: Mapping[str, Mapping[str, Any]], directions: Sequence[str], *, budget: int = BUDGET, ranks: Sequence[int] = RANKS) -> dict[str, Any]:
    usable = [name for name, row in per_bug.items() if row.get("usable")]
    out: dict[str, Any] = {"bugs": len(per_bug), "usable": len(usable), "not_usable": [name for name in per_bug if name not in usable], "budget": budget}
    for direction in directions:
        cell: dict[str, Any] = {}
        for arm in (VOTES, COUNTED):
            rows = [per_bug[name][direction][arm] for name in usable]
            passed = [row["first_pass_rank"] for row in rows if row["repaired"]]
            cell[arm] = {"repaired": len(passed), "right_as_far_as_checked": sum(1 for row in rows if row["right_as_far_as_checked"]),
                         "the_published_fix": sum(1 for row in rows if row["is_the_published_fix"]),
                         "repaired_within": {str(rank): sum(1 for place in passed if place <= rank) for rank in ranks if rank <= budget},
                         "published_fix_among_the_candidates": sum(1 for row in rows if row["published_fix_rank"] is not None),
                         "published_fix_within_the_budget": sum(1 for row in rows if row["published_fix_rank"] is not None and row["published_fix_rank"] <= budget),
                         "first_pass_rank_median": statistics.median(passed) if passed else None,
                         "candidates_run_until_the_repair_in_all": sum(passed) + budget * (len(rows) - len(passed))}
        old = {name: per_bug[name][direction][VOTES] for name in usable}
        new = {name: per_bug[name][direction][COUNTED] for name in usable}
        cell["bug_by_bug"] = {
            "repaired_by_both": sum(1 for name in usable if old[name]["repaired"] and new[name]["repaired"]),
            "repaired_only_in_the_counted_order": [name for name in usable if new[name]["repaired"] and not old[name]["repaired"]],
            "repaired_only_in_the_learners_order": [name for name in usable if old[name]["repaired"] and not new[name]["repaired"]],
            "right_only_in_the_counted_order": [name for name in usable if new[name]["right_as_far_as_checked"] and not old[name]["right_as_far_as_checked"]],
            "right_only_in_the_learners_order": [name for name in usable if old[name]["right_as_far_as_checked"] and not new[name]["right_as_far_as_checked"]],
            "repaired_sooner_in_the_counted_order": sum(1 for name in usable if old[name]["repaired"] and new[name]["repaired"] and new[name]["first_pass_rank"] < old[name]["first_pass_rank"]),
            "repaired_later_in_the_counted_order": sum(1 for name in usable if old[name]["repaired"] and new[name]["repaired"] and new[name]["first_pass_rank"] > old[name]["first_pass_rank"])}
        out[direction] = cell
    return out


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/edit_kind_choice_measure_v1.py", "canonical/runtime/edit_kind_choice_v1.py", "canonical/runtime/edit_kind_learning_v1.py",
             "canonical/tools/expert_fixes_dose_response_measure_v1.py", "canonical/tools/humanevalfix_edit_kind_transfer_measure_v1.py",
             "canonical/tools/humanevalfix_experience_stream_measure_v1.py", "canonical/swe_kernel/zygote_worker_pool_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def merged(records: Sequence[Mapping[str, Any]], same: Sequence[str]) -> dict[str, Any]:
    """Shard records put together. They must agree in everything named in `same`."""
    first = records[0]
    for other in records[1:]:
        for key in same:
            if other.get(key) != first.get(key):
                raise ValueError(f"the shards differ in {key}")
    per_bug: dict[str, Any] = {}
    for record in records:
        for name, row in record["per_bug"].items():
            if name in per_bug:
                raise ValueError(f"{name} is in two shards")
            per_bug[name] = row
    out = {key: value for key, value in first.items() if key not in ("per_bug", "summary", "shard", "seconds", "generated_utc", "not_ended")}
    out["per_bug"] = dict(sorted(per_bug.items(), key=lambda item: int(item[0].split("/")[1])))
    out["shards"] = [record.get("shard") for record in records]
    out["seconds"] = round(sum(record.get("seconds", 0) for record in records), 1)
    out["generated_utc"] = max(record["generated_utc"] for record in records)
    return out


SAME = {"count": ("step", "direction", "which", "code_sha256", "lessons", "benchmark"),
        "places": ("step", "direction", "which", "code_sha256", "lessons", "benchmark", "counts_sha256"),
        "measure": ("step", "which", "code_sha256", "lessons", "benchmark", "counts_sha256", "how", "parameters")}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--condefects", type=pathlib.Path, help="a checkout of github.com/appmlk/ConDefects")
    parser.add_argument("--humanevalfix", type=pathlib.Path, help="humanevalpack.jsonl, the Python data")
    parser.add_argument("--extra-inputs", type=pathlib.Path, default=None, help="HumanEvalPlus-Mini.jsonl")
    parser.add_argument("--work-dir", type=pathlib.Path)
    parser.add_argument("--count", action="store_true", help="step one: the counts, per development bug")
    parser.add_argument("--places", action="store_true", help="step two: the place of each development bug's fix, ordered with the counts of the others")
    parser.add_argument("--direction", choices=DIRECTIONS, default="forwards", help="for --count and --places: which way round the lessons are shown")
    parser.add_argument("--counts", nargs="*", type=pathlib.Path, default=None, help="records of step one: one for --places, one per way round for the measurement")
    parser.add_argument("--how", choices=(choice.SUM, choice.MOST), default=None, help="for the measurement: as step two decided")
    parser.add_argument("--which", choices=("development", "scored"), default="development")
    parser.add_argument("--bugs", nargs="*", default=None, help="only these, by name")
    parser.add_argument("--shard", default="0/1", help="i/n: every n-th bug of the chosen set, starting at the i-th")
    parser.add_argument("--budget", type=int, default=BUDGET)
    parser.add_argument("--any-commit", action="store_true", help="do not insist on the ConDefects commit this was written for")
    parser.add_argument("--merge", nargs="*", type=pathlib.Path, default=None, help="put shard records of one step together instead of running")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    def written(record: dict[str, Any]) -> None:
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.merge:
        records = [json.loads(path.read_text(encoding="utf-8")) for path in args.merge]
        step = records[0]["step"]
        record = merged(records, SAME[step])
        if step == "places":
            record["summary"] = places_summary(record["per_bug"], BUDGET)
            record["how_chosen"] = chosen_how(record["summary"], BUDGET)
        elif step == "measure":
            record["summary"] = summarise(record["per_bug"], record["directions"], budget=record["parameters"]["budget"])
        written(record)
        print(json.dumps(record.get("summary", {"bugs": len(record["per_bug"])}), indent=1)[:6000])
        return 0

    for needed in ("condefects", "humanevalfix"):
        if getattr(args, needed) is None:
            parser.error(f"--{needed} is needed")
    if args.count and args.places:
        parser.error("one step at a time")
    commit = dose.checkout_commit(args.condefects)
    if commit != dose.CONDEFECTS_COMMIT and not args.any_commit:
        parser.error(f"the ConDefects checkout is at {commit}, not at {dose.CONDEFECTS_COMMIT}")
    started = time.time()
    pairs, unreadable = dose.condefects_pairs(args.condefects)
    bugs = hef.load_bugs(args.humanevalfix)
    development, scored = hef.split(bugs)
    names = list(args.bugs) if args.bugs else (scored if args.which == "scored" else development)
    index, of = (int(part) for part in args.shard.split("/"))
    names = [name for position, name in enumerate(names) if position % of == index]
    by_name = {bug["name"]: bug for bug in bugs}
    step = "count" if args.count else "places" if args.places else "measure"
    if step != "measure" and (args.which != "development" or any(name in set(scored) for name in names)):
        parser.error("the counts are made on development bugs only")
    directions = [args.direction] if step != "measure" else list(DIRECTIONS)
    memories = {direction: dose.taught(pairs, backwards=direction == "backwards") for direction in directions}
    record: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "step": step, "which": args.which if not args.bugs else "named", "shard": args.shard,
        "lessons": {"source": "github.com/appmlk/ConDefects", "commit": commit, "pairs": len(pairs), "unreadable": unreadable, "pairs_sha256": dose.pairs_sha256(pairs),
                    **{direction: {"taught_something": len(memory.lessons), "operators": len(memory.operators)} for direction, memory in memories.items()}},
        "benchmark": {"humanevalfix_sha256": hashlib.sha256(args.humanevalfix.read_bytes()).hexdigest(),
                      "extra_inputs_sha256": hashlib.sha256(args.extra_inputs.read_bytes()).hexdigest() if args.extra_inputs else None},
        "grouping": {"support_edges": list(choice.SUPPORT_EDGES), "made_edges": list(choice.MADE_EDGES), "shrink": choice.SHRINK},
        "code_sha256": code_sha256(), "model_calls": 0}
    say = lambda line: print(line, flush=True)
    say(f"{step}: {len(pairs)} pairs; {len(names)} bugs; {round(time.time() - started, 1)} s")

    def stamp(ended: bool) -> None:
        record.update(seconds=round(time.time() - started, 1), generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        if not ended:
            record["not_ended"] = True
        else:
            record.pop("not_ended", None)

    if step == "count":
        record["direction"] = args.direction
        record["per_bug"] = counted_on([by_name[name] for name in names], memories[args.direction], say)
        record["whole"] = put_together(record["per_bug"]).as_dict()
        stamp(True)
        written(record)
        return 0

    if not args.counts:
        parser.error("--counts is needed: the records of step one")
    counts_text = [path.read_text(encoding="utf-8") for path in args.counts]
    counts = [json.loads(text) for text in counts_text]
    record["counts_sha256"] = [hashlib.sha256(text.encode("utf-8")).hexdigest() for text in counts_text]
    by_direction = {one["direction"]: one for one in counts}
    for one in counts:
        if one["step"] != "count" or one["lessons"]["pairs_sha256"] != record["lessons"]["pairs_sha256"] or one["grouping"] != record["grouping"]:
            parser.error("a --counts record is not a count of these lessons with this grouping")
        if any(name in set(scored) for name in one["per_bug"]):
            parser.error("a --counts record was made on scored bugs")

    if step == "places":
        if args.direction not in by_direction:
            parser.error(f"no --counts record for the lessons shown {args.direction}")
        per_counts = by_direction[args.direction]["per_bug"]
        record["direction"] = args.direction
        per_bug: dict[str, Any] = {}
        for number, name in enumerate(names, 1):
            began = time.monotonic()
            table = choice.Table(put_together(per_counts, without=[name]))
            per_bug[name] = places_of_the_fix(by_name[name], memories[args.direction], table)
            say(f"{number:3d} {name:11s} candidates {per_bug[name]['candidates']:6d}  votes {per_bug[name][VOTES]}  sum {per_bug[name][choice.SUM]}  "
                f"most {per_bug[name][choice.MOST]}  {time.monotonic() - began:6.1f} s")
        record["per_bug"] = per_bug
        record["summary"] = places_summary(per_bug, BUDGET)
        record["how_chosen"] = chosen_how(record["summary"], BUDGET)
        stamp(True)
        written(record)
        say(json.dumps(record["summary"], indent=1))
        return 0

    for needed in ("work_dir", "how"):
        if getattr(args, needed) is None:
            parser.error(f"--{needed.replace('_', '-')} is needed to measure")
    if set(by_direction) != set(DIRECTIONS):
        parser.error("the measurement needs one --counts record for each way round of the lessons")
    tables = {direction: choice.Table(put_together(by_direction[direction]["per_bug"])) for direction in DIRECTIONS}
    counted_bugs = sorted(set().union(*(set(one["per_bug"]) for one in counts)))

    def tables_for(name: str) -> dict[str, choice.Table]:
        """A bug the counts were made on is ordered with the counts of the other bugs only."""
        if name not in counted_bugs:
            return tables
        return {direction: choice.Table(put_together(by_direction[direction]["per_bug"], without=[name])) for direction in DIRECTIONS}

    extra = hef.extra_inputs(args.extra_inputs)
    record.update(directions=list(DIRECTIONS), how=args.how, expected_before_the_run=EXPECTED,
                  parameters={"budget": args.budget, "split_seed": hef.SPLIT_SEED, "screen_limit_s": hef.SCREEN_LIMIT_S},
                  counts_made_on={"bugs": len(counted_bugs), "names_sha256": hashlib.sha256("\n".join(counted_bugs).encode("utf-8")).hexdigest()})
    per_bug = {}
    record["per_bug"] = per_bug
    for number, name in enumerate(names, 1):
        where = args.work_dir / name.replace("/", "_")
        per_bug[name] = one_bug(by_name[name], memories, tables_for(name), where, how=args.how, budget=args.budget, extra=extra.get(by_name[name]["number"]))
        per_bug[name]["ordered_with_the_counts_of_the_other_bugs_only"] = name in counted_bugs
        shutil.rmtree(where, ignore_errors=True)
        row = per_bug[name]
        if row.get("usable"):
            show = lambda cell: "rank " + str(cell["first_pass_rank"]) if cell["repaired"] else "-"
            say(f"{number:3d} {name:11s} votes {show(row['forwards'][VOTES]):9s} counted {show(row['forwards'][COUNTED]):9s} | backwards: votes "
                f"{show(row['backwards'][VOTES]):9s} counted {show(row['backwards'][COUNTED]):9s} run {row['candidates_run']:5d} {row['seconds']:6.1f} s")
        else:
            say(f"{number:3d} {name:11s} not usable")
        record["summary"] = summarise(per_bug, DIRECTIONS, budget=args.budget)
        stamp(False)
        written(record)
    record["summary"] = summarise(per_bug, DIRECTIONS, budget=args.budget)
    stamp(True)
    written(record)
    say(json.dumps({direction: {arm: {k: record["summary"][direction][arm][k] for k in ("repaired", "right_as_far_as_checked", "published_fix_within_the_budget")}
                                for arm in (VOTES, COUNTED)} for direction in DIRECTIONS}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
