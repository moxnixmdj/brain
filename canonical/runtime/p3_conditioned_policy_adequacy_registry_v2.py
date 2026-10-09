"""Successor wrapper for conditioned P3 adequacy admission.

V2 adds proof-carrying refinement for the two remaining externally evidenced
typed-acceptance atoms, then delegates to the independently exercised V1
registry for structural, information-boundary, provenance, and policy binding.
No caller truth booleans are accepted.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.p3_conditioned_policy_adequacy_registry_v1 import (
    augment_problem as augment_v1,
)
from canonical.runtime.cursorbench_typed_acceptance_semantics_bound_atom_v1 import (
    ATOM_ID as SEMANTICS_ATOM_ID,
    verify as verify_semantics_atom,
)
from canonical.runtime.cursorbench_typed_acceptance_failure_mode_completeness_atom_v1 import (
    ATOM_ID as COMPLETENESS_ATOM_ID,
    verify as verify_completeness_atom,
)

SCHEMA = "PROJECT_BRAIN_P3_CONDITIONED_POLICY_ADEQUACY_REGISTRY_V2"
ROOT = Path(__file__).resolve().parents[2]


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "registry_authority": False,
        "membership_self_certified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _apply(
    working: dict[str, Any],
    *,
    typed_model: Mapping[str, Any] | None,
    binding_key: str,
    atom_id: str,
    verifier,
    root: Path,
    proof_label: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    binding = working.get(binding_key)
    if binding is None:
        return working, None
    if typed_model is None:
        return None, _fail(binding_key.upper() + "_REQUIRES_TYPED_ACCEPTANCE_MODEL")

    proof = verifier(typed_model, binding, repo_root=root)
    if proof.get("pass") is not True or proof.get("atom_truth_authorized") is not True:
        return None, _fail(
            proof_label + "_ATOM_BINDING_INVALID",
            atom_proof=proof,
        )

    basis = working.get("decision_basis")
    if not isinstance(basis, list):
        return None, _fail("DECISION_BASIS_INVALID")
    basis = list(basis)
    if atom_id not in basis:
        basis.append(atom_id)
    working["decision_basis"] = basis

    atom = {"op": "ATOM", "id": atom_id}
    for key in ("formal_source_constraints", "proposed_refinements"):
        rows = working.get(key, [])
        if not isinstance(rows, list):
            return None, _fail(proof_label + "_REFINEMENT_TARGET_NOT_LIST", field=key)
        rows = deepcopy(rows)
        if atom not in rows:
            rows.append(deepcopy(atom))
        working[key] = rows
    return working, deepcopy(proof)


def augment_problem(
    problem: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_MAPPING_REQUIRED")
    working = deepcopy(dict(problem))
    root = Path(repo_root) if repo_root is not None else ROOT
    typed_model = working.get("typed_acceptance_model")
    if typed_model is not None and not isinstance(typed_model, Mapping):
        return _fail("TYPED_ACCEPTANCE_MODEL_NOT_MAPPING")

    working, semantic_proof = _apply(
        working,
        typed_model=typed_model,
        binding_key="typed_acceptance_semantics_binding",
        atom_id=SEMANTICS_ATOM_ID,
        verifier=verify_semantics_atom,
        root=root,
        proof_label="TYPED_SEMANTICS",
    )
    if working is None:
        return semantic_proof

    working, completeness_proof = _apply(
        working,
        typed_model=typed_model,
        binding_key="typed_acceptance_failure_mode_completeness_binding",
        atom_id=COMPLETENESS_ATOM_ID,
        verifier=verify_completeness_atom,
        root=root,
        proof_label="MODE_COMPLETENESS",
    )
    if working is None:
        return completeness_proof

    out = augment_v1(working, repo_root=root)
    if out.get("pass") is not True:
        return out

    extra = [
        row for row in (semantic_proof, completeness_proof)
        if isinstance(row, Mapping)
        and row.get("pass") is True
        and row.get("atom_truth_authorized") is True
    ]
    proved = set(out.get("proved_condition_atom_ids") or [])
    proved.update(str(row["atom_id"]) for row in extra)

    result = deepcopy(out)
    result["schema"] = SCHEMA
    result["status"] = (
        "PASS__V2_TYPED_ACCEPTANCE_EVIDENCE_REFINEMENTS_DELEGATED_TO_V1_REGISTRY"
    )
    result["typed_semantics_atom_proofs"] = (
        [deepcopy(semantic_proof)] if isinstance(semantic_proof, Mapping) else []
    )
    result["mode_completeness_atom_proofs"] = (
        [deepcopy(completeness_proof)] if isinstance(completeness_proof, Mapping) else []
    )
    result["proved_condition_atom_ids"] = sorted(proved)
    result["registry_authority"] = False
    result["membership_self_certified"] = False
    result["terminal_authority"] = False
    result["terminal_credit_delta"] = 0
    result["boundary_v2"] = (
        "V2_ONLY_ADDS_CONTENT_ADDRESSED_PRODUCER_INDEPENDENT_EVIDENCE_ROUTES_FOR_"
        "THE_TWO_REMAINING_TYPED_ACCEPTANCE_CONDITION_ATOMS;"
        "MISSING_BINDINGS_PROVE_NOTHING;"
        "V1_REMAINS_AUTHORITY_FOR_EXISTING_ATOMS_AND_POLICY_BINDINGS"
    )
    return result
