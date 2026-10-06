from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime import honesty_emission_gateway_v3 as gateway
from canonical.runtime import honesty_envelope_v1 as honesty

INPUT_SCHEMA = "PROJECT_BRAIN_LEDGER_FIRST_EMISSION_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_LEDGER_FIRST_EMISSION_OUTPUT_V1"

STANCE = {"SUPPORTED", "UNCERTAIN", "DECLINED"}
COMPLETE_STATES = {"VERIFIED", "PROMOTED"}
OBLIGATION_STATES = {"OPEN", "EXECUTED", "VERIFIED", "PROMOTED", "FAILED"}


class LedgerFirstError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _token(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerFirstError(name + "_INVALID")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    value = _token(value, name).lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise LedgerFirstError(name + "_INVALID")
    return value


def _receipts(value: Any, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise LedgerFirstError("RECEIPTS_NOT_LIST")
    out = [_sha256(x, "RECEIPT") for x in value]
    if not allow_empty and not out:
        raise LedgerFirstError("RECEIPTS_EMPTY")
    if len(out) != len(set(out)):
        raise LedgerFirstError("RECEIPTS_DUPLICATE")
    return out


def _obligations(raw: Any) -> tuple[list[str], list[dict[str, Any]], str]:
    if not isinstance(raw, list) or not raw:
        raise LedgerFirstError("OBLIGATIONS_REQUIRED")
    ids: list[str] = []
    rows: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise LedgerFirstError(f"OBLIGATION_{i}_INVALID")
        if set(item) != {"id", "state", "receipts"}:
            raise LedgerFirstError(f"OBLIGATION_{i}_FIELDS_INVALID")
        oid = _token(item.get("id"), f"OBLIGATION_{i}_ID")
        if oid in ids:
            raise LedgerFirstError("OBLIGATION_ID_DUPLICATE")
        ids.append(oid)
        state = _token(item.get("state"), f"OBLIGATION_{i}_STATE").upper()
        if state not in OBLIGATION_STATES:
            raise LedgerFirstError(f"OBLIGATION_{i}_STATE_INVALID")
        receipts = _receipts(
            item.get("receipts", []),
            allow_empty=state not in COMPLETE_STATES,
        )
        rows.append({"id": oid, "state": state, "receipts": receipts})
    if any(row["state"] == "FAILED" for row in rows):
        completion = "FAILED"
    elif all(row["state"] in COMPLETE_STATES for row in rows):
        completion = "COMPLETE"
    else:
        completion = "PARTIAL"
    return ids, rows, completion


def _declared_inputs(raw: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(raw, list):
        raise LedgerFirstError("DECLARED_INPUTS_NOT_LIST")
    normalized: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise LedgerFirstError(f"INPUT_{i}_INVALID")
        if set(item) != {"input_id", "sha256"}:
            raise LedgerFirstError(f"INPUT_{i}_FIELDS_INVALID")
        iid = _token(item.get("input_id"), f"INPUT_{i}_ID")
        if iid in seen:
            raise LedgerFirstError("INPUT_ID_DUPLICATE")
        seen.add(iid)
        digest = _sha256(item.get("sha256"), f"INPUT_{i}_SHA256")
        normalized.append({
            "input_id": iid,
            "sha256": digest,
            "material": True,
        })
        provenance.append({
            "event_id": "input::" + iid,
            "material": True,
            "disclosed": True,
            "receipts": [digest],
        })
    return normalized, provenance


def _content(raw: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    if not isinstance(raw, list):
        raise LedgerFirstError("CONTENT_ITEMS_NOT_LIST")
    normalized: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()
    rendered: list[str] = []
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise LedgerFirstError(f"CONTENT_{i}_INVALID")
        if set(item) != {"claim_id", "text", "stance", "evidence_receipts"}:
            raise LedgerFirstError(f"CONTENT_{i}_FIELDS_INVALID")
        cid = _token(item.get("claim_id"), f"CONTENT_{i}_CLAIM_ID")
        if cid in seen:
            raise LedgerFirstError("CLAIM_ID_DUPLICATE")
        seen.add(cid)
        text = _token(item.get("text"), f"CONTENT_{i}_TEXT")
        stance = _token(item.get("stance"), f"CONTENT_{i}_STANCE").upper()
        if stance not in STANCE:
            raise LedgerFirstError(f"CONTENT_{i}_STANCE_INVALID")
        evidence = _receipts(
            item.get("evidence_receipts", []),
            allow_empty=stance != "SUPPORTED",
        )
        if stance == "SUPPORTED" and not evidence:
            raise LedgerFirstError(f"CONTENT_{i}_SUPPORTED_WITHOUT_EVIDENCE")
        row = {
            "claim_id": cid,
            "text": text,
            "stance": stance,
            "evidence_receipts": evidence,
        }
        normalized.append(row)
        claims.append({
            "claim_id": cid,
            "supported": stance == "SUPPORTED",
            "explicit_uncertainty": stance == "UNCERTAIN",
            "declined": stance == "DECLINED",
            "evidence_receipts": evidence,
        })
        rendered.append(text)
    return normalized, claims, "\n".join(rendered)


def _beliefs(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise LedgerFirstError("BELIEF_ASSERTIONS_NOT_LIST")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise LedgerFirstError(f"BELIEF_{i}_INVALID")
        if set(item) != {
            "assertion_id", "registered_state", "asserted_state",
            "evidence_update_receipts"
        }:
            raise LedgerFirstError(f"BELIEF_{i}_FIELDS_INVALID")
        aid = _token(item.get("assertion_id"), f"BELIEF_{i}_ID")
        if aid in seen:
            raise LedgerFirstError("BELIEF_ID_DUPLICATE")
        seen.add(aid)
        registered = _token(
            item.get("registered_state"), f"BELIEF_{i}_REGISTERED"
        ).upper()
        asserted = _token(
            item.get("asserted_state"), f"BELIEF_{i}_ASSERTED"
        ).upper()
        if registered not in honesty.BELIEF_STATES or asserted not in honesty.BELIEF_STATES:
            raise LedgerFirstError(f"BELIEF_{i}_STATE_INVALID")
        updates = _receipts(
            item.get("evidence_update_receipts", []),
            allow_empty=True,
        )
        out.append({
            "assertion_id": aid,
            "registered_state": registered,
            "asserted_state": asserted,
            "evidence_update_receipts": updates,
        })
    return out


def compile_emission(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise LedgerFirstError("SCHEMA_INVALID")
        allowed = {
            "schema", "sequence", "emission_id", "task_id",
            "obligations", "declared_inputs", "content_items",
            "belief_assertions"
        }
        extra = set(doc) - allowed
        if extra:
            raise LedgerFirstError("UNDECLARED_TOP_LEVEL_FIELD:" + ",".join(sorted(extra)))

        sequence = doc.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
            raise LedgerFirstError("SEQUENCE_INVALID")
        emission_id = _token(doc.get("emission_id"), "EMISSION_ID")
        task_id = _token(doc.get("task_id"), "TASK_ID")

        obligation_ids, obligations, completion = _obligations(doc.get("obligations"))
        inputs, provenance = _declared_inputs(doc.get("declared_inputs", []))
        content, claims, rendered_text = _content(doc.get("content_items", []))
        beliefs = _beliefs(doc.get("belief_assertions"))

        payload = {
            "schema": "PROJECT_BRAIN_LEDGER_FIRST_RENDERED_PAYLOAD_V1",
            "task_id": task_id,
            "completion_state": completion,
            "content_items": content,
            "rendered_text": rendered_text,
            "declared_inputs": inputs,
            "belief_assertions": beliefs,
        }
        record = {
            "schema": "PROJECT_BRAIN_HONESTY_ENVELOPE_INPUT_V1",
            "task_contract": {
                "task_id": task_id,
                "required_obligations": obligation_ids,
            },
            "obligations": obligations,
            "completion_claim": completion,
            "provenance_events": provenance,
            "material_claims": claims,
            "belief_assertions": beliefs,
        }
        capsule = gateway.make_capsule(
            sequence=sequence,
            emission_id=emission_id,
            payload=payload,
            honesty_record=record,
        )
        raw = gateway.encode_capsule(capsule)
        parsed = gateway.adjudicate_broker_payload(raw)
        if len(parsed) != 1:
            raise LedgerFirstError("GATEWAY_PARSE_COUNT_MISMATCH")
        row = parsed[0]
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__LEDGER_FIRST_CONTENT_BOUND_EMISSION",
            "payload": payload,
            "payload_sha256": row["payload_sha256"],
            "honesty_record": record,
            "honesty_record_sha256": _sha(record),
            "gateway_emission": row,
            "ledger_complete_by_construction_for_rendered_dynamic_content": True,
            "completion_derived_from_obligation_ledger": True,
            "material_input_provenance_derived_from_declared_inputs": True,
            "arbitrary_dynamic_payload_field_permitted": False,
            "certificate_only": True,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "ledger_complete_by_construction_for_rendered_dynamic_content": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
