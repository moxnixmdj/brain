"""Fail-closed complete-discovery interface theorem for tool identity discovery.

This module does not claim that any concrete registry is globally complete.
It proves a narrower, reusable implication:

If a frozen target scope supplies an independently verified COMPLETE_DISCOVERY_INTERFACE
receipt whose declared source set is complete for that scope, then arbitrary tool
identities returned by those sources are covered without requiring a pre-enumerated
tool-id whitelist.

The evaluator grants no acceptance, capability, family, execution, or promotion credit.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_COMPLETE_INTERFACE_V1"


def _nonempty_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(field)
    if any(not isinstance(x, str) or not x for x in value):
        raise ValueError(field)
    return value


def evaluate(
    spec: Mapping[str, Any],
    receipts: Sequence[Mapping[str, Any]],
    *,
    verified_evidence_ids: Sequence[str],
) -> dict[str, Any]:
    """Verify a complete discovery interface without assuming tool identities.

    Soundness boundary:
    - This function verifies structure and evidence binding.
    - It never manufactures source-set completeness.
    - The source-set completeness evidence must already be independently verified.
    """
    try:
        scope_id = spec.get("scope_id")
        if not isinstance(scope_id, str) or not scope_id:
            raise ValueError("scope_id")
        source_ids = _nonempty_strings(spec.get("declared_source_ids"), "declared_source_ids")
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("declared_source_ids_duplicate")
        source_set_evidence_id = spec.get("source_set_completeness_evidence_id")
        if not isinstance(source_set_evidence_id, str) or not source_set_evidence_id:
            raise ValueError("source_set_completeness_evidence_id")
        if spec.get("unknown_identity_discovery_required") is not True:
            raise ValueError("unknown_identity_discovery_required")
        if spec.get("preenumerated_tool_ids_required") is not False:
            raise ValueError("preenumerated_tool_ids_required")
    except ValueError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__INVALID_SPEC",
            "errors": [str(exc)],
            "admit_interface": False,
            "target_proof_atom_discharged": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    verified = set()
    if isinstance(verified_evidence_ids, (list, tuple, set)) and all(
        isinstance(x, str) and x for x in verified_evidence_ids
    ):
        verified = set(verified_evidence_ids)
    else:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__INVALID_VERIFIED_EVIDENCE_SET",
            "errors": ["verified_evidence_ids"],
            "admit_interface": False,
            "target_proof_atom_discharged": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    errors: list[str] = []
    if source_set_evidence_id not in verified:
        errors.append("UNVERIFIED_SOURCE_SET_COMPLETENESS")

    by_source: dict[str, Mapping[str, Any]] = {}
    declared = set(source_ids)
    for i, rec in enumerate(receipts):
        if not isinstance(rec, Mapping):
            errors.append(f"INVALID_RECEIPT:{i}")
            continue
        if rec.get("kind") != "COMPLETE_DISCOVERY_RESULT":
            errors.append(f"INVALID_RECEIPT_KIND:{i}")
            continue
        sid = rec.get("source_id")
        if not isinstance(sid, str) or not sid:
            errors.append(f"INVALID_SOURCE_ID:{i}")
            continue
        if sid not in declared:
            errors.append(f"UNDECLARED_SOURCE:{sid}")
            continue
        if sid in by_source:
            errors.append(f"DUPLICATE_SOURCE_RECEIPT:{sid}")
            continue
        if rec.get("scope_id") != scope_id:
            errors.append(f"SCOPE_MISMATCH:{sid}")
            continue
        if rec.get("exhaustive_for_scope") is not True:
            errors.append(f"SOURCE_NOT_EXHAUSTIVE:{sid}")
            continue
        eid = rec.get("completeness_evidence_id")
        if not isinstance(eid, str) or eid not in verified:
            errors.append(f"UNVERIFIED_SOURCE_COMPLETENESS:{sid}")
            continue
        tool_ids = rec.get("tool_ids")
        if not isinstance(tool_ids, list) or any(not isinstance(x, str) or not x for x in tool_ids):
            errors.append(f"INVALID_TOOL_IDS:{sid}")
            continue
        by_source[sid] = rec

    missing = sorted(declared - set(by_source))
    if missing:
        errors.extend(f"MISSING_SOURCE_RECEIPT:{sid}" for sid in missing)

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__INCOMPLETE_OR_UNVERIFIED_DISCOVERY_INTERFACE",
            "errors": sorted(set(errors)),
            "admit_interface": False,
            "target_proof_atom_discharged": False,
            "covered_tool_ids": [],
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    covered = sorted(
        {
            tool_id
            for sid in source_ids
            for tool_id in by_source[sid].get("tool_ids", [])
        }
    )

    return {
        "schema": SCHEMA,
        "status": "PASS__VERIFIED_COMPLETE_DISCOVERY_INTERFACE_CONDITIONAL_THEOREM",
        "admit_interface": True,
        "scope_id": scope_id,
        "declared_source_ids": source_ids,
        "source_set_completeness_evidence_id": source_set_evidence_id,
        "covered_tool_ids": covered,
        "unknown_identity_discovery_covered": True,
        "preenumerated_tool_ids_required": False,
        "conditional_theorem": (
            "IF_SOURCE_SET_COMPLETENESS_AND_PER_SOURCE_EXHAUSTIVENESS_ARE_INDEPENDENTLY_VERIFIED"
            "__THEN_ARBITRARY_RECEIPT_RETURNED_TOOL_IDENTITIES_ARE_SCOPE_COVERED"
        ),
        "conditional_implication_proved": True,
        "target_proof_atom_discharged": False,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
