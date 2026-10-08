"""Verifier Compiler V1.

Compiles the lossless raw-task acceptance contract into explicit verifier
requirements without inventing semantic truth. Every raw obligation retains a
mandatory independent goal-satisfaction route. Deterministic structural
constraints are exposed as supplemental checkers when available.

This module has no success, capability-promotion, ownership, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.instruction_constraint_compiler_v1 import (
    ConstraintSet,
    validate_response,
)

SCHEMA = "PROJECT_BRAIN_VERIFIER_COMPILER_V1"


class VerifierCompilerError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def _s(value: Any) -> str:
    return " ".join(str(value or "").split())


def _structural_constraints(raw_contract: Mapping[str, Any]) -> dict[str, Any] | None:
    raw = raw_contract.get("formal_instruction_constraints")
    if not isinstance(raw, Mapping):
        return None
    normalized = {
        "exact_response": raw.get("exact_response"),
        "prefix": raw.get("prefix"),
        "suffix": raw.get("suffix"),
        "min_words": raw.get("min_words"),
        "max_words": raw.get("max_words"),
        "min_unique_words": raw.get("min_unique_words"),
        "exact_numbers": raw.get("exact_numbers"),
        "lowercase_only": raw.get("lowercase_only") is True,
        "uppercase_only": raw.get("uppercase_only") is True,
        "required_literals": list(raw.get("required_literals") or []),
        "forbidden_literals": list(raw.get("forbidden_literals") or []),
    }
    signal = any(
        (
            normalized["exact_response"] is not None,
            normalized["prefix"] is not None,
            normalized["suffix"] is not None,
            normalized["min_words"] is not None,
            normalized["max_words"] is not None,
            normalized["min_unique_words"] is not None,
            normalized["exact_numbers"] is not None,
            normalized["lowercase_only"],
            normalized["uppercase_only"],
            bool(normalized["required_literals"]),
            bool(normalized["forbidden_literals"]),
        )
    )
    return normalized if signal else None


def compile_verifier_plan(raw_contract: Mapping[str, Any]) -> dict[str, Any]:
    """Compile every preserved raw obligation into an explicit verifier route.

    The plan is intentionally conservative:
    - raw obligations are never dropped;
    - structural checkers are supplemental unless a stronger authority proves
      semantic sufficiency elsewhere;
    - final semantic success remains owned by the independently authenticated
      goal-satisfaction binding already used by R2.
    """
    if not isinstance(raw_contract, Mapping) or raw_contract.get("pass") is not True:
        raise VerifierCompilerError("RAW_CONTRACT_PASS_REQUIRED")
    task_contract_sha = _s(raw_contract.get("task_contract_sha256"))
    task_sha = _s(raw_contract.get("task_sha256"))
    if not task_contract_sha or not task_sha:
        raise VerifierCompilerError("RAW_CONTRACT_IDENTITY_INCOMPLETE")

    acceptance = raw_contract.get("acceptance_contract")
    if not isinstance(acceptance, Mapping):
        raise VerifierCompilerError("ACCEPTANCE_CONTRACT_REQUIRED")
    obligations = acceptance.get("obligations")
    if (
        not isinstance(obligations, Sequence)
        or isinstance(obligations, (str, bytes))
        or not obligations
    ):
        raise VerifierCompilerError("ACCEPTANCE_OBLIGATIONS_REQUIRED")

    rows: list[dict[str, Any]] = []
    obligation_ids: list[str] = []
    for index, raw in enumerate(obligations):
        if not isinstance(raw, Mapping):
            raise VerifierCompilerError(f"OBLIGATION_NOT_OBJECT:{index}")
        oid = _s(raw.get("obligation_id"))
        seg_sha = _s(raw.get("segment_sha256"))
        span = raw.get("span")
        if not oid or not seg_sha:
            raise VerifierCompilerError(f"OBLIGATION_IDENTITY_INCOMPLETE:{index}")
        if (
            not isinstance(span, Sequence)
            or isinstance(span, (str, bytes))
            or len(span) != 2
            or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in span)
            or int(span[0]) > int(span[1])
        ):
            raise VerifierCompilerError(f"OBLIGATION_SPAN_INVALID:{index}")
        if oid in obligation_ids:
            raise VerifierCompilerError("OBLIGATION_ID_DUPLICATE:" + oid)
        obligation_ids.append(oid)
        rows.append(
            {
                "obligation_id": oid,
                "segment_sha256": seg_sha,
                "span": [int(span[0]), int(span[1])],
                "kind": _s(raw.get("kind")) or "RAW_SOURCE_SEGMENT_ACCEPTANCE",
                "primary_verifier": {
                    "class": "INDEPENDENT_GOAL_SATISFACTION_BINDING",
                    "authority": "EXISTING_R2_FINAL_ACCEPTANCE_AUTHORITY",
                    "required": True,
                    "self_certifying": False,
                },
                "semantic_acceptance_required": True,
                "silently_droppable": False,
            }
        )

    required_ids = acceptance.get("required_obligation_ids")
    if (
        not isinstance(required_ids, Sequence)
        or isinstance(required_ids, (str, bytes))
        or [str(x) for x in required_ids] != obligation_ids
    ):
        raise VerifierCompilerError("REQUIRED_OBLIGATION_ID_SET_DRIFT")

    structural = _structural_constraints(raw_contract)
    structural_verifier = None
    if structural is not None:
        structural_verifier = {
            "verifier_id": "FORMAL_INSTRUCTION_CONSTRAINT_VALIDATOR_V1",
            "class": "DETERMINISTIC_STRUCTURAL_CHECKER",
            "constraints": structural,
            "semantic_success_authority": False,
            "role": "SUPPLEMENTAL_ACCEPTANCE_EVIDENCE",
        }

    core = {
        "raw_task_contract_sha256": task_contract_sha,
        "task_sha256": task_sha,
        "required_obligation_ids": obligation_ids,
        "obligation_verifiers": rows,
        "task_level_structural_verifier": structural_verifier,
    }
    return {
        "schema": SCHEMA,
        "status": "COMPILED__LOSSLESS_OBLIGATION_VERIFIER_PLAN",
        "pass": True,
        **core,
        "verifier_plan_sha256": _sha(core),
        "raw_obligation_count": len(rows),
        "all_raw_obligations_have_explicit_verifier_route": True,
        "all_raw_obligations_automatically_decidable": False,
        "semantic_acceptance_authority": "AUTHENTICATED_R2_GOAL_SATISFACTION_BINDING",
        "automatic_success_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def validate_structural_candidate(
    verifier_plan: Mapping[str, Any],
    candidate_text: str,
) -> dict[str, Any]:
    """Evaluate only deterministic structural constraints in the verifier plan.

    A pass here is supplemental evidence, never semantic acceptance.
    """
    if not isinstance(verifier_plan, Mapping) or verifier_plan.get("pass") is not True:
        raise VerifierCompilerError("VERIFIER_PLAN_PASS_REQUIRED")
    row = verifier_plan.get("task_level_structural_verifier")
    if not isinstance(row, Mapping):
        return {
            "schema": SCHEMA,
            "status": "NO_STRUCTURAL_VERIFIER_AVAILABLE",
            "pass": True,
            "structural_constraints_present": False,
            "structural_constraints_satisfied": None,
            "semantic_success_authority": False,
        }
    constraints = row.get("constraints")
    if not isinstance(constraints, Mapping):
        raise VerifierCompilerError("STRUCTURAL_CONSTRAINTS_INVALID")
    c = ConstraintSet(
        exact_response=constraints.get("exact_response"),
        prefix=constraints.get("prefix"),
        suffix=constraints.get("suffix"),
        min_words=constraints.get("min_words"),
        max_words=constraints.get("max_words"),
        min_unique_words=constraints.get("min_unique_words"),
        exact_numbers=constraints.get("exact_numbers"),
        lowercase_only=constraints.get("lowercase_only") is True,
        uppercase_only=constraints.get("uppercase_only") is True,
        required_literals=tuple(constraints.get("required_literals") or ()),
        forbidden_literals=tuple(constraints.get("forbidden_literals") or ()),
    )
    ok, errors = validate_response(str(candidate_text or ""), c)
    return {
        "schema": SCHEMA,
        "status": "STRUCTURAL_CONSTRAINTS_PASS" if ok else "STRUCTURAL_CONSTRAINTS_FAIL",
        "pass": ok,
        "structural_constraints_present": True,
        "structural_constraints_satisfied": ok,
        "validation_errors": errors,
        "semantic_success_authority": False,
    }
