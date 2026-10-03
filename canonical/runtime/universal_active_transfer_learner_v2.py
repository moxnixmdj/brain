"""Universal Active Transfer Learner V2.

Additive optimization layer over Project Brain's verified Universal Learning
Contract V1. V2 does not widen acceptance or ownership claims. It minimizes
what must be learned, ranks information-acquisition actions by decision value,
stops once remaining hypotheses imply the same action, invalidates only the
dependency cone affected by change, and compiles verified learning episodes
into reusable skills and learning-strategy hints.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_ACTIVE_TRANSFER_LEARNER_V2"


class ActiveTransferLearnerError(ValueError):
    pass


def _items(values: Iterable[Any]) -> set[str]:
    out: set[str] = set()
    for value in values:
        item = str(value).strip()
        if item:
            out.add(item)
    return out


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ActiveTransferLearnerError(f"{field.upper()}_INVALID")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ActiveTransferLearnerError(f"{field.upper()}_INVALID") from exc
    if not isfinite(number):
        raise ActiveTransferLearnerError(f"{field.upper()}_INVALID")
    return number


def minimum_novelty_delta(*, required_facts: Iterable[Any], verified_facts: Iterable[Any]) -> dict[str, Any]:
    required = _items(required_facts)
    verified = _items(verified_facts)
    covered = sorted(required & verified)
    missing = sorted(required - verified)
    return {
        "schema": SCHEMA,
        "status": "FULLY_COVERED" if not missing else "NOVELTY_DELTA_OPEN",
        "required": sorted(required),
        "covered": covered,
        "missing": missing,
        "novelty_ratio": (len(missing) / len(required)) if required else 0.0,
        "acceptance_credit": False,
        "ownership_credit": False,
    }


def rank_learning_actions(
    actions: Sequence[Mapping[str, Any]],
    *,
    decision_weight: float = 1.0,
    transfer_weight: float = 0.5,
    proof_weight: float = 0.5,
) -> list[dict[str, Any]]:
    weights = {
        "decision_weight": _number(decision_weight, "decision_weight"),
        "transfer_weight": _number(transfer_weight, "transfer_weight"),
        "proof_weight": _number(proof_weight, "proof_weight"),
    }
    if any(value < 0 for value in weights.values()):
        raise ActiveTransferLearnerError("NEGATIVE_WEIGHT")

    ranked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in actions:
        action_id = str(raw.get("id") or "").strip()
        if not action_id:
            raise ActiveTransferLearnerError("ACTION_ID_REQUIRED")
        if action_id in seen:
            raise ActiveTransferLearnerError("ACTION_ID_DUPLICATE")
        seen.add(action_id)

        decision = _number(raw.get("decision_gain", 0), "decision_gain")
        transfer = _number(raw.get("transfer_gain", 0), "transfer_gain")
        proof = _number(raw.get("proof_gain", 0), "proof_gain")
        time = _number(raw.get("time", 0), "time")
        cost = _number(raw.get("cost", 0), "cost")
        risk = _number(raw.get("risk", 0), "risk")
        if any(value < 0 for value in (decision, transfer, proof, time, cost, risk)):
            raise ActiveTransferLearnerError("NEGATIVE_ACTION_DIMENSION")
        denominator = time + cost + risk
        if denominator <= 0:
            raise ActiveTransferLearnerError("ACTION_TOTAL_COST_MUST_BE_POSITIVE")
        numerator = (
            weights["decision_weight"] * decision
            + weights["transfer_weight"] * transfer
            + weights["proof_weight"] * proof
        )
        item = dict(raw)
        item["value_density"] = numerator / denominator
        item["decision_value"] = decision
        item["transfer_value"] = transfer
        item["proof_value"] = proof
        item["total_cost"] = denominator
        ranked.append(item)

    ranked.sort(key=lambda item: (-item["value_density"], str(item["id"])))
    return ranked


def update_hypotheses(
    hypotheses: Sequence[Mapping[str, Any]], *, contradicted_ids: Iterable[Any] = ()
) -> dict[str, Any]:
    contradicted = _items(contradicted_ids)
    known_ids: set[str] = set()
    live: list[str] = []
    eliminated: list[str] = []
    for hypothesis in hypotheses:
        hid = str(hypothesis.get("id") or "").strip()
        if not hid:
            raise ActiveTransferLearnerError("HYPOTHESIS_ID_REQUIRED")
        if hid in known_ids:
            raise ActiveTransferLearnerError("HYPOTHESIS_ID_DUPLICATE")
        known_ids.add(hid)
        if hypothesis.get("plausible") is True and hid not in contradicted:
            live.append(hid)
        else:
            eliminated.append(hid)
    unknown = contradicted - known_ids
    if unknown:
        raise ActiveTransferLearnerError("CONTRADICTED_HYPOTHESIS_UNKNOWN:" + ",".join(sorted(unknown)))
    return {
        "schema": SCHEMA,
        "live_ids": sorted(live),
        "eliminated_ids": sorted(eliminated),
        "remaining_count": len(live),
    }


def decision_sufficient(hypotheses: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    live = [item for item in hypotheses if item.get("plausible") is True]
    if not live:
        return {"schema": SCHEMA, "sufficient": False, "action": None, "reason": "NO_LIVE_HYPOTHESES"}
    actions: set[str] = set()
    for hypothesis in live:
        action = str(hypothesis.get("best_action") or "").strip()
        if not action:
            return {"schema": SCHEMA, "sufficient": False, "action": None, "reason": "LIVE_HYPOTHESIS_WITHOUT_ACTION"}
        actions.add(action)
    if len(actions) == 1:
        return {
            "schema": SCHEMA,
            "sufficient": True,
            "action": next(iter(actions)),
            "reason": "ALL_LIVE_HYPOTHESES_AGREE",
        }
    return {
        "schema": SCHEMA,
        "sufficient": False,
        "action": None,
        "reason": "LIVE_HYPOTHESES_DISAGREE",
        "candidate_actions": sorted(actions),
    }


def invalidation_cone(*, changed: Iterable[Any], dependencies: Mapping[Any, Iterable[Any]]) -> dict[str, Any]:
    changed_set = _items(changed)
    graph: dict[str, set[str]] = {}
    all_nodes: set[str] = set(changed_set)
    for parent, children in dependencies.items():
        p = str(parent).strip()
        if not p:
            raise ActiveTransferLearnerError("DEPENDENCY_PARENT_REQUIRED")
        cs = _items(children)
        graph.setdefault(p, set()).update(cs)
        all_nodes.add(p)
        all_nodes.update(cs)

    invalidated: set[str] = set(changed_set)
    frontier = list(changed_set)
    while frontier:
        node = frontier.pop()
        for child in graph.get(node, set()):
            if child not in invalidated:
                invalidated.add(child)
                frontier.append(child)
    return {
        "schema": SCHEMA,
        "invalidated": sorted(invalidated),
        "preserved": sorted(all_nodes - invalidated),
    }


def compile_verified_skill(
    *,
    skill_id: str,
    applicability: Iterable[Any],
    dependencies: Iterable[Any],
    invalidators: Iterable[Any],
    verification_receipts: Iterable[Any],
) -> dict[str, Any]:
    sid = str(skill_id or "").strip()
    if not sid:
        raise ActiveTransferLearnerError("SKILL_ID_REQUIRED")
    receipts = _items(verification_receipts)
    if not receipts:
        raise ActiveTransferLearnerError("VERIFICATION_RECEIPT_REQUIRED")
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_SKILL",
        "skill_id": sid,
        "applicability": sorted(_items(applicability)),
        "dependencies": sorted(_items(dependencies)),
        "invalidators": sorted(_items(invalidators)),
        "verification_receipts": sorted(receipts),
        "trusted": True,
        "acceptance_credit": False,
        "ownership_credit": False,
        "promotion_authorized": False,
    }


def compile_learning_strategy(episode: Mapping[str, Any]) -> dict[str, Any]:
    if episode.get("verified") is not True:
        raise ActiveTransferLearnerError("VERIFIED_EPISODE_REQUIRED")
    domain = str(episode.get("domain") or "").strip()
    if not domain:
        raise ActiveTransferLearnerError("DOMAIN_REQUIRED")
    actions = episode.get("actions")
    if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes)) or not actions:
        raise ActiveTransferLearnerError("EPISODE_ACTIONS_REQUIRED")

    ranked: list[tuple[float, str]] = []
    for action in actions:
        if not isinstance(action, Mapping):
            raise ActiveTransferLearnerError("EPISODE_ACTION_INVALID")
        kind = str(action.get("kind") or "").strip()
        if not kind:
            raise ActiveTransferLearnerError("EPISODE_ACTION_KIND_REQUIRED")
        gain = _number(action.get("decision_gain", 0), "decision_gain")
        time = _number(action.get("time", 0), "time")
        if gain < 0 or time <= 0:
            raise ActiveTransferLearnerError("EPISODE_ACTION_VALUE_INVALID")
        ranked.append((gain / time, kind))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]))
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_META_STRATEGY_HINT",
        "domain": domain,
        "preferred_action_kind": ranked[0][1],
        "observed_value_density": ranked[0][0],
        "acceptance_credit": False,
        "ownership_credit": False,
        "promotion_authorized": False,
    }


def learning_episode(
    *,
    goal: str,
    required_facts: Iterable[Any],
    verified_facts: Iterable[Any],
    hypotheses: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_goal = " ".join(str(goal or "").split())
    if not normalized_goal:
        raise ActiveTransferLearnerError("GOAL_REQUIRED")
    delta = minimum_novelty_delta(required_facts=required_facts, verified_facts=verified_facts)
    if not delta["missing"]:
        return {
            "schema": SCHEMA,
            "goal": normalized_goal,
            "state": "VERIFIED_COVERAGE",
            "trusted": True,
            "promotion_authorized": True,
            "novelty_delta": delta,
            "decision_sufficiency": {"sufficient": True, "reason": "NO_NOVELTY_DELTA"},
            "next_action": None,
            "acceptance_credit": False,
            "ownership_credit": False,
        }

    ranked = rank_learning_actions(actions) if actions else []
    sufficiency = decision_sufficient(hypotheses)
    return {
        "schema": SCHEMA,
        "goal": normalized_goal,
        "state": "LEARNING",
        "trusted": False,
        "promotion_authorized": False,
        "novelty_delta": delta,
        "decision_sufficiency": sufficiency,
        "next_action": ranked[0] if ranked else None,
        "ranked_action_count": len(ranked),
        "acceptance_credit": False,
        "ownership_credit": False,
    }
