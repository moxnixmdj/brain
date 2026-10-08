"""Option-preserving capability optimizer V1.

Separates *active selection* from *destruction authority*.

A capability may be dominated for today's cost model and therefore leave the hot
Pareto frontier without losing its semantic contract, evidence, reconstruction
recipe, representation family, substrate family, or future option value.

Permanent deletion is never inferred from current-cost dominance. It is authorized
only by a separate independently verified redundancy/reconstructibility proof.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_OPTION_PRESERVING_CAPABILITY_OPTIMIZER_V1"

BENEFITS = ("capability", "generalization", "reliability")
COSTS = ("latency", "compute", "memory", "incremental_spend_usd")
IDENTITY_FIELDS = (
    "capability_id",
    "semantic_contract_sha256",
    "implementation_family",
    "representation_family",
    "substrate_family",
)
DELETE_PROOF_FIELDS = (
    "independent_verified",
    "exact_byte_bound",
    "semantic_contract_superset_proved",
    "behavioral_scope_superset_proved",
    "evidence_not_weaker_proved",
    "unique_representation_absent_proved",
    "unique_substrate_path_absent_proved",
    "future_option_value_zero_proved",
    "reconstructible_from_preserved_artifacts",
    "reconstruction_verified",
)


class OptionPreservationError(ValueError):
    pass


def _s(value: Any) -> str:
    return " ".join(str(value or "").split())


def _f(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise OptionPreservationError(name.upper() + "_INVALID")
    try:
        out = value if isinstance(value, Fraction) else Fraction(str(value))
    except Exception as exc:
        raise OptionPreservationError(name.upper() + "_INVALID") from exc
    if out < 0:
        raise OptionPreservationError(name.upper() + "_NEGATIVE")
    return out


def _require_candidate(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise OptionPreservationError("CANDIDATE_NOT_OBJECT")
    out = dict(raw)
    for field in IDENTITY_FIELDS:
        if not _s(out.get(field)):
            raise OptionPreservationError(field.upper() + "_REQUIRED")
    if out.get("reusable_capability") is not True:
        raise OptionPreservationError("REUSABLE_CAPABILITY_REQUIRED")
    if out.get("independently_verified") is not True:
        raise OptionPreservationError("INDEPENDENT_VERIFICATION_REQUIRED")
    for key in (*BENEFITS, *COSTS):
        _f(out.get(key, 0), key)
    profiles = out.get("cost_profiles", {})
    if profiles is None:
        profiles = {}
    if not isinstance(profiles, Mapping):
        raise OptionPreservationError("COST_PROFILES_NOT_OBJECT")
    for profile_id, profile in profiles.items():
        if not _s(profile_id) or not isinstance(profile, Mapping):
            raise OptionPreservationError("COST_PROFILE_INVALID")
        for key in COSTS:
            _f(profile.get(key, out.get(key, 0)), f"{profile_id}_{key}")
    return out


def _metrics(raw: Mapping[str, Any], *, cost_model_id: str) -> dict[str, Fraction]:
    candidate = _require_candidate(raw)
    profile = candidate.get("cost_profiles", {}).get(cost_model_id, {})
    if not isinstance(profile, Mapping):
        profile = {}
    return {
        **{k: _f(candidate.get(k, 0), k) for k in BENEFITS},
        **{
            k: _f(profile.get(k, candidate.get(k, 0)), k)
            for k in COSTS
        },
    }


def _same_semantic_contract(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    return _s(a.get("semantic_contract_sha256")) == _s(
        b.get("semantic_contract_sha256")
    )


def _dominates_current(
    a: Mapping[str, Any],
    b: Mapping[str, Any],
    *,
    cost_model_id: str,
) -> bool:
    if not _same_semantic_contract(a, b):
        return False
    am = _metrics(a, cost_model_id=cost_model_id)
    bm = _metrics(b, cost_model_id=cost_model_id)
    weak = (
        all(am[k] >= bm[k] for k in BENEFITS)
        and all(am[k] <= bm[k] for k in COSTS)
    )
    strict = (
        any(am[k] > bm[k] for k in BENEFITS)
        or any(am[k] < bm[k] for k in COSTS)
    )
    return weak and strict


def select_active_frontier(
    candidates: Sequence[Mapping[str, Any]],
    *,
    cost_model_id: str = "CURRENT",
) -> dict[str, Any]:
    """Choose today's hot implementations without authorizing knowledge deletion."""
    rows = [_require_candidate(row) for row in candidates]
    ids = [_s(row["capability_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise OptionPreservationError("CAPABILITY_ID_DUPLICATE")

    active: list[dict[str, Any]] = []
    retired: list[dict[str, Any]] = []
    for row in rows:
        dominators = [
            other
            for other in rows
            if _s(other["capability_id"]) != _s(row["capability_id"])
            and _dominates_current(other, row, cost_model_id=cost_model_id)
        ]
        if dominators:
            distinct_option = any(
                _s(row.get(field)) not in {
                    _s(other.get(field)) for other in dominators
                }
                for field in ("implementation_family", "representation_family", "substrate_family")
            )
            retired.append(
                {
                    "capability_id": _s(row["capability_id"]),
                    "semantic_contract_sha256": _s(row["semantic_contract_sha256"]),
                    "dominated_by": sorted(_s(x["capability_id"]) for x in dominators),
                    "active_state": "WARM_RETIRED" if distinct_option else "COLD_RETIRED",
                    "knowledge_preservation_required": True,
                    "physical_deletion_authorized": False,
                    "unique_option_family_preserved": distinct_option,
                }
            )
        else:
            active.append(row)

    active.sort(key=lambda row: _s(row["capability_id"]))
    retired.sort(key=lambda row: row["capability_id"])
    return {
        "schema": SCHEMA,
        "status": "OPTION_PRESERVING_ACTIVE_FRONTIER_SELECTED",
        "cost_model_id": _s(cost_model_id) or "CURRENT",
        "active_capability_ids": [_s(row["capability_id"]) for row in active],
        "retired": retired,
        "active_count": len(active),
        "retired_count": len(retired),
        "semantic_capability_deletion_authority": False,
        "physical_deletion_authority": False,
        "rule": "CURRENT_COST_DOMINANCE_CAN_RETIRE_HOT_EXECUTION_BUT_CANNOT_DELETE_CAPABILITY_KNOWLEDGE",
    }


def evaluate_permanent_deletion(
    incumbent: Mapping[str, Any],
    replacement: Mapping[str, Any],
    deletion_proof: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Fail closed unless permanent destruction is independently proved harmless."""
    old = _require_candidate(incumbent)
    new = _require_candidate(replacement)
    old_id = _s(old["capability_id"])
    new_id = _s(new["capability_id"])

    if old_id == new_id:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__REPLACEMENT_MUST_BE_DISTINCT",
            "pass": False,
            "physical_deletion_authorized": False,
        }
    if not _same_semantic_contract(old, new):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SEMANTIC_CONTRACT_DIFFERS",
            "pass": False,
            "physical_deletion_authorized": False,
        }

    proof = dict(deletion_proof) if isinstance(deletion_proof, Mapping) else {}
    missing = [field for field in DELETE_PROOF_FIELDS if proof.get(field) is not True]
    if proof.get("incumbent_capability_id") != old_id:
        missing.append("incumbent_capability_id")
    if proof.get("replacement_capability_id") != new_id:
        missing.append("replacement_capability_id")
    if proof.get("semantic_contract_sha256") != _s(old["semantic_contract_sha256"]):
        missing.append("semantic_contract_sha256")

    if missing:
        return {
            "schema": SCHEMA,
            "status": "RETIRE_PRESERVE__PERMANENT_DELETION_NOT_PROVED",
            "pass": True,
            "retirement_authorized": True,
            "physical_deletion_authorized": False,
            "missing_deletion_proofs": sorted(set(missing)),
            "preserve": [
                "SEMANTIC_CONTRACT",
                "EVIDENCE",
                "RECONSTRUCTION_RECIPE",
                "REPRESENTATION_FAMILY",
                "SUBSTRATE_FAMILY",
                "RETIREMENT_REASON",
            ],
        }

    return {
        "schema": SCHEMA,
        "status": "PERMANENT_DELETION_ELIGIBLE__SEPARATE_MUTATION_STILL_REQUIRED",
        "pass": True,
        "retirement_authorized": True,
        "physical_deletion_authorized": True,
        "incumbent_capability_id": old_id,
        "replacement_capability_id": new_id,
        "semantic_contract_sha256": _s(old["semantic_contract_sha256"]),
        "mutation_performed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def reextract_on_cost_model_change(
    candidates: Sequence[Mapping[str, Any]],
    *,
    previous_cost_model_id: str,
    new_cost_model_id: str,
) -> dict[str, Any]:
    """Recompute the hot frontier when technology/cost assumptions change."""
    before = select_active_frontier(candidates, cost_model_id=previous_cost_model_id)
    after = select_active_frontier(candidates, cost_model_id=new_cost_model_id)
    before_ids = set(before["active_capability_ids"])
    after_ids = set(after["active_capability_ids"])
    return {
        "schema": SCHEMA,
        "status": "COST_MODEL_REEXTRACTION_COMPLETE",
        "previous_cost_model_id": _s(previous_cost_model_id),
        "new_cost_model_id": _s(new_cost_model_id),
        "previous_active_capability_ids": sorted(before_ids),
        "new_active_capability_ids": sorted(after_ids),
        "reactivated_capability_ids": sorted(after_ids - before_ids),
        "newly_retired_capability_ids": sorted(before_ids - after_ids),
        "physical_deletion_authority": False,
        "rule": "NEW_TECHNOLOGY_REEXTRACTS_IMPLEMENTATIONS_WITHOUT_REWRITING_SEMANTIC_CAPABILITY_CONTRACTS",
    }
