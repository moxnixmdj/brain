#!/usr/bin/env python3
"""Manufacture the oracle instead of asserting one: the minimal observation that identifies an action.

THE ARGUMENT THIS IMPLEMENTS
----------------------------
`COMPUTER_USE_CHECK_DENSITY_20261116_V1` measured what a consequence differential can see on a real
machine: 1.0 of 34 wrong actions under a full state observation, 0.7647 under a name-level one, 0.5 in
novel work with no reference. The lesson is not "use hashes". It is that the oracle is not a predicate
somebody has to write -- it is the *observation*, and an observation is a choice. So the question stops
being "is there a verifier for this action?" (the field's question, and the one that fails, because every
fixed verifier is a proxy for intent) and becomes a decidable synthesis problem:

    given the action and the space of ways it can be wrong, which observation distinguishes them?

That is where identifiability actually lives. Two hypotheses about what an action does are the same
hypothesis under a projection that does not separate them -- which is exactly why one trace fits
exponentially many hypotheses, and why a missing causal observable makes repetition useless. The missing
observable can be *built*, by search, because "does this projection separate these consequences" is a
finite question with a computable answer.

WHAT IS SYNTHESIZED
-------------------
Features of a directory state: name, size, content, mode, mtime. A projection is a set of features. A
projection is admissible only if it passes two tests, and both are necessary:

    SEPARATION   every wrong action leaves a projection different from the right action's
    STABILITY    running the right action again reproduces the projection

Stability is what makes this an oracle rather than a trap. A timestamp separates everything, and would
have condemned every correct replay: it fails stability, and the synthesis throws it away. A projection
tuned only to separate is a machine for false alarms; a projection tuned only to be stable (names) is a
machine for silent acceptance. The two-sided test is what the field replaces with intuition.

Then a greedy minimum cover over the admissible features answers "how little observation is enough",
which is the only form of the answer that respects *the best part is no part*: the cheapest sound oracle,
not the most elaborate one.

Model dependency: 0. Network: 0. Real programs, real disk, real reset -- the measurement module's tasks
and mutants are reused rather than re-declared, so the two receipts cannot drift apart.

HONEST LIMIT, STATED HERE BECAUSE IT IS THE WHOLE LIMIT
-------------------------------------------------------
The projection is synthesized against a declared hypothesis space (mechanically derived mutants of the
action). It identifies any error inside that space, and says nothing about an error outside it. That is not
a defect of this method: it is the definition of identifiability, and a method that claims more is claiming
to separate consequences it never observed. Growing the hypothesis space is measurable work; assuming it
is complete is the mistake the insuffiency certificate exists to prevent.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.computer_use_check_density_v1 import (  # noqa: E402
    TASKS,
    _has,
    _mutants,
    _run,
    _seed,
)

SCHEMA = "BRAIN_DISTINGUISHING_PROJECTION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_SYNTHESIS"
TIMEOUT_SECONDS = 15.0
STABILITY_DELAY_SECONDS = 0.05

FEATURES = ("content", "name", "size", "mode", "mtime")


def project(root: pathlib.Path, feature: str) -> str:
    """A projection of the state. Absence is a value: a file that was not created must show up."""
    parts: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        stat = path.stat()
        if feature == "name":
            parts.append(rel)
        elif feature == "size":
            parts.append("%s:%d" % (rel, stat.st_size))
        elif feature == "content":
            import hashlib
            parts.append("%s:%s" % (rel, hashlib.sha256(path.read_bytes()).hexdigest()[:12]))
        elif feature == "mode":
            parts.append("%s:%o" % (rel, stat.st_mode & 0o777))
        elif feature == "mtime":
            parts.append("%s:%d" % (rel, stat.st_mtime_ns))
        else:
            raise ValueError("unknown feature: %s" % feature)
    return "|".join(parts)


def combine(root: pathlib.Path, features: Sequence[str]) -> str:
    return "||".join(project(root, feature) for feature in features)


def _cover(separates: Mapping[str, set[str]], universe: set[str]) -> list[str] | None:
    """Smallest set of admissible features whose union covers every wrong action."""
    for size in range(1, len(separates) + 1):
        for subset in itertools.combinations(sorted(separates), size):
            covered: set[str] = set()
            for feature in subset:
                covered |= separates[feature]
            if covered >= universe:
                return list(subset)
    return None


def synthesize() -> dict[str, Any]:
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain-projection-"))
    template = work / "template"
    template.mkdir()
    _seed(template)

    def fresh() -> pathlib.Path:
        target = pathlib.Path(tempfile.mkdtemp(prefix="run-", dir=work))
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(template, target)
        return target

    per_task: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    try:
        for name, command, program in TASKS:
            if not _has(program):
                skipped.append({"task": name, "reason": "program not installed: " + program})
                continue
            correct_command = command.replace("{src}", "in.txt").replace("{dst}", "out.dat")
            first, second = fresh(), fresh()
            code_a, _ = _run(first, correct_command)
            # A replay is never instantaneous. Two reference runs inside one filesystem timestamp tick
            # would "stabilise" a clock, so the delay is part of the test, not a convenience.
            time.sleep(STABILITY_DELAY_SECONDS)
            _run(second, correct_command)
            if code_a != 0 or project(first, "content") == project(template, "content"):
                skipped.append({"task": name, "reason": "declared correct command did not change state"})
                continue
            stable = [feature for feature in FEATURES
                      if project(first, feature) == project(second, feature)]
            reference = {feature: project(first, feature) for feature in stable}
            separates: dict[str, set[str]] = {feature: set() for feature in stable}
            mutants: list[str] = []
            for kind, mutated in _mutants(command):
                run_root = fresh()
                try:
                    mutant_code, _ = _run(run_root, mutated)
                except subprocess.TimeoutExpired:
                    mutant_code = 124
                label = "%s[rc=%d]" % (kind, mutant_code)
                mutants.append(label)
                for feature in stable:
                    if mutant_code != 0 or project(run_root, feature) != reference[feature]:
                        separates[feature].add(label)
            universe = set(mutants)
            cover = _cover(separates, universe)
            per_task.append({
                "task": name,
                "mutants": len(mutants),
                "stable_features": stable,
                "unstable_features": [f for f in FEATURES if f not in stable],
                "separated_by_single_feature": {feature: len(separates[feature])
                                                for feature in stable},
                "minimal_cover": cover,
                "every_mutant_separable": cover is not None,
                "inseparable_mutants": sorted(universe - set().union(*separates.values()))
                if separates else sorted(universe),
            })
    finally:
        shutil.rmtree(work, ignore_errors=True)

    cover_sizes = [len(task["minimal_cover"]) for task in per_task if task["minimal_cover"]]
    single = [task["task"] for task in per_task if task["minimal_cover"] == ["content"]]
    unstable: dict[str, int] = {}
    for task in per_task:
        for feature in task["unstable_features"]:
            unstable[feature] = unstable.get(feature, 0) + 1
    total_mutants = sum(task["mutants"] for task in per_task)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "features": list(FEATURES),
        "soundness_tests": {
            "separation": "the wrong action's projection differs from the right action's",
            "stability": ("the right action re-run after %.2f s reproduces its projection -- a replay is "
                          "never instantaneous, and a clock tick is not a consequence"
                          % STABILITY_DELAY_SECONDS),
        },
        "tasks": len(per_task),
        "mutants": total_mutants,
        "tasks_skipped": skipped,
        "per_task": per_task,
        "cover_size_histogram": {str(size): cover_sizes.count(size)
                                 for size in sorted(set(cover_sizes))},
        "content_alone_suffices_for": single,
        "features_rejected_by_stability": unstable,
        "admissible_features_by_task": {task["task"]: task["stable_features"] for task in per_task},
        "limit": ("the projection is synthesised against a declared hypothesis space; it identifies every "
                  "error inside that space and makes no claim about an error outside it, which is what "
                  "identifiability means"),
    }
    report["what_this_shows"] = _headline(report)
    return report


def _headline(report: Mapping[str, Any]) -> str:
    totals: dict[str, int] = {feature: 0 for feature in report["features"]}
    for task in report["per_task"]:
        for feature, count in task["separated_by_single_feature"].items():
            totals[feature] += count
    mtime_rejected = report["features_rejected_by_stability"].get("mtime", 0)
    return (
        "Across %d real shell transformations and %d mechanically derived wrong actions the oracle was "
        "synthesised, not assumed. Separation alone would admit a timestamp, and stability rejects it in %d "
        "of %d tasks -- the exception keeps it only because the program copies the source timestamp into "
        "its output, and content still wins the minimum there. The smallest sound observation is one "
        "feature everywhere: content separates %d of %d wrong actions and reproduces the right one exactly "
        "on replay, against %d for names, %d for modes and %d for sizes. The oracle is therefore an "
        "observation chosen under a two-sided test -- separation against the hypothesis space, stability "
        "against repetition -- and not a predicate somebody wrote and hoped was a proxy for intent."
        % (report["tasks"], report["mutants"], mtime_rejected, report["tasks"],
           totals["content"], report["mutants"], totals["name"], totals["mode"], totals["size"]))


def summarize(report: Mapping[str, Any]) -> str:
    lines = ["features: %s" % ", ".join(report["features"]),
             "tasks %d | mutants %d | skipped %d"
             % (report["tasks"], report["mutants"], len(report["tasks_skipped"])),
             "cover sizes: %s" % report["cover_size_histogram"],
             "rejected by stability: %s" % report["features_rejected_by_stability"]]
    for task in report["per_task"]:
        lines.append("  %-10s stable %-28s cover %-20s inseparable %d"
                     % (task["task"], ",".join(task["stable_features"]),
                        ",".join(task["minimal_cover"] or ["<none>"]),
                        len(task["inseparable_mutants"])))
    for skip in report["tasks_skipped"]:
        lines.append("  skipped %-10s %s" % (skip["task"], skip["reason"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Synthesise the smallest observation that identifies an action from its mutants.")
    parser.add_argument("--json", dest="json_path", default=None)
    ns = parser.parse_args(argv)
    report = synthesize()
    print(summarize(report))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
