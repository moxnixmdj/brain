"""Universal Learning Engine V2 candidate for Project Brain.

Zero-credit candidate. Strengthens the verified V1 novelty router with:
- minimum novelty-delta subtraction,
- evidence-backed structural transfer,
- exact probability-aware decision sufficiency,
- decision-relevant active information acquisition,
- calibrated abstention / discriminator requests,
- dependency-cone invalidation,
- proof-carrying skill compilation.

It does NOT claim universal semantic success or Unknown-Domain acceptance.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_LEARNING_ENGINE_V2"
ALLOWED_TRANSFER_RELATIONS = {"EXACT", "PROVEN_STRONGER"}


class LearningEngineError(ValueError):
    pass


def _f(value: Fraction | int | str) -> Fraction:
    if isinstance(value, Fraction):
        return value
    return Fraction(value)


def normalize_probability_mass(probabilities: Mapping[str, Fraction | int | str]) -> dict[str, Fraction]:
    if not probabilities:
        raise LearningEngineError("HYPOTHESIS_PROBABILITIES_REQUIRED")
    out: dict[str, Fraction] = {}
    for hid, p in probabilities.items():
        hid = str(hid).strip()
        if not hid:
            raise LearningEngineError("EMPTY_HYPOTHESIS_ID")
        q = _f(p)
        if q < 0:
            raise LearningEngineError("NEGATIVE_PROBABILITY")
        out[hid] = q
    total = sum(out.values(), Fraction(0))
    if total <= 0:
        raise LearningEngineError("POSITIVE_PROBABILITY_MASS_REQUIRED")
    return {hid: p / total for hid, p in out.items() if p > 0}


def minimum_novelty_delta(*, required_primitives: Iterable[str], verified_primitives: Iterable[str]) -> dict:
    required = {str(x).strip() for x in required_primitives if str(x).strip()}
    verified = {str(x).strip() for x in verified_primitives if str(x).strip()}
    delta = sorted(required - verified)
    return {
        "schema": SCHEMA,
        "required_primitives": sorted(required),
        "verified_primitives_reused": sorted(required & verified),
        "novelty_delta": delta,
        "novelty_count": len(delta),
        "full_rediscovery_required": False,
    }


def admit_transfer_mapping(*, target_primitive: str, source_primitive: str, relation: str,
                           evidence_receipt: str, provenance_chain: Sequence[str],
                           mapping_basis: str) -> dict:
    target = str(target_primitive).strip()
    source = str(source_primitive).strip()
    receipt = str(evidence_receipt).strip()
    basis = str(mapping_basis).strip()
    prov = [str(x).strip() for x in provenance_chain if str(x).strip()]
    if not target or not source:
        raise LearningEngineError("TRANSFER_PRIMITIVE_REQUIRED")
    if relation not in ALLOWED_TRANSFER_RELATIONS:
        raise LearningEngineError("TRANSFER_RELATION_NOT_PROVED")
    if not receipt or not prov:
        raise LearningEngineError("TRANSFER_EVIDENCE_AND_PROVENANCE_REQUIRED")
    if basis in {"LABEL_MATCH", "IDENTIFIER_MATCH", "NAME_SIMILARITY"}:
        raise LearningEngineError("SURFACE_ONLY_TRANSFER_FORBIDDEN")
    return {
        "schema": SCHEMA,
        "target_primitive": target,
        "source_primitive": source,
        "relation": relation,
        "evidence_receipt": receipt,
        "provenance_chain": prov,
        "mapping_basis": basis,
        "transfer_admitted": True,
        "requires_full_rediscovery": False,
    }


@dataclass(frozen=True)
class LearningAction:
    action_id: str
    outcome_by_hypothesis: Mapping[str, str]
    time_cost: Fraction | int | str = 1
    monetary_cost: Fraction | int | str = 0
    risk_cost: Fraction | int | str = 0
    terminal_value: Fraction | int | str = 0
    future_transfer_value: Fraction | int | str = 0
    proof_value: Fraction | int | str = 0
    safe: bool = True


@dataclass(frozen=True)
class LearningWeights:
    decision: Fraction | int | str = 1
    terminal: Fraction | int | str = 1
    transfer: Fraction | int | str = 1
    proof: Fraction | int | str = 1
    monetary: Fraction | int | str = 1
    risk: Fraction | int | str = 1


def _action_mass(*, probs: Mapping[str, Fraction], terminal_action_by_hypothesis: Mapping[str, str]) -> dict[str, Fraction]:
    masses: dict[str, Fraction] = defaultdict(Fraction)
    for hid, p in probs.items():
        if hid not in terminal_action_by_hypothesis:
            raise LearningEngineError("MISSING_TERMINAL_ACTION:" + hid)
        masses[str(terminal_action_by_hypothesis[hid])] += p
    return dict(masses)


def decision_ambiguity(*, probs: Mapping[str, Fraction], terminal_action_by_hypothesis: Mapping[str, str]) -> Fraction:
    masses = _action_mass(probs=probs, terminal_action_by_hypothesis=terminal_action_by_hypothesis)
    return Fraction(1) - max(masses.values())


def decision_sufficient(*, probabilities: Mapping[str, Fraction | int | str],
                        terminal_action_by_hypothesis: Mapping[str, str]) -> dict:
    probs = normalize_probability_mass(probabilities)
    actions = {str(terminal_action_by_hypothesis[h]) for h in probs}
    sufficient = len(actions) == 1
    return {
        "schema": SCHEMA,
        "decision_sufficient": sufficient,
        "authorized_action": next(iter(actions)) if sufficient else None,
        "surviving_hypotheses": sorted(probs),
        "decision_ambiguity": str(decision_ambiguity(
            probs=probs, terminal_action_by_hypothesis=terminal_action_by_hypothesis
        )),
    }


def expected_post_probe_ambiguity(*, probs: Mapping[str, Fraction],
                                  terminal_action_by_hypothesis: Mapping[str, str],
                                  action: LearningAction) -> Fraction:
    missing = set(probs) - set(action.outcome_by_hypothesis)
    if missing:
        raise LearningEngineError("PROBE_MISSING_HYPOTHESES:" + ",".join(sorted(missing)))
    groups: dict[str, dict[str, Fraction]] = defaultdict(dict)
    for hid, p in probs.items():
        groups[str(action.outcome_by_hypothesis[hid])][hid] = p
    expected = Fraction(0)
    for group in groups.values():
        mass = sum(group.values(), Fraction(0))
        conditional = {hid: p / mass for hid, p in group.items()}
        expected += mass * decision_ambiguity(
            probs=conditional,
            terminal_action_by_hypothesis=terminal_action_by_hypothesis,
        )
    return expected


def rank_learning_actions(*, probabilities: Mapping[str, Fraction | int | str],
                          terminal_action_by_hypothesis: Mapping[str, str],
                          actions: Sequence[LearningAction],
                          weights: LearningWeights = LearningWeights()) -> list[dict]:
    probs = normalize_probability_mass(probabilities)
    before = decision_ambiguity(probs=probs, terminal_action_by_hypothesis=terminal_action_by_hypothesis)
    wd, wt, wx, wp = map(_f, (weights.decision, weights.terminal, weights.transfer, weights.proof))
    wm, wr = map(_f, (weights.monetary, weights.risk))
    ranked: list[dict] = []
    for action in actions:
        if not action.safe:
            continue
        after = expected_post_probe_ambiguity(
            probs=probs,
            terminal_action_by_hypothesis=terminal_action_by_hypothesis,
            action=action,
        )
        gain = before - after
        numerator = (
            wd * gain
            + wt * _f(action.terminal_value)
            + wx * _f(action.future_transfer_value)
            + wp * _f(action.proof_value)
        )
        denominator = (
            _f(action.time_cost)
            + wm * _f(action.monetary_cost)
            + wr * _f(action.risk_cost)
        )
        if denominator <= 0:
            raise LearningEngineError("NONPOSITIVE_ACTION_DENOMINATOR:" + action.action_id)
        ranked.append({
            "action_id": action.action_id,
            "decision_gain": gain,
            "expected_post_probe_ambiguity": after,
            "terminal_value": _f(action.terminal_value),
            "future_transfer_value": _f(action.future_transfer_value),
            "proof_value": _f(action.proof_value),
            "denominator": denominator,
            "score": numerator / denominator,
        })
    ranked.sort(key=lambda r: (-r["score"], -r["decision_gain"], r["denominator"], r["action_id"]))
    return ranked


def choose_learning_step(*, probabilities: Mapping[str, Fraction | int | str],
                         terminal_action_by_hypothesis: Mapping[str, str],
                         actions: Sequence[LearningAction],
                         weights: LearningWeights = LearningWeights()) -> dict:
    suff = decision_sufficient(
        probabilities=probabilities,
        terminal_action_by_hypothesis=terminal_action_by_hypothesis,
    )
    if suff["decision_sufficient"]:
        return {
            "schema": SCHEMA,
            "status": "DECISION_SUFFICIENT__EXECUTE",
            "authorized_action": suff["authorized_action"],
            "abstain": False,
            "probe": None,
        }
    ranked = rank_learning_actions(
        probabilities=probabilities,
        terminal_action_by_hypothesis=terminal_action_by_hypothesis,
        actions=actions,
        weights=weights,
    )
    useful = [
        r for r in ranked
        if r["decision_gain"] > 0 or r["terminal_value"] > 0 or r["proof_value"] > 0
    ]
    if useful:
        return {
            "schema": SCHEMA,
            "status": "SAFE_DISCRIMINATOR_REQUIRED",
            "authorized_action": None,
            "abstain": False,
            "probe": useful[0]["action_id"],
            "ranking": useful,
        }
    return {
        "schema": SCHEMA,
        "status": "NONIDENTIFIABLE_OR_UNDERSPECIFIED__ABSTAIN_OR_REQUEST_DISCRIMINATOR",
        "authorized_action": None,
        "abstain": True,
        "probe": None,
        "ranking": ranked,
    }


def dependency_cone_invalidation(*, changed_facts: Iterable[str],
                                 dependents: Mapping[str, Iterable[str]]) -> dict:
    changed = {str(x).strip() for x in changed_facts if str(x).strip()}
    graph = {
        str(k): {str(v).strip() for v in vals if str(v).strip()}
        for k, vals in dependents.items()
    }
    invalidated = set(changed)
    q = deque(changed)
    while q:
        node = q.popleft()
        for child in graph.get(node, set()):
            if child not in invalidated:
                invalidated.add(child)
                q.append(child)
    all_nodes = set(graph)
    for vals in graph.values():
        all_nodes.update(vals)
    return {
        "schema": SCHEMA,
        "changed_facts": sorted(changed),
        "invalidated_dependency_cone": sorted(invalidated),
        "preserved_outside_cone": sorted(all_nodes - invalidated),
        "global_reset_required": False,
    }


def compile_proof_carrying_skill(*, skill_id: str, learned_primitives: Sequence[str],
                                 applicability: Sequence[str], verification_receipts: Sequence[str],
                                 dependencies: Sequence[str], invalidators: Sequence[str],
                                 transfer_mappings: Sequence[Mapping]) -> dict:
    sid = str(skill_id).strip()
    receipts = [str(x).strip() for x in verification_receipts if str(x).strip()]
    if not sid or not receipts:
        raise LearningEngineError("SKILL_ID_AND_VERIFICATION_RECEIPT_REQUIRED")
    mappings = []
    for mapping in transfer_mappings:
        if mapping.get("transfer_admitted") is not True:
            raise LearningEngineError("UNVERIFIED_TRANSFER_MAPPING_IN_SKILL")
        mappings.append(dict(mapping))
    return {
        "schema": SCHEMA,
        "skill_id": sid,
        "state": "VERIFIED_REUSABLE",
        "learned_primitives": sorted({str(x).strip() for x in learned_primitives if str(x).strip()}),
        "applicability": sorted({str(x).strip() for x in applicability if str(x).strip()}),
        "verification_receipts": receipts,
        "dependencies": sorted({str(x).strip() for x in dependencies if str(x).strip()}),
        "invalidators": sorted({str(x).strip() for x in invalidators if str(x).strip()}),
        "transfer_mappings": mappings,
        "rediscovery_required_until_invalidated": False,
        "promotion_authorized": True,
    }
