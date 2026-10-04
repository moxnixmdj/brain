from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ROOT1_MINIMUM_DELTA_ACQUISITION_V3"

REQUIRED_SOURCE_CLASSES = (
    "CANONICAL_BRAIN_AND_PRIOR_RECEIPTS",
    "SOURCE_CODE_AND_PACKAGE_REGISTRIES",
    "OFFICIAL_DOCUMENTATION_AND_SPECIFICATIONS",
    "PAPERS_AND_CITATION_GRAPHS",
    "ISSUES_PULL_REQUESTS_AND_TECHNICAL_DISCUSSIONS",
    "COMMUNITY_AND_SOCIAL_DISCOVERY_LEADS",
)

class Root1InvariantError(ValueError):
    pass

@dataclass(frozen=True)
class ActionScore:
    action_id: str
    score: Fraction
    posterior_close_probability: Fraction
    denominator: Fraction
    covered: frozenset[str]

def _frac(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise Root1InvariantError(f"{name}_INVALID")
    try:
        out = value if isinstance(value, Fraction) else Fraction(str(value))
    except Exception as exc:
        raise Root1InvariantError(f"{name}_INVALID") from exc
    return out

def _primitive_set(values: Iterable[str]) -> frozenset[str]:
    out = frozenset(str(x).strip() for x in values if str(x).strip())
    if len(out) == 0:
        raise Root1InvariantError("PRIMITIVE_SET_EMPTY")
    return out

def minimum_capability_delta(
    required: Iterable[str],
    *,
    owned: Iterable[str] = (),
    transferable: Iterable[str] = (),
    composable: Iterable[str] = (),
    known_internalizable_routes: Iterable[str] = (),
) -> dict[str, Any]:
    required_set = _primitive_set(required)
    covered = (
        frozenset(owned)
        | frozenset(transferable)
        | frozenset(composable)
        | frozenset(known_internalizable_routes)
    )
    unknown_covered = covered - required_set
    if unknown_covered:
        raise Root1InvariantError("COVERAGE_OUTSIDE_FROZEN_ENVELOPE")
    residual = required_set - covered
    return {
        "schema": SCHEMA,
        "required_count": len(required_set),
        "covered_count": len(required_set) - len(residual),
        "residual_count": len(residual),
        "residual_primitives": sorted(residual),
        "covered_primitives": sorted(required_set & covered),
    }

def beta_posterior_mean(
    successes: int,
    trials: int,
    *,
    alpha: Any = Fraction(1, 2),
    beta: Any = Fraction(1, 2),
) -> Fraction:
    if successes < 0 or trials < 0 or successes > trials:
        raise Root1InvariantError("INVALID_SUCCESS_TRIAL_COUNTS")
    a = _frac(alpha, "ALPHA")
    b = _frac(beta, "BETA")
    if a <= 0 or b <= 0:
        raise Root1InvariantError("BETA_PRIOR_MUST_BE_POSITIVE")
    return (Fraction(successes, 1) + a) / (Fraction(trials, 1) + a + b)

def score_action(action: Mapping[str, Any]) -> ActionScore:
    action_id = str(action.get("action_id") or "").strip()
    if not action_id:
        raise Root1InvariantError("ACTION_ID_REQUIRED")

    p_close = beta_posterior_mean(
        int(action.get("successes", 0)),
        int(action.get("trials", 0)),
        alpha=action.get("alpha", Fraction(1, 2)),
        beta=action.get("beta", Fraction(1, 2)),
    )
    closure_mass = _frac(action.get("expected_closure_mass", 0), "EXPECTED_CLOSURE_MASS")
    information_gain = _frac(action.get("information_gain", 0), "INFORMATION_GAIN")
    transfer_gain = _frac(action.get("transfer_gain", 0), "TRANSFER_GAIN")
    proof_gain = _frac(action.get("proof_gain", 0), "PROOF_GAIN")
    time_cost = _frac(action.get("time_cost", 0), "TIME_COST")
    risk = _frac(action.get("risk", 0), "RISK")
    correlation_penalty = _frac(action.get("correlation_penalty", 0), "CORRELATION_PENALTY")

    for name, value in (
        ("EXPECTED_CLOSURE_MASS", closure_mass),
        ("INFORMATION_GAIN", information_gain),
        ("TRANSFER_GAIN", transfer_gain),
        ("PROOF_GAIN", proof_gain),
        ("TIME_COST", time_cost),
        ("RISK", risk),
        ("CORRELATION_PENALTY", correlation_penalty),
    ):
        if value < 0:
            raise Root1InvariantError(f"{name}_NEGATIVE")

    denominator = time_cost + risk + correlation_penalty
    if denominator <= 0:
        raise Root1InvariantError("ACTION_DENOMINATOR_NONPOSITIVE")

    numerator = p_close * closure_mass + information_gain + transfer_gain + proof_gain
    covered = frozenset(str(x) for x in action.get("covers", ()) if str(x))
    return ActionScore(
        action_id=action_id,
        score=numerator / denominator,
        posterior_close_probability=p_close,
        denominator=denominator,
        covered=covered,
    )

def rank_discovery_actions(
    actions: Sequence[Mapping[str, Any]],
    *,
    required_source_classes: Sequence[str] = REQUIRED_SOURCE_CLASSES,
) -> list[dict[str, Any]]:
    allowed = frozenset(required_source_classes)
    ranked = []
    for action in actions:
        source_class = str(action.get("source_class") or "")
        if source_class not in allowed:
            raise Root1InvariantError("UNKNOWN_SOURCE_CLASS")
        if _frac(action.get("incremental_spend_usd", 0), "INCREMENTAL_SPEND_USD") != 0:
            continue
        if action.get("safe") is not True:
            continue
        scored = score_action(action)
        ranked.append({
            "action_id": scored.action_id,
            "source_class": source_class,
            "score": scored.score,
            "posterior_close_probability": scored.posterior_close_probability,
            "covers": sorted(scored.covered),
        })
    ranked.sort(key=lambda row: (row["score"], row["posterior_close_probability"], row["action_id"]), reverse=True)
    return ranked

def route_is_admissible(route: Mapping[str, Any]) -> bool:
    return (
        route.get("verified") is True
        and route.get("safe") is True
        and route.get("durable") is True
        and route.get("internalizable") is True
        and route.get("ownership_compatible") is True
        and _frac(route.get("incremental_spend_usd", 0), "INCREMENTAL_SPEND_USD") == 0
    )

def _route_cost(route: Mapping[str, Any]) -> Fraction:
    return (
        _frac(route.get("expected_time", 0), "EXPECTED_TIME")
        + _frac(route.get("risk", 0), "RISK")
        + _frac(route.get("integration_cost", 0), "INTEGRATION_COST")
    )

def exact_minimum_route_cover(
    residual_primitives: Iterable[str],
    routes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    residual = _primitive_set(residual_primitives)
    usable = []
    for route in routes:
        if not route_is_admissible(route):
            continue
        route_id = str(route.get("route_id") or "").strip()
        if not route_id:
            raise Root1InvariantError("ROUTE_ID_REQUIRED")
        covers = frozenset(str(x) for x in route.get("covers", ()) if str(x)) & residual
        if not covers:
            continue
        cost = _route_cost(route)
        if cost < 0:
            raise Root1InvariantError("ROUTE_COST_NEGATIVE")
        usable.append((route_id, covers, cost))

    if not residual:
        return {
            "schema": SCHEMA,
            "status": "PASS__NO_RESIDUAL",
            "selected_routes": [],
            "total_cost": Fraction(0, 1),
            "covered_primitives": [],
        }

    best = None
    for r in range(1, len(usable) + 1):
        for combo in combinations(usable, r):
            covered = frozenset().union(*(row[1] for row in combo))
            if not residual <= covered:
                continue
            total_cost = sum((row[2] for row in combo), Fraction(0, 1))
            route_ids = tuple(sorted(row[0] for row in combo))
            candidate = (total_cost, len(combo), route_ids, covered)
            if best is None or candidate[:3] < best[:3]:
                best = candidate
    if best is None:
        return {
            "schema": SCHEMA,
            "status": "OPEN__NO_ADMISSIBLE_COMPLETE_ROUTE_COVER",
            "selected_routes": [],
            "uncovered_primitives": sorted(residual),
        }

    total_cost, _, route_ids, covered = best
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_MINIMUM_ADMISSIBLE_ROUTE_COVER",
        "selected_routes": list(route_ids),
        "total_cost": total_cost,
        "covered_primitives": sorted(residual & covered),
        "uncovered_primitives": sorted(residual - covered),
    }

def envelope_seal_verdict(
    frozen_primitives: Iterable[str],
    primitive_receipts: Mapping[str, Mapping[str, Any]],
    *,
    decomposition_complete: bool,
    decomposition_lossless: bool,
    independent_verification: bool,
) -> dict[str, Any]:
    primitives = _primitive_set(frozen_primitives)
    missing = []
    invalid = []

    for primitive in sorted(primitives):
        receipt = primitive_receipts.get(primitive)
        if not isinstance(receipt, Mapping):
            missing.append(primitive)
            continue
        owned = receipt.get("verified_owned") is True
        route = receipt.get("route")
        routed = isinstance(route, Mapping) and route_is_admissible(route)
        if not (owned or routed):
            invalid.append(primitive)

    sealed = (
        decomposition_complete
        and decomposition_lossless
        and independent_verification
        and not missing
        and not invalid
    )
    return {
        "schema": SCHEMA,
        "status": "SEALED" if sealed else "OPEN",
        "frozen_envelope_sealed": sealed,
        "primitive_count": len(primitives),
        "missing_receipts": missing,
        "invalid_or_uncovered_primitives": invalid,
        "decomposition_complete": decomposition_complete,
        "decomposition_lossless": decomposition_lossless,
        "independent_verification": independent_verification,
        "root1_positive_gap_count_delta": 0,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
