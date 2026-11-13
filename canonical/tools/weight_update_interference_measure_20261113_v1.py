#!/usr/bin/env python3
"""The same 32 verified experiences, pushed into weights two ways.

The owner's question this round: token-space learning is real but the weights never change, so
should we just fine-tune on our own execution traces? This runs that experiment on the only
weight-space learner this tree has, with no LLM and no GPU, and reads the result with an
independent judge: the typed parser that actually answers the goals.

Arm A -- naive, exactly what `solve_task` does today: one gradient step per verified experience.
Arm B -- gated: the step is applied to a copy first and kept only if it improves agreement with the
         parser on goals it was not trained on and breaks none that were already right.

Both arms see the same stream in the same order. Every goal's label is re-derived by `parse_task`.
The trained goal is always excluded from that step's probe set.

    python3 canonical/tools/weight_update_interference_measure_20261113_v1.py --json

Authority: NONE. Producer-run sandbox measurement, $0, zero model calls. It is not a claim about
LLM fine-tuning; it is a claim about what an ungated update receipt can and cannot see.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import weight_update_admission_v1 as W  # noqa: E402

SCHEMA = "PROJECT_BRAIN_WEIGHT_UPDATE_INTERFERENCE_MEASURE_20261113_V1"


def _run_naive(goals: list[str], probes: list[W.Probe], tmp: pathlib.Path) -> dict[str, Any]:
    model = W.fresh_model(tmp / "naive")
    (tmp / "naive").mkdir(parents=True, exist_ok=True)
    by_goal = {p.goal: p for p in probes}
    trained: set[str] = set()
    right = W._correct(model, probes)
    lost_total = 0
    receipts_positive = 0
    for goal in goals:
        probe = by_goal[goal]
        before = W._correct(model, probes)
        receipt = model.update_from_experience(goal, probe.operation, probe.concept, probe.domain,
                                              persist=False)
        after = W._correct(model, probes)
        lost_total += len(before - after)
        receipts_positive += int(receipt["loss_delta"] > 0)
        trained.add(goal)
        right = after
    return {
        "updates_applied": len(goals),
        "updates_refused": 0,
        "receipts_reporting_loss_went_down": receipts_positive,
        "agreement_with_parser_at_end": len(right),
        "goals_scored": len(probes),
        "previously_correct_predictions_broken": lost_total,
    }


def _run_gated(goals: list[str], probes: list[W.Probe], tmp: pathlib.Path) -> dict[str, Any]:
    (tmp / "gated").mkdir(parents=True, exist_ok=True)
    model = W.fresh_model(tmp / "gated")
    by_goal = {p.goal: p for p in probes}
    trained: set[str] = set()
    verdicts: dict[str, int] = {W.ADMIT: 0, W.REFINE: 0, W.REJECT: 0, W.REFUSED: 0}
    applied = 0
    lost_total = 0
    unchanged_on_refusal = True
    for goal in goals:
        probe = by_goal[goal]
        step_probes = [W.Probe(p.goal, p.operation, p.concept, p.domain,
                               W.ARCHIVE if p.goal in trained else W.TRANSFER)
                       for p in probes if p.goal != goal]
        report = W.apply_if_admitted(model, goal, probe.operation, probe.concept, probe.domain,
                                     probes=step_probes, persist=False)
        verdicts[report["verdict"]] = verdicts.get(report["verdict"], 0) + 1
        if report.get("applied"):
            applied += 1
            trained.add(goal)
            lost_total += report["counts"]["lost"]
        else:
            unchanged_on_refusal = unchanged_on_refusal and bool(report.get("weights_unchanged"))
    return {
        "updates_applied": applied,
        "updates_refused": len(goals) - applied,
        "verdicts": verdicts,
        "agreement_with_parser_at_end": len(W._correct(model, probes)),
        "goals_scored": len(probes),
        "previously_correct_predictions_broken": lost_total,
        "weights_untouched_on_every_refusal": unchanged_on_refusal,
    }


def measure() -> dict[str, Any]:
    goals = W.stream_goals()
    built = W.probes_from_goals(goals)
    probes = built["probes"]
    scored = [g for g in goals if g in {p.goal for p in probes}]
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        naive = _run_naive(scored, probes, tmp_path)
        gated = _run_gated(scored, probes, tmp_path)
    return {
        "schema": SCHEMA,
        "judge": "canonical.swe_kernel.semantic_generalization_engine_v1.parse_task",
        "substrate": "OnlineParametricPolicyModel: 3 linear heads over 128 hashed text features",
        "stream_length": len(scored),
        "parser_refused_goals": built["refused"],
        "naive_one_step_per_verified_experience": naive,
        "gated_by_admission_on_other_inputs": gated,
        "authority": "NONE",
        "whole_capability_proved": False,
        "not_a_claim_about_llm_fine_tuning": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = measure()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        naive = report["naive_one_step_per_verified_experience"]
        gated = report["gated_by_admission_on_other_inputs"]
        print(f"stream={report['stream_length']} judge={report['judge'].rsplit('.', 1)[-1]}")
        print(f"naive : applied={naive['updates_applied']} "
              f"receipts_saying_loss_went_down={naive['receipts_reporting_loss_went_down']} "
              f"agreement={naive['agreement_with_parser_at_end']}/{naive['goals_scored']} "
              f"broke={naive['previously_correct_predictions_broken']}")
        print(f"gated : applied={gated['updates_applied']} refused={gated['updates_refused']} "
              f"agreement={gated['agreement_with_parser_at_end']}/{gated['goals_scored']} "
              f"broke={gated['previously_correct_predictions_broken']} "
              f"verdicts={gated['verdicts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
