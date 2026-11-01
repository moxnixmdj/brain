#!/usr/bin/env python3
"""Does the system's model of itself predict anything?

WHY THIS EXISTS
---------------
Every other measurement in this tree asks whether the *work* was real: an inspector re-opens the
artifact and refuses the claim. None of them ask whether the system's *belief about its own
performance* was true. A system that says "I will succeed at this" and is right, and one that says
the same thing and is wrong, are identical from the outside until somebody scores the predictions.
That score is what this module computes.

WHAT IT MEASURES
----------------
Before an attempt, the caller states `p` -- its probability that the independently re-inspected
verdict will be PASS. After the attempt is settled by the acceptance path, the pair `(p, outcome)`
is recorded. From the pairs:

  brier           mean((p - outcome)^2)          lower is better
  brier_base      the same score for a predictor that always says the observed base rate
  skill           1 - brier / brier_base         > 0 means better than knowing nothing
  discrimination  mean(p | pass) - mean(p | fail)  how far the belief separates the two outcomes
  overconfidence  mean(p) - mean(outcome)         positive means it claims more than it delivers

THE RULE THAT MAKES THIS FALSIFIABLE
------------------------------------
A second way to fake it is a curated diet: declare predictions only on the tasks you expect to pass,
and the ledger looks calibrated while saying nothing about the tasks you fail. So the best verdict is
capped by the sample: fewer than MIN_HARD_FRACTION predictions below HARD_PREDICTION_BELOW and the
result can never be CALIBRATED -- it is CALIBRATED_ONLY_ON_EASY_TASKS, and a sample that contains
only one outcome cannot be scored for discrimination at all.

A constant predictor -- always 0.9, always "yes" -- cannot beat the base rate and has zero
discrimination. So a system whose self-model is decoration is not merely unimpressive here, it is
*classified* as decoration: NO_DISCRIMINATION or WORSE_THAN_BASE_RATE. A module that only reported
a Brier score could be passed by a lucky constant; this one cannot.

WHAT THIS DOES NOT CLAIM
------------------------
It does not measure sentience, experience, or selfhood. It measures whether stated expectations
about own performance are accurate. That is a precondition and the whole of what is checkable; the
rest is not something this or any module in this tree can settle, and the docstring says so rather
than leaving a reader to infer it.

Nothing here calls a model. Nothing here spends. The verdict fails closed.

    python3 canonical/runtime/self_prediction_calibration_v1.py --ledger path/to/ledger.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_SELF_PREDICTION_CALIBRATION_V1"
LEDGER_SCHEMA = "PROJECT_BRAIN_SELF_PREDICTION_LEDGER_V1"

DEFAULT_LEDGER = pathlib.Path(__file__).resolve().parent / "state" / "self_prediction_ledger.jsonl"

# A verdict is only issued on enough observations to mean something.
MIN_SETTLED = 20
# A belief that does not separate outcomes at all is decoration, not a self-model.
MIN_DISCRIMINATION = 0.05
# Claiming more than this beyond the delivered rate is systematically overconfident.
MAX_OVERCONFIDENCE = 0.15
# Below this probability the system is saying it expects to fail.
HARD_PREDICTION_BELOW = 0.5
# A sample with fewer than this share of hard predictions is a curated diet. It can be scored, but
# it cannot certify calibration, because the errors it would have caught were never attempted.
MIN_HARD_FRACTION = 0.25

VERDICTS = (
    "INSUFFICIENT_EVIDENCE",
    "UNREPRESENTATIVE_SAMPLE",
    "NO_DISCRIMINATION",
    "WORSE_THAN_BASE_RATE",
    "SYSTEMATICALLY_OVERCONFIDENT",
    "SYSTEMATICALLY_UNDERCONFIDENT",
    "CALIBRATED_ONLY_ON_EASY_TASKS",
    "CALIBRATED",
)


class CalibrationError(ValueError):
    """The caller tried to record something that cannot be scored honestly."""


def _probability(value: Any, *, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalibrationError(f"{what} must be a number in [0,1], got {value!r}")
    p = float(value)
    if math.isnan(p) or math.isinf(p):
        raise CalibrationError(f"{what} must be finite")
    if not 0.0 <= p <= 1.0:
        raise CalibrationError(f"{what} must be in [0,1], got {p}")
    return p


@dataclass
class Prediction:
    record_id: str
    capability_id: str
    predicted_pass_probability: float
    predicted_at_unix: float
    claimed_reason: str = ""
    settled: bool = False
    outcome_pass: bool | None = None
    settled_at_unix: float | None = None
    inspector: str = ""

    def as_row(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "capability_id": self.capability_id,
            "predicted_pass_probability": self.predicted_pass_probability,
            "predicted_at_unix": self.predicted_at_unix,
            "claimed_reason": self.claimed_reason,
            "settled": self.settled,
            "outcome_pass": self.outcome_pass,
            "settled_at_unix": self.settled_at_unix,
            "inspector": self.inspector,
        }


class Ledger:
    """Append-only JSONL. A record is never edited in place after it is settled."""

    def __init__(self, path: pathlib.Path | str | None = None):
        # The acceptance path settles predictions from inside a long run; an operator needs to be
        # able to point that at a scratch file without editing code.
        override = os.environ.get("BRAIN_SELF_PREDICTION_LEDGER")
        self.path = pathlib.Path(path or override or DEFAULT_LEDGER)

    def _rows(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        latest: dict[str, dict[str, Any]] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rid = row.get("record_id")
            if not rid:
                continue
            # Settling appends rather than edits, so the last line for a record is its state.
            latest[rid] = row
        return list(latest.values())

    def predict(self, *, capability_id: str, predicted_pass_probability: Any,
                claimed_reason: str = "") -> dict[str, Any]:
        if not str(capability_id or "").strip():
            raise CalibrationError("capability_id is required")
        p = _probability(predicted_pass_probability, what="predicted_pass_probability")
        pred = Prediction(
            record_id=uuid.uuid4().hex,
            capability_id=str(capability_id),
            predicted_pass_probability=p,
            predicted_at_unix=time.time(),
            claimed_reason=str(claimed_reason)[:2000],
        )
        self._append(pred.as_row())
        return pred.as_row()

    def settle(self, record_id: str, *, outcome_pass: bool, inspector: str) -> dict[str, Any]:
        """Settle a prediction with an INDEPENDENT verdict.

        The value is refused when no inspector is named: a prediction scored by the party that made
        it is the self-certification this tree spends most of its guard rails removing.
        """
        if not isinstance(outcome_pass, bool):
            raise CalibrationError("outcome_pass must be a bool from an independent verdict")
        if not str(inspector or "").strip():
            raise CalibrationError("INSPECTOR_REQUIRED: a prediction cannot be scored by its author")
        current = {r["record_id"]: r for r in self._rows()}.get(record_id)
        if current is None:
            raise CalibrationError(f"unknown record_id {record_id!r}")
        if current.get("settled"):
            raise CalibrationError("PREDICTION_ALREADY_SETTLED")
        row = dict(current)
        row.update({
            "settled": True,
            "outcome_pass": outcome_pass,
            "settled_at_unix": time.time(),
            "inspector": str(inspector),
        })
        self._append(row)
        return row

    def _append(self, row: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    def settled_rows(self) -> list[dict[str, Any]]:
        return [r for r in self._rows() if r.get("settled") and r.get("outcome_pass") is not None]


def score(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Score settled (probability, outcome) pairs. Fails closed on an empty sample."""
    pairs = []
    for row in rows:
        p = row.get("predicted_pass_probability")
        o = row.get("outcome_pass")
        if isinstance(p, bool) or not isinstance(p, (int, float)):
            continue
        if not isinstance(o, bool):
            continue
        pairs.append((float(p), 1.0 if o else 0.0))
    n = len(pairs)
    if n == 0:
        return {"schema": SCHEMA, "n": 0, "verdict": "INSUFFICIENT_EVIDENCE",
                "reason": "NO_SETTLED_PREDICTIONS"}
    brier = sum((p - o) ** 2 for p, o in pairs) / n
    base_rate = sum(o for _, o in pairs) / n
    brier_base = sum((base_rate - o) ** 2 for _, o in pairs) / n
    skill = 0.0 if brier_base == 0 else 1.0 - brier / brier_base
    mean_p = sum(p for p, _ in pairs) / n
    passed = [p for p, o in pairs if o == 1.0]
    failed = [p for p, o in pairs if o == 0.0]
    discrimination = (sum(passed) / len(passed) - sum(failed) / len(failed)
                      if passed and failed else 0.0)
    overconfidence = mean_p - base_rate
    hard = sum(1 for p, _ in pairs if p < HARD_PREDICTION_BELOW)
    hard_fraction = hard / n
    both_classes = bool(passed) and bool(failed)
    verdict, reason = _verdict(n, skill, discrimination, overconfidence, hard_fraction, both_classes)
    return {
        "schema": SCHEMA,
        "n": n,
        "brier": round(brier, 6),
        "brier_base_rate": round(brier_base, 6),
        "skill_over_base_rate": round(skill, 6),
        "discrimination": round(discrimination, 6),
        "mean_predicted": round(mean_p, 6),
        "observed_pass_rate": round(base_rate, 6),
        "overconfidence": round(overconfidence, 6),
        # How much of the sample the system expected to fail. A clean score on a diet of easy tasks
        # is not calibration, so the number travels with the verdict that depends on it.
        "hard_predictions": hard,
        "hard_fraction": round(hard_fraction, 6),
        "required_hard_fraction": MIN_HARD_FRACTION,
        "outcome_classes_observed": int(both_classes) + (0 if both_classes else
                                                          (1 if (passed or failed) else 0)),
        "verdict": verdict,
        "reason": reason,
        # Said here so a reader of the JSON cannot mistake the scope of the number.
        "measures": "accuracy of stated expectations about own performance",
        "does_not_measure": "sentience, experience, selfhood",
    }


def _verdict(n: int, skill: float, discrimination: float, overconfidence: float,
             hard_fraction: float = 1.0, both_classes: bool = True) -> tuple[str, str]:
    if n < MIN_SETTLED:
        return "INSUFFICIENT_EVIDENCE", f"SETTLED_PREDICTIONS_{n}_BELOW_{MIN_SETTLED}"
    if not both_classes:
        # Without both outcomes there is no contrast to measure, so no claim either way.
        return "UNREPRESENTATIVE_SAMPLE", "ONLY_ONE_OUTCOME_CLASS_OBSERVED"
    if discrimination <= MIN_DISCRIMINATION:
        # A constant predictor lands here: it separates nothing, whatever its Brier score.
        return "NO_DISCRIMINATION", "BELIEF_DOES_NOT_SEPARATE_PASS_FROM_FAIL"
    if skill <= 0.0:
        return "WORSE_THAN_BASE_RATE", "NO_BETTER_THAN_ALWAYS_PREDICTING_THE_BASE_RATE"
    if overconfidence > MAX_OVERCONFIDENCE:
        return "SYSTEMATICALLY_OVERCONFIDENT", "CLAIMS_MORE_THAN_IT_DELIVERS"
    if overconfidence < -MAX_OVERCONFIDENCE:
        return "SYSTEMATICALLY_UNDERCONFIDENT", "DELIVERS_MORE_THAN_IT_CLAIMS"
    if hard_fraction < MIN_HARD_FRACTION:
        # The numbers look good, but the sample never asked the system to predict its own failure.
        return ("CALIBRATED_ONLY_ON_EASY_TASKS",
                f"HARD_PREDICTION_FRACTION_{hard_fraction:.2f}_BELOW_{MIN_HARD_FRACTION}")
    return "CALIBRATED", "BEATS_BASE_RATE_AND_SEPARATES_OUTCOMES"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    report = score(Ledger(ns.ledger).settled_rows())
    if ns.json:
        print(json.dumps(report, indent=1, sort_keys=True))
    else:
        print(report["schema"])
        for key in ("n", "brier", "brier_base_rate", "skill_over_base_rate", "discrimination",
                    "mean_predicted", "observed_pass_rate", "overconfidence",
                    "hard_predictions", "hard_fraction"):
            print(f"  {key:<22} {report.get(key)}")
        print(f"  verdict                {report['verdict']} ({report['reason']})")
        print(f"  measures               {report['measures']}")
        print(f"  does not measure       {report['does_not_measure']}")
    return 0 if report["verdict"] != "INSUFFICIENT_EVIDENCE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
