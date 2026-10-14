"""Fresh-instance generators for the three scheduler specs.

* generate_ranking   -> CAPABILITY_FIRST_RANKING_V1      (rank_work)
* generate_frontier  -> PARETO_FRONTIER_UPDATE_V1         (update_pareto_frontier, folded)
* generate_schedule  -> AUTHENTICATED_PARETO_SCHEDULE_V1  (compile_schedule)

Nothing here imports a scheduler.  Numbers are small decimals written as strings
or ints so that the exact-fraction contract is exercised (0.1 + 0.2 must equal
0.3).  Each generator mixes valid instances with deliberately invalid ones that
the solver must refuse.
"""
from __future__ import annotations

import hashlib
import json
import random

WORK_TYPES = ["CAPABILITY_BUILD", "EFFICIENCY_IMPROVEMENT", "RELIABILITY_IMPROVEMENT", "BENCHMARK_INSTRUMENTATION", "FALSIFICATION"]
BENCHMARK_ROLES_OK = ["CAPABILITY_DEFECT_LOCALIZATION", "NEW_CAPABILITY_VALIDATION", "CAPABILITY_CLAIM_FALSIFICATION", "MILESTONE_CERTIFICATION"]
BENCHMARK_ROLES_BAD = ["LEADERBOARD_REFRESH", "SCORE_BOOKKEEPING", "", "VANITY_RERUN"]
NEW_PRIMITIVE_FIELDS = [
    "exact_unsatisfied_predicate",
    "existing_mechanisms_searched",
    "existing_mechanism_unsoundness_reasons",
    "independently_verified_missing_primitive_or_counterexample",
    "minimum_new_primitive_scope",
    "falsifier_and_promotion_criteria",
]
AUTH_MAX_KEYS = ["capability_gain_lcb", "generalization_lcb", "reliability_lcb", "reuse_breadth_lcb", "success_probability_lcb"]
AUTH_MIN_KEYS = ["latency_ms_ucb", "compute_units_ucb", "memory_mb_ucb", "cost_usd_ucb"]


def _hex(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


def _dec(rng: random.Random, lo: int, hi: int, scale: int = 100) -> str:
    """A non-negative decimal with two digits, as a string ('0.37')."""
    v = rng.randint(lo, hi)
    whole, frac = divmod(v, scale)
    return f"{whole}.{frac:02d}" if scale == 100 else str(v)


def _num(rng: random.Random, lo: int, hi: int):
    """Mix of ints and decimal strings so both input spellings are exercised."""
    return rng.randint(lo, hi) if rng.random() < 0.3 else _dec(rng, lo * 100, hi * 100)


# --------------------------------------------------------------------------- ranking
def _work_item(rng: random.Random, work_id: str, small_pool: list[str]) -> dict:
    work_type = rng.choice(WORK_TYPES)
    item: dict = {
        "work_id": work_id,
        "work_type": work_type,
        # scores drawn from a small pool so exact ties are common (tie-break rules get exercised)
        "expected_capability_gain_lcb": rng.choice(small_pool),
        "expected_efficiency_gain_lcb": rng.choice(small_pool),
        "expected_reliability_gain_lcb": rng.choice(small_pool),
        "reuse_breadth_lcb": rng.choice([1, 2, 3, "1.5", "0.5"]),
        "generalization_lcb": rng.choice(["0.25", "0.5", "0.75", 1]),
        "success_probability_lcb": rng.choice(["0.1", "0.25", "0.5", "0.8", 1]),
        "wall_clock_cost_ub": rng.choice([1, 2, "0.5", 4]),
        "compute_cost_ub": rng.choice([0, 1, "0.5"]),
        "memory_cost_ub": rng.choice([0, 1, "0.25"]),
        "complexity_cost_ub": rng.choice([0, 1, 2]),
    }
    if work_type == "BENCHMARK_INSTRUMENTATION":
        item["benchmark_role"] = rng.choice(BENCHMARK_ROLES_OK) if rng.random() < 0.5 else rng.choice(BENCHMARK_ROLES_BAD)
    if rng.random() < 0.25:
        item["frontier_class"] = "OPEN_WORLD_EVIDENCE_FRONTIER"
        if rng.random() < 0.5:
            key = rng.choice(["task_local_counterexample_ids", "verified_capability_defect_ids"])
            item[key] = [f"CE-{_hex(rng, 4)}"]
    if rng.random() < 0.25:
        item["claims_new_primitive"] = True
        mechanisms = [f"MECH-{_hex(rng, 3)}" for _ in range(rng.randint(1, 2))]
        proof = {
            "exact_unsatisfied_predicate": "P_" + _hex(rng, 6),
            "existing_mechanisms_searched": mechanisms,
            "existing_mechanism_unsoundness_reasons": {m: "unsound because " + _hex(rng, 4) for m in mechanisms},
            "independently_verified_missing_primitive_or_counterexample": "CX_" + _hex(rng, 6),
            "minimum_new_primitive_scope": "scope " + _hex(rng, 4),
            "falsifier_and_promotion_criteria": "falsifier " + _hex(rng, 4),
        }
        if rng.random() < 0.5:
            # incomplete proof: drop or blank one requirement, or leave one mechanism without a reason
            victim = rng.choice(NEW_PRIMITIVE_FIELDS)
            if victim == "existing_mechanism_unsoundness_reasons" and rng.random() < 0.5:
                proof[victim] = {mechanisms[0]: ""}
            elif rng.random() < 0.5:
                proof.pop(victim)
            else:
                proof[victim] = "" if victim != "existing_mechanisms_searched" else []
        item.update(proof)
    if rng.random() < 0.35:
        key = rng.choice(["open_obligation_ids", "constructive_gap_for_open_obligation_ids", "scope_complete_discharge"])
        item[key] = True if key == "scope_complete_discharge" else [f"OBL-{_hex(rng, 3)}" for _ in range(rng.randint(1, 3))]
        item["expected_obligation_discharge_lcb"] = rng.choice([0, "0.5", 1])
        item["expected_obligation_unlock_lcb"] = rng.choice([0, 1, 2])
    return item


def _ranking_instance(rng: random.Random) -> dict:
    n = rng.randint(2, 9)
    small_pool = [0, "0.1", "0.2", "0.3", "0.5", 1]
    ids = rng.sample([f"W-{_hex(rng, 5)}" for _ in range(3 * n)], n)
    work = [_work_item(rng, wid, small_pool) for wid in ids]
    leverage_keys = ["expected_capability_gain_lcb", "expected_efficiency_gain_lcb", "expected_reliability_gain_lcb",
                     "reuse_breadth_lcb", "generalization_lcb", "success_probability_lcb",
                     "wall_clock_cost_ub", "compute_cost_ub", "memory_cost_ub", "complexity_cost_ub"]
    for i, item in enumerate(work):
        if i and rng.random() < 0.35:
            # exact leverage tie with an earlier item (tie-break rules must decide)
            src = work[rng.randrange(i)]
            for k in leverage_keys:
                item[k] = src[k]
        elif rng.random() < 0.15:
            # zero expected gain: eligible, but scored 0 like demoted work
            for k in leverage_keys[:3]:
                item[k] = 0
    count = 0 if rng.random() < 0.3 else rng.randint(1, 30)
    defect = None
    if rng.random() < 0.15:
        defect = rng.choice(["DUPLICATE_ID", "BAD_WORK_TYPE", "NEGATIVE_METRIC", "SUCCESS_GT_ONE", "ZERO_COST"])
        victim = rng.choice(work)
        if defect == "DUPLICATE_ID":
            clone = dict(rng.choice(work))
            work.insert(rng.randint(0, len(work)), clone)
        elif defect == "BAD_WORK_TYPE":
            victim["work_type"] = rng.choice(["BENCHMARK_CHASE", "", "capability_build"])
        else:
            # the invalid number must sit on an item that is certainly eligible, so refusal is unconditional
            victim.update({"work_type": "CAPABILITY_BUILD", "frontier_class": None, "claims_new_primitive": False})
            if defect == "NEGATIVE_METRIC":
                victim[rng.choice(["expected_capability_gain_lcb", "reuse_breadth_lcb", "compute_cost_ub"])] = rng.choice(["-0.5", -1])
            elif defect == "SUCCESS_GT_ONE":
                victim["success_probability_lcb"] = rng.choice(["1.01", 2])
            else:
                victim.update({"wall_clock_cost_ub": 0, "compute_cost_ub": 0, "memory_cost_ub": 0, "complexity_cost_ub": 0})
    return {"schema": "CAPABILITY_FIRST_RANKING_INSTANCE_V1", "checkpoint_open_obligation_count": count, "work": work, "defect": defect}


def generate_ranking(rng: random.Random, n: int) -> list[dict]:
    return [_ranking_instance(rng) for _ in range(n)]


# --------------------------------------------------------------------------- frontier update
FRONTIER_BENEFITS = ["capability", "generalization", "reliability"]
FRONTIER_COSTS = ["latency", "compute", "memory", "incremental_spend_usd"]


def _frontier_instance(rng: random.Random) -> dict:
    n = rng.randint(2, 10)
    contracts = [_hex(rng, 64) for _ in range(rng.randint(1, 2))]
    base = {k: rng.randint(0, 4) for k in FRONTIER_BENEFITS + FRONTIER_COSTS}
    candidates = []
    numeric: list[dict] = []
    for i in range(n):
        # metrics near a common base so dominance, incomparability and exact ties all occur
        metrics = {k: max(0, base[k] + rng.choice([-1, 0, 0, 1])) for k in FRONTIER_BENEFITS + FRONTIER_COSTS}
        if rng.random() < 0.3 and numeric:
            # exact clone of an earlier candidate's metrics (tie) or a strictly worse copy
            metrics = dict(rng.choice(numeric))
            if rng.random() < 0.5:
                worse = rng.choice(FRONTIER_BENEFITS)
                metrics[worse] = max(0, metrics[worse] - 1)
        numeric.append(dict(metrics))
        cand = {"capability_id": f"CAP-{i}-{_hex(rng, 4)}", "reusable_capability": True, "independently_verified": True}
        cand.update({k: (str(v) + ".0" if rng.random() < 0.3 else v) for k, v in metrics.items()})
        r = rng.random()
        if r < 0.08:
            cand["reusable_capability"] = rng.choice([False, "yes", None])
        elif r < 0.16:
            cand["independently_verified"] = rng.choice([False, "true", None])
        elif r < 0.21:
            cand[rng.choice(FRONTIER_BENEFITS + FRONTIER_COSTS)] = rng.choice([-1, "-0.5"])
        if rng.random() < 0.8:
            cand["semantic_contract_sha256"] = rng.choice(contracts)
        candidates.append(cand)
    return {"schema": "PARETO_FRONTIER_UPDATE_INSTANCE_V1", "candidates": candidates}


def generate_frontier(rng: random.Random, n: int) -> list[dict]:
    return [_frontier_instance(rng) for _ in range(n)]


# --------------------------------------------------------------------------- authenticated schedule
def subject_sha256(candidate_id: str, metrics: dict) -> str:
    """The receipt binding published by the scheduler: sha256 of the canonical JSON of id + exact metrics."""
    body = {"candidate_id": candidate_id, "metrics": {k: metrics[k] for k in AUTH_MAX_KEYS + AUTH_MIN_KEYS}}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _schedule_instance(rng: random.Random) -> dict:
    n = rng.randint(1, 9)
    base = {k: rng.randint(0, 5) for k in AUTH_MAX_KEYS + AUTH_MIN_KEYS}
    base["cost_usd_ucb"] = 0
    candidates = []
    defect = None
    for i in range(n):
        metrics = {k: base[k] + rng.choice([-1, 0, 0, 1]) for k in AUTH_MAX_KEYS + AUTH_MIN_KEYS}
        metrics = {k: (float(v) if rng.random() < 0.4 else int(v)) for k, v in metrics.items()}
        metrics["cost_usd_ucb"] = 0 if rng.random() < 0.5 else 0.0
        if candidates and rng.random() < 0.3:
            # exact metric twin of an earlier candidate: neither may dominate the other
            metrics = dict(rng.choice(candidates)["metrics"])
        cid = f"C-{i}-{_hex(rng, 4)}"
        candidates.append({
            "candidate_id": cid,
            "metrics": metrics,
            "measurement_receipt": {"independently_verified": True, "sha256": _hex(rng, 64), "subject_sha256": subject_sha256(cid, metrics)},
        })
    if rng.random() < 0.3:
        defect = rng.choice(["DUPLICATE_CANDIDATE_ID", "METRICS_INCOMPLETE", "MEASUREMENT_RECEIPT_INVALID",
                             "MEASUREMENT_RECEIPT_SUBJECT_MISMATCH", "HARD_ZERO_SPEND_VIOLATION", "CANDIDATE_INVALID", "NO_CANDIDATES"])
        if defect == "NO_CANDIDATES":
            candidates = []
        else:
            victim = rng.choice(candidates)
            if defect == "DUPLICATE_CANDIDATE_ID":
                candidates.insert(rng.randint(0, len(candidates)), json.loads(json.dumps(victim)))
            elif defect == "METRICS_INCOMPLETE":
                if rng.random() < 0.5:
                    victim["metrics"].pop(rng.choice(AUTH_MAX_KEYS + AUTH_MIN_KEYS))
                else:
                    victim["metrics"][rng.choice(AUTH_MAX_KEYS)] = "3"
                victim["measurement_receipt"]["subject_sha256"] = "0" * 64  # irrelevant: metrics fail first
            elif defect == "MEASUREMENT_RECEIPT_INVALID":
                choice = rng.random()
                if choice < 0.33:
                    victim["measurement_receipt"]["independently_verified"] = rng.choice([False, "true", None])
                elif choice < 0.66:
                    victim["measurement_receipt"]["sha256"] = rng.choice([_hex(rng, 63), _hex(rng, 64).upper(), "", None])
                else:
                    victim["measurement_receipt"] = None
            elif defect == "MEASUREMENT_RECEIPT_SUBJECT_MISMATCH":
                # metrics tampered after the receipt was issued (the whole point of the binding)
                key = rng.choice(AUTH_MAX_KEYS)
                victim["metrics"][key] = victim["metrics"][key] + 1
            elif defect == "HARD_ZERO_SPEND_VIOLATION":
                victim["metrics"]["cost_usd_ucb"] = rng.choice([0.01, 1, 2.5])
                victim["measurement_receipt"]["subject_sha256"] = subject_sha256(victim["candidate_id"], victim["metrics"])
            elif defect == "CANDIDATE_INVALID":
                victim["candidate_id"] = rng.choice(["", None, 7])
    return {"schema": "AUTHENTICATED_PARETO_SCHEDULE_INSTANCE_V1", "candidates": candidates, "defect": defect}


def generate_schedule(rng: random.Random, n: int) -> list[dict]:
    return [_schedule_instance(rng) for _ in range(n)]
