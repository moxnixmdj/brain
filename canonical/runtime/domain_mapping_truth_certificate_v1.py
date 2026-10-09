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

    target_problem = relation_problems.get(target)
    if not isinstance(target_problem, Mapping):
        checked = checked_predicate_id(
            source_id=source_id,
            raw_span=raw_span,
            scope_id=scope_id,
            target_concept_id=target,
            required_relation=required,
        )
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
