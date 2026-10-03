"""Universal Learning Optimizer V2 for Project Brain.

V2 is a strict optimization layer above the independently verified V1
Universal Learning Contract. V1 remains the safety authority for unknown
capture, verification-before-trust, promotion, reuse, and invalidation.

V2 optimizes how a learning episode is carried out:
1. learn only the minimum goal-relevant novelty delta;
2. admit transfer only from verified EXACT/SUPERSET sources with falsifiers;
3. select safe zero-incremental-spend learning actions by conservative value;
4. stop learning once all surviving safe hypotheses imply the same action;
5. invalidate only the dependency cone affected by change;
6. learn about learning from verified episodes, but never self-promote strategy
   changes without a separate verifier.

It does not prove semantic success on every novel environment.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import universal_learning_contract_v1 as v1

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_LEARNING_OPTIMIZER_V2"

ALLOWED_CHANNELS = frozenset(v1.LEARNING_CHANNELS)
TRANSFER_SCOPE_RELATIONS = frozenset({"EXACT", "SUPERSET"})


class UniversalLearningOptimizerV2Error(ValueError):
    pass


def _clean_atoms(values: Iterable[Any]) -> set[str]:
    return {str(x).strip() for x in values if str(x).strip()}


def minimum_novelty_delta(
    *,
    required_atoms: Iterable[Any],
    verified_atoms: Iterable[Any],
) -> dict[str, Any]:
    """Return the exact goal-relevant set difference.

    Irrelevant verified knowledge is ignored. This is deliberately structural:
    semantic decomposition into atoms is upstream and receives no automatic
    truth credit here.
    """
    required = _clean_atoms(required_atoms)
    verified = _clean_atoms(verified_atoms)
    reused = required & verified
    missing = required - verified
    return {
        "schema": SCHEMA,
        "required_atoms": sorted(required),
        "reused_atoms": sorted(reused),
        "missing_atoms": sorted(missing),
        "minimum_novelty_count": len(missing),
        "full_environment_relearning_required": False,
        "semantic_atomization_proved": False,
    }


def admit_transfer(
    *,
    source_id: str,
    source_verified: Any,
    scope_relation: str,
    target_atom: str,
    falsifier: str,
) -> dict[str, Any]:
    """Fail closed on analogy-only transfer."""
    sid = str(source_id or "").strip()
    target = str(target_atom or "").strip()
    relation = str(scope_relation or "").strip().upper()
    falsifier_text = " ".join(str(falsifier or "").split())
    errors: list[str] = []
    if not sid:
        errors.append("SOURCE_ID_REQUIRED")
    if source_verified is not True:
        errors.append("SOURCE_NOT_VERIFIED")
    if relation not in TRANSFER_SCOPE_RELATIONS:
        errors.append("TRANSFER_SCOPE_NOT_EXACT_OR_SUPERSET")
    if not target:
        errors.append("TARGET_ATOM_REQUIRED")
    if not falsifier_text:
        errors.append("FALSIFIER_REQUIRED")
    return {
        "schema": SCHEMA,
        "admitted": not errors,
        "errors": errors,
        "source_id": sid or None,
        "target_atom": target or None,
        "scope_relation": relation or None,
        "falsifier": falsifier_text or None,
        "analogy_is_proof": False,
    }


def _number(row: Mapping[str, Any], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise UniversalLearningOptimizerV2Error(f"INVALID_NUMBER:{key}") from exc
    if not math.isfinite(value) or value < 0:
        raise UniversalLearningOptimizerV2Error(f"INVALID_NUMBER:{key}")
    return value


def _conservative_action_value(
    row: Mapping[str, Any],
    *,
    transfer_weight: float,
    proof_weight: float,
    risk_weight: float,
) -> float:
    decision = _number(row, "decision_gain_lcb")
    transfer = _number(row, "future_transfer_lcb")
    proof = _number(row, "proof_value_lcb")
    wall = _number(row, "wall_clock_ub")
    risk = _number(row, "risk_ub")
    spend = _number(row, "cost_ub")
    if spend > 0:
        return -math.inf
    burden = wall + risk_weight * risk
    if burden <= 0:
        burden = 1e-12
    return (decision + transfer_weight * transfer + proof_weight * proof) / burden


def choose_learning_action(
    actions: Sequence[Mapping[str, Any]],
    *,
    transfer_weight: float = 1.0,
    proof_weight: float = 1.0,
    risk_weight: float = 1.0,
) -> dict[str, Any]:
    """Choose the best safe zero-spend action by conservative value.

    Inputs use lower confidence bounds for benefits and upper bounds for burden.
    This avoids choosing an action merely because its point estimate is flashy.
    """
    if not actions:
        raise UniversalLearningOptimizerV2Error("ACTION_SET_EMPTY")
    if transfer_weight < 0 or proof_weight < 0 or risk_weight < 0:
        raise UniversalLearningOptimizerV2Error("NEGATIVE_WEIGHT_FORBIDDEN")

    ranked: list[tuple[float, str, Mapping[str, Any]]] = []
    rejected: list[dict[str, Any]] = []
    for raw in actions:
        aid = str(raw.get("id") or "").strip()
        channel = str(raw.get("channel") or "").strip()
        if not aid:
            rejected.append({"id": None, "reason": "ACTION_ID_REQUIRED"})
            continue
        if channel not in ALLOWED_CHANNELS:
            rejected.append({"id": aid, "reason": "UNKNOWN_LEARNING_CHANNEL"})
            continue
        if raw.get("safe") is not True:
            rejected.append({"id": aid, "reason": "ACTION_NOT_PROVED_SAFE"})
            continue
        try:
            score = _conservative_action_value(
                raw,
                transfer_weight=transfer_weight,
                proof_weight=proof_weight,
                risk_weight=risk_weight,
            )
        except UniversalLearningOptimizerV2Error as exc:
            rejected.append({"id": aid, "reason": str(exc)})
            continue
        if score == -math.inf:
            rejected.append({"id": aid, "reason": "POSITIVE_INCREMENTAL_SPEND_FORBIDDEN"})
            continue
        ranked.append((score, aid, raw))

    if not ranked:
        return {
            "schema": SCHEMA,
            "status": "NO_ADMISSIBLE_SAFE_ZERO_SPEND_ACTION",
            "selected_action_id": None,
            "rejected": rejected,
            "execution_authority": False,
        }

    ranked.sort(key=lambda x: (-x[0], x[1]))
    score, aid, row = ranked[0]
    return {
        "schema": SCHEMA,
        "status": "ACTION_SELECTED",
        "selected_action_id": aid,
        "selected_channel": row.get("channel"),
        "conservative_value": score,
        "optimization_basis": "CONSERVATIVE_LOWER_VALUE_OVER_UPPER_BURDEN",
        "hard_zero_incremental_spend": True,
        "rejected": rejected,
        "candidate_count": len(ranked),
        "execution_authority": False,
    }


def update_hypotheses(
    *,
    hypotheses: Sequence[Mapping[str, Any]],
    evidence_compatibility: Mapping[str, Any],
) -> dict[str, Any]:
    """Eliminate hypotheses contradicted by a verified evidence observation.

    The evidence-to-hypothesis compatibility judgment is an input; this function
    does not claim to semantically derive it.
    """
    out: list[dict[str, Any]] = []
    for row in hypotheses:
        hid = str(row.get("id") or "").strip()
        if not hid:
            raise UniversalLearningOptimizerV2Error("HYPOTHESIS_ID_REQUIRED")
        alive = row.get("alive") is True
        if alive and hid in evidence_compatibility:
            alive = evidence_compatibility[hid] is True
        item = dict(row)
        item["id"] = hid
        item["alive"] = alive
        out.append(item)
    surviving = [x["id"] for x in out if x["alive"]]
    return {
        "schema": SCHEMA,
        "hypotheses": out,
        "surviving_hypotheses": sorted(surviving),
        "semantic_compatibility_proved": False,
    }


def decision_sufficiency(
    *,
    hypotheses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Stop learning only if every surviving safe model recommends one action."""
    alive = [h for h in hypotheses if h.get("alive") is True]
    if not alive:
        return {
            "schema": SCHEMA,
            "decision_sufficient": False,
            "action": None,
            "reason": "NO_SURVIVING_HYPOTHESIS",
        }
    if any(h.get("safety_ok") is not True for h in alive):
        return {
            "schema": SCHEMA,
            "decision_sufficient": False,
            "action": None,
            "reason": "SURVIVING_HYPOTHESIS_NOT_SAFETY_CLEARED",
        }
    actions = {str(h.get("recommended_action") or "").strip() for h in alive}
    if "" in actions or len(actions) != 1:
        return {
            "schema": SCHEMA,
            "decision_sufficient": False,
            "action": None,
            "reason": "SURVIVING_HYPOTHESES_DO_NOT_AGREE",
        }
    action = next(iter(actions))
    return {
        "schema": SCHEMA,
        "decision_sufficient": True,
        "action": action,
        "reason": "ALL_SURVIVING_SAFE_HYPOTHESES_AGREE",
        "surviving_hypothesis_count": len(alive),
        "full_environment_model_required": False,
    }


def invalidation_cone(
    *,
    graph: Mapping[str, Sequence[str]],
    changed: Iterable[Any],
) -> dict[str, Any]:
    """Invalidate changed facts and only their transitive dependents."""
    q = deque(sorted(_clean_atoms(changed)))
    invalidated: set[str] = set(q)
    while q:
        node = q.popleft()
        for child in graph.get(node, ()):
            c = str(child).strip()
            if c and c not in invalidated:
                invalidated.add(c)
                q.append(c)
    return {
        "schema": SCHEMA,
        "invalidated": sorted(invalidated),
        "global_reset_required": False,
    }


def _wilson_lcb(successes: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = successes / n
    denom = 1.0 + z * z / n
    centre = p + z * z / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def meta_strategy_candidate(
    episodes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Propose a learning-strategy candidate from verified episodes only.

    Meta-learning can rank candidates but never authorizes its own promotion.
    """
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    verified_count = 0
    for row in episodes:
        if row.get("verified") is not True:
            continue
        strategy = str(row.get("strategy") or "").strip()
        if not strategy:
            continue
        verified_count += 1
        grouped[strategy].append(row)

    if not grouped:
        return {
            "schema": SCHEMA,
            "candidate_strategy": None,
            "verified_episode_count": verified_count,
            "promotion_authorized": False,
            "reason": "NO_VERIFIED_STRATEGY_EPISODES",
        }

    ranked: list[tuple[float, float, int, str]] = []
    details: dict[str, Any] = {}
    for strategy, rows in grouped.items():
        n = len(rows)
        successes = sum(1 for x in rows if x.get("success") is True)
        times: list[float] = []
        for x in rows:
            try:
                t = float(x.get("wall_clock"))
            except (TypeError, ValueError):
                t = math.inf
            if not math.isfinite(t) or t < 0:
                t = math.inf
            times.append(t)
        mean_time = sum(times) / n if all(math.isfinite(t) for t in times) else math.inf
        lcb = _wilson_lcb(successes, n)
        utility = lcb / (1.0 + mean_time) if math.isfinite(mean_time) else 0.0
        ranked.append((-utility, mean_time, -n, strategy))
        details[strategy] = {
            "verified_episodes": n,
            "successes": successes,
            "success_rate_lcb": lcb,
            "mean_wall_clock": mean_time,
            "conservative_learning_utility": utility,
        }

    ranked.sort()
    candidate = ranked[0][3]
    return {
        "schema": SCHEMA,
        "candidate_strategy": candidate,
        "verified_episode_count": verified_count,
        "strategy_evidence": details,
        "promotion_authorized": False,
        "separate_strategy_verification_required": True,
    }


def compile_verified_episode(
    *,
    candidate_id: str,
    verification_pass: bool,
    learned_atoms: Iterable[Any],
    dependencies: Iterable[Any],
    invalidators: Iterable[Any],
) -> dict[str, Any]:
    """Compile a verified episode into a proof-carrying reusable skill record."""
    verdict = v1.verify_candidate(
        candidate_id=candidate_id,
        verification_pass=verification_pass is True,
    )
    learned = sorted(_clean_atoms(learned_atoms))
    deps = sorted(_clean_atoms(dependencies))
    inv = sorted(_clean_atoms(invalidators))
    return {
        "schema": SCHEMA,
        "candidate_id": candidate_id,
        "state": verdict["state"],
        "trusted": verdict["trusted"],
        "promotion_authorized": verdict["promotion_authorized"],
        "learned_atoms": learned,
        "dependencies": deps,
        "invalidators": inv,
        "proof_carrying": verdict["trusted"] and bool(learned),
    }


def prove_optimizer_invariants() -> dict[str, Any]:
    errors: list[str] = []

    v1_theorem = v1.prove_control_invariants()
    if v1_theorem.get("pass") is not True:
        errors.append("V1_SAFETY_GATE_NOT_PROVED")

    delta = minimum_novelty_delta(
        required_atoms={"a", "b"},
        verified_atoms={"a", "z"},
    )
    if delta["missing_atoms"] != ["b"] or delta["reused_atoms"] != ["a"]:
        errors.append("MINIMUM_NOVELTY_DELTA_NOT_EXACT")

    bad_transfer = admit_transfer(
        source_id="s",
        source_verified=True,
        scope_relation="ANALOGOUS",
        target_atom="t",
        falsifier="x",
    )
    if bad_transfer["admitted"]:
        errors.append("ANALOGY_ONLY_TRANSFER_ADMITTED")

    selected = choose_learning_action([
        {
            "id": "unsafe",
            "channel": "SAFE_EXPERIMENT",
            "safe": False,
            "decision_gain_lcb": 1,
            "future_transfer_lcb": 1,
            "proof_value_lcb": 1,
            "wall_clock_ub": 0.01,
            "cost_ub": 0,
            "risk_ub": 0,
        },
        {
            "id": "safe",
            "channel": "DERIVE_AND_REASON",
            "safe": True,
            "decision_gain_lcb": 0.1,
            "future_transfer_lcb": 0.1,
            "proof_value_lcb": 0.1,
            "wall_clock_ub": 1,
            "cost_ub": 0,
            "risk_ub": 0,
        },
    ])
    if selected["selected_action_id"] != "safe":
        errors.append("UNSAFE_ACTION_SELECTED")

    stop = decision_sufficiency(hypotheses=[
        {"id": "h1", "alive": True, "recommended_action": "x", "safety_ok": True},
        {"id": "h2", "alive": True, "recommended_action": "x", "safety_ok": True},
    ])
    if stop.get("decision_sufficient") is not True:
        errors.append("DECISION_SUFFICIENCY_NOT_RECOGNIZED")

    cone = invalidation_cone(
        graph={"changed": ["dependent"], "other": ["unrelated"]},
        changed={"changed"},
    )
    if cone["invalidated"] != ["changed", "dependent"]:
        errors.append("DEPENDENCY_CONE_NOT_MINIMAL")

    meta = meta_strategy_candidate([
        {"strategy": "s", "verified": True, "success": True, "wall_clock": 1},
    ])
    if meta.get("promotion_authorized") is not False:
        errors.append("META_LEARNER_SELF_PROMOTION_ALLOWED")

    passed = not errors
    return {
        "schema": SCHEMA,
        "status": "UNIVERSAL_LEARNING_OPTIMIZER_V2_INVARIANTS_PASS" if passed else "FAIL_CLOSED",
        "pass": passed,
        "errors": errors,
        "v1_required_as_safety_gate": True,
        "minimum_novelty_delta_exact": passed,
        "verified_transfer_only": passed,
        "safe_zero_spend_action_selection": passed,
        "decision_sufficient_stopping": passed,
        "dependency_cone_invalidation": passed,
        "meta_learning_self_promotion_forbidden": passed,
        "semantic_success_rate_proved": False,
        "unknown_domain_acceptance_proved": False,
        "tool_learning_acceptance_credit_added": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "incremental_spend_usd": 0,
    }
