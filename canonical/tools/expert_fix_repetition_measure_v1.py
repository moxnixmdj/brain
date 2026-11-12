#!/usr/bin/env python3
"""How much of an expert's fix had been seen before, in the expert fixes of OTHER tasks.

The question
------------
"Give it the most advanced coding actions, let it experience each once, and it has learned them."
Experiencing a fix once is enough to REPEAT that fix. Whether it is enough to make the next one
depends on a fact about fixes, not about the learner: how much of the next expert fix is something
already seen in the earlier ones. This tool measures that fact on the expert fixes themselves --
the merged pull requests behind SWE-bench Verified -- with the most generous reading:

  * every fix is cut into its smallest independent PIECES (one changed place each), so a fix in
    five places is five small lessons and five small questions, never one large one;
  * for a piece, every other piece of the same fix is taken as already made, and the function to
    change is given;
  * the learner (canonical/runtime/edit_kind_learning_v1.py, unedited) is shown every piece of
    every OTHER task once, and keeps each at every level of generality it writes -- from "exactly
    this" to "any statement taken out";
  * a piece counts as SEEN BEFORE when an operator kept from another task, applied to the function
    as it stands before the piece, makes exactly the expert's version -- and the count of other
    programs that operator makes of the same function is reported beside it, because nothing but
    a test could tell them apart and the benchmark's tests are hidden from the solver.

No test is run and no task is solved here. "Seen before" is an upper bound on what any memory of
fixes could propose; it is not a repair rate.

Zero model calls. Nothing here gives authority to anything.
"""
from __future__ import annotations

import argparse
import ast
import collections
import copy
import difflib
import hashlib
import json
import pathlib
import re
import sys
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402

SCHEMA = "BRAIN_EXPERT_FIX_REPETITION_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
_IGNORED = ("ctx", "type_comment", "kind")           # what the learner's `key` does not count either
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
CAP = kinds.MAX_CANDIDATES_OF_ONE                     # programs one operator may make of one function: the learner's own limit
HAYSTACKS = (1, 10, 100, CAP)
MADE, TOO_LOOSE, NEVER = "made_exactly", "only_by_an_operator_too_loose_to_apply", "never_seen"
MAX_PIECES_OF_ONE_UNIT = 400                          # a function changed in more places than this is counted, not cut up
REWRITTEN_BELOW = 0.5                                 # a statement or expression with less than this much in common with what it was is one change
OUTSIDE = " (statements outside functions)"
CLASS_LINE = " (class line)"


# --------------------------------------------------------------------------- #
# a fix as the pull request gives it
# --------------------------------------------------------------------------- #
def apply_patch(before: str, patch: str, moved: list[int] | None = None) -> str:
    """The file after the hunks of `patch`. Strict about content: every unchanged and every removed
    line of a hunk has to be in the file, together and in order, or ValueError -- so a file and a
    fix that do not belong together are noticed. Where they stand may differ from what the hunk
    says (the branch moved on before the fix went in): then the nearest place that has exactly
    those lines is taken, and how far it was is added to `moved`."""
    old = before.split("\n")
    out: list[str] = []
    at = 0
    lines = patch.split("\n")
    i = 0
    while i < len(lines):
        if not lines[i] and i == len(lines) - 1:
            break
        header = _HUNK.match(lines[i])
        if not header:
            raise ValueError(f"not a hunk header: {lines[i][:60]!r}")
        start, old_left = int(header.group(1)), int(header.group(2) if header.group(2) is not None else 1)
        new_left = int(header.group(4) if header.group(4) is not None else 1)
        begin = start - 1 if old_left else start
        i += 1
        steps: list[tuple[str, str]] = []
        while old_left or new_left:
            if i >= len(lines):
                raise ValueError("the hunk ends early")
            line = lines[i]
            i += 1
            if line.startswith("\\"):
                continue
            tag, text = (line[0], line[1:]) if line else (" ", "")
            if tag not in " -+":
                raise ValueError(f"unexpected line in a hunk: {line[:60]!r}")
            steps.append((tag, text))
            old_left -= tag in " -"
            new_left -= tag in " +"
            if old_left < 0 or new_left < 0:
                raise ValueError("the hunk has more lines than its header says")
        while i < len(lines) and lines[i].startswith("\\"):
            i += 1
        wanted = [text for tag, text in steps if tag in " -"]
        if begin < at or old[begin:begin + len(wanted)] != wanted:
            places = [k for k in range(at, len(old) - len(wanted) + 1) if old[k:k + len(wanted)] == wanted] if wanted else []
            if not places:
                raise ValueError(f"the file does not have the lines of the hunk at line {start}")
            there = min(places, key=lambda k: abs(k - begin))
            if moved is not None:
                moved.append(there - begin)
            begin = there
        out += old[at:begin]
        out += [text for tag, text in steps if tag in " +"]
        at = begin + len(wanted)
    out += old[at:]
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# a file as the units a change can sit in
# --------------------------------------------------------------------------- #
def units(tree: ast.Module) -> dict[str, ast.AST]:
    """Every function (methods by Class.name), every class line (name, bases, decorators), and for
    the module and each class the statements that stand outside functions -- together the whole file."""
    out: dict[str, ast.AST] = {}
    used: set[str] = set()

    def unique(name: str) -> str:
        candidate, n = name, 1
        while candidate in used:
            n += 1
            candidate = f"{name}#{n}"
        used.add(candidate)
        return candidate

    def visit(owner: str, body: Sequence[ast.stmt]) -> None:
        loose = []
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[unique(f"{owner}.{node.name}" if owner else node.name)] = node
            elif isinstance(node, ast.ClassDef):
                name = unique(f"{owner}.{node.name}" if owner else node.name)
                line = copy.copy(node)
                line.body = [ast.Pass()]
                out[name + CLASS_LINE] = line
                visit(name, node.body)
            else:
                loose.append(node)
        out[(owner or "<module>") + OUTSIDE] = ast.Module(body=loose, type_ignores=[])

    visit("", tree.body)
    return out


def owner_class(name: str) -> str | None:
    """The class a unit sits in (for a class line: the class around that class), or None."""
    if name.endswith(OUTSIDE):
        inside = name[:-len(OUTSIDE)]
        return None if inside == "<module>" else inside
    plain = name[:-len(CLASS_LINE)] if name.endswith(CLASS_LINE) else name
    return plain.rsplit(".", 1)[0] if "." in plain else None


# --------------------------------------------------------------------------- #
# a changed unit cut into its smallest independent pieces
# --------------------------------------------------------------------------- #
class _Count:
    def __init__(self) -> None:
        self.n = 0

    def next(self) -> int:
        self.n += 1
        return self.n - 1


def _tokens(node: ast.AST) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", ast.unparse(node))


def _one_change(before: ast.AST, after: ast.AST) -> bool:
    """Whether a changed statement or expression is ONE change as a whole, not changes inside it:
    one of the two is a part of the other (something wrapped around it, or taken off), or the two
    have less than half of their words and signs in common (it was written anew)."""
    one, other = kinds.key(before), kinds.key(after)
    if one in other or other in one:
        return True
    try:
        return difflib.SequenceMatcher(a=_tokens(before), b=_tokens(after), autojunk=False).ratio() < REWRITTEN_BELOW
    except Exception:                                        # a shape that cannot be written out: look inside it
        return False


def _merge(before: Any, after: Any, pick: Callable[[int], bool], count: _Count) -> Any:
    """The tree that has, at every place the two differ, the second one's version where `pick`
    says so and the first one's elsewhere. Places are numbered in the order they are met."""
    if kinds.key(before) == kinds.key(after):
        return before
    if isinstance(before, list) and isinstance(after, list):
        return _merge_lists(before, after, pick, count)
    if not (isinstance(before, ast.AST) and isinstance(after, ast.AST)) or type(before) is not type(after):
        return after if pick(count.next()) else before
    if isinstance(before, (ast.expr, ast.stmt)) and _one_change(before, after):
        return after if pick(count.next()) else before
    differing = [name for name in before._fields if name not in _IGNORED
                 and kinds.key(getattr(before, name, None)) != kinds.key(getattr(after, name, None))]
    if not differing:
        return before
    for name in differing:
        one, other = getattr(before, name, None), getattr(after, name, None)
        if not (isinstance(one, (ast.AST, list)) and isinstance(other, (ast.AST, list)) and isinstance(one, list) == isinstance(other, list)):
            return after if pick(count.next()) else before                       # a name, a constant, something where nothing was
    new = copy.copy(before)
    for name in differing:
        value = _merge(getattr(before, name), getattr(after, name), pick, count)
        if name == "body" and value == [] and not isinstance(before, ast.Module):
            value = [ast.Pass()]
        setattr(new, name, value)
    return new


def _merge_lists(before: list, after: list, pick: Callable[[int], bool], count: _Count) -> list:
    if len(before) == len(after) and not any(isinstance(item, ast.stmt) for item in before + after):
        return [_merge(x, y, pick, count) for x, y in zip(before, after)]          # arguments, elements: place by place
    out: list = []
    matcher = difflib.SequenceMatcher(a=[kinds.key(x) for x in before], b=[kinds.key(x) for x in after], autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            out += before[i1:i2]
        elif tag == "replace" and i2 - i1 == j2 - j1:
            out += [_merge(x, y, pick, count) for x, y in zip(before[i1:i2], after[j1:j2])]
        else:
            for item in before[i1:i2]:                                           # taken out, one place each
                if not pick(count.next()):
                    out.append(item)
            for item in after[j1:j2]:                                            # put in, one place each
                if pick(count.next()):
                    out.append(item)
    return out


def pieces_of(before: ast.AST, after: ast.AST, limit: int = MAX_PIECES_OF_ONE_UNIT) -> list[tuple[str, str]] | int:
    """The change from one unit to the other as its smallest independent pieces: for each, the unit
    with every OTHER piece already made, and the unit with all of them made (the expert's). When
    there are more than `limit` pieces, their number alone."""
    count = _Count()
    none = _merge(before, after, lambda i: False, count)
    total = count.n
    everything = _merge(before, after, lambda i: True, _Count())
    if kinds.key(none) != kinds.key(before) or kinds.key(everything) != kinds.key(after):
        raise AssertionError("the pieces do not add up to the change")
    if total > limit:
        return total
    post = ast.unparse(after)
    out = []
    for piece in range(total):
        pre = ast.unparse(_merge(before, after, lambda i, piece=piece: i != piece, _Count()))
        out.append((pre, post))
    return out


def fix_as_pieces(before_text: str, after_text: str) -> dict[str, Any]:
    """One file of one fix: the units that changed, each cut into pieces; the definitions added and removed."""
    try:
        before, after = ast.parse(before_text), ast.parse(after_text)
    except (SyntaxError, ValueError, RecursionError) as error:
        return {"readable": False, "why": type(error).__name__}
    one, other = units(before), units(after)
    out: dict[str, Any] = {"readable": True, "pieces": [], "definitions_added": [], "definitions_removed": [], "units_changed": [],
                           "units_changed_in_too_many_places": {}}
    for name in sorted(set(one) | set(other)):
        if name not in one or name not in other:
            here, there, rows = (other, one, out["definitions_added"]) if name not in one else (one, other, out["definitions_removed"])
            owner = owner_class(name)
            if owner is not None and owner + CLASS_LINE not in there:
                continue                                                         # inside a class that is itself new (or gone): counted once, with the class
            if name.endswith(OUTSIDE) and not here[name].body:
                continue
            rows.append({"unit": name, "sha": _sha(kinds.key(here[name]))})
            continue
        if ast.dump(one[name]) == ast.dump(other[name]) or kinds.key(one[name]) == kinds.key(other[name]):
            continue
        cut = pieces_of(one[name], other[name])
        out["units_changed"].append(name)
        if isinstance(cut, int):
            out["units_changed_in_too_many_places"][name] = cut
            continue
        out["pieces"] += [{"unit": name, "pre": pre, "post": post} for pre, post in cut]
    return out


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# the tasks
# --------------------------------------------------------------------------- #
def task_from_pull_request(record: Mapping[str, Any]) -> dict[str, Any]:
    """One task as its Python pieces. `record` is what the collector kept of the pull request: for
    every changed file its path, status, hunks, and -- for Python files that are not tests -- the
    file as it was before."""
    out: dict[str, Any] = {"task": record["instance_id"], "repo": record.get("repo"), "pieces": [], "whole_things": [],
                           "files_python": 0, "files_not_python": 0, "problems": [], "hunks_found_at_another_line": 0}
    if record.get("error"):
        out["problems"].append("the pull request could not be fetched")
        return out
    for row in record.get("files", []):
        if row.get("is_test"):
            continue
        if not row.get("is_python"):
            out["files_not_python"] += 1
            continue
        out["files_python"] += 1
        path = row["path"]
        if row["status"] == "added":
            out["whole_things"].append({"what": "file added", "where": path, "sha": _sha(row.get("patch") or path)})
            continue
        if row["status"] == "removed":
            out["whole_things"].append({"what": "file removed", "where": path, "sha": _sha(row.get("before") or path)})
            continue
        if row.get("before") is None or not row.get("patch"):
            if row["status"] == "renamed" and not row.get("patch"):
                continue                                                         # moved, not changed
            out["problems"].append(f"{path}: the file before or its hunks are missing")
            continue
        moved: list[int] = []
        try:
            after = apply_patch(row["before"], row["patch"], moved)
        except ValueError as error:
            out["problems"].append(f"{path}: {error}")
            continue
        out["hunks_found_at_another_line"] += len(moved)
        cut = fix_as_pieces(row["before"], after)
        if not cut["readable"]:
            out["problems"].append(f"{path}: not readable as Python 3 ({cut['why']})")
            continue
        for piece in cut["pieces"]:
            out["pieces"].append({"where": f"{path}::{piece['unit']}", "pre": piece["pre"], "post": piece["post"]})
        for what, rows in (("definition added", cut["definitions_added"]), ("definition removed", cut["definitions_removed"])):
            out["whole_things"] += [{"what": what, "where": f"{path}::{r['unit']}", "sha": r["sha"]} for r in rows]
        for unit, n in cut["units_changed_in_too_many_places"].items():
            out["whole_things"].append({"what": f"unit changed in {n} places", "where": f"{path}::{unit}", "sha": _sha(f"{path}::{unit}::{n}")})
    return out


# --------------------------------------------------------------------------- #
# what was seen before
# --------------------------------------------------------------------------- #
ORDER = {name: n for n, name in enumerate(kinds.OPENNESS)}


def learn(tasks: Sequence[Mapping[str, Any]]) -> tuple[list[list[list[kinds.Operator]]], dict[str, set[str]], dict[str, set[str]]]:
    """Every piece of every task shown once. Returns the operators per task and piece, and for
    every operator text the tasks and the repositories that gave it."""
    operators, by_task, by_repo = [], collections.defaultdict(set), collections.defaultdict(set)
    for task in tasks:
        rows = []
        for piece in task["pieces"]:
            made = kinds.operators_of(piece["pre"], piece["post"])
            rows.append(made)
            for operator in made:
                by_task[operator.text].add(task["task"])
                by_repo[operator.text].add(task["repo"])
        operators.append(rows)
    return operators, by_task, by_repo


class Piece:
    """One piece with what its own operators make of the function, each worked out once."""

    def __init__(self, piece: Mapping[str, Any], made: Sequence[kinds.Operator], cap: int = CAP) -> None:
        self.made, self.cap = sorted(made, key=lambda op: ORDER[op.openness]), cap
        self.post = ast.unparse(ast.parse(piece["post"]))
        try:
            self.place: kinds.Place | None = kinds.Place(piece["pre"])
        except (SyntaxError, ValueError, RecursionError):
            self.place = None
        self.known: dict[str, tuple[int, bool]] = {}

    def of(self, operator: kinds.Operator) -> tuple[int, bool]:
        """(programs the operator makes of the function, whether the expert's is one of them);
        (0, False) when it would make more than the limit and so is not applied at all."""
        if operator.text not in self.known:
            programs = kinds.candidates(operator, self.place, at_most=self.cap)
            self.known[operator.text] = (len(programs), self.post in programs)
        return self.known[operator.text]

    def asked(self, allowed: Callable[[kinds.Operator], bool], first_is_enough: bool = False) -> dict[str, Any]:
        """Of the operators `allowed` lets through: the one that makes exactly the expert's version
        among the fewest programs; failing that, whether one of them is merely too loose to apply."""
        if self.place is None or not self.made:
            return {"answer": NEVER, "readable": False}
        best, too_loose = None, False
        for operator in self.made:
            if not allowed(operator):
                continue
            programs, hit = self.of(operator)
            if hit:
                row = {"programs": programs, "openness": operator.openness, "surroundings": operator.surroundings, "operator": operator.shown()[:200]}
                if best is None or (row["programs"], ORDER[row["openness"]]) < (best["programs"], ORDER[best["openness"]]):
                    best = row
                if first_is_enough:
                    break
            elif programs == 0:
                too_loose = True
        if best is not None:
            return {"answer": MADE, **best}
        return {"answer": TOO_LOOSE if too_loose else NEVER}


def measure(tasks: Sequence[Mapping[str, Any]], cap: int = CAP, progress: Callable[[int, int], None] | None = None) -> dict[str, Any]:
    """Every piece of every task asked three ways: with its own lesson (the same task again), with
    the lessons of all other tasks, and with the lessons of other repositories only."""
    operators, by_task, by_repo = learn(tasks)
    whole = collections.defaultdict(set)
    for task in tasks:
        for thing in task["whole_things"]:
            whole[(thing["what"].split(" in ")[0], thing["sha"])].add(task["task"])
    per_task = {}
    for number, (task, rows) in enumerate(zip(tasks, operators)):
        name, repo = task["task"], task["repo"]
        pieces = []
        for piece, made in zip(task["pieces"], rows):
            one = Piece(piece, made, cap)
            pieces.append({"where": piece["where"],
                           "other_tasks": one.asked(lambda op: bool(by_task[op.text] - {name})),
                           "other_repositories": one.asked(lambda op: bool(by_repo[op.text] - {repo})),
                           "the_same_task_again": one.asked(lambda op: True, first_is_enough=True)})
        things = [{"what": t["what"], "where": t["where"], "seen_in_another_task": bool(whole[(t["what"].split(" in ")[0], t["sha"])] - {name})}
                  for t in task["whole_things"]]
        per_task[name] = {"repo": repo, "pieces": pieces, "whole_things": things, "files_python": task["files_python"],
                          "files_not_python": task["files_not_python"], "problems": list(task["problems"])}
        if progress:
            progress(number + 1, len(tasks))
    return {"per_task": per_task, "operators_kept": len(by_task)}


# --------------------------------------------------------------------------- #
# what it came to
# --------------------------------------------------------------------------- #
def _made(piece: Mapping[str, Any], question: str, at_most_programs: int | None = None, no_looser_than: str | None = None) -> bool:
    row = piece[question]
    if row["answer"] != MADE:
        return False
    if at_most_programs is not None and row["programs"] > at_most_programs:
        return False
    return no_looser_than is None or ORDER[row["openness"]] <= ORDER[no_looser_than]


def _middle(values: Sequence[float]) -> float | None:
    ordered = sorted(values)
    return ordered[len(ordered) // 2] if ordered else None


def summarise(per_task: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    usable = {name: row for name, row in per_task.items() if not row["problems"] and (row["pieces"] or row["whole_things"])}
    out: dict[str, Any] = {
        "tasks": len(per_task),
        "tasks_with_a_problem": sorted(name for name, row in per_task.items() if row["problems"]),
        "tasks_whose_fix_has_no_python_change_outside_tests": sorted(name for name, row in per_task.items()
                                                                     if not row["problems"] and not row["pieces"] and not row["whole_things"]),
        "tasks_counted": len(usable),
        "pieces": sum(len(row["pieces"]) for row in usable.values()),
        "whole_things": dict(sorted(collections.Counter(re.sub(r"\d+", "N", t["what"]) for row in usable.values() for t in row["whole_things"]).items())),
        "tasks_with_a_whole_thing": sum(1 for row in usable.values() if row["whole_things"]),
        "tasks_that_also_change_files_that_are_not_python": sum(1 for row in usable.values() if row["files_not_python"]),
    }
    sizes = [len(row["pieces"]) + len(row["whole_things"]) for row in usable.values()]
    out["pieces_and_whole_things_per_task"] = {
        "least": min(sizes) if sizes else None, "middle": _middle(sizes), "most": max(sizes) if sizes else None,
        "tasks_with_one": sum(1 for n in sizes if n == 1), "tasks_with_at_most_three": sum(1 for n in sizes if n <= 3),
        "tasks_with_more_than_ten": sum(1 for n in sizes if n > 10)}
    pieces = [piece for row in usable.values() for piece in row["pieces"]]
    for question in ("the_same_task_again", "other_tasks", "other_repositories"):
        made = [piece for piece in pieces if piece[question]["answer"] == MADE]
        cell: dict[str, Any] = {
            "of_pieces": len(pieces),
            "pieces_" + MADE: len(made),
            "pieces_" + TOO_LOOSE: sum(1 for piece in pieces if piece[question]["answer"] == TOO_LOOSE),
            "pieces_" + NEVER: sum(1 for piece in pieces if piece[question]["answer"] == NEVER),
            "pieces_made_by_how_exact_the_operator_is": dict(sorted(collections.Counter(p[question]["openness"] for p in made).items(), key=lambda kv: ORDER[kv[0]])),
            "pieces_made_as_one_of_at_most": {str(k): sum(1 for p in made if p[question]["programs"] <= k) for k in HAYSTACKS},
        }

        def whole_task(row: Mapping[str, Any], programs: int | None = None, looseness: str | None = None) -> bool:
            things = question == "the_same_task_again" or all(t["seen_in_another_task"] for t in row["whole_things"])
            return things and all(_made(p, question, programs, looseness) for p in row["pieces"])

        cell["of_tasks"] = len(usable)
        cell["tasks_with_every_piece_made_exactly"] = sum(1 for row in usable.values() if whole_task(row))
        cell["tasks_with_every_piece_made_as_one_of_at_most_10"] = sum(1 for row in usable.values() if whole_task(row, 10))
        cell["tasks_with_every_piece_made_by_an_exact_or_names_open_operator"] = sum(1 for row in usable.values() if whole_task(row, None, kinds.NAMES_OPEN))
        cell["tasks_with_pieces_of_which_none_is_made"] = sum(1 for row in usable.values() if row["pieces"] and not any(_made(p, question) for p in row["pieces"]))
        cell["tasks_with_no_piece_only_whole_things"] = sum(1 for row in usable.values() if not row["pieces"])
        cell["share_of_its_pieces_made_in_the_middle_task"] = _middle([sum(1 for p in row["pieces"] if _made(p, question)) / len(row["pieces"])
                                                                       for row in usable.values() if row["pieces"]])
        if question != "the_same_task_again":
            tries = []
            for row in usable.values():
                if whole_task(row):
                    product = 1
                    for p in row["pieces"]:
                        product *= p[question]["programs"]
                    tries.append(product)
            cell["whole_fixes_to_try_where_every_piece_is_made"] = {
                "tasks": len(tries), "middle": _middle(tries), "one": sum(1 for t in tries if t == 1), "at_most_10": sum(1 for t in tries if t <= 10),
                "at_most_1000": sum(1 for t in tries if t <= 1000), "more_than_a_million": sum(1 for t in tries if t > 10 ** 6)}
            reused = collections.Counter(p[question]["operator"] for p in made)
            cell["operators_that_made_the_most_pieces"] = [{"operator": text, "pieces": n} for text, n in reused.most_common(12)]
        out[question] = cell
    by_repo: dict[str, dict[str, int]] = {}
    for row in usable.values():
        cell = by_repo.setdefault(row["repo"], {"tasks": 0, "pieces": 0, "pieces_made_exactly_from_other_tasks": 0,
                                                "tasks_with_every_piece_made_exactly_from_other_tasks": 0})
        cell["tasks"] += 1
        cell["pieces"] += len(row["pieces"])
        cell["pieces_made_exactly_from_other_tasks"] += sum(1 for p in row["pieces"] if _made(p, "other_tasks"))
        cell["tasks_with_every_piece_made_exactly_from_other_tasks"] += bool(all(t["seen_in_another_task"] for t in row["whole_things"])
                                                                           and all(_made(p, "other_tasks") for p in row["pieces"]))
    out["by_repository"] = dict(sorted(by_repo.items()))
    return out


def code_sha256() -> dict[str, str]:
    files = ("canonical/runtime/edit_kind_learning_v1.py", "canonical/tools/expert_fix_repetition_measure_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--pull-requests-dir", required=True, type=pathlib.Path, help="one JSON file per task, as the collector wrote them")
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    started = time.monotonic()
    records = [json.loads(path.read_text()) for path in sorted(args.pull_requests_dir.glob("*.json"))]
    if args.tasks is not None:
        records = [r for r in records if r["instance_id"] in set(args.tasks)]
    digest = hashlib.sha256()
    for record in records:
        digest.update(json.dumps(record, sort_keys=True).encode("utf-8"))
    tasks = [task_from_pull_request(record) for record in records]
    print(f"{len(tasks)} tasks read as pieces in {time.monotonic() - started:.0f} s: {sum(len(t['pieces']) for t in tasks)} pieces", flush=True)

    def progress(done: int, of: int) -> None:
        if done % 50 == 0 or done == of:
            print(f"{done} of {of} tasks asked, {time.monotonic() - started:.0f} s", flush=True)

    measured = measure(tasks, progress=progress)
    record = {"schema": SCHEMA, "authority": AUTHORITY, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "pull_requests_sha256": digest.hexdigest(), "code_sha256": code_sha256(), "model_calls": 0,
              "programs_one_operator_may_make_of_one_function": CAP, "a_unit_changed_in_more_places_than_this_is_not_cut_up": MAX_PIECES_OF_ONE_UNIT,
              "a_statement_or_expression_with_less_in_common_than_this_is_one_change": REWRITTEN_BELOW,
              "operators_kept": measured["operators_kept"], "summary": summarise(measured["per_task"]), "per_task": measured["per_task"],
              "seconds": round(time.monotonic() - started, 1)}
    args.out.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record["summary"], indent=1)[:5000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
