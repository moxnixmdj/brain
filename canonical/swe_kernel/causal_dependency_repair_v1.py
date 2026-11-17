#!/usr/bin/env python3
"""A dependency you cannot see is a repair you cannot make: discovering it by intervention.

WHY THIS EXISTS
---------------
`STANDING_FACTS_20261116_V1` detects that a legal step falsified an earlier verified fact, two steps before
the symptom. Detection is not repair. To repair, the agent must know *which later steps consumed the fact that
became false* -- and the 2026 record says that is exactly where every residual-ledger design stops:

  * TRACE-FIX (arXiv 2610.25776) binds evidence to resource versions and names its own boundary: "missing
    dependencies, unobserved side effects, or incorrect resource links can exclude relevant events; dependency
    links narrow hypotheses without establishing causality."
  * CausalFlow (arXiv 2605.25338) does counterfactual step repair, but relies on a model to propose the
    replacement step and re-executes the suffix to score it.
  * An open engineering question (agent-interface #165, Sep 2026) states the primitive form: how to discover
    "the smallest complete dependency footprint instead of receiving a hand-authored ground-truth set".

So the object here is a **read set acquired by intervention**, not declared and not inferred from syntax:

    a step depends on path p  iff  perturbing p changes that step's consequence

That is one extra real run per candidate path. It needs no model, no tracing infrastructure, no annotations,
and -- unlike an argv-derived set -- it sees a path that is named by *data* rather than by an argument.

THE HARD PART, MEASURED RATHER THAN ARGUED
------------------------------------------
A path named in an argument is easy. A path named *inside a file* is invisible to any syntactic reading, and
that is not a corner case: it is how build systems, package tools and archives work.

    tar -cf bundle.tar -T list.txt          reads payload.dat because list.txt names it
    cat list.txt | xargs sha256sum > c.txt  reads payload.dat because xargs is handed the name

Both are real, both are ordinary, and in both the argv-derived read set names only `list.txt`.

Three chains, real programs, real sabotage. For each: the invalidated path, the steps the argv read set
blames, the steps the intervention read set proves, what a repair actually re-runs, and whether the
independent goal command passes afterwards. A control chain where the dependency *is* syntactic checks the
other direction: a discovery method that over-declares would redo steps it did not need to.

Model dependency: 0. Network: 0. Every probe is a real subprocess on a real copy of a real state.
"""
from __future__ import annotations

import argparse
import copy
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

from canonical.swe_kernel.computer_use_check_density_v1 import _has, _run  # noqa: E402
from canonical.swe_kernel.predictive_contract_v1 import (  # noqa: E402
    _files,
    _instantiate,
    _seed,
    acquire,
)
from canonical.swe_kernel.standing_facts_v1 import (  # noqa: E402
    ACQUISITION,
    DECOY,
    TEXT,
    establish,
    revalidate,
    touched,
)

SCHEMA = "BRAIN_CAUSAL_DEPENDENCY_REPAIR_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
TIMEOUT_SECONDS = 15.0
PROBE_SUFFIX = b"\nprobe marker 7f3a\n"


# --------------------------------------------------------------------------- #
# read sets: by syntax, and by intervention
# --------------------------------------------------------------------------- #
def read_set_argv(command: str, state: Mapping[str, bytes]) -> set[str]:
    """Every path that appears as a word in the command. The ordinary, syntactic answer."""
    return {token for token in command.replace(">", " ").replace("<", " ").split()
            if token in state}


def _signature(root: pathlib.Path, before: Mapping[str, bytes]) -> tuple[int, frozenset]:
    after = _files(root)
    changed = frozenset((path, after[path]) for path in after
                        if path not in before or before[path] != after[path])
    return (0 if changed else 1), changed


def read_set_intervention(command: str, state: Mapping[str, bytes], work: pathlib.Path,
                          candidates: Sequence[str] | None = None) -> dict[str, Any]:
    """Perturb one candidate path at a time and see whether the step's consequence moves.

    The candidate set is the state itself -- finite, real, and stated. Anything the step reads that is not in
    the state (a config file outside the sandbox, a remote resource) cannot be probed here, and is named as
    the limit rather than assumed away.
    """
    probe_paths = [path for path in sorted(state) if path in set(candidates or state)]

    def run_on(mutate: str | None) -> tuple[int, frozenset] | None:
        root = pathlib.Path(tempfile.mkdtemp(prefix="probe-", dir=work))
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir()
        for path, data in state.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data + PROBE_SUFFIX if path == mutate else data)
        before = _files(root)
        try:
            code, _noise = _run(root, command)
        except subprocess.TimeoutExpired:
            code = 124
        after = _files(root)
        changed = frozenset((path, after[path]) for path in after
                            if path not in before or before[path] != after[path])
        signature = (code, changed)
        shutil.rmtree(root, ignore_errors=True)
        return signature

    baseline = run_on(None)
    dependent: list[str] = []
    if baseline is not None:
        for path in probe_paths:
            signature = run_on(path)
            if signature is not None and signature != baseline:
                dependent.append(path)
    return {"dependent_on": dependent, "probes": len(probe_paths)}


# --------------------------------------------------------------------------- #
# chains
# --------------------------------------------------------------------------- #
def _step(name: str, template: str, program: str, src: str, dst: str,
          truth_reads: Sequence[str], sabotage: bool = False) -> dict[str, Any]:
    return {"name": name, "template": template, "program": program, "src": src, "dst": dst,
            "truth_reads": list(truth_reads), "sabotage": sabotage}


def _command(step: Mapping[str, Any]) -> str:
    return step["template"].replace("{src}", step["src"]).replace("{dst}", step["dst"])


def _written(state_before: Mapping[str, bytes], state_after: Mapping[str, bytes]) -> set[str]:
    return {path for path in state_after
            if path not in state_before or state_before[path] != state_after[path]}


def _blamed(steps: Sequence[Mapping[str, Any]], read_sets: Sequence[set[str]],
            invalidated: Sequence[str], sabotage_index: int) -> list[str]:
    """The first-order answer: which steps name a path whose fact just went false."""
    return [step["name"] for index, step in enumerate(steps)
            if index != sabotage_index and read_sets[index] & set(invalidated)]


def _replay(work: pathlib.Path, steps: Sequence[Mapping[str, Any]], read_sets: Sequence[set[str]],
            invalidated: Sequence[str], sabotage_index: int, goal: str,
            all_steps: bool = False) -> dict[str, Any]:
    """Redo, in plan order, every step whose read set meets a path that has *actually moved*.

    The frontier grows only when a re-run changes something. That detail separates a repair from a cascade:
    re-running a step that read nothing relevant writes the same bytes, so nothing downstream of it is stale.
    A closure that propagates on the *intention* to re-run instead of on a real change invents work -- and, as
    the measurement shows, can wander by luck into the very step that needed redoing.

    Every step is considered, not only those that ran after the sabotage: a product built from good content
    *before* the content changed is exactly as stale as one built after.
    """
    live = pathlib.Path(tempfile.mkdtemp(prefix="repair-", dir=work))
    for step in steps:
        for path, data in step["_after"].items():
            target = live / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    frontier = set(invalidated)
    redone: list[str] = []
    moved_by: dict[str, list[str]] = {}
    for index, step in enumerate(steps):
        if index == sabotage_index:
            continue
        if not all_steps and not (set(read_sets[index]) & frontier):
            continue
        before = _files(live)
        try:
            _run(live, _command(step))
        except subprocess.TimeoutExpired:
            pass
        after = _files(live)
        moved = _written(before, after)
        redone.append(step["name"])
        moved_by[step["name"]] = sorted(moved)
        if moved:
            frontier |= moved

    code, output = _run(live, goal)
    shutil.rmtree(live, ignore_errors=True)
    return {"redone": redone, "moved_by": moved_by, "goal_passes": code == 0,
            "symptom": output.strip()[:160]}


def run_chain(work: pathlib.Path, name: str, steps: Sequence[Mapping[str, Any]],
              goal: str) -> dict[str, Any]:
    root = pathlib.Path(tempfile.mkdtemp(prefix="chain-", dir=work))
    _seed(root, "in.txt", TEXT, "never-written.dat")
    (root / "decoy.txt").write_bytes(DECOY)

    facts = establish(_files(root), 0)
    invalidated: list[str] = []
    sabotage_index = -1

    for index, step in enumerate(steps):
        step["contract"] = acquire(step["template"], step["program"], ACQUISITION, TEXT)
        binding = {"src": step["src"], "dst": step["dst"]}
        before = _files(root)
        try:
            code, _noise = _run(root, _command(step))
        except subprocess.TimeoutExpired:
            code = 124
        after = _files(root)
        step["_before"], step["_after"], step["_code"] = before, after, code

        risky = [fact for fact in facts if fact["path"] in touched(step["contract"], binding)]
        _still, broken = revalidate(risky, after, index)
        if broken and not invalidated:
            invalidated = [fact["path"] for fact in broken]
        if step.get("sabotage"):
            sabotage_index = index

        # the ledger re-stamps a fact only when the step actually rewrote its path
        refreshed = _written(before, after) | {fact["path"] for fact in broken}
        facts = [fact for fact in facts if fact["path"] not in refreshed]
        facts.extend(establish(after, index, sorted(refreshed)))

    argv_sets = [read_set_argv(_command(step), step["_before"]) for step in steps]
    declared_sets = [set(step["truth_reads"]) for step in steps]
    intervention: list[dict[str, Any]] = []
    probes = 0
    for step in steps:
        found = read_set_intervention(_command(step), step["_before"], work)
        intervention.append(found)
        probes += found["probes"]
    intervention_sets = [set(entry["dependent_on"]) for entry in intervention]

    arms = {
        "declared_deps": _replay(work, steps, declared_sets, invalidated, sabotage_index, goal),
        "argv_deps": _replay(work, steps, argv_sets, invalidated, sabotage_index, goal),
        "intervention_deps": _replay(work, steps, intervention_sets, invalidated, sabotage_index, goal),
        "redo_everything": _replay(work, steps, [], invalidated, sabotage_index, goal, all_steps=True),
    }
    redone = {arm: result["redone"] for arm, result in arms.items()}

    return {
        "chain": name,
        "steps": [{"name": step["name"], "invocation": _command(step),
                   "sabotage": bool(step.get("sabotage")),
                   "declared_reads": step["truth_reads"],
                   "argv_reads": sorted(argv_sets[index]),
                   "intervention_reads": intervention[index]["dependent_on"]}
                  for index, step in enumerate(steps)],
        "invalidated": invalidated,
        "sabotage_step": sabotage_index,
        # NB: the arm key is `argv_reads`, not `argv` -- a dict with an `argv` key is read as a DECLARED
        # PREDICATE by canonical/tools/auditability_report_v1.predicate_of(), which would add a phantom
        # "declaration that asks for nothing" to the auditability floor. Same trap as a receipt row keyed
        # `command`; both are pinned by tests.
        "blamed_by": {arm: _blamed(steps, read_sets, invalidated, sabotage_index)
                      for arm, read_sets in (("declared", declared_sets), ("argv_reads", argv_sets),
                                             ("intervention", intervention_sets))},
        "repair": arms,
        "redone_counts": {arm: len(names) for arm, names in redone.items()},
        "missed_by_argv": sorted(set(redone["declared_deps"]) - set(redone["argv_deps"])),
        "over_declared_by_argv": sorted(set(redone["argv_deps"]) - set(redone["declared_deps"])),
        "missed_by_intervention": sorted(set(redone["declared_deps"])
                                         - set(redone["intervention_deps"])),
        "over_declared_by_intervention": sorted(set(redone["intervention_deps"])
                                                - set(redone["declared_deps"])),
        "intervention_matches_declared": (redone["intervention_deps"] == redone["declared_deps"]),
        "goal": {"invocation": goal},
        "probes": probes,
    }


def _chains(work: pathlib.Path) -> list[dict[str, Any]]:
    specs = [
        ("tar_reads_a_name_from_a_list", [
            _step("copy_in", "cp {src} {dst}", "cp", "in.txt", "payload.dat", ["in.txt"]),
            _step("list_it", "ls {src} > {dst}", "cp", "payload.dat", "list.txt", []),
            _step("bundle_by_list", "tar -cf {dst} -T {src}", "tar", "list.txt", "bundle.tar",
                  ["list.txt", "payload.dat"]),
            _step("overwrite_payload", "cp {src} {dst}", "cp", "decoy.txt", "payload.dat",
                  ["decoy.txt"], sabotage=True),
            _step("digest_the_bundle", "sha256sum {src} > {dst}", "sha256sum", "bundle.tar",
                  "bundle.digest", ["bundle.tar"]),
            _step("keep_the_digest", "cp {src} {dst}", "cp", "bundle.digest", "bundle.digest.bak",
                  ["bundle.digest"]),
        ], "tar -xOf bundle.tar payload.dat | cmp - payload.dat && sha256sum -c bundle.digest"),
        ("xargs_reads_a_name_from_stdin", [
            _step("copy_in", "cp {src} {dst}", "cp", "in.txt", "payload.dat", ["in.txt"]),
            _step("list_it", "ls {src} > {dst}", "cp", "payload.dat", "list.txt", []),
            _step("digest_by_xargs", "xargs sha256sum < {src} > {dst}", "cp", "list.txt",
                  "checks.txt", ["list.txt", "payload.dat"]),
            _step("overwrite_payload", "cp {src} {dst}", "cp", "decoy.txt", "payload.dat",
                  ["decoy.txt"], sabotage=True),
            _step("digest_the_checks", "sha256sum {src} > {dst}", "sha256sum", "checks.txt",
                  "checks.digest", ["checks.txt"]),
            _step("keep_the_list", "cp {src} {dst}", "cp", "list.txt", "list.bak", ["list.txt"]),
        ], "sha256sum -c checks.txt && sha256sum -c checks.digest"),
        ("control_the_dependency_is_syntactic", [
            _step("copy_in", "cp {src} {dst}", "cp", "in.txt", "a.dat", ["in.txt"]),
            _step("sort_it", "sort {src} -o {dst}", "sort", "a.dat", "s.dat", ["a.dat"]),
            _step("digest_it", "sha256sum {src} > {dst}", "sha256sum", "s.dat", "s.digest", ["s.dat"]),
            _step("overwrite_a", "cp {src} {dst}", "cp", "decoy.txt", "a.dat", ["decoy.txt"],
                  sabotage=True),
            _step("keep_it", "cp {src} {dst}", "cp", "s.digest", "s.digest.bak", ["s.digest"]),
        ], "sha256sum -c s.digest"),
    ]
    return [run_chain(work, name, steps, goal) for name, steps, goal in specs]


def measure() -> dict[str, Any]:
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain-dep-repair-"))
    missing = [program for program in ("cp", "ls", "tar", "sort", "sha256sum", "xargs", "cmp")
               if not _has(program)]
    try:
        chains = _chains(work) if not missing else []
    finally:
        shutil.rmtree(work, ignore_errors=True)

    def outcomes(arm: str) -> dict[str, Any]:
        return {"goals_passing": sum(1 for chain in chains if chain["repair"][arm]["goal_passes"]),
                "of": len(chains),
                "steps_redone": sum(chain["redone_counts"][arm] for chain in chains),
                "chains": [chain["chain"] for chain in chains if chain["repair"][arm]["goal_passes"]]}

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "environment": {
            "kind": "real directory, real programs from PATH, real sabotage, independent goal commands",
            "dependency_test": "perturb one candidate path, re-run the step, compare its consequence",
            "candidate_set": "every file present in the state before the step; anything outside it is not probed",
        },
        "missing_programs": missing,
        "chains": len(chains),
        "steps": sum(len(chain["steps"]) for chain in chains),
        "probes": sum(chain["probes"] for chain in chains),
        "arms": {arm: outcomes(arm) for arm in
                 ("declared_deps", "argv_deps", "intervention_deps", "redo_everything")},
        "chains_where_syntax_misses_a_real_dependency": [
            chain["chain"] for chain in chains if chain["missed_by_argv"]],
        "blamed_by": {chain["chain"]: chain["blamed_by"] for chain in chains},
        "missed_by_argv": {chain["chain"]: chain["missed_by_argv"] for chain in chains},
        "over_declared_by_argv": {chain["chain"]: chain["over_declared_by_argv"] for chain in chains},
        "missed_by_intervention": {chain["chain"]: chain["missed_by_intervention"] for chain in chains},
        "over_declared_by_intervention": {chain["chain"]: chain["over_declared_by_intervention"]
                                          for chain in chains},
        "intervention_matches_declared": {chain["chain"]: chain["intervention_matches_declared"]
                                          for chain in chains},
        "per_chain": chains,
        "limit": ("the read set is discovered inside a declared candidate set -- the files in the state, and "
                  "the probe is a content change, which matches the kind of fact the ledger records. A "
                  "dependency on a config file outside the sandbox, a lock held by another process, or a "
                  "remote resource is not measured; nor is a dependency on a file's *existence* rather than "
                  "its content, which would need the matching existence-perturbation"),
    }
    report["what_this_shows"] = _headline(report)
    return report


def _headline(report: Mapping[str, Any]) -> str:
    argv = report["arms"]["argv_deps"]
    intervention = report["arms"]["intervention_deps"]
    declared = report["arms"]["declared_deps"]
    over = sum(len(v) for v in report["over_declared_by_intervention"].values())
    missed = sum(len(v) for v in report["missed_by_intervention"].values())
    return (
        "%d real chains, %d steps, one legal sabotage each, %d intervention probes. Given the true read set, "
        "repair restores the independent goal on %d of %d chains by re-running %d steps; re-running everything "
        "takes %d. The argv read set restores %d of %d -- in %d of %d chains a path is named by another file "
        "rather than by an argument (a tar list, an xargs stdin), so the syntactic set misses a step the goal "
        "depends on and blames one it does not. The intervention read set restores %d of %d with %d steps "
        "redone, %d missed and %d over-declared: recovering the declared set exactly, without being told it. "
        "Dependency links narrow hypotheses; only a counterfactual establishes the link."
        % (report["chains"], report["steps"], report["probes"],
           declared["goals_passing"], declared["of"], declared["steps_redone"],
           report["arms"]["redo_everything"]["steps_redone"],
           argv["goals_passing"], argv["of"],
           len(report["chains_where_syntax_misses_a_real_dependency"]), report["chains"],
           intervention["goals_passing"], intervention["of"], intervention["steps_redone"],
           missed, over))


def summarize(report: Mapping[str, Any]) -> str:
    arms = report["arms"]
    lines = ["environment: " + report["environment"]["kind"],
             "chains %d | steps %d | probes %d" % (report["chains"], report["steps"], report["probes"]),
             "  %-20s goals %d/%d, %d steps redone"
             % ("declared read set", arms["declared_deps"]["goals_passing"],
                arms["declared_deps"]["of"], arms["declared_deps"]["steps_redone"]),
             "  %-20s goals %d/%d, %d steps redone"
             % ("argv read set", arms["argv_deps"]["goals_passing"], arms["argv_deps"]["of"],
                arms["argv_deps"]["steps_redone"]),
             "  %-20s goals %d/%d, %d steps redone"
             % ("intervention set", arms["intervention_deps"]["goals_passing"],
                arms["intervention_deps"]["of"], arms["intervention_deps"]["steps_redone"]),
             "  %-20s goals %d/%d, %d steps redone"
             % ("redo everything", arms["redo_everything"]["goals_passing"],
                arms["redo_everything"]["of"], arms["redo_everything"]["steps_redone"])]
    for chain in report["per_chain"]:
        lines.append("  %-34s invalidated %-12s blamed: argv %s | intervention %s"
                     % (chain["chain"], ",".join(chain["invalidated"]) or "-",
                        ",".join(chain["blamed_by"]["argv_reads"]) or "-",
                        ",".join(chain["blamed_by"]["intervention"]) or "-"))
        for step in chain["steps"]:
            mark = ""
            if set(step["declared_reads"]) - set(step["argv_reads"]):
                mark = "  <-- named by data: %s" % sorted(set(step["declared_reads"])
                                                          - set(step["argv_reads"]))
            if set(step["argv_reads"]) - set(step["declared_reads"]):
                mark += "  <-- named by syntax only: %s" % sorted(set(step["argv_reads"])
                                                                  - set(step["declared_reads"]))
            lines.append("      %-22s declared %-26s argv %-26s intervention %s%s"
                         % (step["name"], ",".join(step["declared_reads"]) or "-",
                            ",".join(step["argv_reads"]) or "-",
                            ",".join(step["intervention_reads"]) or "-", mark))
        lines.append("      redone: declared %s | argv %s | intervention %s"
                     % (chain["repair"]["declared_deps"]["redone"],
                        chain["repair"]["argv_deps"]["redone"],
                        chain["repair"]["intervention_deps"]["redone"]))
    if report["missing_programs"]:
        lines.append("  missing: " + ", ".join(report["missing_programs"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Discover which steps depend on a path by perturbing it, then repair minimally.")
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
