"""Proof-carrying domain mapping V1.

A narrow bridge from a raw source mention to scoped domain-concept relations.

This module is intentionally conservative:
- lexical/model candidates never certify mappings;
- missing evidence remains UNKNOWN rather than FALSE;
- finite-registry completeness is only reused when independently authenticated;
- exact semantic identity is delegated to the existing semantic-relation controller;
- unresolved source meaning keeps an opaque remainder upstream.

It grants no execution, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import bounded_authenticated_concept_universe_v1 as concept_universe
from canonical.runtime import semantic_relation_control_v1 as semantic_relation

SCHEMA = "PROJECT_BRAIN_PROOF_CARRYING_DOMAIN_MAPPING_V1"
VALID_EVIDENCE_STATES = {"SUPPORTED", "REFUTED", "UNKNOWN", "CONFLICT"}
VERIFIED_RELATIONS = {
    "SEMANTIC_IDENTITY": "VERIFIED_EXACT",
    "LOGICAL_EQUIVALENCE_IN_SCOPE": "VERIFIED_EXACT",
    "LEFT_ENTAILS_RIGHT": "VERIFIED_SOURCE_NARROWER",
    "RIGHT_ENTAILS_LEFT": "VERIFIED_SOURCE_BROADER",
    "CURRENT_DECISION_SUBSTITUTION": "VERIFIED_DECISION_SUBSTITUTION",
}


class DomainMappingError(ValueError):
    pass


def _raw_span_sha256(raw_span: str) -> str:
    return sha256(raw_span.encode("utf-8")).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "candidate_semantic_atoms": [],
        "proved_semantic_atoms": [],
        "fully_semantically_bound": False,
        "opaque_remainder_required": True,
        "semantic_truth_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _evidence_index(rows: Any) -> dict[str, dict[str, Any]]:
    if rows is None:
        return {}
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise DomainMappingError("EVIDENCE_ROWS_INVALID")
    out: dict[str, dict[str, Any]] = {}
    for i, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise DomainMappingError(f"EVIDENCE_ROW_NOT_OBJECT:{i}")
        atom = str(raw.get("atom") or "").strip()
        state = str(raw.get("state") or "").strip().upper()
        if not atom:
            raise DomainMappingError(f"EVIDENCE_ATOM_REQUIRED:{i}")
        if atom in out:
            raise DomainMappingError("EVIDENCE_ATOM_DUPLICATE:" + atom)
        if state not in VALID_EVIDENCE_STATES:
            raise DomainMappingError("EVIDENCE_STATE_INVALID:" + atom)
        out[atom] = deepcopy(dict(raw))
        out[atom]["state"] = state
    return out


def _candidate_rows(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise DomainMappingError("CANDIDATE_CONCEPTS_REQUIRED")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise DomainMappingError(f"CANDIDATE_NOT_OBJECT:{i}")
        cid = str(raw.get("concept_id") or "").strip()
        if not cid:
            raise DomainMappingError(f"CANDIDATE_ID_REQUIRED:{i}")
        if cid in seen:
            raise DomainMappingError("CANDIDATE_ID_DUPLICATE:" + cid)
        seen.add(cid)
        required = raw.get("required_atoms", [])
        forbidden = raw.get("forbidden_atoms", [])
        for name, value in (("required_atoms", required), ("forbidden_atoms", forbidden)):
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                raise DomainMappingError(f"{name.upper()}_INVALID:{cid}")
            if any(not isinstance(x, str) or not x.strip() for x in value):
                raise DomainMappingError(f"{name.upper()}_INVALID:{cid}")
        row = deepcopy(dict(raw))
        row["concept_id"] = cid
        row["required_atoms"] = sorted(set(str(x).strip() for x in required))
        row["forbidden_atoms"] = sorted(set(str(x).strip() for x in forbidden))
        out.append(row)
    return out


def _evaluate_contract(
    candidate: Mapping[str, Any],
    evidence: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    supported: list[str] = []
    unresolved: list[str] = []
    refutations: list[dict[str, str]] = []

    for atom in candidate.get("required_atoms", []):
        state = str((evidence.get(atom) or {}).get("state") or "UNKNOWN")
        if state == "SUPPORTED":
            supported.append(atom)
        elif state == "REFUTED":
            refutations.append({"atom": atom, "reason": "REQUIRED_ATOM_REFUTED"})
        else:
            unresolved.append(atom)

    for atom in candidate.get("forbidden_atoms", []):
        state = str((evidence.get(atom) or {}).get("state") or "UNKNOWN")
        if state == "SUPPORTED":
            refutations.append({"atom": atom, "reason": "FORBIDDEN_ATOM_SUPPORTED"})
        elif state in {"UNKNOWN", "CONFLICT"}:
            unresolved.append(atom)

    return {
        "supported_required_atoms": sorted(supported),
        "unresolved_atoms": sorted(set(unresolved)),
        "refutations": refutations,
        "contract_refuted": bool(refutations),
        "contract_complete": not refutations and not unresolved,
    }


def _completeness_authenticated(
    *,
    raw_span: str,
    source_id: str,
    receipt: Mapping[str, Any] | None,
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> dict[str, Any]:
    if receipt is None or verifier is None:
        return {"pass": False, "reason": "SOURCE_SEMANTICS_COMPLETENESS_NOT_AUTHENTICATED"}
    if not isinstance(receipt, Mapping):
        return {"pass": False, "reason": "SOURCE_SEMANTICS_COMPLETENESS_RECEIPT_INVALID"}
    result = verifier(deepcopy(dict(receipt)))
    if not isinstance(result, Mapping):
        return {"pass": False, "reason": "SOURCE_SEMANTICS_COMPLETENESS_VERIFIER_NO_RESULT"}
    expected = {
        "pass": True,
        "independent_verified": True,
        "source_id": source_id,
        "raw_span_sha256": _raw_span_sha256(raw_span),
        "decision_relevant_semantics_complete": True,
        "verification_authority_mutated": False,
    }
    mismatches = [k for k, v in expected.items() if result.get(k) != v]
    if mismatches:
        return {
            "pass": False,
            "reason": "SOURCE_SEMANTICS_COMPLETENESS_BINDING_INVALID",
            "mismatch_fields": sorted(mismatches),
            "verifier_result": deepcopy(dict(result)),
        }
    return {"pass": True, "verifier_result": deepcopy(dict(result))}


def resolve(
    raw_span: str,
    *,
    source_id: str,
    scope_id: str,
    candidate_concepts: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]] = (),
    candidate_semantic_atoms: Sequence[str] = (),
    relation_problems: Mapping[str, Mapping[str, Any]] | None = None,
    registry: Mapping[str, Any] | None = None,
    registry_query: Mapping[str, Any] | None = None,
    registry_authority_receipt: Mapping[str, Any] | None = None,
    registry_authority_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    source_semantics_completeness_receipt: Mapping[str, Any] | None = None,
    source_semantics_completeness_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Resolve only the strongest domain mapping justified by existing proof kernels.

    Candidate concepts and relation problems are proposals. Relation authority
    comes only from semantic_relation_control_v1. Evidence contracts can refute a
    candidate or keep it viable; they never by themselves mint exact synonymy.

    fully_semantically_bound additionally requires an independent source-semantics
    completeness certificate bound to the exact raw span bytes.
    """
    try:
        if not isinstance(raw_span, str) or not raw_span.strip():
            raise DomainMappingError("RAW_SPAN_REQUIRED")
        if not isinstance(source_id, str) or not source_id.strip():
            raise DomainMappingError("SOURCE_ID_REQUIRED")
        if not isinstance(scope_id, str) or not scope_id.strip():
            raise DomainMappingError("SCOPE_ID_REQUIRED")
        source_id = source_id.strip()
        scope_id = scope_id.strip()

        candidates = _candidate_rows(candidate_concepts)
        evidence_by_atom = _evidence_index(evidence)

        candidate_atoms: list[str] = []
        for atom in candidate_semantic_atoms:
            if not isinstance(atom, str) or not atom.strip():
                raise DomainMappingError("CANDIDATE_SEMANTIC_ATOM_INVALID")
            value = atom.strip()
            if value not in candidate_atoms:
                candidate_atoms.append(value)

        registry_result = None
        registry_allowed: set[str] | None = None
        if registry is not None:
            registry_result = concept_universe.resolve(
                registry,
                deepcopy(dict(registry_query or {"surface": raw_span})),
                authority_receipt=registry_authority_receipt,
                authority_verifier=registry_authority_verifier,
            )
            registry_allowed = set(registry_result.get("candidate_concept_ids") or [])
            if registry_result.get("status") == "FAIL_CLOSED":
                return _base(
                    "FAIL_CLOSED__REGISTRY_INVALID",
                    reason=registry_result.get("reason"),
                    registry_result=registry_result,
                )

        relation_map = relation_problems or {}
        if not isinstance(relation_map, Mapping):
            raise DomainMappingError("RELATION_PROBLEMS_INVALID")

        evaluated: list[dict[str, Any]] = []
        verified: list[dict[str, Any]] = []
        viable: list[str] = []
        rejected: list[dict[str, Any]] = []

        mention_id = "MENTION:" + sha256(
            (source_id + "\n" + scope_id + "\n" + raw_span).encode("utf-8")
        ).hexdigest()

        for candidate in candidates:
            cid = candidate["concept_id"]
            if registry_allowed is not None and cid not in registry_allowed:
                rejected.append({
                    "concept_id": cid,
                    "reason": "OUTSIDE_SURVIVING_AUTHENTICATED_REGISTRY_CANDIDATES",
                })
                continue

            contract = _evaluate_contract(candidate, evidence_by_atom)

            # Evidence rows in V1 are proposal-side diagnostics only. They may
            # highlight a possible contradiction, but they cannot delete an
            # authenticated-registry candidate or mint semantic truth.
            relation_problem = relation_map.get(cid)
            relation_result = None
            if relation_problem is not None:
                if not isinstance(relation_problem, Mapping):
                    raise DomainMappingError("RELATION_PROBLEM_NOT_OBJECT:" + cid)
                problem = deepcopy(dict(relation_problem))
                problem.setdefault("left_id", mention_id)
                problem.setdefault("left_surface", raw_span)
                problem.setdefault("right_id", cid)
                problem.setdefault("right_surface", str(candidate.get("surface") or cid))
                problem.setdefault("scope_id", scope_id)
                problem.setdefault("required_relation", "LOGICAL_EQUIVALENCE_IN_SCOPE")
                if problem["left_id"] != mention_id:
                    raise DomainMappingError("RELATION_LEFT_ID_MUST_BIND_RAW_MENTION:" + cid)
                if str(problem.get("right_id") or "") != cid:
                    raise DomainMappingError("RELATION_RIGHT_ID_MISMATCH:" + cid)
                if str(problem.get("scope_id") or "") != scope_id:
                    raise DomainMappingError("RELATION_SCOPE_MISMATCH:" + cid)
                relation_result = semantic_relation.resolve(problem)

            row = {
                "concept_id": cid,
                "contract": contract,
                "relation_result": relation_result,
            }
            evaluated.append(row)

            if isinstance(relation_result, Mapping) and relation_result.get("pass") is True:
                strongest = str(relation_result.get("strongest_proved_relation") or "")
                status = VERIFIED_RELATIONS.get(strongest)
                if status:
                    verified.append({
                        "concept_id": cid,
                        "relation": strongest,
                        "status": status,
                        "relation_result": relation_result,
                    })
                    viable.append(cid)
                    continue

            viable.append(cid)

        unique_verified = verified[0] if len(verified) == 1 else None
        completeness = _completeness_authenticated(
            raw_span=raw_span,
            source_id=source_id,
            receipt=source_semantics_completeness_receipt,
            verifier=source_semantics_completeness_verifier,
        )

        if len(verified) > 1:
            status = "UNRESOLVED__MULTIPLE_VERIFIED_RELATIONS"
        elif unique_verified is not None:
            status = unique_verified["status"]
        else:
            status = "UNRESOLVED"

        fully_bound = bool(
            unique_verified is not None
            and completeness.get("pass") is True
            and unique_verified["relation"]
            in {"SEMANTIC_IDENTITY", "LOGICAL_EQUIVALENCE_IN_SCOPE"}
        )

        semantic_authority = bool(unique_verified is not None)
        strongest_rival = None
        if unique_verified is not None:
            rivals = sorted(x for x in viable if x != unique_verified["concept_id"])
            strongest_rival = rivals[0] if rivals else None

        proved_atoms: list[str] = []
        if unique_verified is not None:
            relation_atom_payload = {
                "source_id": source_id,
                "raw_span_sha256": _raw_span_sha256(raw_span),
                "scope_id": scope_id,
                "concept_id": unique_verified["concept_id"],
                "relation": unique_verified["relation"],
            }
            material = json.dumps(
                relation_atom_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
            proved_atoms.append(
                "domain-relation-sha256:" + sha256(material).hexdigest()
            )

        next_discriminator = None
        if registry_result is not None:
            ambiguity = registry_result.get("ambiguity_decision")
            if isinstance(ambiguity, Mapping):
                next_discriminator = ambiguity.get("next_observation_id")

        return _base(
            status,
            passed=bool(unique_verified is not None),
            raw_span_sha256=_raw_span_sha256(raw_span),
            source_id=source_id,
            scope_id=scope_id,
            mention_id=mention_id,
            candidate_semantic_atoms=sorted(candidate_atoms),
            proved_semantic_atoms=proved_atoms,
            fully_semantically_bound=fully_bound,
            opaque_remainder_required=not fully_bound,
            semantic_truth_authority=semantic_authority,
            verified_mapping=deepcopy(unique_verified),
            verified_mappings=deepcopy(verified),
            surviving_candidates=sorted(set(viable)),
            rejected_candidates=rejected,
            candidate_evaluations=evaluated,
            strongest_rival=strongest_rival,
            next_discriminator=next_discriminator,
            registry_result=registry_result,
            source_semantics_completeness=completeness,
            candidate_relations_are_authority=False,
            evidence_contracts_are_authority=False,
            mapping_contracts_are_authority=False,
            boundary=(
                "V1_REUSES_EXISTING_RELATION_AUTHORITY_AND_OPTIONAL_AUTHENTICATED_FINITE_REGISTRY;"
                "GENERAL_WORD_SENSE_INFERENCE_AND_OPEN_WORLD_ONTOLOGY_COMPLETENESS_REMAIN_UNCLAIMED"
            ),
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            reason=type(exc).__name__ + ":" + str(exc),
        )
