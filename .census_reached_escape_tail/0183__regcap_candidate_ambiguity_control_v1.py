"""Bounded regulatory-capital candidate ambiguity control.

Composes already-verified candidate discovery with the generic semantic ambiguity
controller and minimum-information origin router. It never reverse-infers concept
identity from necessary properties and never treats the three named rivals as an
open-world complete ontology.

For an explicitly bounded rival-set task, it can compute the minimum declared
policy-changing observation. For open-world mapping, it returns a structured
minimum-information acquisition request instead of guessing.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime import minimum_information_origin_policy_v1 as origin
from canonical.runtime import semantic_ambiguity_control_v1 as ambiguity
from canonical.runtime import regcap_property_candidate_discovery_v1 as discovery

SCHEMA = "PROJECT_BRAIN_REGCAP_CANDIDATE_AMBIGUITY_CONTROL_V1"
BOUND_SCOPE = "BOUND_REGCAP_RIVAL_SET"


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
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


def _validate_candidate_result(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, Mapping):
        return None, "CANDIDATE_RESULT_REQUIRED"
    row = deepcopy(dict(value))
    if row.get("schema") != discovery.SCHEMA:
        return None, "CANDIDATE_RESULT_SCHEMA_INVALID"
    if row.get("status") == "FAIL_CLOSED":
        return None, "CANDIDATE_DISCOVERY_FAILED"
    if row.get("candidate_generation_authority") is not True:
        return None, "CANDIDATE_GENERATION_AUTHORITY_REQUIRED"
    ids = row.get("candidate_concept_ids")
    if (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(x, str) or not x for x in ids)
        or len(set(ids)) != len(ids)
    ):
        return None, "CANDIDATE_IDS_INVALID"
    return row, None


GROUNDING_SCHEMA = "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V1"


def plan_from_grounding(
    grounding_result: Mapping[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """Route one verified grounding result into candidate ambiguity control."""
    if not isinstance(grounding_result, Mapping):
        return _base("FAIL_CLOSED", reason="GROUNDING_RESULT_REQUIRED")
    if grounding_result.get("schema") != GROUNDING_SCHEMA:
        return _base("FAIL_CLOSED", reason="GROUNDING_RESULT_SCHEMA_INVALID")
    if grounding_result.get("source_constraint_proved") is not True:
        return _base("FAIL_CLOSED", reason="GROUNDING_SOURCE_CONSTRAINT_NOT_PROVED")
    candidate_result = grounding_result.get("candidate_discovery")
    if not isinstance(candidate_result, Mapping):
        return _base("FAIL_CLOSED", reason="GROUNDING_CANDIDATE_DISCOVERY_MISSING")
    out = plan(candidate_result, **kwargs)
    out["grounding_source_id"] = grounding_result.get("source_id")
    out["grounding_source_span"] = deepcopy(grounding_result.get("source_span"))
    out["grounding_raw_span"] = grounding_result.get("raw_span")
    return out


def plan(
    candidate_result: Mapping[str, Any],
    *,
    mapping_scope: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]] = (),
    observation_set_complete: bool,
    information_owner: str,
    source_scope: Mapping[str, Any] | None = None,
    discovery_delegated: bool = False,
    clarification_key: str = "regulatory_capital_mapping_context",
) -> dict[str, Any]:
    row, error = _validate_candidate_result(candidate_result)
    if error:
        return _base("FAIL_CLOSED", reason=error)
    assert row is not None

    ids = list(row["candidate_concept_ids"])
    hints = {
        str(k): list(v)
        for k, v in (row.get("next_positive_evidence_targets_by_candidate") or {}).items()
        if isinstance(k, str) and isinstance(v, list)
    }
    if not hints:
        hints = {
            str(x.get("concept_id")): list(x.get("positive_evidence_targets") or [])
            for x in (row.get("candidates") or [])
            if isinstance(x, Mapping) and x.get("concept_id")
        }

    if not isinstance(mapping_scope, Mapping):
        return _base("FAIL_CLOSED", reason="MAPPING_SCOPE_REQUIRED")
    scope_kind = mapping_scope.get("kind")
    scope_ids = mapping_scope.get("candidate_ids")
    scope_complete = mapping_scope.get("scope_complete")

    # Candidate discovery is explicitly not open-world complete. Without an
    # authenticated bounded rival task, do not manufacture a complete hypothesis set.
    if scope_kind != BOUND_SCOPE or scope_complete is not True:
        route = origin.route({
            "decision_relevant": True,
            "context_value_bound": False,
            "information_owner": information_owner,
            "source_scope": deepcopy(source_scope) if source_scope is not None else None,
            "discovery_delegated": discovery_delegated,
            "clarification_key": clarification_key,
        })
        return _base(
            "OPEN__OPEN_WORLD_MAPPING_REQUIRES_MINIMUM_ADDITIONAL_INFORMATION",
            action=route.get("action"),
            minimum_information_route=route,
            candidate_concept_ids=ids,
            candidate_set_complete_relative_to_bound_rivals=bool(
                row.get("candidate_set_complete_relative_to_bound_rivals")
            ),
            open_world_candidate_set_complete=False,
            search_hints_by_candidate=hints,
            reason=(
                "PROPERTY_MATCHING_DOES_NOT_PROVE_CONCEPT_IDENTITY_AND_THE_BOUND_"
                "RIVAL_SET_IS_NOT_AN_OPEN_WORLD_COMPLETE_ONTOLOGY"
            ),
        )

    if (
        not isinstance(scope_ids, list)
        or sorted(scope_ids) != sorted(ids)
        or row.get("candidate_set_complete_relative_to_bound_rivals") is not True
    ):
        return _base(
            "FAIL_CLOSED",
            reason="BOUND_RIVAL_SCOPE_DOES_NOT_MATCH_AUTHENTICATED_CANDIDATE_SET",
            candidate_concept_ids=ids,
        )
    if observation_set_complete is not True:
        return _base(
            "OPEN__OBSERVATION_MODEL_COMPLETENESS_REQUIRED",
            candidate_concept_ids=ids,
            search_hints_by_candidate=hints,
            reason="MINIMAX_DISCRIMINATOR_REQUIRES_DECLARED_COMPLETE_OBSERVATION_MODEL",
        )
    if not isinstance(observations, Sequence) or isinstance(
        observations, (str, bytes, bytearray)
    ):
        return _base("FAIL_CLOSED", reason="OBSERVATIONS_SEQUENCE_REQUIRED")

    worlds = [
        {
            "world_id": cid,
            "terminal_signature_complete": True,
            "terminal_signature": {"mapped_concept_id": cid},
        }
        for cid in ids
    ]
    control = ambiguity.decide({
        "ambiguity_owner": information_owner,
        "hypothesis_set_complete": True,
        "worlds": worlds,
        "observations": [deepcopy(dict(x)) for x in observations],
    })

    if control.get("status") == "OPEN__MINIMUM_TERMINAL_DISCRIMINATOR_REQUIRED":
        return _base(
            "OPEN__MINIMUM_POLICY_CHANGING_DISCRIMINATOR_READY",
            action="ACQUIRE_MINIMUM_TERMINALLY_RELEVANT_DISCRIMINATOR",
            next_observation_id=control.get("next_observation_id"),
            minimum_worst_case_cost_units=control.get(
                "minimum_worst_case_cost_units"
            ),
            candidate_concept_ids=ids,
            ambiguity_control=control,
            search_hints_by_candidate=hints,
        )

    if control.get("status") == (
        "OPEN__MINIMUM_USER_CLARIFICATION_REQUIRED__SEMANTIC_UNDERDETERMINATION"
    ):
        route = origin.route({
            "decision_relevant": True,
            "context_value_bound": False,
            "information_owner": origin.USER_SPECIFICATION,
            "source_scope": deepcopy(source_scope) if source_scope is not None else None,
            "discovery_delegated": False,
            "clarification_key": clarification_key,
        })
        return _base(
            "OPEN__MINIMUM_USER_CONTEXT_REQUIRED",
            action=route.get("action"),
            candidate_concept_ids=ids,
            ambiguity_control=control,
            minimum_information_route=route,
            search_hints_by_candidate=hints,
        )

    if control.get("status") == (
        "OPEN__DECISIVE_INFORMATION_UNOBSERVABLE_WITHIN_DECLARED_MODEL"
    ):
        route = origin.route({
            "decision_relevant": True,
            "context_value_bound": False,
            "information_owner": information_owner,
            "source_scope": deepcopy(source_scope) if source_scope is not None else None,
            "discovery_delegated": discovery_delegated,
            "clarification_key": clarification_key,
        })
        return _base(
            "OPEN__STRONGER_AUTHENTIC_INFORMATION_REQUIRED",
            action=route.get("action"),
            candidate_concept_ids=ids,
            ambiguity_control=control,
            minimum_information_route=route,
            search_hints_by_candidate=hints,
        )

    if control.get("pass") is True and control.get("terminally_equivalent") is True:
        return _base(
            "PASS__CONCEPT_IDENTITY_IRRELEVANT_TO_CURRENT_TERMINAL_ACTION",
            passed=True,
            action="CONTINUE_WITHOUT_CONCEPT_IDENTITY",
            candidate_concept_ids=ids,
            ambiguity_control=control,
        )

    return _base(
        "FAIL_CLOSED",
        reason="AMBIGUITY_CONTROL_DID_NOT_PRODUCE_SUPPORTED_ACTION",
        candidate_concept_ids=ids,
        ambiguity_control=control,
    )
