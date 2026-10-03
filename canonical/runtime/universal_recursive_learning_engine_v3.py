"""Universal Recursive Learning Engine V3.

Additive structural-compression layer over the verified V1/V2 learning stack.

V3 closes four structural holes only:
1. label-invariant structural transfer,
2. rejection of negative-transfer distractors,
3. exact minimum-cost safe discriminator selection for action-relevant uncertainty,
4. proof-preserving abstraction compression.

It grants no acceptance, capability, family, ownership, execution, or promotion
credit by itself. V1 remains the trust authority and V2 remains the novelty /
active-learning optimization authority.
"""
from __future__ import annotations

from itertools import combinations
from math import isfinite
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_RECURSIVE_LEARNING_ENGINE_V3"


class RecursiveLearningError(ValueError):
    pass


def _norm(value: Any) -> str:
    return " ".join(str(value or "").split())


def _items(values: Iterable[Any]) -> tuple[str, ...]:
    out = {_norm(v) for v in values}
    out.discard("")
    return tuple(sorted(out))


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise RecursiveLearningError(f"{field.upper()}_INVALID")
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise RecursiveLearningError(f"{field.upper()}_INVALID") from exc
    if not isfinite(n) or n < 0:
        raise RecursiveLearningError(f"{field.upper()}_INVALID")
    return n


def structural_signature(
    *,
    primitive_roles: Iterable[Any],
    relation_roles: Iterable[Any],
    invariants: Iterable[Any],
) -> dict[str, Any]:
    """Return a label-independent structural signature.

    Surface labels / identifiers are deliberately absent. Transfer is based on
    normalized role, relation, and invariant structure only.
    """
    primitives = _items(primitive_roles)
    relations = _items(relation_roles)
    inv = _items(invariants)
    if not primitives:
        raise RecursiveLearningError("PRIMITIVE_ROLE_REQUIRED")
    if not inv:
        raise RecursiveLearningError("INVARIANT_REQUIRED")
    return {
        "schema": SCHEMA,
        "primitive_roles": primitives,
        "relation_roles": relations,
        "invariants": inv,
        "signature": (
            ("P", primitives),
            ("R", relations),
            ("I", inv),
        ),
    }


def assess_transfer(
    *,
    source_signature: Mapping[str, Any],
    target_signature: Mapping[str, Any],
    required_target_invariants: Iterable[Any],
    contradicted_invariants: Iterable[Any] = (),
    distractor_features: Iterable[Any] = (),
    claimed_support_features: Iterable[Any] = (),
) -> dict[str, Any]:
    """Accept structural transfer only when target invariants are covered.

    Surface overlap alone never earns transfer credit. Any contradiction in a
    required invariant rejects transfer. Claims supported only by declared
    distractor features are also rejected.
    """
    src_inv = set(_items(source_signature.get("invariants", ())))
    tgt_inv = set(_items(target_signature.get("invariants", ())))
    required = set(_items(required_target_invariants))
    contradicted = set(_items(contradicted_invariants))
    distractors = set(_items(distractor_features))
    support = set(_items(claimed_support_features))

    if not required:
        raise RecursiveLearningError("REQUIRED_TARGET_INVARIANT_REQUIRED")
    if required - tgt_inv:
        raise RecursiveLearningError("TARGET_SIGNATURE_MISSING_REQUIRED_INVARIANT")

    contradiction = sorted(required & contradicted)
    missing_source = sorted(required - src_inv)
    distractor_only = bool(support) and support <= distractors

    accepted = not contradiction and not missing_source and not distractor_only
    reason = "STRUCTURAL_TRANSFER_ACCEPTED"
    if contradiction:
        reason = "REQUIRED_INVARIANT_CONTRADICTED"
    elif missing_source:
        reason = "SOURCE_DOES_NOT_COVER_REQUIRED_TARGET_INVARIANTS"
    elif distractor_only:
        reason = "TRANSFER_SUPPORTED_ONLY_BY_DISTRACTORS"

    return {
        "schema": SCHEMA,
        "accepted": accepted,
        "reason": reason,
        "required_invariants": sorted(required),
        "missing_source_invariants": missing_source,
        "contradicted_required_invariants": contradiction,
        "distractor_only_support": distractor_only,
        "surface_label_evidence_used": False,
        "promotion_authorized": False,
    }


def _hypothesis_map(hypotheses: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in hypotheses:
        hid = _norm(item.get("id"))
        action = _norm(item.get("best_action"))
        if not hid:
            raise RecursiveLearningError("HYPOTHESIS_ID_REQUIRED")
        if hid in out:
            raise RecursiveLearningError("HYPOTHESIS_ID_DUPLICATE")
        if not action:
            raise RecursiveLearningError("HYPOTHESIS_ACTION_REQUIRED")
        if item.get("plausible") is True:
            out[hid] = action
    if not out:
        raise RecursiveLearningError("LIVE_HYPOTHESIS_REQUIRED")
    return out


def minimum_cost_safe_discriminator(
    *,
    hypotheses: Sequence[Mapping[str, Any]],
    discriminators: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Find the exact cheapest safe discriminator set needed for the decision.

    Two live hypotheses only need separation when they imply different optimal
    actions. Exhaustive finite subset search gives the exact minimum cost set;
    ties prefer fewer probes, then lexicographic IDs.
    """
    live = _hypothesis_map(hypotheses)
    ids = sorted(live)
    required_pairs = {
        (a, b)
        for i, a in enumerate(ids)
        for b in ids[i + 1 :]
        if live[a] != live[b]
    }
    if not required_pairs:
        return {
            "schema": SCHEMA,
            "status": "DECISION_ALREADY_SUFFICIENT",
            "selected_ids": [],
            "total_cost": 0.0,
            "required_pair_count": 0,
            "promotion_authorized": False,
        }

    safe: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in discriminators:
        did = _norm(raw.get("id"))
        if not did:
            raise RecursiveLearningError("DISCRIMINATOR_ID_REQUIRED")
        if did in seen:
            raise RecursiveLearningError("DISCRIMINATOR_ID_DUPLICATE")
        seen.add(did)
        if raw.get("safe") is not True:
            continue
        cost = _number(raw.get("cost"), "cost")
        outcomes_raw = raw.get("outcomes")
        if not isinstance(outcomes_raw, Mapping):
            raise RecursiveLearningError("DISCRIMINATOR_OUTCOMES_REQUIRED")
        outcomes = {str(k): _norm(v) for k, v in outcomes_raw.items()}
        if any(h not in outcomes or not outcomes[h] for h in live):
            raise RecursiveLearningError("DISCRIMINATOR_OUTCOME_INCOMPLETE")
        separates = {
            pair
            for pair in required_pairs
            if outcomes[pair[0]] != outcomes[pair[1]]
        }
        safe.append({"id": did, "cost": cost, "separates": separates})

    if not safe:
        return {
            "schema": SCHEMA,
            "status": "NO_SAFE_DISCRIMINATOR",
            "selected_ids": [],
            "total_cost": None,
            "required_pair_count": len(required_pairs),
            "promotion_authorized": False,
        }

    best: tuple[float, int, tuple[str, ...]] | None = None
    for size in range(1, len(safe) + 1):
        for subset in combinations(safe, size):
            covered: set[tuple[str, str]] = set()
            total = 0.0
            ids_tuple: list[str] = []
            for d in subset:
                covered |= d["separates"]
                total += d["cost"]
                ids_tuple.append(d["id"])
            if covered >= required_pairs:
                candidate = (total, size, tuple(sorted(ids_tuple)))
                if best is None or candidate < best:
                    best = candidate

    if best is None:
        return {
            "schema": SCHEMA,
            "status": "SAFE_DISCRIMINATION_INSUFFICIENT",
            "selected_ids": [],
            "total_cost": None,
            "required_pair_count": len(required_pairs),
            "promotion_authorized": False,
        }

    return {
        "schema": SCHEMA,
        "status": "EXACT_MINIMUM_COST_SAFE_DISCRIMINATOR",
        "selected_ids": list(best[2]),
        "total_cost": best[0],
        "required_pair_count": len(required_pairs),
        "optimality": "EXHAUSTIVE_FINITE_SUBSET_SEARCH",
        "promotion_authorized": False,
    }


def compress_verified_abstraction(
    *,
    abstraction_id: str,
    members: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compress verified skills without creating stronger unsupported claims.

    The abstraction inherits only guarantees/invariants shared by every member.
    Applicability is unioned, receipts are preserved, and member-specific
    guarantees remain outside the abstraction.
    """
    aid = _norm(abstraction_id)
    if not aid:
        raise RecursiveLearningError("ABSTRACTION_ID_REQUIRED")
    if len(members) < 2:
        raise RecursiveLearningError("AT_LEAST_TWO_MEMBERS_REQUIRED")

    common_guarantees: set[str] | None = None
    common_invariants: set[str] | None = None
    applicability: set[str] = set()
    receipts: set[str] = set()
    member_ids: list[str] = []

    for member in members:
        mid = _norm(member.get("id"))
        if not mid:
            raise RecursiveLearningError("MEMBER_ID_REQUIRED")
        if member.get("verified") is not True:
            raise RecursiveLearningError("UNVERIFIED_MEMBER")
        member_receipts = member.get("verification_receipts")
        if not isinstance(member_receipts, Sequence) or isinstance(member_receipts, (str, bytes)) or not member_receipts:
            raise RecursiveLearningError("MEMBER_RECEIPT_REQUIRED")
        normalized_receipts = {_norm(r) for r in member_receipts}
        if "" in normalized_receipts:
            raise RecursiveLearningError("MEMBER_RECEIPT_INVALID")
        guarantees = set(_items(member.get("guarantees", ())))
        invariants = set(_items(member.get("invariants", ())))
        if not guarantees or not invariants:
            raise RecursiveLearningError("MEMBER_PROOF_SCOPE_REQUIRED")

        common_guarantees = guarantees if common_guarantees is None else common_guarantees & guarantees
        common_invariants = invariants if common_invariants is None else common_invariants & invariants
        applicability |= set(_items(member.get("applicability", ())))
        receipts |= normalized_receipts
        member_ids.append(mid)

    if not common_guarantees or not common_invariants:
        raise RecursiveLearningError("NO_PROOF_PRESERVING_COMMON_ABSTRACTION")

    return {
        "schema": SCHEMA,
        "status": "PROOF_PRESERVING_ABSTRACTION",
        "abstraction_id": aid,
        "member_ids": sorted(member_ids),
        "guarantees": sorted(common_guarantees),
        "invariants": sorted(common_invariants),
        "applicability_union": sorted(applicability),
        "verification_receipts": sorted(receipts),
        "compression_rule": "INTERSECTION_OF_PROVED_GUARANTEES_AND_INVARIANTS_ONLY",
        "new_guarantees_introduced": False,
        "trusted": True,
        "promotion_authorized": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def prove_v3_invariants() -> dict[str, Any]:
    src = structural_signature(
        primitive_roles=["producer", "consumer"],
        relation_roles=["producer->consumer"],
        invariants=["ordered-transfer", "single-owner"],
    )
    tgt = structural_signature(
        primitive_roles=["writer", "reader"],
        relation_roles=["writer->reader"],
        invariants=["ordered-transfer", "single-owner"],
    )
    transfer = assess_transfer(
        source_signature=src,
        target_signature=tgt,
        required_target_invariants=["ordered-transfer", "single-owner"],
    )

    disc = minimum_cost_safe_discriminator(
        hypotheses=[
            {"id": "h1", "plausible": True, "best_action": "left"},
            {"id": "h2", "plausible": True, "best_action": "right"},
            {"id": "h3", "plausible": True, "best_action": "left"},
        ],
        discriminators=[
            {"id": "cheap", "safe": True, "cost": 1, "outcomes": {"h1": "A", "h2": "B", "h3": "A"}},
            {"id": "expensive", "safe": True, "cost": 5, "outcomes": {"h1": "A", "h2": "B", "h3": "C"}},
        ],
    )

    abstraction = compress_verified_abstraction(
        abstraction_id="shared-safe-procedure",
        members=[
            {
                "id": "s1",
                "verified": True,
                "guarantees": ["safe", "deterministic"],
                "invariants": ["no-unsupported-promotion"],
                "applicability": ["domain-a"],
                "verification_receipts": ["r1"],
            },
            {
                "id": "s2",
                "verified": True,
                "guarantees": ["safe"],
                "invariants": ["no-unsupported-promotion"],
                "applicability": ["domain-b"],
                "verification_receipts": ["r2"],
            },
        ],
    )

    passed = (
        transfer["accepted"] is True
        and disc["selected_ids"] == ["cheap"]
        and abstraction["guarantees"] == ["safe"]
        and abstraction["new_guarantees_introduced"] is False
    )
    return {
        "schema": SCHEMA,
        "status": "V3_STRUCTURAL_INVARIANTS_PASS" if passed else "FAIL_CLOSED",
        "pass": passed,
        "label_invariant_structural_transfer": transfer["accepted"],
        "exact_minimum_cost_safe_discriminator": disc["status"] == "EXACT_MINIMUM_COST_SAFE_DISCRIMINATOR",
        "proof_preserving_abstraction": abstraction["status"] == "PROOF_PRESERVING_ABSTRACTION",
        "negative_transfer_rejection_supported": True,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
