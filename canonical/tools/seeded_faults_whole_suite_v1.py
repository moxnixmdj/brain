#!/usr/bin/env python3
"""Seeded faults: does a wrong version of the whole-suite check get past its tests?

Why this exists
---------------
canonical/tools/resolving_candidate_under_the_whole_suite_measure_v1.py says of a candidate the
benchmark's tests accept whether it KEEPS THE WHOLE SUITE or breaks a test elsewhere. A fault there
that the tests let through would clear a candidate that breaks something, or blame one for what this
machine does. The tool was mended twice after its first push, the second time for a fault its tests
had not seen (a test that fails only through a subtest), so its tests are put to the same trial as
the others': each fault below is one piece of text replaced by a wrong one in a COPY of the tree's
canonical/runtime and canonical/tools; the tool's test file is run on the copy; a fault is caught
when a test fails. The round is made with the code of canonical/tools/seeded_faults_function_found_v1.py.

Left out of the run: the test that compares the files' hashes with the record's (it fails for every
changed file whatever the change is), the test that reads this round's own result out of the record,
and the test that every fault's text stands once in its file (it fails as soon as ANY fault is seeded).

A fault that gets past is a place where the tests do not pin the behaviour down. It is reported,
not hidden: see `survived` in the output.

    python3 -B canonical/tools/seeded_faults_whole_suite_v1.py --work-dir /tmp/mut --out /tmp/mut/whole.json
"""
from __future__ import annotations

import pathlib
import sys
from typing import Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import seeded_faults_function_found_v1 as base  # noqa: E402

MEASURE = "canonical/tools/resolving_candidate_under_the_whole_suite_measure_v1.py"
_TESTS = "canonical/tests/test_resolving_candidate_under_the_whole_suite_measure_v1.py"
TESTS = (_TESTS,)
LEFT_OUT = (f"{_TESTS}::test_the_record_was_made_by_the_code_in_the_tree",
            f"{_TESTS}::test_the_record_says_how_many_seeded_faults_the_tests_caught",
            f"{_TESTS}::test_the_seeded_faults_are_each_one_piece_of_text_that_stands_once")
RECORDS = ("RESOLVING_CANDIDATE_UNDER_THE_WHOLE_SUITE_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json",
           "CANDIDATE_UNDER_THE_TASKS_TESTS_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json", "FILE_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json",
           "FUNCTION_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json", "PASSING_PATCH_SHAPE_SWEBENCH_VERIFIED_20261112_V1.json",
           "SMALL_PASSING_PATCH_PLACE_SWEBENCH_VERIFIED_20261112_V1.json")

_NOT_PASSING = "return sorted(name for name, how in found.items() if how in (judge.FAILED, judge.ERROR) and _NAME_AND_MORE.match(name))"
_BROKEN = "if how == judge.PASSED and _NAME.match(name) and with_the_candidate.get(name) != judge.PASSED)"
_SAID_BREAKING = "breaking = [row for row in said if not row[\"keeps_the_whole_suite\"]]"

FAULTS: tuple[tuple[str, str, str, str], ...] = (
    # reading two runs against each other
    ("a failing subtest is not taken for a test that did not pass", MEASURE, _NOT_PASSING,
     "return sorted(name for name, how in found.items() if how in (judge.FAILED, judge.ERROR) and _NAME.match(name))"),
    ("an error is not taken for a test that did not pass", MEASURE, _NOT_PASSING,
     "return sorted(name for name, how in found.items() if how in (judge.FAILED,) and _NAME_AND_MORE.match(name))"),
    ("a failure is not taken for a test that did not pass", MEASURE, _NOT_PASSING,
     "return sorted(name for name, how in found.items() if how in (judge.ERROR,) and _NAME_AND_MORE.match(name))"),
    ("a skipped test is taken for a test that did not pass", MEASURE, _NOT_PASSING,
     "return sorted(name for name, how in found.items() if how in (judge.FAILED, judge.ERROR, judge.SKIPPED) and _NAME_AND_MORE.match(name))"),
    ("a docstring's line is taken for a test that did not pass", MEASURE, _NOT_PASSING,
     "return sorted(name for name, how in found.items() if how in (judge.FAILED, judge.ERROR))"),
    ("the module of a test keeps its class", MEASURE, "    module = \".\".join(parts[:-1])\n", "    module = \".\".join(parts)\n"),
    ("the method's name printed once more is taken for the class", MEASURE, "    if parts[-1] == found.group(1):", "    if False:"),
    ("unittest's own name for a module that did not load is run as a module", MEASURE,
     "return None if not module or module.startswith(\"unittest.\") or module == \"unittest\" else module", "return None if not module else module"),
    ("a module that did not load is not run again", MEASURE, "    for module in _DID_NOT_LOAD.findall(printed):\n        out[module] = None\n", ""),
    ("the modules of the tests that did not pass are not run again", MEASURE, "        if module is not None:\n            out[module] = None\n", "        pass\n"),
    ("a test that passes with the candidate counts as broken", MEASURE, _BROKEN, "if how == judge.PASSED and _NAME.match(name))"),
    ("a test that fails with the fix too counts as broken", MEASURE, _BROKEN, "if _NAME.match(name) and with_the_candidate.get(name) != judge.PASSED)"),
    ("a test that did not run with the candidate does not count as broken", MEASURE, _BROKEN,
     "if how == judge.PASSED and _NAME.match(name) and with_the_candidate.get(name, judge.PASSED) != judge.PASSED)"),
    ("a test skipped with the candidate does not count as broken", MEASURE, _BROKEN,
     "if how == judge.PASSED and _NAME.match(name) and with_the_candidate.get(name) not in (judge.PASSED, judge.SKIPPED))"),
    ("a docstring's line counts as a broken test of its own", MEASURE, _BROKEN, "if how == judge.PASSED and with_the_candidate.get(name) != judge.PASSED)"),
    ("the fix and the candidate change places", MEASURE, "    names = broken(with_the_fix, with_the_candidate)", "    names = broken(with_the_candidate, with_the_fix)"),
    # the runs
    ("the labels are not handed to the runner", MEASURE, "\"--parallel\", str(processes), *labels],", "\"--parallel\", str(processes)],"),
    ("a run is made on two processes", MEASURE, "def run_whole(tree: pathlib.Path, labels: Sequence[str], seconds: float, processes: int = 1)",
     "def run_whole(tree: pathlib.Path, labels: Sequence[str], seconds: float, processes: int = 2)"),
    ("a run that is stopped is not said to be", MEASURE, "    except subprocess.TimeoutExpired:\n        stopped = True\n", "    except subprocess.TimeoutExpired:\n        stopped = False\n"),
    ("the runner does not find the tree's own code", MEASURE, "\"PYTHONPATH\": str(tree), ", ""),
    ("the passing tests are counted with the docstrings' lines", MEASURE, "\"passing\": sum(1 for name, how in found.items() if how == judge.PASSED and _NAME.match(name))",
     "\"passing\": sum(1 for name, how in found.items() if how == judge.PASSED)"),
    # one candidate
    ("the candidate is not written into the tree", MEASURE, "    (tree / path).write_bytes(text.encode(\"utf-8\"))\n    read = whole_run_from", "    read = whole_run_from"),
    ("the task's tests are not written in", MEASURE, "    if not count.as_the_task_starts(tree, test_patch):\n        raise RuntimeError(\"the test patch did not go in\")\n", ""),
    ("a whole run made before is made again", MEASURE, "    read = whole_run_from is not None and whole_run_from.exists()", "    read = False"),
    ("a whole run is read from a file that is not there", MEASURE, "    read = whole_run_from is not None and whole_run_from.exists()", "    read = whole_run_from is not None"),
    ("the whole run is not kept", MEASURE, "    if keep_output is not None:\n        keep_output.write_text(got[\"output\"], encoding=\"utf-8\")\n", ""),
    ("the whole run is of the task's modules only", MEASURE, "        got = run(tree, [], WHOLE_SECONDS)", "        got = run(tree, [\"store_tests.tests\"], WHOLE_SECONDS)"),
    ("a whole run that did not get to its summary is read all the same", MEASURE, "    if not row[\"whole_run\"][\"finished\"]:", "    if False:"),
    ("stopped for time and ended before its summary are swapped", MEASURE,
     "\"the whole run was stopped for time\" if got[\"stopped\"] else \"the whole run ended before its summary\"",
     "\"the whole run ended before its summary\" if got[\"stopped\"] else \"the whole run was stopped for time\""),
    ("any number of modules is run again", MEASURE, "    if len(modules) > MOST_MODULES_AGAIN:", "    if False:"),
    ("one module fewer than the most is already too many", MEASURE, "    if len(modules) > MOST_MODULES_AGAIN:", "    if len(modules) >= MOST_MODULES_AGAIN:"),
    ("with nothing failing the candidate is not said to keep the suite", MEASURE,
     "    if not modules:\n        row.update(broken_by_the_candidate=[], keeps_the_whole_suite=True)\n        return row\n",
     "    if not modules:\n        row.update(broken_by_the_candidate=[], keeps_the_whole_suite=None)\n        return row\n"),
    ("the second runs are of the whole suite", MEASURE, "    second = run(tree, modules, AGAIN_SECONDS)", "    second = run(tree, [], AGAIN_SECONDS)"),
    ("the run with the fix is made with the candidate still in the tree", MEASURE,
     "    if not count.as_the_task_starts(tree, test_patch) or not count.applied(tree, fix):\n        raise RuntimeError(\"the expert's fix did not go in\")\n", ""),
    ("the fix is written over the candidate without going back", MEASURE,
     "    if not count.as_the_task_starts(tree, test_patch) or not count.applied(tree, fix):", "    if not count.applied(tree, fix):"),
    ("a second run that did not get to its summary is read all the same", MEASURE,
     "    if not (row[\"run_again\"][\"with_the_candidate\"][\"finished\"] and row[\"run_again\"][\"with_the_fix\"][\"finished\"]):", "    if False:"),
    ("only the candidate's second run has to get to its summary", MEASURE,
     "    if not (row[\"run_again\"][\"with_the_candidate\"][\"finished\"] and row[\"run_again\"][\"with_the_fix\"][\"finished\"]):",
     "    if not row[\"run_again\"][\"with_the_candidate\"][\"finished\"]:"),
    ("a candidate that breaks a test is said to keep the suite", MEASURE, "    row.update(broken_by_the_candidate=names, keeps_the_whole_suite=not names)",
     "    row.update(broken_by_the_candidate=names, keeps_the_whole_suite=True)"),
    # all of them
    ("a later resolving candidate is taken for the first", MEASURE, "            firsts.append((task, places[0]))", "            firsts.append((task, places[-1]))"),
    ("a candidate that does not resolve is among the resolving", MEASURE,
     "places = [candidate[\"place\"] for candidate in row.get(\"candidates\") or () if candidate.get(\"resolves\")]",
     "places = [candidate[\"place\"] for candidate in row.get(\"candidates\") or ()]"),
    ("the candidates at place 1 are not run before the rest", MEASURE, "    firsts.sort(key=lambda pair: (pair[1] != 1, int(pair[0].rsplit(\"-\", 1)[1])))",
     "    firsts.sort(key=lambda pair: int(pair[0].rsplit(\"-\", 1)[1]))"),
    ("the tasks are in the order of their names, not their numbers", MEASURE, "    firsts.sort(key=lambda pair: (pair[1] != 1, int(pair[0].rsplit(\"-\", 1)[1])))",
     "    firsts.sort(key=lambda pair: (pair[1] != 1, pair[0]))"),
    ("one submission is every first resolving candidate", MEASURE, "        return [pair for pair in firsts if pair[1] == 1]", "        return firsts"),
    ("the later candidates are run whichever were asked for", MEASURE, "    return firsts + (later if which == \"all\" else [])", "    return firsts + later"),
    ("a candidate of which nothing is said counts as keeping the suite", MEASURE, "        said = [row for row in some if row[\"keeps_the_whole_suite\"] is not None]",
     "        said = list(some)"),
    ("a candidate that keeps the suite counts as breaking a test", MEASURE, _SAID_BREAKING, "breaking = [row for row in said if row[\"keeps_the_whole_suite\"]]"),
    ("one submission is counted over the later candidates at place 1 too", MEASURE, "    one = [row for row in rows if row[\"place\"] == 1 and row[\"first_resolving\"]]",
     "    one = [row for row in rows if row[\"place\"] == 1]"),
    ("one submission is counted over every first resolving candidate", MEASURE, "    one = [row for row in rows if row[\"place\"] == 1 and row[\"first_resolving\"]]",
     "    one = [row for row in rows if row[\"first_resolving\"]]"),
    ("the first resolving are counted over every candidate run", MEASURE, "    first = [row for row in rows if row[\"first_resolving\"]]", "    first = list(rows)"),
    ("a task counts as having a candidate that keeps the suite when its last one does", MEASURE,
     "            tasks[row[\"task\"]] = tasks.get(row[\"task\"], False) or row[\"keeps_the_whole_suite\"]", "            tasks[row[\"task\"]] = row[\"keeps_the_whole_suite\"]"),
    ("the whole runs that got to their summary are all of them", MEASURE,
     "\"whole_runs_that_got_to_their_summary\": sum(1 for row in some if row[\"whole_run\"][\"finished\"]),", "\"whole_runs_that_got_to_their_summary\": len(some),"),
    ("the ends of a range are not counted in", MEASURE, "\"held\": found is not None and low <= found <= high}", "\"held\": found is not None and low < found < high}"),
    ("a count that is not there holds", MEASURE, "\"held\": found is not None and low <= found <= high}", "\"held\": found is None or low <= found <= high}"),
    ("the rule says none breaks when one does", MEASURE, "    if breaking:\n        verdict.append(f\"{breaking} of the {run}", "    if breaking > 1:\n        verdict.append(f\"{breaking} of the {run}"),
    ("the rule does not say when nothing can be said of a candidate", MEASURE, "    if run - breaking - keeping:", "    if False:"),
    ("the rule gives the breaking for the keeping", MEASURE, "one submission that also keeps the whole suite: {keeping}\")", "one submission that also keeps the whole suite: {breaking}\")"),
)


def main(argv: Sequence[str] | None = None) -> int:
    """The round of canonical/tools/seeded_faults_function_found_v1.py, with this file's tests, records and faults."""
    names = ("TESTS", "LEFT_OUT", "RECORDS", "FAULTS")
    kept = {name: getattr(base, name) for name in names}
    for name in names:
        setattr(base, name, globals()[name])
    try:
        return base.main(argv)
    finally:
        for name, value in kept.items():
            setattr(base, name, value)


if __name__ == "__main__":
    raise SystemExit(main())
