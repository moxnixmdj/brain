"""Four-concept regulatory-capital property-driven candidate discovery V2.

V1 queried only CCoB, CCyB, and TLAC. V2 adds independently authenticated
MREL necessary-property authority without changing the epistemic boundary:
necessary-property matching generates candidates only and never proves concept
identity. The returned set is complete only relative to the four explicitly
queried bound concepts, not the open-world regulatory-capital ontology.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel

SCHEMA = "PROJECT_BRAIN_REGCAP_PROPERTY_CANDIDATE_DISCOVERY_V2"
REQUEST_SCHEMA = "PROJECT_BRAIN_REGCAP_PROPERTY_CANDIDATE_DISCOVERY_REQUEST_V2"
SCOPE_ID = "REGCAP_CCOB_CCYB_TLAC_PLUS_EU_MREL_BOUND_INVENTORY_2026_V2"

BOUND_CONCEPTS = (regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL)


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "candidate_generation_authority": False,
        "semantic_identity_authority": False,
        "semantic_truth_authority": False,
        "candidate_set_complete_relative_to_bound_inventory": False,
        "open_world_candidate_set_complete": False,
        "absence_means_refuted": False,
        "unique_identity_authorized": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _authority_for(concept_id: str):
    if concept_id == mrel.MREL:
        return mrel, mrel.SCOPE_ID
    return regcap, regcap.SCOPE_ID


def _positive_targets(concept_id: str, queried_property: str) -> list[str]:
    authority, _ = _authority_for(concept_id)
    return sorted({
        prop
        for concept, prop in authority.RULES
        if concept == concept_id and prop != queried_property
    })


def discover(
    request: Mapping[str, Any],
    *,
    repo_root: Any = None,
) -> dict[str, Any]:
    try:
        if not isinstance(request, Mapping) or request.get("schema") != REQUEST_SCHEMA:
            return _base("FAIL_CLOSED", reason="REQUEST_SCHEMA_INVALID")
        allowed = {"schema", "scope_id", "property_id"}
        extra = set(request) - allowed
        if extra:
            return _base(
                "FAIL_CLOSED",
                reason="UNMODELED_REQUEST_FIELDS:"
                + ",".join(sorted(str(x) for x in extra)),
            )

        scope_id = str(request.get("scope_id") or "").strip()
        property_id = str(request.get("property_id") or "").strip()
        if scope_id != SCOPE_ID:
            return _base("FAIL_CLOSED", reason="SCOPE_ID_MISMATCH")
        if not property_id:
            return _base("FAIL_CLOSED", reason="PROPERTY_ID_REQUIRED")

        candidates = []
        unknown = []
        failures = []

        for concept_id in BOUND_CONCEPTS:
            authority, authority_scope_id = _authority_for(concept_id)
            result = authority.verify_property_request(
                {
                    "schema": authority.REQUEST_SCHEMA,
                    "scope_id": authority_scope_id,
                    "concept_id": concept_id,
                    "property_id": property_id,
                },
                repo_root=repo_root,
            )
            if result.get("status") == "FAIL_CLOSED":
                failures.append({
                    "concept_id": concept_id,
                    "authority_scope_id": authority_scope_id,
                    "reason": result.get("reason"),
                })
                continue
            if result.get("pass") is True:
                candidates.append({
                    "concept_id": concept_id,
                    "authority_scope_id": authority_scope_id,
                    "property_id": property_id,
                    "edge_receipt": result.get("edge_receipt"),
                    "positive_evidence_targets": _positive_targets(
                        concept_id,
                        property_id,
                    ),
                })
            else:
                unknown.append({
                    "concept_id": concept_id,
                    "authority_scope_id": authority_scope_id,
                    "status": result.get("status"),
                    "reason": result.get("reason"),
                })

        if failures:
            return _base(
                "FAIL_CLOSED",
                reason="PROPERTY_AUTHORITY_FAILURE",
                property_id=property_id,
                bound_concept_inventory=list(BOUND_CONCEPTS),
                failures=failures,
                unknown_candidates=unknown,
            )

        ids = sorted(row["concept_id"] for row in candidates)
        common = {
            "property_id": property_id,
            "bound_concept_inventory": list(BOUND_CONCEPTS),
            "unknown_candidates": unknown,
            "candidate_generation_authority": True,
            "candidate_set_complete_relative_to_bound_inventory": True,
            "open_world_candidate_set_complete": False,
            "candidate_set_generation_basis": (
                "EXHAUSTIVE_QUERY_OVER_DECLARED_FOUR_CONCEPT_BOUND_INVENTORY"
            ),
            "necessary_property_is_sufficient_for_identity": False,
            "positive_evidence_targets_are_decisive_discriminators": False,
            "positive_evidence_targets_rule": (
                "SEARCH_TARGETS_ONLY__A_PROVED_TARGET_MAY_SUPPORT_A_CANDIDATE__"
                "ABSENCE_OR_OTHER_CANDIDATE_NONLISTING_DOES_NOT_REFUTE_RIVALS"
            ),
        }

        if not ids:
            return _base(
                "OPEN__NO_VERIFIED_PROPERTY_CANDIDATES_IN_BOUND_INVENTORY",
                no_candidate_means_nonexistence=False,
                **common,
            )

        return _base(
            (
                "OPEN__NON_UNIQUE_PROPERTY_CANDIDATES"
                if len(ids) > 1
                else "OPEN__SINGLE_PROPERTY_CANDIDATE_NOT_IDENTITY"
            ),
            passed=True,
            candidate_concept_ids=ids,
            candidates=candidates,
            non_unique_property_witness=len(ids) > 1,
            boundary=(
                "FOUR_CONCEPT_BOUND_CANDIDATE_DISCOVERY_FROM_AUTHENTICATED_"
                "NECESSARY_PROPERTIES_ONLY__NO_PROPERTY_TO_CONCEPT_REVERSE_"
                "INFERENCE__NO_OPEN_WORLD_CANDIDATE_COMPLETENESS_OR_TERMINAL_AUTHORITY"
            ),
            **common,
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            reason=type(exc).__name__ + ":" + str(exc),
        )
