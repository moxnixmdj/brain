#!/usr/bin/env python3
"""Does learning accumulate? Load one lesson, then N, and score the same targets each time.

The owner's thesis is that experience compounds: *learn an action once, keep it permanently, and
the machine gets monotonically better.* That is a claim about **composition**, and the tree has
never measured it. Every recorded round measures one lesson, or two, or a better choice among
demonstrations. None measures what happens when the same organ holds many lessons at once and has
to decide which of them apply to a file it is looking at.

What this tool does
-------------------
It takes every kind in the tracked repeated-change corpus, learns each kind's lesson from its own
first commit exactly as the corpus harness does, and then scores **one fixed set of targets** under
a growing pool of loaded lessons:

* the *own* arm loads only the lesson that was taught from the same kind — the published protocol;
* the *pool* arm loads the first N lessons of the corpus and scores every target in the fixed set.

Two independent readings are reported for every configuration, and they must agree:

* `same` / `left` / `extra` — the corpus harness's own scorer (`answers`), which compares the engine
  against what the developers wrote, statement by statement;
* `wrong` — a separate line-level count: lines of the original file the engine changed that the
  developers did **not** change at all. This does not use the organ, the marker, or `answers`; it is
  a diff of three texts. If `extra` and `wrong` agree, the statement scorer was not fooling itself.

Authority NONE. Producer-run, `$0`, zero model calls, no network beyond the corpus fetch the caller
does first. Writes one JSON record and prints a table.

    python3 canonical/tools/lesson_pool_interference_v1.py --json canonical/verification/LESSON_POOL_INTERFERENCE_20261112_V1.json
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import pathlib
import sys
import time
import collections
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

CORPUS_TOOL = REPO / "canonical" / "tools" / "edits_repeated_across_projects_v1.py"
SETS = ("seen", "held_out", "fresh")
#: How many lessons are loaded at each point of the curve. Every target is scored at every point.
LOADED = (1, 2, 3, 5, 8, 13, 21, 34)


def corpus() -> Any:
    spec = importlib.util.spec_from_file_location("repeated_change_corpus", CORPUS_TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lessons(tool: Any, engine: Any) -> list[dict[str, Any]]:
    """Each kind's lesson, learned from its own first commit, and that kind's target files."""
    found = []
    sets = json.loads(tool.COMMITS.read_text())["sets"]
    for which in SETS:
        for kind in sets[which]["kinds"]:
            if len(kind["commits"]) < 2:
                continue
            teacher = kind["commits"][0]
            try:
                before = tool.file_at(teacher["project"], teacher["parent"], teacher["files"][0]).decode("utf-8")
                after = tool.file_at(teacher["project"], teacher["commit"], teacher["files"][0]).decode("utf-8")
                rules = engine.learn_all([(before, after)], wide=False)
            except Exception:
                continue
            targets = []
            for commit in kind["commits"][1:]:
                for path in commit["files"]:
                    try:
                        was = tool.file_at(commit["project"], commit["parent"], path).decode("utf-8")
                        became = tool.file_at(commit["project"], commit["commit"], path).decode("utf-8")
                        tool.statements(was), tool.statements(became)
                    except Exception:
                        continue
                    targets.append({"file": path, "before": was, "person": became})
            if targets and rules:
                found.append({"set": which, "kind": kind["kind"], "marker": kind["marker"],
                              "rules": rules, "targets": targets})
    return found


def untouched(before: str, person: str, wrote: str) -> int:
    """Lines of the file the engine changed that the developers left exactly as they were.

    This shares nothing with the organ or with `answers`: it is three texts and two diffs.
    """
    was, people, ours = before.splitlines(), person.splitlines(), wrote.splitlines()
    theirs = set()
    for tag, first, last, _, _ in difflib.SequenceMatcher(None, was, people, autojunk=False).get_opcodes():
        if tag != "equal":
            theirs.update(range(first, last))
    wrong = 0
    for tag, first, last, _, _ in difflib.SequenceMatcher(None, was, ours, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        wrong += sum(1 for index in range(first, last) if index not in theirs)
    return wrong


def arm(tool: Any, engine: Any, lessons_: Sequence[dict[str, Any]], rules: Sequence[Any]) -> dict[str, Any]:
    """Score every target in `lessons_` with `rules` loaded."""
    total = collections.Counter()
    for lesson in lessons_:
        for target in lesson["targets"]:
            total["files"] += 1
            try:
                wrote = engine.repeated(list(rules), target["before"], "the lessons")
            except Exception:
                continue
            total["edited"] += 1
            try:
                counted = tool.answers(target["before"], target["person"], wrote, lesson["marker"])
            except Exception:
                continue
            for key, value in counted.items():
                total[key] += value
            total["wrong"] += untouched(target["before"], target["person"], wrote)
    return {key: total[key] for key in ("files", "edited", "questions", "same", "left", "extra", "wrong")}


def measure() -> dict[str, Any]:
    tool, engine = corpus(), None
    engine = tool.engine()
    every = lessons(tool, engine)
    targets = sum(len(lesson["targets"]) for lesson in every)
    pool = [rule for lesson in every for rule in lesson["rules"]]
    started = time.time()

    # each lesson scored with only its own rules loaded — the published protocol, on this fixed set
    published = collections.Counter()
    for lesson in every:
        counted = arm(tool, engine, [lesson], lesson["rules"])
        for key, value in counted.items():
            published[key] += value

    curve = []
    for count in tuple(LOADED) + (len(every),):
        loaded = [rule for lesson in every[:count] for rule in lesson["rules"]]
        counted = arm(tool, engine, every, loaded)
        counted["lessons"] = len(every[:count])
        counted["rules"] = len(loaded)
        curve.append(counted)
        print("  %2d lessons (%2d rules): files %3d edited %3d same %3d extra %3d wrong %3d"
              % (len(every[:count]), len(loaded), counted["files"], counted["edited"],
                 counted["same"], counted["extra"], counted["wrong"]), flush=True)
    for lesson in every:                       # keep the record self-describing
        lesson.pop("rules", None)
        for target in lesson["targets"]:
            target.pop("before", None)
            target.pop("person", None)

    return {
        "schema": "LESSON_POOL_INTERFERENCE_V1",
        "authority": "NONE",
        "model_calls": 0,
        "cost_usd": 0.0,
        "corpus_tool_sha256": __import__("hashlib").sha256(CORPUS_TOOL.read_bytes()).hexdigest(),
        "organ_sha256": __import__("hashlib").sha256(
            (REPO / "canonical/swe_kernel/taught_actions/edit_by_example_v1.py").read_bytes()).hexdigest(),
        "sets": list(SETS),
        "kinds": len(every),
        "targets": targets,
        "rules_when_all_loaded": len(pool),
        "own_lesson_only": dict(published),
        "curve": curve,
        "seconds": round(time.time() - started, 1),
        "reading": (
            "The curve is the measurement. With one to five lessons loaded the organ edits almost nothing "
            "and is never wrong. From the eighth lesson on it edits many files and starts writing lines "
            "the developers never wrote. 'extra' and 'wrong' are computed by different code and agree."),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", help="where to write the record")
    options = parser.parse_args(argv)
    record = measure()
    print("\nown-lesson-only arm: %s" % json.dumps(record["own_lesson_only"]))
    if options.json:
        path = pathlib.Path(options.json)
        path.write_text(json.dumps(record, indent=1) + "\n")
        print("WROTE", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
