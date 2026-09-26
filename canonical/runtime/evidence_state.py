#!/usr/bin/env python3
"""Machine-enforced epistemic state and evidence receipts for Project Brain."""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
from typing import Any

STATES=("DESIGNED","IMPLEMENTED","EXECUTED","VERIFIED","PROMOTED")
_NEXT={
    "DESIGNED":"IMPLEMENTED",
    "IMPLEMENTED":"EXECUTED",
    "EXECUTED":"VERIFIED",
    "VERIFIED":"PROMOTED",
}
_SHA40=re.compile(r"^[0-9a-f]{40}$")
_SHA64=re.compile(r"^[0-9a-f]{64}$")


class EvidenceError(RuntimeError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise EvidenceError(code)


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        .encode("utf-8")
    )


def receipt_sha256(receipt: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(receipt)).hexdigest()


def validate_transition(previous: str | None, current: str) -> None:
    _require(current in STATES,"EPISTEMIC_STATE_INVALID")
    if previous is None:
        _require(current=="DESIGNED","EPISTEMIC_INITIAL_STATE_MUST_BE_DESIGNED")
        return
    _require(previous in STATES,"EPISTEMIC_PREVIOUS_STATE_INVALID")
    _require(_NEXT.get(previous)==current,"EPISTEMIC_STATE_JUMP_FORBIDDEN")


def validate_receipt(receipt: dict[str, Any], previous: dict[str, Any] | None=None) -> dict[str, Any]:
    _require(receipt.get("schema")=="PROJECT_BRAIN_EVIDENCE_RECEIPT_V1","EVIDENCE_SCHEMA_INVALID")
    artifact_id=str(receipt.get("artifact_id") or "").strip()
    _require(bool(artifact_id),"EVIDENCE_ARTIFACT_ID_MISSING")
    state=str(receipt.get("state") or "").strip().upper()

    previous_state=None if previous is None else str(previous.get("state") or "").upper()
    validate_transition(previous_state,state)

    if previous is not None:
        _require(previous.get("artifact_id")==artifact_id,"EVIDENCE_ARTIFACT_ID_CHANGED")
        expected_prev=receipt_sha256(previous)
        _require(
            receipt.get("previous_receipt_sha256")==expected_prev,
            "EVIDENCE_CHAIN_MISMATCH",
        )

    if state in {"IMPLEMENTED","EXECUTED","VERIFIED","PROMOTED"}:
        revision=str(receipt.get("revision_sha") or "").lower()
        _require(bool(_SHA40.fullmatch(revision)),"EVIDENCE_REVISION_SHA_INVALID")

    if state=="EXECUTED":
        execution=receipt.get("execution") or {}
        _require(bool(str(execution.get("executor_id") or "").strip()),"EXECUTION_EXECUTOR_MISSING")
        _require(bool(str(execution.get("platform") or "").strip()),"EXECUTION_PLATFORM_MISSING")
        _require(bool(str(execution.get("command") or "").strip()),"EXECUTION_COMMAND_MISSING")
        _require(isinstance(execution.get("exit_code"),int),"EXECUTION_EXIT_CODE_MISSING")
        _require(bool(_SHA64.fullmatch(str(execution.get("stdout_sha256") or "").lower())),"EXECUTION_STDOUT_HASH_INVALID")
        _require(bool(_SHA64.fullmatch(str(execution.get("stderr_sha256") or "").lower())),"EXECUTION_STDERR_HASH_INVALID")
        spend=execution.get("incremental_spend_usd")
        _require(spend==0 or spend==0.0,"EXECUTION_NONZERO_SPEND")

    if state=="VERIFIED":
        verification=receipt.get("verification") or {}
        _require(verification.get("verified") is True,"VERIFICATION_NOT_TRUE")
        _require(bool(str(verification.get("verifier_id") or "").strip()),"VERIFIER_ID_MISSING")
        _require(bool(_SHA64.fullmatch(str(verification.get("executed_receipt_sha256") or "").lower())),"VERIFIED_EXECUTION_RECEIPT_HASH_INVALID")
        _require(
            previous is not None
            and receipt_sha256(previous)==verification.get("executed_receipt_sha256"),
            "VERIFIED_EXECUTION_RECEIPT_MISMATCH",
        )
        predicates=verification.get("predicates")
        _require(isinstance(predicates,list) and len(predicates)>0,"VERIFICATION_PREDICATES_MISSING")
        _require(all(x is True for x in predicates),"VERIFICATION_PREDICATE_FAILED")

    if state=="PROMOTED":
        promotion=receipt.get("promotion") or {}
        _require(bool(_SHA64.fullmatch(str(promotion.get("verified_receipt_sha256") or "").lower())),"PROMOTION_VERIFIED_RECEIPT_HASH_INVALID")
        _require(
            previous is not None
            and receipt_sha256(previous)==promotion.get("verified_receipt_sha256"),
            "PROMOTION_VERIFIED_RECEIPT_MISMATCH",
        )
        merge_sha=str(promotion.get("merge_commit_sha") or "").lower()
        _require(bool(_SHA40.fullmatch(merge_sha)),"PROMOTION_MERGE_SHA_INVALID")
        _require(bool(str(promotion.get("canonical_ref") or "").strip()),"PROMOTION_CANONICAL_REF_MISSING")

    return receipt


def append_receipt(path: str | pathlib.Path, receipt: dict[str, Any]) -> str:
    p=pathlib.Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    previous=None
    if p.exists():
        lines=[x for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        if lines:
            previous=json.loads(lines[-1])
    validate_receipt(receipt,previous)
    with p.open("a",encoding="utf-8",newline="\n") as fh:
        fh.write(canonical_json(receipt).decode("utf-8")+"\n")
    return receipt_sha256(receipt)


def load_ledger(path: str | pathlib.Path) -> list[dict[str, Any]]:
    p=pathlib.Path(path)
    if not p.exists():
        return []
    receipts=[]
    previous=None
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        receipt=json.loads(line)
        validate_receipt(receipt,previous)
        receipts.append(receipt)
        previous=receipt
    return receipts
