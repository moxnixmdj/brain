#!/usr/bin/env python3
"""Where a candidate's content could come from, counted rather than argued.

WHY THIS EXISTS
---------------
`THE_CHECK_THE_LOOP_THROWS_AWAY_20261125_V1` retracted a number from the round before it and
replaced it with three measured ones. A retraction is only worth something if the replacement can
be re-derived by somebody who does not trust the receipt, so the two numbers that carry the
conclusion are recomputed here from material anybody can fetch:

  the channel     of the tasks that got no candidate in the 2026-11-13 run, how many issue texts
                  write no code line at all
  the need        of the tasks that got no candidate, how much of what their fix puts in is
                  already held by the file it changes, and how much by the whole project

The third number in that receipt -- what a trace of the failing test reaches -- needs a tree per
task and is a procedure, not a function of two files; it is written out in the receipt instead of
being pretended into this tool.

WHAT IT READS, AND WHAT IT DOES NOT
-----------------------------------
The benchmark's own statements (`problems/swe/swebench-verified/<task>.yaml`) and the merged pull
requests behind each task, as `expert_fix_pull_request_collector_v1` writes them (`path`, `patch`,
and `before` for the Python files that existed before). Nothing here reads a test, runs a program,
or asks a model. The reader for code lines is the tree's own
(`canonical/runtime/quoted_in_the_task_text_v1.code_lines`); the notion of "held" is the tree's own
(`canonical/runtime/fix_shape_v1`, whose `held` errs towards holding).

WHAT "HELD BY THE PROJECT" COSTS
--------------------------------
Reading every `.py` of a tree at the base commit takes ~8 s per task. So the whole-project figure
is reported over a deterministic sample (`--every`, every Nth task in name order) and says so; the
file-only figure is reported over every changed file of the tasks that have no candidate.

Authority NONE. Reads files, writes nothing but what it prints.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import subprocess
import sys
from typing import Any, Iterable, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import fix_shape_v1 as shape      # noqa: E402
from canonical.runtime import quoted_in_the_task_text_v1 as quoted   # noqa: E402

SCHEMA = "BRAIN_THE_CONTENT_CHANNEL_V1"
HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@")


def after_of(before: str, patch: str) -> str:
    """The file `before` with the patch's hunks applied. The patch is the API's own hunks, so the
    context is trusted; a hunk that runs past the file is an error rather than a silent truncation."""
    src = before.split("\n")
    if src and src[-1] == "":
        src = src[:-1]
    out: list[str] = []
    at = 0
    lines = patch.split("\n")
    i = 0
    while i < len(lines):
        found = HUNK.match(lines[i])
        if not found:
            i += 1
            continue
        start = int(found.group(1)) - 1
        if start > at:
            out.extend(src[at:start])
            at = start
        i += 1
        while i < len(lines) and not lines[i].startswith("@@"):
            line = lines[i]
            if line.startswith("-"):
                at += 1
            elif line.startswith("+"):
                out.append(line[1:])
            else:
                out.append(line[1:] if line.startswith(" ") else line)
                at += 1
            i += 1
    out.extend(src[at:])
    return "\n".join(out)


def changed_python(record: dict[str, Any]) -> list[dict[str, Any]]:
    """The files of a task's fix that are Python, are not tests, existed before, and were changed."""
    return [file for file in record.get("files") or ()
            if not file.get("is_test") and file.get("is_python") and file.get("patch") and file.get("before")]


def label(atom: tuple) -> str | None:
    if atom[0] == "name":
        return atom[1]
    if atom[0] == "constant":
        return str(atom[1])
    return None


def new_atoms(before: str, after: str) -> set[str]:
    """The names and constants the fixed file has and the buggy one does not."""
    try:
        held = shape.atoms([ast.parse(before)])
        now = shape.atoms([ast.parse(after)])
    except SyntaxError:
        return set()
    return {name for name in (label(atom) for atom in now - held) if name}


def project_atoms(tree: pathlib.Path) -> set:
    atoms: set = set()
    for file in tree.rglob("*.py"):
        try:
            atoms |= shape.atoms([ast.parse(file.read_text(encoding="utf-8", errors="replace"))])
        except (SyntaxError, ValueError):
            continue
    return atoms


def tree_of(clone: pathlib.Path, commit: str, into: pathlib.Path) -> pathlib.Path:
    """The commit's tree unpacked at `into`, once. A blobless clone fetches what the archive needs."""
    if into.exists():
        return into
    into.mkdir(parents=True)
    tar = into.parent / f"{into.name}.tar"
    with tar.open("wb") as out:
        done = subprocess.run(["git", "-C", str(clone), "archive", "--format=tar", commit], stdout=out)
    if done.returncode != 0:
        raise RuntimeError(f"archive {commit} failed")
    subprocess.run(["tar", "xf", str(tar), "-C", str(into)], check=True)
    tar.unlink()
    return into


def count(statements: pathlib.Path, experts: pathlib.Path, no_candidate: Iterable[str],
          clone: pathlib.Path | None, trees: pathlib.Path | None, every: int) -> dict[str, Any]:
    import yaml                                                  # only here: the statements are yaml

    tasks = sorted(no_candidate)
    channel = {"with_a_code_line": [], "without_a_code_line": []}
    needs: dict[str, int] = {}
    files = 0
    for task in tasks:
        held = yaml.safe_load((statements / f"{task}.yaml").read_text(encoding="utf-8"))
        text = str(held.get("problem_statement") or "")
        (channel["with_a_code_line"] if quoted.code_lines(text) else channel["without_a_code_line"]).append(task)
        record = json.loads((experts / f"{task}.json").read_text(encoding="utf-8"))
        for file in changed_python(record):
            verdict = shape.shape(file["before"], after_of(file["before"], file["patch"]))
            needs[verdict["needs"]] = needs.get(verdict["needs"], 0) + 1
            files += 1
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "tasks_with_no_candidate": len(tasks),
        "the_channel": {"with_a_code_line": len(channel["with_a_code_line"]),
                        "without_a_code_line": len(channel["without_a_code_line"]),
                        "tasks_with_code_lines_but_no_candidate": channel["with_a_code_line"]},
        "the_file_being_changed": {"changed_files": files, "needs": needs},
    }
    if clone is not None and trees is not None:
        sample = tasks[::every]
        vs_file: dict[str, int] = {}
        vs_project: dict[str, int] = {}
        for task in sample:
            record = json.loads((experts / f"{task}.json").read_text(encoding="utf-8"))
            for file in changed_python(record):
                after = after_of(file["before"], file["patch"])
                by_file = shape.shape(file["before"], after)
                vs_file[by_file["needs"]] = vs_file.get(by_file["needs"], 0) + 1
                commit = json.loads((trees / f"{task}.commit").read_text())["base_commit"]
                held = project_atoms(tree_of(clone, commit, trees / task))
                by_project = shape.shape(file["before"], after, held=held)
                vs_project[by_project["needs"]] = vs_project.get(by_project["needs"], 0) + 1
        out["the_whole_project"] = {"sample": len(sample), "every": every,
                                    "needs_vs_the_file": vs_file, "needs_vs_the_project": vs_project}
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statements", type=pathlib.Path, required=True,
                        help="the benchmark's problems/swe/swebench-verified")
    parser.add_argument("--experts", type=pathlib.Path, required=True,
                        help="what expert_fix_pull_request_collector_v1 wrote, one json per task")
    parser.add_argument("--no-candidate", type=pathlib.Path, required=True,
                        help="json list of the tasks that got no candidate, or a receipt with per_task")
    parser.add_argument("--clone", type=pathlib.Path, default=None, help="a django clone, for the project figure")
    parser.add_argument("--work", type=pathlib.Path, default=None, help="where trees are unpacked")
    parser.add_argument("--every", type=int, default=4, help="one task in this many, for the project figure")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    loaded = json.loads(args.no_candidate.read_text())
    if isinstance(loaded, dict):
        tasks = [task for task, row in loaded["per_task"].items() if not (row.get("candidates_made") or 0)]
    else:
        tasks = [str(task) for task in loaded]
    got = count(args.statements, args.experts, tasks, args.clone, args.work, args.every)
    if args.json:
        print(json.dumps(got, indent=1, sort_keys=True))
        return 0
    channel = got["the_channel"]
    print(f"tasks with no candidate                          {got['tasks_with_no_candidate']}")
    print(f"  whose issue writes no code line                {channel['without_a_code_line']}")
    print(f"  whose issue writes a code line                 {channel['with_a_code_line']}")
    print(f"changed files of those tasks                     {got['the_file_being_changed']['changed_files']}")
    for need, n in sorted(got["the_file_being_changed"]["needs"].items(), key=lambda pair: -pair[1]):
        print(f"  needs against the file alone  {need:10s} {n}")
    if "the_whole_project" in got:
        whole = got["the_whole_project"]
        print(f"\nsample: {whole['sample']} tasks (one in {whole['every']})")
        for name in ("needs_vs_the_file", "needs_vs_the_project"):
            print(f"  {name:22s} {dict(sorted(whole[name].items()))}")
        reach = whole["needs_vs_the_project"].get("held", 0) + whole["needs_vs_the_project"].get("nothing", 0)
        print(f"  reachable from the project alone  {reach} of {sum(whole['needs_vs_the_project'].values())}")
    print("\n  authority NONE -- a measurement, not a verification receipt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
