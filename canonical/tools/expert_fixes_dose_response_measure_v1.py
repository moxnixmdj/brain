#!/usr/bin/env python3
"""Expert fixes shown once, more and more of them: how many unseen bugs does that repair?

The owner's plan in its most favourable form: give the system what experts did, each thing once,
and it has learned it. Here the things are bug fixes, and the amount is turned up from 3 fixes to
2,864.

The lessons. ConDefects (github.com/appmlk/ConDefects, commit 43f0834a): Python programs handed
in at AtCoder between 2021 and 2024, each as its author first wrote it wrong and then got it
right, the two versions one faulty line apart. Nobody in this project wrote them. Each pair is
shown once to the edit-kind learner (canonical/runtime/edit_kind_learning_v1.py, as it stands),
from the faulty program to the correct one.

The bugs. The 100 scored HumanEvalFix bugs of the earlier measurements of that learner (split
seed 20261111). No lesson is a HumanEvalFix program, and no bug's own fix is among the lessons.

The dose. A seed puts all the pairs in an order; the first N of the order are the lessons of dose
N. N is 3, 10, 30, 100, 300, 1000, and then all of them. Below "all" there are two orders, so
every dose is two draws; the doses of one order are nested.

What is asked, per bug and dose: the candidate programs those N lessons vote for, best first, at
most 200 of them run against the bug's tests. A bug is repaired when one passes, in the tree's
candidate screen and again in a fresh interpreter. A repair is right as far as checked when it is
the published fix, or answers like the published fix on the extra inputs of HumanEval+ Mini.
Without running anything it is also written down whether the published fix is among the
candidates at all, and at which place: how far the lessons reach, apart from the 200.

The control. The same pairs shown backwards, from the correct program to the faulty one: a
memory of the same size, read off the same programs, that holds no fix. One order, at 100, 1000
and all.

To compare with (HUMANEVALFIX_EDIT_KIND_TRANSFER_20261111_V1.json): the 203 other fixes of the
benchmark itself with 40 of QuixBugs gave 62 repaired within 1,000 candidates and 56 within 200;
100 of them drawn at random gave 50.5 in 100 within 200.

Written down before the scored run. With more lessons there are more candidates as well, so the
number repaired within 200 rises up to some hundreds of lessons and then stops rising or falls;
at the largest dose it stays under 62; and the backwards control at the largest dose stays within
10 of the lessons shown the right way round.

Zero model calls. Nothing here gives authority to anything.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import random
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef  # noqa: E402
from canonical.tools import humanevalfix_experience_stream_measure_v1 as stream  # noqa: E402

SCHEMA = "BRAIN_EXPERT_FIXES_DOSE_RESPONSE_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
CONDEFECTS_COMMIT = "43f0834a82c5e3bc4516c079fe7765f63b1a15cd"
SIZES = (3, 10, 30, 100, 300, 1000)     # lessons per dose, below "all"
ORDER_SEEDS = (20261112, 20261113)      # the orders the lessons are put in
BACKWARDS_SIZES = (100, 1000)           # the doses of the control, beside "all"; the first order only
BUDGET = 200                            # candidates run against a bug's tests, at most, per dose
RANKS = (1, 10, 100, 200)
ALL = "all"


# --------------------------------------------------------------------------- #
# the lessons
# --------------------------------------------------------------------------- #
def condefects_pairs(root: pathlib.Path) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """({name: (faulty program, correct program)}, the names that could not be read), names in order.
    `root` is a checkout of ConDefects; a pair is Code/<task>/Python/<submission>/."""
    pairs: dict[str, tuple[str, str]] = {}
    unreadable: list[str] = []
    for faulty in sorted((root / "Code").glob("*/Python/*/faultyVersion.py")):
        name = f"condefects/{faulty.parts[-4]}/{faulty.parts[-2]}"
        correct = faulty.with_name("correctVersion.py")
        try:
            pairs[name] = (faulty.read_text(encoding="utf-8"), correct.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            unreadable.append(name)
    return pairs, unreadable


def checkout_commit(root: pathlib.Path) -> str | None:
    done = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def pairs_sha256(pairs: Mapping[str, tuple[str, str]]) -> str:
    digest = hashlib.sha256()
    for name in sorted(pairs):
        for text in (name,) + tuple(pairs[name]):
            digest.update(hashlib.sha256(text.encode("utf-8")).digest())
    return digest.hexdigest()


def order_of(names: Sequence[str], seed: int) -> list[str]:
    """Every name once, in the order the seed gives."""
    order = sorted(names)
    random.Random(seed).shuffle(order)
    return order


def taught(pairs: Mapping[str, tuple[str, str]], *, backwards: bool = False) -> kinds.Lessons:
    """Every pair shown once. `backwards`: from the correct program to the faulty one."""
    import warnings
    lessons = kinds.Lessons()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name in sorted(pairs):
            faulty, correct = pairs[name]
            lessons.learn(name, *((correct, faulty) if backwards else (faulty, correct)))
    return lessons


def doses(names: Sequence[str], taught_something: Sequence[str], *, sizes: Sequence[int] = SIZES,
          seeds: Sequence[int] = ORDER_SEEDS, with_all: bool = True) -> list[dict[str, Any]]:
    """The questions: for each seed and size the first `size` pairs of that seed's order, and once
    all of them. `shown` counts every pair shown; `only` holds those of them that taught something."""
    teaching = set(taught_something)
    out: list[dict[str, Any]] = []
    for seed in seeds:
        order = order_of(names, seed)
        for size in sizes:
            if size >= len(order):
                continue
            first = order[:size]
            out.append({"label": f"{size}/{seed}", "size": str(size), "seed": seed, "shown": size,
                        "only": [name for name in first if name in teaching]})
    if with_all:
        out.append({"label": ALL, "size": ALL, "seed": None, "shown": len(names), "only": [name for name in sorted(names) if name in teaching]})
    return out


# --------------------------------------------------------------------------- #
# one bug
# --------------------------------------------------------------------------- #
def one_question(bench: hef.Bench, votes: Mapping[str, Any], only: Sequence[str], budget: int,
                 extra: Mapping[str, Any] | None, known: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The candidates the lessons in `only` vote for, best first, at most `budget` run."""
    ranked = kinds.ranking(votes, only=only) if only else []
    published = ast.unparse(ast.parse(bench.bug["fixed"]))
    programs = 0
    place = None
    for candidate in bench.in_order(ranked):
        programs += 1
        if place is None and candidate == published:
            place = programs
    rank, program, _ = bench.first_pass(ranked, budget)
    out: dict[str, Any] = {"lessons": len(only), "candidates": programs, "published_fix_rank": place,
                           "first_pass_rank": rank, "repaired": rank is not None,
                           "is_the_published_fix": False, "right_as_far_as_checked": False}
    if program is not None:
        verdict = stream.judged(bench, program, extra, known)
        out["is_the_published_fix"] = verdict["is_the_published_fix"]
        out["right_as_far_as_checked"] = verdict["right_as_far_as_checked"]
    return out


def one_bug(bug: Mapping[str, Any], memories: Mapping[str, kinds.Lessons], questions: Mapping[str, Sequence[Mapping[str, Any]]],
            where: pathlib.Path, *, budget: int = BUDGET, extra: Mapping[str, Any] | None = None,
            check: Callable[[Sequence[str]], int | None] | None = None,
            accepted: Callable[[str], bool] | None = None) -> dict[str, Any]:
    """Every dose of every memory asked about one bug. `memories` and `questions` go by the same
    keys ("forwards", "backwards")."""
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
    for arm, memory in memories.items():
        votes = memory.votes(bug["buggy"]) if memory.operators else {}
        out[arm] = {"candidates_of_every_lesson": len(votes),
                    "doses": {question["label"]: one_question(bench, votes, question["only"], budget, extra, known)
                              for question in questions[arm]}}
        del votes
    out["candidates_run"] = bench.runs
    out["screen_said_pass_fresh_interpreter_said_no"] = bench.screen_said_pass_fresh_interpreter_said_no
    out["seconds"] = round(time.monotonic() - started, 2)
    return out


# --------------------------------------------------------------------------- #
# what it came to
# --------------------------------------------------------------------------- #
def _mean(values: Sequence[float]) -> float | None:
    return round(statistics.mean(values), 2) if values else None


def _median(values: Sequence[float]) -> float | None:
    return statistics.median(values) if values else None


def summarise(per_bug: Mapping[str, Mapping[str, Any]], questions: Mapping[str, Sequence[Mapping[str, Any]]],
              *, budget: int = BUDGET, ranks: Sequence[int] = RANKS) -> dict[str, Any]:
    """Per memory and size: the counts over the usable bugs, for each order and their mean."""
    usable = [name for name, row in per_bug.items() if row.get("usable")]
    out: dict[str, Any] = {"bugs": len(per_bug), "usable": len(usable), "not_usable": [name for name in per_bug if name not in usable], "budget": budget}
    for arm, asked in questions.items():
        sizes: dict[str, Any] = {}
        for size in dict.fromkeys(question["size"] for question in asked):
            orders = [question for question in asked if question["size"] == size]
            cells = []
            for question in orders:
                rows = [per_bug[name][arm]["doses"][question["label"]] for name in usable]
                passed = [row["first_pass_rank"] for row in rows if row["repaired"]]
                cells.append({
                    "seed": question["seed"], "shown": question["shown"],
                    "taught_something": question["taught_something"] if "taught_something" in question else len(question["only"]),
                    "repaired": len(passed), "right_as_far_as_checked": sum(1 for row in rows if row["right_as_far_as_checked"]),
                    "the_published_fix": sum(1 for row in rows if row["is_the_published_fix"]),
                    "repaired_within": {str(rank): sum(1 for place in passed if place <= rank) for rank in ranks if rank <= budget},
                    "published_fix_among_the_candidates": sum(1 for row in rows if row["published_fix_rank"] is not None),
                    "published_fix_within_the_budget": sum(1 for row in rows if row["published_fix_rank"] is not None and row["published_fix_rank"] <= budget),
                    "candidates_median": _median([row["candidates"] for row in rows]),
                    "first_pass_rank_median": _median(passed)})
            sizes[size] = {"orders": len(cells), "by_order": cells,
                           "repaired_mean": _mean([cell["repaired"] for cell in cells]),
                           "right_as_far_as_checked_mean": _mean([cell["right_as_far_as_checked"] for cell in cells]),
                           "published_fix_among_the_candidates_mean": _mean([cell["published_fix_among_the_candidates"] for cell in cells]),
                           "published_fix_within_the_budget_mean": _mean([cell["published_fix_within_the_budget"] for cell in cells]),
                           "candidates_median_mean": _mean([cell["candidates_median"] for cell in cells])}
        out[arm] = sizes
    return out


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/expert_fixes_dose_response_measure_v1.py", "canonical/tools/humanevalfix_edit_kind_transfer_measure_v1.py",
             "canonical/tools/humanevalfix_experience_stream_measure_v1.py", "canonical/runtime/edit_kind_learning_v1.py",
             "canonical/swe_kernel/zygote_worker_pool_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def without_the_names(questions: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    """The questions as they are recorded: which lessons each had is given by its hash, not its list."""
    return {arm: [{**{key: value for key, value in question.items() if key != "only"}, "taught_something": len(question["only"]),
                   "only_sha256": hashlib.sha256("\n".join(question["only"]).encode("utf-8")).hexdigest()} for question in asked]
            for arm, asked in questions.items()}


def merged(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Shard records put together. They must be of the same code, lessons, bugs and questions."""
    first = records[0]
    for other in records[1:]:
        for key in ("code_sha256", "lessons", "benchmark", "questions", "parameters", "which"):
            if other[key] != first[key]:
                raise ValueError(f"the shards differ in {key}")
    per_bug: dict[str, Any] = {}
    for record in records:
        for name, row in record["per_bug"].items():
            if name in per_bug:
                raise ValueError(f"{name} is in two shards")
            per_bug[name] = row
    out = {key: value for key, value in first.items() if key not in ("per_bug", "summary", "shard", "seconds", "generated_utc")}
    out["per_bug"] = dict(sorted(per_bug.items(), key=lambda item: int(item[0].split("/")[1])))
    out["shards"] = [record.get("shard") for record in records]
    out["seconds"] = round(sum(record.get("seconds", 0) for record in records), 1)
    out["generated_utc"] = max(record["generated_utc"] for record in records)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--condefects", type=pathlib.Path, help="a checkout of github.com/appmlk/ConDefects")
    parser.add_argument("--humanevalfix", type=pathlib.Path, help="humanevalpack.jsonl, the Python data")
    parser.add_argument("--extra-inputs", type=pathlib.Path, default=None, help="HumanEvalPlus-Mini.jsonl")
    parser.add_argument("--work-dir", type=pathlib.Path)
    parser.add_argument("--which", choices=("development", "scored"), default="development")
    parser.add_argument("--bugs", nargs="*", default=None, help="only these, by name")
    parser.add_argument("--shard", default="0/1", help="i/n: every n-th bug of the chosen set, starting at the i-th")
    parser.add_argument("--budget", type=int, default=BUDGET)
    parser.add_argument("--any-commit", action="store_true", help="do not insist on the ConDefects commit this was written for")
    parser.add_argument("--merge", nargs="*", type=pathlib.Path, default=None, help="put shard records together instead of measuring")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    if args.merge:
        record = merged([json.loads(path.read_text(encoding="utf-8")) for path in args.merge])
        questions = record["questions"]
        record["summary"] = summarise(record["per_bug"], questions, budget=record["parameters"]["budget"])
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({arm: {size: {k: cell[k] for k in ("repaired_mean", "right_as_far_as_checked_mean", "published_fix_among_the_candidates_mean")}
                                for size, cell in record["summary"][arm].items()} for arm in questions}, indent=1))
        return 0

    for needed in ("condefects", "humanevalfix", "work_dir"):
        if getattr(args, needed) is None:
            parser.error(f"--{needed.replace('_', '-')} is needed to measure")
    commit = checkout_commit(args.condefects)
    if commit != CONDEFECTS_COMMIT and not args.any_commit:
        parser.error(f"the ConDefects checkout is at {commit}, not at {CONDEFECTS_COMMIT}")
    started = time.time()
    pairs, unreadable = condefects_pairs(args.condefects)
    memories = {"forwards": taught(pairs), "backwards": taught(pairs, backwards=True)}
    questions = {"forwards": doses(list(pairs), memories["forwards"].lessons, sizes=SIZES, seeds=ORDER_SEEDS),
                 "backwards": doses(list(pairs), memories["backwards"].lessons, sizes=BACKWARDS_SIZES, seeds=ORDER_SEEDS[:1])}
    bugs = hef.load_bugs(args.humanevalfix)
    development, scored = hef.split(bugs)
    names = list(args.bugs) if args.bugs else (scored if args.which == "scored" else development)
    index, of = (int(part) for part in args.shard.split("/"))
    names = [name for position, name in enumerate(names) if position % of == index]
    extra = hef.extra_inputs(args.extra_inputs)
    by_name = {bug["name"]: bug for bug in bugs}
    per_bug: dict[str, Any] = {}
    record: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "which": args.which if not args.bugs else "named", "shard": args.shard,
        "parameters": {"sizes": list(SIZES), "order_seeds": list(ORDER_SEEDS), "backwards_sizes": list(BACKWARDS_SIZES), "budget": args.budget,
                       "split_seed": hef.SPLIT_SEED, "screen_limit_s": hef.SCREEN_LIMIT_S},
        "lessons": {"source": "github.com/appmlk/ConDefects", "commit": commit, "pairs": len(pairs), "unreadable": unreadable,
                    "pairs_sha256": pairs_sha256(pairs),
                    **{arm: {"taught_something": len(memory.lessons), "taught_nothing": len(memory.taught_nothing), "operators": len(memory.operators)}
                       for arm, memory in memories.items()}},
        "benchmark": {"humanevalfix_sha256": hashlib.sha256(args.humanevalfix.read_bytes()).hexdigest(),
                      "extra_inputs_sha256": hashlib.sha256(args.extra_inputs.read_bytes()).hexdigest() if args.extra_inputs else None},
        "questions": without_the_names(questions), "code_sha256": code_sha256(), "model_calls": 0}

    def write(ended: bool) -> None:
        record.update(per_bug=per_bug, summary=summarise(per_bug, questions, budget=args.budget), seconds=round(time.time() - started, 1),
                      generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), not_ended=not ended)
        if ended:
            record.pop("not_ended")
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"{len(pairs)} pairs, {len(memories['forwards'].lessons)} taught something, {len(memories['forwards'].operators)} operators; "
          f"{len(names)} bugs; {round(time.time() - started, 1)} s", flush=True)
    for count, name in enumerate(names, 1):
        where = args.work_dir / name.replace("/", "_")
        per_bug[name] = one_bug(by_name[name], memories, questions, where, budget=args.budget, extra=extra.get(by_name[name]["number"]))
        shutil.rmtree(where, ignore_errors=True)
        row = per_bug[name]
        if row.get("usable"):
            everything = row["forwards"]["doses"][ALL]
            print(f"{count:3d} {name:11s} all lessons: {'rank ' + str(everything['first_pass_rank']) if everything['repaired'] else '-':9s} "
                  f"candidates {everything['candidates']:6d}  run {row['candidates_run']:5d}  {row['seconds']:6.1f} s", flush=True)
        else:
            print(f"{count:3d} {name:11s} not usable", flush=True)
        write(ended=False)
    write(ended=True)
    print(json.dumps({arm: {size: {k: cell[k] for k in ("repaired_mean", "right_as_far_as_checked_mean", "published_fix_among_the_candidates_mean")}
                            for size, cell in record["summary"][arm].items()} for arm in questions}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
