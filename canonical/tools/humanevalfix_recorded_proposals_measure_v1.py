#!/usr/bin/env python3
"""What this tree's checking and fix-shape memory add to a language model's proposals, on HumanEvalFix.

No model is called here. The proposals are files other people published: for each HumanEvalFix
bug, the program (or the ten programs) a named language model wrote when asked to fix it. This
tool reads those files and asks, on the 100 bugs that were scored for the edit-kind learner:

  the model alone          its first program, judged by the bug's tests
  the model and the tests  the first of its programs that passes the tests
  the search alone         what the edit-kind learner repaired from the fixes of other bugs
                           (taken from its record, not run again)
  either                   the model's passing program, else the search's repair
  and the model's attempt  where neither passed: the learner's operators applied to the model's
  repaired                 failed programs instead of to the buggy one, the tests choosing

and for every program that passes: whether it is the published fix or answers like it on inputs
the tests do not have. That is what would be measured if a language model stood in this tree as
the proposer with the tree's screen and memory behind it -- measured without putting one there.

Zero model calls. Nothing here gives authority to anything.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import re
import shutil
import sys
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef  # noqa: E402

SCHEMA = "BRAIN_HUMANEVALFIX_RECORDED_PROPOSALS_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ATTEMPTS_REPAIRED = 3             # of the model's failed programs, how many different ones the operators are applied to
BUDGET_PER_ATTEMPT = 300          # candidates run against the tests for each of them
_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


# --------------------------------------------------------------------------- #
# the published proposals
# --------------------------------------------------------------------------- #
def code_of(text: str) -> str:
    """The program in a model's answer: what stands inside the first code fence, or the answer itself."""
    found = _FENCE.search(text or "")
    return (found.group(1) if found else (text or "")).strip("\n") + "\n"


def load_proposals(path: pathlib.Path, bugs: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    """Proposals by bug name. Two layouts are read: one JSON object per line with `task_id` and the
    program under `extracted` (or the answer under `completion`); or one JSON list with, for every
    bug in the benchmark's order, the list of programs."""
    text = path.read_text(encoding="utf-8")
    out: dict[str, list[str]] = {}
    if path.suffix == ".jsonl":
        for line in text.splitlines():
            if line.strip():
                row = json.loads(line)
                out.setdefault(row["task_id"], []).append(code_of(row.get("extracted") or row.get("completion") or ""))
    else:
        rows = json.loads(text)
        if len(rows) != len(bugs):
            raise ValueError(f"{path.name}: {len(rows)} lists of programs for {len(bugs)} bugs")
        for bug, programs in zip(bugs, rows):
            out[bug["name"]] = [code_of(p) for p in programs]
    unknown = sorted(set(out) - {bug["name"] for bug in bugs})
    if unknown:
        raise ValueError(f"{path.name}: proposals for bugs the benchmark does not have: {unknown[:3]}")
    return out


# --------------------------------------------------------------------------- #
# one bug, one model
# --------------------------------------------------------------------------- #
def judged(bug: Mapping[str, Any], program: str, extra: Mapping[str, Any] | None,
           agreement: Callable[..., dict[str, Any] | None] = hef.agreement) -> dict[str, Any]:
    """A program that passes the tests, against the published fix."""
    if kinds.same_program(program, bug["fixed"]):
        return {"is_the_published_fix": True, "right_as_far_as_checked": True}
    compared = agreement(bug, program, extra)
    right = bool(compared and compared.get("inputs_used") and compared["agree"] == compared["inputs_used"])
    return {"is_the_published_fix": False, "right_as_far_as_checked": right, "on_inputs_the_tests_do_not_have": compared}


def one_bug(bug: Mapping[str, Any], programs: Sequence[str], lessons: kinds.Lessons | None, where: pathlib.Path, *,
            extra: Mapping[str, Any] | None = None, attempts: int = ATTEMPTS_REPAIRED, budget: int = BUDGET_PER_ATTEMPT,
            check: Callable[[Sequence[str]], int | None] | None = None, accepted: Callable[[str], bool] | None = None,
            agreement: Callable[..., dict[str, Any] | None] = hef.agreement) -> dict[str, Any]:
    """The model's programs for this bug run against its tests in the order given; where none
    passes, the operators kept from the fixes of OTHER bugs applied to its failed programs."""
    hef.lay_out(bug, where)
    check = check or (lambda texts: hef.screen(where, texts))
    accepted = accepted or (lambda text: hef.accept(bug, text))
    out: dict[str, Any] = {"bug_type": bug["bug_type"], "programs": len(programs)}

    def passes(text: str) -> bool:
        return kinds.is_a_program(text) and check([text]) == 0 and bool(accepted(text))

    verdicts = [passes(text) for text in programs]
    out["programs_that_pass"] = sum(verdicts)
    out["first_program_passes"] = bool(verdicts and verdicts[0])
    first = next((n for n, ok in enumerate(verdicts) if ok), None)
    out["first_that_passes"] = None if first is None else first + 1
    if first is not None:
        out["the_models_program"] = judged(bug, programs[first], extra, agreement)
        return out
    if lessons is None or attempts <= 0:
        return out
    # around the model's attempt: its failed programs, each once, in the order it gave them
    others = [lesson for lesson in lessons.lessons if lesson != bug["name"]]
    tried: list[str] = []
    for text in programs:
        try:
            normal = ast.unparse(ast.parse(text))
        except (SyntaxError, ValueError, RecursionError):
            continue
        if normal in tried:
            continue
        tried.append(normal)
        if len(tried) > attempts:
            break
        bench = hef.Bench(bug, check, accepted)
        rank, program, _ = bench.first_pass(kinds.ranking(lessons.votes(text), only=others), budget)
        out["candidates_run_around_the_models_attempts"] = out.get("candidates_run_around_the_models_attempts", 0) + bench.runs
        if program is not None:
            out["repaired_around_the_models_attempt"] = {"attempt": len(tried), "rank": rank, "lines": hef.changed_lines(text, program),
                                                         **judged(bug, program, extra, agreement)}
            break
    out["attempts_the_operators_were_applied_to"] = min(len(tried), attempts)
    return out


# --------------------------------------------------------------------------- #
# what it came to
# --------------------------------------------------------------------------- #
def search_outcomes(record: Mapping[str, Any], question: str = "all_other_fixes") -> dict[str, dict[str, bool]]:
    """What the edit-kind learner did on each scored bug, from its record: repaired, and right as far as checked."""
    out = {}
    for name, row in record["per_bug"].items():
        if not row.get("usable"):
            continue
        answer = row[question]
        compared = answer.get("on_inputs_the_tests_do_not_have")
        right = bool(answer.get("repaired") and (answer.get("is_the_published_fix")
                                                 or (compared and compared.get("inputs_used") and compared["agree"] == compared["inputs_used"])))
        out[name] = {"repaired": bool(answer.get("repaired")), "right_as_far_as_checked": right}
    return out


def summarise(per_bug: Mapping[str, Mapping[str, Any]], search: Mapping[str, Mapping[str, bool]]) -> dict[str, Any]:
    names = [name for name in per_bug if name in search]
    def count(test: Callable[[str], bool]) -> int:
        return sum(1 for name in names if test(name))
    model = lambda n: per_bug[n]["first_that_passes"] is not None                                # noqa: E731
    model_right = lambda n: model(n) and per_bug[n]["the_models_program"]["right_as_far_as_checked"]  # noqa: E731
    found = lambda n: search[n]["repaired"]                                                      # noqa: E731
    found_right = lambda n: search[n]["right_as_far_as_checked"]                                 # noqa: E731
    around = lambda n: "repaired_around_the_models_attempt" in per_bug[n]                        # noqa: E731
    around_right = lambda n: around(n) and per_bug[n]["repaired_around_the_models_attempt"]["right_as_far_as_checked"]  # noqa: E731
    # what comes out when the model's passing program is taken first, then the search's repair, then the repaired attempt
    either_right = lambda n: model_right(n) if model(n) else found_right(n)                      # noqa: E731
    all_right = lambda n: model_right(n) if model(n) else found_right(n) if found(n) else around_right(n)  # noqa: E731
    out: dict[str, Any] = {
        "bugs": len(names),
        "the_model_alone_first_program": count(lambda n: per_bug[n]["first_program_passes"]),
        "the_model_and_the_tests": {"passes": count(model), "right_as_far_as_checked": count(model_right),
                                    "passes_and_is_wrong_on_an_extra_input": count(lambda n: model(n) and not model_right(n))},
        "the_search_alone": {"passes": count(found), "right_as_far_as_checked": count(found_right)},
        "either": {"passes": count(lambda n: model(n) or found(n)), "right_as_far_as_checked": count(either_right)},
        "bug_by_bug": {"both": count(lambda n: model(n) and found(n)), "the_model_only": count(lambda n: model(n) and not found(n)),
                       "the_search_only": count(lambda n: found(n) and not model(n)), "neither": count(lambda n: not model(n) and not found(n))},
        "the_models_attempt_repaired": {"asked_where_no_program_of_the_model_passed": count(lambda n: not model(n)),
                                        "passes": count(around), "right_as_far_as_checked": count(around_right),
                                        "of_those_where_the_search_had_also_failed": count(lambda n: around(n) and not found(n))},
        "all_three": {"passes": count(lambda n: model(n) or found(n) or around(n)), "right_as_far_as_checked": count(all_right)},
    }
    by_type: dict[str, dict[str, int]] = {}
    for name in names:
        cell = by_type.setdefault(per_bug[name]["bug_type"], {"bugs": 0, "the_model_and_the_tests": 0, "the_search_alone": 0, "either": 0, "all_three": 0})
        cell["bugs"] += 1
        cell["the_model_and_the_tests"] += model(name)
        cell["the_search_alone"] += found(name)
        cell["either"] += model(name) or found(name)
        cell["all_three"] += model(name) or found(name) or around(name)
    out["by_bug_type"] = dict(sorted(by_type.items()))
    return out


def code_sha256() -> dict[str, str]:
    files = ("canonical/runtime/edit_kind_learning_v1.py", "canonical/tools/humanevalfix_edit_kind_transfer_measure_v1.py",
             "canonical/tools/humanevalfix_recorded_proposals_measure_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--humanevalfix", required=True, type=pathlib.Path)
    parser.add_argument("--quixbugs-dir", required=True, type=pathlib.Path)
    parser.add_argument("--extra-inputs", type=pathlib.Path, default=None)
    parser.add_argument("--search-record", type=pathlib.Path, default=ROOT / "canonical/verification/HUMANEVALFIX_EDIT_KIND_TRANSFER_20261111_V1.json")
    parser.add_argument("--proposals", required=True, type=pathlib.Path, help="the published programs of one model")
    parser.add_argument("--model", required=True, help="who wrote them, as its publisher names it")
    parser.add_argument("--published-at", required=True, help="where the file was taken from")
    parser.add_argument("--all-bugs", action="store_true", help="also judge the model's programs on the bugs that were not scored (no search, no repair)")
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    started = time.monotonic()
    bugs = hef.load_bugs(args.humanevalfix)
    proposals = load_proposals(args.proposals, bugs)
    search_record = json.loads(args.search_record.read_text())
    search = search_outcomes(search_record)
    lessons = hef.taught(bugs, hef.quixbugs_lessons(args.quixbugs_dir))
    extra = hef.extra_inputs(args.extra_inputs)
    per_bug: dict[str, Any] = {}
    for bug in bugs:
        scored = bug["name"] in search
        if not scored and not args.all_bugs:
            continue
        where = args.work_dir / bug["name"].replace("/", "_")
        per_bug[bug["name"]] = one_bug(bug, proposals.get(bug["name"], []), lessons if scored else None, where, extra=extra.get(bug["number"]))
        shutil.rmtree(where, ignore_errors=True)
        row = per_bug[bug["name"]]
        print(f"{bug['name']:11s} {'scored' if scored else 'not scored':10s} model first={row['first_program_passes']} any={row['first_that_passes']} "
              f"search={search.get(bug['name'], {}).get('repaired')} around={'repaired_around_the_models_attempt' in row}", flush=True)
    everything = [row for row in per_bug.values()]
    record = {"schema": SCHEMA, "authority": AUTHORITY, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "model": args.model, "published_at": args.published_at, "proposals_sha256": hashlib.sha256(args.proposals.read_bytes()).hexdigest(),
              "model_calls": 0, "attempts_repaired": ATTEMPTS_REPAIRED, "budget_per_attempt": BUDGET_PER_ATTEMPT,
              "search_record": {"path": str(args.search_record.name), "frozen_commit": search_record.get("frozen_commit"),
                                "code_sha256": search_record.get("code_sha256")},
              "code_sha256": code_sha256(),
              "on_every_bug_judged": {"bugs": len(everything), "first_program_passes": sum(1 for r in everything if r["first_program_passes"]),
                                      "some_program_passes": sum(1 for r in everything if r["first_that_passes"] is not None),
                                      "programs": sum(r["programs"] for r in everything), "programs_that_pass": sum(r["programs_that_pass"] for r in everything)},
              "summary": summarise(per_bug, search), "per_bug": per_bug, "seconds": round(time.monotonic() - started, 1)}
    args.out.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({k: record[k] for k in ("on_every_bug_judged", "summary")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
