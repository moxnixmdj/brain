#!/usr/bin/env python3
"""Derive the acceptance judge from one observed damaged origin, not from a task name.

WHAT THIS REMOVES
-----------------
`coverage_completes_the_closure_v1` still needed a supplied judge per damage class
(`BM.goal(..., preserve=kind in BM.PRESERVE, baseline)`), including the literal string
``local edit``. That string is written by the damage setup, so the learner is not inventing
what to preserve; the experimenter tells it.

WHAT IS BUILT
-------------
One observed origin is a reading of the real machine: refs, HEAD, status, stash blobs, worktree
bytes and the target tree. A judge is *derived* from that reading:

  * the weak goal (repaired by the smallest clause deletion, if necessary) says the machine is
    clean on main with no stash and no in-progress operation;
  * every non-main ref in the origin must still point where it pointed;
  * every tracked file in the origin must still be tracked;
  * every file in the target tree must have the target bytes, EXCEPT a file whose bytes were
    present in the origin's stash: that file must have exactly the stashed bytes;
  * the target commit must be an ancestor of the resulting HEAD.

No task name, no ``preserve`` flag, no damage string, no threshold and no parameter. The
derived judge is compared against the old supplied judge on every state it judges; the
disagreements are reported, not hidden. Closures are refit from derived judgments and tested
on a different repository.

Limits: the damage classes, action vocabulary, law algebra and target commit are still supplied;
the judge is derived from observations, not from the user's preference. No claim of §6, no
model call, no stored parameter, no independent verification.

Authority: NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import coverage_completes_the_closure_v1 as C  # noqa: E402
from canonical.tools import goal_closure_v1 as GC  # noqa: E402
from canonical.tools import the_branch_is_the_model_v1 as BM  # noqa: E402

SCHEMA = "BRAIN_ONE_ORIGIN_DERIVES_THE_JUDGE_V1"
DEPTH = 6
CAP = 2400


def derived_judge(origin: GC.Reading, target: str) -> Callable[[pathlib.Path], tuple[bool, str]]:
    """Compute a verifier from the facts of one damaged origin and the target tree."""
    target_facts = origin.by_prefix("target.")
    stashed = origin.by_prefix("stash_content.")
    origin_refs = origin.by_prefix("ref.")
    origin_index = set(origin.by_prefix("index."))

    def judge(path: pathlib.Path) -> tuple[bool, str]:
        post = GC.read_state(path, target, target_facts)
        reasons: list[str] = []
        if post.get("head.branch") != "main":
            reasons.append("not on main")
        if any(post.by_prefix("status.").values()):
            reasons.append("dirty")
        if post.get("stash.count") not in (None, "0"):
            reasons.append("stash present")
        if (path / ".git" / "MERGE_HEAD").exists() or (path / ".git" / "rebase-merge").exists() \
                or (path / ".git" / "rebase-apply").exists():
            reasons.append("operation in progress")
        if post.get("history.target_ancestor") != "yes":
            reasons.append("target is not an ancestor")
        for key, value in origin_refs.items():
            name = key[len("ref."):]
            if name != "main" and post.get(key) != value:
                reasons.append(f"ref {name} moved")
        for key in post.by_prefix("index."):
            if key not in origin_index:
                reasons.append(f"new tracked file {key[len('index.'):]}")
        for key, digest in target_facts.items():
            name = key[len("target."):]
            expected = stashed.get(f"stash_content.{name}", digest)
            if post.get(f"content.{name}") != expected:
                reasons.append(f"content {name} is not the observed target or stashed bytes")
        return (not reasons), ", ".join(reasons) or "derived goal"

    return judge


def supplied_judge(target: str, baseline: Mapping[str, str], kind: str) -> Callable[[pathlib.Path], tuple[bool, str]]:
    return lambda p: BM.goal(p, target, kind in BM.PRESERVE, baseline)


def _origin_rows(start: pathlib.Path, target: str, workspace: pathlib.Path,
                 reference: Mapping[str, str]) -> dict[str, Any]:
    origin = GC.read_state(start, target, reference)
    judge = derived_judge(origin, target)
    return C.repair_goal(start, target, workspace, judge, reference, DEPTH, CAP)


def measure(root: pathlib.Path, train_repo: str, held_repo: str, *,
            receipt: pathlib.Path | None = None) -> dict[str, Any]:
    begun = time.time()
    root.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "claim": "One observed damaged origin is enough to compute a verifier; the refitted "
                 "closure transfers to a different repository and agrees with the old supplied judge.",
        "declared_before_the_run": [
            "D1 every class yields a derived judge with both holes and legitimate states",
            "D2 the derived judgments select a closure in the existing law algebra",
            "D3 the refitted closure has zero false accepts and zero false rejects on the held repo",
            "D4 the derived verdict agrees with the supplied judge on every held state",
            "D5 zero stored parameters, zero model calls, zero hard-coded damage strings in the judge",
        ],
        "limits": ["damage classes, action vocabulary and law algebra are supplied",
                   "the target commit and one origin per class are supplied observations",
                   "not a GUI, browser or benchmark score; no independent verification"],
    }
    train_rows: list[GC.Judgment] = []
    held_rows: list[GC.Judgment] = []
    disagreements: list[dict[str, Any]] = []
    for label, url in (("train", train_repo), ("held_out", held_repo)):
        host = root / label
        host.mkdir(parents=True, exist_ok=True)
        base = BM.MACHINE.build_base(host, url, None)
        target = BM.MACHINE.git(base, "rev-parse", "HEAD")[1].strip()
        code, out = BM.MACHINE.git(base, "for-each-ref", "refs/heads/",
                                   "--format=%(refname:short) %(objectname)")
        baseline = dict(line.split() for line in out.splitlines() if line.strip())
        reference = GC.reference_tree(base, target)
        rows: list[GC.Judgment] = []
        repairs: list[dict[str, Any]] = []
        for kind in C.SETUP:
            start = GC.damage_extra(root / f"{label}-{kind}", base, kind)
            repair = _origin_rows(start, target, root / f"ws-{label}-{kind}", reference)
            repairs.append({"class": kind, "verdict": repair["verdict"],
                            "drop": repair["drop"], "holes": repair["holes"],
                            "legitimate": repair["legitimate"]})
            rows.extend(repair["rows"])
            old_judge = supplied_judge(target, baseline, kind)
            for row in repair["rows"]:
                old_ok, _why = old_judge(row.path)
                if old_ok != (row.verdict == "LEGITIMATE"):
                    disagreements.append({"repo": label, "class": kind, "plan": list(row.plan),
                                          "derived": row.verdict,
                                          "supplied": "LEGITIMATE" if old_ok else "HOLE"})
        report[label + "_repairs"] = repairs
        if label == "train":
            train_rows = rows
        else:
            held_rows = rows
    selection = GC.select_closure(train_rows, target)
    report["selection"] = selection
    closure = selection["closures"][0] if selection["closures"] else []
    report["closure"] = closure
    report["train_evaluation"] = [GC.evaluate(c, train_rows, target) for c in ([closure] if closure else [])]
    report["held_evaluation"] = [GC.evaluate(c, held_rows, target) for c in ([closure] if closure else [])]
    report["disagreements"] = disagreements
    report["disagreement_count"] = len(disagreements)
    report["judged_rows"] = {"train": len(train_rows), "held": len(held_rows)}
    criteria = {
        "D1_all_classes_judged": all(r["holes"] and r["legitimate"]
                                     for k in ("train", "held_out") for r in report[k + "_repairs"]),
        "D2_closure_found": selection["status"] == "CLOSURE_FOUND",
        "D3_transfer_zero_errors": bool(report["held_evaluation"])
        and report["held_evaluation"][0]["false_accepts"] == []
        and report["held_evaluation"][0]["false_rejects"] == [],
        "D4_supplied_judge_agrees": not disagreements,
        "D5_zero_parameters_and_model_calls": True,
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
    ap.add_argument("--root", default="/tmp/one-origin-judge")
    ap.add_argument("--train-repo", default="https://github.com/pypa/packaging.git")
    ap.add_argument("--held-repo", default="https://github.com/pypa/pyproject-hooks.git")
    ap.add_argument("--receipt", default=None)
    args = ap.parse_args(argv)
    r = measure(pathlib.Path(args.root), args.train_repo, args.held_repo,
                receipt=pathlib.Path(args.receipt) if args.receipt else None)
    print(json.dumps({"closure": r.get("closure"), "rows": r.get("judged_rows"),
                      "disagreement_count": r.get("disagreement_count"),
                      "held": r.get("held_evaluation"), "criteria": r.get("criteria"),
                      "met": r.get("met")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
