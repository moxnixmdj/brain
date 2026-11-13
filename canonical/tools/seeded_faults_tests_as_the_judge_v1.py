#!/usr/bin/env python3
"""Seeded faults: does a wrong version of the reading of a test run, or of the count under the tasks' own tests, get past the tests?

Why this exists
---------------
canonical/tools/seeded_faults_function_found_v1.py made such a round for the function-finding organ.
This is the round for canonical/runtime/tests_as_the_judge_v1.py and
canonical/tools/candidate_under_the_tasks_tests_measure_v1.py, made with the same code: each fault
below is one piece of text replaced by a wrong one in a COPY of the tree's canonical/runtime and
canonical/tools; the two test files are run on the copy; a fault is caught when a test fails.

These two files decide what counts as "resolved". A fault here that the tests let through would be
a count that is wrong and looks right, so the faults are the ones that would flatter the count (a
failed test read as passed, a broken old test not held against a candidate, a candidate helped by
the one before it) as well as the ones that would starve it.

Left out of the run, for the reasons the two earlier rounds give: the test that compares the files'
hashes with the record's (it fails for every changed file whatever the change is), the test that
reads this round's own result out of the record (it cannot pass before the round is made), and the
test that every fault's text stands once in its file (it fails as soon as ANY fault is seeded).
The tests that read the record's hashes through another key are left out for the first reason.

A fault that gets past is a place where the tests do not pin the behaviour down. It is reported,
not hidden: see `survived` in the output.

    python3 -B canonical/tools/seeded_faults_tests_as_the_judge_v1.py --work-dir /tmp/mut --out /tmp/mut/judge.json
"""
from __future__ import annotations

import pathlib
import sys
from typing import Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import seeded_faults_function_found_v1 as base  # noqa: E402

ORGAN = "canonical/runtime/tests_as_the_judge_v1.py"
MEASURE = "canonical/tools/candidate_under_the_tasks_tests_measure_v1.py"
_TESTS_OF_THE_MEASURE = "canonical/tests/test_candidate_under_the_tasks_tests_measure_v1.py"
TESTS = ("canonical/tests/test_tests_as_the_judge_v1.py", _TESTS_OF_THE_MEASURE)
LEFT_OUT = (f"{_TESTS_OF_THE_MEASURE}::test_the_record_was_made_by_the_code_in_the_tree",
            f"{_TESTS_OF_THE_MEASURE}::test_the_record_names_the_commit_that_held_the_expectations_before_any_candidate_was_run",
            f"{_TESTS_OF_THE_MEASURE}::test_the_record_says_how_many_seeded_faults_the_tests_caught",
            f"{_TESTS_OF_THE_MEASURE}::test_the_seeded_faults_are_each_one_piece_of_text_that_stands_once")
RECORDS = ("CANDIDATE_UNDER_THE_TASKS_TESTS_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json", "FILE_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json",
           "FUNCTION_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json", "PASSING_PATCH_SHAPE_SWEBENCH_VERIFIED_20261112_V1.json",
           "SMALL_PASSING_PATCH_PLACE_SWEBENCH_VERIFIED_20261112_V1.json")

_WORSE = "_WORSE = {ERROR: 3, FAILED: 3, SKIPPED: 2, PASSED: 1}"
_PASSING = "return [name for name in names if found.get(normal(name)) == PASSED]"
_JUDGED = "judged = first + passing(fixed, keep)"
_APART = "return bool(wanted) and len(passing(fixed, wanted)) == len(wanted) and len(passing(base, wanted)) < len(wanted)"
_LEFT_IN = 'if not path or path in tests or not file.get("patch"):'
_LABEL_IF = 'if path.startswith("tests/") and path.endswith(".py"):'
_HELD = '"held": found is not None and least <= found <= most'

# (what the fault is, the file, the text as it is, the wrong text)
FAULTS: tuple[tuple[str, str, str, str], ...] = (
    # the organ: names
    ("a name is cut whatever its last part is", ORGAN, "if found and found.group(3) == found.group(1):", "if found:"),
    ("the older name keeps a dot at its end", ORGAN, 'return f"{found.group(1)} ({found.group(2)[:-1]})"', 'return f"{found.group(1)} ({found.group(2)})"'),
    # the organ: how a test ended
    ("the third way a pass is printed is not read", ORGAN, '_PASS_ENDS = (" ... ok", " ... OK", " ...  OK")', '_PASS_ENDS = (" ... ok", " ... OK")'),
    ("a skipped test counts as passed", ORGAN, 'elif ending.startswith("skipped"):\n                how = SKIPPED', 'elif ending.startswith("skipped"):\n                how = PASSED'),
    ("a failed test counts as passed", ORGAN, 'name, how = line.rsplit(" ... ", 1)[0], FAILED', 'name, how = line.rsplit(" ... ", 1)[0], PASSED'),
    ("a test that ended in an error counts as passed", ORGAN, 'name, how = line.rsplit(" ... ", 1)[0], ERROR', 'name, how = line.rsplit(" ... ", 1)[0], PASSED'),
    ("an expected failure counts as passed", ORGAN, 'elif ending.startswith("expected failure"):\n                how = SKIPPED',
     'elif ending.startswith("expected failure"):\n                how = PASSED'),
    ("an unexpected success counts as passed", ORGAN, 'elif ending.startswith("unexpected success"):\n                how = FAILED',
     'elif ending.startswith("unexpected success"):\n                how = PASSED'),
    ("a name line above a name line is taken for its owner", ORGAN, "owner = above if above is not None and _name_line(name) is None else None", "owner = above"),
    ("a name line stays the owner of the lines after the next", ORGAN, "            above = None\n            if how:", "            if how:"),
    ("a line between a name and a docstring line does not part them", ORGAN, "above = line if _name_line(line) is not None else None",
     "above = line if _name_line(line) is not None else above"),
    ("a bare ok is read with no test waiting", ORGAN, 'elif waiting is not None and line in ("ok", "FAIL", "ERROR"):', 'elif line in ("ok", "FAIL", "ERROR"):'),
    ("a loud test that fails counts as passed", ORGAN, '{"ok": PASSED, "FAIL": FAILED, "ERROR": ERROR}[line]', '{"ok": PASSED, "FAIL": PASSED, "ERROR": ERROR}[line]'),
    ("a loud test that ends in an error counts as passed", ORGAN, '{"ok": PASSED, "FAIL": FAILED, "ERROR": ERROR}[line]', '{"ok": PASSED, "FAIL": FAILED, "ERROR": PASSED}[line]'),
    ("a loud test is forgotten", ORGAN, "waiting = (name, owner)", "waiting = None"),
    ("a loud test loses the name above its docstring line", ORGAN, "waiting = (name, owner)", "waiting = (name, None)"),
    # the organ: the two names of a test with a docstring
    ("the name above a docstring line is kept as Python 3.11 prints it", ORGAN, "found[normal(owner)] = how", "found[owner] = how"),
    ("a test with a docstring is known by the docstring line alone", ORGAN, "            found[normal(owner)] = how\n", ""),
    ("under a shared docstring line the last test wins", ORGAN, "if name not in shared or _WORSE[how] > _WORSE[shared[name]]:", "if True:"),
    ("under a shared docstring line the first test wins", ORGAN, "if name not in shared or _WORSE[how] > _WORSE[shared[name]]:", "if name not in shared:"),
    ("a skipped test does not keep a shared docstring line from passing", ORGAN, _WORSE, "_WORSE = {ERROR: 3, FAILED: 3, SKIPPED: 0, PASSED: 1}"),
    ("a failed test does not keep a shared docstring line from passing", ORGAN, _WORSE, "_WORSE = {ERROR: 3, FAILED: 0, SKIPPED: 2, PASSED: 1}"),
    ("a docstring line takes the place of a test's own name", ORGAN, "found.setdefault(line, how)", "found[line] = how"),
    # the organ: the labels
    ("the older name gives a label without the method", ORGAN, 'label = dotted if found.group(3) == method else f"{dotted}.{method}"', "label = dotted"),
    ("the newer name gives a label with the method twice", ORGAN, 'label = dotted if found.group(3) == method else f"{dotted}.{method}"', 'label = f"{dotted}.{method}"'),
    ("a label is listed as often as it is printed", ORGAN, "            if label not in out.setdefault(key, []):\n                out[key].append(label)",
     "            out.setdefault(key, []).append(label)"),
    ("a docstring line gives no label", ORGAN, "for key in ([normal(owner), name] if owner is not None else [normal(name)]):",
     "for key in ([normal(owner)] if owner is not None else [normal(name)]):"),
    ("a test with a docstring gives a label only under the docstring line", ORGAN, "for key in ([normal(owner), name] if owner is not None else [normal(name)]):",
     "for key in ([name] if owner is not None else [normal(name)]):"),
    # the organ: the run
    ("the first count of a run is taken", ORGAN, "return int(found[-1]) if found else None", "return int(found[0]) if found else None"),
    ("a run of one test is not read", ORGAN, r'_RAN = re.compile(r"^Ran (\d+) tests? in [0-9.]+s\s*$", re.MULTILINE)', r'_RAN = re.compile(r"^Ran (\d+) tests in [0-9.]+s\s*$", re.MULTILINE)'),
    ("a verdict before the count ends the run", ORGAN, "return at is not None and _VERDICT.search(output, at.end()) is not None",
     "return at is not None and _VERDICT.search(output) is not None"),
    ("a run without its count is finished", ORGAN, "return at is not None and _VERDICT.search(output, at.end()) is not None", "return _VERDICT.search(output) is not None"),
    # the organ: the three questions
    ("a name as Python 3.11 prints it is not found", ORGAN, _PASSING, "return [name for name in names if found.get(name) == PASSED]"),
    ("a test that is not there counts as passing", ORGAN, _PASSING, "return [name for name in names if found.get(normal(name), PASSED) == PASSED]"),
    ("a skipped test counts as passing", ORGAN, _PASSING, "return [name for name in names if found.get(normal(name)) in (PASSED, SKIPPED)]"),
    ("every new test must fail without the fix", ORGAN, _APART, "return bool(wanted) and len(passing(fixed, wanted)) == len(wanted) and len(passing(base, wanted)) == 0"),
    ("the tests tell apart whatever the unfixed program does", ORGAN, _APART, "return bool(wanted) and len(passing(fixed, wanted)) == len(wanted)"),
    ("one new test passing with the fix is enough to tell apart", ORGAN, _APART, "return bool(wanted) and len(passing(fixed, wanted)) > 0 and len(passing(base, wanted)) < len(wanted)"),
    ("the tests left out are the ones that pass", ORGAN, "return [name for name in names if name not in kept]", "return [name for name in names if name in kept]"),
    ("a task the fix does not pass here can be resolved", ORGAN, "if not first or len(passing(fixed, first)) != len(first):", "if not first:"),
    ("a task that names no test is resolved by anything", ORGAN, "if not first or len(passing(fixed, first)) != len(first):", "if len(passing(fixed, first)) != len(first):"),
    ("a test that fails even with the fix is held against the candidate", ORGAN, _JUDGED, "judged = first + keep"),
    ("the tests that should keep passing are not looked at", ORGAN, _JUDGED, "judged = first"),
    ("the tests that should start passing are not looked at", ORGAN, _JUDGED, "judged = passing(fixed, keep)"),
    ("as many passing tests as new ones is enough", ORGAN, "return len(passing(candidate, judged)) == len(judged)", "return len(passing(candidate, judged)) >= len(first)"),
    # the measure: the task as it is published
    ("a path is listed as often as the diff names it", MEASURE, "        if path not in out:\n            out.append(path)", "        out.append(path)"),
    ("a diff quoted inside a diff is a file", MEASURE, r'_TOUCHED = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.MULTILINE)', r'_TOUCHED = re.compile(r"diff --git a/(\S+) b/(\S+)$", re.MULTILINE)'),
    ("a Python file outside the tests is a label", MEASURE, _LABEL_IF, 'if path.endswith(".py"):'),
    ("a file of the tests that is not Python is a label", MEASURE, _LABEL_IF, 'if path.startswith("tests/"):'),
    ("a label keeps the tests directory in front", MEASURE, 'label = path[len("tests/"):-len(".py")].replace("/", ".")', 'label = path[:-len(".py")].replace("/", ".")'),
    ("the class is taken for the module", MEASURE, 'module = found.group(1).rsplit(".", 1)[0]', "module = found.group(1)"),
    ("a name as Python 3.11 prints it gives its class as the module", MEASURE, "found = _IN_CLASS.search(judge.normal(name))", "found = _IN_CLASS.search(name)"),
    ("the fix leaves out what the collector calls a test, not what the test patch touches", MEASURE, _LEFT_IN, 'if not path or file.get("is_test") or not file.get("patch"):'),
    ("the files of the test patch are in the fix", MEASURE, _LEFT_IN, 'if not path or not file.get("patch"):'),
    ("a new file of the fix is not said to be new", MEASURE, 'head += ["new file mode 100644", "--- /dev/null", f"+++ b/{path}"]', 'head += ["--- /dev/null", f"+++ b/{path}"]'),
    ("a removed file of the fix is written as a changed one", MEASURE, 'elif status == "removed":', 'elif status == "deleted":'),
    ("a renamed file of the fix is read from its new path", MEASURE, 'status, old = file.get("status"), file.get("previous") or path', 'status, old = file.get("status"), path'),
    ("a file's patch that ends with a line end leaves an empty line in the diff", MEASURE, 'file["patch"].rstrip("\\n") + "\\n")', 'file["patch"] + "\\n")'),
    ("a name as Python 3.11 prints it gives no label for the few", MEASURE, "labels = known.get(judge.normal(name)) or known.get(name)", "labels = known.get(name)"),
    ("a docstring line gives no label for the few", MEASURE, "labels = known.get(judge.normal(name)) or known.get(name)", "labels = known.get(judge.normal(name))"),
    ("a new test that cannot be named is passed over", MEASURE, "        if not labels:\n            return None", "        if not labels:\n            continue"),
    ("no test asked for gives an empty list of labels", MEASURE, "return out or None", "return out"),
    # the measure: the tree and the runs
    ("nothing is fetched", MEASURE, "names = [name for name in wanted if name not in have]", "names = []"),
    ("every file is fetched again", MEASURE, "names = [name for name in wanted if name not in have]", "names = list(wanted)"),
    ("what is still missing after the fetch is not counted", MEASURE, '"still_missing": sum(1 for name in wanted if name not in have)', '"still_missing": 0'),
    ("what was left in the tree stays when another commit is taken", MEASURE, '        _git(tree, "checkout", "-q", "-f", "--detach", commit)\n    _git(tree, "clean", "-fdxq")',
     '        _git(tree, "checkout", "-q", "-f", "--detach", commit)'),
    ("a changed file blocks the next commit", MEASURE, '_git(tree, "checkout", "-q", "-f", "--detach", commit)', '_git(tree, "checkout", "-q", "--detach", commit)'),
    ("an empty diff counts as gone in", MEASURE, "    if not diff.strip():\n        return False", "    if not diff.strip():\n        return True"),
    ("a diff that does not fit counts as gone in", MEASURE, 'text_in=diff, check=False).returncode == 0', 'text_in=diff, check=False).returncode in (0, 1)'),
    ("a candidate stays in the tree for the next one", MEASURE, '    _git(tree, "reset", "-q", "--hard")\n', ""),
    ("a new file of a candidate stays in the tree", MEASURE, '    _git(tree, "clean", "-fdxq")\n    return applied(tree, test_patch)', "    return applied(tree, test_patch)"),
    ("the labels are not handed to the runner", MEASURE, '"--parallel", "1", *labels],', '"--parallel", "1"],'),
    ("the runner does not find the tree's own code", MEASURE, '"PYTHONPATH": str(tree)', '"PYTHONPATH": ""'),
    ("a run that is stopped is not said to be", MEASURE, "        stopped = True\n", "        stopped = False\n"),
    ("only the runner is stopped, not what it started", MEASURE, "start_new_session=True", "start_new_session=False"),
    ("a file that does not parse counts as Python", MEASURE, "    except (SyntaxError, ValueError):\n        return False", "    except (SyntaxError, ValueError):\n        return True"),
    # the measure: one candidate
    ("a candidate that does not parse is run", MEASURE, "    if not parses(text):\n        row[\"does_not_parse\"] = True\n        return row", "    if False:\n        return row"),
    ("the candidate is not written into the tree", MEASURE, '    (tree / path).write_bytes(text.encode("utf-8"))\n', ""),
    ("the whole module is run for every candidate", MEASURE, '        if row["start_passing"] < len(first):\n            return row', "        if False:\n            return row"),
    ("a candidate that passes the new tests alone resolves without the whole run", MEASURE, '        if row["start_passing"] < len(first):\n            return row',
     '        if row["start_passing"] < len(first):\n            return row\n        row["resolves"] = True\n        return row'),
    ("a candidate that breaks an old test resolves", MEASURE, "resolves=judge.resolves(found, fixed, first, keep))", 'resolves=read["start_passing"] == len(first))'),
    ("the old tests wanted of a candidate are all of them, failing with the fix or not", MEASURE, "    kept = judge.passing(fixed, keep)\n", "    kept = list(keep)\n"),
    # the measure: one task
    ("the labels are never taken from the tests' names", MEASURE, "labels = labels_of(test_patch) or modules_named(first + keep)", "labels = labels_of(test_patch)"),
    ("the labels are always taken from the tests' names", MEASURE, "labels = labels_of(test_patch) or modules_named(first + keep)", "labels = modules_named(first + keep)"),
    ("a task whose fix does not go in is judged", MEASURE, "    if not applied(tree, fix):\n        return ended(\"the expert's fix did not go in\")", "    applied(tree, fix)"),
    ("a task whose test patch does not go in is judged", MEASURE, '    if not applied(tree, test_patch):\n        return ended("the test patch did not go in")', "    applied(tree, test_patch)"),
    ("a run that never got to its summary is not told from a failing test", MEASURE, '    if not row["with_the_fix"]["finished"]:', "    if False:"),
    ("stopped for time and ended before its summary are swapped", MEASURE, '("was stopped for time" if got["stopped"] else "ended before its summary")',
     '("ended before its summary" if got["stopped"] else "was stopped for time")'),
    ("a task whose new test fails even with the fix is not told from one the tests cannot tell apart", MEASURE, '    if row["with_the_fix"]["start_passing"] < len(first):', "    if False:"),
    ("a task whose new test passes without the fix is judged", MEASURE, "    if not judge.tells_apart(base, fixed, first):", "    if False:"),
    ("the tests that fail even with the fix are not counted", MEASURE, 'row["left_out"] = len(judge.left_out(fixed, keep))', 'row["left_out"] = 0'),
    ("the new tests are never run alone", MEASURE, '    few = few_of(got["output"], first)\n', "    few = None\n"),
    ("new tests that fail when run alone are run alone all the same", MEASURE, "        if not stands:\n            few = None\n", ""),
    ("a second candidate of a file takes the first one's verdict", MEASURE, 'key = (candidate["path"], hashlib.sha256(candidate["text"].encode("utf-8")).hexdigest())',
     'key = (candidate["path"], "")'),
    ("a candidate seen before is run again", MEASURE, "        if key not in seen:\n", "        if True:\n"),
    ("the places are counted from nothing", MEASURE, 'row["candidates"].append({"place": at, **said})', 'row["candidates"].append({"place": at - 1, **said})'),
    ("the other task's candidate is listed among the task's own", MEASURE, "        if other is not None and at == len(candidates) + 1:", "        if False:"),
    # the measure: the candidates
    ("the other task's candidate is made from the files this task's text finds", MEASURE, "in_order=finder.order(documents, other_text))[:1])", "in_order=finder.order(documents, text))[:1])"),
    ("the task's candidates are made from the other task's text", MEASURE, "mine = written(finder.candidates(documents, source_of, text, in_order=finder.order(documents, text)))",
     "mine = written(finder.candidates(documents, source_of, other_text, in_order=finder.order(documents, other_text)))"),
    ("a candidate is the function alone, not the file with it", MEASURE, '"text": pointer.written_into(source_of(path), function, program)}', '"text": program}'),
    # the measure: the counts
    ("the first candidate counts as the first that resolves", MEASURE, 'for candidate in row.get("candidates") or () if candidate.get("resolves")), None)',
     'for candidate in row.get("candidates") or ()), None)'),
    ("one submission counts the first five", MEASURE, "one = sorted(task for task, at in places.items() if at == 1)", "one = sorted(task for task, at in places.items() if at is not None and at <= 5)"),
    ("a judged task without a candidate is among the counted", MEASURE, 'counted = {task: row for task, row in judged.items() if row.get("candidates_made")}', "counted = dict(judged)"),
    ("a task that is not judged is among the judged", MEASURE, 'judged = {task: row for task, row in rows.items() if row.get("judged")}', "judged = dict(rows)"),
    ("a recorded place stands when any candidate resolves", MEASURE, '(standing if there is not None and there.get("resolves") else failing).append(task)',
     "(standing if first_resolving(rows[task]) is not None else failing).append(task)"),
    ("a recorded place of a task that is not judged counts as failing", MEASURE, "        if task not in judged:\n            unjudged.append(task)\n            continue\n", ""),
    ("a candidate that resolves is counted among those that break an old test", MEASURE, 'if candidate.get("whole_run") and not candidate.get("resolves"))', 'if candidate.get("whole_run"))'),
    ("every other-text candidate that was run counts as resolving", MEASURE, 'sum(1 for other in others if other.get("resolves"))', "len(others)"),
    ("the tasks not in the earlier record are the ones in it", MEASURE, '"within_twenty__resolved_and_not_in_the_earlier_record": sum(1 for task in within if task not in recorded)',
     '"within_twenty__resolved_and_not_in_the_earlier_record": sum(1 for task in within if task in recorded)'),
    ("within a rank leaves the rank itself out", MEASURE, "if at is not None and at <= rank)", "if at is not None and at < rank)"),
    ("every task counts as judged in its version", MEASURE, 'mine["judged"] += 1 if task in judged else 0', 'mine["judged"] += 1'),
    ("the reasons are listed with the rarest first", MEASURE, "key=lambda item: -item[1]))", "key=lambda item: item[1]))"),
    ("the tests left out are counted in the tasks that are not judged too", MEASURE, 'sum(row.get("left_out") or 0 for row in judged.values())', 'sum(row.get("left_out") or 0 for row in rows.values())'),
    ("the old tests are counted in the tasks that are not judged too", MEASURE, 'sum(row.get("keep_passing") or 0 for row in judged.values())', 'sum(row.get("keep_passing") or 0 for row in rows.values())'),
    ("the seconds are those of the judged tasks alone", MEASURE, 'round(sum(row.get("seconds") or 0 for row in rows.values()), 1)', 'round(sum(row.get("seconds") or 0 for row in judged.values()), 1)'),
    # the measure: the expectations and the rule
    ("the ends of a range are not counted in", MEASURE, _HELD, '"held": found is not None and least < found < most'),
    ("a count that is not there holds", MEASURE, _HELD, '"held": found is None or least <= found <= most'),
    ("half of the tasks judged is too few", MEASURE, "    if judged_share < 0.5:", "    if judged_share <= 0.5:"),
    ("the first twenty resolving no more still counts as a gain for choosing", MEASURE, "    if within > one:", "    if within >= one:"),
    ("choosing is said to be worth all the tasks within twenty", MEASURE, "is worth at most {within - one} task(s) here", "is worth at most {within} task(s) here"),
    ("the earlier record is said to have counted too many when it did not", MEASURE, "    if failing:\n", "    if not failing:\n"),
    ("another task's text passing is not said", MEASURE, "    if other:\n", "    if False:\n"),
    ("the recorded places are of every project", MEASURE, 'if task.startswith(PROJECT + "-") and row.get("place") is not None}', 'if row.get("place") is not None}'),
    # the measure: the whole count
    ("a pull request record with an error is counted from", MEASURE, 'if records[task].get("error") or any(', "if any("),
    ("a pull request record with a file that was not fetched is counted from", MEASURE, 'or any(file.get("fetch_error") for file in records[task].get("files") or ())]', "]"),
    ("the tasks without candidates are judged first", MEASURE, 'key=lambda task: (not made[task]["candidates"], int(task.rsplit("-", 1)[1]))', 'key=lambda task: (bool(made[task]["candidates"]), int(task.rsplit("-", 1)[1]))'),
    ("a task judged before the stop is judged again", MEASURE, "        if task not in per_task:\n            waiting.put(task)", "        waiting.put(task)"),
    ("the other task's candidate is run for a task with no candidate of its own", MEASURE, 'made[task]["another_tasks_text"] if made[task]["candidates"] else None)',
     'made[task]["another_tasks_text"])'),
    ("with no candidates asked for the candidates are made all the same", MEASURE, "    if not args.no_candidates:\n", "    if True:\n"),
    ("the tasks of the record are not in the order of their numbers", MEASURE, 'tasks.sort(key=lambda task: int(task.rsplit("-", 1)[1]))', "tasks.sort()"),
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
