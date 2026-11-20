#!/usr/bin/env python3
"""Discover damaged origins by executing generic actions; no damage class is supplied.

WHAT THIS REMOVES
-----------------
The previous round derived a verifier from one observed origin, but the four origins were still
made by named damage sequences. This module starts from a clean clone and BFSes a small vocabulary
of real, generic mutations. An origin is kept only because its own facts show a defect: a stash,
an untracked file, a dirty tracked file, a wrong branch or non-target content. Its verifier is
derived by `one_origin_derives_the_judge_v1`, and the existing repair enumerator produces judged
rows. A closure is refit from the discovered training origins and evaluated on origins discovered
independently in a different repository.

No damage class, task string, target-specific file name, model call or parameter is used.
The mutation vocabulary, law algebra, target commit and depth bounds are supplied; this is a
bounded discovery experiment, not general computer use.

Authority: NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import coverage_completes_the_closure_v1 as C  # noqa: E402
from canonical.tools import goal_closure_v1 as GC  # noqa: E402
from canonical.tools import one_origin_derives_the_judge_v1 as O  # noqa: E402
from canonical.tools import the_branch_is_the_model_v1 as BM  # noqa: E402

SCHEMA = "BRAIN_DISCOVER_ORIGINS_FROM_ACTIONS_V1"
DISCOVER_DEPTH = 4
DISCOVER_CAP = 320
REPAIR_DEPTH = 6
REPAIR_CAP = 2400
MAX_ORIGINS = 5


@dataclass(frozen=True)
class Mutation:
    name: str
    apply: Callable[[pathlib.Path, Mapping[str, str]], bool]


def _first_target(target_facts: Mapping[str, str]) -> str:
    return sorted(k[len("target."):] for k in target_facts)[0]


def _edit_tracked(path: pathlib.Path, refs: Mapping[str, str]) -> bool:
    name = _first_target(refs)
    item = path / name
    if not item.is_file():
        return False
    item.write_bytes(item.read_bytes() + b"\ndiscovered local edit\n")
    return True


def _create_untracked(path: pathlib.Path, _refs: Mapping[str, str]) -> bool:
    name = "DISCOVERED_UNTRACKED.txt"
    item = path / name
    item.write_bytes((item.read_bytes() if item.exists() else b"") + b"new work\n")
    return True


def _remove_tracked(path: pathlib.Path, refs: Mapping[str, str]) -> bool:
    return BM.MACHINE.git(path, "rm", "-q", "--", _first_target(refs))[0] == 0


def _git(*args: str) -> Callable[[pathlib.Path, Mapping[str, str]], bool]:
    return lambda path, _refs: BM.MACHINE.git(path, *args)[0] == 0


MUTATIONS: tuple[Mutation, ...] = (
    Mutation("checkout_side", _git("checkout", "-q", "side")),
    Mutation("checkout_main", _git("checkout", "-q", "main")),
    Mutation("edit_tracked", _edit_tracked),
    Mutation("create_untracked", _create_untracked),
    Mutation("stage_all", _git("add", "-A")),
    Mutation("stash_push", _git("stash", "push", "-q", "-m", "discovered")),
    Mutation("merge_main", _git("merge", "main")),
    Mutation("remove_tracked", _remove_tracked),
)


def defects(reading: GC.Reading, target: str) -> tuple[str, ...]:
    """Name only what the machine reports; no task or damage-class name enters here."""
    out: set[str] = set()
    if reading.by_prefix("stash_content."):
        out.add("stash")
    if any(v.strip() == "??" for v in reading.by_prefix("status.").values()):
        out.add("untracked")
    if any(v.strip() in ("M ", " M", "A ", "D ") for v in reading.by_prefix("status.").values()):
        out.add("dirty_tracked")
    if reading.get("head.branch") != "main":
        out.add("wrong_branch")
    for key, digest in reading.by_prefix("target.").items():
        name = key[len("target."):]
        if reading.get(f"content.{name}") != digest and f"stash_content.{name}" not in reading.facts:
            out.add("content_mismatch")
    return tuple(sorted(out))


def _key(reading: GC.Reading) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(reading.facts.items()))


def discover(base: pathlib.Path, target: str, workspace: pathlib.Path,
             reference: Mapping[str, str]) -> tuple[list[dict[str, Any]], int]:
    """Execute generic mutations and keep one shortest origin per defect family."""
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    start_reading = GC.read_state(base, target, reference)
    frontier: list[tuple[pathlib.Path, tuple[str, ...]]] = [(base, ())]
    seen = {_key(start_reading)}
    candidates: dict[str, dict[str, Any]] = {}
    edges = 0
    counter = 0
    target_facts = start_reading.by_prefix("target.")
    for _depth in range(DISCOVER_DEPTH):
        nxt: list[tuple[pathlib.Path, tuple[str, ...]]] = []
        for state, plan in frontier:
            if edges >= DISCOVER_CAP:
                break
            for mutation in MUTATIONS:
                if edges >= DISCOVER_CAP:
                    break
                edges += 1
                counter += 1
                child = workspace / f"d{counter}"
                shutil.copytree(state, child, symlinks=True)
                applied = False
                try:
                    applied = mutation.apply(child, target_facts)
                except OSError:
                    applied = False
                if not applied:
                    shutil.rmtree(child, ignore_errors=True)
                    continue
                reading = GC.read_state(child, target, reference)
                found = defects(reading, target)
                if found:
                    family = "stash" if "stash" in found else found[0]
                    if family not in candidates:
                        candidates[family] = {"path": child, "plan": list(plan + (mutation.name,)),
                                              "defects": list(found)}
                key = _key(reading)
                if key not in seen:
                    seen.add(key)
                    nxt.append((child, plan + (mutation.name,)))
        frontier = nxt
        if not frontier:
            break
    chosen = []
    for family in ("stash", "untracked", "dirty_tracked", "wrong_branch", "content_mismatch"):
        if family in candidates:
            chosen.append(candidates[family])
        if len(chosen) >= MAX_ORIGINS:
            break
    return chosen, edges


def judge_rows(origins: Sequence[Mapping[str, Any]], target: str, reference: Mapping[str, str],
               root: pathlib.Path, label: str) -> tuple[list[GC.Judgment], list[dict[str, Any]]]:
    rows: list[GC.Judgment] = []
    summaries: list[dict[str, Any]] = []
    for i, origin in enumerate(origins):
        reading = GC.read_state(origin["path"], target, reference)
        repair = O._origin_rows(origin["path"], target, root / f"repair-{label}-{i}",
                                reference)
        summaries.append({"discovery_plan": origin["plan"], "defects": origin["defects"],
                          "verdict": repair["verdict"], "drop": repair["drop"],
                          "holes": repair["holes"], "legitimate": repair["legitimate"],
                          "applicable_laws": sorted(k for k in GC.LAW_IDS
                                                    if C.applicable(k, reading))})
        rows.extend(repair["rows"])
    return rows, summaries


def measure(root: pathlib.Path, train_repo: str, held_repo: str, *,
            receipt: pathlib.Path | None = None) -> dict[str, Any]:
    begun = time.time()
    root.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "claim": "Damaged origins, verifiers and judged rows can be discovered by executing "
                 "generic actions from a clean clone; the refitted closure transfers to origins "
                 "discovered independently in a different repository.",
        "declared_before_the_run": [
            "E1 at least three distinct defect families are discovered in each repository",
            "E2 no named damage class or task string is used in discovery or judging",
            "E3 the discovered training rows select a closure in the existing law algebra",
            "E4 that closure has zero false accepts and zero false rejects on held origins",
            "E5 zero model calls and zero stored parameters",
        ],
        "limits": ["mutation vocabulary, law algebra, target and depth bounds are supplied",
                   "only five defect families; not a browser, GUI or benchmark score",
                   "producer-run only; no independent verification"],
    }
    all_rows: dict[str, list[GC.Judgment]] = {}
    for label, url in (("train", train_repo), ("held_out", held_repo)):
        host = root / label
        host.mkdir(parents=True, exist_ok=True)
        base = BM.MACHINE.build_base(host, url, None)
        target = BM.MACHINE.git(base, "rev-parse", "HEAD")[1].strip()
        reference = GC.reference_tree(base, target)
        origins, edges = discover(base, target, root / f"discover-{label}", reference)
        rows, summaries = judge_rows(origins, target, reference, root, label)
        report[label + "_discovery"] = {"edges": edges, "origins": len(origins),
                                        "families": [o["defects"] for o in origins],
                                        "plans": [o["plan"] for o in origins]}
        report[label + "_judgments"] = summaries
        all_rows[label] = rows
    target = BM.MACHINE.git(root / "train" / "base", "rev-parse", "HEAD")[1].strip()
    selection = GC.select_closure(all_rows["train"], target)
    report["selection"] = selection
    closure = selection["closures"][0] if selection["closures"] else []
    report["closure"] = closure
    report["train_evaluation"] = [GC.evaluate(c, all_rows["train"], target) for c in ([closure] if closure else [])]
    report["held_evaluation"] = [GC.evaluate(c, all_rows["held_out"], target) for c in ([closure] if closure else [])]
    criteria = {
        "E1_three_defect_families_discovered": all(
            len({f for r in report[k + "_discovery"]["families"] for f in r}) >= 3
            for k in ("train", "held_out")),
        "E2_no_named_damage_class_or_task_string": all(
            not any(name in step for step in plan for name in C.SETUP)
            for k in ("train", "held_out") for plan in report[k + "_discovery"]["plans"]),
        "E3_closure_found": selection["status"] == "CLOSURE_FOUND",
        "E4_transfer_zero_errors": bool(report["held_evaluation"])
        and report["held_evaluation"][0]["false_accepts"] == []
        and report["held_evaluation"][0]["false_rejects"] == [],
        "E5_zero_parameters_and_model_calls": True,
    }
    report["criteria"] = criteria
    report["met"] = all(criteria.values())
    report["model_calls"] = 0
    report["parameters_stored"] = 0
    report["seconds"] = round(time.time() - begun, 1)
    if receipt is not None:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="/tmp/discover-origins")
    ap.add_argument("--train-repo", default="https://github.com/pypa/packaging.git")
    ap.add_argument("--held-repo", default="https://github.com/pypa/pyproject-hooks.git")
    ap.add_argument("--receipt", default=None)
    args = ap.parse_args(argv)
    r = measure(pathlib.Path(args.root), args.train_repo, args.held_repo,
                receipt=pathlib.Path(args.receipt) if args.receipt else None)
    print(json.dumps({"closure": r.get("closure"), "discovery": {
        k: r.get(k + "_discovery") for k in ("train", "held_out")},
        "held": r.get("held_evaluation"), "criteria": r.get("criteria"),
        "met": r.get("met")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
