#!/usr/bin/env python3
"""Before believing a verdict, check that the judge can pass the answer.

THE DEFECT THIS EXISTS FOR
--------------------------
The repair loop judges candidates with the corpus's published `json_testcases` because that is cheap
and in-process, then judges the survivor with the corpus's own `pytest`. Last session measured the
loop losing answers that existed in the space, and this session found why the count was wrong in both
directions: for several published bugs the **cheap judge rejects the corpus's own corrected program**.

    flatten     the reference is a generator; the cheap judge compares a generator object to a list
    hanoi       the reference returns a different container than the data records
    kheapsort   ditto
    sqrt        two of seven cases, under a comparison the corpus itself does not use
    knapsack, levenshtein, longest_common_subsequence
                do not finish inside 50 ms per case, and a timeout was recorded as "does not run"

Every one of those references passes the corpus's real `pytest`. So the cheap judge was wrong, not
the programs and not the spaces -- and any capability number computed through it was wrong too.

THE RULE, AND WHY IT IS NOT OPTIONAL
------------------------------------
A judge is admissible for a task only if it **passes the corrected program and fails the defective
one** on that task. Passing the answer is the false-reject test; failing the bug is the false-accept
test. Where a judge fails either, no search, grammar, budget, demonstration or weight can help: the
verdict itself is not a measurement.

This tool runs that check per task and names the cause, because each cause has a different repair:

    GENERATOR_NOT_MATERIALISED   compare the value the corpus's own test compares (`list(x)`)
    TIMEOUT_TOO_SHORT            the reference is exponential; 50 ms is not a verdict
    RAISED                       the reference raises on a case the data supplies
    VALUE_DISAGREES              the data and the answer genuinely differ -- quarantine the task

WHAT IT READS, AND WHAT THAT COSTS IT
-------------------------------------
It reads `correct_python_programs/`, which no solver may see. This is an AUDIT OF THE INSTRUMENT: it
writes no patch, proposes no candidate and registers no capability. Its only output is which judges
may be believed on which tasks.

Authority NONE. Producer-run sandbox. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import ast
import collections
import copy
import json
import pathlib
import re
import shutil
import signal
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import grammar_closed_repair_v1 as gen  # noqa: E402

SCHEMA = "BRAIN_JUDGE_THE_JUDGE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_AUDIT_OF_THE_INSTRUMENT_NOT_A_SOLVER"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"
FAST = 0.05
SLOW = 2.0


class _CaseTimeout(Exception):
    pass


def _on_alarm(signum, frame):  # noqa: ARG001
    raise _CaseTimeout("case")


def _materialise(value: Any, cap: int = 1024) -> Any:
    """What the corpus's own test does where the answer is a generator: take the values out.

    Bounded on purpose. A defective candidate can yield forever, and an unbounded `list(value)` turns
    the judge into the thing it was meant to be judging -- it allocates until the measurement dies.
    The cap is one more than any answer can need to be distinguishable from the expected value.
    """
    import itertools

    if isinstance(value, (str, bytes, list, tuple, dict, set, int, float, bool, type(None))):
        return value
    if hasattr(value, "__iter__"):
        try:
            return list(itertools.islice(iter(value), cap))
        except Exception:  # noqa: BLE001
            return value
    return value


def case_outcomes(source: str, function_name: str, cases: Sequence[tuple[list[Any], Any]],
                  timeout: float, materialise: bool) -> list[dict[str, Any]]:
    """Per case: PASS / FAIL / RAISED / TIMEOUT / NORUN. The source is executed once."""
    signal.signal(signal.SIGALRM, _on_alarm)
    namespace: dict[str, Any] = {}
    try:
        exec(compile(source, "<probe>", "exec"), namespace)  # noqa: S102
    except Exception as error:  # noqa: BLE001
        return [{"outcome": "NORUN", "detail": repr(error)[:120]} for _ in cases]
    function = namespace.get(function_name)
    if function is None:
        return [{"outcome": "NORUN", "detail": "function absent"} for _ in cases]
    outcomes: list[dict[str, Any]] = []
    for args, expected in cases:
        try:
            signal.setitimer(signal.ITIMER_REAL, timeout)
            got = function(*copy.deepcopy(args))
            signal.setitimer(signal.ITIMER_REAL, 0)
        except _CaseTimeout:
            signal.setitimer(signal.ITIMER_REAL, 0)
            outcomes.append({"outcome": "TIMEOUT"})
            continue
        except Exception as error:  # noqa: BLE001
            signal.setitimer(signal.ITIMER_REAL, 0)
            outcomes.append({"outcome": "RAISED", "detail": repr(error)[:120]})
            continue
        cap = (len(expected) + 1) if isinstance(expected, (list, tuple, str)) else 1024
        value = _materialise(got, cap) if materialise else got
        try:
            same = bool(value == expected)
        except Exception:  # noqa: BLE001
            same = False
        outcomes.append({"outcome": "PASS" if same else "FAIL"})
    return outcomes


def real_judge(root: pathlib.Path, name: str, program: str, workdir: pathlib.Path,
               timeout: int) -> dict[str, Any]:
    where = workdir / f"{name}__reference"
    if where.exists():
        shutil.rmtree(where)
    where.mkdir(parents=True)
    built = gen.build_task(root, name, where)
    (where / "python_programs" / f"{name}.py").write_text(program, encoding="utf-8")
    result = gen.verify_with_corpus_test(where, built["test_path"], timeout)
    shutil.rmtree(where, ignore_errors=True)
    return {"corpus_test_passes": bool(result.get("returncode") == 0 and not result.get("timed_out")),
            "returncode": result.get("returncode"), "tail": result.get("tail")}


def _counts(outcomes: Sequence[dict[str, Any]]) -> dict[str, int]:
    return dict(collections.Counter(item["outcome"] for item in outcomes))


def diagnose(cases_out: dict[str, Any], slow_out: dict[str, Any]) -> str:
    """Name the cause, cheapest explanation first: a comparison the corpus does not use, then time."""
    naive = cases_out["naive"]
    if all(item["outcome"] == "PASS" for item in cases_out["materialised"]):
        if not all(item["outcome"] == "PASS" for item in naive):
            return "GENERATOR_NOT_MATERIALISED"
    if any(item["outcome"] == "NORUN" for item in naive):
        return "NORUN"
    fast_timeouts = sum(1 for item in naive if item["outcome"] == "TIMEOUT")
    slow_pass = sum(1 for item in slow_out["materialised"] if item["outcome"] == "PASS")
    if fast_timeouts and slow_pass > sum(1 for item in cases_out["materialised"]
                                         if item["outcome"] == "PASS"):
        return "TIMEOUT_TOO_SHORT"
    if any(item["outcome"] == "RAISED" for item in naive):
        return "RAISED"
    return "VALUE_DISAGREES"


def test_file_normalisation(root: pathlib.Path, name: str) -> dict[str, Any]:
    """Does the corpus's own test file transform the published data before comparing?

    It does: `testdata = [[inp, [tuple(x) for x in out]] for inp, out in testdata]` in hanoi. A judge
    that reads `json_testcases` directly is then comparing the answer to a representation the answer
    never produces -- which is exactly how the cheap judge came to reject correct programs.
    """
    path = root / "python_testcases" / f"test_{name}.py"
    if not path.is_file():
        return {"available": False}
    text = path.read_text()
    loads = len(re.findall(r"testdata\s*=\s*load_json_testcases", text))
    rewrites = [line.strip() for line in text.splitlines()
                if re.match(r"\s*testdata\s*=\s*\[", line)]
    return {"available": True, "loads": loads, "rewrites": rewrites,
            "normalises_the_data": bool(rewrites)}


def audit_task(root: pathlib.Path, name: str, workdir: pathlib.Path, verify_timeout: int) -> dict[str, Any]:
    row: dict[str, Any] = {"task": name, "kind": "task"}
    cases = gen.examples_of(root, name)
    row["cases"] = len(cases)
    defective = (root / "python_programs" / f"{name}.py").read_text()
    row["program_sha256"] = gen.sha256(root / "python_programs" / f"{name}.py")
    reference = (root / "correct_python_programs" / f"{name}.py")
    if not cases or not reference.is_file():
        row["stage"] = "NOT_AUDITABLE__NO_CASES_OR_NO_REFERENCE"
        return row
    row["stage"] = "AUDITED"
    reference_source = reference.read_text()
    function = next((n for n in ast.parse(reference_source).body if isinstance(n, ast.FunctionDef)), None)
    defective_function = next((n for n in ast.parse(defective).body if isinstance(n, ast.FunctionDef)),
                              None)
    if function is None or defective_function is None:
        row["stage"] = "NOT_AUDITABLE__NO_FUNCTION"
        return row

    naive = case_outcomes(reference_source, function.name, cases, FAST, materialise=False)
    materialised = case_outcomes(reference_source, function.name, cases, FAST, materialise=True)
    slow = case_outcomes(reference_source, function.name, cases, SLOW, materialise=True)
    buggy = case_outcomes(defective, defective_function.name, cases, FAST, materialise=True)
    row["reference"] = {"naive": _counts(naive), "materialised": _counts(materialised),
                        "slow": _counts(slow)}
    row["defective"] = {"materialised": _counts(buggy)}
    row["real_judge"] = real_judge(root, name, reference_source, workdir, verify_timeout)
    row["test_file"] = test_file_normalisation(root, name)

    passes_reference = (sum(1 for i in naive if i["outcome"] == "PASS") == len(cases)) or \
                       (sum(1 for i in materialised if i["outcome"] == "PASS") == len(cases))
    fails_defective = sum(1 for i in buggy if i["outcome"] == "PASS") < len(cases)
    row["judge_passes_the_answer"] = passes_reference
    row["naive_judge_passes_the_answer"] = (
        sum(1 for i in naive if i["outcome"] == "PASS") == len(cases))
    row["judge_fails_the_bug"] = fails_defective
    row["judge_is_admissible"] = bool(passes_reference and fails_defective
                                     and row["real_judge"]["corpus_test_passes"])
    if not row["judge_is_admissible"]:
        if not passes_reference:
            row["cause"] = diagnose({"naive": naive, "materialised": materialised},
                                    {"materialised": slow})
        elif not row["real_judge"]["corpus_test_passes"]:
            row["cause"] = "THE_REFERENCE_FAILS_THE_REAL_JUDGE"
        else:
            row["cause"] = "THE_CHEAP_JUDGE_ACCEPTS_THE_DEFECTIVE_PROGRAM"
    best = "slow" if row.get("cause") == "TIMEOUT_TOO_SHORT" else (
        "naive" if row.get("cause") == "GENERATOR_NOT_MATERIALISED" else "materialised")
    row["recommended_comparison"] = ("materialised" if row.get("cause") == "GENERATOR_NOT_MATERIALISED"
                                     else best)
    return row


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    audited = [r for r in rows if r.get("stage") == "AUDITED"]
    causes = collections.Counter(r.get("cause") for r in audited if r.get("cause"))
    inadmissible = sorted(r["task"] for r in audited if not r["judge_is_admissible"])
    return {
        "tasks_offered": len(rows),
        "naive_judge_rejects_the_answer": sorted(
            r["task"] for r in audited if not r.get("naive_judge_passes_the_answer")),
        "naive_rejections_repaired_by_comparison": sorted(
            r["task"] for r in audited
            if not r.get("naive_judge_passes_the_answer") and r.get("judge_passes_the_answer")),
        "test_files_that_transform_the_data": sorted(
            r["task"] for r in audited if (r.get("test_file") or {}).get("normalises_the_data")),
        "tasks_audited": len(audited),
        "judge_admissible": len(audited) - len(inadmissible),
        "judge_inadmissible": len(inadmissible),
        "inadmissible_tasks": inadmissible,
        "causes": dict(sorted(causes.items())),
        "reference_passes_the_real_judge": sum(
            1 for r in audited if r["real_judge"]["corpus_test_passes"]),
        "cheap_judge_rejects_the_answer": sorted(
            r["task"] for r in audited if not r["judge_passes_the_answer"]),
        "cheap_judge_accepts_the_bug": sorted(
            r["task"] for r in audited if not r["judge_fails_the_bug"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--verify-timeout", type=int, default=120)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs)
    names = args.tasks or sorted(p.stem for p in (root / "json_testcases").glob("*.json"))
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp, out.open("w", encoding="utf-8") as handle:
        workdir = pathlib.Path(tmp)
        handle.write(json.dumps({
            "kind": "header", "schema": SCHEMA, "authority": AUTHORITY, "upstream": UPSTREAM,
            "model_dependency_count": 0, "external_capability_provider_count": 0,
            "network_calls_at_run_time": 0,
            "corpus_head": (root / ".git" / "HEAD").read_text().strip()
            if (root / ".git" / "HEAD").is_file() else None}) + "\n")
        for name in names:
            try:
                row = audit_task(root, name, workdir, args.verify_timeout)
            except Exception as error:  # noqa: BLE001
                row = {"task": name, "kind": "task", "stage": "RAISED", "error": repr(error)[:300]}
            rows.append(row)
            handle.write(json.dumps(row, default=str) + "\n")
            handle.flush()
            print(f"{name:26s} {str(row.get('stage')):10s} "
                  f"admissible={'Y' if row.get('judge_is_admissible') else 'n'} "
                  f"cause={row.get('cause', '-')}", flush=True)

    summary = summarise(rows)
    summary["seconds"] = round(time.time() - started, 1)
    receipt = {"schema": SCHEMA, "authority": AUTHORITY, "upstream": UPSTREAM,
               "model_dependency_count": 0, "external_capability_provider_count": 0,
               "network_calls_at_run_time": 0,
               "rule": ("a judge is admissible for a task only if it passes the corpus's corrected "
                        "program and fails its defective one"),
               "summary": summary, "rows": rows}
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
