from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_CAPABILITY_COMPARISON_SCHEDULER_V1"
PROGRAM = "canonical/governance/CAPABILITY_COMPARISON_PROGRAM_V1.json"
REGISTRY = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
QUOTIENT = "canonical/governance/FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json"


class CapabilityComparisonError(ValueError):
    pass


def _load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text())


def _d(value: Any, field: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise CapabilityComparisonError(field + "_REQUIRED")
    try:
        out = Decimal(str(value))
    except Exception as exc:
        raise CapabilityComparisonError(field + "_INVALID") from exc
    if out < 0:
        raise CapabilityComparisonError(field + "_NEGATIVE")
    return out


def compile_program(
    program: Mapping[str, Any],
    registry: Mapping[str, Any],
    quotient: Mapping[str, Any],
) -> dict[str, Any]:
    audits = list(program.get("audit_obligations") or [])
    if len(audits) != 13:
        raise CapabilityComparisonError("AUDIT_OBLIGATION_COUNT_MUST_BE_13")

    independent = set(quotient.get("independent_open_obligations") or [])
    registry_rows = {
        str(row.get("id")): row for row in (registry.get("predicates") or [])
        if row.get("id")
    }

    audit_ids: set[str] = set()
    quotient_ids: set[str] = set()
    family_to_audits: dict[str, set[str]] = {}
    predicate_to_audit: dict[str, str] = {}

    for row in audits:
        audit_id = str(row.get("audit_id") or "").strip()
        qid = str(row.get("quotient_obligation_id") or "").strip()
        pids = [str(x) for x in (row.get("predicate_ids") or [])]
        families = [str(x) for x in (row.get("capability_families") or [])]
        if not audit_id or audit_id in audit_ids:
            raise CapabilityComparisonError("AUDIT_ID_INVALID_OR_DUPLICATE")
        if not qid or qid in quotient_ids:
            raise CapabilityComparisonError("QUOTIENT_ID_INVALID_OR_DUPLICATE")
        if qid not in independent:
            raise CapabilityComparisonError("QUOTIENT_OBLIGATION_NOT_CURRENT:" + qid)
        if not pids or not families:
            raise CapabilityComparisonError("PREDICATE_AND_FAMILY_BINDING_REQUIRED:" + audit_id)

        expected_families = set()
        for pid in pids:
            source = registry_rows.get(pid)
            if source is None:
                raise CapabilityComparisonError("REGISTRY_PREDICATE_MISSING:" + pid)
            family = str(source.get("family") or "")
            if not family:
                raise CapabilityComparisonError("REGISTRY_FAMILY_MISSING:" + pid)
            expected_families.add(family)
            prior = predicate_to_audit.get(pid)
            if prior and prior != audit_id:
                raise CapabilityComparisonError("PREDICATE_BOUND_TO_MULTIPLE_AUDITS:" + pid)
            predicate_to_audit[pid] = audit_id

        if set(families) != expected_families:
            raise CapabilityComparisonError("FAMILY_BINDING_MISMATCH:" + audit_id)

        audit_ids.add(audit_id)
        quotient_ids.add(qid)
        for family in families:
            family_to_audits.setdefault(family, set()).add(audit_id)

    if quotient_ids != independent:
        missing = sorted(independent - quotient_ids)
        extra = sorted(quotient_ids - independent)
        raise CapabilityComparisonError(
            "QUOTIENT_COVER_NOT_EXACT:missing=" + ",".join(missing)
            + ";extra=" + ",".join(extra)
        )

    clusters = [
        {
            "capability_family": family,
            "audit_ids": sorted(ids),
            "audit_count": len(ids),
            "dominance_opportunity": len(ids) > 1,
        }
        for family, ids in family_to_audits.items()
    ]
    clusters.sort(key=lambda x: (-x["audit_count"], x["capability_family"]))

    return {
        "schema": SCHEMA,
        "status": "PASS__13_AUDITS_DEDUPLICATED_INTO_CAPABILITY_PROPOSITIONS",
        "audit_obligation_count": len(audits),
        "capability_family_count": len(family_to_audits),
        "capability_clusters": clusters,
        "highest_raw_dominance_count": max(x["audit_count"] for x in clusters),
        "benchmark_score_is_parent_objective": False,
        "automatic_score_to_capability_transfer": False,
        "automatic_capability_to_score_transfer": False,
        "capability_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


@dataclass(frozen=True)
class Witness:
    witness_id: str
    closes_capability_families: frozenset[str]
    entails_audit_ids: frozenset[str]
    wall_clock_units: Decimal
    external_dependency_units: Decimal
    compute_units: Decimal
    incremental_spend_usd: Decimal
    evidence_risk_units: Decimal


def _witness(raw: Mapping[str, Any]) -> Witness:
    wid = str(raw.get("witness_id") or "").strip()
    if not wid:
        raise CapabilityComparisonError("WITNESS_ID_REQUIRED")
    if raw.get("independently_verified") is not True:
        raise CapabilityComparisonError("INDEPENDENT_VERIFICATION_REQUIRED:" + wid)
    if raw.get("scope_complete") is not True:
        raise CapabilityComparisonError("SCOPE_COMPLETE_REQUIRED:" + wid)
    if raw.get("brain_owned") is not True:
        raise CapabilityComparisonError("BRAIN_OWNERSHIP_REQUIRED:" + wid)
    if int(raw.get("external_general_purpose_runtime_cognition", -1)) != 0:
        raise CapabilityComparisonError("EXTERNAL_RUNTIME_COGNITION_MUST_BE_ZERO:" + wid)

    caps = frozenset(str(x) for x in (raw.get("closes_capability_families") or []))
    audits = frozenset(str(x) for x in (raw.get("explicitly_entails_audit_ids") or []))
    if not caps and not audits:
        raise CapabilityComparisonError("WITNESS_HAS_NO_COVERAGE:" + wid)

    return Witness(
        witness_id=wid,
        closes_capability_families=caps,
        entails_audit_ids=audits,
        wall_clock_units=_d(raw.get("wall_clock_units"), wid + "_WALL_CLOCK"),
        external_dependency_units=_d(raw.get("external_dependency_units"), wid + "_EXTERNAL_DEPENDENCY"),
        compute_units=_d(raw.get("compute_units"), wid + "_COMPUTE"),
        incremental_spend_usd=_d(raw.get("incremental_spend_usd"), wid + "_SPEND"),
        evidence_risk_units=_d(raw.get("evidence_risk_units"), wid + "_EVIDENCE_RISK"),
    )


def select_exact_portfolio(
    candidates: Sequence[Mapping[str, Any]],
    *,
    required_capability_families: Iterable[str],
    required_audit_ids: Iterable[str] = (),
) -> dict[str, Any]:
    rows = [_witness(x) for x in candidates]
    if len({x.witness_id for x in rows}) != len(rows):
        raise CapabilityComparisonError("WITNESS_ID_DUPLICATE")
    if len(rows) > 22:
        raise CapabilityComparisonError("EXACT_SOLVER_MAX_22_CANDIDATES")

    required_caps = frozenset(str(x) for x in required_capability_families)
    required_audits = frozenset(str(x) for x in required_audit_ids)
    best: tuple[Any, ...] | None = None
    best_rows: tuple[Witness, ...] = ()

    for n in range(len(rows) + 1):
        for subset in itertools.combinations(rows, n):
            caps = frozenset().union(*(x.closes_capability_families for x in subset))
            audits = frozenset().union(*(x.entails_audit_ids for x in subset))
            missing_caps = required_caps - caps
            missing_audits = required_audits - audits
            objective = (
                len(missing_caps) + len(missing_audits),
                sum((x.wall_clock_units for x in subset), Decimal(0)),
                sum((x.external_dependency_units for x in subset), Decimal(0)),
                sum((x.evidence_risk_units for x in subset), Decimal(0)),
                sum((x.compute_units for x in subset), Decimal(0)),
                sum((x.incremental_spend_usd for x in subset), Decimal(0)),
                len(subset),
                tuple(sorted(x.witness_id for x in subset)),
            )
            if best is None or objective < best:
                best = objective
                best_rows = subset

    assert best is not None
    selected_caps = frozenset().union(*(x.closes_capability_families for x in best_rows))
    selected_audits = frozenset().union(*(x.entails_audit_ids for x in best_rows))
    missing_caps = sorted(required_caps - selected_caps)
    missing_audits = sorted(required_audits - selected_audits)

    return {
        "schema": SCHEMA,
        "status": "EXACT_PORTFOLIO_SELECTED" if not missing_caps and not missing_audits else "PARTIAL_PORTFOLIO__MISSING_COVERAGE",
        "selected_witness_ids": sorted(x.witness_id for x in best_rows),
        "missing_capability_families": missing_caps,
        "missing_audit_ids": missing_audits,
        "forced_complete": not missing_caps and not missing_audits,
        "objective": {
            "wall_clock_units": str(best[1]),
            "external_dependency_units": str(best[2]),
            "evidence_risk_units": str(best[3]),
            "compute_units": str(best[4]),
            "incremental_spend_usd": str(best[5]),
            "witness_count": best[6],
        },
        "rule": "MINIMIZE_UNCOVERED_FIRST__THEN_WALL_CLOCK__EXTERNAL_DEPENDENCY__EVIDENCE_RISK__COMPUTE__SPEND__COUNT",
        "terminal_credit_delta": 0,
    }


def evaluate_current() -> dict[str, Any]:
    return compile_program(_load(PROGRAM), _load(REGISTRY), _load(QUOTIENT))


if __name__ == "__main__":
    print(json.dumps(evaluate_current(), indent=2, sort_keys=True))
