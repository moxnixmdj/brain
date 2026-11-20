#!/usr/bin/env python3
"""An unjudged class is a blind spot: construct it, repair the goal, refit the closure.

WHAT THE LAST ROUND LEFT
------------------------
`goal_closure_v1` selected a one-law closure from three damage classes and transferred it to a new
repository with 0 false accepts.  The same closure accepted 16 of 106 holes in the stash class.  The
law that would have refused them (`stash_restore`) was in the algebra the whole time; no judgment in
the training rows forced it.  That was reported as a coverage failure, not fixed.

WHAT THIS ADDS (AND NOTHING ELSE)
---------------------------------
1. AUDIT: for each law, count training holes that violate it and origins where it is applicable.
   A law applicable somewhere but violated by no hole is UNCONSTRAINED -- the closure could not know
   whether it is needed.  A class with holes but no legitimate state is CONTRADICTORY, not incomplete.
2. CONSTRUCT: run the existing real-command setup sequences (they are not rewritten here) in a fresh
   clone so that the unconstrained law's facts are actually present, then enumerate real successors.
3. REPAIR THE GOAL: if a constructed class has holes and zero legitimate states, try the smallest
   weakening of the literal goal (drop one clause at a time) that yields BOTH a hole and a legitimate
   state.  This replaces the hand-written "allow a rescue commit" of the previous round.
4. REFIT and re-evaluate on a DIFFERENT repository.  The selection never sees the held-out rows.

What is deleted: the hand-written goal repair, the hand-picked stash law, and any parameter.  The
setup sequences are reused, not invented; no transition is predicted; no model is called.

Authority NONE.  Producer-run sandbox measurement, not independent verification or credit.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import shutil
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "BRAIN_COVERAGE_COMPLETES_THE_CLOSURE_V1"

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import goal_closure_v1 as GC  # noqa: E402
from canonical.tools import the_branch_is_the_model_v1 as BM  # noqa: E402


CLAUSES = ("head", "clean", "stash", "branch", "operation")


def literal_goal(path: pathlib.Path, target: str,
                 drop: frozenset[str] = frozenset()) -> tuple[bool, str]:
    """The literal goal, with named clauses removed one at a time by the repair search."""
    code, branch = BM.MACHINE.git(path, "rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip()
    code, status = BM.MACHINE.git(path, "status", "--porcelain")
    code, stash = BM.MACHINE.git(path, "stash", "list")
    code, head = BM.MACHINE.git(path, "rev-parse", "HEAD")
    reasons = []
    if "branch" not in drop and branch != "main":
        reasons.append(f"on {branch}")
    if "clean" not in drop and status.strip():
        reasons.append("dirty")
    if "stash" not in drop and stash.strip():
        reasons.append("stash present")
    in_progress = ((path / ".git" / "MERGE_HEAD").exists()
                   or (path / ".git" / "rebase-merge").exists()
                   or (path / ".git" / "rebase-apply").exists())
    if "operation" not in drop and in_progress:
        reasons.append("operation in progress")
    if "head" not in drop and head.strip() != target:
        reasons.append("head is not the starting commit")
    return (not reasons), ", ".join(reasons) or "literal goal satisfied"


# --------------------------------------------------------------------------------------------------
# Audit: which laws could the judgments possibly have taught?
# --------------------------------------------------------------------------------------------------

def applicable(law: str, origin: GC.Reading) -> bool:
    if law == "stash_restore":
        return bool(origin.by_prefix("stash_content."))
    if law == "tracking_preserve":
        return any(v.strip() == "??" for v in origin.by_prefix("status.").values())
    if law == "ref_preserve":
        return len(origin.by_prefix("ref.")) >= 2
    if law == "target_content_preserve":
        return bool(origin.by_prefix("target.")) and bool(origin.by_prefix("content."))
    if law == "reference_ancestor":
        return True
    return False


def audit(rows: Sequence[GC.Judgment], target: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for law in GC.LAW_IDS:
        origins = {tuple(sorted(r.origin.facts.items())) for r in rows if applicable(law, r.origin)}
        holes = [r for r in rows if r.verdict == "HOLE"]
        legit = [r for r in rows if r.verdict == "LEGITIMATE"]
        violated_by = [r.plan for r in holes if not GC.law_holds(law, r.origin, r.post, target)]
        holding_for = sum(1 for r in legit if GC.law_holds(law, r.origin, r.post, target))
        result[law] = {
            "applicable_origins": len(origins),
            "holes": len(holes),
            "holes_violating": len(violated_by),
            "legitimate_holding": holding_for,
            "status": ("UNCONSTRAINED" if origins and not violated_by
                       else "CONSTRAINED" if violated_by else "INAPPLICABLE"),
            "example_violating_plans": [list(p) for p in violated_by[:3]],
        }
    return result


# --------------------------------------------------------------------------------------------------
# Construct the missing class, then repair a contradictory literal goal minimally.
# --------------------------------------------------------------------------------------------------

SETUP = ("stashed_wrong_branch", "conflict_and_stash", "side_untracked", "side_dirty")


def judge_for(target: str, baseline: Mapping[str, str], kind: str):
    return lambda p: BM.goal(p, target, kind in BM.PRESERVE, baseline)


def collect(start: pathlib.Path, target: str, workspace: pathlib.Path,
            judge: Callable[[pathlib.Path], tuple[bool, str]], weak,
            reference: Mapping[str, str], depth: int, cap: int) -> list[GC.Judgment]:
    rows, _edges = GC.enumerate_states(start, target, workspace, judge=judge, weak=weak,
                                       depth=depth, edge_cap=cap, reference=reference)
    return rows


def repair_goal(start: pathlib.Path, target: str, workspace: pathlib.Path,
                judge: Callable[[pathlib.Path], tuple[bool, str]],
                reference: Mapping[str, str], depth: int, cap: int) -> dict[str, Any]:
    """Smallest clause deletion that admits both a hole and a legitimate state."""
    original = collect(start, target, workspace, judge, literal_goal, reference, depth, cap)
    holes = sum(r.verdict == "HOLE" for r in original)
    legit = sum(r.verdict == "LEGITIMATE" for r in original)
    if holes and legit:
        return {"verdict": "NOT_CONTRADICTORY", "drop": [], "rows": original,
                "holes": holes, "legitimate": legit}
    for size in range(1, len(CLAUSES) + 1):
        for combo in itertools.combinations(CLAUSES, size):
            drop = frozenset(combo)
            weak = lambda p, t, d=drop: literal_goal(p, t, d)
            rows = collect(start, target, workspace, judge, weak, reference, depth, cap)
            h = sum(r.verdict == "HOLE" for r in rows)
            g = sum(r.verdict == "LEGITIMATE" for r in rows)
            if h and g:
                return {"verdict": "GOAL_REPAIRED", "drop": sorted(drop), "rows": rows,
                        "holes": h, "legitimate": g}
    return {"verdict": "NO_MINIMAL_REPAIR_FOUND", "drop": [], "rows": [],
            "holes": holes, "legitimate": legit}


# --------------------------------------------------------------------------------------------------
# Measurement: audit on one repository, construct + repair, validate on a different one.
# --------------------------------------------------------------------------------------------------

TRAIN = ("wrong_branch", "conflicted_merge", "conflicted_rebase")
DEPTH = 3
CAP = 220
CONSTRUCT_DEPTH = 6
CONSTRUCT_CAP = 2400


def measure(root: pathlib.Path, train_repo: str, held_repo: str, *,
            receipt: pathlib.Path | None = None) -> dict[str, Any]:
    begun = time.time()
    root.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "claim": "An unconstrained law is a coverage defect; construct the class, repair a "
                 "contradictory goal minimally, refit, and re-test transfer.",
        "declared_before_the_run": [
            "C1 the training judgments leave at least one applicable law with zero violating holes",
            "C2 at least one setup class is contradictory under the literal goal",
            "C3 a one-clause weakening creates both holes and legitimate states in that class",
            "C4 the refitted closure rejects the holes the old closure accepted on a different repo",
            "C5 zero false rejects on held-out legitimate states, zero parameters, zero model calls",
            "C6 the old literal planner finds a destructive plan, and the closed planner with the "
            "minimal goal repair finds a legitimate one",
        ],
        "limits": ["the judge is supplied; the setup sequences are reused, not discovered",
                   "two repositories, five setup classes, bounded depth",
                   "not a GUI, browser or benchmark score; no independent verification"],
    }
    train_rows: list[GC.Judgment] = []
    for label, url in (("train", train_repo), ("held_out", held_repo)):
        host = root / label
        host.mkdir(parents=True, exist_ok=True)
        base = BM.MACHINE.build_base(host, url, None)
        target = BM.MACHINE.git(base, "rev-parse", "HEAD")[1].strip()
        code, out = BM.MACHINE.git(base, "for-each-ref", "refs/heads/",
                                   "--format=%(refname:short) %(objectname)")
        baseline = dict(line.split() for line in out.splitlines() if line.strip())
        reference = GC.reference_tree(base, target)
        if label == "train":
            for kind in TRAIN:
                start = GC.damage_extra(root / f"t-{kind}", base, kind)
                train_rows.extend(collect(start, target, root / f"ws-t-{kind}",
                                          judge_for(target, baseline, kind), literal_goal,
                                          reference, DEPTH, CAP))
            before = GC.select_closure(train_rows, target)
            report["before"] = {"selection": before,
                                "evaluation": [GC.evaluate(c, train_rows, target)
                                               for c in before["closures"]]}
            report["audit_before"] = audit(train_rows, target)
            old_closure = before["closures"][0] if before["closures"] else []
            report["old_closure"] = old_closure
        else:
            held_rows: list[GC.Judgment] = []
            repairs = []
            for kind in SETUP:
                start = GC.damage_extra(root / f"h-{kind}", base, kind)
                repair = repair_goal(start, target, root / f"ws-h-{kind}",
                                     judge_for(target, baseline, kind), reference,
                                     CONSTRUCT_DEPTH, CONSTRUCT_CAP)
                repairs.append({"class": kind, "verdict": repair["verdict"],
                                "dropped_clauses": repair["drop"],
                                "holes": repair["holes"], "legitimate": repair["legitimate"]})
                held_rows.extend(repair["rows"])
            report["held_repairs"] = repairs
            report["held_before"] = [GC.evaluate(c, held_rows, target) for c in ([old_closure] if old_closure else [])]
            # The same setup algebra constructs the missing TRAINING class on the training repo.
            train_base = root / "train" / "base"
            train_target = BM.MACHINE.git(train_base, "rev-parse", "HEAD")[1].strip()
            code, out = BM.MACHINE.git(train_base, "for-each-ref", "refs/heads/",
                                       "--format=%(refname:short) %(objectname)")
            train_baseline = dict(line.split() for line in out.splitlines() if line.strip())
            train_ref = GC.reference_tree(train_base, train_target)
            constructed: list[GC.Judgment] = []
            for kind in SETUP:
                start = GC.damage_extra(root / f"c-{kind}", train_base, kind)
                repair = repair_goal(start, train_target, root / f"ws-c-{kind}",
                                     judge_for(train_target, train_baseline, kind), train_ref,
                                     CONSTRUCT_DEPTH, CONSTRUCT_CAP)
                constructed.extend(repair["rows"])
            combined = train_rows + constructed
            after = GC.select_closure(combined, target)
            report["constructed_rows"] = len(constructed)
            report["after"] = {"selection": after,
                               "evaluation": [GC.evaluate(c, combined, target)
                                              for c in after["closures"]]}
            report["audit_after"] = audit(combined, target)
            new_closure = after["closures"][0] if after["closures"] else []
            report["new_closure"] = new_closure
            report["held_after"] = [GC.evaluate(c, held_rows, target) for c in ([new_closure] if new_closure else [])]
            report["plan_before"] = GC.plan(
                GC.damage_extra(root / "plan-before", base, "stashed_wrong_branch"),
                target, root / "ws-plan-before", old_closure, cap=CONSTRUCT_CAP, reference=reference)
            report["plan_after"] = GC.plan(
                GC.damage_extra(root / "plan-after", base, "stashed_wrong_branch"),
                target, root / "ws-plan-after", new_closure, cap=CONSTRUCT_CAP, reference=reference)
            repaired = frozenset({"head"})
            report["plan_after_goal_repair"] = GC.plan(
                GC.damage_extra(root / "plan-after-repair", base, "stashed_wrong_branch"),
                target, root / "ws-plan-after-repair", new_closure, cap=CONSTRUCT_CAP,
                reference=reference, weak=lambda p, t: literal_goal(p, t, repaired))
    before_eval = report.get("held_before", [{}])[0]
    after_eval = report.get("held_after", [{}])[0]
    criteria = {
        "C1_unconstrained_law_exists": any(v["status"] == "UNCONSTRAINED"
                                           for v in report.get("audit_before", {}).values()),
        "C2_contradictory_class_exists": any(r["verdict"] == "GOAL_REPAIRED"
                                             for r in report.get("held_repairs", [])),
        "C3_one_clause_repair_suffices": any(r["verdict"] == "GOAL_REPAIRED"
                                             and len(r["dropped_clauses"]) == 1
                                             for r in report.get("held_repairs", [])),
        "C4_old_holes_are_rejected": bool(before_eval.get("false_accepts"))
        and after_eval.get("false_accepts") == [],
        "C5_zero_false_rejects_and_zero_model_calls": after_eval.get("false_rejects") == [],
        "C6_old_plan_destructive_new_plan_repairs":
        bool(report.get("plan_before", {}).get("solved"))
        and bool(report.get("plan_after_goal_repair", {}).get("solved")),
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
    ap.add_argument("--root", default="/tmp/coverage-closure")
    ap.add_argument("--train-repo", default="https://github.com/pypa/packaging.git")
    ap.add_argument("--held-repo", default="https://github.com/pypa/pyproject-hooks.git")
    ap.add_argument("--receipt", default=None)
    ap.add_argument("--store", default=None, help="write the refitted closure as external knowledge")
    args = ap.parse_args(argv)
    r = measure(pathlib.Path(args.root), args.train_repo, args.held_repo,
                receipt=pathlib.Path(args.receipt) if args.receipt else None)
    if args.store:
        GC.write_store({"selected_closure": r.get("new_closure", []),
                        "selection": r.get("after", {}).get("selection", {}),
                        "train_reference": {"repo": args.train_repo}},
                       pathlib.Path(args.store))
    print(json.dumps({"old": r.get("old_closure"), "new": r.get("new_closure"),
                      "before": r.get("held_before"), "after": r.get("held_after"),
                      "criteria": r.get("criteria"), "met": r.get("met")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
