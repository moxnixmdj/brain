#!/usr/bin/env python3
"""What one piece taken out repairs with no lesson at all, beside what 2,864 lessons repair.

What came before. 2,864 real fixes shown once to the edit-kind learner repair 55 of the 100 scored
HumanEvalFix bugs within 200 candidates (EXPERT_FIXES_DOSE_RESPONSE_20261112_V1.json), and an order
counted from further experience did not bring more published fixes to the front
(EDIT_KIND_CHOICE_20261112_V1.json). 22 of the 100 were repaired by nothing here that runs without
a language model, 7 of them bugs that are something too much.

What is asked here. For each bug, every program that is the buggy one with one piece taken out
(canonical/runtime/take_out_v1.py: a few dozen, no lesson behind any of them) is run against the
bug's tests, the smallest piece first, at most 200. How many bugs does that repair, how many of the
repairs are right, and what does it add to the learner with all its lessons when both share the
same 200 candidates: the pieces taken out first, the learner's candidates in what is left?

A bug is repaired when a candidate passes its tests, in the tree's candidate screen and again in a
fresh interpreter. A repair is right as far as checked when it is the published fix or answers
like it on the extra inputs of HumanEval+ Mini. Deleting code is known to make weak tests pass
without repairing anything (Kali, ISSTA 2015), so the two counts are given apart.

The learner is not run again. Its place of the first passing candidate for every scored bug is
read from the dose record, so the sum of the two is arithmetic on two records: a bug counts as
repaired by the two together when a piece taken out passes, or when the learner's first passing
candidate stands within what the pieces left of the 200.

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

from canonical.runtime import take_out_v1 as take_out  # noqa: E402
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef  # noqa: E402
from canonical.tools import humanevalfix_experience_stream_measure_v1 as stream  # noqa: E402

SCHEMA = "BRAIN_TAKE_OUT_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
BUDGET = 200
DOSE_RECORD = ROOT / "canonical" / "verification" / "EXPERT_FIXES_DOSE_RESPONSE_20261112_V1.json"
# Written on 2026-11-12 after the 64 development bugs had been run and before any scored bug was.
EXPECTED = ("On the 64 development bugs a piece taken out repaired 15, 12 of them right as far as checked, and 11 of the 12 bugs that are "
            "something too much, all 11 right; 3 of the 4 repairs of other bugs were not right. The pieces were shaped while looking at the "
            "development bugs, so less is expected of the 100 scored ones. Of their 19 bugs that are something too much: 12 to 16 repaired "
            "and right. Of the other 81: 2 to 6 repaired, most of them not right. In all 15 to 21 repaired and 12 to 17 right. Of the 22 "
            "bugs nothing without a model had repaired, 7 are something too much: 3 to 6 of the 22 repaired. The pieces first and the "
            "learner's candidates in what is left of 200: 58 to 63 repaired against the learner's 55, and 50 to 55 right against 48, with "
            "0 to 3 bugs the learner repaired alone pushed out of the 200. What would make me drop it: the two together repair no more "
            "than 55 or are right for no more than 48; or of the repairs by a piece taken out fewer than two in three are right.")


# --------------------------------------------------------------------------- #
# one bug
# --------------------------------------------------------------------------- #
def one_bug(bug: Mapping[str, Any], where: pathlib.Path, *, budget: int = BUDGET, extra: Mapping[str, Any] | None = None,
            check: Callable[[Sequence[str]], int | None] | None = None,
            accepted: Callable[[str], bool] | None = None) -> dict[str, Any]:
    """The pieces taken out of the buggy program, the smallest first, at most `budget` run against the tests."""
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
    order = take_out.in_order(bug["buggy"])
    texts = [text for text, _, _ in order]
    bench = hef.Bench(bug, check, accepted)
    rank, passing, _ = bench.first_pass(order, budget)
    out.update(candidates=len(order), published_fix_rank=texts.index(fixed) + 1 if fixed in texts else None, first_pass_rank=rank,
               repaired=rank is not None, is_the_published_fix=False, right_as_far_as_checked=False, kind_of_the_piece=None)
    if passing is not None:
        verdict = stream.judged(bench, passing, extra, {})
        out.update(is_the_published_fix=verdict["is_the_published_fix"], right_as_far_as_checked=verdict["right_as_far_as_checked"],
                   kind_of_the_piece=order[rank - 1][2]["kind"], nodes_fewer=order[rank - 1][2]["nodes_fewer"])
        if "on_inputs_the_tests_do_not_have" in verdict:
            out["on_inputs_the_tests_do_not_have"] = verdict["on_inputs_the_tests_do_not_have"]
    out["candidates_run"] = bench.runs
    out["screen_said_pass_fresh_interpreter_said_no"] = bench.screen_said_pass_fresh_interpreter_said_no
    out["seconds"] = round(time.monotonic() - started, 2)
    return out


# --------------------------------------------------------------------------- #
# what it came to
# --------------------------------------------------------------------------- #
def summarise(per_bug: Mapping[str, Mapping[str, Any]], *, budget: int = BUDGET) -> dict[str, Any]:
    usable = {name: row for name, row in per_bug.items() if row.get("usable")}
    rows = list(usable.values())
    made = [row["candidates"] for row in rows]
    by_type: dict[str, dict[str, int]] = {}
    by_kind: dict[str, dict[str, int]] = {}
    for row in rows:
        cell = by_type.setdefault(row["bug_type"], {"bugs": 0, "published_fix_among_the_candidates": 0, "repaired": 0, "right_as_far_as_checked": 0})
        cell["bugs"] += 1
        cell["published_fix_among_the_candidates"] += 1 if row["published_fix_rank"] is not None else 0
        cell["repaired"] += 1 if row["repaired"] else 0
        cell["right_as_far_as_checked"] += 1 if row["right_as_far_as_checked"] else 0
        if row["repaired"]:
            kind = by_kind.setdefault(row["kind_of_the_piece"], {"repaired": 0, "right_as_far_as_checked": 0})
            kind["repaired"] += 1
            kind["right_as_far_as_checked"] += 1 if row["right_as_far_as_checked"] else 0
    return {"bugs": len(per_bug), "usable": len(rows), "not_usable": [name for name in per_bug if name not in usable], "budget": budget,
            "repaired": sum(1 for row in rows if row["repaired"]),
            "right_as_far_as_checked": sum(1 for row in rows if row["right_as_far_as_checked"]),
            "the_published_fix": sum(1 for row in rows if row["is_the_published_fix"]),
            "passes_the_tests_and_is_not_right": sorted((name for name, row in usable.items() if row["repaired"] and not row["right_as_far_as_checked"]),
                                                        key=lambda name: int(name.split("/")[1])),
            "published_fix_among_the_candidates": sum(1 for row in rows if row["published_fix_rank"] is not None),
            "published_fix_within_the_budget": sum(1 for row in rows if row["published_fix_rank"] is not None and row["published_fix_rank"] <= budget),
            "candidates_median": statistics.median(made) if made else None, "candidates_most": max(made) if made else None,
            "bugs_with_more_candidates_than_the_budget": sum(1 for count in made if count > budget),
            "candidates_run_in_all": sum(row["candidates_run"] for row in rows),
            "by_bug_type": dict(sorted(by_type.items())), "by_kind_of_the_piece": dict(sorted(by_kind.items()))}


def beside_the_learner(per_bug: Mapping[str, Mapping[str, Any]], dose_record: Mapping[str, Any], *, budget: int = BUDGET) -> dict[str, Any]:
    """The pieces taken out first and the learner's candidates in what is left of the budget, from
    the learner's recorded places. Only for bugs both records have."""
    learner_rows = dose_record["per_bug"]
    never = set(dose_record.get("every_way_without_a_model_on_these_100_bugs", {}).get("never_repaired_by_any_way", []))
    names = [name for name, row in per_bug.items() if row.get("usable") and name in learner_rows]
    out: dict[str, Any] = {"bugs_in_both_records": len(names), "budget": budget,
                           "the_learner_is": "edit_kind_learning_v1 with all the ConDefects lessons shown forwards, as recorded; not run again"}
    alone = {"repaired": 0, "right_as_far_as_checked": 0}
    pieces = {"repaired": 0, "right_as_far_as_checked": 0}
    together = {"repaired": 0, "right_as_far_as_checked": 0}
    # Two other ways of putting the two together, added after the scored run had been read (see the record):
    learner_first = {"repaired": 0, "right_as_far_as_checked": 0}       # the learner in what the pieces leave of the budget, then the pieces
    larger_budget = {"repaired": 0, "right_as_far_as_checked": 0}       # the learner with the whole budget, then the pieces where it repaired nothing
    more_candidates = 0
    lists: dict[str, list[str]] = {key: [] for key in (
        "repaired_only_by_a_piece_taken_out", "right_only_by_a_piece_taken_out", "repaired_by_the_learner_alone_and_pushed_out_of_the_budget",
        "right_with_the_learner_alone_and_not_right_together", "repaired_among_those_nothing_had_repaired", "right_among_those_nothing_had_repaired")}
    for name in names:
        row = per_bug[name]
        rank, right = learner_rows[name]["forwards"]["all"][:2]
        learner_repaired = rank is not None and rank <= budget
        learner_right = bool(learner_repaired and right)
        alone["repaired"] += 1 if learner_repaired else 0
        alone["right_as_far_as_checked"] += 1 if learner_right else 0
        pieces["repaired"] += 1 if row["repaired"] else 0
        pieces["right_as_far_as_checked"] += 1 if row["right_as_far_as_checked"] else 0
        tried_in_vain = min(row["candidates"], budget)                      # when no piece passes, every piece was run
        if row["repaired"]:
            repaired, is_right = True, bool(row["right_as_far_as_checked"])
        else:
            repaired = rank is not None and tried_in_vain + rank <= budget
            is_right = bool(repaired and right)
        together["repaired"] += 1 if repaired else 0
        together["right_as_far_as_checked"] += 1 if is_right else 0
        if rank is not None and rank + min(row["candidates"], budget) <= budget:
            learner_first["repaired"] += 1
            learner_first["right_as_far_as_checked"] += 1 if right else 0
        elif row["repaired"]:
            learner_first["repaired"] += 1
            learner_first["right_as_far_as_checked"] += 1 if row["right_as_far_as_checked"] else 0
        if learner_repaired:
            larger_budget["repaired"] += 1
            larger_budget["right_as_far_as_checked"] += 1 if right else 0
        else:
            more_candidates += row["first_pass_rank"] if row["repaired"] else min(row["candidates"], budget)
            larger_budget["repaired"] += 1 if row["repaired"] else 0
            larger_budget["right_as_far_as_checked"] += 1 if row["right_as_far_as_checked"] else 0
        if row["repaired"] and not learner_repaired:
            lists["repaired_only_by_a_piece_taken_out"].append(name)
        if row["right_as_far_as_checked"] and not learner_right:
            lists["right_only_by_a_piece_taken_out"].append(name)
        if learner_repaired and not repaired:
            lists["repaired_by_the_learner_alone_and_pushed_out_of_the_budget"].append(name)
        if learner_right and not is_right:
            lists["right_with_the_learner_alone_and_not_right_together"].append(name)
        if name in never and row["repaired"]:
            lists["repaired_among_those_nothing_had_repaired"].append(name)
        if name in never and row["right_as_far_as_checked"]:
            lists["right_among_those_nothing_had_repaired"].append(name)
    out.update(the_learner_alone=alone, a_piece_taken_out_alone=pieces, the_pieces_first_then_the_learner_in_what_is_left=together,
               bugs_nothing_without_a_model_had_repaired=len([name for name in names if name in never]), **lists)
    out["put_together_in_other_ways__looked_at_after_the_scored_run"] = {
        "the_learner_first_in_what_the_pieces_leave_then_the_pieces": learner_first,
        "the_learner_with_the_whole_budget_then_the_pieces_where_it_repaired_nothing": {**larger_budget, "candidates_run_beyond_the_budget_in_all": more_candidates}}
    return out


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/take_out_measure_v1.py", "canonical/runtime/take_out_v1.py", "canonical/runtime/edit_kind_learning_v1.py",
             "canonical/tools/humanevalfix_edit_kind_transfer_measure_v1.py", "canonical/tools/humanevalfix_experience_stream_measure_v1.py",
             "canonical/swe_kernel/zygote_worker_pool_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--humanevalfix", required=True, type=pathlib.Path, help="humanevalpack.jsonl, the Python split")
    parser.add_argument("--extra-inputs", type=pathlib.Path, help="HumanEvalPlus-Mini.jsonl; without it only the published fix counts as right")
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--which", choices=("development", "scored"), default="development")
    parser.add_argument("--bugs", nargs="*", default=None, help="only these, by name")
    parser.add_argument("--budget", type=int, default=BUDGET)
    parser.add_argument("--dose-record", type=pathlib.Path, default=DOSE_RECORD, help="the learner's recorded places, for the sum of the two")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    started = time.time()
    bugs = hef.load_bugs(args.humanevalfix)
    development, scored = hef.split(bugs)
    names = list(args.bugs) if args.bugs else (scored if args.which == "scored" else development)
    by_name = {bug["name"]: bug for bug in bugs}
    extra = hef.extra_inputs(args.extra_inputs)
    record: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "which": args.which if not args.bugs else "named", "expected_before_the_run": EXPECTED,
        "benchmark": {"humanevalfix_sha256": hashlib.sha256(args.humanevalfix.read_bytes()).hexdigest(),
                      "extra_inputs_sha256": hashlib.sha256(args.extra_inputs.read_bytes()).hexdigest() if args.extra_inputs else None},
        "parameters": {"budget": args.budget, "split_seed": hef.SPLIT_SEED, "screen_limit_s": hef.SCREEN_LIMIT_S},
        "code_sha256": code_sha256(), "model_calls": 0, "lessons": 0}
    per_bug: dict[str, Any] = {}
    record["per_bug"] = per_bug

    def written(ended: bool) -> None:
        record["summary"] = summarise(per_bug, budget=args.budget)
        record.update(seconds=round(time.time() - started, 1), generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        if ended:
            record.pop("not_ended", None)
        else:
            record["not_ended"] = True
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    for number, name in enumerate(names, 1):
        where = args.work_dir / name.replace("/", "_")
        row = per_bug[name] = one_bug(by_name[name], where, budget=args.budget, extra=extra.get(by_name[name]["number"]))
        shutil.rmtree(where, ignore_errors=True)
        if row.get("usable"):
            what = f"rank {row['first_pass_rank']:3d} {'right' if row['right_as_far_as_checked'] else 'NOT RIGHT'} ({row['kind_of_the_piece']})" if row["repaired"] else "-"
            print(f"{number:3d} {name:11s} {row['bug_type']:16s} candidates {row['candidates']:4d}  fix at {str(row['published_fix_rank']):4s}  {what}  {row['seconds']:5.1f} s", flush=True)
        else:
            print(f"{number:3d} {name:11s} not usable", flush=True)
        written(False)
    if args.dose_record and args.dose_record.exists():
        dose_text = args.dose_record.read_text(encoding="utf-8")
        record["beside_the_learner"] = {"dose_record_sha256": hashlib.sha256(dose_text.encode("utf-8")).hexdigest(),
                                        **beside_the_learner(per_bug, json.loads(dose_text), budget=args.budget)}
    written(True)
    print(json.dumps({key: value for key, value in record["summary"].items() if key not in ("not_usable",)}, indent=1), flush=True)
    if "beside_the_learner" in record:
        print(json.dumps(record["beside_the_learner"], indent=1), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
