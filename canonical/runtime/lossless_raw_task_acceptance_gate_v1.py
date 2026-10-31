"""Lossless raw-task acceptance completeness gate.

This is the universal acceptance *normal form*, not a universal judge.

Input:
- a lossless_raw_task_contract_v1 contract preserving every non-whitespace source
  segment as an acceptance obligation;
- the exact candidate artifact/content digest being judged;
- one content-addressed acceptance receipt + one separate content-addressed
  independent-verification receipt for every required raw obligation.

Different obligations may be discharged by different verifier classes:
FORMAL, DETERMINISTIC, CONFIGURED_JUDGMENT, HUMAN_AUTHORIZED, or DOMAIN_SPECIFIC.
The gate does not trust the class label alone. Every receipt is exact-byte bound,
and the independent verification must attest the acceptance semantics.

No obligation may be missing, duplicated, or silently ignored.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence
import re

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)

SCHEMA = "PROJECT_BRAIN_LOSSLESS_RAW_TASK_ACCEPTANCE_GATE_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_RAW_TASK_OBLIGATION_ACCEPTANCE_RECEIPT_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_RAW_TASK_OBLIGATION_ACCEPTANCE_INDEPENDENT_VERIFICATION_V1"
ALLOWED_VERIFIER_CLASSES = {
    "FORMAL",
    "DETERMINISTIC",
    "CONFIGURED_JUDGMENT",
    "HUMAN_AUTHORIZED",
    "DOMAIN_SPECIFIC",
}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class AcceptanceGateError(ValueError):
    pass


def _token(v: Any, label: str) -> str:
    if not isinstance(v, str) or not v.strip() or "\x00" in v:
        raise AcceptanceGateError(label + "_INVALID")
    return v.strip()


def _sha64(v: Any, label: str) -> str:
    value = _token(v, label).lower()
    if _HEX64.fullmatch(value) is None:
        raise AcceptanceGateError(label + "_INVALID")
    return value


def _contract_obligations(task_contract: Mapping[str, Any]) -> tuple[str, str, dict[str, Mapping[str, Any]]]:
    if not isinstance(task_contract, Mapping):
        raise AcceptanceGateError("TASK_CONTRACT_NOT_OBJECT")
    if task_contract.get("schema") != "PROJECT_BRAIN_LOSSLESS_RAW_TASK_CONTRACT_V1":
        raise AcceptanceGateError("TASK_CONTRACT_SCHEMA_INVALID")
    if task_contract.get("pass") is not True:
        raise AcceptanceGateError("TASK_CONTRACT_NOT_PASS")
    if task_contract.get("status") != "COMPILED__LOSSLESS_RAW_TASK_ACCEPTANCE_CONTRACT":
        raise AcceptanceGateError("TASK_CONTRACT_STATUS_INVALID")

    task_contract_sha = _sha64(task_contract.get("task_contract_sha256"), "TASK_CONTRACT_SHA256")
    task_sha = _sha64(task_contract.get("task_sha256"), "TASK_SHA256")
    ac = task_contract.get("acceptance_contract")
    if not isinstance(ac, Mapping):
        raise AcceptanceGateError("ACCEPTANCE_CONTRACT_MISSING")
    rows = ac.get("obligations")
    required_ids = ac.get("required_obligation_ids")
    if not isinstance(rows, list) or not rows:
        raise AcceptanceGateError("ACCEPTANCE_OBLIGATIONS_INVALID")
    if not isinstance(required_ids, list) or not required_ids:
        raise AcceptanceGateError("REQUIRED_OBLIGATION_IDS_INVALID")

    by_id: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise AcceptanceGateError("ACCEPTANCE_OBLIGATION_NOT_OBJECT:" + str(i))
        oid = _token(row.get("obligation_id"), "OBLIGATION_ID")
        if oid in by_id:
            raise AcceptanceGateError("OBLIGATION_ID_DUPLICATE:" + oid)
        if row.get("kind") != "RAW_SOURCE_SEGMENT_ACCEPTANCE":
            raise AcceptanceGateError("OBLIGATION_KIND_INVALID:" + oid)
        _sha64(row.get("segment_sha256"), "SEGMENT_SHA256")
        if row.get("acceptance_receipt_required") is not True:
            raise AcceptanceGateError("OBLIGATION_RECEIPT_REQUIREMENT_DISABLED:" + oid)
        by_id[oid] = row

    normalized_required = [_token(x, "REQUIRED_OBLIGATION_ID") for x in required_ids]
    if len(normalized_required) != len(set(normalized_required)):
        raise AcceptanceGateError("REQUIRED_OBLIGATION_ID_DUPLICATE")
    if set(normalized_required) != set(by_id):
        raise AcceptanceGateError("REQUIRED_OBLIGATION_SET_MISMATCH")
    if ac.get("raw_source_is_final_semantic_reference") is not True:
        raise AcceptanceGateError("RAW_SOURCE_SEMANTIC_AUTHORITY_NOT_BOUND")
    if ac.get("unverified_obligation_may_be_silently_dropped") is not False:
        raise AcceptanceGateError("SILENT_OBLIGATION_DROP_NOT_FORBIDDEN")
    return task_contract_sha, task_sha, by_id


def evaluate(
    task_contract: Mapping[str, Any],
    *,
    candidate_sha256: str,
    obligation_receipts: Sequence[Mapping[str, Any]],
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        candidate_sha = _sha64(candidate_sha256, "CANDIDATE_SHA256")
        contract_sha, task_sha, obligations = _contract_obligations(task_contract)
        if not isinstance(obligation_receipts, Sequence) or isinstance(obligation_receipts, (str, bytes)):
            raise AcceptanceGateError("OBLIGATION_RECEIPTS_INVALID")

        accepted: dict[str, dict[str, Any]] = {}
        for i, pair in enumerate(obligation_receipts):
            if not isinstance(pair, Mapping):
                raise AcceptanceGateError("OBLIGATION_RECEIPT_PAIR_INVALID:" + str(i))
            try:
                rr = resolve_receipt_bytes(pair.get("receipt"), repo_root=repo_root)
                vr = resolve_receipt_bytes(pair.get("verification"), repo_root=repo_root)
            except ReceiptResolutionError as exc:
                raise AcceptanceGateError("OBLIGATION_RECEIPT_RESOLUTION_FAILED:" + str(exc)) from exc

            rd = rr["document"]
            vd = vr["document"]
            if rd.get("schema") != RECEIPT_SCHEMA:
                raise AcceptanceGateError("ACCEPTANCE_RECEIPT_SCHEMA_INVALID:" + str(i))
            if vd.get("schema") != VERIFY_SCHEMA:
                raise AcceptanceGateError("ACCEPTANCE_VERIFY_SCHEMA_INVALID:" + str(i))
            if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
                raise AcceptanceGateError("ACCEPTANCE_VERIFY_SUBJECT_MISMATCH:" + str(i))

            oid = _token(rd.get("obligation_id"), "OBLIGATION_ID")
            if oid not in obligations:
                raise AcceptanceGateError("RECEIPT_FOR_UNKNOWN_OBLIGATION:" + oid)
            if oid in accepted:
                raise AcceptanceGateError("DUPLICATE_ACCEPTANCE_RECEIPT:" + oid)
            row = obligations[oid]
            verifier_class = _token(rd.get("verifier_class"), "VERIFIER_CLASS")
            if verifier_class not in ALLOWED_VERIFIER_CLASSES:
                raise AcceptanceGateError("VERIFIER_CLASS_INVALID:" + oid)
            verifier_id = _token(rd.get("verifier_id"), "VERIFIER_ID")

            required_receipt = {
                "task_contract_sha256": contract_sha,
                "task_sha256": task_sha,
                "obligation_id": oid,
                "segment_sha256": row["segment_sha256"],
                "candidate_sha256": candidate_sha,
                "accepted": True,
            }
            for key, expected in required_receipt.items():
                if rd.get(key) != expected:
                    raise AcceptanceGateError("ACCEPTANCE_RECEIPT_MISMATCH:" + oid + ":" + key)

            required_verify = {
                "task_contract_sha256": contract_sha,
                "task_sha256": task_sha,
                "obligation_id": oid,
                "segment_sha256": row["segment_sha256"],
                "candidate_sha256": candidate_sha,
                "verifier_class": verifier_class,
                "verifier_id": verifier_id,
                "accepted": True,
                "pass": True,
                "independent_verified": True,
                "acceptance_semantics_verified": True,
            }
            for key, expected in required_verify.items():
                if vd.get(key) != expected:
                    raise AcceptanceGateError("ACCEPTANCE_VERIFY_MISMATCH:" + oid + ":" + key)
            independent_verifier_id = _token(
                vd.get("independent_verifier_id"), "INDEPENDENT_VERIFIER_ID"
            )
            accepted[oid] = {
                "obligation_id": oid,
                "verifier_class": verifier_class,
                "verifier_id": verifier_id,
                "independent_verifier_id": independent_verifier_id,
                "receipt": {"path": rr["path"], "git_blob_sha": rr["git_blob_sha"]},
                "verification": {"path": vr["path"], "git_blob_sha": vr["git_blob_sha"]},
            }

        missing = sorted(set(obligations) - set(accepted))
        if missing:
            return {
                "schema": SCHEMA,
                "status": "UNRESOLVED__RAW_TASK_ACCEPTANCE_OBLIGATIONS_MISSING",
                "pass": False,
                "task_contract_sha256": contract_sha,
                "task_sha256": task_sha,
                "candidate_sha256": candidate_sha,
                "required_obligation_count": len(obligations),
                "accepted_obligation_count": len(accepted),
                "missing_obligation_ids": missing,
                "accepted_obligations": [accepted[x] for x in sorted(accepted)],
                "terminal_authority": False,
            }

        return {
            "schema": SCHEMA,
            "status": "PASS__EVERY_RAW_TASK_OBLIGATION_INDEPENDENTLY_ACCEPTED",
            "pass": True,
            "task_contract_sha256": contract_sha,
            "task_sha256": task_sha,
            "candidate_sha256": candidate_sha,
            "required_obligation_count": len(obligations),
            "accepted_obligation_count": len(accepted),
            "missing_obligation_ids": [],
            "accepted_obligations": [accepted[x] for x in sorted(accepted)],
            "routing_effects_were_acceptance_authority": False,
            "raw_task_semantic_omission_detected": False,
            "terminal_authority": False,
            "hard_rule": (
                "ALL_RAW_SOURCE_SEGMENTS_REQUIRE_EXACT_CANDIDATE_BOUND_ACCEPTANCE_AND_SEPARATE_INDEPENDENT_VERIFICATION"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }


def verify(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Universal-solver verifier interface."""
    if not isinstance(payload, Mapping):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "PAYLOAD_INVALID"}
    if not isinstance(proposal, Mapping):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "PROPOSAL_INVALID"}
    allowed_payload = {"task_contract", "candidate_sha256", "repo_root"}
    if set(payload) != allowed_payload:
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "PAYLOAD_FIELDS_INVALID"}
    if set(proposal) != {"obligation_receipts"}:
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "PROPOSAL_FIELDS_INVALID"}
    result = evaluate(
        payload["task_contract"],
        candidate_sha256=payload["candidate_sha256"],
        obligation_receipts=proposal["obligation_receipts"],
        repo_root=payload["repo_root"],
    )
    ok = result.get("pass") is True
    return {
        "schema": SCHEMA,
        "pass": ok,
        "status": "VERIFIED" if ok else (
            "NEED_MORE_INFORMATION"
            if str(result.get("status") or "").startswith("UNRESOLVED")
            else "FALSIFIED"
        ),
        "reason": None if ok else result.get("status"),
        "detail": result,
        "verified_output": {
            "candidate_sha256": result.get("candidate_sha256"),
            "accepted_obligation_count": result.get("accepted_obligation_count"),
            "required_obligation_count": result.get("required_obligation_count"),
        } if ok else None,
        "terminal_authority": False,
    }
