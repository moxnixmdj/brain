#!/usr/bin/env python3
"""Computer use: how often is a wrong action indistinguishable from the right one?

WHY THIS EXISTS
---------------
The composed law (`capability_law_v1`) carries one term it cannot compute: check density for computer
use, printed as UNMEASURED because there is no test corpus on a desktop. That left "all computer use"
as an assumption. It does not have to stay one.

On a real machine the oracle does not need a human and does not need a test file. In *replay* -- the case
the claim "do it once and it has it" lives in -- the intent IS the recorded consequence, so the oracle is
a differential: run the action from the same state and compare the observable with the one that was
recorded. Nothing about the semantics of the program is needed. The only question is how much of a wrong
action survives that comparison, and that is a measurable property of the observation, not of the action.

WHAT IS MEASURED HERE
---------------------
A real directory (`computer_env_v1.ComputerEnv`), real programs, real subprocesses, real reset. For a
declared set of real shell transformations:

    the right action, run from the base state       -> the recorded consequence
    mechanically derived wrong actions (mutants)    -> run from the same base state

Every mutant is classified, per observation model:

    CRASH             the action failed visibly (non-zero exit) -- caught by anyone
    NO_EFFECT         the observable is unchanged and a change was recorded -- caught by the differential
    DIFFERS           the observable differs from the recorded consequence -- caught by the differential
    INDISTINGUISHABLE the observable is *identical* to the recorded consequence: the wrong action is
                      silently accepted

Three observation models are reported, because the whole of computer use turns on which one you have:

    full     names, sizes and a content hash per file   (what an OS lets a program see)
    coarse   names and sizes                            (what a screen shows you at a glance)
    listing  names only

Mutants are derived mechanically from the declared command -- wrong source, wrong target, dropped target,
swapped source and target, dropped first flag -- so nothing is chosen because it is expected to fail.

Model dependency: 0. Network: 0. Every effect is a real file on a real disk in a temporary directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_COMPUTER_USE_CHECK_DENSITY_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
TIMEOUT_SECONDS = 15.0

TEXT = b"alpha beta gamma\ndelta epsilon\nzeta eta theta\niota kappa\n"
DECOY = b"one two three\nfour five\nsix seven eight\nnine ten\n"

# name, command template ({src} and {dst}), required program
TASKS: tuple[tuple[str, str, str], ...] = (
    ("gzip", "gzip -k -f {src}", "gzip"),
    ("gunzip", "gzip -f {src} && gunzip -f {src}.gz", "gzip"),
    ("sort", "sort {src} -o {dst}", "sort"),
    ("base64", "base64 {src} > {dst}", "base64"),
    ("tr", "tr a-z A-Z < {src} > {dst}", "tr"),
    ("sed", "sed s/alpha/ALPHA/ {src} > {dst}", "sed"),
    ("sha256sum", "sha256sum {src} > {dst}", "sha256sum"),
    ("cp", "cp {src} {dst}", "cp"),
    ("split", "split -l 2 {src} chunk_", "split"),
    ("tar", "tar -cf {dst} {src}", "tar"),
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def _observe(root: pathlib.Path, model: str) -> str:
    parts: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        if model == "listing":
            parts.append(rel)
        elif model == "coarse":
            parts.append("%s:%d" % (rel, len(data)))
        else:
            parts.append("%s:%d:%s" % (rel, len(data), _sha(data)))
    return "|".join(parts)


def _seed(root: pathlib.Path) -> None:
    (root / "in.txt").write_bytes(TEXT)
    (root / "decoy.txt").write_bytes(DECOY)
    (root / "sub").mkdir(exist_ok=True)
    (root / "sub" / "keep.txt").write_bytes(b"keep me\n")


def _run(root: pathlib.Path, command: str) -> tuple[int, str]:
    result = subprocess.run(["/bin/sh", "-c", command], cwd=str(root), capture_output=True,
                            timeout=TIMEOUT_SECONDS)
    return result.returncode, (result.stdout + result.stderr).decode("utf-8", errors="replace")


def _mutants(template: str) -> list[tuple[str, str]]:
    """Mechanical wrong actions derived from the declared template: none is chosen for its failure mode."""
    mutated: list[tuple[str, str]] = []
    if "{src}" in template:
        mutated.append(("wrong_source", template.replace("{src}", "decoy.txt")))
    if "{dst}" in template:
        mutated.append(("wrong_target", template.replace("{dst}", "sub/out.dat")))
        mutated.append(("drop_target", template.replace("> {dst}", "").replace(" {dst}", "")))
    if "{src}" in template and "{dst}" in template:
        mutated.append(("swap_source_target",
                        template.replace("{src}", "@@SRC@@").replace("{dst}", "{src}")
                        .replace("@@SRC@@", "{dst}")))
    flags = [token for token in template.replace("<", " ").split() if token.startswith("-")]
    if flags:
        mutated.append(("drop_first_flag", template.replace(flags[0] + " ", "", 1)))
    return [(kind, command.replace("{src}", "in.txt").replace("{dst}", "out.dat"))
            for kind, command in mutated]


def _has(program: str) -> bool:
    return shutil.which(program) is not None


def measure() -> dict[str, Any]:
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain-computer-check-"))
    template = work / "template"
    template.mkdir()
    _seed(template)

    def fresh() -> pathlib.Path:
        target = pathlib.Path(tempfile.mkdtemp(prefix="run-", dir=work))
        shutil.copytree(template, target, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns())
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(template, target)
        return target

    base_state = {model: _observe(template, model) for model in ("full", "coarse", "listing")}
    tasks: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    try:
        for name, command, program in TASKS:
            if not _has(program):
                skipped.append({"task": name, "reason": "program not installed: " + program})
                continue
            correct_command = command.replace("{src}", "in.txt").replace("{dst}", "out.dat")
            correct_root = fresh()
            code, output = _run(correct_root, correct_command)
            correct_state = {model: _observe(correct_root, model)
                             for model in ("full", "coarse", "listing")}
            changed = correct_state["full"] != base_state["full"]
            if code != 0 or not changed:
                skipped.append({"task": name,
                                "reason": "the declared correct command did not work (rc=%d): %s"
                                          % (code, output.strip()[:120])})
                continue
            rows = []
            for kind, mutated in _mutants(command):
                run_root = fresh()
                try:
                    mutant_code, mutant_output = _run(run_root, mutated)
                except subprocess.TimeoutExpired:
                    mutant_code, mutant_output = 124, "timeout"
                outcome = {}
                for model in ("full", "coarse", "listing"):
                    state = _observe(run_root, model)
                    if mutant_code != 0:
                        outcome[model] = "CRASH"
                    elif state == base_state[model]:
                        outcome[model] = "NO_EFFECT"
                    elif state == correct_state[model]:
                        outcome[model] = "INDISTINGUISHABLE"
                    else:
                        outcome[model] = "DIFFERS"
                rows.append({"mutant": kind, "command": mutated,
                             "returncode": mutant_code,
                             "noise": mutant_output.strip()[:120],
                             "outcome_by_observation": outcome})
            tasks.append({"task": name, "command": correct_command,
                          "correct_state_changed": changed, "mutants": rows})
    finally:
        shutil.rmtree(work, ignore_errors=True)

    mutants = [row for task in tasks for row in task["mutants"]]
    counts = {model: {"CRASH": 0, "NO_EFFECT": 0, "DIFFERS": 0, "INDISTINGUISHABLE": 0}
              for model in ("full", "coarse", "listing")}
    for row in mutants:
        for model, outcome in row["outcome_by_observation"].items():
            counts[model][outcome] += 1
    total = len(mutants)
    density = {}
    for model, cell in counts.items():
        caught = cell["CRASH"] + cell["NO_EFFECT"] + cell["DIFFERS"]
        density[model] = {
            "mutants": total,
            **cell,
            "caught_by_any_check": caught,
            "density": round(caught / total, 4) if total else 0.0,
            "indistinguishable_share": round(cell["INDISTINGUISHABLE"] / total, 4) if total else 0.0,
        }

    # Two regimes, because they are not the same problem. In replay the intent is the recorded
    # consequence, so any difference is an error. In novel work there is no reference, and the only
    # content-free checks left are "it crashed" and "nothing happened".
    regime: dict[str, Any] = {}
    for model in ("full", "coarse", "listing"):
        replay_caught = counts[model]["CRASH"] + counts[model]["NO_EFFECT"] + counts[model]["DIFFERS"]
        novel_caught = counts[model]["CRASH"] + counts[model]["NO_EFFECT"]
        regime[model] = {
            "replay_density": round(replay_caught / total, 4) if total else 0.0,
            "replay_invisible": round((total - replay_caught) / total, 4) if total else 0.0,
            "novel_density": round(novel_caught / total, 4) if total else 0.0,
            "novel_invisible": round((total - novel_caught) / total, 4) if total else 0.0,
            "novel_caught_only_by_crash_or_no_effect": True,
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls":  0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "environment": {
            "kind": "real directory, real programs from PATH, real subprocesses, real reset",
            "observation_models": {
                "full": "relative name, size, content hash per file",
                "coarse": "relative name and size",
                "listing": "relative name only",
            },
            "what_an_oracle_needs": ("a recorded consequence to compare against; in replay the intent is "
                                     "the recorded consequence, so no human specification is required"),
        },
        "tasks_run": len(tasks),
        "tasks_skipped": skipped,
        "mutants": total,
        "density_by_observation": density,
        "density_by_regime": regime,
        "per_task": [{"task": task["task"], "mutants": len(task["mutants"]),
                      "full": {key: sum(1 for row in task["mutants"]
                                        if row["outcome_by_observation"]["full"] == key)
                               for key in ("CRASH", "NO_EFFECT", "DIFFERS", "INDISTINGUISHABLE")}}
                     for task in tasks],
        "examples": {
            "indistinguishable_under_full": next(
                ({"task": task["task"], "mutant": row["mutant"], "command": row["command"]}
                 for task in tasks for row in task["mutants"]
                 if row["outcome_by_observation"]["full"] == "INDISTINGUISHABLE"), None),
            "caught_only_by_content": next(
                ({"task": task["task"], "mutant": row["mutant"],
                  "full": row["outcome_by_observation"]["full"],
                  "coarse": row["outcome_by_observation"]["coarse"]}
                 for task in tasks for row in task["mutants"]
                 if row["outcome_by_observation"]["full"] != "INDISTINGUISHABLE"
                 and row["outcome_by_observation"]["coarse"] == "INDISTINGUISHABLE"), None),
        },
    }
    report["what_this_shows"] = _headline(report)
    return report


def _headline(report: Mapping[str, Any]) -> str:
    full = report["density_by_observation"]["full"]
    coarse = report["density_by_observation"]["coarse"]
    listing = report["density_by_observation"]["listing"]
    return (
        "%d mechanically derived wrong actions on %d real shell transformations in a real directory: a "
        "replay differential catches %s of them under a full state observation (%s silently identical), "
        "%s under a name-and-size observation (%s silently identical) and %s under a listing (%s silently "
        "identical). That completeness is not a property of the agent: without a recorded consequence -- "
        "novel work, where there is nothing to replay -- only crashes and no-ops are visible, so density "
        "falls to %s even with a full digest. Computer-use check density is therefore neither zero nor "
        "fixed: it is set by how much of the state the agent can see, and by whether it has a consequence "
        "to compare against."
        % (report["mutants"], report["tasks_run"], full["density"], full["indistinguishable_share"],
           coarse["density"], coarse["indistinguishable_share"], listing["density"],
           listing["indistinguishable_share"],
           report["density_by_regime"]["full"]["novel_density"]))


def summarize(report: Mapping[str, Any]) -> str:
    lines = ["environment: " + report["environment"]["kind"],
             "tasks %d | mutants %d | skipped %d"
             % (report["tasks_run"], report["mutants"], len(report["tasks_skipped"]))]
    for model, cell in report["density_by_observation"].items():
        lines.append("  %-8s density %-6s invisible %-6s  (crash %d, no-effect %d, differs %d, identical %d)"
                     % (model, cell["density"], cell["indistinguishable_share"], cell["CRASH"],
                        cell["NO_EFFECT"], cell["DIFFERS"], cell["INDISTINGUISHABLE"]))
    for model, cell in report["density_by_regime"].items():
        lines.append("  %-8s replay %-6s | novel %-6s (novel sees only crashes and no-ops)"
                     % (model, cell["replay_density"], cell["novel_density"]))
    for skip in report["tasks_skipped"]:
        lines.append("  skipped %-10s %s" % (skip["task"], skip["reason"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="How much of a wrong computer action does a replay differential catch?")
    parser.add_argument("--json", dest="json_path", default=None)
    ns = parser.parse_args(argv)
    report = measure()
    print(summarize(report))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
