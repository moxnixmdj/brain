#!/usr/bin/env python3
"""Selective-risk evaluator: report coverage AND error, or report nothing.

A single pass rate hides the only number that matters for a system that is
allowed to refuse: *among the cases it chose to answer*, how often was it
wrong? Every benchmark in the 2026 coding-agent crisis is a victim of the
opposite habit -- aggregate scores over a fixed set, with no abstention
accounted for and a verifier nobody audited. This tool refuses that shape.

It reports the standard selective-prediction triple, with denominators:

    coverage        = answered / total
    selective error = wrong answered / answered       (risk on the accepted set)
    abstention rate = unanswered / total

swept over the router's own confidence, producing a risk-coverage curve
and its area (AURC, lower is better). The router's confidence is routing
coverage -- an evidence-completeness signal, not a model logit, which is
why it is meaningful to sweep.

Two gates, both fail-closed, and both deliberate:

1. ``headline_reportable`` is False unless every task is post-cutoff mined.
   Hand-authored tasks measure whether a contract holds; they cannot
   measure generalisation. The tool says so instead of letting a flattering
   number escape.
2. An answered task counts only if the route was confident AND the engine
   matches the expectation. Answering the wrong thing is an error, not a
   partial credit -- no soft scoring.

Usage:
    python3 canonical/tools/selective_risk_eval_v1.py
    python3 canonical/tools/selective_risk_eval_v1.py --json out.json
    python3 canonical/tools/selective_risk_eval_v1.py --threshold 0.5

Authority NONE. Reads the model, runs routes, writes nothing unless asked.
Grants no capability, changes no scoreboard, spends nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TASK_SET = ROOT / "canonical/verification/FRONTIER_FRESH_TASK_SET_20261126_V1.json"


def _aurc(points: list[tuple[float, float]]) -> float | None:
    """Trapezoidal area under the risk-coverage curve. Lower is better.

    Points are (coverage, risk). AURC is only defined when at least two
    distinct coverage levels exist; otherwise it returns None rather than a
    meaningless zero.
    """
    pts = sorted({(round(c, 6), round(r, 6)) for c, r in points})
    if len(pts) < 2:
        return None
    area = 0.0
    for (c0, r0), (c1, r1) in zip(pts, pts[1:]):
        area += (c1 - c0) * (r0 + r1) / 2.0
    return round(area, 6)


def evaluate(*, model: Any = None, task_set: Path = TASK_SET, thresholds: list[float] | None = None) -> dict[str, Any]:
    if model is None:
        from canonical.runtime.brain_unified_model_v1 import open_model

        model = open_model()
    doc = json.loads(task_set.read_text(encoding="utf-8"))
    tasks = list(doc.get("tasks") or [])
    if not tasks:
        raise ValueError("TASK_SET_EMPTY")

    rows: list[dict[str, Any]] = []
    for task in tasks:
        goal = str(task["goal"])
        routing = model.route(goal)
        confidence = float(routing.get("coverage") or 0.0)
        best = routing.get("best") or {}
        best_id = str(best.get("id") or "")
        cls = str(task.get("class") or "").upper()
        if cls == "ABSTAIN":
            correct = not routing["confident"]
            decided_correctly_when_answered = False
        else:
            expected = str(task.get("expect_engine") or "")
            correct = routing["confident"] and best_id == expected
            decided_correctly_when_answered = correct
        rows.append(
            {
                "id": str(task["id"]),
                "class": cls,
                "domain": str(task.get("domain") or ""),
                "goal": goal,
                "confidence": round(confidence, 6),
                "router_confident": bool(routing["confident"]),
                "best": best_id,
                "expect_engine": str(task.get("expect_engine") or ""),
                "correct_if_answered": decided_correctly_when_answered,
                # For the sweep, "answered" means the router committed.
                # An ABSTAIN-class task the router commits to is an error.
                "answer_is_correct": decided_correctly_when_answered,
            }
        )

    if thresholds is None:
        thresholds = [0.0, 0.2, 0.3, 0.34, 0.4, 0.5, 0.57, 0.7, 0.8, 0.9]

    curve: list[dict[str, Any]] = []
    for tau in thresholds:
        accepted = [r for r in rows if r["confidence"] >= tau]
        answered = len(accepted)
        wrong = sum(1 for r in accepted if not r["answer_is_correct"])
        curve.append(
            {
                "threshold": tau,
                "answered": answered,
                "coverage": round(answered / len(rows), 4),
                "selective_error": round(wrong / answered, 4) if answered else None,
                "abstention_rate": round(1 - answered / len(rows), 4),
            }
        )

    # The router's own operating point: what it actually does with no tuning.
    committed = [r for r in rows if r["router_confident"]]
    committed_wrong = sum(1 for r in committed if not r["answer_is_correct"])
    committed_correct = len(committed) - committed_wrong

    provenance = doc.get("provenance") or {}
    mined = str(provenance.get("kind") or "").upper() == "POST_CUTOFF_MINED" and bool(
        provenance.get("mined_after")
    )
    reportable = bool(mined)

    return {
        "schema": "BRAIN_SELECTIVE_RISK_EVAL_V1",
        "task_set": str(doc.get("set_id") or task_set.name),
        "model_digest": getattr(model, "digest", None),
        "tasks": len(rows),
        "operating_point": {
            "answered": len(committed),
            "coverage": round(len(committed) / len(rows), 4),
            "correct_answered": committed_correct,
            "wrong_answered": committed_wrong,
            "selective_error": (
                round(committed_wrong / len(committed), 4) if committed else None
            ),
            "abstention_rate": round(1 - len(committed) / len(rows), 4),
        },
        "risk_coverage_curve": curve,
        "aurc": _aurc(
            [(p["coverage"], p["selective_error"]) for p in curve if p["selective_error"] is not None]
        ),
        "provenance": provenance,
        "headline_reportable": reportable,
        "headline_blocked_reason": (
            None
            if reportable
            else "TASKS_NOT_POST_CUTOFF_MINED__CONTRACT_CHECK_ONLY_NOT_A_FRONTIER_SCORE"
        ),
        "rows": rows,
        "authority": "NONE",
        "non_claims": [
            "NOT_A_FRONTIER_BENCHMARK_SCORE",
            "NOT_AN_INDEPENDENT_VERIFICATION__SANDBOX_MEASUREMENT_ONLY",
            "TASKS_ARE_HAND_AUTHORED_UNLESS_PROVENANCE_SAYS_OTHERWISE",
        ],
    }


def render(report: dict[str, Any]) -> str:
    op = report["operating_point"]
    out: list[str] = []
    out.append("SELECTIVE RISK EVALUATION")
    out.append(f"  task set     {report['task_set']}  ({report['tasks']} tasks)")
    out.append(f"  model digest {report['model_digest']}")
    out.append("")
    out.append("  operating point (router commits, no tuning)")
    out.append(f"    answered           {op['answered']}/{report['tasks']}")
    out.append(f"    coverage           {op['coverage']:.2%}")
    out.append(f"    selective error    {op['selective_error']:.2%}  ({op['wrong_answered']} wrong of {op['answered']} answered)")
    out.append(f"    abstention rate    {op['abstention_rate']:.2%}")
    out.append("")
    out.append("  risk-coverage curve")
    out.append(f"    {'tau':>5} {'answered':>8} {'coverage':>9} {'sel.err':>8} {'abstain':>8}")
    for point in report["risk_coverage_curve"]:
        err = "-" if point["selective_error"] is None else f"{point['selective_error']:.2%}"
        out.append(
            f"    {point['threshold']:>5.2f} {point['answered']:>8} "
            f"{point['coverage']:>9.2%} {err:>8} {point['abstention_rate']:>8.2%}"
        )
    aurc = report["aurc"]
    out.append("")
    out.append(f"  AURC (lower is better)  {'undefined' if aurc is None else f'{aurc:.4f}'}")
    out.append("")
    if report["headline_reportable"]:
        out.append("  HEADLINE: reportable (post-cutoff mined tasks)")
    else:
        out.append("  HEADLINE: BLOCKED -- " + str(report["headline_blocked_reason"]))
        out.append("  This measures whether the routing contract holds. It is not a")
        out.append("  frontier score, and it must not be quoted as one.")
    out.append("")
    out.append("  AUTHORITY NONE -- sandbox measurement, not a receipt")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task-set", default=str(TASK_SET))
    ap.add_argument("--json", default="")
    ap.add_argument("--threshold", type=float, default=None, help="report one extra operating point")
    ns = ap.parse_args(argv)

    thresholds = None
    if ns.threshold is not None:
        thresholds = [0.0, 0.2, 0.3, 0.34, 0.4, 0.5, 0.57, 0.7, 0.8, 0.9, ns.threshold]
    report = evaluate(task_set=Path(ns.task_set), thresholds=thresholds)
    print(render(report))
    if ns.json:
        Path(ns.json).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\n  wrote {ns.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
