#!/usr/bin/env python3
"""Whether a task's own text says what a small fix is written with, and which line it changes.

Why this exists
---------------
Measured 2026-11-12 (canonical/verification/SMALL_PASSING_PATCH_PLACE_SWEBENCH_VERIFIED_20261112_V1.json):
with the function to change GIVEN, the lists built in this tree hold a small test-passing repair
within the first 200 candidates for 16 of 80 real tasks. A piece taken out is reached (14 of the 23
tasks that have one). A small piece put in is not (0 of 46), though the piece is small (three
nodes in the middle) and its names stand in the file. Those lists are ordered by what fixes of
OTHER programs looked like. Nothing in them says what a fix of THIS task is written with.

Doing a similar task after having seen one needs two things that come from different places: the
SHAPE of the change, which other tasks can teach (take a piece out; put a keyword into a call), and
the CONTENT, which only the new task has (which keyword, which name). A task comes with a text.
Before a list is built that takes its content from that text, this asks what costs no test run:

  for the small passing patches of the 80 tasks, does the issue text name what the patch brings
  in, how many other things does it name, and does it point at the line that is changed?

What is counted
---------------
  wanted leaves    the names and constants the changed statement holds after the patch and did
                   not hold before
  the pool         every name and constant the issue text mentions that the program could supply
                   (the changed files hold it, or it is a Python builtin), the most mentioned
                   first, then the first mentioned
  at hand          nothing is wanted; or only 0, 1, 2, True, False, None, ''; or the constant next
                   to the one replaced; or every wanted leaf is in the pool -- then its place there
  the line         where the changed line stands among the lines of the definition when they are
                   ordered by the names on them that the issue mentions, a name weighing one over
                   the number of lines that hold it; ties from the top
  quoted           the changed line as it was, or as the patch leaves it, stands in the issue text

and the same with ANOTHER task's issue text (the task 40 further on in the sorted list), which is
what the counts would be if the text said nothing about the task.

Nothing here runs a program, a test or a model. It reads texts. A mention is a whole word that is
the same, letter for letter; a text that describes a thing without naming it does not count, so
"at hand" is a floor of what a reader of the text could take from it, and a ceiling of what a list
built on whole-word mentions could.

What was expected and the rule were written here before anything was counted: EXPECTED below.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import collections
import datetime
import difflib
import hashlib
import json
import keyword
import pathlib
import re
import statistics
import sys
import time
import warnings
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import fix_shape_v1 as fix_shape  # noqa: E402
from canonical.tools import passing_patch_shape_measure_v1 as passing  # noqa: E402
from canonical.tools import small_passing_patch_place_measure_v1 as place  # noqa: E402

SCHEMA = "BRAIN_FIX_CONTENT_IN_TASK_TEXT_V1"
PLACE_RECORD = ROOT / "canonical" / "verification" / "SMALL_PASSING_PATCH_PLACE_SWEBENCH_VERIFIED_20261112_V1.json"
STATEMENTS = ("hyang0129/onlycodes", "7548222e5f33b4e760b3cbeb193e5403f8e2e6cc", "problems/swe/swebench-verified")
SECOND_COPY = ("Junjie4/distillation", "5475dd3f75b23e203a48c066653e76b5b3e8ef43", "dataset")
BUDGET = place.BUDGET
FIRST_OF_THE_POOL = 10          # a wanted leaf further down the pool than this does not count as at hand for the rule
FIRST_LINES = (1, 3, 5, 10)
OTHER_TASK = 40                 # the control: the issue text of the task this many further on in the sorted list
SHORTEST_QUOTE = 8              # characters without blanks; a shorter line would be "quoted" by chance
SHORTEST_STRING = 3             # a string constant shorter than this is not looked for in the text

NOTHING, SMALL, POINTED, FURTHER, NOT_POINTED = ("nothing wanted", "small constants only", "pointed to, among the first of the pool",
                                                 "pointed to, further down the pool", "not pointed to")
CLASSES = (NOTHING, SMALL, POINTED, FURTHER, NOT_POINTED)
AT_HAND = (NOTHING, SMALL, POINTED)

EXPECTED: dict[str, Any] = {
    "written": "2026-11-12 about 22:17 UTC, before anything was counted. Seen by then: one issue text (django__django-11066, which quotes the line "
               "and the keyword), the published figure that a third of resolved Verified tasks have the solution outlined in the issue "
               "(arXiv 2410.06992), and the shapes and needs of the 159 patches from the earlier record. No pool, no place of any line.",
    "tasks of the 55 that only put in or exchange and that no list reaches within 200, with the content of a small passing patch at hand": [16, 40],
    "the same with another task's issue text": [3, 16],
    "tasks of the 46 with a put-in passing patch for which what one of those brings in is at hand or further down the pool": [20, 38],
    "median size of the pool": [10, 60],
    "median share of the names of the definition that the issue text mentions": [0.15, 0.5],
    "tasks of 80 whose changed line is among the first 5 lines of the definition in the order the issue text gives": [20, 50],
    "tasks of 80 for which the changed line as it was is quoted in the issue text": [5, 25],
    "rule": "The earlier rule asks for a small passing patch within the first 200 candidates for 40 of the 80 tasks before a repair run on real "
            "projects is built; 16 are there. Take the 55 tasks whose small passing patches all put something in or exchange a leaf and that no "
            "list here reaches within 200. If for at least 24 of them the content of a small passing patch is at hand (so that 16 + 24 = 40 can be "
            "reached in the best case), a list that takes its content from the task text is the next thing to build, and to count the same way: "
            "the place of the same patches, the same 200. If for fewer than 12, the task text does not hold what small fixes are written with, and "
            "such a list is not built. From 12 to 23: undecided; it is not built on this count alone. Whatever the number, the same count with "
            "another task's text must come out clearly lower, or the count says nothing about the text.",
}

_WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_KEYWORDS = frozenset(keyword.kwlist)
_SMALL_CONSTANTS = frozenset(leaf for leaf in fix_shape._FREE if leaf[0] == "constant")  # 0, 1, 2, True, False, None, ''
_BUILTIN_NAMES = frozenset(("name", name) for name in dir(builtins))


# --------------------------------------------------------------------------- #
# the issue texts
# --------------------------------------------------------------------------- #
def statement_of(yaml_text: str) -> str | None:
    """The problem statement out of one task file of the first copy. Two ways of writing occur there:
    one line in double quotes (read as JSON, which it is), and single quotes over several lines
    (the doubled quote undone; the folding of lines is not, which moves no word)."""
    lines = yaml_text.split("\n")
    for at, line in enumerate(lines):
        if not line.startswith("problem_statement:"):
            continue
        rest = line[len("problem_statement:"):].strip()
        if rest.startswith('"'):
            return json.loads(rest)
        if rest.startswith("'"):
            taken = [rest[1:]]
            for more in lines[at + 1:]:
                if re.match(r"^[A-Za-z_]+:", more):
                    break
                taken.append(more.strip())
            text = "\n".join(taken).rstrip()
            return (text[:-1] if text.endswith("'") else text).replace("''", "'")
        return rest
    return None


def statements(directory: pathlib.Path, tasks: Sequence[str]) -> dict[str, str]:
    out = {}
    for task in tasks:
        path = directory / f"{task}.yaml"
        text = statement_of(path.read_text(encoding="utf-8")) if path.exists() else None
        if text is not None:
            out[task] = text
    return out


def copies_agree(first: Mapping[str, str], second_directory: pathlib.Path | None) -> dict[str, int]:
    """How many of the texts stand in the second copy too, and for how many the words are the same in the same order."""
    both = same = 0
    if second_directory is not None:
        for task, text in first.items():
            path = second_directory / f"{task}.json"
            if not path.exists():
                continue
            both += 1
            same += _WORD.findall(json.loads(path.read_text(encoding="utf-8")).get("problem_statement") or "") == _WORD.findall(text)
    return {"in_both_copies": both, "the_same_words_in_the_same_order": same}


# --------------------------------------------------------------------------- #
# what a text mentions
# --------------------------------------------------------------------------- #
class Text:
    """An issue text and what it mentions: whole words, numbers standing alone, strings as written."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.first: dict[str, int] = {}
        self.times: collections.Counter = collections.Counter()
        for found in _WORD.finditer(text):
            self.first.setdefault(found.group(), found.start())
            self.times[found.group()] += 1
        self.squeezed = squeezed(text)

    def mentions(self, leaf: tuple[str, ...]) -> tuple[int, int]:
        """(how often, where first) the text mentions a name or a constant; (0, -1) when it does not."""
        if leaf[0] == "name":
            return (self.times[leaf[1]], self.first[leaf[1]]) if leaf[1] in self.first else (0, -1)
        try:
            value = ast.literal_eval(leaf[2])
        except (ValueError, SyntaxError, MemoryError, RecursionError):
            return 0, -1
        if isinstance(value, str):
            if len(value) < SHORTEST_STRING or value not in self.text:
                return 0, -1
            return self.text.count(value), self.text.index(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            hits = [found.start() for found in re.finditer(r"(?<![\w.])" + re.escape(repr(value)) + r"(?![\w.])", self.text)]
            return (len(hits), hits[0]) if hits else (0, -1)
        return 0, -1


def squeezed(text: str) -> str:
    """Without blanks, and with one kind of quote: how a line is looked for in a text."""
    return "".join(text.split()).replace('"', "'")


def pool_of(text: Text, could_supply: set[tuple[str, ...]]) -> list[tuple[str, ...]]:
    """Every leaf the text mentions that the program could supply, the most mentioned first, then the first mentioned."""
    found = []
    for leaf in could_supply - _SMALL_CONSTANTS:
        times, first = text.mentions(leaf)
        if times:
            found.append((-times, first, leaf))
    return [leaf for _, _, leaf in sorted(found)]


# --------------------------------------------------------------------------- #
# what one patch brings in, and whether it is at hand
# --------------------------------------------------------------------------- #
def _parsed(text: str) -> ast.Module:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ast.parse(text)


def wanted_leaves(before: str, after: str) -> set[tuple[str, ...]]:
    """The names and constants the changed statements hold after and did not hold before."""
    found = fix_shape.descend(_parsed(before), _parsed(after))
    if found["block"] is None:
        return set()
    _, left_before, left_after = fix_shape.window(*found["block"])
    return fix_shape.atoms(left_after) - fix_shape.atoms(left_before)


def at_hand(wanted: set[tuple[str, ...]], pool: Sequence[tuple[str, ...]], next_to_it: bool = False) -> tuple[str, int | None]:
    """(which of CLASSES, the place in the pool of the wanted leaf that stands furthest down it)."""
    if not wanted:
        return NOTHING, None
    rest = wanted - _SMALL_CONSTANTS
    if not rest or next_to_it:
        return SMALL, None
    where = {leaf: at for at, leaf in enumerate(pool, 1)}
    if not all(leaf in where for leaf in rest):
        return NOT_POINTED, None
    furthest = max(where[leaf] for leaf in rest)
    return (POINTED if furthest <= FIRST_OF_THE_POOL else FURTHER), furthest


# --------------------------------------------------------------------------- #
# the line
# --------------------------------------------------------------------------- #
def _is_only_a_string(line: str) -> bool:
    return line.lstrip()[:1] in ("'", '"')


def weights(lines: Sequence[str], text: Text) -> list[float]:
    """For each line, the names on it that the text mentions, each weighing one over the number of lines that hold it.
    A line that is only a string (documentation) weighs nothing."""
    on = [set() if _is_only_a_string(line) else set(_WORD.findall(line)) - _KEYWORDS for line in lines]
    holding = collections.Counter(word for words in on for word in words)
    return [sum(1.0 / holding[word] for word in words if word in text.first) for words in on]


def changed_lines(before: Sequence[str], after: Sequence[str]) -> tuple[list[int], list[str], list[str]]:
    """(the lines of `before` that are changed -- for lines only put in, the line before and the line
    after the gap --, those lines as they were, the lines that are new)."""
    at, were, new = [], [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, list(before), list(after), autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if i1 < i2:
            at.extend(range(i1, i2))
            were.extend(before[i1:i2])
        else:
            at.extend(index for index in (i1 - 1, i1) if 0 <= index < len(before))
        new.extend(after[j1:j2])
    return sorted(set(at)), were, new


def place_of_line(order: Sequence[float], changed: Sequence[int]) -> int | None:
    """The best place of a changed line when the lines are ordered by weight, the heaviest first, ties from the top."""
    best = None
    for index in changed:
        here = 1 + sum(1 for other, weight in enumerate(order) if weight > order[index] or (weight == order[index] and other < index))
        best = here if best is None else min(best, here)
    return best


def is_quoted(lines: Sequence[str], text: Text) -> bool:
    return any(len(squeezed(line)) >= SHORTEST_QUOTE and squeezed(line) in text.squeezed for line in lines)


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #
def held_by(record: Mapping[str, Any]) -> set[tuple[str, ...]]:
    """What the files the expert changed are written with, as they were."""
    out: set[tuple[str, ...]] = set()
    for row in record.get("files", []):
        if row.get("is_test") or not row.get("is_python") or row.get("before") is None:
            continue
        try:
            out |= fix_shape.atoms(_parsed(row["before"]))
        except (SyntaxError, ValueError, RecursionError):
            continue
    return out


def of_task(patches: Sequence[Mapping[str, Any]], held: set[tuple[str, ...]], issue: str) -> dict[str, Any]:
    """What the issue text gives for one task: per patch what is at hand, the best of them, the pool, the line."""
    text = Text(issue)
    pool = pool_of(text, held | _BUILTIN_NAMES)
    rows = []
    for patch in patches:
        before = place.normal(patch["before"])
        wanted = wanted_leaves(before, patch["wanted"])
        level, furthest = at_hand(wanted, pool, patch.get("needs") == fix_shape.NEXT_TO_IT)
        lines_before, lines_after = before.split("\n"), patch["wanted"].split("\n")
        changed, were, new = changed_lines(lines_before, lines_after)
        names = {leaf[1] for leaf in fix_shape.atoms(_parsed(before)) if leaf[0] == "name"}
        rows.append({
            "shape": patch["shape"], "class": level, "place_in_the_pool": furthest, "wanted": len(wanted),
            "wanted_and_mentioned": sum(1 for leaf in wanted - _SMALL_CONSTANTS if text.mentions(leaf)[0]),
            "wanted_not_small": len(wanted - _SMALL_CONSTANTS),
            "lines": len(lines_before), "place_of_the_line": place_of_line(weights(lines_before, text), changed),
            "place_of_the_line_from_the_top": min(changed) + 1 if changed else None,
            "line_as_it_was_quoted": is_quoted(were, text), "line_as_patched_quoted": is_quoted(new, text),
            "names_of_the_definition": len(names), "names_of_the_definition_mentioned": sum(1 for name in names if name in text.first),
        })
    best = min(rows, key=lambda row: (CLASSES.index(row["class"]), row["place_in_the_pool"] or 0, row["place_of_the_line"] or 10 ** 6))
    return {"patches": rows, "best": best, "pool": len(pool), "words_of_the_text": sum(text.times.values()),
            "names_held": sum(1 for leaf in held if leaf[0] == "name")}


# --------------------------------------------------------------------------- #
# all of them
# --------------------------------------------------------------------------- #
def _best_of(rows: Sequence[Mapping[str, Any]], shape: str | None = None) -> Mapping[str, Any] | None:
    mine = [row for row in rows if shape is None or row["shape"] == shape]
    if not mine:
        return None
    return min(mine, key=lambda row: (CLASSES.index(row["class"]), row["place_in_the_pool"] or 0))


def _median(values: Sequence[float]) -> float | None:
    values = [value for value in values if value is not None]
    return round(statistics.median(values), 3) if values else None


def summarise(per_task: Mapping[str, Mapping[str, Any]], reached_before: Mapping[str, bool], only_put_in_or_exchange: Sequence[str]) -> dict[str, Any]:
    """The counts over the tasks. `reached_before`: whether the earlier lists hold a small passing patch
    of the task within the budget. `only_put_in_or_exchange`: the tasks none of whose patches takes a piece out."""
    tasks = sorted(per_task)
    by_class = collections.Counter(per_task[task]["best"]["class"] for task in tasks)
    asked = [task for task in only_put_in_or_exchange if task in per_task and not reached_before.get(task)]
    by_shape = {}
    for shape in (fix_shape.PUT_IN, fix_shape.LEAF, fix_shape.TAKEN_OUT):
        best = [found for found in (_best_of(per_task[task]["patches"], shape) for task in tasks) if found is not None]
        by_shape[shape] = {"tasks_with_such_a_passing_patch": len(best), **{name: sum(1 for row in best if row["class"] == name) for name in CLASSES}}
    lines = [per_task[task]["best"] for task in tasks]
    line_places = [min((row["place_of_the_line"] for row in per_task[task]["patches"] if row["place_of_the_line"] is not None), default=None) for task in tasks]
    from_the_top = [min((row["place_of_the_line_from_the_top"] for row in per_task[task]["patches"] if row["place_of_the_line_from_the_top"] is not None), default=None)
                    for task in tasks]
    shares = [row["names_of_the_definition_mentioned"] / row["names_of_the_definition"] for row in lines if row["names_of_the_definition"]]
    wanted_total = sum(row["wanted_not_small"] for task in tasks for row in per_task[task]["patches"])
    wanted_mentioned = sum(row["wanted_and_mentioned"] for task in tasks for row in per_task[task]["patches"])
    return {
        "tasks": len(tasks), "tasks_by_what_is_at_hand_for_the_best_patch": {name: by_class[name] for name in CLASSES},
        "tasks_that_only_put_in_or_exchange_and_were_not_reached": len(asked),
        "of_those_with_the_content_at_hand": sum(1 for task in asked if per_task[task]["best"]["class"] in AT_HAND),
        "of_those_by_class": {name: sum(1 for task in asked if per_task[task]["best"]["class"] == name) for name in CLASSES},
        "by_shape_of_the_passing_patch": by_shape,
        "wanted_leaves_that_are_not_small_constants": wanted_total, "of_them_mentioned_in_the_issue_text": wanted_mentioned,
        "median_size_of_the_pool": _median([per_task[task]["pool"] for task in tasks]),
        "median_names_the_changed_files_hold": _median([per_task[task]["names_held"] for task in tasks]),
        "median_names_of_the_definition": _median([row["names_of_the_definition"] for row in lines]),
        "median_share_of_the_names_of_the_definition_mentioned": _median(shares),
        "median_words_of_the_issue_text": _median([per_task[task]["words_of_the_text"] for task in tasks]),
        "median_lines_of_the_definition": _median([row["lines"] for row in lines]),
        "tasks_whose_changed_line_is_among_the_first": {str(n): sum(1 for value in line_places if value is not None and value <= n) for n in FIRST_LINES},
        "the_same_counted_from_the_top_of_the_definition": {str(n): sum(1 for value in from_the_top if value is not None and value <= n) for n in FIRST_LINES},
        "tasks_with_the_line_as_it_was_quoted": sum(1 for task in tasks if any(row["line_as_it_was_quoted"] for row in per_task[task]["patches"])),
        "tasks_with_the_line_as_patched_quoted": sum(1 for task in tasks if any(row["line_as_patched_quoted"] for row in per_task[task]["patches"])),
    }


def rule(at_hand_count: int, with_another_text: int) -> dict[str, Any]:
    verdict = ("build the list that takes its content from the task text, and count it the same way" if at_hand_count >= 24
               else "the task text does not hold it: such a list is not built" if at_hand_count < 12
               else "undecided: not built on this count alone")
    return {"tasks_with_the_content_at_hand": at_hand_count, "the_same_with_another_tasks_text": with_another_text,
            "the_text_says_something_about_its_task": with_another_text < at_hand_count, "verdict": verdict}


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/fix_content_in_task_text_measure_v1.py", "canonical/tools/small_passing_patch_place_measure_v1.py",
             "canonical/tools/passing_patch_shape_measure_v1.py", "canonical/runtime/fix_shape_v1.py", "canonical/runtime/take_out_v1.py",
             "canonical/runtime/edit_kind_learning_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cache-dir", required=True, type=pathlib.Path, help="the verdicts and patches, as passing_patch_shape_measure_v1.py --fetch kept them")
    parser.add_argument("--pull-requests-dir", required=True, type=pathlib.Path)
    parser.add_argument("--statements-dir", required=True, type=pathlib.Path, help=f"{STATEMENTS[2]} of github.com/{STATEMENTS[0]} at {STATEMENTS[1]}")
    parser.add_argument("--second-copy-dir", type=pathlib.Path, help=f"{SECOND_COPY[2]} of github.com/{SECOND_COPY[0]} at {SECOND_COPY[1]}")
    parser.add_argument("--place-record", type=pathlib.Path, default=PLACE_RECORD)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    started = time.time()
    say = lambda line: print(line, round(time.time() - started, 1), "s", flush=True)  # noqa: E731
    before = json.loads(args.place_record.read_text())["per_task"]
    tasks = sorted(before)
    records = {task: json.loads((args.pull_requests_dir / f"{task}.json").read_text()) for task in tasks}
    then = passing.verdicts(args.cache_dir, passing.WITH_PATCHES)
    with_patches = {name: found for name, found in then.items() if (args.cache_dir / passing.WITH_PATCHES[:10] / name / "all_preds.jsonl").exists()}
    found_targets = place.targets(records, tasks, with_patches, lambda name: passing.patches(args.cache_dir, name))
    say(f"{len(tasks)} tasks, {sum(len(rows) for rows in found_targets.values())} small passing patches")
    issues = statements(args.statements_dir, tasks)
    agree = copies_agree(statements(args.statements_dir, sorted(path.stem for path in args.statements_dir.glob("*.yaml"))), args.second_copy_dir)
    say(f"{len(issues)} issue texts; the two copies: {agree}")

    held = {task: held_by(records[task]) for task in tasks}
    per_task = {task: of_task(found_targets[task], held[task], issues[task]) for task in tasks if found_targets[task] and task in issues}
    other = {task: tasks[(at + OTHER_TASK) % len(tasks)] for at, task in enumerate(tasks)}
    with_another = {task: of_task(found_targets[task], held[task], issues[other[task]]) for task in per_task if other[task] in issues}
    reached = {task: row[2] is not None and row[2] <= BUDGET for task, row in before.items()}
    only = [task for task in tasks if task in per_task and all(row["shape"] != fix_shape.TAKEN_OUT for row in per_task[task]["patches"])]
    summary, control = summarise(per_task, reached, only), summarise(with_another, reached, only)
    record = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expected_before": EXPECTED, "summary": summary, "with_another_tasks_text": control,
        "rule": rule(summary["of_those_with_the_content_at_hand"], control["of_those_with_the_content_at_hand"]),
        "the_two_copies_of_the_issue_texts": agree, "issue_texts_from": list(STATEMENTS), "second_copy": list(SECOND_COPY),
        "tasks_reached_before_within_the_budget": sum(1 for task in tasks if reached[task]),
        "per_task": per_task, "experiments_commit": passing.WITH_PATCHES, "submissions_with_patches": len(with_patches),
        "model_calls": 0, "programs_run": 0, "tests_run": 0, "code_sha256": code_sha256(), "seconds": round(time.time() - started, 1),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("WROTE", args.out, record["seconds"], "s", flush=True)
    print(json.dumps({"rule": record["rule"], "summary": summary, "control": {key: control[key] for key in (
        "of_those_with_the_content_at_hand", "tasks_by_what_is_at_hand_for_the_best_patch", "tasks_whose_changed_line_is_among_the_first",
        "tasks_with_the_line_as_it_was_quoted", "median_size_of_the_pool")}}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
