"""Proof-Carrying Outcome V1.

Normalizes already-authenticated R2 acceptance evidence into one bounded,
obligation-complete capsule. This module does not create acceptance authority:
it only packages the existing independently authenticated goal-satisfaction
binding against every exact raw obligation preserved by the lossless contract.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.verifier_compiler_v1 import validate_structural_candidate

SCHEMA = "PROJECT_BRAIN_PROOF_CARRYING_OUTCOME_V1"


class ProofCarryingOutcomeError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def _s(value: Any) -> str:
    return " ".join(str(value or "").split())


def verify_proof_carrying_outcome_integrity(
    outcome: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute the bounded capsule digest and structural acceptance invariants.

    This verifies capsule integrity only. It does not replace reauthentication of
    the underlying independent receipt/verification bytes when authority is needed.
    """
    try:
        if not isinstance(outcome, Mapping):
            raise ProofCarryingOutcomeError("OUTCOME_NOT_OBJECT")
        if outcome.get("schema") != SCHEMA:
            raise ProofCarryingOutcomeError("OUTCOME_SCHEMA_INVALID")
        if outcome.get("pass") is not True:
            raise ProofCarryingOutcomeError("OUTCOME_PASS_REQUIRED")
        if outcome.get("status") != "PASS__PROOF_CARRYING_OUTCOME_OBLIGATION_COMPLETE":
            raise ProofCarryingOutcomeError("OUTCOME_STATUS_INVALID")
        if outcome.get("self_certifying") is not False:
            raise ProofCarryingOutcomeError("OUTCOME_SELF_CERTIFYING_INVALID")
        if outcome.get("semantic_acceptance_complete") is not True:
            raise ProofCarryingOutcomeError("SEMANTIC_ACCEPTANCE_INCOMPLETE")
        if outcome.get("all_raw_obligations_bound_to_authenticated_acceptance") is not True:
            raise ProofCarryingOutcomeError("OBLIGATION_ACCEPTANCE_COVERAGE_INCOMPLETE")

        evidence = outcome.get("obligation_evidence")
        if (
            not isinstance(evidence, Sequence)
            or isinstance(evidence, (str, bytes))
            or not evidence
        ):
            raise ProofCarryingOutcomeError("OBLIGATION_EVIDENCE_REQUIRED")
        ids: list[str] = []
        for index, row in enumerate(evidence):
            if not isinstance(row, Mapping):
                raise ProofCarryingOutcomeError(f"OBLIGATION_EVIDENCE_INVALID:{index}")
            oid = _s(row.get("obligation_id"))
            binding = row.get("acceptance_binding")
            if not oid or oid in ids:
                raise ProofCarryingOutcomeError("OBLIGATION_EVIDENCE_ID_INVALID:" + oid)
            if row.get("accepted") is not True or not isinstance(binding, Mapping):
                raise ProofCarryingOutcomeError("OBLIGATION_EVIDENCE_NOT_ACCEPTED:" + oid)
            if not _s(binding.get("independent_verifier_id")):
                raise ProofCarryingOutcomeError("OBLIGATION_INDEPENDENT_VERIFIER_MISSING:" + oid)
            ids.append(oid)

        raw_count = outcome.get("raw_obligation_count")
        accepted_count = outcome.get("accepted_obligation_count")
        if raw_count != len(evidence) or accepted_count != len(evidence):
            raise ProofCarryingOutcomeError("OBLIGATION_COUNT_MISMATCH")

        core = {
            "raw_task_contract_sha256": outcome.get("raw_task_contract_sha256"),
            "task_sha256": outcome.get("task_sha256"),
            "verifier_plan_sha256": outcome.get("verifier_plan_sha256"),
            "selected_policy_id": outcome.get("selected_policy_id"),
            "realization_sha256": outcome.get("realization_sha256"),
            "obligation_evidence": list(evidence),
            "structural_validation": outcome.get("structural_validation"),
            "goal_satisfaction_binding": outcome.get("goal_satisfaction_binding"),
        }
        actual = _sha(core)
        expected = _s(outcome.get("proof_carrying_outcome_sha256"))
        if actual != expected:
            raise ProofCarryingOutcomeError("PROOF_CARRYING_OUTCOME_DIGEST_MISMATCH")
        return {
            "schema": SCHEMA,
            "status": "PASS__PROOF_CARRYING_OUTCOME_INTEGRITY",
            "pass": True,
            "proof_carrying_outcome_sha256": actual,
            "raw_obligation_count": len(evidence),
            "self_certifying": False,
            "authority_reauthentication_complete": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__PROOF_CARRYING_OUTCOME_INTEGRITY",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "self_certifying": False,
            "authority_reauthentication_complete": False,
            "terminal_authority": False,
        }


def build_proof_carrying_outcome(
    *,
    raw_contract: Mapping[str, Any],
    verifier_plan: Mapping[str, Any],
    selected_policy_id: str,
    realization: Mapping[str, Any],
    goal_satisfaction_binding: Mapping[str, Any],
    candidate_text: str | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(raw_contract, Mapping) or raw_contract.get("pass") is not True:
            raise ProofCarryingOutcomeError("RAW_CONTRACT_PASS_REQUIRED")
        if not isinstance(verifier_plan, Mapping) or verifier_plan.get("pass") is not True:
            raise ProofCarryingOutcomeError("VERIFIER_PLAN_PASS_REQUIRED")
        if (
            verifier_plan.get("raw_task_contract_sha256")
            != raw_contract.get("task_contract_sha256")
        ):
            raise ProofCarryingOutcomeError("VERIFIER_PLAN_RAW_CONTRACT_MISMATCH")
        policy_id = _s(selected_policy_id)
        if not policy_id:
            raise ProofCarryingOutcomeError("SELECTED_POLICY_ID_REQUIRED")
        if not isinstance(realization, Mapping):
            raise ProofCarryingOutcomeError("REALIZATION_NOT_OBJECT")
        binding = goal_satisfaction_binding
        if not isinstance(binding, Mapping) or binding.get("pass") is not True:
            raise ProofCarryingOutcomeError("AUTHENTICATED_GOAL_SATISFACTION_REQUIRED")
        if binding.get("status") != "PASS__ACTUAL_GOAL_SATISFACTION_AUTHENTICATED":
            raise ProofCarryingOutcomeError("GOAL_SATISFACTION_STATUS_INVALID")
        if binding.get("policy_id") != policy_id:
            raise ProofCarryingOutcomeError("GOAL_SATISFACTION_POLICY_MISMATCH")
        verifier_id = _s(binding.get("independent_verifier_id"))
        if not verifier_id:
            raise ProofCarryingOutcomeError("INDEPENDENT_VERIFIER_ID_REQUIRED")

        acceptance = raw_contract.get("acceptance_contract")
        obligations = acceptance.get("obligations") if isinstance(acceptance, Mapping) else None
        if (
            not isinstance(obligations, Sequence)
            or isinstance(obligations, (str, bytes))
            or not obligations
        ):
            raise ProofCarryingOutcomeError("RAW_OBLIGATIONS_REQUIRED")

        plan_rows = verifier_plan.get("obligation_verifiers")
        if (
            not isinstance(plan_rows, Sequence)
            or isinstance(plan_rows, (str, bytes))
            or len(plan_rows) != len(obligations)
        ):
            raise ProofCarryingOutcomeError("VERIFIER_PLAN_OBLIGATION_COVERAGE_INVALID")
        plan_by_id = {
            _s(row.get("obligation_id")): row
            for row in plan_rows
            if isinstance(row, Mapping) and _s(row.get("obligation_id"))
        }

        evidence = []
        for raw in obligations:
            if not isinstance(raw, Mapping):
                raise ProofCarryingOutcomeError("RAW_OBLIGATION_INVALID")
            oid = _s(raw.get("obligation_id"))
            if oid not in plan_by_id:
                raise ProofCarryingOutcomeError("OBLIGATION_MISSING_VERIFIER_ROUTE:" + oid)
            evidence.append(
                {
                    "obligation_id": oid,
                    "segment_sha256": _s(raw.get("segment_sha256")),
                    "verifier_class": "INDEPENDENT_GOAL_SATISFACTION_BINDING",
                    "acceptance_binding": {
                        "goal_sha256": binding.get("goal_sha256"),
                        "policy_id": binding.get("policy_id"),
                        "realization_sha256": binding.get("realization_sha256"),
                        "receipt_path": binding.get("receipt_path"),
                        "receipt_git_blob_sha": binding.get("receipt_git_blob_sha"),
                        "verification_path": binding.get("verification_path"),
                        "verification_git_blob_sha": binding.get("verification_git_blob_sha"),
                        "independent_verifier_id": verifier_id,
                    },
                    "accepted": True,
                }
            )

        structural = None
        if candidate_text is not None:
            structural = validate_structural_candidate(verifier_plan, candidate_text)
            if (
                structural.get("structural_constraints_present") is True
                and structural.get("pass") is not True
            ):
                raise ProofCarryingOutcomeError(
                    "STRUCTURAL_ACCEPTANCE_CONTRADICTION:"
                    + ",".join(structural.get("validation_errors") or [])
                )

        core = {
            "raw_task_contract_sha256": raw_contract.get("task_contract_sha256"),
            "task_sha256": raw_contract.get("task_sha256"),
            "verifier_plan_sha256": verifier_plan.get("verifier_plan_sha256"),
            "selected_policy_id": policy_id,
            "realization_sha256": binding.get("realization_sha256") or _sha(realization),
            "obligation_evidence": evidence,
            "structural_validation": structural,
            "goal_satisfaction_binding": {
                "status": binding.get("status"),
                "receipt_path": binding.get("receipt_path"),
                "receipt_git_blob_sha": binding.get("receipt_git_blob_sha"),
                "verification_path": binding.get("verification_path"),
                "verification_git_blob_sha": binding.get("verification_git_blob_sha"),
                "independent_verifier_id": verifier_id,
            },
        }
        return {
            "schema": SCHEMA,
            "status": "PASS__PROOF_CARRYING_OUTCOME_OBLIGATION_COMPLETE",
            "pass": True,
            **core,
            "proof_carrying_outcome_sha256": _sha(core),
            "raw_obligation_count": len(evidence),
            "accepted_obligation_count": len(evidence),
            "all_raw_obligations_bound_to_authenticated_acceptance": True,
            "semantic_acceptance_complete": True,
            "proof_authority_derived_from": "AUTHENTICATED_R2_GOAL_SATISFACTION_BINDING",
            "acceptance_authority": False,
            "self_certifying": False,
            "capability_promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__PROOF_CARRYING_OUTCOME_INVALID",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "semantic_acceptance_complete": False,
            "acceptance_authority": False,
            "self_certifying": False,
            "capability_promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
