"""Content-binding adapter for composition_state_capsule_v1.

V1 deliberately treats action_ref and evidence_refs as caller-supplied tokens.
This adapter converts actual JSON action/evidence referents into content-addressed
tokens, appends through the V1 capsule, and returns a receipt that can be
revalidated against the exact referent contents.

The adapter does not prove no-bypass. Direct V1 callers remain possible until
the shared channel graph proves every credited action/evidence path is mediated.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.composition_state_capsule_v1 import (
    CapsuleError,
    append_macrostep,
    verify_capsule,
)

SCHEMA = "PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_REFERENT_BINDING_V1"


class ReferentBindingError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def content_sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _logical_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReferentBindingError(label + "_INVALID")
    text = value.strip()
    if any(ch in text for ch in ("@", "\n", "\r")):
        raise ReferentBindingError(label + "_UNSAFE")
    return text


def action_token(action: Any) -> str:
    return "sha256:" + content_sha256(action)


def evidence_token(logical_id: str, evidence: Any) -> str:
    lid = _logical_id(logical_id, "EVIDENCE_ID")
    return lid + "@sha256:" + content_sha256(evidence)


def _transform_lineage(
    lineage: Mapping[str, Sequence[str]],
    action_ref: str,
    evidence_tokens: Mapping[str, str],
) -> dict[str, list[str]]:
    if not isinstance(lineage, Mapping):
        raise ReferentBindingError("LINEAGE_INVALID")
    out: dict[str, list[str]] = {}
    for output, refs in lineage.items():
        if not isinstance(output, str) or not output:
            raise ReferentBindingError("LINEAGE_OUTPUT_INVALID")
        if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes, bytearray)):
            raise ReferentBindingError("LINEAGE_REFS_INVALID:" + output)
        transformed: list[str] = []
        for raw in refs:
            if not isinstance(raw, str) or not raw:
                raise ReferentBindingError("LINEAGE_REF_INVALID:" + output)
            if raw == "action":
                transformed.append("action:" + action_ref)
            elif raw.startswith("state:"):
                transformed.append(raw)
            elif raw.startswith("evidence:"):
                logical = raw[len("evidence:") :]
                token = evidence_tokens.get(logical)
                if token is None:
                    raise ReferentBindingError(
                        "LINEAGE_EVIDENCE_UNBOUND:" + output + ":" + logical
                    )
                transformed.append("evidence:" + token)
            else:
                raise ReferentBindingError(
                    "LINEAGE_KIND_UNKNOWN:" + output + ":" + raw
                )
        if not transformed:
            raise ReferentBindingError("LINEAGE_EMPTY:" + output)
        out[output] = transformed
    return out


def append_bound_macrostep(
    capsule: Mapping[str, Any],
    *,
    producer: str,
    action: Any,
    requires: Sequence[str],
    provides: Sequence[str],
    values: Mapping[str, Any],
    evidence: Mapping[str, Any],
    lineage: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise ReferentBindingError("EVIDENCE_INVALID")

    act_token = action_token(action)
    ev_tokens = {
        _logical_id(str(key), "EVIDENCE_ID"): evidence_token(str(key), value)
        for key, value in evidence.items()
    }
    if len(ev_tokens) != len(evidence):
        raise ReferentBindingError("EVIDENCE_ID_COLLISION")

    transformed = _transform_lineage(lineage, act_token, ev_tokens)
    out = append_macrostep(
        capsule,
        producer=producer,
        action_ref=act_token,
        requires=requires,
        provides=provides,
        values=values,
        evidence_refs=list(ev_tokens.values()),
        lineage=transformed,
    )
    verdict = verify_capsule(out)
    if verdict.get("status") != "PASS":
        raise CapsuleError("BOUND_APPEND_FAILED:" + str(verdict.get("reason")))

    receipt = {
        "schema": SCHEMA,
        "record_index": len(out["records"]) - 1,
        "record_hash": out["records"][-1]["record_hash"],
        "action": copy.deepcopy(action),
        "action_sha256": content_sha256(action),
        "action_ref": act_token,
        "evidence": {
            logical: {
                "content": copy.deepcopy(evidence[logical]),
                "sha256": content_sha256(evidence[logical]),
                "token": ev_tokens[logical],
            }
            for logical in sorted(ev_tokens)
        },
    }
    return {"capsule": out, "binding_receipt": receipt}


def verify_binding(
    capsule: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        cap_verdict = verify_capsule(capsule)
        if cap_verdict.get("status") != "PASS":
            raise ReferentBindingError(
                "CAPSULE_INVALID:" + str(cap_verdict.get("reason"))
            )
        if not isinstance(receipt, Mapping) or receipt.get("schema") != SCHEMA:
            raise ReferentBindingError("RECEIPT_SCHEMA_INVALID")

        index = receipt.get("record_index")
        if not isinstance(index, int) or index < 0 or index >= len(capsule["records"]):
            raise ReferentBindingError("RECORD_INDEX_INVALID")
        record = capsule["records"][index]
        if record.get("record_hash") != receipt.get("record_hash"):
            raise ReferentBindingError("RECORD_HASH_MISMATCH")

        action = receipt.get("action")
        action_sha = content_sha256(action)
        expected_action_ref = "sha256:" + action_sha
        if receipt.get("action_sha256") != action_sha:
            raise ReferentBindingError("ACTION_HASH_MISMATCH")
        if receipt.get("action_ref") != expected_action_ref:
            raise ReferentBindingError("ACTION_REF_MISMATCH")
        if record.get("action_ref") != expected_action_ref:
            raise ReferentBindingError("CAPSULE_ACTION_REF_MISMATCH")

        evidence_rows = receipt.get("evidence")
        if not isinstance(evidence_rows, Mapping):
            raise ReferentBindingError("EVIDENCE_RECEIPT_INVALID")
        expected_tokens: list[str] = []
        for logical, row in sorted(evidence_rows.items()):
            lid = _logical_id(logical, "EVIDENCE_ID")
            if not isinstance(row, Mapping):
                raise ReferentBindingError("EVIDENCE_ROW_INVALID:" + lid)
            content = row.get("content")
            sha = content_sha256(content)
            token = evidence_token(lid, content)
            if row.get("sha256") != sha:
                raise ReferentBindingError("EVIDENCE_HASH_MISMATCH:" + lid)
            if row.get("token") != token:
                raise ReferentBindingError("EVIDENCE_TOKEN_MISMATCH:" + lid)
            expected_tokens.append(token)

        if list(record.get("evidence_refs") or []) != expected_tokens:
            raise ReferentBindingError("CAPSULE_EVIDENCE_REFS_MISMATCH")

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "record_index": index,
            "record_hash": record["record_hash"],
            "action_content_bound": True,
            "evidence_content_bound": True,
            "no_bypass_proved": False,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "no_bypass_proved": False,
            "acceptance_credit_delta": 0,
        }
