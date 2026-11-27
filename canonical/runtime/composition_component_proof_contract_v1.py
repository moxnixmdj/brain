"""Proof-carrying semantic/scope admission for Composition component receipts.

A receipt may close a component only by exact subject/scope identity or by a
content-bound certificate already present in an independently verified
certificate authority. Merely asserting semantic entailment is not enough.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ComponentContract:
    component_id: str
    interface_id: str
    subject_id: str
    scope_id: str


@dataclass(frozen=True)
class ProofReceipt:
    proved_subject_id: str
    proved_scope_id: str
    subject_implication_certificate_id: str | None = None
    scope_inclusion_certificate_id: str | None = None
    independent_or_objective: bool = False
    current: bool = False
    contamination_clean: bool = False
    content_bound: bool = False
    preconditions_compatible: bool = False


@dataclass(frozen=True)
class VerifiedBridgeCertificate:
    certificate_id: str
    relation: str
    source_id: str
    target_id: str
    independently_verified: bool
    content_bound: bool


def _bridge_valid(
    *,
    certificate_id: str | None,
    relation: str,
    source_id: str,
    target_id: str,
    authority: Mapping[str, VerifiedBridgeCertificate],
) -> bool:
    if certificate_id is None:
        return False
    cert = authority.get(certificate_id)
    if cert is None:
        return False
    return (
        cert.certificate_id == certificate_id
        and cert.relation == relation
        and cert.source_id == source_id
        and cert.target_id == target_id
        and cert.independently_verified
        and cert.content_bound
    )


def receipt_admissible_for_contract(
    contract: ComponentContract,
    receipt: ProofReceipt,
    *,
    verified_bridge_authority: Mapping[str, VerifiedBridgeCertificate],
) -> bool:
    """Fail closed unless subject, scope, and evidence admissibility all bind."""
    subject_ok = receipt.proved_subject_id == contract.subject_id or _bridge_valid(
        certificate_id=receipt.subject_implication_certificate_id,
        relation="SUBJECT_IMPLIES",
        source_id=receipt.proved_subject_id,
        target_id=contract.subject_id,
        authority=verified_bridge_authority,
    )
    scope_ok = receipt.proved_scope_id == contract.scope_id or _bridge_valid(
        certificate_id=receipt.scope_inclusion_certificate_id,
        relation="SCOPE_COVERS",
        source_id=receipt.proved_scope_id,
        target_id=contract.scope_id,
        authority=verified_bridge_authority,
    )

    evidence_ok = all(
        (
            receipt.independent_or_objective,
            receipt.current,
            receipt.contamination_clean,
            receipt.content_bound,
            receipt.preconditions_compatible,
        )
    )
    return subject_ok and scope_ok and evidence_ok
