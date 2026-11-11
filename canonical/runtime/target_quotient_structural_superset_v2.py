from __future__ import annotations

from dataclasses import dataclass


class SupersetCertificateError(ValueError):
    pass


@dataclass(frozen=True)
class StructuralSupersetCertificate:
    target_subset_receipt_verified: bool
    superset_semantics_complete: bool
    superset_dominance_verified: bool
    condition_composition_closure_verified: bool
    resource_safety_authority_nonregression_verified: bool
    donor_independent_ownership_verified: bool

    @property
    def terminal_sufficient(self) -> bool:
        return all((
            self.target_subset_receipt_verified,
            self.superset_semantics_complete,
            self.superset_dominance_verified,
            self.condition_composition_closure_verified,
            self.resource_safety_authority_nonregression_verified,
            self.donor_independent_ownership_verified,
        ))


def certify_structural_superset(
    *,
    target_subset_receipt_verified: bool,
    superset_semantics_complete: bool,
    superset_dominance_verified: bool,
    condition_composition_closure_verified: bool,
    resource_safety_authority_nonregression_verified: bool,
    donor_independent_ownership_verified: bool,
) -> StructuralSupersetCertificate:
    values = locals()
    if any(type(v) is not bool for v in values.values()):
        raise SupersetCertificateError("BOOLEAN_PROOF_FLAGS_REQUIRED")
    return StructuralSupersetCertificate(**values)


def require_terminal_sufficient(cert: StructuralSupersetCertificate) -> str:
    if not isinstance(cert, StructuralSupersetCertificate):
        raise SupersetCertificateError("CERTIFICATE_REQUIRED")
    if not cert.terminal_sufficient:
        raise SupersetCertificateError("SUPERSET_ROUTE_PREMISE_MISSING")
    return "PASS__STRUCTURAL_SUPERSET_ROUTE_SUFFICIENT_WITHOUT_TARGET_MEMBERSHIP_ENUMERATION"
