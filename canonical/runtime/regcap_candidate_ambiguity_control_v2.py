"""Reg-cap ambiguity control V2 with authenticated discriminator reuse.

V2 composes the source-backed CCoB/CCyB/TLAC contrastive discriminator
matrix into the existing bounded ambiguity controller. It never invents
acquisition costs: callers must bind non-negative costs for every authenticated
matrix observation before minimax selection can run.

Open-world mapping behavior remains unchanged and fail-closed.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import regcap_candidate_ambiguity_control_v1 as v1
from canonical.runtime import regcap_contrastive_discriminator_matrix_v1 as matrix

SCHEMA = "PROJECT_BRAIN_REGCAP_CANDIDATE_AMBIGUITY_CONTROL_V2"


def _base(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": False,
        "mapped_concept_id": None,
        "semantic_identity_authority": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def plan_with_authenticated_matrix(
    candidate_result: Mapping[str, Any],
    *,
    mapping_scope: Mapping[str, Any],
    observation_cost_units: Mapping[str, float] | None,
    information_owner: str,
    source_scope: Mapping[str, Any] | None = None,
    discovery_delegated: bool = False,
    clarification_key: str = "regulatory_capital_mapping_context",
    repo_root: str | Path | None = None,
    projection_verifier=matrix.verify_projection_pack,
) -> dict[str, Any]:
    """Reuse authenticated matrix outcomes; require caller-bound acquisition costs."""
    if not isinstance(mapping_scope, Mapping):
        return _base("FAIL_CLOSED", reason="MAPPING_SCOPE_REQUIRED")

    # Preserve V1's exact open-world behavior. V2 only adds a bounded reuse path.
    if (
        mapping_scope.get("kind") != v1.BOUND_SCOPE
        or mapping_scope.get("scope_complete") is not True
    ):
        out = v1.plan(
            candidate_result,
            mapping_scope=mapping_scope,
            observations=[],
            observation_set_complete=False,
            information_owner=information_owner,
            source_scope=source_scope,
            discovery_delegated=discovery_delegated,
            clarification_key=clarification_key,
        )
        out = deepcopy(dict(out))
        out["schema"] = SCHEMA
        out["authenticated_matrix_reused"] = False
        return out

    checked, error = v1._validate_candidate_result(candidate_result)
    if error:
        return _base("FAIL_CLOSED", reason=error)
    assert checked is not None

    ids = list(checked["candidate_concept_ids"])
    scope_ids = mapping_scope.get("candidate_ids")
    if not isinstance(scope_ids, list) or sorted(scope_ids) != sorted(ids):
        return _base(
            "FAIL_CLOSED",
            reason="BOUND_RIVAL_SCOPE_DOES_NOT_MATCH_AUTHENTICATED_CANDIDATE_SET",
            candidate_concept_ids=ids,
        )

    authenticated = matrix.verify_matrix(
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if authenticated.get("pass") is not True:
        return _base(
            "FAIL_CLOSED",
            reason="AUTHENTICATED_DISCRIMINATOR_MATRIX_UNAVAILABLE",
            matrix_result=authenticated,
            candidate_concept_ids=ids,
        )

    domain = authenticated.get("candidate_domain")
    if not isinstance(domain, list) or sorted(domain) != sorted(ids):
        return _base(
            "FAIL_CLOSED",
            reason="AUTHENTICATED_MATRIX_DOMAIN_MISMATCH",
            matrix_result=authenticated,
            candidate_concept_ids=ids,
        )

    rows = authenticated.get("observations")
    if not isinstance(rows, list) or not rows:
        return _base(
            "FAIL_CLOSED",
            reason="AUTHENTICATED_MATRIX_OBSERVATIONS_MISSING",
            matrix_result=authenticated,
        )
    observation_ids = [str(row.get("observation_id") or "") for row in rows]
    if any(not x for x in observation_ids) or len(set(observation_ids)) != len(observation_ids):
        return _base("FAIL_CLOSED", reason="AUTHENTICATED_MATRIX_OBSERVATION_IDS_INVALID")

    if not isinstance(observation_cost_units, Mapping):
        return _base(
            "OPEN__AUTHENTICATED_MATRIX_COST_BINDING_REQUIRED",
            action="BIND_ONLY_OBSERVATION_ACQUISITION_COSTS",
            authenticated_matrix_reused=True,
            matrix_sha256=authenticated.get("matrix_sha256"),
            candidate_concept_ids=ids,
            required_observation_cost_ids=observation_ids,
            reason=(
                "SOURCE_AUTHORITY_PROVES_OUTCOME_MAPS_BUT_DOES_NOT_PROVE_CURRENT_"
                "TASK_ACQUISITION_COSTS"
            ),
        )

    costs: dict[str, float] = {}
    missing: list[str] = []
    for oid in observation_ids:
        raw = observation_cost_units.get(oid)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or float(raw) < 0:
            missing.append(oid)
        else:
            costs[oid] = float(raw)
    if missing:
        return _base(
            "OPEN__AUTHENTICATED_MATRIX_COST_BINDING_REQUIRED",
            action="BIND_ONLY_OBSERVATION_ACQUISITION_COSTS",
            authenticated_matrix_reused=True,
            matrix_sha256=authenticated.get("matrix_sha256"),
            candidate_concept_ids=ids,
            required_observation_cost_ids=observation_ids,
            invalid_or_missing_cost_ids=missing,
        )

    observations = []
    for row in rows:
        oid = str(row["observation_id"])
        outcomes = row.get("outcomes")
        if not isinstance(outcomes, Mapping) or set(outcomes) != set(ids):
            return _base(
                "FAIL_CLOSED",
                reason="AUTHENTICATED_MATRIX_OUTCOME_DOMAIN_INVALID:" + oid,
            )
        observations.append(
            {
                "observation_id": oid,
                "outcome_map_complete": True,
                "cost_units": costs[oid],
                "outcomes": deepcopy(dict(outcomes)),
            }
        )

    out = v1.plan(
        candidate_result,
        mapping_scope=mapping_scope,
        observations=observations,
        observation_set_complete=True,
        information_owner=information_owner,
        source_scope=source_scope,
        discovery_delegated=discovery_delegated,
        clarification_key=clarification_key,
    )
    out = deepcopy(dict(out))
    out["schema"] = SCHEMA
    out["authenticated_matrix_reused"] = True
    out["matrix_sha256"] = authenticated.get("matrix_sha256")
    out["matrix_source_authority"] = authenticated.get("source_authority") is True
    out["matrix_semantic_truth_authority"] = (
        authenticated.get("semantic_truth_authority") is True
    )
    out["observation_cost_authority"] = "CALLER_BOUND_TASK_LOCAL_ONLY"
    out["candidate_universe_complete"] = False
    out["open_world_ontology_complete"] = False
    out["terminal_authority"] = False
    out["terminal_credit_delta"] = 0
    return out
