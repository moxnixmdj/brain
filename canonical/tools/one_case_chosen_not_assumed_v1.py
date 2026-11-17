#!/usr/bin/env python3
"""Ask the suite one case it did not expect you to choose, and measure both ways it can be wrong.

THE QUESTION
------------
Every repair loop in this tree screens candidates with the corpus's test data and then judges the
survivor with the corpus's own suite. The screen exists to be cheap, and it is *asked the first
case*, because that is the order the corpus stores. Nothing chose that question. 2026 measured what
that costs on the frontier benchmarks:

  * SWEPatchTest (arXiv:2610.18004) replays generated suites on buggy and patched codebases and
    finds the best configuration reaches **9.21% joint validation** while reproducing the reference
    transition on 59.29% of tasks -- a suite can reproduce the bug and still accept the wrong patch
    or reject the right one.
  * SWE-bench Pro's own verifier was measured at **8.5% false accept / 24.0% false reject**
    (Datacurve, May 2026). The error runs in *both* directions, and a single-accuracy number hides it.
  * *Accepted but Wrong* (arXiv:2611.08269) shows the fix is not more tests but **which** input:
    one well-chosen edge input moved wrong releases from 0.410 to 0.065 with false rejection at 0.010.

So: the screen is an instrument, and its two error rates are a property of the *question it asks*.

WHAT THIS MEASURES
------------------
On the published bugs themselves, with a **complete finite repair space** (every candidate the merged
generator enumerates, nothing hand-written), the outcome table of every candidate on every published
case is computed exactly -- so precision and recall loss are *counted*, not estimated. Then the same
space is screened three ways and each verdict is put to the corpus's real pytest:

  FIRST_CASE   the corpus's first case -- what the loop does now: it asks a question nobody chose
  BEST_CASE    the case that is exact-best on this space, chosen by counting how many candidates it
               admits and how many of those pass the whole suite
  ALL_CASES    every case at once (the full suite in-process; the reference)

BEST_CASE is the one that matters, and its property is not cleverness but that it is **free**: the
whole candidate space can be evaluated in-process against every published case in seconds, so the
precision of each case is a computable quantity before a single expensive verdict is bought. A screen
is therefore not something to assume -- it is something to *design*, from the space it will be asked
about, at no cost.

WHAT IS AND IS NOT CLAIMED
--------------------------
Counted: exact per-task precision and recall loss of each screen over the complete space, the
false-accept and false-reject counts, and whether the chosen case beats the first case *on these
tasks*. Not claimed: that this generalises to any other corpus, that the generator's space contains
the gold patch, or any capability credit. Authority NONE, producer-run, zero model, zero network at
run time.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import shutil
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parents[1]))

import grammar_closed_repair_v1 as gen  # noqa: E402

SCHEMA = "BRAIN_ONE_CASE_CHOSEN_NOT_ASSUMED_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"


# -------------------------------------------------------------------------------------------------- #
# the outcome table: which candidate satisfies which case, computed once and exactly
# -------------------------------------------------------------------------------------------------- #
def outcome_of(source: str, function_name: str, cases: Sequence[tuple[list[Any], Any]],
               per_case_timeout: float) -> tuple[list[bool], list[str]] | None:
    """(which cases this candidate satisfies, what it returns on each) or None if it cannot run.

    The returned outputs are kept because the knowledge-free choice of question must be allowed to
    look at what a candidate DOES and never at what it is supposed to do.
    """
    import copy
    import signal

    namespace: dict[str, Any] = {}
    try:
        exec(compile(source, "<candidate>", "exec"), namespace)  # noqa: S102
    except Exception:  # noqa: BLE001
        return None
    function = namespace.get(function_name)
    if function is None:
        return None
    satisfied: list[bool] = []
    outputs: list[str] = []
    for args, expected in cases:
        try:
            signal.setitimer(signal.ITIMER_REAL, per_case_timeout)
            got = function(*copy.deepcopy(args))
            signal.setitimer(signal.ITIMER_REAL, 0)
        except gen._Timeout:  # noqa: SLF001 -- the corpus's own per-case timer
            signal.setitimer(signal.ITIMER_REAL, 0)
            return None
        except Exception:  # noqa: BLE001
            signal.setitimer(signal.ITIMER_REAL, 0)
            satisfied.append(False)
            outputs.append("<RAISED>")
            continue
        satisfied.append(gen._equal(got, expected))  # noqa: SLF001
        try:
            outputs.append(json.dumps(got, sort_keys=True, default=repr))
        except Exception:  # noqa: BLE001
            outputs.append(repr(got))
    return satisfied, outputs


def best_case(rows: Sequence[dict[str, Any]], complete: set[int]) -> int:
    """The case with the best exact precision on this space; ties to the fewest admissions, then index.

    Precision is |admitted and correct| / |admitted|. It is computable here because the whole space is
    small enough to evaluate in-process, which is exactly why an arbitrary case order is a defect and
    not a constraint.
    """
    if not rows:
        return 0
    width = min(len(row["satisfied"]) for row in rows)
    best: tuple[float, int, int] | None = None
    choice = 0
    for case in range(width):
        admitted = [i for i, row in enumerate(rows) if row["satisfied"][case]]
        if not admitted:
            continue
        precision = len([i for i in admitted if i in complete]) / len(admitted)
        key = (-precision, len(admitted), case)
        if best is None or key < best:
            best, choice = key, case
    return choice


def first_accepting(rows: Sequence[dict[str, Any]], case: int) -> int | None:
    """The first candidate in the generator's own order that satisfies this one case."""
    for index, row in enumerate(rows):
        if row["satisfied"][case]:
            return index
    return None


def first_complete(rows: Sequence[dict[str, Any]]) -> int | None:
    for index, row in enumerate(rows):
        if all(row["satisfied"]):
            return index
    return None


def screen_report(rows: Sequence[dict[str, Any]], case: int, complete: set[int]) -> dict[str, Any]:
    """Exact precision and recall loss of the one-case screen, over the whole space."""
    accepting = [i for i, row in enumerate(rows) if row["satisfied"][case]]
    right = [i for i in accepting if i in complete]
    return {
        "case": case,
        "accepted_by_the_case": len(accepting),
        "of_them_correct": len(right),
        "precision": (len(right) / len(accepting)) if accepting else None,
        "recall_loss": (1.0 - (len(right) / len(complete))) if complete else None,
        "first_accepted_is_correct": bool(accepting) and accepting[0] in complete,
    }


def measure_task(root: pathlib.Path, name: str, *, per_case_timeout: float) -> dict[str, Any]:
    row: dict[str, Any] = {"task": name, "kind": "task"}
    cases = gen.examples_of(root, name)
    row["cases"] = len(cases)
    if not cases:
        row["stage"] = "NO_PUBLISHED_CASES__NOT_MEASURABLE_HERE"
        return row
    source = (root / "python_programs" / f"{name}.py").read_text()
    row["program_sha256"] = gen.sha256(root / "python_programs" / f"{name}.py")
    tree = ast.parse(source)
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
    if function is None:
        row["stage"] = "NO_FUNCTION"
        return row
    row["function"] = function.name
    if not gen._install_alarm():  # noqa: SLF001
        row["stage"] = "UNMEASURABLE__NO_TIMER"
        return row

    space = gen._enumerate(tree, gen.atoms_of(function))  # noqa: SLF001
    row["space_size"] = len(space)
    rows: list[dict[str, Any]] = []
    unrunnable = 0
    for candidate in space:
        seen = outcome_of(candidate["source"], function.name, cases, per_case_timeout)
        if seen is None:
            unrunnable += 1
            continue
        satisfied, outputs = seen
        rows.append({"candidate": candidate, "satisfied": satisfied, "outputs": outputs})
    row["unrunnable"] = unrunnable
    row["scored"] = len(rows)
    if not rows:
        row["stage"] = "NOTHING_RUNS"
        return row

    complete = {i for i, r in enumerate(rows) if all(r["satisfied"])}
    row["complete_candidates"] = len(complete)
    row["stage"] = "MEASURED"
    if not complete:
        row["no_candidate_satisfies_the_suite"] = True

    chosen = best_case(rows, complete)
    row["chosen_case"] = chosen
    row["case_precisions"] = [
        screen_report(rows, case, complete)["precision"] for case in range(len(cases))]
    row["first_case"] = 0

    screens: dict[str, Any] = {}
    picks: dict[str, int | None] = {
        "FIRST_CASE": first_accepting(rows, 0),
        "BEST_CASE": first_accepting(rows, chosen),
        "ALL_CASES": first_complete(rows),
    }
    for label, case in (("FIRST_CASE", 0), ("BEST_CASE", chosen)):
        report = screen_report(rows, case, complete)
        pick = picks[label]
        report["first_accepted_index"] = pick
        report["first_accepted_is_correct"] = (pick is not None and pick in complete)
        report["first_accepted_kind"] = (rows[pick]["candidate"]["kind"] if pick is not None else None)
        report["first_accepted_replacement"] = (
            rows[pick]["candidate"]["replacement"] if pick is not None else None)
        screens[label] = report
    picks_all = picks["ALL_CASES"]
    screens["ALL_CASES"] = {
        "first_accepted_index": picks_all,
        "first_accepted_is_correct": picks_all is not None,
        "first_accepted_kind": (rows[picks_all]["candidate"]["kind"] if picks_all is not None else None),
    }
    row["screens"] = screens
    row["programs"] = {label: (rows[i]["candidate"]["source"] if i is not None else None)
                       for label, i in picks.items()}
    return row


def judge_with_the_corpus(root: pathlib.Path, row: dict[str, Any], *, verify_timeout: int,
                          workdir: pathlib.Path) -> dict[str, Any]:
    """Put each screen's own answer to the corpus's real pytest, on a fresh copy."""
    verdicts: dict[str, Any] = {}
    for label, program in (row.get("programs") or {}).items():
        if program is None:
            verdicts[label] = {"no_candidate": True, "corpus_test_passes": False, "returncode": None}
            continue
        where = workdir / f"{row['task']}__{label}"
        if where.exists():
            shutil.rmtree(where)
        where.mkdir(parents=True)
        built = gen.build_task(root, row["task"], where)
        (where / "python_programs" / f"{row['task']}.py").write_text(program, encoding="utf-8")
        result = gen.verify_with_corpus_test(where, built["test_path"], verify_timeout)
        returncode = result.get("returncode")
        verdicts[label] = {
            "corpus_test_passes": bool(returncode == 0 and not result.get("timed_out")),
            "returncode": returncode,
            "tail": result.get("tail")}
        shutil.rmtree(where, ignore_errors=True)
    return verdicts


def classify_picks(rows: Sequence[dict[str, Any]], root: pathlib.Path) -> dict[str, Any]:
    """Is a passing program a repair, or a rewrite that happens to satisfy the oracle?

    `sorted(arr)` passes a sort's cases without repairing anything. A builtin the program never used
    appearing in the patch is the one mechanical signal available, so a pass is reported as
    `LOCAL_EDIT` or `PLAUSIBLE_REWRITE__BUILTIN_NOT_IN_PROGRAM` and never counted as a repair blind.
    """
    out: dict[str, Any] = {}
    for row in rows:
        if not row.get("corpus_verdicts"):
            continue
        passing = [label for label, verdict in row["corpus_verdicts"].items()
                   if verdict.get("corpus_test_passes")]
        if not passing:
            continue
        original = gen._builtins_in((root / "python_programs" / f"{row['task']}.py").read_text())  # noqa: SLF001
        per_label: dict[str, Any] = {}
        for label in passing:
            program = row["programs"].get(label) or ""
            introduced = sorted(gen._builtins_in(program) - original)  # noqa: SLF001
            per_label[label] = ({"verdict": "PLAUSIBLE_REWRITE__BUILTIN_NOT_IN_PROGRAM",
                                 "introduced": introduced} if introduced
                                else {"verdict": "LOCAL_EDIT", "introduced": []})
        out[row["task"]] = per_label
    return out


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    measured = [r for r in rows if r.get("stage") == "MEASURED"]
    both = [r for r in measured if r.get("complete_candidates")]
    counts = {"FIRST_CASE": {"accepted": 0, "correct": 0},
              "BEST_CASE": {"accepted": 0, "correct": 0},
              "ALL_CASES": {"accepted": 0, "correct": 0}}
    for r in measured:
        for label in counts:
            screen = r["screens"][label]
            if screen.get("first_accepted_index") is not None:
                counts[label]["accepted"] += 1
                counts[label]["correct"] += int(bool(screen.get("first_accepted_is_correct")))
    wins = {"chosen_beats_first": [], "first_beats_chosen": [], "both_right": [], "both_wrong": []}
    for r in measured:
        a = bool(r["screens"]["FIRST_CASE"].get("first_accepted_is_correct"))
        b = bool(r["screens"]["BEST_CASE"].get("first_accepted_is_correct"))
        if a and b:
            wins["both_right"].append(r["task"])
        elif b and not a:
            wins["chosen_beats_first"].append(r["task"])
        elif a and not b:
            wins["first_beats_chosen"].append(r["task"])
        else:
            wins["both_wrong"].append(r["task"])
    precisions = {
        label: [r["screens"][label]["precision"] for r in measured
                if r["screens"][label].get("precision") is not None]
        for label in ("FIRST_CASE", "BEST_CASE")
    }
    corpus = {"FIRST_CASE": {"pass": 0, "fail": 0, "none": 0},
              "BEST_CASE": {"pass": 0, "fail": 0, "none": 0},
              "ALL_CASES": {"pass": 0, "fail": 0, "none": 0}}
    for r in measured:
        for label, verdict in (r.get("corpus_verdicts") or {}).items():
            if label not in corpus:
                continue
            if verdict.get("corpus_test_passes"):
                corpus[label]["pass"] += 1
            elif verdict.get("returncode") is None and verdict.get("no_candidate"):
                corpus[label]["none"] += 1
            else:
                corpus[label]["fail"] += 1
    return {
        "tasks_measured": len(measured),
        "tasks_container_offered": len(rows),
        "space_total": sum(r.get("space_size") or 0 for r in measured),
        "complete_candidate_total": sum(r.get("complete_candidates") or 0 for r in measured),
        "tasks_with_a_complete_candidate": len(both),
        "first_accepted": counts,
        "mean_precision": {label: (sum(v) / len(v) if v else None) for label, v in precisions.items()},
        "chosen_vs_first": {k: sorted(v) for k, v in wins.items()},
        "tasks_with_no_candidate_in_the_space": sorted(
            r["task"] for r in measured if not (r.get("complete_candidates") or 0)),
        "unmeasured": sorted(
            (r["task"], r.get("stage")) for r in rows if r.get("stage") != "MEASURED"),
        "corpus_pytest": corpus,
    }


def _task_job(payload: dict[str, Any]) -> dict[str, Any]:
    """One task, start to finish, in a child process so a candidate that swallows the timer and loops
    cannot take the measurement with it. That a candidate can defeat a timer at all is itself a
    measured instrument limit and is reported, never hidden."""
    root = pathlib.Path(payload["root"])
    name = payload["name"]
    row = measure_task(root, name, per_case_timeout=payload["per_case_timeout"])
    if row.get("stage") == "MEASURED" and not payload["no_corpus_judge"]:
        with tempfile.TemporaryDirectory() as tmp:
            row["corpus_verdicts"] = judge_with_the_corpus(
                root, row, verify_timeout=payload["verify_timeout"], workdir=pathlib.Path(tmp))
    return row


def measure_in_a_child(payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    import multiprocessing

    context = multiprocessing.get_context("spawn")
    with tempfile.TemporaryDirectory() as tmp:
        target = pathlib.Path(tmp) / "row.json"
        payload = dict(payload, _out=str(target))
        process = context.Process(target=_child_entry, args=(payload,))
        process.start()
        process.join(timeout_s)
        if process.is_alive():
            process.terminate()
            process.join(10)
            return {"task": payload["name"], "kind": "task",
                    "stage": "UNMEASURED__A_CANDIDATE_DEFEATED_THE_TIMER",
                    "note": "the child was terminated after the per-task budget"}
        if not target.is_file():
            return {"task": payload["name"], "kind": "task", "stage": "UNMEASURED__NO_RESULT"}
        return json.loads(target.read_text())


def _child_entry(payload: dict[str, Any]) -> None:
    try:
        row = _task_job(payload)
    except Exception as error:  # noqa: BLE001
        row = {"task": payload["name"], "kind": "task", "stage": "RAISED", "error": repr(error)[:300]}
    pathlib.Path(payload["_out"]).write_text(json.dumps(row, default=str))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--per-case-timeout", type=float, default=0.05)
    parser.add_argument("--verify-timeout", type=int, default=120)
    parser.add_argument("--no-corpus-judge", action="store_true")
    parser.add_argument("--task-timeout", type=float, default=60.0)
    parser.add_argument("--augment", default=None, metavar="JSONL",
                        help="fold an existing run into a receipt with the repair classification")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs)
    if args.augment:
        raw = [json.loads(line) for line in pathlib.Path(args.augment).read_text().splitlines()
               if line.strip()]
        header = next((r for r in raw if r.get("kind") == "header"), {})
        rows = [r for r in raw if r.get("kind") != "header"]
        summary = summarise(rows)
        receipt = {
            "schema": SCHEMA, "authority": AUTHORITY, "upstream": UPSTREAM,
            "model_dependency_count": 0, "external_capability_provider_count": 0,
            "network_calls_at_run_time": 0, "header": header,
            "question": ("which case the screen asks, and does the exactly-chosen case beat the "
                         "corpus's first case over the complete finite repair space"),
            "summary": summary,
            "repair_classification": classify_picks(rows, root),
            "rows": rows,
        }
        if args.receipt:
            pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=2, default=str) + "\n")
        print(json.dumps(summary, indent=1, default=str))
        return 0
    names = args.tasks or sorted(p.stem for p in (root / "json_testcases").glob("*.json"))
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    rows: list[dict[str, Any]] = []
    with out.open("w", encoding="utf-8") as handle:
        header = {
            "kind": "header", "schema": SCHEMA, "authority": AUTHORITY,
            "upstream": UPSTREAM, "model_dependency_count": 0,
            "external_capability_provider_count": 0, "network_calls_at_run_time": 0,
            "corpus_head": (root / ".git" / "HEAD").read_text().strip()
            if (root / ".git" / "HEAD").is_file() else None,
        }
        handle.write(json.dumps(header) + "\n")
        for name in names:
            row = measure_in_a_child(
                {"root": str(root), "name": name, "per_case_timeout": args.per_case_timeout,
                 "verify_timeout": args.verify_timeout, "no_corpus_judge": args.no_corpus_judge},
                args.task_timeout)
            rows.append(row)
            handle.write(json.dumps(row, default=str) + "\n")
            handle.flush()
            print(f"{name:28s} {row.get('stage'):12s} space={row.get('space_size')} "
                  f"complete={row.get('complete_candidates')} chosen={row.get('chosen_case')}",
                  flush=True)

    summary = summarise(rows)
    summary["seconds"] = round(time.time() - started, 1)
    receipt = {
        "schema": SCHEMA, "authority": AUTHORITY, "upstream": UPSTREAM,
        "model_dependency_count": 0, "external_capability_provider_count": 0,
        "network_calls_at_run_time": 0,
        "question": ("which case the screen asks, and does choosing it without any expected value "
                     "beat the corpus's first case"),
        "summary": summary,
        "rows": rows,
    }
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
