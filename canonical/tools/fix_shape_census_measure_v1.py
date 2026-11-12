#!/usr/bin/env python3
"""Count the shapes of real fixes, before another family of small changes is built.

What is asked
-------------
Everything measured here so far without a model makes single small changes to a buggy program and
lets the tests judge them. How many real fixes ARE one small change? If few are, no such family,
learned from experience or listed outright, can go further, however well it is ordered; and the
question of what to build next is answered before anything is built.

Three sets of fixes that nobody here wrote, read as pairs (the program before, the program after):

  HumanEvalFix, the 64 development bugs   bugs made by hand, one to a function. The 100 scored
                                          bugs are NOT read: their fixes stay unseen.
  ConDefects, 2,864 pairs                 real wrong and corrected submissions to AtCoder tasks
  SWE-bench Verified, 500 pull requests   the experts' merged fixes in 12 real projects, as the
                                          collector fetched them from GitHub; test files set aside

Each fix is given the first shape that fits (canonical/runtime/fix_shape_v1.py): one piece taken
out, one piece put in, one leaf exchanged, one expression exchanged, one statement rewritten,
several statements at one place, several places; for a pull request also several files. No
program and no test is run.

"Can be listed" is the ceiling of every list of single small changes that knows nothing but the
buggy program: one piece taken out; a piece of at most three nodes put in, written with what the
program holds or Python has built in; one leaf exchanged for an operator, for something held or
built in, or for the constant next to it. It says nothing of how long such a list would be.

What was expected, and the two rules, were written into EXPECTED before any fix was read by this
tool, and the tool was committed in that state.

What was found
--------------
See WHAT_WAS_FOUND below and canonical/verification/FIX_SHAPE_CENSUS_20261112_V1.json.

Usage
-----
  python3 canonical/tools/fix_shape_census_measure_v1.py \\
      --humanevalfix /tmp/hef/humanevalpack.jsonl --condefects /tmp/cd/ConDefects \\
      --pull-requests-dir /tmp/swe/pulls --out /tmp/shape/census.json
"""
from __future__ import annotations

import argparse
import ast
import collections
import datetime
import hashlib
import json
import pathlib
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import fix_shape_v1 as fix_shape  # noqa: E402
from canonical.runtime import take_out_v1 as take_out  # noqa: E402

SCHEMA = "BRAIN_FIX_SHAPE_CENSUS_V1"

SEVERAL_FILES, A_WHOLE_FILE, NO_PYTHON = "several files", "a file added or removed", "no python changed outside the tests"
SHAPES = fix_shape.SHAPES + (SEVERAL_FILES, A_WHOLE_FILE)
SET_ASIDE = (fix_shape.UNREADABLE, fix_shape.SAME, NO_PYTHON)
AT_MOST_ONE_STATEMENT = (fix_shape.TAKEN_OUT, fix_shape.PUT_IN, fix_shape.LEAF, fix_shape.EXPRESSION, fix_shape.STATEMENT)
SIZES = ((1, "1"), (2, "2"), (3, "3"), (6, "4 to 6"), (12, "7 to 12"), (10 ** 9, "13 or more"))

EXPECTED: dict[str, Any] = {
    "written": "2026-11-12 about 19:05 UTC, before this tool had read a single fix of any of the three sets",
    "humanevalfix_development_of_64": {
        fix_shape.TAKEN_OUT: [9, 11],
        "note": "an earlier look at these 64 found the fix by taking a piece out for 10: that line is known, not expected",
        fix_shape.PUT_IN: [8, 14], fix_shape.LEAF: [25, 35], "can be listed": [40, 52]},
    "condefects_share_of_2864": {
        fix_shape.TAKEN_OUT: [0.03, 0.08], fix_shape.PUT_IN: [0.10, 0.20], fix_shape.LEAF: [0.20, 0.35], "can be listed": [0.25, 0.45]},
    "swe_bench_verified_of_500": {
        fix_shape.TAKEN_OUT: [0, 10], "can be listed": [10, 40], "at most one statement, in one file": [75, 150]},
    "swe_bench_verified_cut_into_pieces": {
        "written": "2026-11-12 about 19:16 UTC, AFTER the count of whole fixes above had been seen and before any fix was cut into pieces here",
        "tasks of which every piece can be listed, of 500": [60, 110], "share of the pieces that can be listed": [0.25, 0.40]},
    "rules": {
        "one piece put in": "A family that puts one piece in is built for HumanEvalFix only if at least 6 of the 64 development fixes are "
                            "one piece put in, of at most 3 nodes, written with what the program holds or Python has built in.",
        "real projects": "A repair run on real projects with lists of single small changes is built only if at least 50 of the 500 expert "
                         "fixes can be listed. Below that such lists have their ceiling in sight there, and what comes next has to make "
                         "several changes that belong together."},
}

WHAT_WAS_FOUND: dict[str, Any] = {}


# --------------------------------------------------------------------------- #
# the fixes
# --------------------------------------------------------------------------- #
def humanevalfix_development(path: pathlib.Path) -> dict[str, tuple[str, str]]:
    """The 64 development bugs as (buggy, fixed). The scored bugs are not handed out by this tool."""
    from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef
    bugs = hef.load_bugs(path)
    development, _ = hef.split(bugs)
    keep = set(development)
    return {bug["name"]: (bug["buggy"], bug["fixed"]) for bug in bugs if bug["name"] in keep}


def condefects(root: pathlib.Path) -> dict[str, tuple[str, str]]:
    from canonical.tools import expert_fixes_dose_response_measure_v1 as dose
    pairs, _ = dose.condefects_pairs(root)
    return pairs


def of_pull_request(record: Mapping[str, Any]) -> dict[str, Any]:
    """The shape of one expert fix: the Python it changes outside the tests. Files that are not
    Python (documentation, release notes, data) are counted beside it and do not change the shape."""
    from canonical.tools import expert_fix_repetition_measure_v1 as repetition
    python = [row for row in record.get("files", []) if not row.get("is_test") and row.get("is_python")]
    other = sum(1 for row in record.get("files", []) if not row.get("is_test") and not row.get("is_python"))
    out: dict[str, Any] = {"kind": None, "needs": None, "nodes": None, "python_files": len(python), "other_files": other}
    if record.get("error"):
        return {**out, "shape": fix_shape.UNREADABLE, "kind": "the pull request could not be fetched"}
    if not python:
        return {**out, "shape": NO_PYTHON}
    if len(python) > 1:
        return {**out, "shape": SEVERAL_FILES}
    row = python[0]
    if row.get("status") in ("added", "removed"):
        return {**out, "shape": A_WHOLE_FILE, "kind": row["status"]}
    if row.get("before") is None or not row.get("patch"):
        return {**out, "shape": fix_shape.UNREADABLE, "kind": "the file before or its hunks are missing"}
    try:
        after = repetition.apply_patch(row["before"], row["patch"], [])
    except ValueError as error:
        return {**out, "shape": fix_shape.UNREADABLE, "kind": str(error)[:120]}
    return {**out, **fix_shape.shape(row["before"], after)}


def pieces_of_pull_request(record: Mapping[str, Any]) -> dict[str, Any]:
    """The same fix cut into its smallest independent pieces (expert_fix_repetition_measure_v1:
    for each piece the unit with every other piece already made, and the unit as the expert left
    it), each piece given its shape. "Held" is what the changed files held BEFORE the fix, so a
    name that another piece of the same fix brings in is not held. Definitions and files added or
    removed are whole things, not pieces, and cannot be listed."""
    from canonical.tools import expert_fix_repetition_measure_v1 as repetition
    task = repetition.task_from_pull_request(record)
    held: set = set()
    for row in record.get("files", []):
        if not row.get("is_test") and row.get("is_python") and row.get("before"):
            try:
                held |= fix_shape.atoms(ast.parse(row["before"]))
            except (SyntaxError, ValueError, RecursionError):
                pass
    shapes = [fix_shape.shape(piece["pre"], piece["post"], held=held) for piece in task["pieces"]]
    listed = [found["shape"] in fix_shape.SHAPES and fix_shape.can_be_listed(found) for found in shapes]
    return {"pieces": len(shapes), "whole_things": len(task["whole_things"]), "problems": len(task["problems"]),
            "pieces_that_can_be_listed": sum(listed), "shapes": dict(collections.Counter(found["shape"] for found in shapes)),
            "every_piece_can_be_listed": bool(shapes) and all(listed) and not task["whole_things"] and not task["problems"]}


def summarise_pieces(rows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    whole = [row for row in rows.values() if row["every_piece_can_be_listed"]]
    shapes: collections.Counter = collections.Counter()
    for row in rows.values():
        shapes.update(row["shapes"])
    pieces = sum(row["pieces"] for row in rows.values())
    can = sum(row["pieces_that_can_be_listed"] for row in rows.values())

    def how_many(row: Mapping[str, Any]) -> str:
        return str(row["pieces"]) if row["pieces"] <= 3 else "4 or more"

    return {"tasks": len(rows), "tasks_with_a_problem": sum(1 for row in rows.values() if row["problems"]),
            "tasks_with_a_whole_thing": sum(1 for row in rows.values() if row["whole_things"]),
            "pieces": pieces, "pieces_that_can_be_listed": can, "share_of_pieces_that_can_be_listed": round(can / pieces, 4) if pieces else None,
            "pieces_by_shape": {name: shapes[name] for name in fix_shape.SHAPES + SET_ASIDE if shapes[name]},
            "tasks_of_which_every_piece_can_be_listed": len(whole),
            "of_those_by_number_of_pieces": dict(sorted(collections.Counter(how_many(row) for row in whole).items())),
            "all_tasks_by_number_of_pieces": dict(sorted(collections.Counter(how_many(row) for row in rows.values()).items()))}


# --------------------------------------------------------------------------- #
# the count
# --------------------------------------------------------------------------- #
def _size(nodes: int) -> str:
    return next(label for limit, label in SIZES if nodes <= limit)


def summarise(rows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Counts over fixes that were each given a shape. Shares are of the fixes counted, which
    leaves out those that could not be read or change nothing that runs."""
    counted = {name: row for name, row in rows.items() if row["shape"] not in SET_ASIDE}
    by_shape = collections.Counter(row["shape"] for row in counted.values())
    listed = [name for name, row in counted.items() if row["shape"] in fix_shape.SHAPES and fix_shape.can_be_listed(row)]
    put_in = [row for row in counted.values() if row["shape"] == fix_shape.PUT_IN]
    leaves = [row for row in counted.values() if row["shape"] == fix_shape.LEAF]
    small = [row for row in put_in if row["nodes"] <= fix_shape.SMALL_PIECE]
    total = len(counted)

    def share(n: int) -> float | None:
        return round(n / total, 4) if total else None

    def table(found: Iterable[Mapping[str, Any]], key: str) -> dict[str, dict[str, int]]:
        cells: dict[str, dict[str, int]] = {}
        for row in found:
            label = _size(row["nodes"]) if key == "nodes" else str(row[key])
            cells.setdefault(label, {})
            cells[label][row["needs"]] = cells[label].get(row["needs"], 0) + 1
        return cells

    at_most_one = sum(by_shape[name] for name in AT_MOST_ONE_STATEMENT)
    return {
        "fixes": len(rows), "set_aside": dict(collections.Counter(row["shape"] for row in rows.values() if row["shape"] in SET_ASIDE)),
        "counted": total,
        "by_shape": {name: by_shape[name] for name in SHAPES if by_shape[name]},
        "share_by_shape": {name: share(by_shape[name]) for name in SHAPES if by_shape[name]},
        "at_most_one_statement": at_most_one, "share_at_most_one_statement": share(at_most_one),
        "can_be_listed": len(listed), "share_can_be_listed": share(len(listed)),
        "can_be_listed_by_shape": dict(collections.Counter(counted[name]["shape"] for name in listed)),
        "taken_out_by_kind": dict(collections.Counter(row["kind"] for row in counted.values() if row["shape"] == fix_shape.TAKEN_OUT)),
        "put_in_by_kind": dict(collections.Counter(row["kind"] for row in put_in)),
        "put_in_by_size_and_what_it_needs": table(put_in, "nodes"),
        "put_in_small_and_nothing_new": sum(1 for row in small if row["needs"] != fix_shape.NEW),
        "leaf_by_kind_and_what_it_needs": table(leaves, "kind"),
        "what_the_rest_needs": dict(collections.Counter(row["needs"] for row in counted.values()
                                                        if row["shape"] in fix_shape.SHAPES and row["shape"] not in (fix_shape.TAKEN_OUT, fix_shape.PUT_IN, fix_shape.LEAF))),
        "too_large_to_ask_take_out": sum(1 for row in counted.values() if row.get("not_listed")),
    }


def against_the_full_list(pairs: Mapping[str, tuple[str, str]], at_most: int | None = None) -> dict[str, Any]:
    """fix_shape decides "one piece taken out" from the part of the program that differs. Here
    the same is decided the long way, by listing every candidate of take_out_v1 for the whole
    program and looking for the other program among them; the two have to agree, both ways round."""
    def among(whole: str, other: str) -> bool:
        try:
            wanted = ast.unparse(ast.parse(other))
        except (SyntaxError, ValueError, RecursionError):
            return False
        return any(text == wanted for text, _, _ in take_out.candidates(whole))

    names = sorted(pairs)
    if at_most is not None:                                           # spread over the whole set, not its first names
        names = names[::max(1, len(names) // at_most)][:at_most] if at_most > 0 else []
    apart: list[str] = []
    said = collections.Counter()
    for name in names:
        buggy, fixed = pairs[name]
        found = fix_shape.shape(buggy, fixed)["shape"]
        if found in (fix_shape.UNREADABLE, fix_shape.SAME):
            continue
        forwards = among(buggy, fixed)
        backwards = not forwards and among(fixed, buggy)
        long_way = fix_shape.TAKEN_OUT if forwards else fix_shape.PUT_IN if backwards else "neither"
        short_way = found if found in (fix_shape.TAKEN_OUT, fix_shape.PUT_IN) else "neither"
        said[long_way] += 1
        if long_way != short_way:
            apart.append(name)
    return {"pairs": sum(said.values()), "said_the_long_way": dict(said), "the_two_ways_apart": apart}


def pairs_sha256(pairs: Mapping[str, tuple[str, str]]) -> str:
    digest = hashlib.sha256()
    for name in sorted(pairs):
        for text in (name,) + tuple(pairs[name]):
            digest.update(hashlib.sha256(text.encode("utf-8")).digest())
    return digest.hexdigest()


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/fix_shape_census_measure_v1.py", "canonical/runtime/fix_shape_v1.py", "canonical/runtime/take_out_v1.py",
             "canonical/tools/expert_fix_repetition_measure_v1.py", "canonical/tools/expert_fix_pull_request_collector_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def _row(found: Mapping[str, Any]) -> list[Any]:
    return [found["shape"], found.get("kind"), found.get("needs"), found.get("nodes")]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--humanevalfix", type=pathlib.Path, help="humanevalpack.jsonl, the Python split; only the development bugs are read")
    parser.add_argument("--condefects", type=pathlib.Path, help="a checkout of ConDefects")
    parser.add_argument("--pull-requests-dir", type=pathlib.Path, help="one JSON file per task, as the collector wrote them")
    parser.add_argument("--check-pairs", type=int, default=60, help="how many ConDefects pairs to decide the long way as well (some seconds each)")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    started = time.time()
    record: dict[str, Any] = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expected_before": EXPECTED, "sets": {}, "per_fix_key": "[shape, kind, what it needs, nodes]", "per_fix": {},
        "checks": {}, "model_calls": 0, "programs_run": 0, "tests_run": 0, "code_sha256": code_sha256()}

    if args.humanevalfix:
        pairs = humanevalfix_development(args.humanevalfix)
        rows = {name: fix_shape.shape(*pair) for name, pair in pairs.items()}
        record["sets"]["humanevalfix_development"] = {**summarise(rows), "pairs_sha256": pairs_sha256(pairs)}
        record["per_fix"]["humanevalfix_development"] = {name: _row(row) for name, row in rows.items()}
        record["checks"]["humanevalfix_development_against_the_full_list"] = against_the_full_list(pairs)
        print("humanevalfix", json.dumps(record["sets"]["humanevalfix_development"]["by_shape"]), flush=True)
    if args.condefects:
        pairs = condefects(args.condefects)
        rows = {name: fix_shape.shape(*pair) for name, pair in pairs.items()}
        record["sets"]["condefects"] = {**summarise(rows), "pairs_sha256": pairs_sha256(pairs)}
        record["checks"]["condefects_against_the_full_list"] = against_the_full_list(pairs, args.check_pairs)
        print("condefects", json.dumps(record["sets"]["condefects"]["by_shape"]), flush=True)
    if args.pull_requests_dir:
        records = {path.stem: json.loads(path.read_text()) for path in sorted(args.pull_requests_dir.glob("*.json"))}
        rows = {name: of_pull_request(found) for name, found in records.items()}
        digest = hashlib.sha256()
        for name in sorted(records):
            digest.update(hashlib.sha256(json.dumps(records[name], sort_keys=True).encode("utf-8")).digest())
        by_project: dict[str, collections.Counter] = {}
        for name, row in rows.items():
            by_project.setdefault(records[name].get("repo", "?"), collections.Counter())[row["shape"]] += 1
        record["sets"]["swe_bench_verified"] = {
            **summarise(rows), "pull_requests_sha256": digest.hexdigest(),
            "that_also_change_files_that_are_not_python": sum(1 for row in rows.values() if row["other_files"]),
            "by_project": {project: dict(count) for project, count in sorted(by_project.items())},
            "can_be_listed_by_project": dict(collections.Counter(
                records[name].get("repo", "?") for name, row in rows.items() if row["shape"] in fix_shape.SHAPES and fix_shape.can_be_listed(row)))}
        record["per_fix"]["swe_bench_verified"] = {name: _row(row) for name, row in rows.items()}
        print("swe-bench verified", json.dumps(record["sets"]["swe_bench_verified"]["by_shape"]), flush=True)
        cut = {}
        for done, (name, found) in enumerate(records.items()):
            cut[name] = pieces_of_pull_request(found)
            if (done + 1) % 100 == 0:
                print("cut into pieces:", done + 1, "tasks,", round(time.time() - started, 1), "s", flush=True)
        record["sets"]["swe_bench_verified_cut_into_pieces"] = summarise_pieces(cut)
        record["per_fix"]["swe_bench_verified_cut_into_pieces"] = {
            name: [row["pieces"], row["pieces_that_can_be_listed"], row["whole_things"], row["every_piece_can_be_listed"]] for name, row in cut.items()}
        record["per_fix_key_cut_into_pieces"] = "[pieces, pieces that can be listed, whole things, every piece can be listed]"
        print("cut into pieces", json.dumps(record["sets"]["swe_bench_verified_cut_into_pieces"]), flush=True)

    record["seconds"] = round(time.time() - started, 1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("WROTE", args.out, record["seconds"], "s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
