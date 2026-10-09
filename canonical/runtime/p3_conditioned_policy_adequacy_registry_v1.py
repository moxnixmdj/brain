"""Fail-closed registry for condition-bound authenticated P3 policy adequacy cells.

This registry complements, and does not replace, the R2 raw-source
self-authenticating adequacy registry. Entries here are useful only after an
upstream authority has already introduced the exact condition atom into the
current decision basis.

Presence in this registry never proves a condition true. P3 still evaluates
all surviving models, so false-condition worlds remain uncovered unless an
accepted source-backed refinement proves the membership condition.

Four narrow proof-carrying refinements are supported for the typed acceptance
specialist:
1. exact model structure may prove the supported-transform atom;
2. a content-addressed independently verified pre-verifier information-boundary
   receipt may prove the no-hidden-verifier-access atom for those exact model bytes;
3. a content-addressed producer-independent dependency/provenance audit may prove
   the dependency/provenance-truth atom for those exact model bytes; and
4. one lossless-source/model coverage audit may prove both typed-semantics-bound
   and failure-mode-completeness for the exact source contract and model bytes.

None of these routes proves whole policy membership by itself.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import (
    ATOM_ID as SUPPORTED_TRANSFORM_ATOM_ID,
    verify as verify_supported_transform_atom,
)
from canonical.runtime.cursorbench_typed_acceptance_information_boundary_atom_v1 import (
    ATOM_ID as NO_HIDDEN_VERIFIER_ATOM_ID,
    verify as verify_information_boundary_atom,
)
from canonical.runtime.cursorbench_typed_acceptance_dependency_provenance_atom_v1 import (
    ATOM_ID as DEPENDENCY_PROVENANCE_ATOM_ID,
    verify as verify_dependency_provenance_atom,
)
from canonical.runtime.cursorbench_typed_acceptance_source_coverage_atoms_v1 import (
    PROVED_ATOM_IDS as SOURCE_COVERAGE_ATOM_IDS,
    verify as verify_source_coverage_atoms,
)

SCHEMA = "PROJECT_BRAIN_P3_CONDITIONED_POLICY_ADEQUACY_REGISTRY_V1"
ROOT = Path(__file__).resolve().parents[2]

_REGISTRY = {
    "SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1": {
        "condition": {
            "op": "ATOM",
            "id": "SYNTHESIS_TYPED_VISIBLE_SUPPORT_COMMON_POLICY_TOP_LAW_V1",
        },
        "binding_path": (
            "canonical/governance/"
            "SYNTHESIS_VISIBLE_SUPPORT_POLICY_ADEQUACY_BINDING_20261007_V1.json"
        ),
        "binding_blob_sha": "7d2322ff8205e98752c4cd2674215f93c145305c",
    },
    "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1": {
        "condition": {
            "op": "AND",
            "args": [
                {"op": "ATOM", "id": "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1"},
                {"op": "ATOM", "id": "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1"},
                {"op": "ATOM", "id": "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1"},
                {"op": "ATOM", "id": "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1"},
                {"op": "ATOM", "id": "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1"},
            ],
        },
        "binding_path": (
            "canonical/governance/"
            "CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_BINDING_20261009_V1.json"
        ),
        "binding_blob_sha": "f385b555064e546e90c04c285053c9717014fa8a",
    },
    "BRAIN_FINITE_CANDIDATE_EXACT_ORACLE_SOLVER_V1": {
        "condition": {
            "op": "AND",
            "args": [
                {"op": "ATOM", "id": "CODING_FINITE_SOLVER_CANDIDATE_SET_FINITE_V1"},
                {"op": "ATOM", "id": "CODING_FINITE_SOLVER_ORACLE_TOTAL_V1"},
                {"op": "ATOM", "id": "CODING_FINITE_SOLVER_ORACLE_SOUND_COMPLETE_V1"},
                {"op": "ATOM", "id": "CODING_FINITE_SOLVER_VALID_MEMBER_EXISTS_V1"},
                {"op": "ATOM", "id": "CODING_FINITE_SOLVER_CALL_BUDGET_SUFFICIENT_V1"},
                {"op": "ATOM", "id": "CODING_FINITE_SOLVER_ORACLE_PRETERMINAL_ADMISSIBLE_V1"},
            ],
        },
        "binding_path": (
            "canonical/governance/"
            "CODING_FINITE_EXACT_ORACLE_POLICY_ADEQUACY_BINDING_20261009_V1.json"
        ),
        "binding_blob_sha": "25a8c91580a9d2409b30806f4eae4b77e31dab65",
    }
,
    "BRAIN_ROBUST_FINITE_MULTI_INTERPRETATION_SOLVER_V1": {
        "condition": {
            "op": "AND",
            "args": [
                {"op": "ATOM", "id": "CODING_ROBUST_FINITE_CANDIDATE_SET_FINITE_V1"},
                {"op": "ATOM", "id": "CODING_ROBUST_FINITE_INTERPRETATION_SET_SOUND_COMPLETE_V1"},
                {"op": "ATOM", "id": "CODING_ROBUST_FINITE_ORACLE_TOTAL_V1"},
                {"op": "ATOM", "id": "CODING_ROBUST_FINITE_ORACLE_SOUND_COMPLETE_PER_INTERPRETATION_V1"},
                {"op": "ATOM", "id": "CODING_ROBUST_FINITE_COMMON_VALID_MEMBER_EXISTS_V1"},
                {"op": "ATOM", "id": "CODING_ROBUST_FINITE_CALL_BUDGET_SUFFICIENT_V1"},
                {"op": "ATOM", "id": "CODING_ROBUST_FINITE_ORACLE_PRETERMINAL_ADMISSIBLE_V1"},
            ],
        },
        "binding_path": (
            "canonical/governance/"
            "CODING_ROBUST_FINITE_MULTI_INTERPRETATION_POLICY_ADEQUACY_BINDING_20261009_V1.json"
        ),
        "binding_blob_sha": "d0b7f819e38d10009082cc695976ad00b6ab6228",
    },
    "BRAIN_VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_V1": {
        "condition": {
            "op": "AND",
            "args": [
                {"op": "ATOM", "id": "CODING_VISIBLE_ACCEPTANCE_CONTRACT_FINITE_V1"},
                {"op": "ATOM", "id": "CODING_VISIBLE_ACCEPTANCE_CHECKERS_TOTAL_V1"},
                {"op": "ATOM", "id": "CODING_VISIBLE_ACCEPTANCE_CONJUNCTION_SOUND_COMPLETE_V1"},
                {"op": "ATOM", "id": "CODING_VISIBLE_ACCEPTANCE_SOURCE_AUTHORIZED_V1"},
                {"op": "ATOM", "id": "CODING_VISIBLE_ACCEPTANCE_BUILDER_INDEPENDENT_V1"},
                {"op": "ATOM", "id": "CODING_VISIBLE_ACCEPTANCE_CHECK_BUDGET_SUFFICIENT_V1"},
                {"op": "ATOM", "id": "CODING_VISIBLE_ACCEPTANCE_PRETERMINAL_ADMISSIBLE_V1"},
            ],
        },
        "binding_path": (
            "canonical/governance/"
            "CODING_VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_POLICY_ADEQUACY_BINDING_20261009_V1.json"
        ),
        "binding_blob_sha": "c8a1fff64da2bff4e8972c71c040b1920271fee6",
    }

}

_BINDING_KEYS = (
    "adequacy_certificate_path",
    "adequacy_certificate_blob_sha",
    "independent_verification_path",
    "independent_verification_blob_sha",
)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


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


def _binding_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value.get(key) for key in _BINDING_KEYS}


def _safe_bound_file(rel: str, *, root: Path) -> tuple[Path | None, str | None]:
    p = Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        return None, "REGISTERED_BINDING_PATH_INVALID:" + rel
    if not rel.startswith("canonical/governance/"):
        return None, "REGISTERED_BINDING_PATH_OUTSIDE_ALLOWED_SCOPE:" + rel

    base = root.resolve(strict=True)
    path = base / p
    for part in [path, *path.parents]:
        if part == base:
            continue
        try:
            if part.is_symlink():
                return None, "REGISTERED_BINDING_SYMLINK_FORBIDDEN:" + rel
        except OSError:
            return None, "REGISTERED_BINDING_PATH_INSPECTION_FAILED:" + rel

    resolved = path.resolve(strict=False)
    allowed = (base / "canonical/governance").resolve(strict=False)
    if not resolved.is_relative_to(allowed):
        return None, "REGISTERED_BINDING_RESOLVED_PATH_OUTSIDE_ALLOWED_SCOPE:" + rel
    if not path.is_file():
        return None, "REGISTERED_BINDING_MISSING:" + rel
    return path, None


def _load_registered_binding(
    policy_id: str,
    entry: Mapping[str, Any],
    *,
    root: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    rel = str(entry["binding_path"])
    path, path_error = _safe_bound_file(rel, root=root)
    if path_error is not None or path is None:
        return None, path_error

    actual = _git_blob_sha(path)
    if actual != entry["binding_blob_sha"]:
        return None, "REGISTERED_BINDING_DRIFT:" + rel + ":" + actual
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, "REGISTERED_BINDING_JSON_INVALID:" + type(exc).__name__
    if not isinstance(value, Mapping):
        return None, "REGISTERED_BINDING_NOT_OBJECT"
    if value.get("schema") != "PROJECT_BRAIN_POLICY_ADEQUACY_BINDING_V1":
        return None, "REGISTERED_BINDING_SCHEMA_INVALID:" + policy_id
    if value.get("policy_id") != policy_id:
        return None, "REGISTERED_BINDING_POLICY_ID_MISMATCH:" + policy_id
    if value.get("policy_condition") != entry["condition"]:
        return None, "REGISTERED_BINDING_CONDITION_MISMATCH:" + policy_id
    projected = _binding_projection(value)
    if any(
        not isinstance(projected[key], str) or not projected[key]
        for key in _BINDING_KEYS
    ):
        return None, "REGISTERED_BINDING_FIELDS_INVALID:" + policy_id
    return projected, None


def _condition_atoms(condition: Mapping[str, Any]) -> set[str]:
    op = condition.get("op")
    if op == "ATOM":
        atom = condition.get("id")
        return {atom} if isinstance(atom, str) and atom else set()
    if op == "NOT" and isinstance(condition.get("arg"), Mapping):
        return _condition_atoms(condition["arg"])
    atoms: set[str] = set()
    rows = condition.get("args")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, Mapping):
                atoms.update(_condition_atoms(row))
    for key in ("if", "then"):
        row = condition.get(key)
        if isinstance(row, Mapping):
            atoms.update(_condition_atoms(row))
    return atoms


def augment_problem(
    problem: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_MAPPING_REQUIRED")
    working = deepcopy(dict(problem))
    basis = working.get("decision_basis")
    if (
        not isinstance(basis, list)
        or not basis
        or any(not isinstance(x, str) or not x for x in basis)
        or len(set(basis)) != len(basis)
    ):
        return _fail("DECISION_BASIS_INVALID")

    root = Path(repo_root) if repo_root is not None else ROOT
    structural_atom_proofs: list[dict[str, Any]] = []
    information_boundary_atom_proofs: list[dict[str, Any]] = []
    dependency_provenance_atom_proofs: list[dict[str, Any]] = []
    source_coverage_atom_proofs: list[dict[str, Any]] = []
    typed_model = working.get("typed_acceptance_model")
    if typed_model is not None:
        proof = verify_supported_transform_atom(typed_model)
        structural_atom_proofs.append(deepcopy(proof))
        if proof.get("pass") is True and proof.get("atom_truth_authorized") is True:
            atom = {"op": "ATOM", "id": SUPPORTED_TRANSFORM_ATOM_ID}
            basis = list(basis)
            if SUPPORTED_TRANSFORM_ATOM_ID not in basis:
                basis.append(SUPPORTED_TRANSFORM_ATOM_ID)
            working["decision_basis"] = basis
            for key in ("formal_source_constraints", "proposed_refinements"):
                rows = working.get(key, [])
                if not isinstance(rows, list):
                    return _fail(
                        "STRUCTURAL_ATOM_REFINEMENT_TARGET_NOT_LIST",
                        field=key,
                    )
                rows = deepcopy(rows)
                if atom not in rows:
                    rows.append(deepcopy(atom))
                working[key] = rows

    information_boundary_binding = working.get(
        "typed_acceptance_information_boundary_binding"
    )
    if information_boundary_binding is not None:
        if typed_model is None:
            return _fail(
                "INFORMATION_BOUNDARY_BINDING_REQUIRES_TYPED_ACCEPTANCE_MODEL"
            )
        proof = verify_information_boundary_atom(
            typed_model,
            information_boundary_binding,
            repo_root=root,
        )
        information_boundary_atom_proofs.append(deepcopy(proof))
        if proof.get("pass") is not True or proof.get("atom_truth_authorized") is not True:
            return _fail(
                "INFORMATION_BOUNDARY_ATOM_BINDING_INVALID",
                information_boundary_atom_proof=proof,
            )
        atom = {"op": "ATOM", "id": NO_HIDDEN_VERIFIER_ATOM_ID}
        basis = list(basis)
        if NO_HIDDEN_VERIFIER_ATOM_ID not in basis:
            basis.append(NO_HIDDEN_VERIFIER_ATOM_ID)
        working["decision_basis"] = basis
        for key in ("formal_source_constraints", "proposed_refinements"):
            rows = working.get(key, [])
            if not isinstance(rows, list):
                return _fail(
                    "INFORMATION_BOUNDARY_REFINEMENT_TARGET_NOT_LIST",
                    field=key,
                )
            rows = deepcopy(rows)
            if atom not in rows:
                rows.append(deepcopy(atom))
            working[key] = rows

    dependency_provenance_binding = working.get(
        "typed_acceptance_dependency_provenance_binding"
    )
    if dependency_provenance_binding is not None:
        if typed_model is None:
            return _fail(
                "DEPENDENCY_PROVENANCE_BINDING_REQUIRES_TYPED_ACCEPTANCE_MODEL"
            )
        proof = verify_dependency_provenance_atom(
            typed_model,
            dependency_provenance_binding,
            repo_root=root,
        )
        dependency_provenance_atom_proofs.append(deepcopy(proof))
        if proof.get("pass") is not True or proof.get("atom_truth_authorized") is not True:
            return _fail(
                "DEPENDENCY_PROVENANCE_ATOM_BINDING_INVALID",
                dependency_provenance_atom_proof=proof,
            )
        atom = {"op": "ATOM", "id": DEPENDENCY_PROVENANCE_ATOM_ID}
        basis = list(basis)
        if DEPENDENCY_PROVENANCE_ATOM_ID not in basis:
            basis.append(DEPENDENCY_PROVENANCE_ATOM_ID)
        working["decision_basis"] = basis
        for key in ("formal_source_constraints", "proposed_refinements"):
            rows = working.get(key, [])
            if not isinstance(rows, list):
                return _fail(
                    "DEPENDENCY_PROVENANCE_REFINEMENT_TARGET_NOT_LIST",
                    field=key,
                )
            rows = deepcopy(rows)
            if atom not in rows:
                rows.append(deepcopy(atom))
            working[key] = rows

    source_coverage_binding = working.get(
        "typed_acceptance_source_coverage_binding"
    )
    if source_coverage_binding is not None:
        if typed_model is None:
            return _fail(
                "SOURCE_COVERAGE_BINDING_REQUIRES_TYPED_ACCEPTANCE_MODEL"
            )
        proof = verify_source_coverage_atoms(
            typed_model,
            source_coverage_binding,
            repo_root=root,
        )
        source_coverage_atom_proofs.append(deepcopy(proof))
        if proof.get("pass") is not True or proof.get("atom_truth_authorized") is not True:
            return _fail(
                "SOURCE_COVERAGE_ATOMS_BINDING_INVALID",
                source_coverage_atom_proof=proof,
            )
        basis = list(basis)
        for atom_id in SOURCE_COVERAGE_ATOM_IDS:
            atom = {"op": "ATOM", "id": atom_id}
            if atom_id not in basis:
                basis.append(atom_id)
            for key in ("formal_source_constraints", "proposed_refinements"):
                rows = working.get(key, [])
                if not isinstance(rows, list):
                    return _fail(
                        "SOURCE_COVERAGE_REFINEMENT_TARGET_NOT_LIST",
                        field=key,
                    )
                rows = deepcopy(rows)
                if atom not in rows:
                    rows.append(deepcopy(atom))
                working[key] = rows
        working["decision_basis"] = basis

    policies = working.get("policy_conditions", {})
    bindings = working.get("policy_adequacy_bindings", {})
    if not isinstance(policies, Mapping):
        return _fail("POLICY_CONDITIONS_NOT_MAPPING")
    if not isinstance(bindings, Mapping):
        return _fail("POLICY_ADEQUACY_BINDINGS_NOT_MAPPING")

    augmented = deepcopy(working)
    out_policies = deepcopy(dict(policies))
    out_bindings = deepcopy(dict(bindings))
    basis_set = set(basis)
    injected: list[str] = []
    reused: list[str] = []
    skipped: list[dict[str, Any]] = []

    for policy_id, entry in sorted(_REGISTRY.items()):
        condition = deepcopy(entry["condition"])
        missing = sorted(_condition_atoms(condition) - basis_set)
        if missing:
            skipped.append(
                {
                    "policy_id": policy_id,
                    "reason": "CONDITION_ATOMS_OUTSIDE_DECISION_BASIS",
                    "missing_atoms": missing,
                }
            )
            continue

        registered_binding, error = _load_registered_binding(
            policy_id, entry, root=root
        )
        if error is not None or registered_binding is None:
            return _fail(
                "REGISTERED_POLICY_ADEQUACY_BINDING_INVALID",
                policy_id=policy_id,
                binding_error=error,
            )

        existing_condition = out_policies.get(policy_id)
        if existing_condition is not None and existing_condition != condition:
            return _fail(
                "CALLER_POLICY_CONDITION_CONFLICTS_WITH_REGISTERED_ADEQUACY",
                policy_id=policy_id,
            )

        existing_binding = out_bindings.get(policy_id)
        if existing_binding is not None:
            if not isinstance(existing_binding, Mapping):
                return _fail("CALLER_POLICY_BINDING_INVALID", policy_id=policy_id)
            if _binding_projection(existing_binding) != registered_binding:
                return _fail(
                    "CALLER_POLICY_BINDING_CONFLICTS_WITH_REGISTERED_ADEQUACY",
                    policy_id=policy_id,
                )
            reused.append(policy_id)
        else:
            out_bindings[policy_id] = registered_binding
            if existing_condition is None:
                injected.append(policy_id)
            else:
                reused.append(policy_id)

        out_policies[policy_id] = condition

    augmented["policy_conditions"] = out_policies
    augmented["policy_adequacy_bindings"] = out_bindings
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": (
            "PASS__CONDITIONED_REGISTERED_ADEQUACY_REUSED_WITHOUT_"
            "MEMBERSHIP_SELF_CERTIFICATION"
        ),
        "problem": augmented,
        "registered_policy_count": len(_REGISTRY),
        "structural_atom_proofs": structural_atom_proofs,
        "structurally_proved_atom_ids": sorted({
            str(row.get("atom_id"))
            for row in structural_atom_proofs
            if row.get("pass") is True and row.get("atom_truth_authorized") is True
        }),
        "information_boundary_atom_proofs": information_boundary_atom_proofs,
        "information_boundary_proved_atom_ids": sorted({
            str(row.get("atom_id"))
            for row in information_boundary_atom_proofs
            if row.get("pass") is True and row.get("atom_truth_authorized") is True
        }),
        "dependency_provenance_atom_proofs": dependency_provenance_atom_proofs,
        "dependency_provenance_proved_atom_ids": sorted({
            str(row.get("atom_id"))
            for row in dependency_provenance_atom_proofs
            if row.get("pass") is True and row.get("atom_truth_authorized") is True
        }),
        "source_coverage_atom_proofs": source_coverage_atom_proofs,
        "source_coverage_proved_atom_ids": sorted({
            str(atom_id)
            for row in source_coverage_atom_proofs
            if row.get("pass") is True and row.get("atom_truth_authorized") is True
            for atom_id in (row.get("proved_atom_ids") or [])
        }),
        "proved_condition_atom_ids": sorted({
            str(atom_id)
            for row in [
                *structural_atom_proofs,
                *information_boundary_atom_proofs,
                *dependency_provenance_atom_proofs,
            ]
            if row.get("pass") is True and row.get("atom_truth_authorized") is True
            for atom_id in ([row.get("atom_id")] if row.get("atom_id") else [])
        } | {
            str(atom_id)
            for row in source_coverage_atom_proofs
            if row.get("pass") is True and row.get("atom_truth_authorized") is True
            for atom_id in (row.get("proved_atom_ids") or [])
        }),
        "basis_eligible_policy_count": len(injected) + len(reused),
        "injected_policy_ids": injected,
        "reused_policy_ids": reused,
        "skipped_registered_policies": skipped,
        "registry_authority": False,
        "membership_self_certified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "COMPLEMENTS_R2_SELF_AUTHENTICATING_RAW_SOURCE_REGISTRY;"
            "SEMANTIC_CONDITION_ATOMS_MUST_ALREADY_EXIST_IN_DECISION_BASIS;"
            "ONLY_THE_EXACT_SUPPORTED_TRANSFORM_STRUCTURAL_ATOM_MAY_BE_RECOMPUTED;"
            "THE_NO_HIDDEN_VERIFIER_ATOM_REQUIRES_A_CONTENT_ADDRESSED_INDEPENDENT_"
            "PREVERIFIER_INFORMATION_BOUNDARY_RECEIPT;"
            "THE_DEPENDENCY_PROVENANCE_ATOM_REQUIRES_A_CONTENT_ADDRESSED_PRODUCER_"
            "INDEPENDENT_DEPENDENCY_PROVENANCE_AUDIT;"
            "THE_TYPED_SEMANTICS_AND_FAILURE_COMPLETENESS_ATOMS_REQUIRE_ONE_"
            "CONTENT_ADDRESSED_INDEPENDENT_LOSSLESS_SOURCE_TO_MODEL_COVERAGE_AUDIT;"
            "REGISTRY_NEVER_PROVES_OTHER_CONDITION_TRUTH;"
            "P3_STILL_REQUIRES_SOURCE_AUTHORIZED_REFINEMENT_TO_REMOVE_FALSE_WORLDS"
        ),
    }


def catalog() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "CONDITIONED_POLICY_ADEQUACY_REGISTRY_CATALOG",
        "policy_count": len(_REGISTRY),
        "policies": [
            {
                "policy_id": policy_id,
                "condition": deepcopy(entry["condition"]),
                "binding_path": entry["binding_path"],
                "binding_blob_sha": entry["binding_blob_sha"],
            }
            for policy_id, entry in sorted(_REGISTRY.items())
        ],
        "membership_self_certified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
