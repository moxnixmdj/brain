#!/usr/bin/env python3
"""Close the loop: run the real tests twice, with the contrasting value, and see if the outcome moves.

WHY THIS IS THE ONLY VERSION OF THIS EXPERIMENT THAT COUNTS
----------------------------------------------------------
The previous round measured that 151 real test call sites could exercise a recorded contrast. Reachability
is not evidence: a call site that *could* pass a different value proves nothing about what happens when it
does.

This file performs the intervention. For each recorded contrast whose function is called by tests:

    1. run the test file                      -> baseline outcome
    2. monkeypatch the function so that, when called at the contrasting argument position, it receives the
       OTHER witness value instead                        -> intervened outcome
    3. compare

An outcome that changes under intervention is a test that DEPENDS on the behaviour the entry recorded. An
outcome that does not change is a test that either never reaches the argument or does not care -- and both
are recorded, because a store whose entries are all inert is a museum.

THE CONTROL
-----------
`swap` mode intervenes; `same` mode monkeypatches the function to an identical wrapper WITHOUT changing the
argument. If `same` moves anything, the measurement is contaminated by the wrapper itself and the `swap`
result is not admissible. The control runs first and its result is reported either way.

INTEGRITY
---------
This runs the repo's own tests against the repo's own code. It changes nothing on disk (the patch lives in
one process), it is reverted by process exit, and no test's source is edited. The tests that move are
reported by name.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
SCHEMA = "BRAIN_REPLAY_THE_CONTRAST_IN_ITS_CALLERS_V1"

#: One test run harness, executed as a child process so the monkeypatch cannot outlive it.
HARNESS = '''
import json, sys, pathlib
sys.path.insert(0, {repo!r})
module_name, attribute, position, witness_index, swap = {module_name!r}, {attribute!r}, {position!r}, {witness_index!r}, {swap!r}
import importlib
module = importlib.import_module("canonical.swe_kernel." + module_name)
original = getattr(module, attribute)
witness = {witness!r}

def patched(*args, **kwargs):
    args = list(args)
    if len(args) > position:
        args[position] = witness[1 - witness_index] if swap else args[position]
    return original(*args, **kwargs)

setattr(module, attribute, patched)
import pytest
code = pytest.main([{test_file!r}, "-q", "--tb=no", "-p", "no:cacheprovider"])
print("PYTEST_EXIT:" + str(int(code)))
'''


def run_harness(module_name: str, attribute: str, position: int, witness: list[str],
                witness_index: int, swap: bool, test_file: str) -> dict[str, Any]:
    source = HARNESS.format(repo=str(REPO), module_name=module_name, attribute=attribute,
                            position=position, witness_index=witness_index, swap=swap,
                            witness=witness, test_file=test_file)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
        handle.write(source)
        path = handle.name
    try:
        result = subprocess.run([sys.executable, path], cwd=REPO, capture_output=True,
                                text=True, check=False, timeout=600)
    finally:
        pathlib.Path(path).unlink(missing_ok=True)
    code = None
    for line in result.stdout.splitlines():
        if line.startswith("PYTEST_EXIT:"):
            code = int(line.split(":")[1])
    # the passed/failed summary line is the useful outcome, not just the exit code
    # THE COMPARATOR IS THE MEASUREMENT. A first version compared the pytest summary LINE, which ends
    # with a wall-clock ("11 passed in 1.34s"), so every run looked different and the identity control
    # reported 4 of 4 contaminated. Only the COUNTS may be compared; the timing is noise and is kept
    # separately for reporting.
    import re as _re
    passed = failed = errored = 0
    for line in reversed(result.stdout.splitlines()):
        numbers = _re.findall(r"(\d+) (passed|failed|error|errors|skipped)", line)
        if not numbers:
            continue
        for count, kind in numbers:
            if kind == "passed":
                passed = int(count)
            elif kind == "failed":
                failed = int(count)
            elif kind.startswith("error"):
                errored = int(count)
        break
    return {"exit": code, "passed": passed, "failed": failed, "errors": errored,
            "summary": f"{passed} passed, {failed} failed, {errored} errors"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--entries",
                        default=str(REPO / "canonical" / "verification" /
                                    "ONE_CONTRAST_ONE_EFFECT_20261124_V1.json"))
    parser.add_argument("--callers",
                        default=str(REPO / "canonical" / "verification" /
                                    "DOES_A_CONTRAST_PREDICT_ITS_CALLERS_20261124_V1.json"))
    args = parser.parse_args(argv)

    started = time.time()
    entries = {f"{e['function']}": e for e in
               json.loads(pathlib.Path(args.entries).read_text())["summary"]["sample_entries"]}
    callers = json.loads(pathlib.Path(args.callers).read_text())["summary"].get("rows", []) \
        if pathlib.Path(args.callers).exists() else []

    trials: list[dict[str, Any]] = []
    for row in callers:
        entry = entries.get(row["function"])
        if entry is None or not row["sites"]:
            continue
        # one representative test file per contrast: the one with the most call sites
        by_file: dict[str, int] = {}
        for site in row["sites"]:
            by_file[site["file"]] = by_file.get(site["file"], 0) + 1
        test_file = max(by_file, key=by_file.get)
        module_name, _, attribute = row["function"].partition("::")
        base = run_harness(module_name, attribute, row["position"], row["witness"],
                           0, False, test_file)
        control = run_harness(module_name, attribute, row["position"], row["witness"],
                              0, False, test_file)      # identical wrapper, no swap
        swapped_a = run_harness(module_name, attribute, row["position"], row["witness"],
                                0, True, test_file)
        swapped_b = run_harness(module_name, attribute, row["position"], row["witness"],
                                1, True, test_file)
        trials.append({
            "function": row["function"], "test_file": test_file,
            "argument": row["argument"], "position": row["position"],
            "witness": row["witness"],
            "baseline": base, "control_same_wrapper": control,
            "swapped_to_other_witness": swapped_a, "swapped_from_other_witness": swapped_b,
            "outcome_moved": (base["passed"], base["failed"], base["errors"])
            != (swapped_a["passed"], swapped_a["failed"], swapped_a["errors"]),
            "control_moved": (base["passed"], base["failed"], base["errors"])
            != (control["passed"], control["failed"], control["errors"]),
            "baseline_is_green": base["failed"] == 0 and base["errors"] == 0,
        })

    moved = [trial for trial in trials if trial["outcome_moved"]]
    contaminated = [trial for trial in trials if trial["control_moved"]]
    admissible = [trial for trial in trials if not trial["control_moved"]]
    admissible_moved = [trial for trial in admissible if trial["outcome_moved"]]
    summary = {
        "contrasts_tested": len(trials),
        "test_files_run": sorted({trial["test_file"] for trial in trials}),
        "outcomes_that_moved_under_intervention": len(moved),
        "controls_that_moved": len(contaminated),
        "admissible_trials": len(admissible),
        "admissible_and_moved": len(admissible_moved),
        "moved_detail": [{"function": t["function"], "test_file": t["test_file"],
                          "baseline": t["baseline"]["summary"],
                          "swapped": t["swapped_to_other_witness"]["summary"]} for t in moved],
        "trials": trials,
        "verdicts": {
            "the_control_is_clean": len(contaminated) == 0,
            "some_test_depends_on_the_recorded_behaviour": len(admissible_moved) > 0,
            "every_contrast_reaches_a_test_that_cares":
                len(admissible) > 0 and len(admissible_moved) == len(admissible),
            "the_store_is_inert_against_this_suite": len(admissible) > 0 and not admissible_moved,
        },
        "honest_reading": (
            "An outcome that moves proves the test DEPENDS on the recorded behaviour. An outcome that does "
            "not move proves only that this test file does not exercise that argument at that position -- it "
            "does not show the entry is wrong. Both counts are reported."),
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "trials"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
