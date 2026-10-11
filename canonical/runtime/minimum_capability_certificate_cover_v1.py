"""Minimum capability-certificate cover for benchmark-as-measurement scheduling.

This module does not execute benchmarks and does not grant benchmark, capability,
acceptance, ownership, or terminal credit. It compiles benchmark-derived claims
into explicit propositions and selects the cheapest exact certificate cover from
already-admissible evidence candidates.

Crucial invariant: a general capability proposition and a literal named-benchmark
score predicate are distinct. No implication exists between them unless supplied
explicitly as a sound implication edge.
"""
from __future__ import annotations

import itertools
import math
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_MINIMUM_CAPABILITY_CERTIFICATE_COVER_V1"
_ALLOWED_CLAIM_KINDS = {"CAPABILITY_COMPARISON", "LITERAL_BENCHMARK_SCORE"}
_EPS = 1e-12


class CertificateCoverError(ValueError):
    pass


def _nonempty_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CertificateCoverError(f"{name.upper()}_REQUIRED")
    return value.strip()


def _string_set(values: Any, name: str, *, allow_empty: bool = False) -> set[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise CertificateCoverError(f"{name.upper()}_MUST_BE_SEQUENCE")
    out = {_nonempty_str(v, name) for v in values}
    if not out and not allow_empty:
        raise CertificateCoverError(f"{name.upper()}_REQUIRED")
    return out


def compile_benchmark_claim(claim: Mapping[str, Any]) -> dict[str, Any]:
    """Compile one benchmark-derived claim into explicit proof obligations.

    CAPABILITY_COMPARISON requires one or more capability propositions.
    LITERAL_BENCHMARK_SCORE additionally requires an exact literal score
    predicate. Capability propositions are retained for audit/context but do
    not satisfy the literal predicate by themselves.
    """
    if not isinstance(claim, Mapping):
        raise CertificateCoverError("CLAIM_MUST_BE_MAPPING")
    claim_id = _nonempty_str(claim.get("id"), "claim_id")
    kind = _nonempty_str(claim.get("claim_kind"), "claim_kind")
    if kind not in _ALLOWED_CLAIM_KINDS:
        raise CertificateCoverError("CLAIM_KIND_INVALID")
    if claim.get("benchmark_is_parent_objective") is True:
        raise CertificateCoverError("BENCHMARK_PARENT_OBJECTIVE_FORBIDDEN")

    capability = _string_set(
        claim.get("capability_propositions", []),
        "capability_propositions",
        allow_empty=(kind == "LITERAL_BENCHMARK_SCORE"),
    )
    literal = claim.get("literal_score_predicate")
    if literal is not None:
        literal = _nonempty_str(literal, "literal_score_predicate")

    if kind == "CAPABILITY_COMPARISON":
        if not capability:
            raise CertificateCoverError("CAPABILITY_PROPOSITIONS_REQUIRED")
        required = set(capability)
    else:
        if literal is None:
            raise CertificateCoverError("LITERAL_SCORE_PREDICATE_REQUIRED")
        required = {literal}

    return {
        "schema": SCHEMA,
        "claim_id": claim_id,
        "claim_kind": kind,
        "benchmark": claim.get("benchmark"),
        "capability_propositions": sorted(capability),
        "literal_score_predicate": literal,
        "required_propositions": sorted(required),
        "benchmark_is_parent_objective": False,
        "score_delta_is_development_credit": False,
        "reverse_inference_from_capability_to_literal_score": False,
    }


def implication_closure(
    seed: Iterable[str],
    implication_edges: Mapping[str, Sequence[str]] | None = None,
) -> set[str]:
    """Return transitive closure under explicit implication edges only."""
    reached = {_nonempty_str(x, "seed_proposition") for x in seed}
    edges = implication_edges or {}
    if not isinstance(edges, Mapping):
        raise CertificateCoverError("IMPLICATION_EDGES_MUST_BE_MAPPING")
    normalized: dict[str, set[str]] = {}
    for src, dsts in edges.items():
        s = _nonempty_str(src, "implication_source")
        normalized[s] = _string_set(
            dsts, "implication_targets", allow_empty=True
        )

    frontier = list(reached)
    while frontier:
        src = frontier.pop()
        for dst in normalized.get(src, ()):
            if dst not in reached:
                reached.add(dst)
                frontier.append(dst)
    return reached


def _finite_nonnegative(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise CertificateCoverError(f"{name.upper()}_INVALID")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise CertificateCoverError(f"{name.upper()}_INVALID") from exc
    if not math.isfinite(x) or x < 0:
        raise CertificateCoverError(f"{name.upper()}_INVALID")
    return x


def _admissible_certificate(
    raw: Mapping[str, Any],
    *,
    require_donor_free: bool,
    max_incremental_spend_usd: float,
) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        raise CertificateCoverError("CERTIFICATE_MUST_BE_MAPPING")
    cid = _nonempty_str(raw.get("id"), "certificate_id")
    proves = _string_set(raw.get("proves", []), "certificate_proves")
    valid = raw.get("valid") is True
    scope_bound = raw.get("scope_bound") is True
    donor_free = raw.get("donor_free") is True
    spend = _finite_nonnegative(raw.get("incremental_spend_usd", 0), "incremental_spend_usd")
    if not valid or not scope_bound:
        return None
    if require_donor_free and not donor_free:
        return None
    if spend > max_incremental_spend_usd + _EPS:
        return None

    wall = _finite_nonnegative(raw.get("wall_clock_cost", 0), "wall_clock_cost")
    compute = _finite_nonnegative(raw.get("compute_cost", 0), "compute_cost")
    risk = _finite_nonnegative(raw.get("evidence_risk", 0), "evidence_risk")
    complexity = _finite_nonnegative(raw.get("complexity_cost", 0), "complexity_cost")
    return {
        "id": cid,
        "proves": proves,
        "wall_clock_cost": wall,
        "compute_cost": compute,
        "evidence_risk": risk,
        "complexity_cost": complexity,
        "incremental_spend_usd": spend,
        "cost_vector": (spend, wall, compute, risk, complexity),
    }


def _aggregate_cost(certs: Sequence[Mapping[str, Any]]) -> tuple[float, ...]:
    if not certs:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0)
    sums = [
        sum(float(c["cost_vector"][i]) for c in certs)
        for i in range(5)
    ]
    return (*sums, len(certs))


def select_minimum_certificate_cover(
    obligations: Sequence[Mapping[str, Any]],
    certificates: Sequence[Mapping[str, Any]],
    *,
    implication_edges: Mapping[str, Sequence[str]] | None = None,
    already_proved: Sequence[str] = (),
    require_donor_free: bool = True,
    max_incremental_spend_usd: float = 0.0,
    exact_certificate_limit: int = 20,
) -> dict[str, Any]:
    """Select the exact lexicographically cheapest sufficient certificate cover.

    Cost order is incremental spend, wall-clock, compute, evidence risk,
    complexity, then certificate count. Candidate sets above the exact limit
    fail closed instead of pretending a greedy result is globally optimal.
    """
    if not isinstance(obligations, Sequence) or isinstance(obligations, (str, bytes)):
        raise CertificateCoverError("OBLIGATIONS_MUST_BE_SEQUENCE")
    if not isinstance(certificates, Sequence) or isinstance(certificates, (str, bytes)):
        raise CertificateCoverError("CERTIFICATES_MUST_BE_SEQUENCE")
    max_spend = _finite_nonnegative(max_incremental_spend_usd, "max_incremental_spend_usd")

    required_by_obligation: dict[str, set[str]] = {}
    for raw in obligations:
        if not isinstance(raw, Mapping):
            raise CertificateCoverError("OBLIGATION_MUST_BE_MAPPING")
        oid = _nonempty_str(raw.get("id"), "obligation_id")
        if oid in required_by_obligation:
            raise CertificateCoverError("DUPLICATE_OBLIGATION_ID:" + oid)
        required_by_obligation[oid] = _string_set(
            raw.get("required_propositions", []), "required_propositions"
        )

    required = set().union(*required_by_obligation.values()) if required_by_obligation else set()
    base = implication_closure(already_proved, implication_edges)
    unresolved_initial = required - base
    if not unresolved_initial:
        return {
            "schema": SCHEMA,
            "status": "COMPLETE_ZERO_NEW_CERTIFICATES",
            "selected_certificate_ids": [],
            "required_propositions": sorted(required),
            "proved_propositions": sorted(base),
            "unresolved_propositions": [],
            "covered_obligation_ids": sorted(required_by_obligation),
            "unresolved_obligation_ids": [],
            "aggregate_cost": {
                "incremental_spend_usd": 0.0,
                "wall_clock_cost": 0.0,
                "compute_cost": 0.0,
                "evidence_risk": 0.0,
                "complexity_cost": 0.0,
                "certificate_count": 0,
            },
            "credit_delta": 0,
        }

    admissible = []
    for raw in certificates:
        cert = _admissible_certificate(
            raw,
            require_donor_free=require_donor_free,
            max_incremental_spend_usd=max_spend,
        )
        if cert is not None:
            admissible.append(cert)

    if len(admissible) > exact_certificate_limit:
        raise CertificateCoverError("EXACT_CERTIFICATE_LIMIT_EXCEEDED")

    best = None
    n = len(admissible)
    for mask in range(1 << n):
        selected = [admissible[i] for i in range(n) if mask & (1 << i)]
        seeds = set(base)
        for cert in selected:
            seeds.update(cert["proves"])
        proved = implication_closure(seeds, implication_edges)
        unresolved = required - proved
        key = (len(unresolved), _aggregate_cost(selected), tuple(sorted(c["id"] for c in selected)))
        if best is None or key < best[0]:
            best = (key, selected, proved, unresolved)

    assert best is not None
    _, selected, proved, unresolved = best
    covered_obligations = []
    unresolved_obligations = []
    for oid, props in required_by_obligation.items():
        (covered_obligations if props <= proved else unresolved_obligations).append(oid)

    cost = _aggregate_cost(selected)
    return {
        "schema": SCHEMA,
        "status": "COMPLETE_MINIMUM_COVER" if not unresolved else "INCOMPLETE_NO_SUFFICIENT_COVER",
        "selected_certificate_ids": sorted(c["id"] for c in selected),
        "required_propositions": sorted(required),
        "proved_propositions": sorted(proved),
        "unresolved_propositions": sorted(unresolved),
        "covered_obligation_ids": sorted(covered_obligations),
        "unresolved_obligation_ids": sorted(unresolved_obligations),
        "aggregate_cost": {
            "incremental_spend_usd": cost[0],
            "wall_clock_cost": cost[1],
            "compute_cost": cost[2],
            "evidence_risk": cost[3],
            "complexity_cost": cost[4],
            "certificate_count": cost[5],
        },
        "credit_delta": 0,
    }
