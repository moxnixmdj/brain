#!/usr/bin/env python3
"""Seeded faults: does a wrong version of the function-finding organ or of its measure get past the tests?

Why this exists
---------------
Four records of this line of work say that no round of seeded faults was made. This is one, for
canonical/runtime/function_the_task_text_points_at_v1.py and
canonical/tools/function_found_from_task_text_measure_v1.py: each fault below is one piece of text
replaced by a wrong one, in a COPY of the tree's canonical/runtime, canonical/tools and the two
test files; the two test files are run on the copy; a fault is caught when a test fails.

Two tests are left out of the run. The one that compares the files' hashes with the hashes in the
record would fail for every changed file whatever the change is, and so would show nothing about
the other tests. The one that reads this round's own result out of the record cannot pass before
the round has been made.

A fault that gets past is a place where the tests do not pin the behaviour down. It is reported,
not hidden: see `survived` in the output.

    python3 -B canonical/tools/seeded_faults_function_found_v1.py --work-dir /tmp/mut --out /tmp/mut/found.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time
from typing import Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
ORGAN = "canonical/runtime/function_the_task_text_points_at_v1.py"
MEASURE = "canonical/tools/function_found_from_task_text_measure_v1.py"
TESTS = ("canonical/tests/test_function_the_task_text_points_at_v1.py", "canonical/tests/test_function_found_from_task_text_measure_v1.py")
LEFT_OUT = ("canonical/tests/test_function_found_from_task_text_measure_v1.py::test_the_record_was_counted_with_the_files_as_they_are",
            "canonical/tests/test_function_found_from_task_text_measure_v1.py::test_the_record_says_how_many_seeded_faults_the_tests_caught")
RECORDS = ("FUNCTION_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json", "PASSING_PATCH_SHAPE_SWEBENCH_VERIFIED_20261112_V1.json",
           "SMALL_PASSING_PATCH_PLACE_SWEBENCH_VERIFIED_20261112_V1.json")

# (what the fault is, the file, the text as it is, the wrong text)
FAULTS: tuple[tuple[str, str, str, str], ...] = (
    ("the order is the wrong way round", ORGAN, "sorted(zip([-score for score in scores], found))", "sorted(zip([score for score in scores], found))"),
    ("ties go from the bottom", ORGAN, "sorted(zip([-score for score in scores], found))", "sorted(zip([-score for score in scores], found), key=lambda pair: (pair[0], -pair[1].first))"),
    ("the parts of an identifier are not words", ORGAN, "if part != word and len(part) >= SHORTEST_PART", "if False and len(part) >= SHORTEST_PART"),
    ("a part of any length is a word", ORGAN, "if part != word and len(part) >= SHORTEST_PART", "if part != word and len(part) >= 1"),
    ("Python's own words are kept", ORGAN, "        if word in _KEYWORDS:\n            continue", "        if False:\n            continue"),
    ("the class does not count for its methods", ORGAN, 'words(" ".join(function.name.split(".")[:-1]) + "\\n" + ', 'words("" + "\\n" + '),
    ("a function begins at its def, not at its first decorator", ORGAN, "first = min([child.lineno] + [decorator.lineno for decorator in child.decorator_list])", "first = child.lineno"),
    ("a function inside an if or a try is not found", ORGAN, "            elif isinstance(child, ast.stmt):\n                go(child, above)", "            elif False:\n                go(child, above)"),
    ("a class is a function too", ORGAN, "if not isinstance(child, ast.ClassDef):", "if True:"),
    ("one candidate too many for each function", ORGAN, "at_most=of_each))", "at_most=of_each + 1))"),
    ("one function too many gets candidates", ORGAN, "order(source, text)[:functions]", "order(source, text)[:functions + 1]"),
    ("candidates are made from the file's order, not the text's", ORGAN, "for function in order(source, text)[:functions]:", "for function in functions_of(source)[:functions]:"),
    ("the function's last line stays when it is written back", ORGAN, "+ new + lines[function.last:])", "+ new + lines[function.last - 1:])"),
    ("the depth is lost when a function is written back", ORGAN, "new = [depth + line if line.strip() else line for line in new_text.split(\"\\n\")]", "new = [line for line in new_text.split(\"\\n\")]"),
    ("an empty line gets the depth's spaces", ORGAN, "new = [depth + line if line.strip() else line for line in new_text.split(\"\\n\")]", "new = [depth + line for line in new_text.split(\"\\n\")]"),
    ("a function's text is not moved to the margin", ORGAN, 'return textwrap.dedent("\\n".join(source.split("\\n")[function.first - 1:function.last]))', 'return "\\n".join(source.split("\\n")[function.first - 1:function.last])'),
    ("the scorer counts shared words instead of weighing them", ORGAN, "scores = [row[0] if isinstance(row, tuple) else row for row in bm25._bm25_scores(words(text), documents)]",
     "scores = [len(set(words(text)) & set(document)) for document in documents]"),
    ("places are counted from 0", MEASURE, "for at, program in enumerate(made, 1):\n        if program in wanted:", "for at, program in enumerate(made, 0):\n        if program in wanted:"),
    ("the worst function of a task is taken, not the best", MEASURE, "    return min(values) if values else None\n\n\ndef _share", "    return max(values) if values else None\n\n\ndef _share"),
    ("within n means below n", MEASURE, "if value is not None and value <= n) for n in ranks}", "if value is not None and value < n) for n in ranks}"),
    ("the rule asks for seven tenths, not two thirds", MEASURE, "if kept >= 2 / 3", "if kept >= 0.7"),
    ("the rule's lower bound is a half", MEASURE, "if kept < 1 / 3 else", "if kept < 1 / 2 else"),
    ("one task outside the 80 is not enough to say it carries", MEASURE, '"carries_to_tasks_it_was_not_shaped_on": outside > 0}', '"carries_to_tasks_it_was_not_shaped_on": outside > 1}'),
    ("the other text is the task's own", MEASURE, "mine[(mine.index(task) + 1) % len(mine)]", "mine[(mine.index(task) + 0) % len(mine)]"),
    ("a change outside every function counts as a function", MEASURE, "        if not any((function.first, function.last) == span for function in functions[path]):\n            not_one_function += 1",
     "        if False:\n            not_one_function += 1"),
    ("the earlier lists keep their whole 200", MEASURE, "earlier_in_turns[task] <= BUDGET - FIRST]", "earlier_in_turns[task] <= BUDGET]"),
    ("for the lower bound any first function is enough", MEASURE, "if ranks and all(rank == 1 for rank in ranks):", "if ranks and any(rank == 1 for rank in ranks):"),
    ("a patch to a test file counts as a change", MEASURE, 'changed = [row for row in passing.files_of(diff) if not collector.is_test(files.repo, row["path"])]\n    there = [row for row in changed if row["path"].endswith(".py") and row["status"] != "added"]\n    if len(there) != 1 or there[0]["status"] != "modified" or there[0]["path"] not in files.before:\n        return None\n    path',
     'changed = [row for row in passing.files_of(diff)]\n    there = [row for row in changed if row["path"].endswith(".py") and row["status"] != "added"]\n    if len(there) != 1 or there[0]["status"] != "modified" or there[0]["path"] not in files.before:\n        return None\n    path'),
    ("with the file given the other task's text is used", MEASURE, '"file_given": in_the_file(text) if rows else None', '"file_given": in_the_file(other_text) if rows else None'),
    ("the tasks shaped on and the others change places", MEASURE, "inside = [task for task in tasks if task in set(the_80)]\n    outside = [task for task in tasks if task not in set(the_80)]",
     "inside = [task for task in tasks if task not in set(the_80)]\n    outside = [task for task in tasks if task in set(the_80)]"),
    ("the share kept is of all tasks, not of the reached", MEASURE, '"share_kept": _share(len(kept), len(reached)),', '"share_kept": _share(len(kept), len(mine)),'),
    ("the rank from another text is the rank from the own text", MEASURE, '"rank_other_text": spans_other.index(span) + 1,', '"rank_other_text": spans_own.index(span) + 1,'),
    ("from the top is counted from 0", MEASURE, '"from_the_top": [(f.first, f.last) for f in functions[path]].index(span) + 1,', '"from_the_top": [(f.first, f.last) for f in functions[path]].index(span),'),
    ("a task reached only with the file is counted as kept", MEASURE, "kept = [task for task in reached if in_file[task] is not None]", "kept = [task for task in mine if in_file[task] is not None]"),
)


def copy_of_the_tree(work: pathlib.Path) -> None:
    if work.exists():
        shutil.rmtree(work)
    (work / "canonical" / "tests").mkdir(parents=True)
    (work / "canonical" / "verification").mkdir(parents=True)
    for name in ("runtime", "tools"):
        shutil.copytree(ROOT / "canonical" / name, work / "canonical" / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in TESTS:
        shutil.copy(ROOT / name, work / name)
    for name in RECORDS:
        if (ROOT / "canonical" / "verification" / name).exists():
            shutil.copy(ROOT / "canonical" / "verification" / name, work / "canonical" / "verification" / name)
    if (ROOT / "canonical" / "__init__.py").exists():
        shutil.copy(ROOT / "canonical" / "__init__.py", work / "canonical" / "__init__.py")


def tests_fail(work: pathlib.Path) -> tuple[bool, str]:
    """Whether the two test files fail on the copy, and pytest's last line."""
    done = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *[part for name in LEFT_OUT for part in ("--deselect", name)], *TESTS],
                          cwd=work, capture_output=True, text=True, timeout=300)
    lines = [line for line in done.stdout.strip().splitlines() if line.strip()]
    failed = next((line for line in lines if line.startswith("FAILED ")), "")
    return done.returncode != 0, (failed or (lines[-1] if lines else ""))[:200]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    started = time.time()
    copy_of_the_tree(args.work_dir)
    failing, last = tests_fail(args.work_dir)
    if failing:
        print("THE TESTS FAIL ON THE UNCHANGED COPY:", last, flush=True)
        return 2
    print("unchanged copy:", last, flush=True)
    rows = []
    for what, name, old, new in FAULTS:
        path = args.work_dir / name
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            rows.append({"fault": what, "file": name, "caught": None, "by": f"the text to replace stands {text.count(old)} times"})
            print("NOT SEEDED", what, flush=True)
            continue
        path.write_text(text.replace(old, new), encoding="utf-8")
        try:
            caught, by = tests_fail(args.work_dir)
        finally:
            path.write_text(text, encoding="utf-8")
        rows.append({"fault": what, "file": name, "caught": caught, "by": by})
        print("caught  " if caught else "SURVIVED", what, "|", by if caught else "", flush=True)
    seeded = [row for row in rows if row["caught"] is not None]
    out = {"seeded": len(seeded), "caught": sum(1 for row in seeded if row["caught"]),
           "survived": [row["fault"] for row in seeded if not row["caught"]], "not_seeded": [row["fault"] for row in rows if row["caught"] is None],
           "left_out_of_the_run": list(LEFT_OUT), "rows": rows, "seconds": round(time.time() - started, 1)}
    args.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: out[key] for key in ("seeded", "caught", "survived", "not_seeded", "seconds")}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
