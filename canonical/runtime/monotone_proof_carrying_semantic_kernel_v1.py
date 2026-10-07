"""Fail-closed finite semantic refinement kernel.

The kernel starts maximally permissive over a declared finite decision basis. It may
shrink the abstract semantic state only from content-addressed, exact typed boolean
facts whose field identity is the semantic atom identity. Missing semantics therefore
remain possible instead of being guessed away.

This is deliberately a small sound core, not a natural-language semantic parser.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_MONOTONE_PROOF_CARRYING_SEMANTIC_KERNEL_V1"
PROOF_SCHEMA = "PROJECT_BRAIN_EXACT_TYPED_BOOLEAN_FACT_PROOF_V1"


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Literal:
    atom: str
    value: bool


class SemanticKernel:
    """Finite over-approximation of all still-authorized decision-basis valuations."""

    def __init__(self, basis: Sequence[str], *, max_atoms: int = 16):
        atoms = tuple(str(x).strip() for x in basis)
        if not atoms or any(not x for x in atoms):
            raise ValueError("DECISION_BASIS_EMPTY_OR_INVALID")
        if len(set(atoms)) != len(atoms):
            raise ValueError("DECISION_BASIS_DUPLICATE")
        if len(atoms) > max_atoms:
            raise ValueError("DECISION_BASIS_EXCEEDS_FINITE_KERNEL_BOUND")
        self.basis = atoms
        self._models = [
            dict(zip(atoms, values))
            for values in itertools.product((False, True), repeat=len(atoms))
        ]
        self._accepted_proofs: list[dict[str, Any]] = []

    @property
    def model_count(self) -> int:
        return len(self._models)

    @property
    def accepted_proofs(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(x) for x in self._accepted_proofs)

    def possible_values(self, atom: str) -> frozenset[bool]:
        if atom not in self.basis:
            raise KeyError(atom)
        return frozenset(bool(m[atom]) for m in self._models)

    def admit_exact_typed_boolean_fact(
        self,
        typed_semantics: Any,
        proof: Any,
    ) -> dict[str, Any]:
        """Admit one one-sided sound refinement or leave state unchanged.

        Soundness is intentionally narrow. The source must itself be an explicit
        typed semantic mapping, the semantic field must have exactly the same name
        as the decision-basis atom, its value must already be boolean, and the
        proof must content-address the complete supplied mapping.
        """
        errors: list[str] = []
        before = self.model_count

        if not isinstance(typed_semantics, Mapping):
            errors.append("TYPED_SEMANTICS_NOT_OBJECT")
            typed_semantics = {}
        if not isinstance(proof, Mapping):
            errors.append("PROOF_NOT_OBJECT")
            proof = {}

        if proof.get("schema") != PROOF_SCHEMA:
            errors.append("PROOF_SCHEMA_INVALID")

        atom = proof.get("atom")
        if not isinstance(atom, str) or atom not in self.basis:
            errors.append("ATOM_NOT_IN_DECISION_BASIS")
            atom = ""

        field = proof.get("field")
        if not isinstance(field, str) or not field:
            errors.append("FIELD_INVALID")
            field = ""

        if atom and field and field != atom:
            errors.append("FIELD_ATOM_IDENTITY_REQUIRED")

        source_sha256 = proof.get("source_sha256")
        actual_sha256 = _canonical_sha256(dict(typed_semantics))
        if source_sha256 != actual_sha256:
            errors.append("SOURCE_HASH_MISMATCH")

        if field not in typed_semantics:
            errors.append("FIELD_MISSING")
            source_value = None
        else:
            source_value = typed_semantics[field]
            if not isinstance(source_value, bool):
                errors.append("FIELD_VALUE_NOT_BOOLEAN")

        claimed_value = proof.get("value")
        if not isinstance(claimed_value, bool):
            errors.append("CLAIMED_VALUE_NOT_BOOLEAN")
        elif isinstance(source_value, bool) and claimed_value is not source_value:
            errors.append("CLAIMED_VALUE_MISMATCH")

        if errors:
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "REJECTED_FAIL_CLOSED",
                "errors": sorted(set(errors)),
                "models_before": before,
                "models_after": self.model_count,
                "state_changed": False,
            }

        assert atom
        assert isinstance(claimed_value, bool)
        self._models = [m for m in self._models if bool(m[atom]) is claimed_value]
        self._accepted_proofs.append({
            "schema": PROOF_SCHEMA,
            "atom": atom,
            "field": field,
            "value": claimed_value,
            "source_sha256": actual_sha256,
        })
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "ACCEPTED_SOUND_MONOTONE_REFINEMENT",
            "errors": [],
            "atom": atom,
            "value": claimed_value,
            "models_before": before,
            "models_after": self.model_count,
            "state_changed": self.model_count != before,
        }

    def entails(self, requirements: Sequence[Mapping[str, Any] | Literal]) -> bool:
        literals: list[Literal] = []
        for raw in requirements:
            if isinstance(raw, Literal):
                lit = raw
            elif isinstance(raw, Mapping):
                atom = raw.get("atom")
                value = raw.get("value")
                if not isinstance(atom, str) or atom not in self.basis:
                    raise ValueError("POLICY_REQUIREMENT_ATOM_INVALID")
                if not isinstance(value, bool):
                    raise ValueError("POLICY_REQUIREMENT_VALUE_INVALID")
                lit = Literal(atom, value)
            else:
                raise ValueError("POLICY_REQUIREMENT_INVALID")
            if lit.atom not in self.basis:
                raise ValueError("POLICY_REQUIREMENT_ATOM_INVALID")
            literals.append(lit)

        if not literals or not self._models:
            return False
        return all(
            all(bool(model[lit.atom]) is lit.value for lit in literals)
            for model in self._models
        )

    def select_certified_policy(
        self,
        policies: Mapping[str, Sequence[Mapping[str, Any] | Literal]],
    ) -> dict[str, Any]:
        entailed = sorted(
            policy_id
            for policy_id, requirements in policies.items()
            if self.entails(requirements)
        )
        if not entailed:
            return {
                "schema": SCHEMA,
                "status": "UNKNOWN_FAIL_CLOSED",
                "selected_policy": None,
                "entailed_policies": [],
                "model_count": self.model_count,
            }
        return {
            "schema": SCHEMA,
            "status": "CERTIFIED_POLICY_AVAILABLE",
            "selected_policy": entailed[0],
            "entailed_policies": entailed,
            "model_count": self.model_count,
        }


def make_exact_typed_boolean_fact_proof(
    typed_semantics: Mapping[str, Any],
    atom: str,
) -> dict[str, Any]:
    """Create a proof envelope for an explicit typed same-name boolean fact.

    The verifier, not this helper, decides admissibility.
    """
    value = typed_semantics.get(atom)
    return {
        "schema": PROOF_SCHEMA,
        "atom": atom,
        "field": atom,
        "value": value,
        "source_sha256": _canonical_sha256(dict(typed_semantics)),
    }
