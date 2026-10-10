"""Domain-mapping semantic truth certificate V1.

Turns one scoped domain-concept relation into a canonical TRUE/FALSE/UNKNOWN
predicate observation for the existing P3 relevance CEGAR loop.

Truth authority is recomputed through proof_carrying_domain_mapping_v1 and its
underlying semantic relation controller. Caller predicate labels, embeddings,
model guesses, and unresolved candidates have no truth authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.proof_carrying_domain_mapping_v1 import resolve as resolve_mapping
from canonical.runtime.source_aligned_regcap_context_proof_v1 import (
    CCOB_KIND,
    CCYB_KIND,
    TLAC_KIND,
    verify_proof as verify_regcap_context_proof,
)
from canonical.runtime import regcap_bounded_rival_registry_authority_v1 as regcap_registry
from canonical.runtime import regcap_context_signature_v1 as regcap_context_signature
from canonical.runtime import regcap_contextual_resolution_v1 as regcap_contextual_resolution
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as tlac_mrel_pair
from canonical.runtime import regcap_mrel_pair_discriminator_v1 as regcap_mrel_pair
from canonical.runtime import regcap_mrel_no_descriptor_pair_v1 as regcap_mrel_no_descriptor_pair

SCHEMA = "PROJECT_BRAIN_DOMAIN_MAPPING_TRUTH_CERTIFICATE_V1"
TRUTH_KIND = "DOMAIN_MAPPING_RELATION"
RELATIONS = {
    "SEMANTIC_IDENTITY",
    "LOGICAL_EQUIVALENCE_IN_SCOPE",
    "LEFT_ENTAILS_RIGHT",
    "RIGHT_ENTAILS_LEFT",
    "CURRENT_DECISION_SUBSTITUTION",
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "predicate_id": None,
        "predicate_truth": "UNKNOWN",
        "truthful_precommitment_observation": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_empty_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def checked_predicate_id(
    *,
    source_id: str,
    raw_span: str,
    scope_id: str,
    target_concept_id: str,
    required_relation: str,
) -> str:
    fields = {
        "source_id": str(source_id or "").strip(),
        "raw_span_sha256": sha256(str(raw_span).encode("utf-8")).hexdigest(),
        "scope_id": str(scope_id or "").strip(),
        "target_concept_id": str(target_concept_id or "").strip(),
        "required_relation": str(required_relation or "").strip().upper(),
    }
    if (
        not fields["source_id"]
        or not str(raw_span or "").strip()
        or not fields["scope_id"]
        or not fields["target_concept_id"]
        or fields["required_relation"] not in RELATIONS
    ):
        raise ValueError("DOMAIN_MAPPING_PREDICATE_IDENTITY_FIELDS_INVALID")
    material = json.dumps(
        fields,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "domain-mapping-sha256:" + sha256(material).hexdigest()


def _contextual_refinement(raw_span: str, source_id: str) -> dict[str, Any]:
    """Harvest bounded source-native context facts without minting concept identity."""
    try:
        claims = [
            {
                "claim_id": "auto:ccob-structure",
                "kind": CCOB_KIND,
                "start": 0,
                "end": len(raw_span),
            },
            {
                "claim_id": "auto:ccyb-release",
                "kind": CCYB_KIND,
                "start": 0,
                "end": len(raw_span),
            },
            {
                "claim_id": "auto:tlac-resolution",
                "kind": TLAC_KIND,
                "start": 0,
                "end": len(raw_span),
            },
        ]
        result = verify_regcap_context_proof(
            raw_span,
            source_id=source_id,
            claims=claims,
        )
        if not isinstance(result, Mapping):
            raise ValueError("CONTEXT_PROOF_RESULT_NOT_MAPPING")
        atom_ids = sorted({
            str(row.get("id"))
            for row in result.get("proved_constraints", [])
            if isinstance(row, Mapping) and str(row.get("id") or "").strip()
        })
        accepted_kinds = sorted({
            str(row.get("kind"))
            for row in result.get("accepted_claims", [])
            if isinstance(row, Mapping) and str(row.get("kind") or "").strip()
        })
        return {
            "status": (
                "PASS__AUTHENTICATED_REGCAP_CONTEXT_FACTS"
                if atom_ids and result.get("semantic_truth_authority") is True
                else "OPEN__NO_BOUND_REGCAP_CONTEXT_FACTS"
            ),
            "source_proof_status": result.get("status"),
            "proved_atom_ids": atom_ids,
            "accepted_context_kinds": accepted_kinds,
            "semantic_truth_authority": bool(
                atom_ids and result.get("semantic_truth_authority") is True
            ),
            "concept_identity_claimed": False,
            "reverse_property_to_concept_classification_authorized": False,
            "candidate_universe_complete": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "status": "OPEN__CONTEXT_REFINEMENT_UNAVAILABLE",
            "reason": type(exc).__name__ + ":" + str(exc),
            "proved_atom_ids": [],
            "accepted_context_kinds": [],
            "semantic_truth_authority": False,
            "concept_identity_claimed": False,
            "reverse_property_to_concept_classification_authorized": False,
            "candidate_universe_complete": False,
            "terminal_authority": False,
        }


def _bounded_regcap_no_descriptor_context_relation(
    *,
    raw_span: str,
    source_id: str,
    scope_id: str,
    target_concept_id: str,
    required_relation: str,
    candidate_concepts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Resolve direct authenticated reg-cap context without requiring descriptor text."""
    if (
        scope_id != regcap_registry.SCOPE_ID
        or required_relation != "LOGICAL_EQUIVALENCE_IN_SCOPE"
    ):
        return {
            "status": "NOT_APPLICABLE",
            "pass": False,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    supplied_ids = []
    for i, row in enumerate(candidate_concepts):
        if not isinstance(row, Mapping):
            return {
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "CANDIDATE_CONCEPT_NOT_OBJECT:" + str(i),
                "semantic_truth_authority": False,
                "terminal_authority": False,
            }
        cid = str(row.get("concept_id") or "").strip()
        if not cid:
            return {
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "CANDIDATE_CONCEPT_ID_REQUIRED:" + str(i),
                "semantic_truth_authority": False,
                "terminal_authority": False,
            }
        supplied_ids.append(cid)

    resolved = regcap_contextual_resolution.resolve_authenticated_regcap_scope(
        raw_span,
        start=0,
        end=len(raw_span),
        task_scope_id=scope_id,
        candidate_ids=supplied_ids,
    )
    if resolved.get("status") == "FAIL_CLOSED":
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "REGCAP_NO_DESCRIPTOR_CONTEXT_FAIL_CLOSED",
            "context_result": resolved,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
    if (
        resolved.get("pass") is not True
        or resolved.get("concept_identity_authority") is not True
        or not resolved.get("selected_concept_id")
    ):
        return {
            "status": "OPEN__BOUNDED_NO_DESCRIPTOR_CONTEXT_RELATION_NOT_RESOLVED",
            "pass": False,
            "context_result": resolved,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    selected = str(resolved["selected_concept_id"])
    return {
        "status": "PASS__AUTHENTICATED_BOUNDED_NO_DESCRIPTOR_CONTEXT_RELATION",
        "pass": True,
        "predicate_truth": "TRUE" if selected == target_concept_id else "FALSE",
        "selected_concept_id": selected,
        "target_concept_id": target_concept_id,
        "required_relation": required_relation,
        "registry_scope_id": regcap_registry.SCOPE_ID,
        "context_result": resolved,
        "semantic_truth_authority": True,
        "global_semantic_identity_authority": False,
        "open_world_candidate_set_complete": False,
        "terminal_authority": False,
        "boundary": (
            "LOGICAL_EQUIVALENCE_ONLY_INSIDE_THE_EXACT_AUTHENTICATED_THREE_RIVAL_"
            "REGISTRY_SCOPE_FROM_DIRECT_BOUND_CONTEXT__NO_GLOBAL_SEMANTIC_IDENTITY_"
            "OR_OPEN_WORLD_COMPLETENESS"
        ),
    }


def _bounded_regcap_context_relation(
    *,
    raw_span: str,
    source_id: str,
    scope_id: str,
    target_concept_id: str,
    required_relation: str,
    candidate_concepts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Prove only task-scoped identity inside the authenticated three-rival registry.

    This path is deliberately unavailable to global SEMANTIC_IDENTITY.  The
    exact scope id names a Brain-owned finite registry whose completeness and
    discriminator semantics are independently reauthenticated.
    """
    if (
        scope_id != regcap_registry.SCOPE_ID
        or required_relation != "LOGICAL_EQUIVALENCE_IN_SCOPE"
    ):
        return {
            "status": "NOT_APPLICABLE",
            "pass": False,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    universe = regcap_registry.resolve_authenticated_registry()
    if universe.get("status") == "FAIL_CLOSED":
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "REGCAP_BOUNDED_REGISTRY_AUTHORITY_FAILED",
            "registry_result": universe,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
    if (
        universe.get("authenticated_scope_completeness") is not True
        or universe.get("hypothesis_set_complete") is not True
    ):
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "REGCAP_BOUNDED_REGISTRY_COMPLETENESS_UNPROVED",
            "registry_result": universe,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    registry_ids = sorted(str(x) for x in universe.get("candidate_concept_ids") or [])
    supplied_ids = []
    for i, row in enumerate(candidate_concepts):
        if not isinstance(row, Mapping):
            return {
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "CANDIDATE_CONCEPT_NOT_OBJECT:" + str(i),
                "registry_result": universe,
                "semantic_truth_authority": False,
                "terminal_authority": False,
            }
        cid = str(row.get("concept_id") or "").strip()
        if not cid:
            return {
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "CANDIDATE_CONCEPT_ID_REQUIRED:" + str(i),
                "registry_result": universe,
                "semantic_truth_authority": False,
                "terminal_authority": False,
            }
        supplied_ids.append(cid)
    if sorted(supplied_ids) != registry_ids:
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "CANDIDATES_DO_NOT_MATCH_AUTHENTICATED_REGISTRY",
            "registry_candidate_ids": registry_ids,
            "supplied_candidate_ids": sorted(supplied_ids),
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
    if target_concept_id not in registry_ids:
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "TARGET_OUTSIDE_AUTHENTICATED_REGISTRY",
            "registry_candidate_ids": registry_ids,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    surface = regcap_context_signature.EXACT_SURFACE
    folded = raw_span.casefold()
    starts = []
    cursor = 0
    while True:
        found = folded.find(surface, cursor)
        if found < 0:
            break
        starts.append(found)
        cursor = found + len(surface)
    if len(starts) != 1:
        return {
            "status": "OPEN__EXACTLY_ONE_BOUND_DESCRIPTOR_OCCURRENCE_REQUIRED",
            "pass": False,
            "descriptor_occurrence_count": len(starts),
            "registry_result": universe,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    authority = universe.get("authority_result")
    matrix_result = (
        authority.get("matrix_result")
        if isinstance(authority, Mapping)
        else None
    )
    source_results = (
        matrix_result.get("source_results")
        if isinstance(matrix_result, Mapping)
        else None
    )
    if not isinstance(source_results, Mapping):
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "AUTHENTICATED_MATRIX_SOURCE_RESULTS_MISSING",
            "registry_result": universe,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    def cached_projection(pack: Mapping[str, Any]) -> Mapping[str, Any]:
        sid = str(pack.get("source_id") or "")
        row = source_results.get(sid)
        return dict(row) if isinstance(row, Mapping) else {"pass": False}

    start = starts[0]
    end = start + len(surface)
    resolved = regcap_context_signature.resolve_relative(
        raw_span,
        source_id=source_id,
        start=start,
        end=end,
        candidate_concept_ids=registry_ids,
        projection_verifier=cached_projection,
    )
    if resolved.get("status") == "FAIL_CLOSED":
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "REGCAP_CONTEXT_SIGNATURE_FAIL_CLOSED",
            "registry_result": universe,
            "context_result": resolved,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
    if (
        resolved.get("pass") is not True
        or resolved.get("relative_selection_authority") is not True
        or not resolved.get("relative_selected_concept_id")
    ):
        return {
            "status": "OPEN__BOUNDED_CONTEXT_RELATION_NOT_RESOLVED",
            "pass": False,
            "registry_result": universe,
            "context_result": resolved,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    selected = str(resolved["relative_selected_concept_id"])
    return {
        "status": "PASS__AUTHENTICATED_BOUNDED_CONTEXT_RELATION",
        "pass": True,
        "predicate_truth": "TRUE" if selected == target_concept_id else "FALSE",
        "selected_concept_id": selected,
        "target_concept_id": target_concept_id,
        "required_relation": required_relation,
        "registry_scope_id": regcap_registry.SCOPE_ID,
        "registry_candidate_ids": registry_ids,
        "registry_result": universe,
        "context_result": resolved,
        "semantic_truth_authority": True,
        "global_semantic_identity_authority": False,
        "open_world_candidate_set_complete": False,
        "terminal_authority": False,
        "boundary": (
            "LOGICAL_EQUIVALENCE_ONLY_INSIDE_THE_EXACT_AUTHENTICATED_THREE_RIVAL_"
            "REGISTRY_SCOPE__NO_GLOBAL_SEMANTIC_IDENTITY_OR_OPEN_WORLD_COMPLETENESS"
        ),
    }



def _bounded_regcap_mrel_no_descriptor_context_relation(
    *,
    raw_span: str,
    source_id: str,
    scope_id: str,
    target_concept_id: str,
    required_relation: str,
    candidate_concepts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Prove CCoB/MREL or CCyB/MREL only in exact authenticated pair scopes."""
    pair_id = None
    for candidate_pair_id, candidate_scope in regcap_mrel_pair.PAIR_SCOPE.items():
        if scope_id == candidate_scope:
            pair_id = candidate_pair_id
            break
    if (
        pair_id is None
        or required_relation != "LOGICAL_EQUIVALENCE_IN_SCOPE"
    ):
        return {
            "status": "NOT_APPLICABLE",
            "pass": False,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    supplied_ids = []
    for i, row in enumerate(candidate_concepts):
        if not isinstance(row, Mapping):
            return {
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "REGCAP_MREL_NO_DESCRIPTOR_CANDIDATE_NOT_OBJECT:" + str(i),
                "semantic_truth_authority": False,
                "terminal_authority": False,
            }
        cid = str(row.get("concept_id") or "").strip()
        if not cid:
            return {
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "REGCAP_MREL_NO_DESCRIPTOR_CANDIDATE_ID_REQUIRED:" + str(i),
                "semantic_truth_authority": False,
                "terminal_authority": False,
            }
        supplied_ids.append(cid)

    required_ids = sorted(regcap_mrel_pair.PAIR_DOMAIN[pair_id])
    if sorted(supplied_ids) != required_ids:
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "REGCAP_MREL_NO_DESCRIPTOR_CANDIDATE_SET_MISMATCH",
            "pair_id": pair_id,
            "supplied_candidate_ids": sorted(supplied_ids),
            "required_candidate_ids": required_ids,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
    if target_concept_id not in regcap_mrel_pair.PAIR_DOMAIN[pair_id]:
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "REGCAP_MREL_NO_DESCRIPTOR_TARGET_OUTSIDE_BOUND_PAIR",
            "pair_id": pair_id,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    resolved = regcap_mrel_no_descriptor_pair.resolve_relative(
        raw_span,
        source_id=source_id,
        pair_id=pair_id,
        candidate_concept_ids=supplied_ids,
    )
    if resolved.get("status") == "FAIL_CLOSED":
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "REGCAP_MREL_NO_DESCRIPTOR_DISCRIMINATOR_FAIL_CLOSED",
            "pair_id": pair_id,
            "context_result": resolved,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
    if (
        resolved.get("pass") is not True
        or resolved.get("relative_selection_authority") is not True
        or not resolved.get("selected_concept_id")
    ):
        return {
            "status": "OPEN__BOUNDED_REGCAP_MREL_NO_DESCRIPTOR_RELATION_NOT_RESOLVED",
            "pass": False,
            "pair_id": pair_id,
            "context_result": resolved,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    selected = str(resolved["selected_concept_id"])
    return {
        "status": "PASS__AUTHENTICATED_BOUNDED_REGCAP_MREL_NO_DESCRIPTOR_RELATION",
        "pass": True,
        "predicate_truth": "TRUE" if selected == target_concept_id else "FALSE",
        "selected_concept_id": selected,
        "target_concept_id": target_concept_id,
        "required_relation": required_relation,
        "pair_id": pair_id,
        "scope_id": regcap_mrel_pair.PAIR_SCOPE[pair_id],
        "candidate_ids": list(regcap_mrel_pair.PAIR_DOMAIN[pair_id]),
        "context_result": resolved,
        "semantic_truth_authority": True,
        "global_semantic_identity_authority": False,
        "open_world_candidate_set_complete": False,
        "terminal_authority": False,
        "boundary": (
            "LOGICAL_EQUIVALENCE_ONLY_INSIDE_THE_EXACT_AUTHENTICATED_CCOB_MREL_"
            "OR_CCYB_MREL_PAIR_TASK_SCOPE__NO_GLOBAL_SEMANTIC_IDENTITY_DISJOINTNESS_"
            "OR_OPEN_WORLD_COMPLETENESS"
        ),
    }


def _bounded_tlac_mrel_context_relation(
    *,
    raw_span: str,
    source_id: str,
    scope_id: str,
    target_concept_id: str,
    required_relation: str,
    candidate_concepts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Prove task-scoped TLAC/MREL identity only inside the authenticated pair."""
    if (
        scope_id != tlac_mrel_pair.SCOPE_ID
        or required_relation != "LOGICAL_EQUIVALENCE_IN_SCOPE"
    ):
        return {
            "status": "NOT_APPLICABLE",
            "pass": False,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    supplied_ids = []
    for i, row in enumerate(candidate_concepts):
        if not isinstance(row, Mapping):
            return {
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "TLAC_MREL_CANDIDATE_NOT_OBJECT:" + str(i),
                "semantic_truth_authority": False,
                "terminal_authority": False,
            }
        cid = str(row.get("concept_id") or "").strip()
        if not cid:
            return {
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "TLAC_MREL_CANDIDATE_ID_REQUIRED:" + str(i),
                "semantic_truth_authority": False,
                "terminal_authority": False,
            }
        supplied_ids.append(cid)

    if sorted(supplied_ids) != sorted(tlac_mrel_pair.DOMAIN):
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "TLAC_MREL_CANDIDATE_SET_MISMATCH",
            "supplied_candidate_ids": sorted(supplied_ids),
            "required_candidate_ids": sorted(tlac_mrel_pair.DOMAIN),
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
    if target_concept_id not in tlac_mrel_pair.DOMAIN:
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "TLAC_MREL_TARGET_OUTSIDE_BOUND_PAIR",
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    resolved = tlac_mrel_pair.resolve_relative(
        raw_span,
        source_id=source_id,
        candidate_concept_ids=supplied_ids,
    )
    if resolved.get("status") == "FAIL_CLOSED":
        return {
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "TLAC_MREL_DISCRIMINATOR_FAIL_CLOSED",
            "context_result": resolved,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
    if (
        resolved.get("pass") is not True
        or resolved.get("relative_selection_authority") is not True
        or not resolved.get("selected_concept_id")
    ):
        return {
            "status": "OPEN__BOUNDED_TLAC_MREL_CONTEXT_RELATION_NOT_RESOLVED",
            "pass": False,
            "context_result": resolved,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }

    selected = str(resolved["selected_concept_id"])
    return {
        "status": "PASS__AUTHENTICATED_BOUNDED_TLAC_MREL_CONTEXT_RELATION",
        "pass": True,
        "predicate_truth": "TRUE" if selected == target_concept_id else "FALSE",
        "selected_concept_id": selected,
        "target_concept_id": target_concept_id,
        "required_relation": required_relation,
        "scope_id": tlac_mrel_pair.SCOPE_ID,
        "candidate_ids": list(tlac_mrel_pair.DOMAIN),
        "context_result": resolved,
        "semantic_truth_authority": True,
        "global_semantic_identity_authority": False,
        "open_world_candidate_set_complete": False,
        "terminal_authority": False,
        "boundary": (
            "LOGICAL_EQUIVALENCE_ONLY_INSIDE_THE_EXACT_AUTHENTICATED_TLAC_MREL_"
            "PAIR_TASK_SCOPE__NO_GLOBAL_SEMANTIC_IDENTITY_DISJOINTNESS_OR_OPEN_WORLD_COMPLETENESS"
        ),
    }


def _unknown(
    *,
    checked_id: str,
    requested_id: str,
    reason: str,
    mapping_result: Mapping[str, Any] | None = None,
    contextual_refinement: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    refinement = dict(contextual_refinement or {})
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNKNOWN__DOMAIN_MAPPING_RELATION_NOT_PROVED",
        "reason": reason,
        "predicate_id": checked_id,
        "requested_predicate_id": requested_id,
        "requested_predicate_id_authority": False,
        "predicate_truth": "UNKNOWN",
        "mapping_result": dict(mapping_result or {}),
        "authenticated_context_refinement": refinement,
        "truthful_precommitment_observation": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_empty_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    atom_ids = list(refinement.get("proved_atom_ids") or [])
    if refinement.get("semantic_truth_authority") is True and atom_ids:
        out["next_information_request"] = {
            "kind": "REUSE_AUTHENTICATED_CONTEXT_FACTS_FOR_DOMAIN_MAPPING",
            "proved_atom_ids": atom_ids,
            "relation_truth_still_required": True,
            "concept_identity_authorized": False,
            "candidate_universe_complete": False,
            "terminal_authority": False,
        }
    return out


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    allowed = {
        "truth_kind",
        "predicate_id",
        "raw_span",
        "source_id",
        "scope_id",
        "target_concept_id",
        "required_relation",
        "candidate_concepts",
        "evidence",
        "candidate_semantic_atoms",
        "relation_problems",
    }
    extra = set(payload) - allowed
    if extra:
        return _fail("UNMODELED_FIELDS:" + ",".join(sorted(str(x) for x in extra)))

    truth_kind = payload.get("truth_kind")
    if truth_kind not in (None, TRUTH_KIND):
        return _fail("TRUTH_KIND_INVALID")

    requested_id = str(payload.get("predicate_id") or "").strip()
    raw_span = payload.get("raw_span")
    source_id = str(payload.get("source_id") or "").strip()
    scope_id = str(payload.get("scope_id") or "").strip()
    target = str(payload.get("target_concept_id") or "").strip()
    required = str(payload.get("required_relation") or "").strip().upper()
    candidates = payload.get("candidate_concepts")
    relation_problems = payload.get("relation_problems", {})

    if not requested_id:
        return _fail("PREDICATE_ID_REQUIRED")
    if not isinstance(raw_span, str) or not raw_span.strip():
        return _fail("RAW_SPAN_REQUIRED")
    if not source_id:
        return _fail("SOURCE_ID_REQUIRED")
    if not scope_id:
        return _fail("SCOPE_ID_REQUIRED")
    if not target:
        return _fail("TARGET_CONCEPT_ID_REQUIRED")
    if required not in RELATIONS:
        return _fail("REQUIRED_RELATION_INVALID")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return _fail("CANDIDATE_CONCEPTS_REQUIRED")
    if not isinstance(relation_problems, Mapping):
        return _fail("RELATION_PROBLEMS_INVALID")

    contextual_refinement = _contextual_refinement(raw_span, source_id)

    try:
        checked = checked_predicate_id(
            source_id=source_id,
            raw_span=raw_span,
            scope_id=scope_id,
            target_concept_id=target,
            required_relation=required,
        )
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

    bounded_tlac_mrel = _bounded_tlac_mrel_context_relation(
        raw_span=raw_span,
        source_id=source_id,
        scope_id=scope_id,
        target_concept_id=target,
        required_relation=required,
        candidate_concepts=candidates,
    )
    if bounded_tlac_mrel.get("status") == "FAIL_CLOSED":
        return _fail(
            "BOUNDED_TLAC_MREL_CONTEXT_FAIL_CLOSED",
            bounded_tlac_mrel=bounded_tlac_mrel,
        )
    if bounded_tlac_mrel.get("pass") is True:
        truth = str(bounded_tlac_mrel.get("predicate_truth") or "")
        if truth not in {"TRUE", "FALSE"}:
            return _fail(
                "BOUNDED_TLAC_MREL_CONTEXT_TRUTH_INVALID",
                bounded_tlac_mrel=bounded_tlac_mrel,
            )
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": (
                "PASS__BOUNDED_TLAC_MREL_CONTEXT_RELATION_PROVED_TRUE"
                if truth == "TRUE"
                else "PASS__BOUNDED_TLAC_MREL_CONTEXT_RELATION_PROVED_FALSE"
            ),
            "predicate_id": checked,
            "requested_predicate_id": requested_id,
            "requested_predicate_id_authority": False,
            "predicate_truth": truth,
            "target_concept_id": target,
            "required_relation": required,
            "source_id": source_id,
            "source_sha256": sha256(raw_span.encode("utf-8")).hexdigest(),
            "scope_id": scope_id,
            "mapping_result": {},
            "authenticated_context_refinement": contextual_refinement,
            "bounded_tlac_mrel_context_relation": bounded_tlac_mrel,
            "truthful_precommitment_observation": True,
            "semantic_truth_authority": True,
            "policy_adequacy_authority": False,
            "db_admission_authority": False,
            "u_empty_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "AUTHENTICATED_TLAC_MREL_PAIR_TASK_SCOPE_ONLY__"
                "LOGICAL_EQUIVALENCE_IN_SCOPE_ONLY__NO_GLOBAL_SEMANTIC_IDENTITY__"
                "NO_OPEN_WORLD_CANDIDATE_COMPLETENESS_OR_TERMINAL_AUTHORITY"
            ),
        }

    bounded_regcap_mrel_no_descriptor = _bounded_regcap_mrel_no_descriptor_context_relation(
        raw_span=raw_span,
        source_id=source_id,
        scope_id=scope_id,
        target_concept_id=target,
        required_relation=required,
        candidate_concepts=candidates,
    )
    if bounded_regcap_mrel_no_descriptor.get("status") == "FAIL_CLOSED":
        return _fail(
            "BOUNDED_REGCAP_MREL_NO_DESCRIPTOR_CONTEXT_FAIL_CLOSED",
            bounded_regcap_mrel_no_descriptor=bounded_regcap_mrel_no_descriptor,
        )
    if bounded_regcap_mrel_no_descriptor.get("pass") is True:
        truth = str(bounded_regcap_mrel_no_descriptor.get("predicate_truth") or "")
        if truth not in {"TRUE", "FALSE"}:
            return _fail(
                "BOUNDED_REGCAP_MREL_NO_DESCRIPTOR_CONTEXT_TRUTH_INVALID",
                bounded_regcap_mrel_no_descriptor=bounded_regcap_mrel_no_descriptor,
            )
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": (
                "PASS__BOUNDED_REGCAP_MREL_NO_DESCRIPTOR_CONTEXT_RELATION_PROVED_TRUE"
                if truth == "TRUE"
                else "PASS__BOUNDED_REGCAP_MREL_NO_DESCRIPTOR_CONTEXT_RELATION_PROVED_FALSE"
            ),
            "predicate_id": checked,
            "requested_predicate_id": requested_id,
            "requested_predicate_id_authority": False,
            "predicate_truth": truth,
            "target_concept_id": target,
            "required_relation": required,
            "source_id": source_id,
            "source_sha256": sha256(raw_span.encode("utf-8")).hexdigest(),
            "scope_id": scope_id,
            "mapping_result": {},
            "authenticated_context_refinement": contextual_refinement,
            "bounded_regcap_mrel_no_descriptor_context_relation": bounded_regcap_mrel_no_descriptor,
            "truthful_precommitment_observation": True,
            "semantic_truth_authority": True,
            "policy_adequacy_authority": False,
            "db_admission_authority": False,
            "u_empty_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "AUTHENTICATED_CCOB_MREL_OR_CCYB_MREL_PAIR_TASK_SCOPE_ONLY__"
                "LOGICAL_EQUIVALENCE_IN_SCOPE_ONLY__NO_GLOBAL_SEMANTIC_IDENTITY__"
                "NO_OPEN_WORLD_CANDIDATE_COMPLETENESS_OR_TERMINAL_AUTHORITY"
            ),
        }

    bounded_no_descriptor = _bounded_regcap_no_descriptor_context_relation(
        raw_span=raw_span,
        source_id=source_id,
        scope_id=scope_id,
        target_concept_id=target,
        required_relation=required,
        candidate_concepts=candidates,
    )
    if bounded_no_descriptor.get("status") == "FAIL_CLOSED":
        return _fail(
            "BOUNDED_REGCAP_NO_DESCRIPTOR_CONTEXT_FAIL_CLOSED",
            bounded_no_descriptor=bounded_no_descriptor,
        )
    if bounded_no_descriptor.get("pass") is True:
        truth = str(bounded_no_descriptor.get("predicate_truth") or "")
        if truth not in {"TRUE", "FALSE"}:
            return _fail(
                "BOUNDED_REGCAP_NO_DESCRIPTOR_CONTEXT_TRUTH_INVALID",
                bounded_no_descriptor=bounded_no_descriptor,
            )
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": (
                "PASS__BOUNDED_REGCAP_NO_DESCRIPTOR_CONTEXT_RELATION_PROVED_TRUE"
                if truth == "TRUE"
                else "PASS__BOUNDED_REGCAP_NO_DESCRIPTOR_CONTEXT_RELATION_PROVED_FALSE"
            ),
            "predicate_id": checked,
            "requested_predicate_id": requested_id,
            "requested_predicate_id_authority": False,
            "predicate_truth": truth,
            "target_concept_id": target,
            "required_relation": required,
            "source_id": source_id,
            "source_sha256": sha256(raw_span.encode("utf-8")).hexdigest(),
            "scope_id": scope_id,
            "mapping_result": {},
            "authenticated_context_refinement": contextual_refinement,
            "bounded_no_descriptor_context_relation": bounded_no_descriptor,
            "truthful_precommitment_observation": True,
            "semantic_truth_authority": True,
            "policy_adequacy_authority": False,
            "db_admission_authority": False,
            "u_empty_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "AUTHENTICATED_THREE_RIVAL_REGISTRY_SCOPE_DIRECT_CONTEXT_ONLY__"
                "LOGICAL_EQUIVALENCE_IN_SCOPE_ONLY__NO_GLOBAL_SEMANTIC_IDENTITY__"
                "NO_OPEN_WORLD_CANDIDATE_COMPLETENESS_OR_TERMINAL_AUTHORITY"
            ),
        }

    bounded_context = _bounded_regcap_context_relation(
        raw_span=raw_span,
        source_id=source_id,
        scope_id=scope_id,
        target_concept_id=target,
        required_relation=required,
        candidate_concepts=candidates,
    )
    if bounded_context.get("status") == "FAIL_CLOSED":
        return _fail(
            "BOUNDED_REGCAP_CONTEXT_FAIL_CLOSED",
            bounded_context=bounded_context,
        )
    if bounded_context.get("pass") is True:
        truth = str(bounded_context.get("predicate_truth") or "")
        if truth not in {"TRUE", "FALSE"}:
            return _fail(
                "BOUNDED_REGCAP_CONTEXT_TRUTH_INVALID",
                bounded_context=bounded_context,
            )
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": (
                "PASS__BOUNDED_REGCAP_CONTEXT_RELATION_PROVED_TRUE"
                if truth == "TRUE"
                else "PASS__BOUNDED_REGCAP_CONTEXT_RELATION_PROVED_FALSE"
            ),
            "predicate_id": checked,
            "requested_predicate_id": requested_id,
            "requested_predicate_id_authority": False,
            "predicate_truth": truth,
            "target_concept_id": target,
            "required_relation": required,
            "source_id": source_id,
            "source_sha256": sha256(raw_span.encode("utf-8")).hexdigest(),
            "scope_id": scope_id,
            "mapping_result": {},
            "authenticated_context_refinement": contextual_refinement,
            "bounded_context_relation": bounded_context,
            "truthful_precommitment_observation": True,
            "semantic_truth_authority": True,
            "policy_adequacy_authority": False,
            "db_admission_authority": False,
            "u_empty_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "AUTHENTICATED_THREE_RIVAL_REGISTRY_SCOPE_ONLY__"
                "LOGICAL_EQUIVALENCE_IN_SCOPE_ONLY__NO_GLOBAL_SEMANTIC_IDENTITY__"
                "NO_OPEN_WORLD_CANDIDATE_COMPLETENESS_OR_TERMINAL_AUTHORITY"
            ),
        }

    target_problem = relation_problems.get(target)
    if not isinstance(target_problem, Mapping):
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            reason="TARGET_RELATION_PROBLEM_REQUIRED",
            contextual_refinement=contextual_refinement,
        )
    target_required = str(target_problem.get("required_relation") or required).strip().upper()
    if target_required != required:
        return _fail(
            "TARGET_RELATION_REQUIRED_RELATION_MISMATCH",
            target_required_relation=target_required,
            certificate_required_relation=required,
        )

    result = resolve_mapping(
        raw_span,
        source_id=source_id,
        scope_id=scope_id,
        candidate_concepts=candidates,
        evidence=payload.get("evidence", ()),
        candidate_semantic_atoms=payload.get("candidate_semantic_atoms", ()),
        relation_problems=relation_problems,
    )
    if result.get("status") == "FAIL_CLOSED":
        return _fail(
            "DOMAIN_MAPPING_FAIL_CLOSED",
            mapping_reason=result.get("reason"),
            mapping_result=result,
        )

    target_eval = None
    for row in result.get("candidate_evaluations") or []:
        if isinstance(row, Mapping) and row.get("concept_id") == target:
            target_eval = row
            break
    if not isinstance(target_eval, Mapping):
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            reason="TARGET_CONCEPT_NOT_SURVIVING_FOR_RELATION_EVALUATION",
            mapping_result=result,
            contextual_refinement=contextual_refinement,
        )

    relation = target_eval.get("relation_result")
    if not isinstance(relation, Mapping):
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            reason="TARGET_RELATION_RESULT_UNAVAILABLE",
            mapping_result=result,
            contextual_refinement=contextual_refinement,
        )

    if (
        relation.get("pass") is True
        and str(relation.get("required_relation") or "").upper() == required
    ):
        truth = "TRUE"
        status = "PASS__DOMAIN_MAPPING_RELATION_PROVED_TRUE"
    elif (
        relation.get("required_relation_disproved") is True
        and str(relation.get("required_relation") or "").upper() == required
    ):
        truth = "FALSE"
        status = "PASS__DOMAIN_MAPPING_RELATION_PROVED_FALSE"
    else:
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            reason=str(
                relation.get("status")
                or relation.get("reason")
                or "TARGET_RELATION_NOT_PROVED"
            ),
            mapping_result=result,
            contextual_refinement=contextual_refinement,
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": status,
        "predicate_id": checked,
        "requested_predicate_id": requested_id,
        "requested_predicate_id_authority": False,
        "predicate_truth": truth,
        "target_concept_id": target,
        "required_relation": required,
        "source_id": source_id,
        "source_sha256": sha256(raw_span.encode("utf-8")).hexdigest(),
        "scope_id": scope_id,
        "mapping_result": result,
        "authenticated_context_refinement": contextual_refinement,
        "truthful_precommitment_observation": True,
        "semantic_truth_authority": True,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_empty_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "DOMAIN_MAPPING_RELATION_TRUTH_ONLY__CALLER_PREDICATE_LABEL_NONAUTHORITATIVE__"
            "UNRESOLVED_MAPPING_STAYS_UNKNOWN__NO_POLICY_ACCEPTANCE_OR_TERMINAL_AUTHORITY"
        ),
    }
