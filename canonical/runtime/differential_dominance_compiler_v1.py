"""Fail-closed finite differential-dominance compiler.

This compiler proves only a bounded, finite noninferiority relation. It never samples
or simulates a comparator. Given a frozen complete case universe and authoritative
case-level evidence, it asks whether any case can satisfy:

    comparator_success AND NOT brain_success

A candidate dominance witness is emitted only when every case in the declared
universe is eliminated by either:
  * verified Brain success under the shared success criterion,
  * verified comparator failure, or
  * an authoritative verified proof that comparator success is impossible.

Missing or merely unverified evidence remains an explicit residual. The compiler
grants no capability, family, acceptance, execution, or promotion authority.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_DIFFERENTIAL_DOMINANCE_COMPILER_V1"

AUTHORITATIVE_EXCLUSION_PROOF_KINDS = {
    "FORMAL_PROOF",
    "THEORETICAL_IMPOSSIBILITY",
    "EXHAUSTIVE_FINITE_VERIFICATION",
    "INDEPENDENT_VERIFIED_BOUNDED_ENVELOPE",
    "INDEPENDENT_VERIFIED_SCOPE_EQUIVALENT_PROTOCOL",
}
_ALLOWED_STATUS = {"SUCCESS", "FAILURE", "UNKNOWN"}


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "candidate_witness": None,
        "verified_counterexamples": [],
        "residual_case_ids": [],
        "differential_dominance_proved": False,
        "fresh_terminal_evidence_consumed": 0,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _outcome(row: Any, *, side: str, errors: list[str]) -> tuple[str, bool, str | None]:
    if row is None:
        return "UNKNOWN", False, None
    if not isinstance(row, Mapping):
        errors.append(f"{side.upper()}_OUTCOME_INVALID")
        return "UNKNOWN", False, None
    status = row.get("status", "UNKNOWN")
    if status not in _ALLOWED_STATUS:
        errors.append(f"{side.upper()}_STATUS_INVALID")
        return "UNKNOWN", False, None
    verified = row.get("verified") is True
    receipt = row.get("receipt")
    if verified and status != "UNKNOWN" and not _nonempty_str(receipt):
        errors.append(f"{side.upper()}_VERIFIED_OUTCOME_RECEIPT_REQUIRED")
        return status, False, None
    return status, verified, receipt if _nonempty_str(receipt) else None


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(doc, Mapping):
        return _fail("INPUT_NOT_OBJECT")

    predicate_id = doc.get("predicate_id")
    if not _nonempty_str(predicate_id):
        return _fail("PREDICATE_ID_REQUIRED")
    predicate_id = str(predicate_id).strip()

    scope = doc.get("scope")
    if not isinstance(scope, Mapping):
        return _fail("SCOPE_REQUIRED")
    scope_id = scope.get("scope_id")
    if not _nonempty_str(scope_id):
        errors.append("SCOPE_ID_REQUIRED")
        scope_id = None

    for field in (
        "frozen",
        "complete",
        "finite",
        "independently_verified",
        "shared_success_criterion",
        "shared_authority_boundary",
        "contamination_clean",
    ):
        if scope.get(field) is not True:
            errors.append(f"SCOPE_{field.upper()}_MUST_BE_TRUE")
    if not _nonempty_str(scope.get("scope_receipt")):
        errors.append("SCOPE_RECEIPT_REQUIRED")
    if not _nonempty_str(scope.get("criterion_receipt")):
        errors.append("CRITERION_RECEIPT_REQUIRED")

    case_ids = scope.get("case_ids")
    if (
        not isinstance(case_ids, list)
        or not case_ids
        or any(not _nonempty_str(x) for x in case_ids)
        or len(case_ids) != len(set(case_ids))
    ):
        errors.append("SCOPE_CASE_IDS_INVALID")
        case_ids = []
    else:
        case_ids = [str(x).strip() for x in case_ids]

    cases = doc.get("cases")
    if not isinstance(cases, list):
        errors.append("CASES_REQUIRED")
        cases = []

    parsed: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(cases):
        if not isinstance(row, Mapping):
            errors.append(f"CASE_{i}_INVALID")
            continue
        cid = row.get("case_id")
        if not _nonempty_str(cid):
            errors.append(f"CASE_{i}_ID_REQUIRED")
            continue
        cid = str(cid).strip()
        if cid in parsed:
            errors.append(f"DUPLICATE_CASE_ID:{cid}")
            continue
        parsed[cid] = row

    if case_ids and set(parsed) != set(case_ids):
        missing = sorted(set(case_ids) - set(parsed))
        extra = sorted(set(parsed) - set(case_ids))
        if missing:
            errors.append("MISSING_CASE_ROWS:" + ",".join(missing))
        if extra:
            errors.append("EXTRA_CASE_ROWS:" + ",".join(extra))
    if errors:
        return _fail(*errors)

    verified_counterexamples: list[dict[str, Any]] = []
    residual_case_ids: list[str] = []
    resolved: list[dict[str, Any]] = []

    for cid in case_ids:
        row = parsed[cid]
        row_errors: list[str] = []
        brain_status, brain_verified, brain_receipt = _outcome(
            row.get("brain"), side="brain", errors=row_errors
        )
        comp_status, comp_verified, comp_receipt = _outcome(
            row.get("comparator"), side="comparator", errors=row_errors
        )
        if row_errors:
            return _fail(*(f"{cid}:{e}" for e in row_errors))

        if (
            brain_status == "FAILURE"
            and brain_verified
            and comp_status == "SUCCESS"
            and comp_verified
        ):
            verified_counterexamples.append({
                "case_id": cid,
                "brain_receipt": brain_receipt,
                "comparator_receipt": comp_receipt,
            })
            continue

        if brain_status == "SUCCESS" and brain_verified:
            resolved.append({
                "case_id": cid,
                "basis": "VERIFIED_BRAIN_SUCCESS",
                "receipt": brain_receipt,
            })
            continue

        if comp_status == "FAILURE" and comp_verified:
            resolved.append({
                "case_id": cid,
                "basis": "VERIFIED_COMPARATOR_FAILURE",
                "receipt": comp_receipt,
            })
            continue

        exclusion = row.get("comparator_success_exclusion")
        if exclusion is not None:
            if not isinstance(exclusion, Mapping):
                return _fail(f"{cid}:COMPARATOR_SUCCESS_EXCLUSION_INVALID")
            if exclusion.get("comparator_success_impossible") is not True:
                return _fail(f"{cid}:EXCLUSION_MUST_ASSERT_COMPARATOR_SUCCESS_IMPOSSIBLE")
            proof_kind = exclusion.get("proof_kind")
            verified = exclusion.get("verified") is True
            receipt = exclusion.get("receipt")
            scope_complete = exclusion.get("scope_complete_for_case") is True
            if (
                verified
                and scope_complete
                and proof_kind in AUTHORITATIVE_EXCLUSION_PROOF_KINDS
                and _nonempty_str(receipt)
            ):
                resolved.append({
                    "case_id": cid,
                    "basis": "VERIFIED_COMPARATOR_SUCCESS_IMPOSSIBLE",
                    "proof_kind": proof_kind,
                    "receipt": receipt,
                })
                continue

        residual_case_ids.append(cid)

    if verified_counterexamples:
        return {
            "schema": SCHEMA,
            "status": "VERIFIED_DIFFERENTIAL_COUNTEREXAMPLE",
            "errors": [],
            "predicate_id": predicate_id,
            "scope_id": scope_id,
            "case_count": len(case_ids),
            "resolved_case_count": len(resolved),
            "verified_counterexamples": verified_counterexamples,
            "residual_case_ids": sorted(residual_case_ids),
            "candidate_witness": None,
            "differential_dominance_proved": False,
            "reason": "AT_LEAST_ONE_VERIFIED_CASE_HAS_COMPARATOR_SUCCESS_AND_BRAIN_FAILURE",
            "fresh_terminal_evidence_consumed": 0,
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    if residual_case_ids:
        return {
            "schema": SCHEMA,
            "status": "DIFFERENTIAL_RESIDUAL_OPEN",
            "errors": [],
            "predicate_id": predicate_id,
            "scope_id": scope_id,
            "case_count": len(case_ids),
            "resolved_case_count": len(resolved),
            "verified_counterexamples": [],
            "residual_case_ids": sorted(residual_case_ids),
            "residual_obligations": [{
                "case_id": cid,
                "query": "DETERMINE_WHETHER_COMPARATOR_SUCCESS_AND_BRAIN_FAILURE_IS_POSSIBLE",
            } for cid in sorted(residual_case_ids)],
            "candidate_witness": None,
            "differential_dominance_proved": False,
            "reason": "COMPLETE_SCOPE_KNOWN_BUT_DIFFERENTIAL_LOSS_REMAINS_POSSIBLE_ON_RESIDUAL_CASES",
            "fresh_terminal_evidence_consumed": 0,
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    witness = {
        "id": f"DIFFERENTIAL_DOMINANCE::{predicate_id}::{scope_id}",
        "predicate_id": predicate_id,
        "mode": "FINITE_COMPLETE_DIFFERENTIAL_DOMINANCE",
        "verified": False,
        "independent": False,
        "contamination_clean": True,
        "binds_frozen_predicate": True,
        "scope_relation": "EXACT",
        "scope_id": scope_id,
        "scope_case_count": len(case_ids),
        "proves_noninferiority_on_declared_scope": True,
        "reason": "NO_CASE_IN_THE_COMPLETE_FROZEN_SCOPE_CAN_SATISFY_COMPARATOR_SUCCESS_AND_BRAIN_FAILURE",
    }
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_DIFFERENTIAL_DOMINANCE_READY__INDEPENDENT_VERIFICATION_REQUIRED",
        "errors": [],
        "predicate_id": predicate_id,
        "scope_id": scope_id,
        "case_count": len(case_ids),
        "resolved_case_count": len(resolved),
        "resolution_basis": resolved,
        "verified_counterexamples": [],
        "residual_case_ids": [],
        "candidate_witness": witness,
        "differential_dominance_proved": True,
        "fresh_terminal_evidence_consumed": 0,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
