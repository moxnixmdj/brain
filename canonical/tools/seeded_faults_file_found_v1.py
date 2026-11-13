#!/usr/bin/env python3
"""Seeded faults: does a wrong version of the file-finding organ or of its measure get past the tests?

Why this exists
---------------
canonical/tools/seeded_faults_function_found_v1.py made such a round for the function-finding organ.
This is the round for canonical/runtime/file_the_task_text_points_at_v1.py and
canonical/tools/file_found_from_task_text_measure_v1.py, made with the same code: each fault below
is one piece of text replaced by a wrong one in a COPY of the tree's canonical/runtime and
canonical/tools; the two test files of the organ and the measure are run on the copy; a fault is
caught when a test fails.

Three tests are left out of the run. Two for the reasons given there: the one that compares the
files' hashes with the hashes in the record fails for every changed file whatever the change is,
and the one that reads this round's own result out of the record cannot pass before the round is
made. The third is the test that every fault's text stands once in its file: it fails as soon as
ANY fault is seeded, because the text is then gone. A first run of this round had it in and came
out as 64 caught of 64, six of them by that test alone; with it left out the six got past.

A fault that gets past is a place where the tests do not pin the behaviour down. It is reported,
not hidden: see `survived` in the output.

    python3 -B canonical/tools/seeded_faults_file_found_v1.py --work-dir /tmp/mut --out /tmp/mut/found.json
"""
from __future__ import annotations

import pathlib
import sys
from typing import Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import seeded_faults_function_found_v1 as base  # noqa: E402

ORGAN = "canonical/runtime/file_the_task_text_points_at_v1.py"
MEASURE = "canonical/tools/file_found_from_task_text_measure_v1.py"
TESTS = ("canonical/tests/test_file_the_task_text_points_at_v1.py", "canonical/tests/test_file_found_from_task_text_measure_v1.py")
LEFT_OUT = ("canonical/tests/test_file_found_from_task_text_measure_v1.py::test_the_record_was_made_by_the_code_in_the_tree",
            "canonical/tests/test_file_found_from_task_text_measure_v1.py::test_the_record_says_how_many_seeded_faults_the_tests_caught",
            "canonical/tests/test_file_found_from_task_text_measure_v1.py::test_the_seeded_faults_are_each_one_piece_of_text_that_stands_once")
RECORDS = ("FILE_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json", "FUNCTION_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json",
           "PASSING_PATCH_SHAPE_SWEBENCH_VERIFIED_20261112_V1.json", "SMALL_PASSING_PATCH_PLACE_SWEBENCH_VERIFIED_20261112_V1.json")

_KEY = "key=lambda path: (-level[path], -found[path], path)"
_LEVEL = "level = {path: named(path, text) if use_names else NOT_NAMED for path in documents}"

# (what the fault is, the file, the text as it is, the wrong text)
FAULTS: tuple[tuple[str, str, str, str], ...] = (
    # the organ: the order of the files
    ("the files are ordered by score the wrong way round", ORGAN, _KEY, "key=lambda path: (-level[path], found[path], path)"),
    ("the files the text names come last", ORGAN, _KEY, "key=lambda path: (level[path], -found[path], path)"),
    ("ties between files go against the path", ORGAN, _KEY, "key=lambda path: (-level[path], -found[path], [-ord(letter) for letter in path])"),
    ("the files the text names are not put first", ORGAN, _LEVEL, "level = {path: NOT_NAMED for path in documents}"),
    ("the names are used even when the caller turns them off", ORGAN, _LEVEL, "level = {path: named(path, text) for path in documents}"),
    # the organ: the words and the score
    ("the words of the path are not in the document", ORGAN, 'out.update(counted(path.replace("/", " ").replace(".", " ")))', "out.update({})"),
    ("a word counts once however often it stands", ORGAN, "out[one] += times", "out[one] += 1"),
    ("k1 is 1.2", ORGAN, "K1, B = 1.5, 0.75", "K1, B = 1.2, 0.75"),
    ("b is 0.5", ORGAN, "K1, B = 1.5, 0.75", "K1, B = 1.5, 0.5"),
    ("the length of a file does not count", ORGAN, "norm = K1 * (1.0 - B + B * lengths[name] / average)", "norm = K1"),
    ("a word that stands in every file weighs as much as a rare one", ORGAN, "math.log(1.0 + (len(names) - held[word] + 0.5) / (held[word] + 0.5))", "1.0"),
    ("how often a word stands in a file does not count", ORGAN, "score += idf * (times * (K1 + 1.0) / (times + norm))", "score += idf"),
    # the organ: how a text names a file
    ("a file name alone counts as written out", ORGAN, "return WRITTEN_OUT if package else FILE_NAME_ONLY", "return WRITTEN_OUT"),
    ("a module path does not name a file", ORGAN, ' or _stands(text, ".".join(last_two), a_name_may_follow_a_dot=not package)', ""),
    ("a path with a directory does not name a file", ORGAN, '_stands(text, "/".join(last_two) + end) or ', ""),
    ("a name that ends a longer name counts", ORGAN, "before_ok = at == 0 or text[at - 1] not in _WORD_CHARS", "before_ok = True"),
    ("a name that begins a longer name counts", ORGAN, "after_ok = end == len(text) or text[end] not in _WORD_CHARS", "after_ok = True"),
    ("a package is named by anything inside it", ORGAN, "a_name_may_follow_a_dot=not package)", "a_name_may_follow_a_dot=True)"),
    ("only the first place a name stands is looked at", ORGAN, "at = text.find(written, at + 1)", "at = -1"),
    ("a package is never named", ORGAN, 'package = parts[-1] == "__init__.py"', "package = False"),
    # the organ: the candidates
    ("the candidates come from the second file", ORGAN, "(order(documents, text) if in_order is None else in_order)[:files_tried]", "(order(documents, text) if in_order is None else in_order)[1:files_tried + 1]"),
    ("an order handed over is not used", ORGAN, "(order(documents, text) if in_order is None else in_order)[:files_tried]", "order(documents, text)[:files_tried]"),
    ("only the first function gets candidates", ORGAN, "range(len(rows))))[:functions]:", "range(len(rows))))[:1]:"),
    ("the functions are ranked the wrong way round", ORGAN, "zip([-score for score in scored], range(len(rows)))", "zip([score for score in scored], range(len(rows)))"),
    ("a function gets every candidate there is", ORGAN, "at_most=of_each)", "at_most=400)"),
    ("the class a method stands in is not among its words", ORGAN,
     'pointer.words(" ".join(function.name.split(".")[:-1]) + "\\n" + "\\n".join(lines[function.first - 1:function.last]))', 'pointer.words("\\n".join(lines[function.first - 1:function.last]))'),
    # the measure: the tree
    ("the tests are listed with the project's files", MEASURE, "(tests_too or not collector.is_test(repository, path))", "True"),
    ("the tests are never listed", MEASURE, "(tests_too or not collector.is_test(repository, path))", "not collector.is_test(repository, path)"),
    ("files that are not Python are listed", MEASURE, 'and path.endswith(".py") and (tests_too', "and (tests_too"),
    ("a file is kept under its name only, whatever its path", MEASURE, "key = (name, path)\n                if key not in kept:", "key = (name, '')\n                if key not in kept:"),
    # the measure: one task
    ("the rank of a file counts from 0", MEASURE, "for at, path in enumerate(order, 1):", "for at, path in enumerate(order, 0):"),
    ("the place of a candidate counts from 0", MEASURE, "in enumerate(made, 1):", "in enumerate(made, 0):"),
    ("the place of the function counts from 0", MEASURE, "enumerate(ranked, 1)", "enumerate(ranked, 0)"),
    ("the right text in another function counts", MEASURE, "if program in targets.get((path, (function.first, function.last)), ()):", "if any(program in texts for texts in targets.values()):"),
    ("the expert's file is ranked by score alone", MEASURE, '"expert": rank_of(in_order, expert),', '"expert": rank_of(by_score, expert),'),
    ("score alone is the order of the organ", MEASURE, "by_score = finder.order(documents, text, use_names=False)", "by_score = finder.order(documents, text)"),
    ("the other text is the task's own", MEASURE, "with_other = finder.order(documents, other_text)", "with_other = finder.order(documents, text)"),
    ("the candidates of the other text are made from the task's own", MEASURE, "finder.candidates(documents, source_of, other_text, in_order=with_other)", "finder.candidates(documents, source_of, text, in_order=with_other)"),
    ("three files are one file", MEASURE, "files_tried=THREE_FILES, in_order=in_order)", "files_tried=1, in_order=in_order)"),
    ("the chain is handed the expert's file", MEASURE, 'row["place"] = place_of(finder.candidates(documents, source_of, text, in_order=in_order), targets)',
     'row["place"] = place_of(finder.candidates(documents, source_of, text, in_order=sorted(expert) + in_order), targets)'),
    ("the function is looked for in the expert's file, wherever it stands", MEASURE, "if targets and in_order and in_order[0] in holding:\n        spans = {span for path, span in targets if path == in_order[0]}\n        ranked = pointer.order(source_of(in_order[0]), text)",
     "if targets and in_order:\n        spans = {span for path, span in targets}\n        ranked = pointer.order(source_of(sorted(holding)[0]), text)"),
    ("a file that holds no passing patch counts as holding one", MEASURE, '"passing": rank_of(in_order, holding) if holding else None,', '"passing": rank_of(in_order, expert),'),
    ("the text in the tree is never compared with the text the collector read", MEASURE, 'row["same_text"] = all(source_of(path) == before[path] for path in expert if path in documents)', 'row["same_text"] = True'),
    ("a function whose span is not a function of the file is a target", MEASURE, "if not any((function.first, function.last) == span for function in functions[path]):\n            continue", "pass"),
    # the measure: added up
    ("among the first 3 is among the first 5", MEASURE, "RANKS = (1, 3, 10)", "RANKS = (1, 5, 10)"),
    ("a share has two places", MEASURE, "return round(count / of, 3) if of else None", "return round(count / of, 2) if of else None"),
    ("a rank equal to the bound is not within it", MEASURE, "value is not None and value <= n)", "value is not None and value < n)"),
    ("a file name alone is not naming the file", MEASURE, 'named = [row for row in rows if row["expert_named"]]', 'named = [row for row in rows if row["expert_named"] == finder.WRITTEN_OUT]'),
    ("by project, the first 3 are the first 10", MEASURE, 'found["among_the_first_3"] += rank is not None and rank <= 3', 'found["among_the_first_3"] += rank is not None and rank <= 10'),
    ("the median is the mean", MEASURE, "statistics.median([row[\"files\"] for row in rows])", "statistics.mean([row[\"files\"] for row in rows])"),
    ("a task reached with another task's text is not counted", MEASURE, 'sum(1 for row in rows if row["place_other_text"] is not None)', "0"),
    ("every task reached counts as reached from the tree only", MEASURE, "sum(1 for task in reached if task not in set(given))", "len(reached)"),
    ("a task reached twice counts twice", MEASURE, "len(set(reached) | set(earlier))", "len(reached) + len(earlier)"),
    ("the earlier lists count with their file anywhere in the order", MEASURE, 'per_task[task]["passing"] == 1]', 'per_task[task]["passing"] is not None]'),
    ("a task reached with the file given that is not among the tasks still counts", MEASURE, "given = [task for task in reached_with_the_file if task in per_task]", "given = list(reached_with_the_file)"),
    # the measure: the rule, the earlier lists, the input
    ("the rule: 6 kept is enough", MEASURE, "if kept >= 7", "if kept >= 6"),
    ("the rule: 4 kept is the limiting step", MEASURE, "if kept <= 3 else", "if kept <= 4 else"),
    ("the rule: a share outside the range still agrees", MEASURE, "share is not None and low <= share <= high", "share is not None"),
    ("the earlier lists: within all 200", MEASURE, "at > BUDGET - FIRST", "at > BUDGET"),
    ("the earlier lists: one small function first is enough", MEASURE, "all(rank == 1 for rank in ranks)", "any(rank == 1 for rank in ranks)"),
    ("the earlier lists: a function that is not small counts", MEASURE, 'if row["small"]]', "]"),
    ("a record without the text of the expert's file is counted", MEASURE, '"files" not in record or any(row.get("fetch_error") for row in record["files"]))', '"files" not in record)'),
    ("fewer submissions than the function record had are counted", MEASURE, "if submissions_with_patches != submissions_then:", "if submissions_with_patches > submissions_then:"),
    ("the base commit is read from the middle of a line", MEASURE, '_BASE = re.compile(r"^base_commit:', '_BASE = re.compile(r"base_commit:'),
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
