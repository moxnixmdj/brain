"""Bounded contextual discriminator for "loss-absorbing cushion".

This module composes existing verified primitives. It does not invent a new
semantic oracle.

Pipeline:
1. ground the exact phrase with loss_absorbing_cushion_regcap_grounding_v2;
2. compile only exact, bounded contextual clauses into matrix observations;
3. authenticate the CCoB/CCyB/TLAC contrastive matrix;
4. if and only if the caller supplies an explicitly complete bounded rival set
   matching the grounded candidates, filter candidates by observed outcome.

Open-world mapping never receives identity authority here.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v2 as grounding
from canonical.runtime import regcap_candidate_ambiguity_control_v1 as ambiguity
from canonical.runtime import regcap_contrastive_discriminator_matrix_v1 as matrix

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXT_DISCRIMINATOR_V1"
BOUND_SCOPE = ambiguity.BOUND_SCOPE

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", text.strip()).casefold()


def _sha(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "mapped_concept_id": None,
        "bounded_scope_identity_authority": False,
        "semantic_identity_authority": False,
        "semantic_truth_authority": False,
        "global_phrase_identity_authority": False,
        "candidate_universe_complete": False,
        "open_world_candidate_set_complete": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def compile_context_observations(
    source_text: str,
    *,
    context_start: int,
    context_end: int,
) -> dict[str, Any]:
    """Compile only exact bounded clauses into matrix observation values.

    V1 recognizes three intentionally narrow source forms:
    - Basel buffer class: explicit "additional layer ... above the regulatory
      minimums" + "must be met with ... CET1";
    - CCyB releasability: explicit "only designated releasable buffer in the
      Basel Framework";
    - TLAC framework class: explicit "Minimum External TLAC ... alongside
      minimum regulatory capital requirements".

    These are observation facts, not global concept identity claims.
    """
    if not isinstance(source_text, str) or not source_text:
        return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
    if (
        isinstance(context_start, bool)
        or not isinstance(context_start, int)
        or isinstance(context_end, bool)
        or not isinstance(context_end, int)
        or context_start < 0
        or context_end <= context_start
        or context_end > len(source_text)
    ):
        return _base("FAIL_CLOSED", reason="CONTEXT_SPAN_INVALID")

    raw = source_text[context_start:context_end]
    text = _norm(raw)
    observations = []

    # Positive Basel buffer framework shape. This deliberately does not separate
    # CCoB from CCyB.
    if (
        "additional layer of capital above the regulatory minimums" in text
        and (
            "must be met with common equity tier 1" in text
            or "must be met with cet1" in text
        )
    ):
        observations.append({
            "observation_id": "FRAMEWORK_CLASS",
            "observed_outcome": "BASEL_CAPITAL_BUFFER_ABOVE_REGULATORY_MINIMUM",
            "proof_kind": "EXACT_BOUNDED_CONTEXT_CLAUSE",
        })

    # Only this explicit designation is allowed to answer the releasability
    # observation. Generic words such as "released" are not enough.
    if (
        "only designated releasable buffer in the basel framework" in text
        or "only designated releasable buffer in the basel framework." in text
    ):
        observations.append({
            "observation_id": "RELEASABILITY_CLASS",
            "observed_outcome": "BASEL_DESIGNATED_RELEASABLE_BUFFER",
            "proof_kind": "EXACT_BOUNDED_CONTEXT_CLAUSE",
        })

    # TLAC is source-backed as a separate minimum requirement alongside Basel
    # minimum regulatory capital requirements.
    if (
        "minimum external tlac" in text
        and "alongside minimum regulatory capital requirements" in text
    ):
        observations.append({
            "observation_id": "FRAMEWORK_CLASS",
            "observed_outcome": "SEPARATE_MINIMUM_TLAC_REQUIREMENT",
            "proof_kind": "EXACT_BOUNDED_CONTEXT_CLAUSE",
        })

    return _base(
        "PASS__BOUNDED_CONTEXT_OBSERVATIONS_COMPILED",
        passed=True,
        source_text_sha256=sha256(source_text.encode("utf-8")).hexdigest(),
        context_span=[context_start, context_end],
        raw_context=raw,
        observations=observations,
        observation_count=len(observations),
        semantic_truth_authority=bool(observations),
        boundary=(
            "EXACT_BOUNDED_CONTEXT_CLAUSES_ONLY__GENERIC_RELEASE_RESOLUTION_"
            "RECAPITALISATION_OR_CET1_WORDS_DO_NOT_AUTHORIZE_MATRIX_OUTCOMES__"
            "NO_GLOBAL_CONCEPT_IDENTITY"
        ),
    )


def _validate_bound_scope(
    mapping_scope: Mapping[str, Any],
    candidate_ids: list[str],
) -> str | None:
    if not isinstance(mapping_scope, Mapping):
        return "MAPPING_SCOPE_REQUIRED"
    if mapping_scope.get("kind") != BOUND_SCOPE:
        return "OPEN_WORLD_OR_UNBOUND_SCOPE"
    if mapping_scope.get("scope_complete") is not True:
        return "BOUND_SCOPE_COMPLETENESS_REQUIRED"
    scope_ids = mapping_scope.get("candidate_ids")
    if not isinstance(scope_ids, list):
        return "BOUND_SCOPE_CANDIDATE_IDS_REQUIRED"
    if sorted(scope_ids) != sorted(candidate_ids):
        return "BOUND_SCOPE_CANDIDATES_MISMATCH"
    return None


def _filter_candidates(
    candidate_ids: list[str],
    observations: list[Mapping[str, Any]],
    matrix_result: Mapping[str, Any],
) -> tuple[list[str], list[dict[str, Any]]]:
    surviving = list(candidate_ids)
    applied = []
    rows = {
        str(row["observation_id"]): row
        for row in matrix_result.get("observations") or []
        if isinstance(row, Mapping) and row.get("observation_id")
    }
    for observed in observations:
        oid = str(observed.get("observation_id") or "")
        outcome = observed.get("observed_outcome")
        row = rows.get(oid)
        if row is None:
            continue
        outcomes = row.get("outcomes")
        if not isinstance(outcomes, Mapping):
            continue
        before = list(surviving)
        surviving = [
            cid
            for cid in surviving
            if outcomes.get(cid) == outcome
        ]
        applied.append({
            "observation_id": oid,
            "observed_outcome": outcome,
            "candidate_ids_before": before,
            "candidate_ids_after": list(surviving),
        })
    return surviving, applied


def resolve(
    source_text: str,
    *,
    source_id: str,
    phrase_start: int,
    phrase_end: int,
    context_start: int,
    context_end: int,
    mapping_scope: Mapping[str, Any],
    repo_root: Any = None,
    matrix_projection_verifier: Any = None,
) -> dict[str, Any]:
    """Resolve only within an explicitly complete bounded rival task."""
    base_grounding = grounding.ground(
        source_text,
        source_id=source_id,
        start=phrase_start,
        end=phrase_end,
        repo_root=repo_root,
    )
    if base_grounding.get("status") == "FAIL_CLOSED":
        return _base(
            "FAIL_CLOSED",
            reason="GROUNDING_FAILED",
            grounding_result=base_grounding,
        )

    # Preserve stronger source-local identity already owned by V2.
    if (
        base_grounding.get("mapped_concept_id")
        and base_grounding.get("semantic_identity_authority") is True
    ):
        return _base(
            "PASS__PREEXISTING_SOURCE_LOCAL_IDENTITY",
            passed=True,
            mapped_concept_id=base_grounding["mapped_concept_id"],
            bounded_scope_identity_authority=True,
            semantic_identity_authority=True,
            semantic_truth_authority=True,
            global_phrase_identity_authority=False,
            grounding_result=base_grounding,
            source_specific_identity_precedence=True,
        )

    discovery = base_grounding.get("candidate_discovery")
    if not isinstance(discovery, Mapping):
        return _base(
            "FAIL_CLOSED",
            reason="GROUNDING_CANDIDATE_DISCOVERY_MISSING",
            grounding_result=base_grounding,
        )
    candidate_ids = list(discovery.get("candidate_concept_ids") or [])
    if (
        not candidate_ids
        or discovery.get("candidate_set_complete_relative_to_bound_rivals") is not True
    ):
        return _base(
            "FAIL_CLOSED",
            reason="AUTHENTICATED_BOUND_CANDIDATE_SET_REQUIRED",
            grounding_result=base_grounding,
        )

    scope_error = _validate_bound_scope(mapping_scope, candidate_ids)
    if scope_error == "OPEN_WORLD_OR_UNBOUND_SCOPE":
        return _base(
            "OPEN__CONTEXT_FACTS_CANNOT_GRANT_OPEN_WORLD_IDENTITY",
            grounding_result=base_grounding,
            candidate_concept_ids=candidate_ids,
            open_world_candidate_set_complete=False,
            candidate_universe_complete=False,
            reason=scope_error,
        )
    if scope_error is not None:
        return _base(
            "FAIL_CLOSED",
            reason=scope_error,
            grounding_result=base_grounding,
            candidate_concept_ids=candidate_ids,
        )

    compiled = compile_context_observations(
        source_text,
        context_start=context_start,
        context_end=context_end,
    )
    if compiled.get("status") == "FAIL_CLOSED":
        return compiled

    verifier = matrix_projection_verifier
    if verifier is None:
        matrix_result = matrix.verify_matrix(repo_root=repo_root)
    else:
        matrix_result = matrix.verify_matrix(
            repo_root=repo_root,
            projection_verifier=verifier,
        )
    if matrix_result.get("pass") is not True:
        return _base(
            "FAIL_CLOSED",
            reason="CONTRASTIVE_MATRIX_AUTHORITY_FAILED",
            matrix_result=matrix_result,
            context_result=compiled,
        )

    observations = list(compiled.get("observations") or [])
    if not observations:
        return _base(
            "OPEN__NO_BOUND_CONTEXT_DISCRIMINATOR_PROVED",
            candidate_concept_ids=candidate_ids,
            grounding_result=base_grounding,
            context_result=compiled,
            matrix_sha256=matrix_result.get("matrix_sha256"),
        )

    surviving, applied = _filter_candidates(
        candidate_ids,
        observations,
        matrix_result,
    )
    if not surviving:
        return _base(
            "FAIL_CLOSED",
            reason="AUTHENTICATED_CONTEXT_CONTRADICTS_BOUND_CANDIDATE_SET",
            candidate_concept_ids=candidate_ids,
            applied_observations=applied,
            context_result=compiled,
            matrix_sha256=matrix_result.get("matrix_sha256"),
        )

    if len(surviving) != 1:
        return _base(
            "OPEN__BOUND_CONTEXT_REDUCES_BUT_DOES_NOT_RESOLVE",
            candidate_concept_ids=candidate_ids,
            surviving_candidate_ids=surviving,
            applied_observations=applied,
            grounding_result=base_grounding,
            context_result=compiled,
            matrix_sha256=matrix_result.get("matrix_sha256"),
        )

    mapped = surviving[0]
    proof_material = {
        "source_id": source_id,
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "phrase_span": [phrase_start, phrase_end],
        "context_span": [context_start, context_end],
        "candidate_ids": sorted(candidate_ids),
        "mapped_concept_id": mapped,
        "applied_observations": applied,
        "matrix_sha256": matrix_result.get("matrix_sha256"),
    }
    return _base(
        "PASS__BOUNDED_CONTEXT_DISCRIMINATOR_RESOLVED",
        passed=True,
        mapped_concept_id=mapped,
        bounded_scope_identity_authority=True,
        semantic_identity_authority=True,
        semantic_truth_authority=True,
        global_phrase_identity_authority=False,
        candidate_universe_complete=True,
        open_world_candidate_set_complete=False,
        candidate_concept_ids=candidate_ids,
        surviving_candidate_ids=surviving,
        applied_observations=applied,
        grounding_result=base_grounding,
        context_result=compiled,
        matrix_sha256=matrix_result.get("matrix_sha256"),
        proof_sha256=_sha(proof_material),
        boundary=(
            "IDENTITY_ONLY_RELATIVE_TO_EXPLICITLY_COMPLETE_BOUND_REGCAP_RIVAL_SET__"
            "CONTEXT_MUST_PROVE_AN_AUTHENTICATED_MATRIX_OUTCOME__"
            "NO_OPEN_WORLD_OR_GLOBAL_PHRASE_IDENTITY"
        ),
    )
