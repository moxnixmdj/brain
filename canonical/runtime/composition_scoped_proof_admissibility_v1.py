"""Fail-closed semantic admission rule for composition component scoped proofs.

This module resolves only what counts as an admissible scoped component proof.
It grants no acceptance, family, capability, ownership, execution, or fresh-reality
authority by itself.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScopedProofEvidence:
    subject_contract_bound: bool
    subject_entails_component_obligation: bool
    scope_covers_interface: bool
    independent_or_objective: bool
    current: bool
    contamination_clean: bool
    content_bound: bool
    preconditions_compatible: bool


def admissible_component_scoped_proof(evidence: ScopedProofEvidence) -> bool:
    """Return True iff every load-bearing semantic/admissibility premise is proved."""
    return all(
        (
            evidence.subject_contract_bound,
            evidence.subject_entails_component_obligation,
            evidence.scope_covers_interface,
            evidence.independent_or_objective,
            evidence.current,
            evidence.contamination_clean,
            evidence.content_bound,
            evidence.preconditions_compatible,
        )
    )


def classify_scope_only(
    *,
    scope_complete: bool,
    subject_entails_component_obligation: bool,
) -> str:
    """Make the scope/performance distinction explicit and fail closed."""
    if scope_complete and not subject_entails_component_obligation:
        return "SCOPE_ONLY__NO_COMPONENT_CREDIT"
    if not scope_complete:
        return "SCOPE_INCOMPLETE__NO_COMPONENT_CREDIT"
    return "SUBJECT_AND_SCOPE_SEMANTICALLY_ELIGIBLE__CHECK_ADMISSIBILITY_PRECONDITIONS"


def whole_family_acceptance_is_logically_required(
    *,
    direct_component_proof_admissible: bool,
) -> bool:
    """A direct proof is a counterexample to whole-family acceptance being logically necessary.

    When no direct proof is presently admissible, this returns False as well: absence
    of one current route does not prove that whole-family acceptance is logically
    necessary. It may still be the cheapest available sufficient receipt.
    """
    _ = direct_component_proof_admissible
    return False
