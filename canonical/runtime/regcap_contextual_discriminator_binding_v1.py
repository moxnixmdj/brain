"""Bind bounded contextual facts to the bounded reg-cap discriminator matrix.

This module can identify which declared matrix candidate matches a proved
functional/structural signature. The result is RELATIVE to the caller-declared
candidate subset and never claims global concept identity or candidate-universe
completeness.
"""
from __future__ import annotations

from typing import Any, Sequence

from canonical.runtime import regcap_contextual_fact_compiler_v1 as ctx
from canonical.runtime import regcap_contrastive_discriminator_matrix_v1 as matrix
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXTUAL_DISCRIMINATOR_BINDING_V1"

_PROFILE_OBSERVATION_OUTCOME = {
    "CCOB_STRUCTURAL_PROFILE": (
        "STRUCTURAL_SIGNATURE_CLASS",
        "TWO_POINT_FIVE_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
    ),
    "CCYB_RELEASE_PROFILE": (
        "FUNCTIONAL_SIGNATURE_CLASS",
        "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
    ),
    "TLAC_RESOLUTION_PROFILE": (
        "FUNCTIONAL_SIGNATURE_CLASS",
        "G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
    ),
}


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "relative_resolution_authority": False,
        "global_concept_identity_authority": False,
        "candidate_universe_complete": False,
        "open_world_ontology_complete": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def resolve_relative(
    source_text: str,
    *,
    source_id: str,
    declared_candidate_ids: Sequence[str],
    repo_root=None,
    projection_verifier=matrix.verify_projection_pack,
) -> dict[str, Any]:
    compiled = ctx.compile_context(source_text, source_id=source_id)
    if compiled.get("pass") is not True:
        return _base(
            "UNRESOLVED__NO_BOUND_CONTEXT_PROFILE",
            contextual_fact_result=compiled,
        )

    if (
        not isinstance(declared_candidate_ids, Sequence)
        or isinstance(declared_candidate_ids, (str, bytes))
        or not declared_candidate_ids
    ):
        return _base("FAIL_CLOSED", reason="DECLARED_CANDIDATES_REQUIRED")
    candidates = [str(x) for x in declared_candidate_ids]
    if len(candidates) != len(set(candidates)):
        return _base("FAIL_CLOSED", reason="DECLARED_CANDIDATES_DUPLICATE")
    if not set(candidates).issubset(set(matrix.DOMAIN)):
        return _base("FAIL_CLOSED", reason="DECLARED_CANDIDATE_OUTSIDE_MATRIX_DOMAIN")

    verified_matrix = matrix.verify_matrix(
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if verified_matrix.get("pass") is not True:
        return _base(
            "FAIL_CLOSED",
            reason="DISCRIMINATOR_MATRIX_NOT_AUTHENTICATED",
            matrix_result=verified_matrix,
        )

    observation_rows = {
        row["observation_id"]: row
        for row in verified_matrix["observations"]
    }

    votes = []
    for profile in compiled.get("matched_profiles", []):
        binding = _PROFILE_OBSERVATION_OUTCOME.get(profile)
        if binding is None:
            continue
        observation_id, observed_outcome = binding
        row = observation_rows.get(observation_id)
        if not isinstance(row, dict):
            return _base(
                "FAIL_CLOSED",
                reason="REQUIRED_MATRIX_OBSERVATION_MISSING:" + observation_id,
            )
        matches = sorted(
            cid for cid in candidates
            if row["outcomes"].get(cid) == observed_outcome
        )
        votes.append({
            "profile": profile,
            "observation_id": observation_id,
            "observed_outcome": observed_outcome,
            "matching_candidate_ids": matches,
        })

    if not votes:
        return _base(
            "UNRESOLVED__NO_MATRIX_BOUND_PROFILE",
            contextual_fact_result=compiled,
            matrix_sha256=verified_matrix.get("matrix_sha256"),
        )

    candidate_sets = [set(v["matching_candidate_ids"]) for v in votes]
    surviving = set(candidates)
    for subset in candidate_sets:
        surviving &= subset

    if not surviving:
        return _base(
            "CONFLICT__BOUND_CONTEXT_PROFILES_HAVE_NO_COMMON_MATRIX_CANDIDATE",
            contextual_fact_result=compiled,
            votes=votes,
            declared_candidate_ids=candidates,
            matrix_sha256=verified_matrix.get("matrix_sha256"),
        )

    if len(surviving) == 1:
        relative = next(iter(surviving))
        return _base(
            "PASS__RELATIVE_MATRIX_CANDIDATE_RESOLVED",
            passed=True,
            relative_resolution_authority=True,
            relative_candidate_id=relative,
            surviving_candidate_ids=[relative],
            declared_candidate_ids=candidates,
            contextual_fact_result=compiled,
            votes=votes,
            matrix_sha256=verified_matrix.get("matrix_sha256"),
            relative_only=True,
            theorem_boundary=(
                "UNIQUE_ONLY_RELATIVE_TO_CALLER_DECLARED_MATRIX_SUBSET__"
                "NO_HYPOTHESIS_SET_COMPLETENESS_OR_GLOBAL_CONCEPT_IDENTITY"
            ),
        )

    return _base(
        "UNRESOLVED__MULTIPLE_MATRIX_CANDIDATES_SURVIVE",
        declared_candidate_ids=candidates,
        surviving_candidate_ids=sorted(surviving),
        contextual_fact_result=compiled,
        votes=votes,
        matrix_sha256=verified_matrix.get("matrix_sha256"),
    )
