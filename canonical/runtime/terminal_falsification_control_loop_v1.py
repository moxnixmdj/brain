from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Mapping, Sequence

LANE_ORDER = {
    "UNIVERSE_AUTHORITY": 0,
    "EFFECT_CLOSURE": 1,
    "CONDITION_TRANSFER": 2,
    "PERFORMANCE_WITNESS": 3,
    "OWNERSHIP": 4,
}

LIVE_STATUSES = {
    "ACTIVE",
    "SURVIVED_NONEXHAUSTIVE",
    "SURVIVED_EXHAUSTIVE",
    "PROVED",
}

@dataclass(frozen=True)
class ClaimVerdict:
    claim_id: str
    lane: str
    effective_status: str
    proof_credit: int
    blocked_by: Sequence[str]
    reason: str

@dataclass(frozen=True)
class ControlLoopResult:
    terminal_ready: bool
    universe_complete: bool
    proof_credit_delta: int
    ordered_claim_ids: Sequence[str]
    dead_claim_ids: Sequence[str]
    unrepaired_dead_claim_ids: Sequence[str]
    blocked_claim_ids: Sequence[str]
    verdicts: Sequence[Dict[str, Any]]

def _sha1(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(c in "0123456789abcdef" for c in value)
    )

def _binding(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and bool(value["path"].strip())
        and _sha1(value.get("git_blob_sha"))
    )

def _validate_claim(claim: Mapping[str, Any]) -> None:
    required = ("id", "lane", "status", "cost_units", "target_truth_obligations")
    missing = [k for k in required if k not in claim]
    if missing:
        raise ValueError(f"missing claim fields: {missing}")
    if claim["lane"] not in LANE_ORDER:
        raise ValueError(f"unknown lane: {claim['lane']}")
    if claim["status"] not in LIVE_STATUSES | {"FALSIFIED", "BLOCKED"}:
        raise ValueError(f"unknown status: {claim['status']}")
    if not isinstance(claim["cost_units"], int) or claim["cost_units"] <= 0:
        raise ValueError("cost_units must be a positive integer")
    if not isinstance(claim["target_truth_obligations"], list):
        raise ValueError("target_truth_obligations must be a list")
    count = claim.get(
        "target_truth_obligation_count",
        len(set(claim["target_truth_obligations"])),
    )
    if not isinstance(count, int) or count < len(set(claim["target_truth_obligations"])) or count <= 0:
        raise ValueError("target_truth_obligation_count must be a positive integer not smaller than the explicit unique target list")

def _successors(claims: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    out: Dict[str, List[Mapping[str, Any]]] = {}
    for claim in claims:
        predecessor = claim.get("successor_of")
        if predecessor:
            out.setdefault(predecessor, []).append(claim)
    return out

def _live_successor_exists(
    predecessor: str,
    successor_map: Mapping[str, Sequence[Mapping[str, Any]]],
) -> bool:
    return any(c.get("status") in LIVE_STATUSES for c in successor_map.get(predecessor, ()))

def _dependency_blockers(
    claim: Mapping[str, Any],
    by_id: Mapping[str, Mapping[str, Any]],
    successor_map: Mapping[str, Sequence[Mapping[str, Any]]],
) -> List[str]:
    blockers: List[str] = []
    for dep in claim.get("depends_on", []):
        target = by_id.get(dep)
        if target is None:
            blockers.append(dep)
            continue
        if target.get("status") == "FALSIFIED" and not _live_successor_exists(dep, successor_map):
            blockers.append(dep)
    return blockers

def _proof_credit(claim: Mapping[str, Any]) -> int:
    # Falsifier survival is not proof. Proof credit requires explicit PROVED
    # promotion plus one or more content-addressed proof receipts.
    if claim.get("status") != "PROVED":
        return 0
    receipts = claim.get("proof_receipts")
    if not isinstance(receipts, list) or not receipts or not all(_binding(x) for x in receipts):
        return 0
    return 1

def _target_count(claim: Mapping[str, Any]) -> int:
    return claim.get(
        "target_truth_obligation_count",
        len(set(claim.get("target_truth_obligations", []))),
    )

def _priority_key(claim: Mapping[str, Any]) -> tuple:
    # Universe authority has strict logical precedence. All remaining lanes are
    # compared by deterministic proof-state reachability per unit cost. Lane
    # order is only a deterministic tie-breaker, not a claim of higher value.
    authority_rank = 0 if claim["lane"] == "UNIVERSE_AUTHORITY" else 1
    cost = claim["cost_units"]
    leverage = _target_count(claim) / cost
    return (authority_rank, -leverage, LANE_ORDER[claim["lane"]], cost, claim["id"])

def compile_control_loop(state: Mapping[str, Any]) -> ControlLoopResult:
    claims = list(state.get("claims", []))
    if not claims:
        raise ValueError("claims must be non-empty")
    for claim in claims:
        _validate_claim(claim)

    by_id = {claim["id"]: claim for claim in claims}
    if len(by_id) != len(claims):
        raise ValueError("claim ids must be unique")

    successor_map = _successors(claims)
    universe_ids = [c["id"] for c in claims if c["lane"] == "UNIVERSE_AUTHORITY"]
    if not universe_ids:
        raise ValueError("at least one UNIVERSE_AUTHORITY claim is required")

    verdicts: List[ClaimVerdict] = []
    schedulable: List[Mapping[str, Any]] = []
    dead: List[str] = []
    unrepaired_dead: List[str] = []
    blocked: List[str] = []

    for claim in claims:
        cid = claim["id"]
        if claim["status"] == "FALSIFIED":
            dead.append(cid)
            repaired = _live_successor_exists(cid, successor_map)
            if not repaired:
                unrepaired_dead.append(cid)
            verdicts.append(ClaimVerdict(
                claim_id=cid,
                lane=claim["lane"],
                effective_status="DEAD_REPAIRED_BY_SUCCESSOR" if repaired else "DEAD_UNREPAIRED",
                proof_credit=0,
                blocked_by=(),
                reason=(
                    "FALSIFIED_ROUTE_REPLACED_BY_LIVE_SUCCESSOR"
                    if repaired
                    else "FALSIFIED_ROUTE_HAS_NO_LIVE_REPAIRED_SUCCESSOR_AND_REMAINS_A_TERMINAL_BLOCKER"
                ),
            ))
            continue

        dependency_blockers = _dependency_blockers(claim, by_id, successor_map)
        if dependency_blockers:
            blocked.append(cid)
            verdicts.append(ClaimVerdict(
                claim_id=cid,
                lane=claim["lane"],
                effective_status="BLOCKED",
                proof_credit=0,
                blocked_by=tuple(dependency_blockers),
                reason="DEPENDENCY_IS_FALSIFIED_OR_MISSING_WITHOUT_A_LIVE_REPAIRED_SUCCESSOR",
            ))
            continue

        credit = _proof_credit(claim)
        if claim["status"] in {"SURVIVED_NONEXHAUSTIVE", "SURVIVED_EXHAUSTIVE"}:
            reason = "NO_COUNTEREXAMPLE_SURVIVAL_IS_ZERO_PROOF_CREDIT_UNTIL_SEPARATE_PROOF_PROMOTION"
        elif claim["status"] == "PROVED" and credit == 0:
            reason = "PROVED_LABEL_WITHOUT_VALID_CONTENT_ADDRESSED_PROOF_RECEIPTS_IS_ZERO_CREDIT"
        else:
            reason = "LIVE_CLAIM"

        verdicts.append(ClaimVerdict(
            claim_id=cid,
            lane=claim["lane"],
            effective_status=claim["status"],
            proof_credit=credit,
            blocked_by=(),
            reason=reason,
        ))

        if claim["status"] != "PROVED":
            schedulable.append(claim)

    schedulable.sort(key=_priority_key)

    universe_complete = any(
        by_id[cid].get("status") == "PROVED" and _proof_credit(by_id[cid]) == 1
        for cid in universe_ids
    )

    known_open = state.get("known_open_truth_obligations")
    if not isinstance(known_open, int) or known_open < 0:
        raise ValueError("known_open_truth_obligations must be a nonnegative integer")

    unresolved_nonuniverse = any(
        v.effective_status not in {"PROVED", "DEAD_REPAIRED_BY_SUCCESSOR"}
        and v.lane != "UNIVERSE_AUTHORITY"
        for v in verdicts
    )

    terminal_ready = (
        universe_complete
        and known_open == 0
        and not unresolved_nonuniverse
        and not blocked
        and not unrepaired_dead
    )

    return ControlLoopResult(
        terminal_ready=terminal_ready,
        universe_complete=universe_complete,
        proof_credit_delta=0,
        ordered_claim_ids=tuple(c["id"] for c in schedulable),
        dead_claim_ids=tuple(dead),
        unrepaired_dead_claim_ids=tuple(unrepaired_dead),
        blocked_claim_ids=tuple(blocked),
        verdicts=tuple(asdict(v) for v in verdicts),
    )
