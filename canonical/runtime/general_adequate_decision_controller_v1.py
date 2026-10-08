"""General adequate-decision controller V1.

One fail-closed front door for the Brain's R2 decision loop:
raw goal -> authenticated semantic decision context -> minimum policy-changing
information -> authenticated adequate policy -> grounded realization or verified
execution -> actual-goal satisfaction.

The controller never upgrades routing, provider output, or a successful effect into
semantic success. Every authority-bearing bridge is content-addressed and
independently verified. Provider callbacks are proposal/information carriers only.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.p3_real_context_v3_admission_v12 import evaluate as evaluate_p3
from canonical.runtime.universal_verified_adaptive_solver_v12 import run as run_universal
from canonical.runtime.observable_policy_cover_executor_v1 import (
    evaluate as evaluate_policy_cover,
)
from canonical.runtime.r2_authenticated_adequacy_authority_registry_v1 import (
    discover as discover_authenticated_adequacy,
)

SCHEMA = "PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_CONTROLLER_V1"
ROOT = Path(__file__).resolve().parents[2]
GOAL_BINDING_SCHEMA = "PROJECT_BRAIN_GOAL_TO_DECISION_CONTEXT_BINDING_V1"
GOAL_BINDING_VERIFY_SCHEMA = "PROJECT_BRAIN_GOAL_TO_DECISION_CONTEXT_BINDING_INDEPENDENT_VERIFICATION_V1"
PARTIAL_GOAL_BINDING_SCHEMA = "PROJECT_BRAIN_PARTIAL_GOAL_TO_DECISION_CONTEXT_BINDING_V1"
PARTIAL_GOAL_BINDING_VERIFY_SCHEMA = "PROJECT_BRAIN_PARTIAL_GOAL_TO_DECISION_CONTEXT_BINDING_INDEPENDENT_VERIFICATION_V1"
POLICY_EXECUTION_SCHEMA = "PROJECT_BRAIN_POLICY_EXECUTION_BINDING_V1"
POLICY_EXECUTION_VERIFY_SCHEMA = "PROJECT_BRAIN_POLICY_EXECUTION_BINDING_INDEPENDENT_VERIFICATION_V1"
GOAL_SATISFACTION_SCHEMA = "PROJECT_BRAIN_GOAL_SATISFACTION_BINDING_V1"
GOAL_SATISFACTION_VERIFY_SCHEMA = "PROJECT_BRAIN_GOAL_SATISFACTION_BINDING_INDEPENDENT_VERIFICATION_V1"
MAX_INFORMATION_ROUNDS = 16


class DecisionControllerError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _bound_json(
    ref: Mapping[str, Any],
    *,
    repo_root: Path,
    prefixes: tuple[str, ...],
) -> tuple[dict[str, Any], str, str]:
    if not isinstance(ref, Mapping):
        raise DecisionControllerError("BOUND_REF_REQUIRED")
    rel = str(ref.get("path") or "").strip()
    expected = str(ref.get("git_blob_sha") or "").strip()
    p = Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise DecisionControllerError("BOUND_PATH_INVALID")
    if not any(rel.startswith(prefix) for prefix in prefixes):
        raise DecisionControllerError("BOUND_PATH_OUTSIDE_ALLOWED_SCOPE")
    # The lexical prefix check above is not enough: a symlink inside an
    # allowed evidence directory can escape to a different filesystem location.
    # Evidence references must resolve to real files within the permitted scope.
    base = repo_root.resolve(strict=True)
    full = base / p
    if any(part.is_symlink() for part in [full, *full.parents] if part != base and base in part.parents):
        raise DecisionControllerError("BOUND_SYMLINK_FORBIDDEN:" + rel)
    resolved = full.resolve(strict=False)
    if not any(
        resolved.is_relative_to((base / prefix).resolve(strict=False))
        for prefix in prefixes
    ):
        raise DecisionControllerError("BOUND_RESOLVED_PATH_OUTSIDE_ALLOWED_SCOPE")
    if not full.is_file():
        raise DecisionControllerError("BOUND_FILE_MISSING:" + rel)
    actual = _git_blob_sha(full)
    if expected != actual:
        raise DecisionControllerError("BOUND_BLOB_DRIFT:" + rel)
    doc = json.loads(full.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise DecisionControllerError("BOUND_JSON_NOT_OBJECT:" + rel)
    return doc, rel, actual


def _authenticate_goal_binding(
    binding: Mapping[str, Any] | None,
    *,
    goal: str,
    decision_payload: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        return {"pass": False, "status": "OPEN__GOAL_TO_DECISION_BINDING_REQUIRED"}
    try:
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            repo_root=repo_root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification, verification_path, verification_blob = _bound_json(
            binding.get("verification"),
            repo_root=repo_root,
            prefixes=("canonical/verification/",),
        )
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        decision_sha = _digest(decision_payload)
        if receipt.get("schema") != GOAL_BINDING_SCHEMA:
            raise DecisionControllerError("GOAL_BINDING_SCHEMA_INVALID")
        if receipt.get("goal_sha256") != goal_sha:
            raise DecisionControllerError("GOAL_BINDING_GOAL_MISMATCH")
        if receipt.get("decision_payload_sha256") != decision_sha:
            raise DecisionControllerError("GOAL_BINDING_DECISION_MISMATCH")
        for field in (
            "binding_proved",
            "load_bearing_constraints_preserved",
            "decision_context_semantically_sufficient",
        ):
            if receipt.get(field) is not True:
                raise DecisionControllerError("GOAL_BINDING_PREMISE_UNPROVED:" + field)
        if verification.get("schema") != GOAL_BINDING_VERIFY_SCHEMA:
            raise DecisionControllerError("GOAL_BINDING_VERIFY_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise DecisionControllerError("GOAL_BINDING_VERIFY_SUBJECT_MISMATCH")
        if verification.get("goal_sha256") != goal_sha:
            raise DecisionControllerError("GOAL_BINDING_VERIFY_GOAL_MISMATCH")
        if verification.get("decision_payload_sha256") != decision_sha:
            raise DecisionControllerError("GOAL_BINDING_VERIFY_DECISION_MISMATCH")
        for field in ("pass", "independent_verified", "semantic_preservation_verified"):
            if verification.get(field) is not True:
                raise DecisionControllerError(
                    "GOAL_BINDING_VERIFY_PREMISE_UNPROVED:" + field
                )
        return {
            "pass": True,
            "status": "PASS__GOAL_TO_DECISION_CONTEXT_AUTHENTICATED",
            "goal_sha256": goal_sha,
            "decision_payload_sha256": decision_sha,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__GOAL_TO_DECISION_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _opaque_goal_atom_id(obligation_id: str) -> str:
    return "GOALOPAQUE::" + sha256(obligation_id.encode("utf-8")).hexdigest()


def _bootstrap_opaque_decision_context(
    *,
    task_id: str,
    goal: str,
    raw_contract: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create a sound zero-semantic-authority starting context.

    Every raw obligation is represented only by its deterministic opaque atom.
    This claims no interpretation. It merely moves an arbitrary goal from
    "no decision context" into the existing refinement machinery without losing
    any load-bearing source obligation.
    """
    obligation_ids = _raw_obligation_ids(raw_contract)
    opaque_atoms = [_opaque_goal_atom_id(oid) for oid in obligation_ids]
    if not opaque_atoms:
        raise DecisionControllerError("OPAQUE_BOOTSTRAP_REQUIRES_RAW_OBLIGATIONS")
    payload = {
        "context_id": "opaque-bootstrap:" + sha256(
            (task_id + "\n" + goal + "\n" + str(raw_contract.get("task_contract_sha256") or "")).encode("utf-8")
        ).hexdigest(),
        "v3_input": {
            "task": {
                "claims": [],
                "raw_task_contract_sha256": raw_contract.get("task_contract_sha256"),
                "opaque_goal_bootstrap": True,
            }
        },
        "bound_relevance_cegar_loop": {
            "cegar_problem": {
                "decision_basis": opaque_atoms,
                "formal_source_constraints": [],
            },
            "truth_payloads_by_discriminator_id": {},
            "truth_payloads_by_predicate_id": {},
            "source_positive_selection_contracts": {},
        },
    }
    binding = {
        "pass": True,
        "status": "PASS__OPAQUE_GOAL_CONTEXT_BOOTSTRAPPED_BY_CONSTRUCTION",
        "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
        "raw_task_contract_sha256": raw_contract.get("task_contract_sha256"),
        "decision_payload_sha256": _digest(payload),
        "raw_obligation_count": len(obligation_ids),
        "opaque_remainder_obligation_count": len(obligation_ids),
        "opaque_atom_ids": opaque_atoms,
        "all_raw_obligations_represented": True,
        "sound_overapproximation_only": True,
        "semantic_completeness_claimed": False,
        "semantic_authority": False,
        "construction_rule": "ONE_DETERMINISTIC_OPAQUE_ATOM_PER_RAW_OBLIGATION",
    }
    return payload, binding


def _decision_basis_from_payload(decision_payload: Mapping[str, Any]) -> set[str]:
    loop = decision_payload.get("bound_relevance_cegar_loop")
    if not isinstance(loop, Mapping):
        raise DecisionControllerError(
            "PARTIAL_GOAL_BINDING_REQUIRES_BOUND_RELEVANCE_CEGAR_LOOP"
        )
    problem = loop.get("cegar_problem")
    if not isinstance(problem, Mapping):
        raise DecisionControllerError(
            "PARTIAL_GOAL_BINDING_REQUIRES_CEGAR_PROBLEM"
        )
    basis = problem.get("decision_basis")
    if (
        not isinstance(basis, Sequence)
        or isinstance(basis, (str, bytes))
        or not basis
        or any(not isinstance(x, str) or not x for x in basis)
        or len(set(basis)) != len(basis)
    ):
        raise DecisionControllerError("PARTIAL_GOAL_DECISION_BASIS_INVALID")
    return set(basis)


def _raw_obligation_ids(raw_contract: Mapping[str, Any]) -> list[str]:
    acceptance = raw_contract.get("acceptance_contract")
    if not isinstance(acceptance, Mapping):
        raise DecisionControllerError("RAW_ACCEPTANCE_CONTRACT_INVALID")
    obligations = acceptance.get("obligations")
    if (
        not isinstance(obligations, Sequence)
        or isinstance(obligations, (str, bytes))
        or not obligations
    ):
        raise DecisionControllerError("RAW_ACCEPTANCE_OBLIGATIONS_INVALID")
    out: list[str] = []
    for index, row in enumerate(obligations):
        if not isinstance(row, Mapping):
            raise DecisionControllerError(
                f"RAW_ACCEPTANCE_OBLIGATION_INVALID:{index}"
            )
        obligation_id = row.get("obligation_id")
        if not isinstance(obligation_id, str) or not obligation_id:
            raise DecisionControllerError(
                f"RAW_ACCEPTANCE_OBLIGATION_ID_INVALID:{index}"
            )
        if obligation_id in out:
            raise DecisionControllerError(
                "RAW_ACCEPTANCE_OBLIGATION_ID_DUPLICATE:" + obligation_id
            )
        out.append(obligation_id)
    return out


def _authenticate_partial_goal_binding(
    binding: Mapping[str, Any] | None,
    *,
    goal: str,
    decision_payload: Mapping[str, Any],
    raw_contract: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    """Authenticate a sound partial goal semantics overapproximation.

    Every exact raw-source obligation must remain represented in the actual
    decision basis. A fully semantically bound obligation may be represented by
    independently verified semantic atoms. Every obligation not proved fully
    bound must additionally carry a deterministic opaque remainder atom. The
    opaque atom preserves all still-unknown load-bearing meaning, so missing
    semantics can reduce precision but cannot silently create policy authority.
    """
    if not isinstance(binding, Mapping):
        return {
            "pass": False,
            "status": "OPEN__PARTIAL_GOAL_TO_DECISION_BINDING_REQUIRED",
        }
    try:
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            repo_root=repo_root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification, verification_path, verification_blob = _bound_json(
            binding.get("verification"),
            repo_root=repo_root,
            prefixes=("canonical/verification/",),
        )
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        decision_sha = _digest(decision_payload)
        raw_contract_sha = str(raw_contract.get("task_contract_sha256") or "")
        if not raw_contract_sha:
            raise DecisionControllerError("RAW_TASK_CONTRACT_SHA_MISSING")

        if receipt.get("schema") != PARTIAL_GOAL_BINDING_SCHEMA:
            raise DecisionControllerError("PARTIAL_GOAL_BINDING_SCHEMA_INVALID")
        if receipt.get("goal_sha256") != goal_sha:
            raise DecisionControllerError("PARTIAL_GOAL_BINDING_GOAL_MISMATCH")
        if receipt.get("decision_payload_sha256") != decision_sha:
            raise DecisionControllerError("PARTIAL_GOAL_BINDING_DECISION_MISMATCH")
        if receipt.get("raw_task_contract_sha256") != raw_contract_sha:
            raise DecisionControllerError(
                "PARTIAL_GOAL_BINDING_RAW_CONTRACT_MISMATCH"
            )

        for field in (
            "binding_proved",
            "all_raw_obligations_represented",
            "sound_overapproximation_proved",
            "load_bearing_constraints_preserved",
        ):
            if receipt.get(field) is not True:
                raise DecisionControllerError(
                    "PARTIAL_GOAL_BINDING_PREMISE_UNPROVED:" + field
                )

        raw_ids = _raw_obligation_ids(raw_contract)
        raw_set = set(raw_ids)
        fully_bound = receipt.get("fully_semantically_bound_obligation_ids", [])
        if (
            not isinstance(fully_bound, list)
            or any(not isinstance(x, str) or not x for x in fully_bound)
            or len(set(fully_bound)) != len(fully_bound)
        ):
            raise DecisionControllerError(
                "PARTIAL_GOAL_FULLY_BOUND_OBLIGATIONS_INVALID"
            )
        fully_bound_set = set(fully_bound)
        if not fully_bound_set.issubset(raw_set):
            raise DecisionControllerError(
                "PARTIAL_GOAL_FULLY_BOUND_UNKNOWN_OBLIGATION"
            )

        semantic_map = receipt.get("semantic_atom_ids_by_obligation", {})
        if not isinstance(semantic_map, Mapping):
            raise DecisionControllerError("PARTIAL_GOAL_SEMANTIC_MAP_INVALID")
        if not set(semantic_map).issubset(raw_set):
            raise DecisionControllerError(
                "PARTIAL_GOAL_SEMANTIC_MAP_UNKNOWN_OBLIGATION"
            )

        semantic_atoms: set[str] = set()
        for obligation_id, raw_atoms in semantic_map.items():
            if (
                not isinstance(raw_atoms, list)
                or any(not isinstance(x, str) or not x for x in raw_atoms)
                or len(set(raw_atoms)) != len(raw_atoms)
            ):
                raise DecisionControllerError(
                    "PARTIAL_GOAL_SEMANTIC_ATOMS_INVALID:" + obligation_id
                )
            semantic_atoms.update(raw_atoms)

        opaque_map = receipt.get("opaque_remainder_atom_ids", {})
        if not isinstance(opaque_map, Mapping):
            raise DecisionControllerError("PARTIAL_GOAL_OPAQUE_MAP_INVALID")
        expected_opaque_ids = raw_set - fully_bound_set
        if set(opaque_map) != expected_opaque_ids:
            raise DecisionControllerError(
                "PARTIAL_GOAL_OPAQUE_REMAINDER_COVERAGE_MISMATCH"
            )
        opaque_atoms: set[str] = set()
        for obligation_id in sorted(expected_opaque_ids):
            atom = opaque_map.get(obligation_id)
            expected = _opaque_goal_atom_id(obligation_id)
            if atom != expected:
                raise DecisionControllerError(
                    "PARTIAL_GOAL_OPAQUE_ATOM_MISMATCH:" + obligation_id
                )
            opaque_atoms.add(expected)

        basis = _decision_basis_from_payload(decision_payload)
        missing_atoms = sorted((semantic_atoms | opaque_atoms) - basis)
        if missing_atoms:
            raise DecisionControllerError(
                "PARTIAL_GOAL_REPRESENTATION_OUTSIDE_DECISION_BASIS:"
                + ",".join(missing_atoms)
            )

        if verification.get("schema") != PARTIAL_GOAL_BINDING_VERIFY_SCHEMA:
            raise DecisionControllerError(
                "PARTIAL_GOAL_BINDING_VERIFY_SCHEMA_INVALID"
            )
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise DecisionControllerError(
                "PARTIAL_GOAL_BINDING_VERIFY_SUBJECT_MISMATCH"
            )
        if verification.get("goal_sha256") != goal_sha:
            raise DecisionControllerError(
                "PARTIAL_GOAL_BINDING_VERIFY_GOAL_MISMATCH"
            )
        if verification.get("decision_payload_sha256") != decision_sha:
            raise DecisionControllerError(
                "PARTIAL_GOAL_BINDING_VERIFY_DECISION_MISMATCH"
            )
        if verification.get("raw_task_contract_sha256") != raw_contract_sha:
            raise DecisionControllerError(
                "PARTIAL_GOAL_BINDING_VERIFY_RAW_CONTRACT_MISMATCH"
            )
        for field in (
            "pass",
            "independent_verified",
            "representation_completeness_verified",
            "semantic_atom_mapping_verified",
            "opaque_remainder_completeness_verified",
            "sound_overapproximation_verified",
            "load_bearing_constraints_verified",
        ):
            if verification.get(field) is not True:
                raise DecisionControllerError(
                    "PARTIAL_GOAL_BINDING_VERIFY_PREMISE_UNPROVED:" + field
                )

        return {
            "pass": True,
            "status": (
                "PASS__PARTIAL_GOAL_CONTEXT_SOUND_OVERAPPROXIMATION_AUTHENTICATED"
            ),
            "goal_sha256": goal_sha,
            "decision_payload_sha256": decision_sha,
            "raw_task_contract_sha256": raw_contract_sha,
            "raw_obligation_count": len(raw_ids),
            "fully_semantically_bound_obligation_count": len(fully_bound_set),
            "opaque_remainder_obligation_count": len(expected_opaque_ids),
            "semantic_atom_count": len(semantic_atoms),
            "opaque_atom_count": len(opaque_atoms),
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
            "sound_overapproximation_only": True,
            "semantic_completeness_claimed": False,
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__PARTIAL_GOAL_TO_DECISION_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _authenticate_policy_execution_binding(
    binding: Mapping[str, Any] | None,
    *,
    selected_policy_id: str,
    execution_problem: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        return {"pass": False, "status": "OPEN__POLICY_EXECUTION_BINDING_REQUIRED"}
    try:
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            repo_root=repo_root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification, verification_path, verification_blob = _bound_json(
            binding.get("verification"),
            repo_root=repo_root,
            prefixes=("canonical/verification/",),
        )
        problem_sha = _digest(execution_problem)
        if receipt.get("schema") != POLICY_EXECUTION_SCHEMA:
            raise DecisionControllerError("POLICY_EXECUTION_SCHEMA_INVALID")
        if receipt.get("policy_id") != selected_policy_id:
            raise DecisionControllerError("POLICY_EXECUTION_POLICY_MISMATCH")
        if receipt.get("execution_problem_sha256") != problem_sha:
            raise DecisionControllerError("POLICY_EXECUTION_PROBLEM_MISMATCH")
        for field in (
            "binding_proved",
            "brain_owned_execution",
            "execution_success_implies_policy_realization",
            "load_bearing_constraints_preserved",
        ):
            if receipt.get(field) is not True:
                raise DecisionControllerError(
                    "POLICY_EXECUTION_PREMISE_UNPROVED:" + field
                )
        if verification.get("schema") != POLICY_EXECUTION_VERIFY_SCHEMA:
            raise DecisionControllerError("POLICY_EXECUTION_VERIFY_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise DecisionControllerError("POLICY_EXECUTION_VERIFY_SUBJECT_MISMATCH")
        if verification.get("policy_id") != selected_policy_id:
            raise DecisionControllerError("POLICY_EXECUTION_VERIFY_POLICY_MISMATCH")
        if verification.get("execution_problem_sha256") != problem_sha:
            raise DecisionControllerError("POLICY_EXECUTION_VERIFY_PROBLEM_MISMATCH")
        for field in ("pass", "independent_verified", "realization_implication_verified"):
            if verification.get(field) is not True:
                raise DecisionControllerError(
                    "POLICY_EXECUTION_VERIFY_PREMISE_UNPROVED:" + field
                )
        return {
            "pass": True,
            "status": "PASS__POLICY_EXECUTION_BINDING_AUTHENTICATED",
            "policy_id": selected_policy_id,
            "execution_problem_sha256": problem_sha,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__POLICY_EXECUTION_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _authenticate_goal_satisfaction_binding(
    binding: Mapping[str, Any] | None,
    *,
    goal: str,
    selected_policy_id: str,
    realization: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    """Authenticate the final semantic acceptance edge.

    Adequate-policy selection and mechanically verified realization are necessary
    but not sufficient to claim that the caller's original goal was actually
    satisfied. This gate binds an independently verified acceptance receipt to the
    exact raw goal, selected policy, and realized output/execution object.
    """
    if not isinstance(binding, Mapping):
        return {"pass": False, "status": "OPEN__GOAL_SATISFACTION_BINDING_REQUIRED"}
    try:
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            repo_root=repo_root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification, verification_path, verification_blob = _bound_json(
            binding.get("verification"),
            repo_root=repo_root,
            prefixes=("canonical/verification/",),
        )
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        realization_sha = _digest(realization)
        if receipt.get("schema") != GOAL_SATISFACTION_SCHEMA:
            raise DecisionControllerError("GOAL_SATISFACTION_SCHEMA_INVALID")
        if receipt.get("goal_sha256") != goal_sha:
            raise DecisionControllerError("GOAL_SATISFACTION_GOAL_MISMATCH")
        if receipt.get("policy_id") != selected_policy_id:
            raise DecisionControllerError("GOAL_SATISFACTION_POLICY_MISMATCH")
        if receipt.get("realization_sha256") != realization_sha:
            raise DecisionControllerError("GOAL_SATISFACTION_REALIZATION_MISMATCH")
        for field in (
            "goal_satisfaction_proved",
            "all_load_bearing_constraints_satisfied",
            "acceptance_relation_bound",
        ):
            if receipt.get(field) is not True:
                raise DecisionControllerError(
                    "GOAL_SATISFACTION_PREMISE_UNPROVED:" + field
                )
        if verification.get("schema") != GOAL_SATISFACTION_VERIFY_SCHEMA:
            raise DecisionControllerError("GOAL_SATISFACTION_VERIFY_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise DecisionControllerError("GOAL_SATISFACTION_VERIFY_SUBJECT_MISMATCH")
        if verification.get("goal_sha256") != goal_sha:
            raise DecisionControllerError("GOAL_SATISFACTION_VERIFY_GOAL_MISMATCH")
        if verification.get("policy_id") != selected_policy_id:
            raise DecisionControllerError("GOAL_SATISFACTION_VERIFY_POLICY_MISMATCH")
        if verification.get("realization_sha256") != realization_sha:
            raise DecisionControllerError("GOAL_SATISFACTION_VERIFY_REALIZATION_MISMATCH")
        for field in (
            "pass",
            "independent_verified",
            "goal_satisfaction_verified",
            "acceptance_relation_verified",
            "load_bearing_constraints_verified",
        ):
            if verification.get(field) is not True:
                raise DecisionControllerError(
                    "GOAL_SATISFACTION_VERIFY_PREMISE_UNPROVED:" + field
                )
        verifier_id = verification.get("independent_verifier_id")
        if not isinstance(verifier_id, str) or not verifier_id.strip():
            raise DecisionControllerError("GOAL_SATISFACTION_INDEPENDENT_VERIFIER_ID_MISSING")
        return {
            "pass": True,
            "status": "PASS__ACTUAL_GOAL_SATISFACTION_AUTHENTICATED",
            "goal_sha256": goal_sha,
            "policy_id": selected_policy_id,
            "realization_sha256": realization_sha,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
            "independent_verifier_id": verifier_id.strip(),
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__GOAL_SATISFACTION_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _extract_information_gap(decision: Mapping[str, Any]) -> dict[str, Any] | None:
    detail = decision.get("detail")
    if not isinstance(detail, Mapping):
        return None
    loop = detail.get("loop_result")
    if not isinstance(loop, Mapping):
        return None
    status = loop.get("status")
    if status not in {
        "OPEN__SELECTED_PREDICATE_PROOF_PAYLOAD_REQUIRED",
        "OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED",
    }:
        return None
    loop_detail = loop.get("detail")
    predicate_id = (
        loop_detail.get("predicate_id") if isinstance(loop_detail, Mapping) else None
    )
    if not isinstance(predicate_id, str) or not predicate_id:
        return None
    return {
        "predicate_id": predicate_id,
        "loop_status": status,
        "loop_reason": loop.get("reason"),
    }


def _append_truth_payload(
    decision_payload: dict[str, Any],
    predicate_id: str,
    payload: Mapping[str, Any],
) -> None:
    loop = decision_payload.get("bound_relevance_cegar_loop")
    if not isinstance(loop, dict):
        raise DecisionControllerError(
            "BOUND_RELEVANCE_CEGAR_LOOP_REQUIRED_FOR_INFORMATION_REFINEMENT"
        )
    by_predicate = loop.setdefault("truth_payloads_by_predicate_id", {})
    if not isinstance(by_predicate, dict):
        raise DecisionControllerError("TRUTH_PAYLOADS_BY_PREDICATE_ID_INVALID")
    prior = by_predicate.get(predicate_id)
    candidate = deepcopy(dict(payload))
    if prior is None:
        by_predicate[predicate_id] = candidate
    elif isinstance(prior, list):
        prior.append(candidate)
    elif isinstance(prior, Mapping):
        by_predicate[predicate_id] = [deepcopy(dict(prior)), candidate]
    else:
        raise DecisionControllerError("EXISTING_TRUTH_PAYLOAD_INVALID")


def _open(
    status: str,
    *,
    task_id: str,
    goal: str,
    raw_contract: Mapping[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": False,
        "task_id": task_id,
        "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
        "raw_task_contract_sha256": raw_contract.get("task_contract_sha256"),
        "raw_source_coverage_complete": (
            raw_contract.get("nonwhitespace_source_coverage_complete") is True
        ),
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    information_provider: Callable[
        [Mapping[str, Any], int], Mapping[str, Any] | None
    ]
    | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
    execution_provider: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else ROOT
    try:
        if not isinstance(request, Mapping):
            raise DecisionControllerError("REQUEST_NOT_OBJECT")
        allowed = {
            "task_id",
            "goal",
            "decision_payload",
            "goal_to_decision_binding",
            "partial_goal_to_decision_binding",
            "execution_problem",
            "policy_execution_binding",
            "goal_satisfaction_binding",
            "policy_cover_observation_bindings",
            "max_policy_cover_observations",
            "max_information_rounds",
            "episode_id",
            "scope_id",
        }
        extra = set(request) - allowed
        if extra:
            raise DecisionControllerError(
                "UNMODELED_REQUEST_FIELDS:" + ",".join(sorted(extra))
            )
        task_id = str(request.get("task_id") or "").strip()
        goal = str(request.get("goal") or "").strip()
        if not task_id:
            raise DecisionControllerError("TASK_ID_REQUIRED")
        if not goal:
            raise DecisionControllerError("GOAL_REQUIRED")

        raw_contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=["decision.adequate_action"],
        )
        if raw_contract.get("pass") is not True:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__LOSSLESS_RAW_GOAL_CONTRACT",
                "pass": False,
                "task_id": task_id,
                "errors": raw_contract.get("errors"),
                "semantic_acceptance_complete": False,
                "actual_goal_satisfaction_verified": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
                "incremental_spend_usd": 0,
            }

        decision_payload = request.get("decision_payload")
        full_binding_supplied = isinstance(
            request.get("goal_to_decision_binding"), Mapping
        )
        partial_binding_supplied = isinstance(
            request.get("partial_goal_to_decision_binding"), Mapping
        )

        # Before starting open-ended semantic refinement, reuse any exact
        # Brain-owned adequacy region that proves its own raw-source membership.
        # This registry accepts no provider/caller semantic authority. A matched
        # adequate policy still must pass the independent raw-goal satisfaction
        # gate below.
        specialist_adequacy = None
        if (
            not isinstance(decision_payload, Mapping)
            and not full_binding_supplied
            and not partial_binding_supplied
            and request.get("execution_problem") is None
        ):
            specialist_adequacy = discover_authenticated_adequacy(
                goal,
                source_id="user",
            )
            if (
                isinstance(specialist_adequacy, Mapping)
                and specialist_adequacy.get("pass") is True
            ):
                selected_policy_id = specialist_adequacy.get("policy_id")
                realization = specialist_adequacy.get("realization")
                if (
                    not isinstance(selected_policy_id, str)
                    or not selected_policy_id
                    or not isinstance(realization, Mapping)
                    or specialist_adequacy.get("scope_membership_verified") is not True
                    or specialist_adequacy.get("selected_policy_adequacy_verified") is not True
                    or specialist_adequacy.get("policy_selection_authorized") is not True
                    or specialist_adequacy.get("actual_goal_satisfaction_verified") is not False
                    or specialist_adequacy.get("terminal_authority") is not False
                ):
                    raise DecisionControllerError(
                        "SPECIALIST_ADEQUACY_PASS_WITH_INVALID_AUTHORITY_BOUNDARY"
                    )
                realization = deepcopy(dict(realization))
                goal_satisfaction = _authenticate_goal_satisfaction_binding(
                    request.get("goal_satisfaction_binding"),
                    goal=goal,
                    selected_policy_id=selected_policy_id,
                    realization=realization,
                    repo_root=root,
                )
                if goal_satisfaction.get("pass") is not True:
                    return _open(
                        str(
                            goal_satisfaction.get("status")
                            or "OPEN__GOAL_SATISFACTION_BINDING_REQUIRED"
                        ),
                        task_id=task_id,
                        goal=goal,
                        raw_contract=raw_contract,
                        next_required_edge=(
                            "INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION"
                        ),
                        selected_policy_id=selected_policy_id,
                        decision_result=specialist_adequacy,
                        realization=realization,
                        goal_satisfaction_binding=goal_satisfaction,
                        specialist_adequacy_authority=specialist_adequacy,
                    )
                return {
                    "schema": SCHEMA,
                    "status": (
                        "PASS__GOAL_BOUND_AUTHENTICATED_SPECIALIST_POLICY_"
                        "REALIZED_AND_ACCEPTANCE_VERIFIED"
                    ),
                    "pass": True,
                    "task_id": task_id,
                    "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
                    "raw_task_contract_sha256": raw_contract[
                        "task_contract_sha256"
                    ],
                    "raw_source_coverage_complete": raw_contract[
                        "nonwhitespace_source_coverage_complete"
                    ],
                    "decision_result": specialist_adequacy,
                    "selected_policy_id": selected_policy_id,
                    "action_kind": "AUTHENTICATED_SPECIALIST_POLICY_RESULT",
                    "action": realization,
                    "realization": realization,
                    "goal_satisfaction_binding": goal_satisfaction,
                    "specialist_adequacy_authority": specialist_adequacy,
                    "information_trace": [],
                    "minimum_information_rounds_used": 0,
                    "semantic_acceptance_complete": True,
                    "actual_goal_satisfaction_verified": True,
                    "verification_scope": (
                        "SELF_AUTHENTICATING_SPECIALIST_ADEQUACY_PLUS_"
                        "INDEPENDENT_ACTUAL_GOAL_SATISFACTION"
                    ),
                    "terminal_authority": False,
                    "terminal_credit_delta": 0,
                    "incremental_spend_usd": 0,
                }

        opaque_bootstrap_binding = None
        if not isinstance(decision_payload, Mapping):
            decision_payload, opaque_bootstrap_binding = _bootstrap_opaque_decision_context(
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
            )
        working = deepcopy(dict(decision_payload))

        if opaque_bootstrap_binding is not None and (
            full_binding_supplied or partial_binding_supplied
        ):
            raise DecisionControllerError("OPAQUE_BOOTSTRAP_BINDING_MODE_CONFLICT")
        if full_binding_supplied and partial_binding_supplied:
            raise DecisionControllerError("GOAL_BINDING_MODE_AMBIGUOUS")

        if opaque_bootstrap_binding is not None:
            goal_binding = opaque_bootstrap_binding
            goal_binding_mode = "OPAQUE_BOOTSTRAP_BY_CONSTRUCTION"
        elif full_binding_supplied:
            goal_binding = _authenticate_goal_binding(
                request.get("goal_to_decision_binding"),
                goal=goal,
                decision_payload=decision_payload,
                repo_root=root,
            )
            goal_binding_mode = "FULL"
        elif partial_binding_supplied:
            goal_binding = _authenticate_partial_goal_binding(
                request.get("partial_goal_to_decision_binding"),
                goal=goal,
                decision_payload=decision_payload,
                raw_contract=raw_contract,
                repo_root=root,
            )
            goal_binding_mode = "PARTIAL_SOUND_OVERAPPROXIMATION"
        else:
            goal_binding = {
                "pass": False,
                "status": "OPEN__GOAL_TO_DECISION_BINDING_REQUIRED",
            }
            goal_binding_mode = "NONE"

        if goal_binding.get("pass") is not True:
            return _open(
                str(
                    goal_binding.get("status")
                    or "OPEN__GOAL_TO_DECISION_BINDING_REQUIRED"
                ),
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
                next_required_edge=(
                    "AUTHENTICATED_FULL_OR_SOUND_PARTIAL_GOAL_TO_DECISION_CONTEXT"
                ),
                goal_to_decision_binding=goal_binding,
                goal_binding_mode=goal_binding_mode,
            )

        max_rounds = request.get("max_information_rounds", MAX_INFORMATION_ROUNDS)
        if (
            isinstance(max_rounds, bool)
            or not isinstance(max_rounds, int)
            or not 0 <= max_rounds <= MAX_INFORMATION_ROUNDS
        ):
            raise DecisionControllerError("MAX_INFORMATION_ROUNDS_INVALID")

        information_trace: list[dict[str, Any]] = []
        decision = None
        for round_index in range(max_rounds + 1):
            decision = evaluate_p3(working, repo_root=root)
            if decision.get("pass") is True:
                break
            gap = _extract_information_gap(decision)
            if gap is None:
                cover_cfg = working.get("observable_policy_cover")
                if isinstance(cover_cfg, Mapping):
                    extra_cover_fields = set(cover_cfg) - {"problem", "cover_binding"}
                    if extra_cover_fields:
                        raise DecisionControllerError(
                            "UNMODELED_OBSERVABLE_POLICY_COVER_FIELDS:"
                            + ",".join(sorted(extra_cover_fields))
                        )
                    cover_result = evaluate_policy_cover(
                        {
                            "problem": cover_cfg.get("problem"),
                            "cover_binding": cover_cfg.get("cover_binding"),
                            "observation_bindings_by_discriminator_id": request.get(
                                "policy_cover_observation_bindings", {}
                            ),
                            "max_observations": request.get(
                                "max_policy_cover_observations", 64
                            ),
                        },
                        repo_root=root,
                    )
                    if cover_result.get("pass") is True:
                        cover_policy_id = cover_result.get("selected_policy_id")
                        if (
                            not isinstance(cover_policy_id, str)
                            or not cover_policy_id
                            or cover_result.get("policy_selection_authorized") is not True
                            or cover_result.get("selected_policy_adequacy_verified") is not True
                            or cover_result.get("bound_state_totality_proved") is not True
                        ):
                            raise DecisionControllerError(
                                "POLICY_COVER_PASS_WITHOUT_AUTHORIZED_ADEQUATE_SELECTION"
                            )
                        decision = {
                            "pass": True,
                            "status": "PASS__R2_AUTHENTICATED_OBSERVABLE_POLICY_COVER",
                            "route": "OBSERVABLE_POLICY_COVER_EXECUTOR_V1",
                            "selected_policy_id": cover_policy_id,
                            "policy_cover_result": cover_result,
                        }
                        break
                    next_observation = cover_result.get("next_observation_request")
                    return _open(
                        str(
                            cover_result.get("status")
                            or "OPEN__OBSERVABLE_POLICY_COVER_UNRESOLVED"
                        ),
                        task_id=task_id,
                        goal=goal,
                        raw_contract=raw_contract,
                        next_required_edge=(
                            "AUTHENTICATED_SELECTED_POLICY_CHANGING_OBSERVATION"
                            if isinstance(next_observation, Mapping)
                            else "AUTHENTICATED_OBSERVABLE_POLICY_COVER"
                        ),
                        next_observation_request=next_observation,
                        decision_result=decision,
                        policy_cover_result=cover_result,
                        information_trace=information_trace,
                        goal_to_decision_binding=goal_binding,
                    )
                return _open(
                    "OPEN__ADEQUATE_POLICY_OR_SEMANTIC_COVERAGE_REQUIRED",
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="EXACT_P3_V12_OPEN_EDGE",
                    decision_result=decision,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            request_packet = {
                "schema": "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_REQUEST_V1",
                "task_id": task_id,
                "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
                "decision_payload_sha256": _digest(working),
                "predicate_id": gap["predicate_id"],
                "reason": gap["loop_status"],
                "information_authority": False,
                "semantic_truth_authority": False,
            }
            if information_provider is None:
                return _open(
                    "OPEN__MINIMUM_POLICY_CHANGING_INFORMATION_REQUIRED",
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="SOURCE_BOUND_TRUTH_FOR_SELECTED_PREDICATE",
                    next_information_request=request_packet,
                    decision_result=decision,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            if round_index >= max_rounds:
                return _open(
                    "OPEN__MINIMUM_INFORMATION_ROUND_BOUND_EXHAUSTED",
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="STRONGER_INFORMATION_OR_ADEQUACY_EDGE",
                    next_information_request=request_packet,
                    decision_result=decision,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            provided = information_provider(request_packet, round_index)
            information_trace.append(
                {
                    "round": round_index,
                    "predicate_id": gap["predicate_id"],
                    "provider_returned_payload": isinstance(provided, Mapping),
                    "provider_authority": False,
                }
            )
            if not isinstance(provided, Mapping):
                return _open(
                    "OPEN__MINIMUM_POLICY_CHANGING_INFORMATION_REQUIRED",
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="SOURCE_BOUND_TRUTH_FOR_SELECTED_PREDICATE",
                    next_information_request=request_packet,
                    decision_result=decision,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            _append_truth_payload(working, gap["predicate_id"], provided)

        if not isinstance(decision, Mapping) or decision.get("pass") is not True:
            return _open(
                "OPEN__ADEQUATE_DECISION_NOT_CERTIFIED",
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
                decision_result=decision,
                information_trace=information_trace,
                goal_to_decision_binding=goal_binding,
            )

        selected_policy_id = decision.get("selected_policy_id")
        if not isinstance(selected_policy_id, str) or not selected_policy_id:
            raise DecisionControllerError("P3_SELECTED_POLICY_ID_INVALID")

        execution_problem = request.get("execution_problem")
        if execution_problem is None:
            rendered = decision.get("rendered_text")
            if not isinstance(rendered, str) or not rendered:
                return _open(
                    "OPEN__ADEQUATE_POLICY_REALIZATION_REQUIRED",
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="GROUNDED_REALIZATION_OF_SELECTED_POLICY",
                    decision_result=decision,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            realization = {
                "kind": "GROUNDED_DECISION_EXPRESSION",
                "policy_id": selected_policy_id,
                "rendered_text": rendered,
                "decision_result_sha256": _digest(decision),
            }
            goal_satisfaction = _authenticate_goal_satisfaction_binding(
                request.get("goal_satisfaction_binding"),
                goal=goal,
                selected_policy_id=selected_policy_id,
                realization=realization,
                repo_root=root,
            )
            if goal_satisfaction.get("pass") is not True:
                return _open(
                    str(
                        goal_satisfaction.get("status")
                        or "OPEN__GOAL_SATISFACTION_BINDING_REQUIRED"
                    ),
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
                    decision_result=decision,
                    realization=realization,
                    goal_satisfaction_binding=goal_satisfaction,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            return {
                "schema": SCHEMA,
                "status": "PASS__GOAL_BOUND_ADEQUATE_DECISION_REALIZED_AND_ACCEPTANCE_VERIFIED",
                "pass": True,
                "task_id": task_id,
                "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
                "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
                "raw_source_coverage_complete": raw_contract[
                    "nonwhitespace_source_coverage_complete"
                ],
                "goal_to_decision_binding": goal_binding,
                "decision_result": decision,
                "selected_policy_id": selected_policy_id,
                "action_kind": "GROUNDED_DECISION_EXPRESSION",
                "action": rendered,
                "realization": realization,
                "goal_satisfaction_binding": goal_satisfaction,
                "information_trace": information_trace,
                "minimum_information_rounds_used": len(information_trace),
                "semantic_acceptance_complete": True,
                "actual_goal_satisfaction_verified": True,
                "verification_scope": (
                    "AUTHENTICATED_GOAL_BOUND_P3_V12_DECISION_CONTEXT"
                ),
                "terminal_authority": False,
                "terminal_credit_delta": 0,
                "incremental_spend_usd": 0,
            }

        if not isinstance(execution_problem, Mapping):
            raise DecisionControllerError("EXECUTION_PROBLEM_NOT_OBJECT")
        execution_binding = _authenticate_policy_execution_binding(
            request.get("policy_execution_binding"),
            selected_policy_id=selected_policy_id,
            execution_problem=execution_problem,
            repo_root=root,
        )
        if execution_binding.get("pass") is not True:
            return _open(
                str(
                    execution_binding.get("status")
                    or "OPEN__POLICY_EXECUTION_BINDING_REQUIRED"
                ),
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
                next_required_edge="AUTHENTICATED_SELECTED_POLICY_TO_EXECUTION_BINDING",
                decision_result=decision,
                information_trace=information_trace,
                goal_to_decision_binding=goal_binding,
                policy_execution_binding=execution_binding,
            )

        executor = execution_provider or run_universal
        execution = executor(
            execution_problem,
            repo_root=root,
            episode_id=str(request.get("episode_id") or task_id),
            scope_id=str(request.get("scope_id") or "general-adequate-decision"),
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
        )
        if not isinstance(execution, Mapping):
            raise DecisionControllerError("EXECUTION_PROVIDER_RESULT_NOT_OBJECT")
        if execution.get("pass") is not True:
            return _open(
                "OPEN__SELECTED_ADEQUATE_POLICY_EXECUTION_UNRESOLVED",
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
                next_required_edge=(
                    "UNIVERSAL_SOLVER_EXACT_NEXT_REQUIRED_INPUT_OR_CAPABILITY"
                ),
                decision_result=decision,
                execution_result=execution,
                information_trace=information_trace,
                goal_to_decision_binding=goal_binding,
                policy_execution_binding=execution_binding,
            )

        realization = {
            "kind": "VERIFIED_POLICY_EXECUTION",
            "policy_id": selected_policy_id,
            "execution_result": execution,
        }
        goal_satisfaction = _authenticate_goal_satisfaction_binding(
            request.get("goal_satisfaction_binding"),
            goal=goal,
            selected_policy_id=selected_policy_id,
            realization=realization,
            repo_root=root,
        )
        if goal_satisfaction.get("pass") is not True:
            return _open(
                str(
                    goal_satisfaction.get("status")
                    or "OPEN__GOAL_SATISFACTION_BINDING_REQUIRED"
                ),
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
                next_required_edge="INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
                decision_result=decision,
                execution_result=execution,
                realization=realization,
                goal_satisfaction_binding=goal_satisfaction,
                information_trace=information_trace,
                goal_to_decision_binding=goal_binding,
                policy_execution_binding=execution_binding,
            )

        return {
            "schema": SCHEMA,
            "status": "PASS__GOAL_BOUND_ADEQUATE_POLICY_EXECUTED_AND_ACCEPTANCE_VERIFIED",
            "pass": True,
            "task_id": task_id,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
            "raw_source_coverage_complete": raw_contract[
                "nonwhitespace_source_coverage_complete"
            ],
            "goal_to_decision_binding": goal_binding,
            "decision_result": decision,
            "selected_policy_id": selected_policy_id,
            "policy_execution_binding": execution_binding,
            "execution_result": execution,
            "realization": realization,
            "goal_satisfaction_binding": goal_satisfaction,
            "information_trace": information_trace,
            "minimum_information_rounds_used": len(information_trace),
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "verification_scope": (
                "AUTHENTICATED_GOAL_BINDING_PLUS_P3_ADEQUACY_PLUS_"
                "AUTHENTICATED_POLICY_EXECUTION_PLUS_VERIFIED_TARGET_EFFECTS"
            ),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "semantic_acceptance_complete": False,
            "actual_goal_satisfaction_verified": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }
