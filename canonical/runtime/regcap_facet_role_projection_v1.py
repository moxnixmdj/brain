"""Typed facet-role projection for already-proved regulatory-capital context.

This module does not parse a second time and does not classify concepts. It
reuses source_aligned_regcap_context_proof_v1, then projects proved semantic atoms
onto a Brain-owned facet-role IR.

A clause may carry multiple facet roles. V1 therefore never claims that the
source mention refers to exactly one facet.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import source_aligned_regcap_context_proof_v1 as context

SCHEMA = "PROJECT_BRAIN_REGCAP_FACET_ROLE_PROJECTION_V1"

ROLE_QUANTIFIED_LEVEL = "FACET_ROLE::QUANTIFIED_LEVEL"
ROLE_COMPOSITION = "FACET_ROLE::COMPOSITION"
ROLE_POSITION = "FACET_ROLE::POSITION"
ROLE_FUNCTION = "FACET_ROLE::FUNCTION_OR_CAPACITY"
ROLE_REGIME = "FACET_ROLE::REGIME"
ROLE_SUBJECT_SCOPE = "FACET_ROLE::SUBJECT_SCOPE"
ROLE_TRANSITION = "FACET_ROLE::STATE_TRANSITION_OR_TRIGGER"

ATOM_TO_ROLE = {
    context.ATOM_2_5: ROLE_QUANTIFIED_LEVEL,
    context.ATOM_CET1: ROLE_COMPOSITION,
    context.ATOM_ABOVE_MIN: ROLE_POSITION,
    context.ATOM_RELEASE: ROLE_TRANSITION,
    context.ATOM_LOSS: ROLE_FUNCTION,
    context.ATOM_RECAP: ROLE_FUNCTION,
    context.ATOM_RESOLUTION: ROLE_REGIME,
    context.ATOM_GSIB: ROLE_SUBJECT_SCOPE,
}

KNOWN_ROLES = frozenset(ATOM_TO_ROLE.values())
KNOWN_CONTEXT_KINDS = {
    context.CCOB_KIND,
    context.CCYB_KIND,
    context.TLAC_KIND,
}


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "facet_role_authority": False,
        "single_facet_reference_authority": False,
        "concept_identity_authority": False,
        "global_identity_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def project(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    context_kind: str,
) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text:
        return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
    if not isinstance(source_id, str) or not source_id.strip():
        return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")
    if context_kind not in KNOWN_CONTEXT_KINDS:
        return _base("FAIL_CLOSED", reason="CONTEXT_KIND_INVALID")

    claim = {
        "claim_id": "facet-role-source",
        "kind": context_kind,
        "start": start,
        "end": end,
    }
    proof = context.verify_proof(
        source_text,
        source_id=source_id,
        claims=[claim],
    )
    if proof.get("status") == "FAIL_CLOSED":
        return _base(
            "FAIL_CLOSED",
            reason="REGCAP_CONTEXT_PROOF_FAIL_CLOSED",
            context_proof=proof,
        )

    accepted = [
        row
        for row in (proof.get("accepted_claims") or [])
        if isinstance(row, Mapping)
        and row.get("claim_id") == "facet-role-source"
    ]
    if len(accepted) != 1:
        return _base(
            "UNRESOLVED__BOUND_CONTEXT_NOT_CERTIFIED",
            context_proof=proof,
        )

    row = accepted[0]
    atoms = [
        str(atom)
        for atom in (row.get("proved_atom_ids") or [])
        if isinstance(atom, str)
    ]
    roles = sorted({ATOM_TO_ROLE[a] for a in atoms if a in ATOM_TO_ROLE})
    if not roles:
        return _base(
            "UNRESOLVED__NO_FACET_ROLE_FOR_PROVED_ATOMS",
            context_proof=proof,
            proved_atom_ids=atoms,
        )

    support = {
        role: sorted(a for a in atoms if ATOM_TO_ROLE.get(a) == role)
        for role in roles
    }
    material = {
        "source_id": source_id.strip(),
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "source_span": [start, end],
        "context_kind": context_kind,
        "proved_atom_ids": atoms,
        "facet_roles": roles,
    }
    projection_sha = sha256(
        json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    return _base(
        "PASS__REGCAP_FACET_ROLES_PROJECTED",
        passed=True,
        semantic_truth_authority=True,
        facet_role_authority=True,
        source_id=source_id.strip(),
        source_span=[start, end],
        context_kind=context_kind,
        proved_atom_ids=atoms,
        facet_roles=roles,
        facet_role_support=support,
        frame_level_projection=len(roles) > 1,
        projection_sha256=projection_sha,
        context_proof=proof,
        single_facet_reference_authority=False,
        concept_identity_authority=False,
        boundary=(
            "TYPED_ROLE_PROJECTION_OVER_ALREADY_PROVED_REGCAP_ATOMS_ONLY__"
            "MULTIPLE_ROLES_ARE_PRESERVED__NO_SINGLE_FACET_REFERENCE_CLAIM__"
            "NO_CONCEPT_IDENTITY_OR_TERMINAL_AUTHORITY"
        ),
    )
