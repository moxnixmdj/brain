#!/usr/bin/env python3
"""Does naming the changed symbol give a lesson ownership? And: can weights even be evidenced here?

Two questions, one corpus, one run.

**Question 1.** The previous round measured that a pool of lessons writes lines no developer wrote,
because nothing decides which lesson owns a place. The declared next step was "scope by the changed
name". This measures that, and it measures it against the two controls that could make the answer
a tautology:

* **Discriminating power** — on how many targets does the symbol filter leave exactly one lesson?
  A filter that keeps everything decides nothing. (The previous round's import scope was unique on
  1 of 232 targets: it was a tautology and was thrown away. This is the control that caught it.)
* **Matched volume** — blind random subsets of lessons, at volumes the symbol filter actually
  chooses, with the wrong lines per edit compared. If random does fewer edits *and* more wrong
  lines per edit, the scope is a decision and not merely caution.

**Question 2.** Whether weight-space learning is the missing layer cannot be answered by reading.
It needs a corpus with sequences from the same project so training and held-out tasks exist. This
counts that, because the answer decides the order of the whole roadmap.

Authority NONE. Producer-run, `$0`, zero model calls.

    python3 canonical/tools/lesson_ownership_measure_v1.py \
        --json canonical/verification/LESSON_OWNERSHIP_20261112_V1.json
"""
from __future__ import annotations

import argparse
import ast
import collections
import difflib
import importlib.util
import json
import pathlib
import random
import sys
import time
from typing import Any, Callable, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

CORPUS_TOOL = REPO / "canonical" / "tools" / "edits_repeated_across_projects_v1.py"
COMMITS = REPO / "canonical" / "tools" / "edits_repeated_across_projects_commits_v1.json"
SETS = ("seen", "held_out", "fresh")
SEED = 20261112


def corpus() -> Any:
    spec = importlib.util.spec_from_file_location("repeated_change_corpus", CORPUS_TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def symbols(text: str) -> set[str]:
    """Every name and attribute a file mentions. What a lesson about that code could own."""
    found: set[str] = set()
    try:
        tree = ast.parse(text)
    except Exception:
        return found
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
    return found


def changed_symbols(before: str, after: str) -> set[str]:
    """The names the example added or took away: the shortest honest statement of what it is about."""
    was, now = symbols(before), symbols(after)
    return (now - was) | (was - now)


def untouched(before: str, person: str, wrote: str) -> int:
    """Lines the engine changed that the developers left exactly as they were. Independent of the scorer."""
    was, people, ours = before.splitlines(), person.splitlines(), wrote.splitlines()
    theirs: set[int] = set()
    for tag, first, last, _, _ in difflib.SequenceMatcher(None, was, people, autojunk=False).get_opcodes():
        if tag != "equal":
            theirs.update(range(first, last))
    wrong = 0
    for tag, first, last, _, _ in difflib.SequenceMatcher(None, was, ours, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        wrong += sum(1 for index in range(first, last) if index not in theirs)
    return wrong


def lessons(tool: Any, engine: Any) -> list[dict[str, Any]]:
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
                    targets.append((was, became))
            if targets and rules:
                found.append({"set": which, "kind": kind["kind"], "marker": kind["marker"],
                              "rules": rules, "own": changed_symbols(before, after), "targets": targets})
    return found


def score(tool: Any, engine: Any, pool: Sequence[dict[str, Any]],
          choose: Callable[[dict[str, Any], str], list[Any]]) -> dict[str, int]:
    total = collections.Counter()
    for lesson in pool:
        for before, person in lesson["targets"]:
            total["files"] += 1
            chosen = choose(lesson, before)
            if not chosen:
                continue
            try:
                wrote = engine.repeated(chosen, before, "the lessons")
            except Exception:
                continue
            total["edited"] += 1
            try:
                counted = tool.answers(before, person, wrote, lesson["marker"])
            except Exception:
                continue
            for key, value in counted.items():
                total[key] += value
            total["wrong"] += untouched(before, person, wrote)
    return {key: total[key] for key in ("files", "edited", "questions", "same", "left", "extra", "wrong")}


def measure() -> dict[str, Any]:
    tool = corpus()
    engine = tool.engine()
    every = lessons(tool, engine)
    started = time.time()

    def unscoped(lesson, before):
        return [rule for one in every for rule in one["rules"]]

    def scoped(lesson, before):
        here = symbols(before)
        return [rule for one in every if one["own"] & here for rule in one["rules"]]

    curve = []
    for count in (8, 13, 21, 34, len(every)):
        pool = every[:count]
        row = {"lessons": count}
        for label, chooser in (("unscoped", lambda l, b, p=pool: [r for o in p for r in o["rules"]]),
                               ("symbol_scoped", lambda l, b, p=pool: [
                                   r for o in p if o["own"] & symbols(b) for r in o["rules"]])):
            row[label] = score(tool, engine, pool, chooser)
        curve.append(row)
        print("  %2d lessons: unscoped same %3d wrong %2d | scoped same %3d wrong %2d"
              % (count, row["unscoped"]["same"], row["unscoped"]["wrong"],
                 row["symbol_scoped"]["same"], row["symbol_scoped"]["wrong"]), flush=True)

    # CONTROL 1 -- does the filter actually decide anything?
    surviving = collections.Counter()
    for lesson in every:
        for before, _ in lesson["targets"]:
            here = symbols(before)
            surviving[sum(1 for one in every if one["own"] & here)] += 1
    total_targets = sum(surviving.values())

    # CONTROL 2 -- the same volumes, chosen blind
    blind = []
    for trial in range(5):
        generator = random.Random(SEED + trial)

        def chooser(lesson, before, g=generator):
            keep = g.sample(every, min(len(every), g.randint(1, len(every))))
            return [rule for one in keep for rule in one["rules"]]
        blind.append(score(tool, engine, every, chooser))
    full = score(tool, engine, every, scoped)

    # QUESTION 2 -- can a weight-training experiment be held out on this corpus?
    sets = json.loads(COMMITS.read_text())["sets"]
    commits_per_project = collections.Counter()
    kinds_per_project = collections.Counter()
    for which in sets:
        for kind in sets[which]["kinds"]:
            for commit in kind["commits"]:
                commits_per_project[commit["project"]] += 1
    for which in sets:
        for kind in sets[which]["kinds"]:
            if kind["commits"]:
                kinds_per_project[kind["commits"][0]["project"]] += 1

    for lesson in every:
        lesson.pop("rules", None)
        lesson["targets"] = len(lesson["targets"])

    def rate(row):
        return round(row["wrong"] / row["edited"], 3) if row["edited"] else None

    return {
        "schema": "LESSON_OWNERSHIP_V1",
        "authority": "NONE",
        "model_calls": 0,
        "cost_usd": 0.0,
        "corpus_tool_sha256": __import__("hashlib").sha256(CORPUS_TOOL.read_bytes()).hexdigest(),
        "lessons": len(every),
        "targets": total_targets,
        "curve": curve,
        "control_discriminating_power": {
            "surviving_lessons_histogram": {str(k): v for k, v in sorted(surviving.items())},
            "unique": surviving[1],
            "targets": total_targets,
            "unique_share": round(surviving[1] / total_targets, 3),
            "reading": ("A filter that keeps every lesson decides nothing. This one leaves one lesson "
                        "standing on a minority of targets, so it is a real decision and not a tautology, "
                        "but it is silent most of the time and must not be quoted as a general rule."),
        },
        "control_matched_volume": {
            "symbol_scoped": dict(full, wrong_per_edit=rate(full)),
            "blind_random": [dict(row, wrong_per_edit=rate(row)) for row in blind],
            "reading": ("Blind random lessons at comparable volumes write two to three times as many wrong "
                        "lines per edit. The scope is therefore a decision about which lesson owns a place, "
                        "not merely caution that does less work."),
        },
        "question_2_weight_training_evidencable": {
            "commits": sum(commits_per_project.values()),
            "projects": len(commits_per_project),
            "projects_with_three_or_more_commits": sum(1 for v in commits_per_project.values() if v >= 3),
            "projects_with_two_or_more_lessons": sum(1 for v in kinds_per_project.values() if v >= 2),
            "reading": ("A weight-update experiment needs a stream from the same distribution with tasks kept "
                        "back. This corpus is one commit per project almost everywhere, so training and "
                        "held-out tasks cannot be separated, and no claim about weight learning can be "
                        "evidenced on it. That is a data-shape fact, not an opinion about weights."),
        },
        "seconds": round(time.time() - started, 1),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json")
    options = parser.parse_args(argv)
    record = measure()
    for key in ("control_discriminating_power", "control_matched_volume",
                "question_2_weight_training_evidencable"):
        print("\n%s\n  %s" % (key, json.dumps(record[key])[:400]))
    if options.json:
        path = pathlib.Path(options.json)
        path.write_text(json.dumps(record, indent=1) + "\n")
        print("\nWROTE", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
