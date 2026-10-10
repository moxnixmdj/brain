from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LOGICAL_ATTEMPT_IDENTITY_V2"
_TASK_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CLAIM_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class LogicalAttemptIdentityError(ValueError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def logical_attempt_id(
    *,
    slot_id: str,
    task_digest: str,
    execution_claim_binding_digest: str,
) -> str:
    slot_id = str(slot_id or "").strip()
    task_digest = str(task_digest or "").strip()
    execution_claim_binding_digest = str(execution_claim_binding_digest or "").strip()

    if not slot_id:
        raise LogicalAttemptIdentityError("SLOT_ID_REQUIRED")
    if len(slot_id) > 4096:
        raise LogicalAttemptIdentityError("SLOT_ID_TOO_LONG")
    if _TASK_DIGEST_RE.fullmatch(task_digest) is None:
        raise LogicalAttemptIdentityError("TASK_DIGEST_INVALID")
    if _CLAIM_DIGEST_RE.fullmatch(execution_claim_binding_digest) is None:
        raise LogicalAttemptIdentityError("EXECUTION_CLAIM_BINDING_DIGEST_INVALID")

    material = {
        "schema": SCHEMA,
        "slot_id": slot_id,
        "task_digest": task_digest,
        "execution_claim_binding_digest": execution_claim_binding_digest,
    }
    return hashlib.sha256(_canonical_bytes(material)).hexdigest()


def logical_attempt_identity(
    *,
    slot_id: str,
    task_digest: str,
    execution_claim_binding_digest: str,
) -> dict[str, str]:
    slot_id = str(slot_id or "").strip()
    task_digest = str(task_digest or "").strip()
    execution_claim_binding_digest = str(execution_claim_binding_digest or "").strip()
    return {
        "schema": SCHEMA,
        "slot_id": slot_id,
        "task_digest": task_digest,
        "execution_claim_binding_digest": execution_claim_binding_digest,
        "logical_attempt_id": logical_attempt_id(
            slot_id=slot_id,
            task_digest=task_digest,
            execution_claim_binding_digest=execution_claim_binding_digest,
        ),
    }


__all__ = [
    "SCHEMA",
    "LogicalAttemptIdentityError",
    "logical_attempt_id",
    "logical_attempt_identity",
]
