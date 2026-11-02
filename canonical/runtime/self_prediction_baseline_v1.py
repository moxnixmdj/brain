#!/usr/bin/env python3
"""A predictor the system cannot author, to judge the one it does.

WHY THIS EXISTS
---------------
`self_prediction_calibration_v1` scores the system's stated probability of passing its own
independent inspection. Its recorded counterexample is honest about the limit: the *number* is still
the system's claim, so a mildly varying, uninformative probability can nudge the overconfidence term
under the ceiling without any gain in self-knowledge.

The only way to find out whether a self-claim carries information is to compare it against a number
the system did not write. This module computes that number mechanically, from the same inspector
verdicts, using only outcomes that were already settled *before* each attempt:

    baseline_p = (passes + SHRINK * global_rate) / (attempts + SHRINK)

A shrunk pass rate. No model, no learning, no self-report, nothing the system can influence except
by doing work. If the system's claims cannot beat this, its self-model is decoration -- and that
report is the point of the whole exercise, so it is named plainly: WORSE_THAN_EXTERNAL_BASELINE.

ORDER MATTERS AND IS NOT OPTIONAL
---------------------------------
The baseline for an attempt uses only earlier settled attempts. A baseline computed over the whole
history would be scoring the past with knowledge of the future, and would flatter itself on exactly
the kind of drifting performance this is meant to catch.

WHAT THIS DOES NOT DO
---------------------
It does not improve the system. It is a referee for the referee: a way to tell whether the
self-prediction work measures anything. Nothing here calls a model or spends.
"""
from __future__ import annotations

import pathlib
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SELF_PREDICTION_BASELINE_V1"

# Pseudo-counts pulling a thin capability history toward the global rate. Five is enough that one
# lucky pass does not make a capability look reliable, and cheap enough that a real trend shows.
SHRINK = 5.0
# The global rate is smoothed too, toward a neutral 0.5. Without this the baseline chases the last
# outcome: on an alternating pass/fail sequence it predicts 1.0 before every failure and is beaten by
# a constant 0.5 -- measured, and caught by the test that ships with this module. A predictor that is
# confident after one observation is not a baseline, it is a mirror.
GLOBAL_SHRINK = 2.0
NEUTRAL_PRIOR = 0.5
# A claim must beat the baseline by this much Brier to be called informative. Anything inside the
# band is "no better", because a difference that small is indistinguishable from noise on samples
# this size.
MEANINGFUL_MARGIN = 0.02
MIN_SETTLED = 20

VERDICTS = (
    "INSUFFICIENT_EVIDENCE",
    "WORSE_THAN_EXTERNAL_BASELINE",
    "NO_BETTER_THAN_EXTERNAL_BASELINE",
    "CLAIM_BEATS_EXTERNAL_BASELINE",
)


def _chronological(rows: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Settled rows in the order they were settled, so no baseline sees the future."""
    usable = [r for r in rows
              if isinstance(r.get("outcome_pass"), bool)
              and isinstance(r.get("predicted_pass_probability"), (int, float))
              and not isinstance(r.get("predicted_pass_probability"), bool)]
    return sorted(usable, key=lambda r: (r.get("settled_at_unix") or 0.0))


def baseline_probability(*, passes: int, attempts: int, global_rate: float,
                         shrink: float = SHRINK) -> float:
    if attempts < 0 or passes < 0 or passes > attempts:
        raise ValueError("INCONSISTENT_HISTORY")
    if not 0.0 <= global_rate <= 1.0:
        raise ValueError("GLOBAL_RATE_OUT_OF_RANGE")
    return (passes + shrink * global_rate) / (attempts + shrink)


def compare(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Score the system's claims against the external baseline, causally."""
    ordered = _chronological(rows)
    n = len(ordered)
    if n == 0:
        return {"schema": SCHEMA, "n": 0, "verdict": "INSUFFICIENT_EVIDENCE",
                "reason": "NO_SETTLED_PREDICTIONS"}

    history: dict[str, list[int]] = {}
    total_wins = total_attempts = 0
    squared_claim = squared_base = squared_global = 0.0
    per_row = []

    for row in ordered:
        cid = str(row.get("capability_id") or "")
        outcome = 1.0 if row["outcome_pass"] else 0.0
        claim = float(row["predicted_pass_probability"])
        global_rate = ((total_wins + GLOBAL_SHRINK * NEUTRAL_PRIOR)
                       / (total_attempts + GLOBAL_SHRINK))
        passes, attempts = history.get(cid, [0, 0])
        # Strictly prior data: this attempt is added to the history only after it is scored.
        base = baseline_probability(passes=passes, attempts=attempts, global_rate=global_rate)

        squared_claim += (claim - outcome) ** 2
        squared_base += (base - outcome) ** 2
        squared_global += (global_rate - outcome) ** 2

        per_row.append({
            "capability_id": cid,
            "claim": round(claim, 6),
            "external_baseline": round(base, 6),
            "global_rate_before": round(global_rate, 6),
            "outcome_pass": row["outcome_pass"],
        })

        history[cid] = [passes + (1 if outcome else 0), attempts + 1]
        total_wins += int(outcome)
        total_attempts += 1

    brier_claim = squared_claim / n
    brier_capability = squared_base / n
    brier_global = squared_global / n
    # The referee is the STRONGEST naive predictor, not the most convenient one. Comparing a claim
    # against a baseline it can trivially beat would flatter it, and a bar that moves down is a
    # tolerance widening in disguise.
    brier_base = min(brier_capability, brier_global)
    margin = brier_base - brier_claim  # positive means the claim is better
    verdict, reason = _verdict(n, margin)
    return {
        "schema": SCHEMA,
        "n": n,
        "brier_claim": round(brier_claim, 6),
        "brier_external_baseline": round(brier_base, 6),
        "brier_per_capability_rate": round(brier_capability, 6),
        "brier_global_rate_only": round(brier_global, 6),
        "margin_over_baseline": round(margin, 6),
        "verdict": verdict,
        "reason": reason,
        "baseline_rule": "shrunk per-capability pass rate from strictly earlier settled attempts",
        "shrink_pseudo_count": SHRINK,
        "global_shrink_pseudo_count": GLOBAL_SHRINK,
        "meaningful_margin": MEANINGFUL_MARGIN,
        "measures": "whether the system's stated expectations beat a lookup table of its own history",
        "does_not_measure": "sentience, experience, selfhood",
        "rows": per_row[:50],
    }


def _verdict(n: int, margin: float) -> tuple[str, str]:
    if n < MIN_SETTLED:
        return "INSUFFICIENT_EVIDENCE", f"SETTLED_PREDICTIONS_{n}_BELOW_{MIN_SETTLED}"
    if margin <= -MEANINGFUL_MARGIN:
        return ("WORSE_THAN_EXTERNAL_BASELINE",
                "THE_SYSTEM_KNOWS_LESS_ABOUT_ITSELF_THAN_ITS_OWN_TRACK_RECORD_DOES")
    if margin < MEANINGFUL_MARGIN:
        return "NO_BETTER_THAN_EXTERNAL_BASELINE", "WITHIN_NOISE_OF_A_LOOKUP_TABLE"
    return "CLAIM_BEATS_EXTERNAL_BASELINE", "THE_STATED_EXPECTATIONS_CARRY_INFORMATION"


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import json

    from canonical.runtime import self_prediction_calibration_v1 as calibration

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    report = compare(calibration.Ledger(ns.ledger).settled_rows())
    if ns.json:
        print(json.dumps(report, indent=1, sort_keys=True))
    else:
        for key in ("n", "brier_claim", "brier_external_baseline", "brier_global_rate_only",
                    "margin_over_baseline", "verdict", "reason"):
            print(f"  {key:<26} {report.get(key)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
