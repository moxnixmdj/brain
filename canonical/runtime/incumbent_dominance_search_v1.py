"""Incumbent dominance search controller V1.

Implements the invariant: never treat the first adequate candidate as optimal.
After every incumbent, derive the region that could materially beat it, search
that region, and stop only with a scope-complete exhaustion/dominance proof or
an explicit sufficiency contract. Open-world uncertainty fails closed.

This controller does not generate reality, prove candidate-family completeness,
or invent objective tradeoff weights. Those are upstream evidence obligations.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_INCUMBENT_DOMINANCE_SEARCH_V1"
BENEFITS = ("capability", "generalization", "reliability")
COSTS = ("latency", "compute", "memory", "incremental_spend_usd")


class SearchControlError(ValueError):
    pass


def _s(v: Any) -> str:
    return " ".join(str(v or "").split())


def _f(v: Any, field: str) -> Fraction:
    if isinstance(v, bool):
        raise SearchControlError(field.upper() + "_INVALID")
    try:
        x = v if isinstance(v, Fraction) else Fraction(str(v))
    except Exception as exc:
        raise SearchControlError(field.upper() + "_INVALID") from exc
    if x < 0:
        raise SearchControlError(field.upper() + "_NEGATIVE")
    return x


def _candidate(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise SearchControlError("CANDIDATE_NOT_OBJECT")
    out = dict(raw)
    if not _s(out.get("candidate_id")):
        raise SearchControlError("CANDIDATE_ID_REQUIRED")
    if out.get("independently_verified") is not True:
        raise SearchControlError("INDEPENDENT_VERIFICATION_REQUIRED")
    if not _s(out.get("semantic_contract_sha256")):
        raise SearchControlError("SEMANTIC_CONTRACT_SHA256_REQUIRED")
    for k in (*BENEFITS, *COSTS):
        _f(out.get(k, 0), k)
    return out


def _metrics(raw: Mapping[str, Any]) -> dict[str, Fraction]:
    c = _candidate(raw)
    return {k: _f(c.get(k, 0), k) for k in (*BENEFITS, *COSTS)}


def pareto_dominates(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """True only for same-contract, dimension-wise current dominance."""
    aa, bb = _candidate(a), _candidate(b)
    if _s(aa["semantic_contract_sha256"]) != _s(bb["semantic_contract_sha256"]):
        return False
    am, bm = _metrics(aa), _metrics(bb)
    weak = all(am[k] >= bm[k] for k in BENEFITS) and all(am[k] <= bm[k] for k in COSTS)
    strict = any(am[k] > bm[k] for k in BENEFITS) or any(am[k] < bm[k] for k in COSTS)
    return weak and strict


def derive_better_than_region(incumbent: Mapping[str, Any]) -> dict[str, Any]:
    """Describe what any Pareto dominator must accomplish."""
    c = _candidate(incumbent)
    m = _metrics(c)
    return {
        "incumbent_candidate_id": _s(c["candidate_id"]),
        "semantic_contract_sha256": _s(c["semantic_contract_sha256"]),
        "must_preserve_contract": True,
        "weak_requirements": {
            **{k: {"op": ">=", "value": str(m[k])} for k in BENEFITS},
            **{k: {"op": "<=", "value": str(m[k])} for k in COSTS},
        },
        "strict_improvement_required_on_at_least_one_dimension": list(BENEFITS + COSTS),
    }


def _region(row: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise SearchControlError("REGION_NOT_OBJECT")
    x = dict(row)
    if not _s(x.get("region_id")):
        raise SearchControlError("REGION_ID_REQUIRED")
    status = _s(x.get("status"))
    allowed = {"EXHAUSTED", "UPPER_BOUND_ELIMINATED", "OPEN", "DOMINATOR_FOUND"}
    if status not in allowed:
        raise SearchControlError("REGION_STATUS_INVALID")
    if status == "UPPER_BOUND_ELIMINATED" and x.get("independent_bound_proof") is not True:
        raise SearchControlError("UPPER_BOUND_PROOF_REQUIRED")
    if status == "DOMINATOR_FOUND" and not _s(x.get("candidate_id")):
        raise SearchControlError("DOMINATOR_CANDIDATE_ID_REQUIRED")
    return x


def evaluate(
    *,
    incumbent: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]] = (),
    candidate_regions: Sequence[Mapping[str, Any]] = (),
    candidate_family_cover_complete: bool = False,
    family_cover_independently_verified: bool = False,
    explicit_sufficiency_contract: Mapping[str, Any] | None = None,
    optimality_required: bool = True,
) -> dict[str, Any]:
    """Challenge an incumbent and return the only sound next state.

    Optimality is authorized only when candidate-family coverage is independently
    verified complete and every better-than region is exhausted or eliminated by
    an independent upper bound. Otherwise the controller remains open.
    """
    inc = _candidate(incumbent)
    rows = [_candidate(x) for x in candidates]
    if len({_s(x["candidate_id"]) for x in rows}) != len(rows):
        raise SearchControlError("CANDIDATE_ID_DUPLICATE")

    dominators = [x for x in rows if pareto_dominates(x, inc)]
    if dominators:
        dominators.sort(key=lambda x: _s(x["candidate_id"]))
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "REPLACE_INCUMBENT_AND_REPEAT",
            "incumbent_candidate_id": _s(inc["candidate_id"]),
            "dominating_candidate_ids": [_s(x["candidate_id"]) for x in dominators],
            "next_incumbent_candidate_id": _s(dominators[0]["candidate_id"]),
            "better_than_region": derive_better_than_region(inc),
            "optimality_proved": False,
            "must_repeat_search_after_replacement": True,
            "terminal_authority": False,
        }

    regions = [_region(x) for x in candidate_regions]
    explicit = [x for x in regions if x["status"] == "DOMINATOR_FOUND"]
    if explicit:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "DOMINATOR_REPORTED__VERIFY_AND_REPEAT",
            "incumbent_candidate_id": _s(inc["candidate_id"]),
            "reported_dominator_candidate_ids": sorted(_s(x["candidate_id"]) for x in explicit),
            "better_than_region": derive_better_than_region(inc),
            "optimality_proved": False,
            "must_repeat_search_after_replacement": True,
            "terminal_authority": False,
        }

    if not optimality_required:
        contract = dict(explicit_sufficiency_contract or {})
        if contract.get("independently_verified") is True and contract.get("incumbent_satisfies") is True:
            return {
                "schema": SCHEMA,
                "pass": True,
                "status": "SUFFICIENT__OPTIMALITY_NOT_REQUIRED",
                "incumbent_candidate_id": _s(inc["candidate_id"]),
                "optimality_proved": False,
                "sufficiency_proved": True,
                "search_may_stop": True,
                "terminal_authority": False,
            }

    unresolved = [x for x in regions if x["status"] == "OPEN"]
    eliminated = [x for x in regions if x["status"] in {"EXHAUSTED", "UPPER_BOUND_ELIMINATED"}]
    cover_ok = candidate_family_cover_complete is True and family_cover_independently_verified is True
    if cover_ok and not unresolved and len(eliminated) == len(regions) and regions:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "OPTIMALITY_PROVED__NO_BETTER_REGION_REMAINS",
            "incumbent_candidate_id": _s(inc["candidate_id"]),
            "better_than_region": derive_better_than_region(inc),
            "candidate_family_cover_complete": True,
            "all_better_regions_eliminated": True,
            "optimality_proved": True,
            "search_may_stop": True,
            "terminal_authority": False,
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "OPEN__MATERIALLY_BETTER_CANDIDATE_NOT_EXCLUDED",
        "incumbent_candidate_id": _s(inc["candidate_id"]),
        "better_than_region": derive_better_than_region(inc),
        "candidate_family_cover_complete": cover_ok,
        "unresolved_region_ids": sorted(_s(x["region_id"]) for x in unresolved),
        "family_coverage_challenge_required": not cover_ok,
        "next_required_actions": [
            "SEARCH_ONLY_REGIONS_CAPABLE_OF_DOMINATING_INCUMBENT",
            "CHALLENGE_CANDIDATE_FAMILY_COVER_FOR_MISSING_SOLUTION_CLASSES",
            "PRESERVE_INCUMBENT_AND_NONDOMINATED_ALTERNATIVES",
            "REPEAT_AFTER_EACH_NEW_DOMINATOR_OR_SCOPE_REFINEMENT",
        ],
        "optimality_proved": False,
        "search_may_stop": False,
        "terminal_authority": False,
    }
