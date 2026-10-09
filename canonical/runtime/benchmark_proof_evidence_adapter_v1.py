"""Adapter from benchmark proof-kernel verdicts to canonical acceptance-ledger candidates.

This module does not edit the ledger and has no promotion authority.  It only
produces a row shaped like OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V3
after proving that the predicate exists in the frozen registry and that the
kernel verdict is PROVEN.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_BENCHMARK_PROOF_EVIDENCE_ADAPTER_V1"

def _hex40(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(ch in "0123456789abcdef" for ch in value)
    )

def _binding(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and bool(value["path"].strip())
        and _hex40(value.get("git_blob_sha"))
    )

def _registry_rows(registry: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = registry.get("predicates")
    if not isinstance(rows, list):
        return {}
    return {
        row["id"]: row
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("id"), str)
    }

def adapt(
    kernel_verdict: Mapping[str, Any],
    verification_receipt_binding: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    pid = kernel_verdict.get("predicate_id")
    rows = _registry_rows(registry)

    if registry.get("schema") != "PROJECT_BRAIN_OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2":
        errors.append("FROZEN_REGISTRY_SCHEMA_MISMATCH")
    if kernel_verdict.get("schema") != "PROJECT_BRAIN_BENCHMARK_CLAIM_KERNEL_V4":
        errors.append("KERNEL_SCHEMA_MISMATCH")
    if kernel_verdict.get("status") != "PROVEN":
        errors.append("KERNEL_VERDICT_NOT_PROVEN")
    if kernel_verdict.get("promotion_authority") is not False:
        errors.append("KERNEL_MUST_HAVE_ZERO_PROMOTION_AUTHORITY")
    if kernel_verdict.get("terminal_credit") != 0:
        errors.append("KERNEL_TERMINAL_CREDIT_MUST_BE_ZERO")
    if not isinstance(pid, str) or pid not in rows:
        errors.append("PREDICATE_NOT_IN_FROZEN_REGISTRY")
    if not _binding(verification_receipt_binding):
        errors.append("VERIFICATION_RECEIPT_BINDING_INVALID")

    family = rows.get(pid, {}).get("family") if isinstance(pid, str) else None
    candidate = None
    if not errors:
        candidate = {
            "predicate_id": pid,
            "state": "PROVED",
            "proof_kind": "BENCHMARK_PROOF_KERNEL_V4",
            "source_path": verification_receipt_binding["path"],
            "source_sha": verification_receipt_binding["git_blob_sha"],
            "independent_or_objective": True,
            "scope_complete": kernel_verdict.get("locks", {}).get("scope") == "PASS",
            "family": family,
            "basis": (
                "V4_PROOF_KERNEL_PROVEN__IDENTITY_SCOPE_POLICY_FREEZE_PROVENANCE_"
                "EVALUATOR_EVIDENCE_FRESHNESS_AND_V3_PROOF_RELATION_LOCKS_PASS"
            ),
            "promotion_authority": False,
            "terminal_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "errors": sorted(set(errors)),
        "predicate_id": pid,
        "family": family,
        "candidate_claim": candidate,
        "ledger_target_schema": "PROJECT_BRAIN_OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V3",
        "promotion_authority": False,
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "rule": (
            "ADAPTER_NEVER_EDITS_OR_PROMOTES_THE_LEDGER__ONLY_EXISTING_GOVERNANCE_"
            "MAY_PROMOTE_AN_INDEPENDENTLY_VERIFIED_CONTENT_ADDRESSED_CANDIDATE"
        ),
    }
