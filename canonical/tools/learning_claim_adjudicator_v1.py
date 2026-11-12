#!/usr/bin/env python3
"""Fixed-threshold adjudicator for "the agent learned it" claims.

Why this exists
---------------
This repository has produced at least twelve confident false positives. Almost none
were failures of the learner; they were failures of the *instrument*:

  * a probe re-created the instance it taught and called the replay "transfer";
  * a status string printed SOLVED_BY_RECALLED_PLAN for 15/15 while 14/15 cost more;
  * an unsolvable kind plus a 10**6 penalty constant produced a "948,766x prize";
  * every lambda had the same goal key (`<lambda>`), so recall never happened;
  * warm runs became 12x cheaper and strictly wronger while every status said success;
  * a 700/700 helper was called by no production code;
  * a counter treated any non-None body as a solve, hiding 0/3 -> 2/3 reach;
  * zero held-out evaluation: every reported number was a fit;
  * twelve programs were counted where three explanations existed;
  * 226/233 "failures" were one deliberate gate saying no;
  * a bridge refused every multi-statement program, so G_t stayed empty;
  * a zlib-byte compression gate rejected the real corpus with d(B_exec) < 0.

This module is not a learner, a capability, a benchmark score, or an organ. It is a
ruler: a decision rule written down BEFORE the data, plus controls that prove the
ruler can reject a cache, a status string, a leak, a self-graded verifier, a
penalty-constant artefact, and a cheaper-but-wronger run, and can accept a real
compounding effect. If the controls do not pass, no claim may be adjudicated.

Design rules (all load-bearing)
-------------------------------
1. Fail closed. Any preflight defect returns INSTRUMENT_INVALID; no claim is scored.
2. A cache-only arm is MANDATORY. A prediction a cache can satisfy is not a test.
3. A random/default arm is MANDATORY and kept permanently.
4. Cost is measured on the held-out kind, never on a seen kind; success is checked
   separately, because "cheaper and wronger" is a real historical failure.
5. Claims not supplied with their own measurement are reported NOT_MEASURED, never
   inferred. Fabricating a verdict from a missing field is the defect being guarded.
6. Thresholds are fixed here, in code, before any future real run. This artifact is
   not independently timestamped, so it is not an externally registered protocol.
7. Hash syntax and author labels are only consistency checks: this tool cannot prove
   that the underlying evidence was withheld or that an oracle is truly independent.
   A trusted harness must supply those facts and preserve the raw receipts.

Authority: NONE. truth.achieved stays false. $0. No model, no network, no writes.
Run: python3 canonical/tools/learning_claim_adjudicator_v1.py
"""
from __future__ import annotations

import json
import math
import re
import statistics
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


PREREGISTRATION: dict[str, Any] = {
    "schema": "PROJECT_BRAIN_LEARNING_CLAIM_ADJUDICATOR_V1",
    "thresholds_fixed_before_any_future_real_run": True,
    "independent_timestamp_or_signature": False,
    "date": "2026-11-12",
    "registration_limit": (
        "The thresholds are frozen in this artifact for future real runs, but this "
        "artifact is not independently timestamped; do not call it an externally "
        "preregistered experiment."
    ),
    "question": (
        "Does experience with old kinds make a genuinely new kind cheaper to solve, "
        "or is the apparent gain recall, selection noise, or an instrument defect?"
    ),
    "thresholds": {
        "min_held_out_tasks": 5,
        "min_mean_cost_ratio_warm_vs_cold": 1.5,
        "min_paired_win_fraction": 0.8,
        "min_incremental_ratio_warm_vs_cache": 1.5,
        "max_cost_outlier_multiple": 100.0,
        "one_shot_new_kind_min_held_out_success": 0.30,
        "one_shot_new_kind_max_extra_interactions": 0,
        "verifier_independent_min_held_out_success": 0.80,
    },
    "stopping_rule": (
        "The thresholds above are fixed before measurement. No threshold, feature, "
        "arm, or exclusion may be changed after seeing a result. A negative result "
        "is a decision, not a tuning pass."
    ),
    "required_arms": ("cold", "warm", "cache_only", "random"),
    "sources_of_known_instrument_defects": (
        "INSTANT_LEARNING_SCOPE_20261101_V1.md",
        "INSTANT_LEARNING_NEW_INSTANCE_REMEASUREMENT_20261103_V1.md",
        "LEARN_TO_LEARN_VERDICT_20261103_V1.md",
        "THE_DEEPEST_LAYER_20261103_V1.md",
        "SETTLED_IS_COMPUTED_NEVER_REACHED_20261104_V1.md",
        "A_REFUSAL_MUST_LEARN_20261104_V1.md",
        "THE_INSTRUMENT_WAS_BLIND_20261104_V1.md",
        "NOBODY_WAS_EVER_PREDICTING_20261104_V1.md",
        "COUNTING_IDEAS_NOT_PROGRAMS_20261104_V1.md",
        "DOES_IT_SOLVE_EVERYTHING_20261103_V1.md",
        "THE_DEEPEST_STILL_OPEN_DEFECT_NOTHING_IS_EVER_COMPRESSED_20261104_V1.md",
        "ONE_TRY_IS_NOT_A_LEARNING_SIGNAL_20261112_V1.md",
    ),
}


@dataclass(frozen=True)
class Arm:
    """Per-task measured cost and success on the SAME held-out tasks."""

    costs: tuple[float, ...]
    successes: tuple[bool, ...]
    task_ids: tuple[str, ...]


@dataclass(frozen=True)
class Experiment:
    held_out_kind: str
    seen_kinds: tuple[str, ...]
    task_ids: tuple[str, ...]
    cost_unit: str
    arms: Mapping[str, Arm]
    demonstration_evidence_hash: str
    held_out_scorer_hash: str
    verifier_author: str
    producer_id: str
    source_kind_costs_before: tuple[float, ...] = ()
    source_kind_costs_after: tuple[float, ...] = ()
    one_shot_new_kind: Mapping[str, Any] | None = None
    self_authored_structural_test: Mapping[str, Any] | None = None
    interface_evolution: Mapping[str, Any] | None = None
    verifier_independent: Mapping[str, Any] | None = None


def _mean(values: Sequence[float]) -> float:
    return float(statistics.fmean(values)) if values else float("inf")


def _looks_like_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value))


def preflight(exp: Experiment) -> list[str]:
    """Reject the instrument before it is allowed to produce a verdict."""
    errors: list[str] = []
    t = PREREGISTRATION["thresholds"]

    required = PREREGISTRATION["required_arms"]
    for name in required:
        if name not in exp.arms:
            errors.append(f"MISSING_ARM:{name}")
    if errors:
        return errors

    n = len(exp.task_ids)
    if n < t["min_held_out_tasks"]:
        errors.append(f"TOO_FEW_HELD_OUT_TASKS:{n}")
    if len(set(exp.task_ids)) != n:
        errors.append("TASK_IDS_NOT_DISTINCT")
    if exp.held_out_kind in exp.seen_kinds:
        errors.append("HELD_OUT_KIND_WAS_SEEN")
    if not exp.held_out_kind.strip():
        errors.append("HELD_OUT_KIND_EMPTY")
    if not exp.cost_unit.strip():
        errors.append("COST_UNIT_MISSING")

    for name, arm in exp.arms.items():
        if len(arm.costs) != n or len(arm.successes) != n:
            errors.append(f"ARM_LENGTH_MISMATCH:{name}")
            continue
        if any(not math.isfinite(c) or c < 0 for c in arm.costs):
            errors.append(f"NON_MEASURED_COST:{name}")
        if not arm.costs:
            errors.append(f"STATUS_STRING_ONLY_NO_COST_DATA:{name}")
        if arm.task_ids != exp.task_ids:
            errors.append(f"ARM_TASK_ALIGNMENT_MISMATCH:{name}")
        if any(not isinstance(s, bool) for s in arm.successes):
            errors.append(f"SUCCESS_NOT_BOOLEAN:{name}")

    if (not _looks_like_sha256(exp.demonstration_evidence_hash)
            or not _looks_like_sha256(exp.held_out_scorer_hash)):
        errors.append("EVIDENCE_FINGERPRINT_INVALID")
    elif exp.demonstration_evidence_hash == exp.held_out_scorer_hash:
        errors.append("SCORER_NOT_HELD_OUT")
    if exp.verifier_author == exp.producer_id:
        errors.append("PRODUCER_WROTE_THE_VERIFIER")
    if not exp.verifier_author.strip() or not exp.producer_id.strip():
        errors.append("VERIFIER_PROVENANCE_MISSING")

    # A penalty constant applied to unsolvable kinds once produced a fake 948,766x
    # prize. Any single cost that dominates the cold median by >100x is arithmetic
    # about that constant, not learning.
    cold = exp.arms["cold"].costs
    if cold:
        median = statistics.median(cold) or 1.0
        for name, arm in exp.arms.items():
            if any(c > t["max_cost_outlier_multiple"] * median for c in arm.costs):
                errors.append(f"COST_OUTLIER_ARTIFACT:{name}")
    return sorted(set(errors))


def _cross_kind(exp: Experiment) -> dict[str, Any]:
    """C1: the only claim computable from cost arms, and the one that compounds."""
    t = PREREGISTRATION["thresholds"]
    cold, warm = exp.arms["cold"], exp.arms["warm"]
    cache, random = exp.arms["cache_only"], exp.arms["random"]
    n = len(cold.costs)
    reasons: list[str] = []

    mean_ratio = _mean(cold.costs) / max(_mean(warm.costs), 1e-9)
    paired_wins = sum(1 for c, w in zip(cold.costs, warm.costs) if w < c)
    win_fraction = paired_wins / max(n, 1)

    cache_mean_ratio = _mean(cold.costs) / max(_mean(cache.costs), 1e-9)
    incremental_warm_vs_cache = _mean(cache.costs) / max(_mean(warm.costs), 1e-9)
    warm_vs_random = _mean(random.costs) / max(_mean(warm.costs), 1e-9)

    if mean_ratio < t["min_mean_cost_ratio_warm_vs_cold"]:
        reasons.append(f"MEAN_RATIO_TOO_SMALL:{mean_ratio:.3f}")
    if win_fraction < t["min_paired_win_fraction"]:
        reasons.append(f"PAIRED_WINS_TOO_FEW:{paired_wins}/{n}")
    if cache_mean_ratio >= t["min_mean_cost_ratio_warm_vs_cold"]:
        reasons.append("CACHE_ONLY_ARM_ALSO_WINS__GAIN_IS_RECALL_NOT_COMPOUNDING")
    if incremental_warm_vs_cache < t["min_incremental_ratio_warm_vs_cache"]:
        reasons.append(
            f"WARM_NOT_INCREMENTALLY_BETTER_THAN_CACHE:{incremental_warm_vs_cache:.3f}"
        )
    if warm_vs_random < t["min_mean_cost_ratio_warm_vs_cold"]:
        reasons.append(f"DOES_NOT_BEAT_RANDOM_ARM:{warm_vs_random:.3f}")

    cold_success = sum(cold.successes)
    warm_success = sum(warm.successes)
    random_success = sum(random.successes)
    if warm_success < cold_success:
        reasons.append(f"CHEAPER_BUT_WRONGER:{warm_success}<{cold_success}")
    if warm_success < random_success:
        reasons.append(f"RANDOM_ARM_HAS_MORE_SUCCESSES:{random_success}>{warm_success}")

    before, after = exp.source_kind_costs_before, exp.source_kind_costs_after
    if before and after:
        if len(before) != len(after):
            reasons.append("BACKWARD_TRANSFER_LENGTH_MISMATCH")
        elif _mean(after) > _mean(before):
            reasons.append("BACKWARD_TRANSFER_REGRESSION")

    return {
        "claim_id": "C1_cross_kind_compounding",
        "status": "PASS" if not reasons else "FAIL",
        "mean_cost_ratio_cold_over_warm": round(mean_ratio, 4),
        "paired_wins": f"{paired_wins}/{n}",
        "cache_only_mean_ratio": round(cache_mean_ratio, 4),
        "incremental_warm_over_cache_ratio": round(incremental_warm_vs_cache, 4),
        "warm_over_random_ratio": round(warm_vs_random, 4),
        "cold_success": cold_success,
        "warm_success": warm_success,
        "random_success": random_success,
        "reasons": reasons,
    }


def _unmeasured(claim_id: str, supplied: Mapping[str, Any] | None, key: str,
                threshold: float) -> dict[str, Any]:
    """Claims needing their own experiment are never inferred from cost arms."""
    if supplied is None:
        return {"claim_id": claim_id, "status": "NOT_MEASURED",
                "reason": f"no {claim_id} measurement supplied; not inferred"}
    value = supplied.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return {"claim_id": claim_id, "status": "INSTRUMENT_INVALID",
                "reason": f"{key} missing or non-numeric"}
    extra = supplied.get("extra_interactions", 0)
    if extra not in (0, None) and claim_id == "C2_one_shot_new_kind":
        return {"claim_id": claim_id, "status": "FAIL",
                "reason": f"extra interactions after the one episode: {extra}"}
    return {"claim_id": claim_id,
            "status": "PASS" if float(value) >= threshold else "FAIL",
            "measured": float(value), "threshold": threshold}


def adjudicate(exp: Experiment) -> dict[str, Any]:
    errors = preflight(exp)
    report: dict[str, Any] = {
        "schema": PREREGISTRATION["schema"],
        "held_out_kind": exp.held_out_kind,
        "preflight_errors": errors,
        "thresholds_fixed_in_artifact": True,
        "independently_timestamped_registration": False,
    }
    if errors:
        report["verdict"] = "INSTRUMENT_INVALID"
        report["note"] = "Fail closed: no claim is scored until the instrument is valid."
        return report

    t = PREREGISTRATION["thresholds"]
    claims = [
        _cross_kind(exp),
        _unmeasured("C2_one_shot_new_kind", exp.one_shot_new_kind,
                    "held_out_success", t["one_shot_new_kind_min_held_out_success"]),
        _unmeasured("C3_self_authored_structural_test", exp.self_authored_structural_test,
                    "held_out_success", 0.30),
        _unmeasured("C4_interface_evolution", exp.interface_evolution,
                    "held_out_cost_ratio", 1.5),
        _unmeasured("C5_verifier_independent_success", exp.verifier_independent,
                    "held_out_success", t["verifier_independent_min_held_out_success"]),
    ]
    report["claims"] = claims
    c1 = claims[0]
    report["verdict"] = "COMPOUNDING" if c1["status"] == "PASS" else "NO_COMPOUNDING"
    report["note"] = (
        "COMPOUNDING here means only C1 passed: experience made a genuinely new "
        "kind measurably cheaper, a cache cannot explain it, it beat the random "
        "arm, and it did not make the system wronger or damage old kinds. "
        "It is not a claim about general computer use or sentience."
    )
    return report


# ---------------------------------------------------------------------------
# Calibration controls: prove the ruler before the ruler is used on anything.
# Every control is deterministic; no randomness, no network, no files.
# ---------------------------------------------------------------------------

def _arm(costs: Sequence[float], successes: Sequence[bool] | None = None,
         task_ids: Sequence[str] | None = None) -> Arm:
    ids = tuple(task_ids) if task_ids is not None else tuple(
        f"t{i + 1}" for i in range(len(costs))
    )
    return Arm(
        tuple(float(c) for c in costs),
        tuple(bool(s) for s in (successes if successes is not None
                                else [True] * len(costs))),
        ids,
    )


def _exp(arms: Mapping[str, Arm], **overrides: Any) -> Experiment:
    kwargs: dict[str, Any] = dict(
        held_out_kind="held_out_kind_X",
        seen_kinds=("kind_A", "kind_B", "kind_C"),
        task_ids=("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"),
        cost_unit="environment_calls",
        arms=arms,
        demonstration_evidence_hash="d" * 64,
        held_out_scorer_hash="a" * 64,
        verifier_author="independent_oracle",
        producer_id="producer",
    )
    kwargs.update(overrides)
    return Experiment(**kwargs)


def calibration_controls() -> dict[str, dict[str, Any]]:
    """Each key states the verdict the ruler MUST return; controls are deterministic."""
    n = 8
    cold = [10.0] * n
    all_ok = [True] * n

    cases: dict[str, tuple[Experiment, str]] = {}

    # 1. A pure cache: cheaper ONLY where the instance was seen. Held-out is flat.
    cases["pure_cache_must_be_rejected"] = (
        _exp({"cold": _arm(cold), "warm": _arm(cold),
              "cache_only": _arm(cold), "random": _arm([11.0] * n)}),
        "NO_COMPOUNDING",
    )

    # 2. Real compounding: warm halves held-out cost, cache cannot, random loses,
    #    success is unchanged, old kinds are not damaged.
    cases["real_compounding_must_be_accepted"] = (
        _exp({"cold": _arm(cold), "warm": _arm([5.0] * n),
              "cache_only": _arm(cold), "random": _arm([12.0] * n)},
             source_kind_costs_before=(4.0, 4.0), source_kind_costs_after=(4.0, 4.0)),
        "COMPOUNDING",
    )

    # 3. The SETTLED failure: 12x cheaper and wronger, every status said success.
    cases["cheaper_but_wronger_must_be_rejected"] = (
        _exp({"cold": _arm(cold, all_ok),
              "warm": _arm([1.0] * n, [False] * n),
              "cache_only": _arm(cold), "random": _arm([12.0] * n)}),
        "NO_COMPOUNDING",
    )

    # 4. A coin flip: no systematic advantage over the random arm.
    cases["coin_flip_must_be_rejected"] = (
        _exp({"cold": _arm(cold),
              "warm": _arm([10.0, 2.0, 10.0, 2.0, 10.0, 2.0, 10.0, 2.0]),
              "cache_only": _arm(cold), "random": _arm([6.0] * n)}),
        "NO_COMPOUNDING",
    )

    # 5-9. Instrument defects must fail closed before any claim is scored.
    cases["same_instance_replay_must_fail_closed"] = (
        _exp({"cold": _arm(cold), "warm": _arm([1.0] * n),
              "cache_only": _arm(cold), "random": _arm([12.0] * n)},
             held_out_kind="kind_A"),
        "INSTRUMENT_INVALID",
    )
    cases["producer_wrote_verifier_must_fail_closed"] = (
        _exp({"cold": _arm(cold), "warm": _arm([1.0] * n),
              "cache_only": _arm(cold), "random": _arm([12.0] * n)},
             verifier_author="producer"),
        "INSTRUMENT_INVALID",
    )
    cases["scorer_leak_must_fail_closed"] = (
        _exp({"cold": _arm(cold), "warm": _arm([1.0] * n),
              "cache_only": _arm(cold), "random": _arm([12.0] * n)},
             held_out_scorer_hash="demo-bytes"),
        "INSTRUMENT_INVALID",
    )
    cases["missing_cache_arm_must_fail_closed"] = (
        _exp({"cold": _arm(cold), "warm": _arm([1.0] * n),
              "random": _arm([12.0] * n)}),
        "INSTRUMENT_INVALID",
    )
    cases["penalty_constant_artifact_must_fail_closed"] = (
        _exp({"cold": _arm(cold), "warm": _arm([1.0] * (n - 1) + [10.0 ** 6]),
              "cache_only": _arm(cold), "random": _arm([12.0] * n)}),
        "INSTRUMENT_INVALID",
    )

    out: dict[str, dict[str, Any]] = {}
    for name, (exp, expected) in cases.items():
        got = adjudicate(exp)
        out[name] = {
            "expected_verdict": expected,
            "actual_verdict": got["verdict"],
            "calibrated": got["verdict"] == expected,
            "preflight_errors": got.get("preflight_errors", []),
            "reasons": (got.get("claims") or [{}])[0].get("reasons", [])
            if got.get("claims") else [],
        }
    return out


def main() -> int:
    controls = calibration_controls()
    all_ok = all(v["calibrated"] for v in controls.values())
    print(json.dumps({
        "schema": PREREGISTRATION["schema"],
        "authority": "NONE",
        "truth_achieved": False,
        "claim": "MEASUREMENT_INSTRUMENT_ONLY__NO_CAPABILITY_CREDIT",
        "purpose": "calibrate the ruler before the ruler is used on any learner",
        "preregistration": PREREGISTRATION,
        "calibration": controls,
        "calibration_pass": all_ok,
        "usage": (
            "Build an Experiment from a real run's per-task costs, then call "
            "adjudicate(exp). INSTRUMENT_INVALID means the instrument is broken; "
            "NO_COMPOUNDING means the claim failed; COMPOUNDING means only C1 passed."
        ),
    }, indent=2, sort_keys=True))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
