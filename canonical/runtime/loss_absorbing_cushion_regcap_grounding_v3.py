"""Loss-absorbing cushion regulatory-capital grounding V3.

V3 composes the already-verified V2 source-local identity route with the
authenticated bounded CCoB/CCyB/TLAC discriminator matrix.

Control order:
1. prove the bounded source meaning and discover candidates;
2. use exact source-local identity when independently proved;
3. otherwise, when an exact bounded rival scope is supplied, reuse authenticated
   discriminator semantics and ask only for caller-bound acquisition costs / the
   resulting minimax discriminator;
4. preserve open-world ambiguity and zero terminal authority everywhere else.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v2 as v2
from canonical.runtime import regcap_candidate_ambiguity_control_v2 as ambiguity_v2

SCHEMA = "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V3"


def ground(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    mapping_scope: Mapping[str, Any] | None = None,
    observation_cost_units: Mapping[str, float] | None = None,
    information_owner: str = "SYSTEM_MODEL",
    source_scope: Mapping[str, Any] | None = None,
    discovery_delegated: bool = False,
    clarification_key: str = "regulatory_capital_mapping_context",
    repo_root: str | Path | None = None,
    projection_verifier=ambiguity_v2.matrix.verify_projection_pack,
) -> dict[str, Any]:
    base = v2.ground(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        repo_root=repo_root,
    )
    out = deepcopy(dict(base))
    out["schema"] = SCHEMA
    out["ambiguity_control_attempted"] = False
    out["authenticated_matrix_reused"] = False
    out.setdefault("terminal_authority", False)
    out.setdefault("terminal_credit_delta", 0)

    if base.get("status") == "FAIL_CLOSED":
        return out

    if (
        base.get("pass") is True
        and base.get("fully_semantically_bound") is True
        and isinstance(base.get("mapped_concept_id"), str)
        and base.get("mapped_concept_id")
    ):
        out["status"] = "PASS__SOURCE_LOCAL_REGCAP_IDENTITY_PRECEDENCE"
        out["ambiguity_control_reason"] = "EXACT_SOURCE_LOCAL_IDENTITY_ALREADY_PROVED"
        return out

    candidate_result = base.get("candidate_discovery")
    if not isinstance(candidate_result, Mapping):
        return out

    if mapping_scope is None:
        out["ambiguity_control_reason"] = "EXPLICIT_MAPPING_SCOPE_NOT_BOUND"
        return out

    planned = ambiguity_v2.plan_with_authenticated_matrix(
        candidate_result,
        mapping_scope=mapping_scope,
        observation_cost_units=observation_cost_units,
        information_owner=information_owner,
        source_scope=source_scope,
        discovery_delegated=discovery_delegated,
        clarification_key=clarification_key,
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )

    out["ambiguity_control_attempted"] = True
    out["ambiguity_control"] = deepcopy(dict(planned))
    out["authenticated_matrix_reused"] = (
        planned.get("authenticated_matrix_reused") is True
    )
    out["matrix_sha256"] = planned.get("matrix_sha256")
    out["next_observation_id"] = planned.get("next_observation_id")
    out["minimum_worst_case_cost_units"] = planned.get(
        "minimum_worst_case_cost_units"
    )
    out["minimum_information_action"] = planned.get("action")

    if planned.get("status") == "FAIL_CLOSED":
        out["status"] = "FAIL_CLOSED"
        out["pass"] = False
        out["reason"] = (
            "REGCAP_AMBIGUITY_CONTROL_FAIL_CLOSED:"
            + str(planned.get("reason") or "UNKNOWN")
        )
        out["semantic_identity_authority"] = False
        out["terminal_authority"] = False
        out["terminal_credit_delta"] = 0
        return out

    out["status"] = str(planned.get("status") or base.get("status"))
    out["pass"] = planned.get("pass") is True
    out["semantic_identity_authority"] = (
        planned.get("semantic_identity_authority") is True
    )
    out["semantic_truth_authority"] = (
        planned.get("semantic_truth_authority") is True
    )
    out["policy_adequacy_authority"] = False
    out["execution_authority"] = False
    out["acceptance_authority"] = False
    out["promotion_authority"] = False
    out["terminal_authority"] = False
    out["terminal_credit_delta"] = 0
    out["open_world_ontology_complete"] = False
    out["boundary"] = (
        "EXACT_LOSS_ABSORPTION_SOURCE_GROUNDING_PLUS_SOURCE_LOCAL_IDENTITY_OR_"
        "AUTHENTICATED_BOUNDED_REGCAP_MATRIX_MINIMUM_INFORMATION_ONLY__"
        "NO_GLOBAL_PHRASE_IDENTITY_OPEN_WORLD_ONTOLOGY_POLICY_OR_TERMINAL_AUTHORITY"
    )
    return out
